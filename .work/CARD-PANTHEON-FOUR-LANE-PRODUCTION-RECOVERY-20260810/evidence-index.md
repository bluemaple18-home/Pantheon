---
id: CARD-PANTHEON-FOUR-LANE-PRODUCTION-RECOVERY-20260810
status: ready_for_final_re_review
type: evidence_index
repair_round: 2
---

# Repair-2 證據索引

## Entry points

- Actor：`scripts/pantheon_content_actor_recovery.py`。
- Capability probe：`scripts/pantheon_content_capability_probe.py`。
- 七步正式 dry-run adapter：`scripts/pantheon_content_capability_adapter.py`。
- Aggregate/runtime/barrier gate：`scripts/pantheon_content_runtime_manifest.py`。
- Unique activation：`scripts/install_agy_gemini_coordinator_launchd.sh --activate`。

## Artifact

- Positive adapter chain：`evidence/repair-2/capability-verified-positive/`。
- 七個 negative adapter chains：`evidence/repair-2/capability-verified-negative-{create,run,select,publish,transaction,tag,push}/`。
- Capacity：`evidence/repair-2/capacity-exercise.json`。
- Readiness receipt：`production-canary-capability-receipt.json`。
- Production capacity boundary：`capacity-safety-receipt.json`，刻意維持 `NO-GO`。

## 驗證摘要

- Affected：`219 passed, 1 warning`。
- Full repository final rerun：`957 passed, 2 warnings`。
- 四個 preserved CLOSED：`5 passed`。
- Readiness gate：`READY`、`canary_created=false`。
- Capacity bounded exercise：`PASS`；production capacity：`NO-GO`。
- Shell、plist、diff、scope 與 debug marker gates 皆須在 commit 前重驗。

## 未執行

沒有 production actor restore、installer install/activate、launchctl mutation、真實 queue/provider、canary、transaction、tag、push、merge。
