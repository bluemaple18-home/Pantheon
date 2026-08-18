# Four-Lane Production Canary Readiness Read-Only Audit

## Verdict

- capability verdict: `BLOCKED`
- capacity verdict: `NO-GO`
- overall: `NO-GO`
- production authorization: `false`
- canary authorization: `false`
- canary created by this audit: `false`

Fail-closed reason: the evidence required by the task card is absent from the audited checkout at `b268d4e1a202c535713e9ed4f9ded857c160b35c`; fallback evidence is either tracked but stale or present only as untracked files outside this worktree; current runtime/capacity state cannot be matched to the required source SHA, repair commits, manifest authority, or runtime identity.

## Audited Baseline

- Worktree: `/Users/mattkuo/.codex/worktrees/5c40/Pantheon`
- HEAD: `b268d4e1a202c535713e9ed4f9ded857c160b35c`
- `git status --short`: clean before report generation
- CodeGraph: not initialized for this worktree; audit used limited `rg`, `git`, `jq`, and official gate script evidence.

## Required Artifact Check

Task-card required paths:

- `handoff_20260817_pantheon_writer_vnext_four_lane_recovery.md`: missing from audited checkout and missing from `git ls-tree -r HEAD`.
- `artifacts/fortune_council/four_lane_runtime_execution/publisher_recovery_rewrite_acceptance_20260817/readiness-package/production-canary-capability-receipt.json`: missing from audited checkout and missing from `git ls-tree -r HEAD`.
- `artifacts/fortune_council/four_lane_runtime_execution/publisher_recovery_rewrite_acceptance_20260817/readiness-package/capacity-proof-normalized.json`: missing from audited checkout and missing from `git ls-tree -r HEAD`.

Repro command:

```bash
python3 /Users/mattkuo/ai-core/scripts/production_canary_readiness_gate.py --receipt artifacts/fortune_council/four_lane_runtime_execution/publisher_recovery_rewrite_acceptance_20260817/readiness-package/production-canary-capability-receipt.json
```

Observed result:

```json
{"status":"BLOCKED","failures":["[Errno 2] No such file or directory: 'artifacts/fortune_council/four_lane_runtime_execution/publisher_recovery_rewrite_acceptance_20260817/readiness-package/production-canary-capability-receipt.json'"]}
```

This alone satisfies the task-card stop condition: any missing artifact collapses to `NO-GO`.

## External Untracked Evidence

The same-named package exists in `/Users/mattkuo/Documents/Pantheon/artifacts/fortune_council/four_lane_runtime_execution/publisher_recovery_rewrite_acceptance_20260817/readiness-package/`, but it is not tracked in `HEAD`.

Evidence:

```text
git -C /Users/mattkuo/Documents/Pantheon status --short artifacts/fortune_council/four_lane_runtime_execution/publisher_recovery_rewrite_acceptance_20260817
?? artifacts/fortune_council/four_lane_runtime_execution/publisher_recovery_rewrite_acceptance_20260817/

git -C /Users/mattkuo/Documents/Pantheon ls-tree -r --name-only HEAD | rg 'four_lane_runtime_execution/publisher_recovery_rewrite_acceptance_20260817/readiness-package'
# no output
```

The external receipt passes the thin ai-core capability gate:

```json
{"execution_line_id":"exec-ra-slice-004","failures":[],"status":"READY"}
```

But it omits freshness fields:

```json
{
  "source_sha": null,
  "git_sha": null,
  "manifest_authority": null,
  "runtime_identity": null
}
```

The external capacity proof reports `PASS`, but is explicitly synthetic and also omits current identity/freshness fields:

```json
{
  "status": "PASS",
  "mode": "synthetic-non-production-capacity-proof",
  "source_sha": null,
  "git_sha": null,
  "manifest_authority": null,
  "runtime_identity": null
}
```

Therefore it is a useful clue but not authoritative evidence for this audited source SHA.

## Tracked Fallback Evidence

Tracked fallback receipt:

- `artifacts/fortune_council/content_writer_vnext_execution/apf_004_readiness/package/production-canary-capability-receipt.json`

Official gate result:

```json
{"execution_line_id":"exec-apf-004-readiness","failures":[],"status":"READY"}
```

Positive facts:

- Seven steps are present: `create`, `run`, `select`, `publish`, `transaction`, `tag`, `push`.
- `transaction`, `tag`, and `push` are represented separately.
- `canary_created=false`.

