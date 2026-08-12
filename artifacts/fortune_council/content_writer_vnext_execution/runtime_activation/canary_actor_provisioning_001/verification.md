# Canary Actor Provisioning 001 Verification

Status: DELIVERED_CANDIDATE

Scope:
- Added a deterministic `scripts.prepare_pantheon_canary_actor` CLI with `plan`, `preflight`, and explicit `prepare`.
- Added optional runtime manifest binding for `actor_head` and `python_executable`.
- Added canary deployment preflight enforcement for one exact run and `--max-runs 1`.
- Added installer support for `PANTHEON_PUBLISH_EXACT_RUN_ID` gated by `PANTHEON_PUBLISH_MAX_RUNS=1`.
- Documented the single-run Canary actor provisioning workflow.

Verification:
- `uv run pytest tests/test_prepare_pantheon_canary_actor.py tests/test_pantheon_content_runtime_manifest.py tests/test_agy_content_publisher.py -q`
  - Result: `136 passed, 1 existing SyntaxWarning`
- `.venv/bin/python -m py_compile scripts/prepare_pantheon_canary_actor.py scripts/pantheon_content_runtime_manifest.py scripts/agy_content_publisher.py`
  - Result: PASS
- `bash -n scripts/install_agy_content_publisher_launchd.sh`
  - Result: PASS
- `.venv/bin/python -m json.tool artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/canary_actor_provisioning_001/negative-matrix.json`
  - Result: PASS
- `.venv/bin/python -m json.tool artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/canary_actor_provisioning_001/host-noop.json`
  - Result: PASS
- `git diff --check`
  - Result: PASS
- changed-files allowlist script
  - Result: ALLOWLIST_PASS

Boundary:
- No real actor root was created.
- No launchctl command was executed.
- No production queue/state/log roots were touched.
- No model calls, run creation, publisher transaction, tag, push, or deploy were executed.

Known residual risk:
- The candidate is source-only. A future mainline provisioning card must still run this against the selected production-safe sandbox root before any Canary publish can proceed.
