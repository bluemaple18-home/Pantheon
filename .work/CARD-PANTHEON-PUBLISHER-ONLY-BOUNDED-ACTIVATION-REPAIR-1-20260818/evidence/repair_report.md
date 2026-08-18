# Repair-1 evidence: Publisher exact-run receipt drift

- Finding: `PANTHEON-PUBLISHER-ONLY-REVIEW-F001`
- Repair regression ID: `PANTHEON-PUBLISHER-ONLY-REPAIR-1-F001-EXACT-RUN-RECEIPT`
- Source SHA: `6791ad8e88d685712a01be9b13ce2b650ef8100e`
- Production mutations: `0`

## RED

` .venv/bin/python .work/CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-REVIEW-20260818/reproduce_stale_exact_receipt.py`

Before the repair, the repro returned `0` and recorded Publisher `bootout` and
`bootstrap` mutations despite a stale `publisher-exact-run-id` receipt.

## GREEN

After the repair, the same repro returns `1`, prints
`publisher plist exact-run-id receipt mismatch`, and records no launchctl
mutation. The installer now requires either an exact equality between the
stage receipt and the staged plist child argument, or absence from both.

The regression matrix covers matching receipt/plist, neither present, missing
receipt, stale extra receipt, differing receipt value, and an empty receipt.

## Verification

- Publisher-only F001 regression tests: `10 passed`
- Publisher-only affected coordinator subset: `14 passed`
- Publisher installer subset: `3 passed`
- Runtime manifest suite: `48 passed`
- `bash -n` for both launchd installer scripts: passed
- `git diff --check`: passed

The full coordinator suite still has the pre-existing APF-004 matrix-backlog
failure (`ASTRO-SCENARIO-BIG-THREE` absent); it is outside F001 and was not
modified.
