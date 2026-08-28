---
schema_version: 1
title: Pantheon gen05 production entrypoint INVALID_RECEIPT repair reviewer response
date: 2026-08-28
status: RE_REVIEW_REQUESTED
review_artifact: artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_production_entrypoint_invalid_receipt_repair_20260828/REVIEW-PANTHEON-ACCEPTANCE-B-GEN05-PRODUCTION-ENTRYPOINT-INVALID-RECEIPT-REPAIR-20260828.md
production_mutation: false
provider_calls: 0
push: false
commit: false
---

# Reviewer response

前次 independent review verdict 為 `NO-GO`。本輪只修同一 bounded Repair 的 P1，並做最小 P2，不擴 production scope。

## P1 fix

`operator-exact-process-once` 現在會傳播 barrier / child runner nonzero：

- result `status == "executed"` 且 `returncode != 0` 時，外層 CLI 回該 nonzero code。
- 若 child code 不在 shell 1..255 範圍，外層回 `1`。
- `blocked` / `rejected` 仍回 `1`。

## P2 minimal fix

stdout 多行時，不回 raw stdout：

- 只找最後一個 non-empty JSON object line。
- 寫入 `child_result_summary_parse`。
- `child_result_summary` 只保留安全 allowlist 欄位。
- stdout/stderr 仍只有 bytes/sha256/empty receipt。

## RED

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_agy_gemini_runner.py::test_operator_exact_process_cli_propagates_child_nonzero_without_raw_streams tests/test_agy_gemini_runner.py::test_operator_exact_process_summarizes_last_json_line_without_raw_output -q`

Result: `2 failed`。

- 舊 CLI outer exit `0`，expected `42`。
- 舊多行 stdout 缺 `child_result_summary_parse`。

## GREEN

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_agy_gemini_runner.py::test_operator_exact_process_cli_propagates_child_nonzero_without_raw_streams tests/test_agy_gemini_runner.py::test_operator_exact_process_summarizes_last_json_line_without_raw_output -q`

Result: `2 passed`。

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_agy_gemini_runner.py::test_formal_production_lane_missing_transport_env_blocks_before_claim tests/test_agy_gemini_runner.py::test_operator_exact_process_uses_current_manifest_and_plist_env_without_stale_program tests/test_agy_gemini_runner.py::test_operator_exact_process_cli_propagates_child_nonzero_without_raw_streams tests/test_agy_gemini_runner.py::test_operator_exact_process_summarizes_last_json_line_without_raw_output tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_plan_only_accepts_provider_zero_invalid_receipt_legacy_null_correlation tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_legacy_null_correlation_result_recovers_without_actor_run_dir tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_rejects_invalid_receipt_when_provider_attempt_exists -q`

Result: `7 passed`。

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_agy_gemini_runner.py -q`

Result: `7 passed`。

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_agy_gemini_runner.py tests/test_agy_gemini_coordinator.py -k 'failed_external_job_replacement' -q`

Result: `28 passed, 308 deselected`。

`.venv/bin/python -m py_compile scripts/agy_gemini_runner.py scripts/agy_gemini_coordinator.py tests/test_agy_gemini_runner.py tests/test_agy_gemini_coordinator.py`

Result: PASS。

`git diff --check`

Result: PASS。

## Boundary

- 未 production mutation。
- 未 provider call。
- 未 push / promotion / deploy / publish / tag。
- 未 commit。
- 未修 locale plan 既有 8 fail，仍分類為外部既有 scope。
