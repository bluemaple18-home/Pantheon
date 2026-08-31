---
id: PANTHEON-FOUR-LANE-BASELINE-FIXTURE-SAFETY-AUTHORITY-ALIGNMENT
parent: PANTHEON-FOUR-LANE-CURRENT-ACTOR-OPERABILITY-ACCEPTANCE
status: ready
type: implementation
root_question: 修正共用 `_CampaignTranslationClient` 違反 fresh provider schema 的 test-only fixture drift，讓 requirement-mapped baseline 可在 fresh process 轉綠。
overall_status: BLOCKED_PHASE_2_BASELINE
classification: BASELINE_FIXTURE_DRIFT
production_activation_authorized: false
shadow_execution_authorized: false
frontier: Slice 2A 是唯一 frontier；後續 activation/shadow blocked。
runtime_actor_sha: "待驗證；runtime-owned source 不得變更"
acceptance_harness_sha: "待驗證；僅允許 test-only fixture 修正"
---

# 派工卡：Four-Lane Baseline Fixture Safety Authority Alignment

## 任務目的

修正共用 `_CampaignTranslationClient` 的 test-only fixture drift。Fixture 必須依傳入的 fresh provider schema 產生合法 coverage payload，使 requirement-mapped baseline 能在 fresh process 通過；不得藉此改動 production hydration、legacy contract 或任何 activation/shadow 行為。

## 穩定追蹤與驗收契約

| Trace ID | 契約 | 互相追蹤 |
| --- | --- | --- |
| FR-001 | fresh fixture 只輸出 schema-authorized coverage 欄位。 | FR-002、SC-001、SC-002 |
| FR-002 | 不改 production hydration／legacy contracts。 | FR-001、SC-001、SC-002 |
| SC-001 | exact baseline 全綠，且 provider calls = 0、production mutation = 0。 | FR-001、FR-002、SC-002 |
| SC-002 | diff 僅符合 allowlist，且通過 allowlist audit。 | FR-001、FR-002、SC-001 |

## Frontier 與授權邊界

本 Slice 2A 是唯一 frontier；後續 activation/shadow blocked。`production_activation_authorized: false` 與 `shadow_execution_authorized: false` 固定有效。

### Allowed change

- `tests/test_agy_gemini_coordinator.py`
- 本派工卡
- 唯一 result receipt：`artifacts/fortune_council/four_lane_runtime_execution/RESULT-PANTHEON-FOUR-LANE-BASELINE-FIXTURE-SAFETY-AUTHORITY-ALIGNMENT-20260831.md`

除上述三個路徑外不得修改檔案；result receipt 僅記錄證據與驗收結果。

### Forbidden

- 所有 `scripts/**`
- Publisher、promotion、runtime manifest、model routes、queue／registry
- production artifacts／public content
- commit、push、deploy、production writes、external writes

## 修正契約

1. Fixture 從傳入的 fresh schema 讀取 coverage item contract。
2. 驗證 schema `additionalProperties=false`。
3. 驗證 `safety_boundary` 不在 `properties`／`required`。
4. 驗證 identity field 恰為 `source_fact_id` 或 `source_ref`。
5. 每個 mapping 僅輸出 `identity`、`planned_h2_slot`、`coverage_note`。
6. 不得削弱 strict validation；不得擴張 legacy compatibility。
7. 不得改動 production hydration 或既有 legacy contract。

## Regression 必測矩陣

- fresh safety：RED（不合法 safety 欄位必拒絕）
- fresh no-safety：accepted
- hydrated plan：含 local deterministic safety
- receipt-bound legacy：accepted
- missing／wrong receipt：RED

## Baseline 範圍

必須在 fresh process 驗證下列項目：

- `test_campaign_translation_runs_new_and_rewrite_through_real_vertical_chain`
- 三個 private campaign E2E：compose、resume、capacity rollback
- 原 exact 26 manifest
- fresh／legacy safety tests
- expanded exact node IDs 記錄

禁止 skip、xfail、waiver。驗收時 provider calls 必須為 0，production mutation 必須為 0。

## Actor／harness split

- `runtime_actor_sha` 與 `acceptance_harness_sha` 必須分欄記錄。
- test-only commit 不得自動成為 runtime actor。
- runtime-owned source digest／diff 必須保持不變。

## Verification

依序執行並記錄證據：

1. targeted pytest。
2. original 26 baseline + added test + safety matrix。
3. `git diff --check`。
4. allowlist audit。
5. independent review。

所有結論須以可重現輸出、diff 與 receipt 支持；單次狀態文案不得單獨證明完成。

## Stop conditions

若發現任何 production source diff、provider call、production mutation 或新的 product defect，立即標記 `BLOCKED`，停止實作與後續 activation/shadow 工作，不得建立額外 Repair。

## 交付格式

交付時回報：修改檔案清單、expanded exact node IDs、targeted pytest 與 exact baseline 結果、provider／production mutation 計數、`git diff --check`、allowlist audit、independent review 結果，以及 result receipt 路徑。不得回報未經證據支持的完成狀態。
