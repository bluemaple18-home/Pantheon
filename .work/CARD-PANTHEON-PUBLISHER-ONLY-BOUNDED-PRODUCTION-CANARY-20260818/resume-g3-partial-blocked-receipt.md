# Publisher-only bounded production canary G3 evidence

狀態：PARTIAL / BLOCKED
時間：2026-08-18
formal_thread_id：01a013e9-9c66-7133-99e6-6d1694cb4dca

## 授權 identity

- authoritative_source_sha：2e8d4776725f75208ebf49d12a48924f538ab031
- authorized_run_id：auto-i18n-en-614aa4dc3542ab2c5637
- authorized_target：ASTRO-BASE-01:en
- activation_token：PANTHEON-PUBLISHER-ONLY-BOUNDED-PRODUCTION-CANARY-20260818-G1
- G3 RCA verdict：INPUT_CANONICALIZATION_ONLY
- G3 RCA thread：01a01410-6b60-7780-ba9f-b0fd4376a6cb

## Bootstrap / source state

- worktree cwd：/Users/mattkuo/.codex/worktrees/c879/Pantheon
- worktree HEAD：2e8d4776725f75208ebf49d12a48924f538ab031
- formal actor HEAD after promotion：2e8d4776725f75208ebf49d12a48924f538ab031
- CodeGraph readiness：CONTEXT_DEGRADED；本 worktree 未初始化 CodeGraph index，未作 authority 使用。

## G3 live queue canonical evidence

依使用者指定，從 live queue 重新唯讀抽出 preserve-run-id：

- count：140
- unique：140
- invalid：0
- canonical algorithm：sorted(set(run_ids))
- canonical list SHA256：72ac800347c15f7e7fa286f16207b0610b1b748453013ad20a5a3073a9bd2bcd
- expected SHA256：72ac800347c15f7e7fa286f16207b0610b1b748453013ad20a5a3073a9bd2bcd
- result：PASS

G2 order bug recorded：original preserve-run-id sequence was unsorted; first inversion from RCA was `auto-new-v1-20260817-024-01 > auto-new-v1-20260817-021-01`. G3 used canonical sorted unique order, not the RCA plan digest.

## Capacity evidence

Fresh exact-source capacity exercise was rebuilt under:

`.work/CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-PRODUCTION-CANARY-20260818/resume-g3-capacity-20260818/`

- receipt：`capacity-receipt.json`
- result：PASS
- cycle-bytes：1048576
- production_mutation：false
- swap_available：true
- capacity_receipt_digest used by promotion plan：6ef134b9554022a5cc7cedc4ece0f5c6c266e60228e4ce1e63a0a7e1ee235f61

## Formal promotion plan / apply / finalize

Formal promotion plan was rerun from current source and current live queue canonical ids.

- plan status：READY_TO_APPLY
- plan_digest：2d76183914656f5a4f43758ff0a8a0dbff773067b330d8558208f4e561578a7a
- target_manifest_digest：24afc9b76308b6f3e9aac094892a37c11dea7c920a494dd8420fb4d52676a9de
- target generation：g9-2e8d477672-20260818T090000Z
- target identity：gate2-actor:2e8d4776725f75208ebf49d12a48924f538ab031:four-lane-model-route-v1
- runtime_digest：e8261a1dbd08dac632f11aeb03ea3fa037b012e66a874be7fdf1ab9e59f297a7
- config_version：formal-runtime-v3-model-route-v1
- apply result：POSTCHECK_PASSED
- finalize result：COMMITTED
- rollback_bundle_finalized：true

Post-finalize runtime manifest evidence:

- manifest_digest：24afc9b76308b6f3e9aac094892a37c11dea7c920a494dd8420fb4d52676a9de
- actor_head：2e8d4776725f75208ebf49d12a48924f538ab031
- identity：gate2-actor:2e8d4776725f75208ebf49d12a48924f538ab031:four-lane-model-route-v1
- generation：g9-2e8d477672-20260818T090000Z

## Stage status before blocker

Private stage files observed under `/Users/mattkuo/Library/LaunchAgents/.pantheon-four-lane-stage`:

- `com.pantheon.agy-gemini-coordinator.plist`
- `com.pantheon.agy-gemini-new.plist`
- `com.pantheon.agy-gemini-rewrite.plist`
- `com.pantheon.agy-gemini-i18n-new.plist`
- `com.pantheon.agy-gemini-i18n-rewrite.plist`
- `com.pantheon.agy-content-publisher.plist`
- `publisher-exact-run-id`
- `publisher-max-runs`
- `manifest-digest`
- `model-route-digest`
- `model-route-path`
- `generation`

Publisher bounded stage evidence:

- `publisher-exact-run-id`：auto-i18n-en-614aa4dc3542ab2c5637
- `publisher-max-runs`：1

## Blocking failure

Capacity guard installer was run after coordinator and publisher private stage, before aggregate activation-only and before publisher activation. It returned NO-GO:

```json
{
  "bytes": 13363611,
  "disk_free_bytes": 72083587072,
  "disk_total_bytes": 245107195904,
  "file_count": 1694,
  "reasons": ["rss_telemetry_unknown"],
  "rss_available": false,
  "rss_bytes": null,
  "rss_error": "loaded_service_pid_missing:com.pantheon.agy-content-publisher",
  "rss_identity": {
    "absent_labels": [],
    "idle_labels": [],
    "inert_labels": [],
    "loaded_labels": []
  },
  "status": "NO-GO",
  "swap_available": true,
  "swap_error": null,
  "swap_used_bytes": 8095730237
}
```

Acceptance mapping：production canary readiness requires capacity safety gate PASS before LaunchAgent mutation/activation. Because capacity guard staging preflight returned NO-GO, the canary must stop fail-closed here.

## Explicit non-actions / preservation

- aggregate activation-only：not run
- `--activate-publisher-only`：not run
- publisher transaction：not created
- transaction directories matching `transaction-*`：0
- production content publish：0
- release/tag/push/public artifact：not created
- second publish：0
- aggregate normal：not run
- source fix：not attempted
- manual queue/state/plist/barrier edit：not attempted

## Current decision

Stop at PARTIAL / BLOCKED. Promotion is committed to the exact authorized source, and publisher bounded private stage exists, but activation and publish remain unstarted because the capacity guard installer preflight returned NO-GO.
