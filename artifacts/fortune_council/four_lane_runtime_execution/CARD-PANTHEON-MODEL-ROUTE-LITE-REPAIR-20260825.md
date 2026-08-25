---
id: CARD-PANTHEON-MODEL-ROUTE-LITE-REPAIR-20260825
status: ready
chain_id: PANTHEON-MODEL-ROUTE-CAPABILITY-20260825
role: repair
role_slot: repair
cycle: 1
type: implementation
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 使用者已固定 Writer／Reviewer 均為 Flash Lite；需修正正式模型路由、CLI capability 與錯誤分類，但不開架構岔，屬 strict/core-bounded Repair。
traces_to:
  - MR-LITE-001
  - MR-LITE-002
  - MR-LITE-003
---

# 修正 Pantheon 正式 Lite 模型路由

工作名稱：修正 Gemini Lite 模型路由與能力判定

## 唯一責任

修正目前把正式路由改成非 Lite 的錯誤，恢復並鎖定以下唯一角色契約：

- Writer：`gemini-3.5-flash-lite`
- Reviewer：`gemini-3.1-flash-lite`

不得以 `gemini-3.5-flash`、`gemini-3.1-pro`、3.6、3.7 或其他模型替代。不得重做 promotion、activation 或發文流程。

## 已確認事實

1. 使用者提供的 Antigravity 用量畫面同時列出 `Gemini 3.1 Flash Lite` 與 `Gemini 3.5 Flash Lite`，且兩者均有實際用量。
2. 8/17 原始可配置路由卡指定 Writer `gemini-3.5-flash-lite`、Reviewer `gemini-3.1-flash-lite`。
3. 目前 tracked config 被 8/25 candidate 改成 Writer `gemini-3.5-flash`、Reviewer `gemini-3.1-pro`。
4. 目前正式 CLI `<user-home>/.antigravity/bin/agy-1.1.3 models` 的唯讀輸出只列非 Lite selectable labels。這只能證明該 CLI inventory 沒公開 Lite label，不能證明帳戶沒有 Lite capability。
5. 現行 `validate_antigravity_cli_capabilities()` 把 route ID 綁到 `ANTIGRAVITY_MODEL_LABELS`，label 不存在或未出現在 `models` 時統一回 `model is unavailable`；目前錯誤訊息無法區分 route mapping 缺失、CLI inventory 未曝光、quota／rate limit或真正 model absence。
6. 原 Reviewer thread：`01a036cf-bebb-70e3-ad25-d95fcc2712ec`。Repair 交付後必須回此 thread re-review，禁止建立第二 Reviewer。

## Root finding

### MR-LITE-001 — P1 — 正式角色路由違反使用者固定的 Lite 契約

目前 production source 與 live runtime 採用非 Lite Writer／Reviewer；這不是允許的 fallback，而是錯誤模型。

### MR-LITE-002 — P1 — capability gate 把 route mapping／inventory 問題誤報為模型不存在

必須以可重現證據定位 Lite 的正式可呼叫 seam。不得因 dashboard 有額度就猜 CLI label，也不得因 `models` 未列就宣稱 Lite 不存在。

### MR-LITE-003 — P1 — 缺少 Lite 角色契約的 fail-closed 回歸

測試必須鎖定兩個 Lite ID、角色不可互換、不得靜默降級成非 Lite／Pro，並對 capability error 做封閉且可區分的分類。

## RED → GREEN 契約

1. 先建立一個最小 RED，證明 current config／capability path 不符合兩個 Lite role。
2. 只允許一次 `agy-1.1.3 models` 唯讀 inventory；若需要驗證未公開 label，Writer／Reviewer 各最多一次最小 sandbox/plan smoke，prompt 固定只輸出空 JSON。禁止枚舉或猜測其他模型名稱。
3. 若能證明 Lite 有正式可呼叫入口：做最小 source/config/test 修正並轉 GREEN。
4. 若無法證明 Lite 的正式入口：不得提交把 Lite ID 對應到臆測 label 的 source；交付 `BLOCKED_CLI_LITE_ENTRYPOINT_UNPROVEN`，列出唯一缺口與下一個外部前提。不得改回非 Lite。

## 可改範圍

- `config/agy_gemini_model_routes.v1.json`
- `scripts/agy_seo_copy_pipeline.py`
- `scripts/agy_gemini_v4_broker.py`
- `scripts/agy_gemini_outbox.py`（僅路由／錯誤分類直接受影響時）
- `tests/test_agy_seo_copy_pipeline.py`
- `tests/test_agy_gemini_v4_broker.py`
- `tests/test_agy_gemini_outbox.py`（僅直接回歸）
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-MODEL-ROUTE-LITE-REPAIR-20260825-RESULT.md`
- `artifacts/fortune_council/four_lane_runtime_execution/model_route_lite_repair_20260825/`

## 禁止範圍

- 禁止修改 installer、runtime manifest、LaunchAgents、production actor、queue/state、V0391 run、Publisher 或公開內容。
- 禁止 promotion、activation、Gemini 正式 job、run resume、publication、push、tag。
- 禁止新增 fallback 模型、改用 Pro／非 Lite、調 quota、繞過 capability gate或把 unavailable 當 retryable。
- 禁止另開 Reviewer、第二 Repair、replacement card/thread 或任何其他任務。
- 禁止碰主工作區既有未追蹤檔。

## 驗證

- Lite role RED/GREEN 回歸。
- capability inventory／mapping／closed diagnostic targeted tests。
- 受影響的 pipeline、broker、outbox targeted tests；只跑直接受影響範圍。
- `git diff --check`
- 若改 shell 才需 `bash -n`；本卡預設禁止改 installer。
- `rg -n "\\[DBG-" scripts tests` 無本卡殘留 debug prefix。

## 交付

- 一個 Repair candidate commit 與完整 SHA。
- RESULT 必須是 `DELIVERED_CANDIDATE` 或 `BLOCKED_CLI_LITE_ENTRYPOINT_UNPROVEN`，附 RED、GREEN／blocker、實際 changed files、驗證結果與剩餘風險。
- 不得宣稱已 activation、可發文或 production 已採用；主線收卡後只回原 Reviewer thread做 targeted re-review。
