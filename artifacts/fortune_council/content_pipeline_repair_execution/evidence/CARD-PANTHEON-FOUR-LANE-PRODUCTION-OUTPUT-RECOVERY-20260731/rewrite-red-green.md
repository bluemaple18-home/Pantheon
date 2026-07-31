# A3 rewrite eligibility deadlock — RED/GREEN evidence

- Card: `CARD-PANTHEON-FOUR-LANE-A3-REWRITE-ELIGIBILITY-DEADLOCK-REPAIR-20260731`
- Base: `v0.3.183` / `de68b6b283493a3e9ca5f80286c682cb7846735e`
- Status: `CANDIDATE_READY_FOR_REVIEW`
- Production mutation: not authorized and not performed
- Provider call: not authorized and not performed

## Root cause

`summarize_legacy_rewrite_backlog()` counted every deterministic
clean-approval as publish-ready, but `collect_ready_rewrite_runs()` independently
excluded candidates whose retry budget was exhausted. The coordinator therefore
returned `publish_ready_first` forever even though Publisher could select no run.

The repair gives both call paths one retry classification:
`eligible`, `deferred`, `exhausted`, or `invalid`. The summary preserves the
total clean-approval count while exposing publish-ready and blocked/terminal
subsets. Coordinator behavior is now bounded:

- eligible clean-approval: `publish_ready_first`;
- deferred or invalid retry: `rewrite_retry_blocked`;
- exhausted retry with fresh inventory: seed fresh inventory;
- exhausted retry after inventory drain: `rewrite_retry_exhausted`.

No retry artifact is reset, deleted, rewritten, or replayed by this decision.

## RED

Command:

```text
.venv/bin/pytest -q tests/test_agy_gemini_coordinator.py::test_seed_legacy_rewrite_runs_advances_past_exhausted_clean_approvals
```

Deterministic fixture:

- five clean-approved rewrite candidates;
- all five at `attempts=3`, `max_attempts=3`, `eligibility=exhausted`;
- one fresh unattempted legacy record;
- Publisher-ready collection empty;
- retry bytes snapshotted before coordinator execution.

Observed result:

```text
1 failed
AssertionError: assert 'publish_ready_first' == 'seeded'
```

## GREEN

Focused command:

```text
.venv/bin/pytest -q \
  tests/test_agy_gemini_coordinator.py::test_seed_legacy_rewrite_runs_advances_past_exhausted_clean_approvals \
  tests/test_agy_gemini_coordinator.py::test_seed_legacy_rewrite_runs_surfaces_non_idle_retry_blocker \
  tests/test_agy_gemini_coordinator.py::test_seed_legacy_rewrite_runs_surfaces_exhausted_terminal_when_inventory_is_done \
  tests/test_agy_content_publisher.py::test_legacy_rewrite_backlog_classifies_retry_terminal_states_without_replay
```

Result:

```text
5 passed in 0.08s
```

The regression matrix covers fresh, deferred, invalid, exhausted, rejected, and
published runs. Repeated summary calls are identical, only the fresh candidate
is Publisher-ready, and retry artifact bytes remain unchanged.

Affected suites:

```text
.venv/bin/pytest -q tests/test_agy_gemini_coordinator.py tests/test_agy_content_publisher.py
128 passed, 1 warning in 15.53s
```

The warning is the existing `SyntaxWarning: invalid escape sequence '\/'` raised
by `test_preflight_test_command_selectors_resolve_to_top_level_tests`.

## Strict review repair

The strict review reproduced two malformed retry artifacts that bypassed the
intended `invalid` state:

```text
payload=[]                 -> AttributeError: 'list' object has no attribute 'get'
payload={"attempts": null} -> TypeError: int() argument must be ... not 'NoneType'
```

RED command:

```text
.venv/bin/pytest -q tests/test_agy_content_publisher.py::test_malformed_rewrite_retry_blocks_coordinator_without_mutation
2 failed
```

The parser now rejects a non-object top level before field access and treats a
non-parsable `attempts` value as `invalid`. GREEN result:

```text
.venv/bin/pytest -q tests/test_agy_content_publisher.py::test_malformed_rewrite_retry_blocks_coordinator_without_mutation
2 passed in 0.05s
```

For both payloads, the regression verifies `retry_invalid == 1`,
coordinator status `rewrite_retry_blocked`, identical repeated summaries, and
byte-for-byte unchanged retry artifacts.

## Scope and remaining risk

Changed scope is limited to the coordinator, Publisher, their two test modules,
and this evidence file. No runner, broker, multilingual pipeline, registry,
generated page, LaunchAgent, queue, ledger, candidate, archive, or `.work`
production state was changed.

Production canary, runtime actor alignment, strict review, deployment, and
publication remain outside this card and require their separate gates and user
authorization.
