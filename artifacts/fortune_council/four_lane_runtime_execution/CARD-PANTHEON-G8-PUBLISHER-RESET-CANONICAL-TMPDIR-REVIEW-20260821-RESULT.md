# G8 Publisher reset canonical TMPDIR Reviewer RESULT

- card: `CARD-PANTHEON-G8-PUBLISHER-RESET-CANONICAL-TMPDIR-REVIEW-20260821`
- formal reviewer thread ID: `01a02443-227d-7072-b8fa-42cdf82100e3`
- correction: `01a02434-2695-7261-9aa8-b718e74ef743` is the source/mainline thread, not this reviewer thread.
- base: `fdca2f7a2c45694b649940ca345c31ed336d0752`
- candidate: `51da4581afeb028903735cd98f918cc3482e6f52`
- reviewer cwd: `<repo-root>` (detached worktree)
- reviewer HEAD: `942b923ca21b4933f4236f04ab5c982140643ba6`
- verdict: `REVIEW_GO`

## Findings

No P0/P1 findings.

## Review assessment

- Correctness: `scripts/install_agy_gemini_coordinator_launchd.sh:469-475` resolves `TMPDIR` through `Cwd::realpath`, rejects an empty/non-directory result, then supplies the canonical path to `mktemp`. This removes the `/var` versus `/private/var` alias mismatch before the reset temporary plist exists.
- Fail-closed / mutation ordering: canonical-directory, `mktemp`, `cp`, `chmod`, transform, and temporary `publisher-plist-receipt` occur before backup creation (`:541`), live plist replacement (`:620`), or `launchctl` mutation (`:622`, `:628`). Existing `ERR` handling records a failure receipt before live mutation.
- Receipt observability: `:530-539` captures failed temp-receipt output and re-emits it to stderr before failing. The focused test at `tests/test_agy_gemini_coordinator.py:5885-5933` verifies `NO-GO` stderr, unchanged Publisher bytes, no mutation log, and unchanged peer plists.
- Regression / production safety: identity-field comparison and seven-service checks remain unchanged (`:501-528`, `:543-597`). `scripts/pantheon_content_runtime_manifest.py`, other live plists, launchctl paths, and child I/O behavior are outside the candidate diff.
- Test coverage: `tests/test_agy_gemini_coordinator.py:5839-5882` uses a symlinked `TMPDIR`, then verifies successful reset, the expected single bootstrap, all labels loaded, and unchanged peer plists. This and the receipt-failure test cover both altered boundaries.

## Verification

1. CodeGraph task-semantic query: unavailable because CodeGraph is not initialized in this reviewer worktree; bounded candidate diff/blob inspection was used as the prescribed fallback.
2. `git diff fdca2f7a2c45694b649940ca345c31ed336d0752..51da4581afeb028903735cd98f918cc3482e6f52 -- scripts/install_agy_gemini_coordinator_launchd.sh tests/test_agy_gemini_coordinator.py`: passed; complete scoped diff inspected.
3. `git diff --check fdca2f7a2c45694b649940ca345c31ed336d0752..51da4581afeb028903735cd98f918cc3482e6f52`: passed.
4. Candidate installer `bash -n`: passed.
5. In the exact reviewer worktree (`pwd=<repo-root>`, `HEAD=942b923ca21b4933f4236f04ab5c982140643ba6`): `PYTHONPATH=. <main-workspace>/.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -k 'canonicalizes_ambient_tmpdir_alias or reports_temp_receipt_failure_before_mutation' -q` passed: `2 passed, 254 deselected`.
6. In the same reviewer worktree: `PYTHONPATH=. <main-workspace>/.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -k publisher_terminal_reset -q` passed: `16 passed`.
7. `bash -n scripts/install_agy_gemini_coordinator_launchd.sh`: passed.

## Unverified scope and residual risk

- No real macOS LaunchAgents, `launchctl` calls, production reset, queue/runtime actor, remote, tag, push, or deploy was touched.
- The review is bounded to the stated candidate diff and focused reset tests; it does not substitute for a production canary.
