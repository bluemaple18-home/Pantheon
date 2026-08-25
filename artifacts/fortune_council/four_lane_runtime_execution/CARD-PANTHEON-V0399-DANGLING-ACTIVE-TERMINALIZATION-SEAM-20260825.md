---
id: CARD-PANTHEON-V0399-DANGLING-ACTIVE-TERMINALIZATION-SEAM-20260825
status: ready
chain_id: PANTHEON-PUBLISH-FLOW-ACTIVATION-CANARY-20260825
role: repair
cycle: 2
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: production registry lifecycle 的固定缺口與狀態機契約修復，屬 strict/core-bounded Repair。
---

# Pantheon dangling active terminalization seam

工作名稱：Pantheon dangling active terminalization seam

任務目的：新增唯一正式入口，將「registry active、實體 run_dir 已不可恢復」原子轉成 terminal failed 並產生可驗 receipt；關閉 V0397/V0398 的共同根因。

## Root invariant

`active registry` 必須對應可驗 `run_dir + brief identity`；若實體已永久遺失，只能經明確 authority 與 CAS preconditions 轉成 terminal，禁止假造 run、刪 registry或自動 seed 新 identity。

## 可改範圍

- `scripts/agy_gemini_coordinator.py`
- `tests/test_agy_gemini_coordinator.py`
- 本卡 RESULT
- `artifacts/fortune_council/four_lane_runtime_execution/g8_v0399_dangling_active_terminalization_20260825/evidence.md`

## 必要契約

- repo-owned CLI/public seam；名稱與參數依現有 coordinator CLI 風格。
- 必須鎖定 run_id、expected registry digest/identity、允許的固定 reason，並在 coordinator/registry lock 下 CAS。
- 只接受 `status=active`、run_dir canonical 且確實不存在、registry identity 未漂移。
- terminal 結果保留原 lineage/replacement metadata，寫入 `status=failed`、terminal reason/time 與獨立 receipt；receipt 可重算並綁 before/after digest。
- digest mismatch、run_dir 存在、狀態非 active、identity/path traversal、並發漂移：零 mutation fail-closed。
- retry 必須 idempotent；不得建立 run、job、replacement、queue payload或呼叫模型。
- coordinator automatic sweep 不得因 terminalization 建立替代 identity。

## 驗證

- RED 先重現：dangling active 無正式 terminal seam。
- GREEN 至少覆蓋 success、run_dir exists、digest mismatch、non-active、idempotent replay、concurrent drift、replacement metadata preservation、no new identity。
- 跑完整 `tests/test_agy_gemini_coordinator.py`、受影響 promotion tests、CLI help/syntax、`git diff --check`。

## 禁止

- 禁止 production/runtime mutation、push/tag/publish/Gemini、手寫 production JSON、migration、重構、另開 thread。
- 不處理其他 P2/P3 或舊資料清理。

## 交付

- 單一 candidate commit、changed files、RED/GREEN、完整測試、receipt schema與剩餘風險。
- 完成後回原 V0396 Reviewer，只複審本 lifecycle finding。

## RESULT

狀態：pending
