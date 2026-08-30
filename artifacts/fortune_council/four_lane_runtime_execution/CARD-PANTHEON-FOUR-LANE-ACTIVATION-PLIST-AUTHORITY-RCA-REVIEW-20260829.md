# Pantheon Four-Lane Activation Plist Authority RCA Review

## Task

Independently review the plist authority RCA for the four-lane activation blocker before any production activation resumes.

## Inputs

- RCA result: `<rca-worktree>/artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_activation_plist_authority_rca_20260829/RESULT.md`
- RCA card: `<rca-worktree>/artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-FOUR-LANE-ACTIVATION-PLIST-AUTHORITY-RCA-20260829.md`
- RCA evidence directory: `<rca-worktree>/artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_activation_plist_authority_rca_20260829/evidence/`
- RCA worktree source/history: read-only

## Scope

Review only whether the RCA closes these points:

- The exact failing object is the capacity installer `TEMP_PLIST`, not staged publisher/lane/live plist authority.
- macOS `/var` temp paths resolve to `/private/var`, while uid, mode, file type, and symlink checks remain correct.
- The shell order passes `TEMP_PLIST` into preactivation and fails before capacity stage copy.
- Shared `plist_receipt` rejects because strict `path == realpath` fails on the temp alias.
- RED double-run is byte-identical and the one-variable canonical path counterfactual turns GREEN.
- Last-good, first-bad, and cross-version masking are sufficiently closed.
- Production bytes are immutable, loaded service count remains 0, and scheduler/provider/reviewer/publisher calls remain 0.
- The sole root cause should be locked to `TEMP_PLIST_CANONICAL_PATH_CONTRACT_GAP` or the RCA's equivalent name.
- Repair must be limited to the capacity installer to validator seam by passing a canonical temp path or an equivalently narrower fix.

## Forbidden

- Do not modify RCA result, RCA evidence, RCA source, or tests.
- Do not touch production plist files, launchctl state, queue, registry, publisher, lanes, aggregate activation, tags, deploys, or pushes.
- Do not run installer, activation, scheduler, provider, reviewer, or publisher production commands.
- Do not broaden repair to shared `plist_receipt`, chmod/chown production, publisher/lane/aggregate changes, or any new authority mechanism.

## Required Verification

- Re-run isolated RED/GOOD harness without overwriting the RCA worktree evidence.
- Run diff-check on the main workspace after writing the review artifact.
- Compare RCA evidence to source order and filesystem facts.

## Output

Write only:

- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_activation_plist_authority_rca_review_20260829/RESULT.md`

The result must contain a single `GO` or `NO_GO`, P0/P1 findings if any, and an exact Repair allowlist with required tests.
