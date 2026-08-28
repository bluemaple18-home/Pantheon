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

Provider0 RCA closure 已補：同一 execute path 現在也 receipt-first quarantine lane-level `archive` / `inbox` / `production-attempt` residue；下一次相同 deterministic request 不會吃舊 inbox，而會建立 fresh outbox job。

Null `last_job_id` RCA closure 已補：同一 seam 現在只在 registry `failed + LocalePlanValidationError + last_job_id=null` 且 operator 提供 exact expected job id/digests 時，透過 gen06 `plan-operation` prompt/schema 與 lane archive/inbox/attempt request identity 重新綁定 job identity；同時窄接受同 job prior quarantine + restored root cache shape。沒有掃描多 job、沒有猜 timestamp、沒有新 CLI。

沒有 production、provider、publish、commit、push。

## 變更檔案

- `scripts/agy_gemini_coordinator.py`
- `tests/test_agy_gemini_coordinator.py`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-ACCEPTANCE-B-GEN06-SAME-GEN-PLANNING-RETRY-REPAIR-20260828.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_same_gen_planning_retry_repair_20260828/RESULT-PANTHEON-ACCEPTANCE-B-GEN06-SAME-GEN-PLANNING-RETRY-REPAIR-20260828.md`

## Anti-bloat accounting

- source: +159 lines, within <=160 cap
- tests: +169 lines, within <=200 reviewer closure cap
- provider0 closure delta against 18b seam: source `+31/-11`, tests `+25/-11`; within additional `<=40` / `<=80` cap
- null last_job identity closure delta against 29c seam: source `+25/-11`, tests `+76/-1`; within additional `<=40` / `<=80` cap

Why not less:
- 需要同時鎖 registry、job attempt/archive/inbox、gen06 artifact digests、continuation active next_generation、gen07/candidate/reviewer absence、receipt-first quarantine、crash-window replay；provider0 RCA 已證明只搬 generation-local cache 會重吃舊 inbox，少於這些會回到 manual deletion 或 generic retry。

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
- Execute quarantines four generation planning cache files: `external-plan.json`, `plan-operation.json`, `planning-result.json`, `source-ref-map.json`.
- Execute also quarantines the exact lane-level transport residue for the same job: `archive/<job>.json`, `inbox/<job>.json`, `production-attempts/<job>.attempt`.
- Null `last_job_id` recovery is accepted only when the supplied expected job id is proven by exact lane archive/inbox/attempt digests plus `plan-operation` prompt/schema matching the lane archive.
- Reviewer P1 closure: null `last_job_id` branch now requires both `plan-operation` and archive `prompt_sha256` / `schema_sha256` to be strings matching `SHA256_PATTERN` before equality; missing both or invalid matching values fail closed.
- Prior same-job quarantine plus restored root cache is accepted only through the existing receipt identity; unrelated/mixed quarantine remains fail-closed.
- Quarantine receipt stores expected digests and is validated on replay.
- Quarantine receipt stores narrow selector snapshot (`lane` / `mode` / `routing_schema_version`); active replay rejects drift.
- Execute rechecks generation and lane residue boundary inside the run identity lock; TOCTOU gen07/candidate/lane residue drift fails closed and registry remains failed.
- Crash after quarantine but before registry resume replays to `RETRY_READY`.
- Same gen06 is re-enqueued through fresh outbox; stale inbox consumption is rejected; gen07 is not created.
- Candidate/reviewer boundary remains untouched.

## Provider0 RCA closure evidence

- RCA result: `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_same_gen_retry_provider0_rca_20260828/RESULT-PANTHEON-ACCEPTANCE-B-GEN06-SAME-GEN-RETRY-PROVIDER0-RCA-20260828.md`
- RED harness: `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_same_gen_retry_provider0_rca_20260828/temp-copy-red-harness.json`
- Closure test: `tests/test_agy_gemini_coordinator.py::test_same_generation_locale_plan_retry_execute_enqueues_fresh_gen06` now asserts old lane `archive/inbox/production-attempt` paths are absent, the same deterministic job id enters fresh `outbox`, and `consume_external_response` raises `ExternalJobPending` instead of consuming stale inbox.
- TOCTOU lane residue drift: `tests/test_agy_gemini_coordinator.py::test_same_generation_locale_plan_retry_rechecks_generation_boundary_inside_lock[lane_residue]`.

Updated verification:

- `python -m pytest tests/test_agy_gemini_coordinator.py -k 'null_last_job or same_generation_locale_plan_retry_recovers_null'`: 4 passed
- `python -m pytest tests/test_agy_gemini_coordinator.py -k same_generation_locale_plan_retry`: 19 passed
- `python -m pytest tests/test_agy_gemini_coordinator.py -k 'same_generation_locale_plan_retry or resume_locale_plan_validation_failure or resume_other_failure'`: 21 passed
- Reviewer P1 rerun:
  - `python -m pytest tests/test_agy_gemini_coordinator.py -k 'null_last_job_rejects_identity_drift and (missing_both_hashes or invalid_matching_hashes)'`: 2 passed
  - `python -m pytest tests/test_agy_gemini_coordinator.py -k 'null_last_job or same_generation_locale_plan_retry_recovers_null'`: 6 passed
  - `python -m pytest tests/test_agy_gemini_coordinator.py -k same_generation_locale_plan_retry`: 21 passed
  - `python -m pytest tests/test_agy_gemini_coordinator.py -k 'same_generation_locale_plan_retry or resume_locale_plan_validation_failure or resume_other_failure'`: 23 passed
- `python -m py_compile scripts/agy_gemini_coordinator.py tests/test_agy_gemini_coordinator.py`: PASS
- `git diff --check`: PASS

## Null last_job identity RCA closure evidence

- RCA result: `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_null_last_job_identity_rca_20260828/RESULT-PANTHEON-ACCEPTANCE-B-GEN06-NULL-LAST-JOB-IDENTITY-RCA-20260828.md`
- RED harness: `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_null_last_job_identity_rca_20260828/temp-copy-red-harness.json`
- Closure test: `tests/test_agy_gemini_coordinator.py::test_same_generation_locale_plan_retry_recovers_null_last_job_from_exact_residue`
- Drift matrix: `tests/test_agy_gemini_coordinator.py::test_same_generation_locale_plan_retry_null_last_job_rejects_identity_drift`
