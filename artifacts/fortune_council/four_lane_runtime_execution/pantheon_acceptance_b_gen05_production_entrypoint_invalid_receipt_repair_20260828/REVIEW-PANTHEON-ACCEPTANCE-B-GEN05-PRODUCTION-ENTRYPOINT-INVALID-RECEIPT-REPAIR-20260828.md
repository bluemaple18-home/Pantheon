---
schema_version: 1
title: Pantheon Acceptance B gen05 production entrypoint INVALID_RECEIPT repair review
date: 2026-08-28
status: COMPLETE
verdict: NO-GO
reviewer: independent_reviewer
scope: production entrypoint INVALID_RECEIPT bounded repair
base_head: 23eab63ea310
production_mutation: false
provider_calls: 0
push: false
promotion: false
deploy: false
publish: false
tag: false
---

# Verdict

NO-GO for production promotion / exact recovery.

The transport guard and replacement seam are narrowly implemented and the
targeted tests pass, but the new `operator-exact-process-once` CLI can still
return outer exit `0` when the barrier/child runner returns nonzero. That breaks
the operator contract for a production one-shot: automation and runbooks that
trust the CLI exit code can classify a failed exact recovery as successful.

# Findings

- [P1] Operator exact CLI masks child/barrier nonzero as outer success - `scripts/agy_gemini_runner.py:1748`

  `operator_exact_process_once` records `completed.returncode` in the JSON
  result, but always returns `status="executed"` after the subprocess returns.
  `main()` then exits nonzero only for `status in {"blocked", "rejected"}`.
  Therefore a barrier timeout/drift code or child `process-once` failure can
  produce JSON with `"returncode": 42` while the outer CLI exits `0`. I confirmed
  this with a read-only probe that mocked `operator_exact_process_once` to return
  `{"status":"executed","returncode":42,...}`; `main()` printed that result and
  returned `outer_exit 0`.

  Minimal fix: propagate nonzero `result["returncode"]` from
  `operator-exact-process-once` to the outer CLI, either by returning nonzero
  when `status=="executed" and returncode != 0`, or by classifying the result as
  a failed/blocked operator execution. Add a RED test that runs the CLI/main path
  with a child/barrier nonzero and asserts the outer exit is nonzero and the JSON
  safely exposes the child failure without raw stdout/stderr.

- [P2] Child result summary parsing drops valid summaries when stdout is multi-line - `scripts/agy_gemini_runner.py:598`

  The wrapper uses `json.loads(completed.stdout)`, so any banner, barrier
  receipt, warning, or extra newline-delimited JSON around the child receipt
  causes `child_result_summary` to disappear. This is not a production blocker
  because stdout/stderr are still represented by hashed stream receipts, and the
  P1 exit-code fix is the correctness gate. Minimal fix: parse the last
  non-empty JSON object line, or record an explicit `child_result_summary_parse`
  status while continuing to avoid raw stdout/stderr leakage.

# Positive Checks

Formal transport guard:

- `process_once` calls `_formal_production_transport_block` before `_peek_next_model`
  and `_claim_next`, so missing credential pool / allocator / model-route env
  blocks before queue claim.
- The test snapshot confirms no `processing`, `archive`, `failed`, or
  `production-attempts` mutation when formal production transport env is missing.

Operator entrypoint:

- The operator command is built from the current manifest, current barrier,
  service label lane, and plist `EnvironmentVariables`.
- It does not use plist `ProgramArguments`; stale `ProgramArguments` are ignored.
- Manifest-derived `PANTHEON_RUNTIME_*` env values overwrite stale plist runtime
  env such as `PANTHEON_RUNTIME_GENERATION`.
- Added receipts avoid raw stdout/stderr and avoid raw env/secret values. File
  envs are represented by presence/absolute/size/sha256; non-file envs by
  presence/sha256.

Replacement seam:

- The provider-attempt=0 INVALID_RECEIPT path is narrow: it requires
  `failure_category == INVALID_RECEIPT`, no `error_code`, no `credential_pool`,
  source request `transport_attempt == 0`, no production-attempt marker, and
  legacy null correlation authority matching the expected run ID.
- Normal failed replacement behavior still requires exact failure category and
  error code identity. Existing replacement tests plus the new production
  attempt marker negative reduce the risk of broad INVALID_RECEIPT acceptance.
- The end-to-end recovery test consumes replacement inbox identity after actor
  run dir removal and keeps durable `correlation_id` as `null`, closing the
  intended legacy identity path.

# Evidence

Inspected:

- `CARD-PANTHEON-ACCEPTANCE-B-GEN05-PRODUCTION-ENTRYPOINT-INVALID-RECEIPT-REPAIR-20260828.md`
- `pantheon_acceptance_b_gen05_production_entrypoint_invalid_receipt_repair_20260828/RESULT-PANTHEON-ACCEPTANCE-B-GEN05-PRODUCTION-ENTRYPOINT-INVALID-RECEIPT-REPAIR-20260828.md`
- `pantheon_acceptance_b_gen05_production_entrypoint_invalid_receipt_rca_20260828/RESULT-PANTHEON-ACCEPTANCE-B-GEN05-PRODUCTION-ENTRYPOINT-INVALID-RECEIPT-RCA-20260828.md`
- uncommitted diff vs HEAD `23eab63ea310`
  - `scripts/agy_gemini_runner.py`
  - `scripts/agy_gemini_coordinator.py`
  - `tests/test_agy_gemini_runner.py`
  - `tests/test_agy_gemini_coordinator.py`

Commands run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_agy_gemini_runner.py::test_formal_production_lane_missing_transport_env_blocks_before_claim tests/test_agy_gemini_runner.py::test_operator_exact_process_uses_current_manifest_and_plist_env_without_stale_program tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_plan_only_accepts_provider_zero_invalid_receipt_legacy_null_correlation tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_legacy_null_correlation_result_recovers_without_actor_run_dir tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_rejects_invalid_receipt_when_provider_attempt_exists -q
```

Result: `5 passed in 0.07s`.

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_agy_gemini_runner.py tests/test_agy_gemini_coordinator.py -k 'failed_external_job_replacement' -q
```

Result: `28 passed, 306 deselected in 0.35s`.

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_agy_gemini_runner.py -q
```

Result: `5 passed in 0.05s`.

```bash
.venv/bin/python -m py_compile scripts/agy_gemini_runner.py scripts/agy_gemini_coordinator.py tests/test_agy_gemini_runner.py tests/test_agy_gemini_coordinator.py
```

Result: PASS.

```bash
git diff --check
```

Result: PASS.

Read-only exit semantics probe:

```text
{"status": "executed", "returncode": 42, "stdout_receipt": {"empty": false}, "stderr_receipt": {"empty": false}, "env_receipt": {}}
outer_exit 0
```

# Required RED Test

Add a regression test for child nonzero propagation. Minimum acceptable shape:

- invoke `operator-exact-process-once` through `main()` or a subprocess-level CLI
  harness, not only `operator_exact_process_once`;
- make the barrier/child runner return a nonzero code, for example `42`;
- assert outer CLI exit is nonzero;
- assert JSON remains secret-safe and includes enough child failure identity
  (`returncode`, stream receipts, and optional safe child summary);
- assert no production/provider call and no queue claim mutation.

# Residual Risk

The repair result reports full `tests/test_agy_gemini_coordinator.py` still has
8 pre-existing locale-plan strict coverage failures outside this bounded repair.
Those are not attributed to this diff, but production push/promotion should not
use this review as a waiver for that separate gate.
