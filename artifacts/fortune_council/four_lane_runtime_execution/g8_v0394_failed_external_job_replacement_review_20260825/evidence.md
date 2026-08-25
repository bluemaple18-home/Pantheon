# V0394 failed external job replacement review evidence

## Scope

- Review card commit / current HEAD: `13deef25d11630c223c3fb4a067d09be6f4b958a`.
- Base: `998a797f3618a47a3d0493503e937a06b84e3da3`.
- Candidate: `a0c3ffe33e9dbbb80524fe75d0486063e02d67d7`.
- Worktree status before review: clean.
- CodeGraph was attempted first and unavailable for this worktree: `CodeGraph not initialized`.
- Candidate-only evidence was read with `git show a0c3ffe33e9dbbb80524fe75d0486063e02d67d7:<repo-relative-path>`.
- No checkout change, source/test/runtime mutation, production runtime action, merge, push, deploy, promotion, launchctl action, or archive action was performed.

## Commands

- `pwd` -> `/Users/mattkuo/.codex/worktrees/1400/Pantheon`.
- `git rev-parse HEAD` -> `13deef25d11630c223c3fb4a067d09be6f4b958a`.
- `git status --short` -> clean.
- `git diff --name-status 998a797f3618a47a3d0493503e937a06b84e3da3..a0c3ffe33e9dbbb80524fe75d0486063e02d67d7` -> only V0393 card/evidence plus `scripts/agy_gemini_outbox.py`, `scripts/agy_gemini_coordinator.py`, `tests/test_agy_gemini_outbox.py`, `tests/test_agy_gemini_coordinator.py`.
- `git diff --check 998a797f3618a47a3d0493503e937a06b84e3da3..a0c3ffe33e9dbbb80524fe75d0486063e02d67d7` -> passed with no output.
- Candidate Repair evidence reports `450 passed in 451.32s (0:07:31)` for `tests/test_agy_gemini_outbox.py tests/test_agy_gemini_coordinator.py`.

## Finding P1

- Severity: P1.
- Category: production safety / correctness / crash consistency.
- Path: `scripts/agy_gemini_coordinator.py:1631`.
- Trigger: `replace-failed-external-job --execute` crashes or is killed after `atomic_write_json(outbox_path, replacement_request)` and before both the formal replacement decision and run-state transition are durably written; or the runner wakes in that window.
- Evidence: Candidate writes the replacement request directly to live `outbox/*.json` at line 1631, writes the decision at line 1635, and updates state at lines 1637-1645. The runner independently claims any `outbox/*.json` by globbing and `os.replace` at `scripts/agy_gemini_runner.py:524` and `scripts/agy_gemini_runner.py:551`; it does not share the coordinator flock or require the replacement decision before provider execution.
- Risk: A replacement can be processed without the formal decision that makes the original failed job route to the replacement response. That creates an orphan provider call, leaves the original failed result terminal, breaks exactly-once recovery, and violates the contract that formal decision precedes redirection and that mutation is all-or-none.
- Suggested fix: Stage the replacement request under a non-runner-visible name/directory, write and fsync the decision/state transition first or use a resumable two-phase receipt, then atomically publish the request to `outbox` only after the formal decision is durable. Also make replay repair or complete any recognized in-progress receipt instead of rejecting a half-written replacement as `request already exists without decision`.
- Validation gap: Existing tests cover happy-path execute, same-authority replay, drift rejection, and plan-only zero mutation, but no crash/partial-write or runner-race harness exercises the window between outbox publish and decision/state durability.
- Confidence: high.

## Non-Blocking Observations

- P2 / validation hardening: source archive and failed receipt validation still uses separate path checks and later path reads (`scripts/agy_gemini_coordinator.py:1514`, `scripts/agy_gemini_coordinator.py:1524`, `scripts/agy_gemini_outbox.py:474`). A concurrent local path replacement can make validation and read operate on different filesystem objects. Use `openat`/`O_NOFOLLOW` plus `fstat` and read from the same descriptor if this endpoint will operate against mutable production queues. Confidence: medium.

## Verdict

`REPAIR_REQUIRED`

Minimum repair scope:

- Keep changes limited to `scripts/agy_gemini_coordinator.py`, `scripts/agy_gemini_outbox.py` if routing validation needs a receipt-state tweak, and the two affected test files.
- Add targeted tests for crash/partial states around replacement request, decision receipt, and state transition.
- Add a runner-race or equivalent harness proving runner cannot process a replacement before the formal decision exists.
- Preserve current fail-closed identity checks and CLI receipt shape.
