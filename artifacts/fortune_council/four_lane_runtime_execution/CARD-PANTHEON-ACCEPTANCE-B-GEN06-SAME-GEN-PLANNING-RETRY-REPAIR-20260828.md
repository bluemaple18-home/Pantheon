---
status: RE_REVIEW_REQUESTED
date: 2026-08-28
owner: codex
scope: bounded_repair
target_run: auto-i18n-ja-1414b75a404721e95e74
production_mutation: 0
provider_mutation: 0
commit_push: forbidden
---

# CARD — gen06 same-generation planning retry Repair

## 目標

依 RCA 建立唯一 bounded formal seam：對 hash-bound `LocalePlanValidationError` stale gen06 planning cache 做 receipt-first quarantine，並用既有 resume semantics 重新暴露同一 gen06 writer retry。

## 可改範圍

- `scripts/agy_gemini_coordinator.py`
- `tests/test_agy_gemini_coordinator.py`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-ACCEPTANCE-B-GEN06-SAME-GEN-PLANNING-RETRY-REPAIR-20260828.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_same_gen_planning_retry_repair_20260828/`

## 禁止範圍

- production/runtime state mutation
- provider call
- publish/deploy/tag/push/commit
- manual queue/state edit
- generic retry/new registry/FSM/database
- gen07 或第二次 gen06

## 驗收

- plan-only zero-write
- execute 驗 exact run-dir/run-id、registry failed `LocalePlanValidationError`、last_job_id/job attempt succeeded、continuation active next_generation=6、gen06 artifact digests、gen07 absent、Reviewer/candidate absent
- receipt-first quarantine stale gen06 planning artifacts
- same gen06 re-enqueued through existing resume semantics
- crash-window idempotency and drift fail-closed
- RED→GREEN tests、targeted regressions、py_compile、`git diff --check`

## 實際結果

- source diff: +159
- test diff: +169
- targeted regressions: 29/29 PASS
- production/provider/commit/push: 0
- Reviewer P1 closure: lock-inner gen07/candidate/reviewer boundary recheck；receipt selector snapshot exact active replay
