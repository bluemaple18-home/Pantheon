# RA-SLICE-001 Source Inventory

## Fixed Lineage

- Dispatch source SHA: `1f2dbce31827bc254d8860625512570d0bde6aef`
- Plan integration commit referenced by card: `bb96dd0f703b083d0acf3570e6da3d7101192b55`
- Fixed review commit: `ab682a298342aa2763d45d10d680923d39c1aeb6`
- Review verdict: `REVIEW_GO`

## CodeGraph

Bounded prepare command:

```text
bash ~/ai-core/scripts/worktree_capability_preflight.sh --prepare --with-codegraph --root <repo-root>
```

Result:

```text
provisioning=ready
codegraph=ready
codegraph_indexed_sha=1f2dbce31827bc254d8860625512570d0bde6aef
prepare_required=false
```

Task-semantic graph query:

```text
pantheon_content_capability_probe pantheon_content_capability_adapter test_pantheon_content_capability_probe formal_capability_preflight CAPABILITY_ORDER create run select publish transaction tag push
```

Graph-surfaced source files:

- `scripts/pantheon_content_capability_probe.py`
- `scripts/pantheon_content_capability_adapter.py`
- `tests/test_pantheon_content_capability_probe.py`
- `scripts/agy_content_publisher.py`
- `scripts/agy_gemini_coordinator.py`
- `scripts/agy_gemini_runner.py`

## Bounded Source Confirmation

- `scripts/pantheon_content_capability_probe.py` defines the seven capability names and writes a bounded dry-run chain, but does not provide a reusable strict receipt validator authority.
- `scripts/pantheon_content_capability_adapter.py` invokes the existing production boundaries in dry-run form and blocks digest or identity mismatch.
- `scripts/agy_content_publisher.py` exposes `formal_capability_preflight` for `select`, `publish`, `transaction`, `tag`, and `push`.
- `scripts/agy_gemini_coordinator.py` records `correlation_id` on `register_run`, supporting the plan's create/run evidence gap statement.
- Existing regression tests live in `tests/test_pantheon_content_capability_probe.py` and remained green after this slice.

## New Public Authority

- `scripts/pantheon_content_capability_receipt.py`
- `tests/test_pantheon_content_capability_receipt.py`

This slice intentionally does not import the new validator from the existing probe, adapter, coordinator, runner, Publisher, runtime manifest, capacity guard, deployment scripts, or production paths.
