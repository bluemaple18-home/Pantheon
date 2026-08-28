---
status: RE_REVIEW_REQUESTED
owner: codex
task: pantheon_acceptance_b_gen06_queue_reactivation_repair_20260828
created_at: 2026-08-28T18:45:00+08:00
scope: bounded_repair
---

# RESULT — gen06 queue reactivation Repair

## Status

RE_REVIEW_REQUESTED.

本輪沒有 production、provider、publish、push、commit、promotion、tag 或手改 runtime state。只改 source/tests 與本輪 card/result。

## Changed files

- `scripts/agy_gemini_coordinator.py`
- `tests/test_agy_gemini_coordinator.py`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-ACCEPTANCE-B-GEN06-QUEUE-REACTIVATION-REPAIR-20260828.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_queue_reactivation_repair_20260828/RESULT-PANTHEON-ACCEPTANCE-B-GEN06-QUEUE-REACTIVATION-REPAIR-20260828.md`

## Implementation summary

- 新增 `reactivate-authorized-next-generation` formal coordinator CLI。
- 新增 `reactivate_authorized_next_generation_registry(...)`。
- 預設 plan-only，不寫檔。
- `--execute` 在 exact run identity、registry digest、authority-transition digest、state_after digest、run-local active next_generation 全部吻合後，才把 queue registry 從 `complete/result.complete` 切回 `active`。
- 沒有建立 generation、沒有呼叫 provider、沒有觸碰 publisher。
- active replay 只接受 clean active shape：exact reactivation receipt 相同，且無 stale `result/error_type/error_code/failure_category/transport_attempts`。

## Reviewer P1 response

P1-1：execute 進 `_run_identity_lock` 後重讀並重驗 transition/state。

- 新增鎖內 re-read：
  - `authority-transition-XX.json`
  - `continuation/state.json`
- 鎖內重新驗證：
  - transition canonical digest；
  - transition contract/action/run_id/generation/next_generation；
  - transition `state_after_sha256`；
  - transition embedded `state_after` canonical hash；
  - current run-local state canonical hash。

P1-2：active replay 僅 clean exact shape。

- `ALREADY_ACTIVE` 只在 registry 已 active、`authorized_next_generation_reactivation` receipt exact match，且沒有 stale terminal result/error 欄位時回傳。
- active registry 若帶 stale result/error 或 receipt drift，一律 fail closed。

Final P1 closure：active replay 額外綁定 selector-critical shape。

- reactivation receipt 會保存 `lane/mode/routing_schema_version` snapshot。
- active replay 時 current registry 的 `lane/mode/routing_schema_version` 必須與 receipt snapshot 精確一致。
- 新增 lane/mode/routing_schema_version 三個 drift probes，任一 drift 都 fail closed。

## RED / GREEN

Initial RED:

```text
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -k 'authorized_next_generation_reactivation' -q
8 failed, 329 deselected
```

Reviewer P1 RED probes:

```text
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -k 'revalidates_transition_inside_lock or rejects_active_replay_with_stale_result' -q
2 failed, 337 deselected
```

Final targeted GREEN:

```text
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -k 'authorized_next_generation_reactivation or resume_locale_plan_validation_failure or resume_other_failure_preserves_existing_job_lineage' -q
15 passed, 327 deselected in 0.56s
```

Additional validation:

```text
.venv/bin/python -m py_compile scripts/agy_gemini_coordinator.py tests/test_agy_gemini_coordinator.py
git diff --check -- scripts/agy_gemini_coordinator.py tests/test_agy_gemini_coordinator.py artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-ACCEPTANCE-B-GEN06-QUEUE-REACTIVATION-REPAIR-20260828.md artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_queue_reactivation_repair_20260828/RESULT-PANTHEON-ACCEPTANCE-B-GEN06-QUEUE-REACTIVATION-REPAIR-20260828.md
```

Both completed with no error output.

## Full affected classification

No new long full-file test was completed after the safety interruption. The prior completed coordinator full-file run showed:

```text
8 failed, 329 passed in 446.31s
```

The same 8 failing nodeids were run against a clean `f12f24315d` export and also failed with the same:

```text
LocalePlanValidationError: deterministic locale plan failure: external locale plan coverage fields are strict for article-01
```

Classification: PRE_EXISTING, not this Repair regression.

Compact comparison artifact:

- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_queue_reactivation_repair_20260828/baseline-nodeid-comparison.md`

The interrupted final full-file run had reached:

```text
8 failed, 215 passed in 151.18s
KeyboardInterrupt
```

The visible failures matched the same baseline locale-plan strictness failures.

## Anti-bloat accounting

Total current diff for source/tests:

```text
scripts/agy_gemini_coordinator.py    +137/-1
tests/test_agy_gemini_coordinator.py +200/-0
```

This remains under the original source/tests caps. The final P1 closure added about `+7` source lines and `+12` test lines, under the requested incremental caps.

## Risk

- The seam is intentionally narrow and does not generalize resume.
- It still requires exact hashes from the live registry and authority transition.
- Production use still requires fresh Rule24/25 and explicit production mutation authorization.

## Suggested commit message

`fix: reactivate authorized translation queue registry`
