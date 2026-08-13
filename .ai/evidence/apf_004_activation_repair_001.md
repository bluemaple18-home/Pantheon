# APF-004-ACTIVATION-REPAIR-001｜Sanitized evidence

## 邊界

- 所有 runtime root、home、LaunchAgents、barrier、readiness 與 mutation log 均由 pytest temp fixture 建立。
- `launchctl` 是 fixture stub；未呼叫 live `launchctl`、`--install`、`--activate`、deploy、publish、push 或外部服務。
- 本證據不含 secrets、live path 或 production receipt。

## RED

Command：

```text
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_aggregate_activation_rejects_mixed_installer_manifest_before_mutation
```

Observed：

```text
1 failed
FileNotFoundError: .../.pantheon-four-lane-stage/failure-receipt.json
```

同一 test 在讀 receipt 前已確認 activation `returncode != 0`、stdout 含 aggregate identity mismatch、fake launchctl mutation log 不存在、live-target fixture 不存在。

## GREEN

原始 RED command：

```text
1 passed in 2.63s
```

Success／fail-closed rollback matrix：

```text
tests/test_agy_gemini_coordinator.py::test_aggregate_activation_rejects_mixed_installer_manifest_before_mutation
tests/test_agy_gemini_coordinator.py::test_four_lane_activation_failure_restores_previous_plists_and_loaded_state
tests/test_agy_gemini_coordinator.py::test_four_lane_activation_success_commits_matching_private_stage
4 passed in 11.36s
```

Affected suite：

```text
bash -n scripts/install_agy_gemini_coordinator_launchd.sh
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py -k 'installer or aggregate_activation or four_lane_activation or four_lane_recovery_coordinator' tests/test_pantheon_content_runtime_manifest.py tests/test_pantheon_runtime_activation.py
30 passed, 151 deselected in 35.78s
```

## Acceptance mapping

- Pre-mutation fail-closed receipt：`status=ACTIVATION_REJECTED`，含本次 `correlation_id`、manifest digest＋generation stage identity、phase＋exit code。
- Live mutation failure receipt：保留 `ROLLBACK_COMPLETE|ROLLBACK_FAILED`，同樣含 correlation、stage identity 與 closed exit reason。
- Success path：matching private stage 啟動七個 fixture labels、barrier 驗證 PASS、stage 移除。

## P1 re-review follow-up

Reviewer edge RED：

```text
.venv/bin/python -m pytest -q 'tests/test_agy_gemini_coordinator.py::test_aggregate_activation_rejects_before_mutation_with_failure_receipt[invalid correlation-None-correlation_validation]'
1 failed
FileNotFoundError: .../.pantheon-four-lane-stage/failure-receipt.json
```

同一 fixture 已先確認 `exit=1`、correlation validation error、零 fake launchctl mutation。

GREEN matrix：

```text
5 passed in 14.19s
```

受影響 suite：

```text
31 passed, 151 deselected in 37.94s
```

無效 external correlation receipt 使用 generated `activation-<generation>-<pid>`，未回寫無效字串；`status=ACTIVATION_REJECTED`、`phase=correlation_validation`、stage identity 與 `exit_code=1` 均由 fixture 驗證。
