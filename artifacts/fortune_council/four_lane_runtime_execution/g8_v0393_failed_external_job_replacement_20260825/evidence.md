# V0393 failed external job replacement evidence

## Scope

- Worktree HEAD before work: `998a797f3618a47a3d0493503e937a06b84e3da3`.
- CodeGraph was attempted first and unavailable for this worktree: `CodeGraph not initialized`.
- No production runtime, real queue/state, launchctl, activation, Publisher, publish, push, tag, model route, manifest, promotion, registry schema, or article content was touched.

## RED

### V0393 entrypoint RED

Command:

```bash
uv run pytest tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_cli_entrypoint_exists -q
```

Observed failure before implementation:

```text
invalid choice: 'replace-failed-external-job'
1 failed
```

This proved there was no formal public CLI entrypoint for replacing a terminal failed external job.

### V0394 crash/race RED

Reviewer receipt: `df84805b96c8b1ac5d21d3094da502c67d83d443`.

Command:

```bash
uv run pytest tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_runner_claim_race_leaves_no_executable_orphan -q
```

Observed failure before V0394 repair:

```text
AssertionError: assert not [queue/processing/<replacement-job-id>.json]
1 failed
```

This proved the reviewer P1: V0393 published live `outbox/*.json` before formal decision/state were durable, so the runner could claim an executable orphan replacement.

### Follow-up durable registry RED

Production-reproduced failure:

```text
{"status":"rejected","error":"run directory must contain brief.json"}
```

Minimal test command:

```bash
uv run pytest tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_plan_only_uses_durable_registry_when_run_dir_missing -q
```

Observed failure before follow-up repair:

```text
ValueError: run directory must contain brief.json
1 failed
```

This proved the formal replacement seam still depended on actor-local `run_dir/brief.json`, even though promotion only preserves durable queue/state and may atomically replace actor-local `.work`.

## GREEN

Targeted coordinator tests:

```bash
uv run pytest tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_cli_entrypoint_exists tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_plan_only_is_side_effect_free tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_execute_is_exactly_once_and_consumable tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_rejects_drift_without_mutation tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_rejects_second_authority_without_mutation tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_cli_plan_only_and_execute -q
```

Result:

```text
11 passed in 0.43s
```

Targeted outbox tests:

```bash
uv run pytest tests/test_agy_gemini_outbox.py::test_failed_external_replacement_request_preserves_logical_identity tests/test_agy_gemini_outbox.py::test_failed_external_replacement_decision_routes_source_to_replacement_result tests/test_agy_gemini_outbox.py::test_transport_failure_terminal_categories_do_not_enqueue_retry -q
```

Result:

```text
6 passed in 0.13s
```

Full affected files:

```bash
uv run pytest tests/test_agy_gemini_outbox.py tests/test_agy_gemini_coordinator.py -q
```

Result:

```text
450 passed in 451.32s (0:07:31)
```

V0394 targeted coordinator crash/race/TOCTOU tests:

```bash
uv run pytest tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_runner_claim_race_leaves_no_executable_orphan tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_crash_before_staging_is_zero_mutation tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_decision_crash_leaves_only_non_executable_stage_and_replays tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_state_crash_replays_without_second_replacement tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_final_publish_crash_replays_same_job tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_revalidates_archive_path_after_location_check tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_execute_is_exactly_once_and_consumable tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_rejects_second_authority_without_mutation -q
```

Result:

```text
8 passed in 0.28s
```

V0394 replacement targeted tests:

```bash
uv run pytest tests/test_agy_gemini_coordinator.py -k failed_external_job_replacement -q
uv run pytest tests/test_agy_gemini_outbox.py -k 'failed_external_replacement or validate_external_failure_receipt_rejects_path_replacement_drift or transport_failure_terminal_categories_do_not_enqueue_retry' -q
```

Result:

```text
17 passed, 266 deselected in 0.23s
7 passed, 167 deselected in 0.04s
```

Full affected files after V0394 repair:

```bash
uv run pytest tests/test_agy_gemini_outbox.py tests/test_agy_gemini_coordinator.py -q
```

Result:

```text
457 passed in 432.06s (0:07:12)
```

Follow-up durable registry targeted tests:

```bash
uv run pytest tests/test_agy_gemini_coordinator.py -k failed_external_job_replacement -q
uv run pytest tests/test_agy_gemini_outbox.py -k 'failed_external_replacement or validate_external_failure_receipt_rejects_path_replacement_drift or transport_failure_terminal_categories_do_not_enqueue_retry' -q
```

Result:

```text
19 passed, 266 deselected in 0.25s
7 passed, 167 deselected in 0.04s
```

Full affected files after follow-up repair:

```bash
uv run pytest tests/test_agy_gemini_outbox.py tests/test_agy_gemini_coordinator.py -q
```

Result:

```text
459 passed in 444.22s (0:07:24)
```

Diff whitespace check:

```bash
git diff --check
```

Result: passed with no output.

## Plan-only / CLI receipt

The new CLI entrypoint is:

```bash
python -m scripts.agy_gemini_coordinator --queue-root <state-root> replace-failed-external-job <run-dir> --job-queue-root <job-root> --lane <lane> --run-id <run-id> --job-id <failed-job-id> --request-sha256 <request-sha256> --namespace <namespace> --correlation-id <correlation-id> --failure-category CLI_NONZERO --error-code CLI_NONZERO --authority-digest <sha256> --plan-only
```

Machine-readable plan-only status is `plan_only`; execute status is `replacement_created`; same-authority replay status is `already_replaced`; rejection status from CLI is `rejected`.

## Contract evidence

- `CLI_NONZERO` remains terminal in the transport retry path; existing terminal taxonomy test still covers `GeminiCliFailure / CLI_NONZERO`.
- Replacement request preserves original model, role, prompt, schema, operation level, prompt/schema hashes, and logical `request_sha256`.
- Replacement uses a deterministic distinct `job_id` and `replacement` lineage payload with `lineage_kind=failed_external_job_replacement`, `lineage_attempt=1`, `lineage_id`, `source_job_id`, and `authority_digest`.
- V0394 repair publishes replacement in four recoverable phases: runner-invisible staging request, formal decision receipt, run registry transition, final atomic live outbox publish.
- Crash before staging leaves zero mutation; crash before decision leaves only non-executable staging and same-authority replay completes; crash before state leaves decision+staging and replay completes; crash before final publish leaves decision+state+staging and replay publishes the same job.
- Runner claim after final live publish is allowed only after decision/state are durable; the test verifies decision receipt and registry point to the replacement before claim.
- Source archive and failed receipt JSON reads now use descriptor-bound `O_NOFOLLOW` + `fstat` validation; tests cover archive path replacement after location check and failed receipt path replacement drift.
- Follow-up repair makes formal replacement plan/execute read active run identity from durable registry by expected `run_id`; local `brief.json` is still verified when present, but is no longer required when promotion has removed actor-local `.work`.
- Follow-up continuation path lets `cycle_once(..., exact_run_ids=...)` complete a run with formal replacement state and missing actor-local run_dir by consuming the archived source request through the formal replacement decision/result. This proves recovery is not limited to enqueue.
- Source archive request and source failed receipt are preserved; no source failed evidence is deleted or rewritten.
- Identity drift, second authority, existing success result, non-active run, last-job drift, missing archive, and missing failed receipt are all rejected with zero mutation in tests.
