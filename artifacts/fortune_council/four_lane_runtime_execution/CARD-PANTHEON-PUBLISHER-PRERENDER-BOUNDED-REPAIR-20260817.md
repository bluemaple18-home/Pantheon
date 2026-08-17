---
id: CARD-PANTHEON-PUBLISHER-PRERENDER-BOUNDED-REPAIR-20260817
status: ready
type: implementation
chain_id: pantheon-publisher-prerender-recovery-20260817
role: implementation
cycle: 1
thickness: standard
risk: high
model: gpt-5.6-terra
reasoning: medium
model_reason: bounded Publisher core repair with a fixed two-file scope and test-first stop conditions
---

# Publisher prerender 有界等待修復

## 目標

針對 Publisher 在 `_run_prerender()` 邊界等待、但沒有可觀測子程序的故障，先建立能重現「子程序無法正常完成時 Publisher 不可無界等待」的 RED，再做最小修復，使失敗有 timeout、結構化診斷與 fail-closed recovery 訊號。

## 已知事實

- `new`、`i18n-new`、`i18n-rewrite` bounded acceptance 已完成；`rewrite` 在共用 Publisher prerender 邊界停止。
- 現場留下 `state/transaction-ond6ep49`，但沒有足夠 parent PID、child PID、exit、signal、wait-point 證據，唯一根因尚未證明。
- 呼叫鏈為 `_run_prerender()` → `_run_checked()` → `subprocess.run()`；目前沒有顯式 timeout。
- 先前唯讀 RED 被 `ModuleNotFoundError: fastapi` 擋住，不算目標 RED。

## 允許修改

- `scripts/agy_content_publisher.py`
- `tests/test_agy_content_publisher.py`
- `.work/CARD-PANTHEON-PUBLISHER-PRERENDER-BOUNDED-REPAIR-20260817/**`

## 禁止範圍

- 不得啟動、reload 或修改 production／launchd。
- 不得修改、清理或 recovery `state/transaction-ond6ep49`、queue、runtime manifest、已發布文章、tag、sitemap。
- 不得 deploy、publish、push、force push。
- 不得修改 prerender 內容邏輯、四線 routing、Writer vNext 或其他非本故障檔案。
- 不得以 sleep、無界 retry、吞掉 exception 或環境 shim 掩蓋失敗。

## 執行契約

1. 先做任務語意 CodeGraph query，再由原始碼確認 `_run_prerender`／`_run_checked` 與測試 seam。
2. 先建立並實際執行一個單一 RED：模擬 prerender 子程序不結束或啟動後失聯，斷言 Publisher 在固定上限內終止並產生足以定位的診斷；無關 import／fixture／環境錯誤不算 RED。
3. 只有取得合格 RED 才可改 implementation。最小修復須：有界 timeout、fail closed、保留既有 `PolicyRejected` 行為，並提供 command、cwd、elapsed/timeout 與 process outcome 的可重驗訊號；不得記錄 secret 或整包環境。
4. GREEN 後補正常 prerender 與 policy failure regression，確保 create／rewrite 共用路徑不退化。
5. 若無法建立目標 RED，或修復需要超出 allowlist，立即交付 `BLOCKED`，不得猜根因或擴 scope。

## 驗收

- 目標 timeout／missing-child 回歸測試先 RED 後 GREEN。
- 既有 rewrite mode 與 `PolicyRejected` 測試通過。
- `uv run --frozen python -m pytest tests/test_agy_content_publisher.py -q` 通過；若成本過高，至少跑所有受影響 selector 並列出未跑項目。
- `git diff --check` 通過，diff 僅含 allowlist。
- 交付原子 candidate commit、`result.md` 與 `.work/.../evidence/verification.md`；不得自行宣稱已整合或 production 已修復。

## 停止條件

- 同一 blocker 兩次失敗即停。
- 不做 production acceptance；主線驗收 candidate 後另行決定是否進 recovery／canary。
