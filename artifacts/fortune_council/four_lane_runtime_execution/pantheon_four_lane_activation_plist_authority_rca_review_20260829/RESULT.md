# Pantheon Four-Lane Activation Plist Authority RCA Review

Verdict: `GO`

This `GO` accepts the RCA and authorizes only a bounded repair attempt. It is not approval to activate production services or run four-lane canaries.

## Scope Reviewed

- RCA result: `<rca-worktree>/artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_activation_plist_authority_rca_20260829/RESULT.md`
- RCA evidence: `<rca-worktree>/artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_activation_plist_authority_rca_20260829/evidence/`
- RCA source/history at `6541693e929a20cbcffe8b070085b5f1caec7a92`
- Review card: `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-FOUR-LANE-ACTIVATION-PLIST-AUTHORITY-RCA-REVIEW-20260829.md`

## Findings

No P0/P1 findings.

## Evidence Checked

- Independent isolated harness rerun:
  - RED run 1: `status=RED`, `reason=plist canonical realpath or owner mismatch`
  - RED run 2: same normalized payload
  - RED byte identity: `true`
  - GOOD counterfactual: changing only the capacity plist argument from `/var/...` to `/private/var/...` returns `GREEN`, `preactivation_transition=accepted`
  - production mutation in RED/GOOD: `false`
  - provider invocations in RED/GOOD: `0`
- Independent before/after read-only production snapshot during harness:
  - live plist sha map before == after: `true`
  - loaded count before/after: `0/0`
  - pid count before/after: `0/0`
- RCA evidence inventory:
  - staged publisher/coordinator/lane plists are g72, uid `501`, gid `20`, mode `0600`, regular, non-symlink
  - staged capacity plist is absent before successful capacity stage copy
  - existing live seven plists are g47, uid `501`, gid `20`, mode `0600`, regular, non-symlink, launchctl absent
  - `/var/folders/.../T` resolves to `/private/var/folders/.../T`
- Source order:
  - `scripts/install_pantheon_content_capacity_guard_launchd.sh:26` creates `TEMP_PLIST` through `mktemp`
  - `scripts/install_pantheon_content_capacity_guard_launchd.sh:161-170` passes `--capacity-plist "${TEMP_PLIST}"` into `preactivation-transition`
  - `scripts/install_pantheon_content_capacity_guard_launchd.sh:223` runs preactivation
  - `scripts/install_pantheon_content_capacity_guard_launchd.sh:229-230` would copy capacity plist into stage only after preactivation succeeds
  - `scripts/pantheon_content_capacity_guard.py:1080-1083` maps `CAPACITY_GUARD_LABEL` to caller-provided `capacity_plist`
  - `scripts/pantheon_content_capacity_guard.py:1098-1102` sends that path to shared `plist_receipt`
  - `scripts/pantheon_content_runtime_manifest.py:326-330` rejects when `path.resolve(strict=True) != path`
- History:
  - `94226be7a8c` introduced the mechanism by passing `TEMP_PLIST` as `--capacity-plist` and validating it through the shared staged receipt path.
  - `774e90ce103` exposed the same latent mechanism in the stopped-normal recovery path.

## Acceptance Mapping

- Exact failing object: PASS. The rejected path is capacity installer `TEMP_PLIST`; staged publisher/lane/live plist files are not the failing object.
- `/var` to `/private/var` canonical mismatch: PASS. The failing path is regular, uid `501`, mode `0600`, non-symlink; the mismatching field is strict logical path vs realpath.
- Shell ordering: PASS. Preactivation runs before capacity stage copy, so the stage target is not yet authoritative.
- Shared receipt strictness: PASS. The failure is emitted by `plist_receipt` before owner/mode relaxation or production mutation.
- RED/GOOD evidence: PASS. Double RED is byte-identical, and the one-variable canonical path counterfactual turns GREEN.
- Last-good/first-bad/masking: PASS. RCA sufficiently closes this as a first-bad mechanism introduced at the capacity-plist validation seam, later exposed by recovery-stage flow.
- Production immutability: PASS. Evidence and independent rerun show no live plist byte change, no loaded services, no pids, and no scheduler/provider/reviewer/publisher calls.
- Sole root cause: PASS. Lock as `TEMP_PLIST_CANONICAL_PATH_CONTRACT_GAP`.

## Repair Allowlist

Allowed repair frontier:

- In `scripts/install_pantheon_content_capacity_guard_launchd.sh`, canonicalize `TEMP_PLIST` before it is passed as `--capacity-plist` to `preactivation-transition`.
- Or create/pass the capacity candidate through an already canonical temp path that preserves the same bytes, owner, mode, regular-file, and non-symlink checks.
- Equivalent narrower fix is allowed only if it stays inside the capacity installer to validator seam and does not change authority ownership.

Forbidden repair surface:

- Do not relax shared `plist_receipt`.
- Do not chmod/chown, symlink, rewrite, or replace production plist files.
- Do not change aggregate activation, publisher, coordinator, lane runner, queue, registry, canary selection, tags, deploys, or production content.
- Do not add a new authority ledger, FSM, registry, status promotion rule, or broad macOS temp alias tolerance.

## Required Tests For Repair

- Add or update a regression test where noncanonical `/var/...` capacity temp input reproduces `plist canonical realpath or owner mismatch` before repair.
- Add or update a regression test where canonical `/private/var/...` capacity temp input is accepted without weakening uid/mode/symlink checks.
- Re-run the isolated RED/GOOD harness and confirm RED stays byte-identical on the unfixed fixture while the repaired seam turns GREEN.
- Re-run affected unit tests for `pantheon_content_capacity_guard` and `pantheon_content_runtime_manifest`.
- Run `git diff --check`.

## Residual Risk

The RCA review does not certify four-lane activation. After the bounded repair is implemented and reviewed, activation acceptance still needs fresh Rule24/25, loading the seven services, one canary per lane, publisher public URL acceptance, and auto-stop verification.
