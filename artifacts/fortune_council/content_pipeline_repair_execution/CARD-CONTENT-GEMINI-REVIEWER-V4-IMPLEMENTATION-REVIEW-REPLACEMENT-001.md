---
card_id: CARD-CONTENT-GEMINI-REVIEWER-V4-IMPLEMENTATION-REVIEW-REPLACEMENT-001
chain_id: CONTENT-GEMINI-REVIEWER-V4-IMPLEMENTATION-001
status: CARD_DRAFTED
role: replacement_independent_reviewer
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
candidate_sha: bfdf6cb841235f87fd6af23576eb8a458a78f3c9
candidate_parent_sha: ef5b81307ca895d500ce1b6c346d17a451428942
replaces_thread_id: 019f8964-4599-7a02-a0ee-00346aa32666
replacement_reason: three consecutive Codex systemError interruptions before verdict
allowlist:
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_v4_implementation_review_replacement_001/**
forbidden_scope:
  - prior review task uncommitted evidence
  - candidate code, tests and implementation evidence
  - app/**, articles, registry, metadata and publishing files
  - dependency, real Gemini invocation, HTTP or external model
  - repair, merge, push, deploy, publish or content-line recovery
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_v4_implementation_review_replacement_001/
thread_id: PENDING
thread_status: CARD_DRAFTED
worktree_path: PENDING
cwd: PENDING
---

# Gemini Reviewer V4 Implementation｜Replacement Independent Review

## 任務邊界

- 原 Review thread 因同一 `systemError` 連續三次中止，沒有 verdict或commit；本卡是環境替代，不是 Repair。
- 從同一 candidate `bfdf6cb841235f87fd6af23576eb8a458a78f3c9` 建立全新 clean worktree；不得讀取或沿用原 thread 未提交 evidence。
- 完整執行 `CARD-CONTENT-GEMINI-REVIEWER-V4-IMPLEMENTATION-REVIEW-001` 的所有 review gate與 fresh probes。
- 唯一可寫為本卡 replacement evidence root；只審不修。

## 必驗已知反例

- Fresh probe 在 `OPERATION_CREATED` durable 後、fork 前製造 executable digest race。
- 核對真實 ledger、anchor、target launch count與最終 replay。
- 卡片要求此 pre-fork 路徑需有 durable `BROKER_ABORTED(CRASH_BEFORE_FORK)` 並回 `BLOCKED/0`；若 production 僅留下 `OPERATION_CREATED` 且回 `INVALID/UNKNOWN`，正式列 P1 並 `NO_GO`。
- 不得只用手工 ledger fixture取代 production path fault injection。

## 交付

- evidence 至少 `review.md`、`findings.json`、`fresh_probes.py`、`fresh_results.json`、`verification.txt`。
- verdict 只能 `GO / NO_GO`；若 NO_GO，給 bounded Repair allowlist，不得直接修。
- 建立單一純 review evidence commit，回完整 SHA、父 SHA、verdict、測試與 clean worktree。
- 禁止 Gemini/HTTP/model、dependency、merge、push、deploy、publish、真實 CLI canary或 content recovery。
