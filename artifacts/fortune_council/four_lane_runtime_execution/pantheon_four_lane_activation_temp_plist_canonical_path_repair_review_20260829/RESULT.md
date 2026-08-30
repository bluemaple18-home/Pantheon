# Pantheon Four-Lane Activation Temp Plist Canonical Path Repair Review

Verdict: `GO`

This `GO` authorizes only mainline commit/integration of the bounded repair. It is not a production activation, canary, deploy, tag, or launchctl approval.

## Findings

No P0/P1 findings.

## Reviewed Diff

Candidate worktree: `<repair-worktree>`

Base: `6541693e929a20cbcffe8b070085b5f1caec7a92`

Tracked source/test diff:

- `scripts/install_pantheon_content_capacity_guard_launchd.sh`
- `tests/test_pantheon_content_capacity_guard.py`

Candidate artifacts present:

- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-FOUR-LANE-ACTIVATION-TEMP-PLIST-CANONICAL-PATH-REPAIR-20260829.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_activation_temp_plist_canonical_path_repair_20260829/RESULT.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_activation_temp_plist_canonical_path_repair_20260829/evidence.md`

No `uv.lock` drift was found.

## Acceptance Mapping

- Root fix: PASS. The candidate canonicalizes `TEMP_PLIST` immediately after `mktemp`, before the path is passed to `--capacity-plist` for `preactivation-transition`.
- Minimum frontier: PASS. The source change is confined to the capacity installer; no publisher, coordinator, lane, aggregate activation, queue, registry, production content, tag, deploy, or new authority surface is changed.
- Shared validator strictness: PASS. `scripts/pantheon_content_runtime_manifest.py` is not modified; `plist_receipt` still rejects non-absolute, missing, symlink, noncanonical realpath, wrong owner, and non-`0600` plist files.
- Fail-closed behavior: PASS. Empty `realpath`, non-regular file, or symlink at the canonicalized temp path exits before preactivation. Existing shared validator negative coverage remains in place.
- Cleanup: PASS. Reassigning `TEMP_PLIST` to the canonical path keeps the existing `trap cleanup EXIT` pointed at the same inode; the new regression test checks no alias temp residue remains.
- Bytes/uid/gid/mode/regular/non-symlink: PASS. The repair changes only the path string handed to validation. The candidate does not alter plist bytes mutation, stage copy, mode `0600`, or receipt owner/type checks.
- Exact alias RED to GREEN: PASS. Candidate evidence states the pre-repair `/var` alias path failed with `plist canonical realpath or owner mismatch`; the repaired test passes with `/var` and `/private/var` proven as the same inode.
- Normal/recovery coverage: PASS. Existing installer and preactivation tests remain, and the full affected files passed.
- Anti-expansion: PASS. No helper subsystem, env bypass, registry, FSM, production mutation, or broad macOS alias tolerance was introduced.

## Independent Verification

Commands independently rerun from review:

- `git -C <repair-worktree> diff --check`: PASS
- `bash -n <repair-worktree>/scripts/install_pantheon_content_capacity_guard_launchd.sh`: PASS
- `git -C <repair-worktree> diff --exit-code 6541693e929a20cbcffe8b070085b5f1caec7a92 -- uv.lock`: PASS
- In-memory compile of:
  - `scripts/pantheon_content_capacity_guard.py`
  - `scripts/pantheon_content_runtime_manifest.py`
  - result: PASS
- `PYTHONDONTWRITEBYTECODE=1 <repair-worktree>/.venv/bin/python -m pytest tests/test_pantheon_content_capacity_guard.py tests/test_pantheon_content_runtime_manifest.py -p no:cacheprovider`
  - result: `119 passed in 38.86s`

## Evidence Relied On

Candidate evidence:

- `<repair-worktree>/artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_activation_temp_plist_canonical_path_repair_20260829/evidence.md`
- `<repair-worktree>/artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_activation_temp_plist_canonical_path_repair_20260829/RESULT.md`

Code evidence:

- `scripts/install_pantheon_content_capacity_guard_launchd.sh:26-41` creates `TEMP_PLIST`, resolves it to canonical realpath, fail-closes on invalid canonical temp file, then reassigns `TEMP_PLIST`.
- `tests/test_pantheon_content_capacity_guard.py:1608-1644` exercises macOS `/var` to `/private/var` alias behavior through the public installer and verifies staging, no fake launchctl mutation, and no temp residue.
- `scripts/pantheon_content_runtime_manifest.py:319-332` remains unchanged and still enforces strict plist authority checks.

## Limits

This review did not run production install, production activation, live canary, scheduler, provider, reviewer, publisher, launchctl mutation, commit, push, tag, or deploy. Four-lane activation acceptance remains blocked until this repair is integrated and the activation acceptance card is rerun from fresh Rule24/25 through seven-service load, one canary per lane, public URL acceptance, and auto-stop verification.
