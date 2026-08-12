# RA-SLICE-005 Verification Receipt

## Positive Probe

- `capacity-receipt.json` 保存兩個完整 synthetic non-production E2E cycles。
- `cycle-1-measurements.json` 與 `cycle-2-measurements.json` 含 before、peak、after-cleanup sample。
- 每個 cycle root 已清理，cleanup reclaim bytes/file count 均大於零。
- `canary_created=false` 且 `production_mutation=false`。

## Fail-closed Probe

- `negative-matrix.json` 覆蓋 bytes、file count、host reserve、RSS、swap、cleanup failure、unknown write、missing measurement、invalid policy 與 caller verdict。
- `blocked-capacity.json` 為 BLOCKED fixture，沒有 PASS receipt authority。

## Verification Commands

- `uv run pytest tests/test_pantheon_writer_vnext_runtime_activation_capacity.py -q`
- `uv run pytest tests/test_pantheon_writer_vnext_runtime_activation_e2e.py -q`
- `git diff --check`
