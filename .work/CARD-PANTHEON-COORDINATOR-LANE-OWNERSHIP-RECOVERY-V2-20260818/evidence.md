# Coordinator Lane Ownership Recovery V2 Evidence

activation_token: `ACTIVATE-PANTHEON-COORDINATOR-LANE-V2-d6525d6616`

## RED

Command:

```text
uv run --frozen python -m pytest tests/test_agy_gemini_coordinator.py -q -k "routing or missing_brief or bad_routing"
```

Result before implementation:

```text
7 failed, 187 deselected
```

Observed failures:

- `register_run` did not persist `routing_schema_version`, `mode`, or `lane`.
- `_migrate_pending_jobs` crashed on a legacy active state whose `brief.json` was missing.
- `cycle_once(..., lane_mode=True)` crashed through the same missing-brief path.
- `_lane_for_state` used mutable `brief.json` instead of immutable state routing fields.

## GREEN

Focused new tests:

```text
uv run --frozen python -m pytest tests/test_agy_gemini_coordinator.py -q -k "routing or missing_brief or bad_routing"
7 passed, 187 deselected
```

Focused existing routing regressions:

```text
uv run --frozen python -m pytest tests/test_agy_gemini_coordinator.py -q -k "register_run or lane_mode or new_only_cycle or cycle_exact_run_ids or oldest_active_runs"
18 passed, 176 deselected
```

Required full coordinator file:

```text
uv run --frozen python -m pytest tests/test_agy_gemini_coordinator.py -q
153 passed, 41 failed
```

Failure groups observed in the required full run:

- APF-004 adapter fixtures fail because `ASTRO-SCENARIO-BIG-THREE` is not present in the matrix backlog.
- launchd activation/adoption tests fail on existing receipt phase expectations such as `aggregate_preflight` versus `previous_barrier_validation`.

The full-run failures are outside this card's allowlist and do not involve the new Coordinator lane routing tests.

## Boundary

- No service was started.
- No production, Publisher, Node, prerender, launchd, queue data, transaction, tag, push, or deployment mutation was performed.

## Repair V2

activation_token: `REPAIR-PANTHEON-COORDINATOR-V2-REVIEW-89966ec28b`

Reviewer findings addressed:

- P1: `_lane_for_state_or_none` no longer swallows `OSError` from state routing migration writes. Only unroutable `ValueError` outcomes are converted to `None`.
- P2: `seed_failed_translation_replacements` now calls `_lane_for_state(..., root)` for active replacement and failed terminal states, so legacy translation routing is persisted before replacement selection/enqueue and no longer drifts with later `legacy_article_ids` changes.

Repair RED:

```text
uv run --frozen python -m pytest tests/test_agy_gemini_coordinator.py -q -k "write_failure or persists_legacy_routing"
2 failed, 194 deselected
```

Repair GREEN:

```text
uv run --frozen python -m pytest tests/test_agy_gemini_coordinator.py -q -k "write_failure or persists_legacy_routing"
2 passed, 194 deselected
```

Repair focused routing suite:

```text
uv run --frozen python -m pytest tests/test_agy_gemini_coordinator.py -q -k "routing or missing_brief or bad_routing or write_failure or persists_legacy_routing"
9 passed, 187 deselected
```

Existing routing regression subset:

```text
uv run --frozen python -m pytest tests/test_agy_gemini_coordinator.py -q -k "register_run or lane_mode or new_only_cycle or cycle_exact_run_ids or oldest_active_runs"
18 passed, 178 deselected
```

Post-repair full coordinator file:

```text
uv run --frozen python -m pytest tests/test_agy_gemini_coordinator.py -q
155 passed, 41 failed
```

The remaining full-file failures match the known baseline groups from the prior candidate: APF-004 adapter fixture/backlog and launchd activation/adoption receipt phase expectations. They are outside this card's repair allowlist.