Blocking facts:

- The receipt has no top-level `source_sha`, `git_sha`, `manifest_authority`, or `runtime_identity`.
- The package was added by commit `75dd38bd07 Add APF-004 readiness evidence`.
- Later commits touching relevant runtime/source files include `b711184af2 Fix coordinator lane routing ownership` and `db74e966b4 Repair coordinator routing migration failures`.
- Per task-card freshness gate, those coordinator repairs must be covered by the receipt. They are not covered by this older package.

Tracked fallback capacity proof:

- `artifacts/fortune_council/content_writer_vnext_execution/apf_004_readiness/package/capacity-proof-normalized.json`

Positive facts:

- `status=PASS`
- `canary_created=false`
- two cycles
- `stop_loss_negative_result=BLOCKED`
- `capacity_negative_case_count=10`

Blocking facts:

- `mode=synthetic-non-production-capacity-proof`
- no `source_sha`, `git_sha`, `manifest_authority`, or `runtime_identity`
- not current to source `b268d4e1a2`
- not current to runtime manifest/plist state

## Current Runtime And Capacity Read-Only Snapshot

Readonly launchd/process observations:

- `launchctl list | rg 'com\\.pantheon'`: no output.
- `pgrep -fal 'pantheon|agy|gemini|content-publisher|capacity'`: no output after escalation.
- `ps -p 62609 -o pid,ppid,stat,etime,command`: header only; PID from stale capacity state is not running.

LaunchAgent plist files exist under `/Users/mattkuo/Library/LaunchAgents/` and point to:

- `PANTHEON_RUNTIME_ACTOR_HEAD=811999c1e2dcacdfed9b96b9ea95369b2da7372b`
- `PANTHEON_RUNTIME_IDENTITY_DIGEST=641dc6dfe28fe897dca9a9a9bf9f5eaa209318ca4b746a0da20d24d87b2ad8fb`
- `PANTHEON_RUNTIME_MANIFEST=/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/runtime-manifest.json`
- `PANTHEON_RUNTIME_MANIFEST_DIGEST=88ab341aedbba9d5cbff5885abd55182e1f3f6366e5f70321d5536bcb3cd70fa`

Runtime manifest file exists, but its internal values differ:

```json
{
  "identity": "gate2-actor:387d73eef8cb525efced572f5aef772ee9a135e2:four-lane-model-route-v1",
  "runtime_identity_digest": "fceb001e84af70bc4206a02529b60a741a2cae589ebb20e439bc699835914b3e",
  "manifest_digest": "1331c26c25d3e5883a4d634e91f0319d60c4fb824d6f30dadd1ff638cfa26836",
  "runtime_digest": "77bf68e9f2dbcccbd6476a55f7ecb506d429e609ddf22dd35ce2bc105b9fa62b",
  "actor_head": "387d73eef8cb525efced572f5aef772ee9a135e2"
}
```

Both `811999c1e2...` and `387d73eef8...` are older than the required coordinator repair commits `b711184af2` and `db74e966b4`.

Capacity state:

```json
{
  "status": "STOPPED",
  "bytes": 110475673,
  "file_count": 6815,
  "disk_free_bytes": 51889864704,
  "disk_total_bytes": 245107195904,
  "rss_available": false,
  "rss_bytes": null,
  "swap_available": true,
  "swap_used_bytes": 4863620546
}
```

Capacity stderr includes `RuntimeManifestError: actor git command failed` and an earlier `TypeError` when prior RSS was `None`. This is not current PASS capacity evidence.

## Capability Gate Result

`BLOCKED`

Reason: the exact required receipt is absent from the audited source tree; substitute receipts are either untracked external artifacts or stale tracked artifacts. Even when the thin official gate returns `READY` for substitutes, the required freshness fields and current runtime alignment are missing.

## Capacity Gate Result

`NO-GO`

Reason: no current capacity proof exists in the audited source tree for `b268d4e1a2`; substitute capacity proof is synthetic non-production, lacks current identity/source fields, and current capacity guard state is stopped with unavailable RSS telemetry.

## Overall Result

`NO-GO`

This card does not authorize production and does not authorize canary creation.

## Exact Blockers

