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
