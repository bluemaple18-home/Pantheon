# Canary actor repair 001 verification receipt

## Scope

- Card: `CARD-CONTENT-WRITER-VNEXT-CANARY-ACTOR-REPAIR-001`
- Activation: received for this dispatch; token value not persisted in evidence
- Mutations: allowlist only
- Production: no actor root provisioning, no `launchctl`, no production queue/state/model/run/publish/tag/push/deploy

## Repair summary

- `load_manifest()` keeps legacy compatibility when `actor_head` is absent.
- When `actor_head` is present, `actor_root` must be a canonical Git worktree root, clean, and `git rev-parse HEAD` must exactly equal the manifest SHA.
- `load_manifest(..., expected_python_executable=...)` now fails closed when the manifest Python is missing or differs from the actual deployment Python realpath.
- The content publisher installer rejects non-canonical/symlink Python paths before invoking Python modules, then validates the manifest with `--expected-python-executable`.

## Verification

- RED: `.venv/bin/python -m pytest tests/test_pantheon_content_runtime_manifest.py -q` before repair => `17 passed, 5 failed`
- GREEN targeted: `.venv/bin/python -m pytest tests/test_pantheon_content_runtime_manifest.py tests/test_prepare_pantheon_canary_actor.py tests/test_agy_content_publisher.py -q` => `142 passed, 1 warning`
- py_compile: `.venv/bin/python -m py_compile scripts/pantheon_content_runtime_manifest.py scripts/prepare_pantheon_canary_actor.py scripts/agy_content_publisher.py` => PASS
- shell syntax: `bash -n scripts/install_agy_content_publisher_launchd.sh` => PASS
- JSON parse: `negative-matrix.json` => PASS after receipt parse
- allowlist: PASS; changed source/test/evidence files are within the repair card allowlist
- git diff check: `git diff --check` => PASS
