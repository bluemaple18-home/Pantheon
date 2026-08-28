---
status: RE_REVIEW_REQUESTED
date: 2026-08-28
target_run: auto-i18n-ja-1414b75a404721e95e74
source_mutation: bounded
production_mutation: 0
provider_mutation: 0
commit_push: 0
---

# RESULT — gen06 same-generation planning retry Repair

## 結論

已實作唯一 bounded formal seam：`retry-same-generation-locale-plan`。

此 seam 只接受 hash-bound same-generation `LocalePlanValidationError` planning cache residue；plan-only zero-write，execute 在 run identity lock 內重讀並驗證 registry、job attempt/inbox/archive、continuation state、gen06 planning artifact digests、gen07 absence、candidate/reviewer absence，接著 receipt-first 將 stale gen06 planning cache 移入 run-local quarantine，再以既有 resume semantics 將 registry 轉回 active。

沒有 production、provider、publish、commit、push。

## 變更檔案

- `scripts/agy_gemini_coordinator.py`
- `tests/test_agy_gemini_coordinator.py`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-ACCEPTANCE-B-GEN06-SAME-GEN-PLANNING-RETRY-REPAIR-20260828.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_same_gen_planning_retry_repair_20260828/RESULT-PANTHEON-ACCEPTANCE-B-GEN06-SAME-GEN-PLANNING-RETRY-REPAIR-20260828.md`

## Anti-bloat accounting

- source: +159 lines, within <=160 cap
- tests: +169 lines, within <=200 reviewer closure cap

Why not less:
- 需要同時鎖 registry、job attempt/archive/inbox、gen06 artifact digests、continuation active next_generation、gen07/candidate/reviewer absence、receipt-first quarantine、crash-window replay；少於這些會回到 manual deletion 或 generic retry。

Why not more:
- 沒有新增 registry/FSM/database，沒有 generic retry，沒有跨 generation transition，沒有 publisher/provider path 變更。

Do not absorb:
- 不把 `resume` 改成自動清 planning cache。
- 不支援任意 planning retry。
- 不碰 production state 或 gen07 lifecycle。

## RED / GREEN

RED:

- `tests/test_agy_gemini_coordinator.py::test_same_generation_locale_plan_retry_plan_is_zero_write`
- 修前因 `scripts.agy_gemini_coordinator` 沒有 `retry_same_generation_locale_plan` 而失敗。

GREEN / regressions:

- `tests/test_agy_gemini_coordinator.py::test_same_generation_locale_plan_retry_plan_is_zero_write`
- `tests/test_agy_gemini_coordinator.py::test_same_generation_locale_plan_retry_cli_plan_only`
- `tests/test_agy_gemini_coordinator.py::test_same_generation_locale_plan_retry_execute_enqueues_fresh_gen06`
- `tests/test_agy_gemini_coordinator.py::test_same_generation_locale_plan_retry_rejects_drift`
- `tests/test_agy_gemini_coordinator.py::test_same_generation_locale_plan_retry_crash_window_replay`
- plus related `resume` and authorized-next-generation reactivation regressions

Final targeted command result:

- 29 passed in 0.49s

Other gates:

- `python -m py_compile scripts/agy_gemini_coordinator.py tests/test_agy_gemini_coordinator.py`: PASS
- `git diff --check`: PASS

## Reviewer focus

- Plan-only zero-write is covered.
- Execute quarantines only four planning cache files: `external-plan.json`, `plan-operation.json`, `planning-result.json`, `source-ref-map.json`.
- Quarantine receipt stores expected digests and is validated on replay.
- Quarantine receipt stores narrow selector snapshot (`lane` / `mode` / `routing_schema_version`); active replay rejects drift.
- Execute rechecks generation boundary inside the run identity lock; TOCTOU gen07/candidate drift fails closed and registry remains failed.
- Crash after quarantine but before registry resume replays to `RETRY_READY`.
- Same gen06 is re-enqueued; gen07 is not created.
- Candidate/reviewer boundary remains untouched.
