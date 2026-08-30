# RA-SLICE-004 Verification Receipt

## Positive Probe

- Seven official preflight steps produced one digest-continuous receipt.
- `positive-receipt.json`: PASS by `validate_capability_receipt`.
- `canary_created=false` and `production_mutation=false`.

## Fail-closed Probe

- `negative-matrix.json`: identity, digest, step, caller verdict, production boundary, Publisher drift, overlapping roots, dry-run mode, empty selection, untrusted root, and symlink escape probes BLOCKED.
- `blocked-receipt.json`: fail-closed fixture remains separate from the PASS receipt.

## Artifact Separation

- Positive artifacts are under `sandbox/evidence/positive/`.
- Blocked artifacts are under `sandbox/evidence/blocked/`.

## Verification Commands

- `uv run pytest tests/test_pantheon_writer_vnext_runtime_activation_e2e.py -q`
- `uv run pytest tests/test_agy_gemini_coordinator_capability_receipt.py tests/test_agy_content_publisher_capability_receipt.py tests/test_pantheon_content_capability_receipt.py -q`
- `git diff --check`
