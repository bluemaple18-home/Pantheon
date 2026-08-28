---
schema_version: 1
title: Pantheon Acceptance B gen05 production entrypoint INVALID_RECEIPT repair re-review
date: 2026-08-28
status: COMPLETE
verdict: GO
reviewer: independent_reviewer
scope: P1/P2 closure re-review for production entrypoint INVALID_RECEIPT bounded repair
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

GO for commit/push of this bounded repair.

GO for production promotion / exact recovery from this review scope, provided
mainline still runs the normal production readiness gates and confirms the live
failed receipt shape matches this repair's narrow authority:
provider-attempt=0 `INVALID_RECEIPT`, no `error_code`, no `credential_pool`,
legacy null correlation, and no production attempt marker.

This re-review does not waive the separate pre-existing locale-plan 8-failure
coordinator suite blocker if mainline requires full-file green for promotion.

# Findings

No P0/P1/P2 findings remain.

# Closure Checks

P1 closure:

- `operator-exact-process-once` now propagates child/barrier nonzero from the
  `executed` result to the outer CLI.
- Exit range normalization is present: nonzero `1..255` returns as-is; other
  nonzero integer values return `1`.
- I verified this with a read-only probe:
  - child `42` -> outer `42`
  - child `300` -> outer `1`
  - child `-1` -> outer `1`
  - child `0` -> outer `0`

P2 closure:

- `_safe_child_result_summary` scans stdout from the end and parses only the
  last non-empty line shaped as a JSON object.
- It records `child_result_summary_parse`.
- `child_result_summary` is still allowlist-only via
  `OPERATOR_SAFE_CHILD_RESULT_KEYS`; untrusted fields such as `secret` are not
  copied.
- Raw stdout/stderr remain absent from the result; only byte count, sha256, and
  empty flag are returned.

Formal transport / operator entrypoint:

- Formal production transport env guard still runs before queue claim/provider
  attempt in `process_once`.
- Operator command still uses current manifest/barrier, service label lane, and
  plist `EnvironmentVariables`.
- Stale plist `ProgramArguments` remain ignored.
- Manifest runtime env overwrites stale runtime values from plist.
- Env receipts do not expose raw env or credential values.

Replacement seam:

- The legacy null correlation recovery path remains narrow and does not broaden
  general failed replacement behavior.
- The replacement path still requires `INVALID_RECEIPT`, no error code, no
  credential pool, source request `transport_attempt == 0`, no production
  attempt marker, and the synthetic legacy-null-correlation authority for the
  expected run ID.
- End-to-end consume identity is covered by the replacement inbox recovery test
  after actor run dir removal, with durable `correlation_id` preserved as null.

# Evidence

Inspected:

- `RESULT-PANTHEON-ACCEPTANCE-B-GEN05-PRODUCTION-ENTRYPOINT-INVALID-RECEIPT-REPAIR-20260828.md`
- `REVIEW-RESPONSE-P1-OPERATOR-EXIT-CODE-20260828.md`
- current diff vs HEAD `23eab63ea310`
  - `scripts/agy_gemini_runner.py`
  - `scripts/agy_gemini_coordinator.py`
  - `tests/test_agy_gemini_runner.py`
  - `tests/test_agy_gemini_coordinator.py`

Commands run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_agy_gemini_runner.py::test_operator_exact_process_cli_propagates_child_nonzero_without_raw_streams tests/test_agy_gemini_runner.py::test_operator_exact_process_summarizes_last_json_line_without_raw_output -q
```

Result: `2 passed in 0.04s`.

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_agy_gemini_runner.py::test_formal_production_lane_missing_transport_env_blocks_before_claim tests/test_agy_gemini_runner.py::test_operator_exact_process_uses_current_manifest_and_plist_env_without_stale_program tests/test_agy_gemini_runner.py::test_operator_exact_process_cli_propagates_child_nonzero_without_raw_streams tests/test_agy_gemini_runner.py::test_operator_exact_process_summarizes_last_json_line_without_raw_output tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_plan_only_accepts_provider_zero_invalid_receipt_legacy_null_correlation tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_legacy_null_correlation_result_recovers_without_actor_run_dir tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_rejects_invalid_receipt_when_provider_attempt_exists -q
```

Result: `7 passed in 0.10s`.

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_agy_gemini_runner.py -q
```

Result: `7 passed in 0.04s`.

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_agy_gemini_runner.py tests/test_agy_gemini_coordinator.py -k 'failed_external_job_replacement' -q
```

Result: `28 passed, 308 deselected in 0.36s`.

```bash
.venv/bin/python -m py_compile scripts/agy_gemini_runner.py scripts/agy_gemini_coordinator.py tests/test_agy_gemini_runner.py tests/test_agy_gemini_coordinator.py
```

Result: PASS.

```bash
git diff --check
```

Result: PASS.

Read-only exit range probe:

```text
42 42
300 1
-1 1
0 0
```

# Residual Risk

Range normalization is manually probed in this review but not separately covered
by a committed regression test for out-of-range return codes. I do not consider
that a P0/P1/P2 blocker because real subprocess return codes are normally already
bounded or negative-for-signal, and the implemented branch is simple. A small
future test for `300 -> 1` and `-1 -> 1` would still be a useful hardening
follow-up.