- Missing tracked required handoff and readiness package at `b268d4e1a2`.
- Untracked external package cannot be used as source-SHA evidence.
- Available receipts lack source SHA, script digest binding, manifest authority, and runtime identity fields.
- Available tracked package predates `b711184af2` and `db74e966b4`.
- Current runtime manifest/plist values are inconsistent and older than required repairs.
- Current capacity guard state is not PASS: `STOPPED`, RSS unavailable, and logs show manifest/runtime failures.

## Stale Artifacts

- `/Users/mattkuo/Documents/Pantheon/artifacts/fortune_council/four_lane_runtime_execution/publisher_recovery_rewrite_acceptance_20260817/readiness-package/**`: untracked outside audited worktree; not part of `HEAD`.
- `artifacts/fortune_council/content_writer_vnext_execution/apf_004_readiness/package/**`: tracked but added at `75dd38bd07`, before the required coordinator repair commits.
- `/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/runtime-manifest.json`: current file points at actor head `387d73eef8...`, older than `b711184af2` and `db74e966b4`.
- `/Users/mattkuo/Library/LaunchAgents/com.pantheon*.plist`: plist values point at actor head `811999c1...`, also older and inconsistent with the runtime manifest file.

## Repro Commands

```bash
git rev-parse HEAD
git status --short
git ls-tree -r --name-only HEAD | rg 'handoff_20260817|publisher_recovery_rewrite_acceptance_20260817|production-canary-capability-receipt\\.json|capacity-proof-normalized\\.json'
python3 /Users/mattkuo/ai-core/scripts/production_canary_readiness_gate.py --receipt artifacts/fortune_council/four_lane_runtime_execution/publisher_recovery_rewrite_acceptance_20260817/readiness-package/production-canary-capability-receipt.json
git -C /Users/mattkuo/Documents/Pantheon status --short artifacts/fortune_council/four_lane_runtime_execution/publisher_recovery_rewrite_acceptance_20260817
python3 /Users/mattkuo/ai-core/scripts/production_canary_readiness_gate.py --receipt /Users/mattkuo/Documents/Pantheon/artifacts/fortune_council/four_lane_runtime_execution/publisher_recovery_rewrite_acceptance_20260817/readiness-package/production-canary-capability-receipt.json
jq '{schema_version,execution_line_id,production_target,correlation_id,canary_created,production_authorized,production_mutation,source_sha,git_sha,manifest_authority,runtime_identity,steps:(.steps|keys)}' /Users/mattkuo/Documents/Pantheon/artifacts/fortune_council/four_lane_runtime_execution/publisher_recovery_rewrite_acceptance_20260817/readiness-package/production-canary-capability-receipt.json
jq '{status,mode,canary_created,production_mutation,source_sha,git_sha,manifest_authority,runtime_identity,source_digest,policy,cycles:(.cycles|length),projections,stop_loss_negative_result,capacity_negative_case_count}' /Users/mattkuo/Documents/Pantheon/artifacts/fortune_council/four_lane_runtime_execution/publisher_recovery_rewrite_acceptance_20260817/readiness-package/capacity-proof-normalized.json
git log --oneline 75dd38bd07..HEAD -- scripts/agy_gemini_coordinator.py scripts/agy_content_publisher.py scripts/pantheon_writer_vnext_runtime_activation_readiness.py scripts/pantheon_writer_vnext_runtime_activation_capacity.py scripts/pantheon_content_capacity_guard.py scripts/pantheon_content_capability_receipt.py
launchctl list | rg 'com\\.pantheon'
pgrep -fal 'pantheon|agy|gemini|content-publisher|capacity'
jq '{schema_version,identity,runtime_identity_digest,manifest_digest,runtime_digest,config_version,generation,actor_head,actor_root,queue_root,publisher_state_root,log_root,service_labels}' /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/runtime-manifest.json
jq '{status,bytes,file_count,disk_free_bytes,disk_total_bytes,rss_available,rss_bytes,swap_available,swap_used_bytes,rss_identity}' /Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue/capacity-guard-state.json
```

## Next Single Repair Card Scope

Open one repair card to regenerate and commit the four-lane readiness package under `artifacts/fortune_council/four_lane_runtime_execution/publisher_recovery_rewrite_acceptance_20260817/readiness-package/` after current runtime/manifest/plist alignment. The repair must include capability receipt fields for source SHA, script digests, manifest authority, runtime identity, and correlation lineage; capacity proof must be current to the same runtime and include two-cycle, host reserve, RSS/swap, cleanup, and stop-loss evidence. The official gate must return `READY` with `canary_created=false`.
