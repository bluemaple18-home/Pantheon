# Writer vNext Integration 003 Verification Receipt

Status: CANDIDATE_READY_FOR_REVIEW
Resolved blocker: HOST_CAPACITY_FLOOR
Candidate commit created: true

## Passing Gates

- Overlay identity: 37 paths, all added.
- Overlay blob equality: 37/37 equal to `c7ad4881eabc47cbf43e5053f1ac79d7e70af546`.
- Overlay absent from source: 37/37.
- Publisher equality: Runtime/source/worktree blob `633bb011e404c0d6e77564f1885e2b5b2396b981`.
- Authority review verdicts: Runtime=REVIEW_GO, Writer contract=REVIEW_GO, Writer orchestration=REVIEW_GO.
- Source vs Runtime base: only Integration-002/003 task cards added.
- Changed path allowlist: PASS.
- git diff --check: PASS.
- Conflict marker scan: PASS.

## Resumed Full Gate

Required pytest suite: 412 passed, 1 warning, duration 161.22s (0:02:41), exit code 0.

Full output: `pytest-output-resume.txt`.

## Preserved Historical Failure

The initial full run remains in `pytest-output.txt`: 410 passed, 2 failed, 1 warning in 160.70s. The same two failures from the clean-source targeted reproduction remain in `source-cbed-targeted-failures.txt`. Only trailing whitespace was normalized; all failure text and results are preserved, with before/after hashes recorded in `host-capacity-recovery.md`.

The earlier `RUNTIME_BASE_TEST_CONTRACT_DRIFT` interpretation is superseded. Mainline established the blocker as `HOST_CAPACITY_FLOOR`, restored available capacity, and reported the exact-source targeted rerun as 2 passed in 12.12s. This worktree then passed the complete 10-group gate. See `host-capacity-recovery.md`.

## Final Decision

All Integration-003 composition and verification gates pass. The candidate is ready for review; production remains 0/4 and NO-GO under the card boundary.
