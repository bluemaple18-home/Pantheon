---
card_id: CARD-CONTENT-GEMINI-REVIEWER-V4-IMPLEMENTATION-REPAIR-001
chain_id: CONTENT-GEMINI-REVIEWER-V4-IMPLEMENTATION-001
status: CARD_DRAFTED
repair_generation: 1
role: production_repair
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
base_candidate_sha: bfdf6cb841235f87fd6af23576eb8a458a78f3c9
review_evidence_sha: ae3cf1b
allowlist:
  - scripts/agy_gemini_v4_broker.py
  - tests/test_agy_gemini_v4_broker.py
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_v4_implementation_repair_001/**
forbidden_scope:
  - scripts/agy_gemini_runner.py
  - tests/test_agy_gemini_outbox.py
  - implementation/review/architecture evidence modification
  - other production modules, app/**, articles and publishing files
  - dependency, real Gemini invocation, HTTP or external model
  - merge, push, deploy, publish or content-line recovery
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_v4_implementation_repair_001/
thread_id: PENDING
thread_status: CARD_DRAFTED
worktree_path: PENDING
cwd: PENDING
---

# Gemini Reviewer V4 Implementation Repair 1｜Pre-fork durable abort

## 唯一 Finding

`V4_IMPL_PREFORK_ABORT_EVENT_MISSING`（P1）：production `run_single_shot` 在 `OPERATION_CREATED` durable 後、fork 前發生 executable digest mismatch，只留下單一建立事件，replay 為 `INVALID/UNKNOWN`；規格要求可判定的 pre-fork failure 必須 durable 記錄 abort 並為 `BLOCKED/0`。

## 固定修正

- real `run_single_shot` path 在 `OPERATION_CREATED` 後先 durable `BROKER_ATTEMPTED`。
- 在 `FORK_ATTEMPTED` 前的可判定 failure（至少 Reviewer 的 digest mismatch case）durable append `BROKER_ABORTED(outcome=CRASH_BEFORE_FORK)`。
- 最終 result與 fresh replay固定 `BLOCKED`、process count `0`、complete false、automatic resend false；target launch count仍為0。
- 不得把 schema/binding/order/frame/chain等資料不合法案例改成 BLOCKED；它們仍是 `INVALID/UNKNOWN`。
- 不得改 runner、flag、anchor boundary或其他已通過行為；不得新增 retry/fallback或第二 launcher。

## RED／GREEN 與回歸

- 完整讀 replacement review evidence，先直接執行未修改的 `fresh_probes.py` 重現 RED。
- 新增 production-path regression 到 `tests/test_agy_gemini_v4_broker.py`；禁止以手工 ledger fixture冒充。
- GREEN 後同一 Reviewer probe 必須顯示事件 `OPERATION_CREATED → BROKER_ATTEMPTED → BROKER_ABORTED`、0 target、`BLOCKED/0`。
- 重跑 broker focused、原 implementation focused/affected、全套 tests、py_compile、determinism、allowlist/privacy、`git diff --check`。
- 兩個既有 Ziwei provider baseline失敗不得在本卡修改。

## 交付

- evidence至少 `root-cause.md`、`red-green.txt`、`verification.txt`、`decision.md`。
- 單一 Repair 1 candidate commit；狀態只能 `READY_FOR_REVIEW / BLOCKED`，不得自審 GO。
- 回原 replacement Reviewer或全新 Reviewer re-review；GO前不得整合、真實 CLI canary或恢復內容線。
