#!/usr/bin/env python3
"""封存 complete-unpublished replacement promotion identity blocker。"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path("/Users/mattkuo/Documents/Pantheon")
EVIDENCE = ROOT / "artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-4237-FINAL-ACTIVATION-ACCEPTANCE-20260830"
RUNTIME = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8")
RUN_ID = "auto-i18n-en-aa637e1bf05d3ad21429-replacement-01"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, payload: dict) -> None:
    (EVIDENCE / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def collector_module():
    path = EVIDENCE / "collect_phase0.py"
    spec = importlib.util.spec_from_file_location("phase0_collector", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    collector = collector_module()
    before = json.loads((EVIDENCE / "protected-bytes-before.json").read_text(encoding="utf-8"))
    after = {
        "schema_version": 1,
        "snapshot_phase": "after_phase1_plan_block",
        "queue": collector.tree(collector.QUEUE),
        "state": collector.tree(collector.STATE),
        "runtime_manifest": {"path": str(collector.MANIFEST), "sha256": collector.sha(collector.MANIFEST), "bytes": collector.MANIFEST.stat().st_size},
        "stage": collector.tree(collector.STAGE),
        "live_plists": {
            label: ({"sha256": collector.sha(collector.LIVE / f"{label}.plist"), "bytes": (collector.LIVE / f"{label}.plist").stat().st_size} if (collector.LIVE / f"{label}.plist").is_file() else None)
            for label in collector.LABELS
        },
        "production_static": collector.tree(collector.SOURCE / "app/web/static"),
    }
    write("protected-bytes-after.json", after)
    left = dict(before); right = dict(after)
    left.pop("snapshot_phase", None); right.pop("snapshot_phase", None)
    unchanged = left == right
    plan = json.loads((EVIDENCE / "phase-1-promotion-plan.json").read_text(encoding="utf-8"))
    registry_matches = []
    for path in sorted((RUNTIME / "queue/runs").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("run_id") == RUN_ID:
            registry_matches.append({"path": str(path), "sha256": sha(path), "payload": payload})
    ledger_path = RUNTIME / "state/ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger_matches = [entry for entry in ledger.get("translation_published_runs", []) if isinstance(entry, dict) and entry.get("run_id") == RUN_ID]
    brief = RUNTIME / "queue/translation-runs" / RUN_ID / "brief.json"
    blocker = {
        "schema_version": 1,
        "status": "BLOCKED",
        "stop_condition": "SECOND_SOURCE_SEAM_REQUIRED",
        "error": plan.get("result", {}).get("error"),
        "target_sha": "54ad8654675dbf729367a25a5093a52b379b2538",
        "last_good": {
            "promotion_generation": "g75-e01d56e3-legacy-replacement-brief-20260830",
            "preserved_run_count": 136,
            "state": "COMMITTED",
            "fact": "g75 promotion completed before the replacement run was added"
        },
        "first_bad_state": {
            "formation": "g75 replacement lifecycle terminalized after three Reviewer REJECT attempts",
            "run_id": RUN_ID,
            "registry_matches": registry_matches,
            "brief_sha256": sha(brief),
            "identity_envelope_present": bool(registry_matches and registry_matches[0]["payload"].get("identity_envelope") is not None),
            "publisher_ledger_matches": ledger_matches,
            "publisher_ledger_sha256": sha(ledger_path),
        },
        "durable_invariant": "A complete but unpublished translation replacement must have one promotion-preservable authoritative identity source without being forged as published, failed, or active.",
        "promotion_contract_observed": {
            "complete_with_ledger": "accepted",
            "failed_without_envelope": "brief reconstruction accepted",
            "complete_without_ledger_without_envelope": "rejected",
        },
        "exact_red": {
            "receipt": "phase-1-promotion-plan.json",
            "receipt_sha256": sha(EVIDENCE / "phase-1-promotion-plan.json"),
            "returncode": plan.get("returncode"),
            "result": plan.get("result"),
        },
        "production_mutation": 0,
        "protected_bytes_unchanged": unchanged,
    }
    write("phase-1-promotion-blocker-analysis.json", blocker)
    common = {
        "schema_version": 1,
        "status": "NOT_EXECUTED",
        "blocked_by": "COMPLETE_UNPUBLISHED_REPLACEMENT_PROMOTION_IDENTITY_GAP",
        "stop_condition": "SECOND_SOURCE_SEAM_REQUIRED",
        "production_mutation": 0,
    }
    for name in (
        "phase-1-promotion-apply.json", "phase-1-promotion-finalize.json", "phase-1-promotion-status.json",
        "phase-2-rule24-receipt.json", "phase-2-rule25-receipt.json", "phase-3-stage-receipt.json",
        "phase-3-publisher-plan.json", "phase-3-publisher-result.json", "phase-3-remote-ledger-evidence-closure.json",
        "phase-4-public-en-http.json", "phase-4-public-en-rendered-validation.json", "phase-4-carry-forward-public-recheck.json",
        "phase-5-seven-service-activation.json", "phase-6-four-lane-current-actor-smoke.json",
    ):
        write(name, {**common, "phase_artifact": name})
    green = json.loads((EVIDENCE / "phase-0-exact-stage-green.json").read_text(encoding="utf-8"))
    write("phase-3-stage-plan.json", {
        "schema_version": 1,
        "status": "PRE_PROMOTION_PLAN_ONLY_GREEN_BUT_NOT_AUTHORIZED_TO_EXECUTE_WITHOUT_PROMOTION",
        "green_receipt": "phase-0-exact-stage-green.json",
        "green_receipt_sha256": sha(EVIDENCE / "phase-0-exact-stage-green.json"),
        "plan_digest": (json.loads(green.get("stdout") or "{}") or {}).get("plan_digest"),
        "production_mutation": 0,
    })
    write("mutation-accounting.json", {
        "schema_version": 1,
        "status": "SEALED_ZERO_PRODUCTION_MUTATION",
        "production_mutation": 0,
        "provider_calls": 0, "writer_calls": 0, "reviewer_calls": 0, "publisher_calls": 0,
        "service_load_unload": 0, "commit": 0, "tag": 0, "push": 0, "public_requests": 0,
        "promotion_plan_calls": 1, "promotion_apply_calls": 0,
        "protected_bytes_unchanged": unchanged,
        "evidence_files_only": True,
    })
    result = """# Pantheon 四線 54ad 最終 Activation Acceptance 結果

## 最終狀態

`BLOCKED`

唯一 stop condition：`SECOND_SOURCE_SEAM_REQUIRED`。

Owner 已授權同一卡 base supersession `4237d7c282` → `54ad865467`。Empty-continuation Repair review `GO`；production-shaped exact stage plan-only 已由 RED 轉為 GREEN，bytes與calls皆為0。

Fresh g76 promotion 在正式 `plan-only` fail closed：`preserved run identity envelope is missing or invalid`。未執行 apply/finalize，live actor仍為 e01/g75。

## 根因閉包

- last-good：g75 promotion `COMMITTED/PASS`，當時 preserved run count為136；replacement run尚未建立。
- first-bad state：g75 replacement經三次 Reviewer REJECT後形成第137筆 `status=complete` registry；該 record沒有 `identity_envelope`，也因尚未發布而沒有 `translation_published_runs` ledger entry。
- durable invariant：`complete + unpublished` translation replacement仍必須有唯一、可由promotion正式採信的identity source；不得偽造成published、failed或active，也不得從preserve allowlist排除。
- exact RED：`phase-1-promotion-plan.json`，returncode 1、NO-GO error如上，production/protected bytes mutation 0。

Promotion目前只接受 complete+publisher-ledger、failed+brief reconstruction或current identity envelope；本 shape不屬任何合法分支。繼續需要新增/修正promotion lifecycle seam，符合原卡second-seam stop condition。本卡不得改registry、補假ledger、刪run或開Repair後直接續跑。

## Phase verdict

| Phase | Verdict | Mutation |
|---|---|---:|
| 0 54ad authority snapshot | PASS | 0 |
| 0a production-shaped stage plan | GREEN_CONFIRMED | 0 |
| 1 fresh g76 promotion plan | NO-GO | 0 |
| 1 apply/finalize | NOT_EXECUTED | 0 |
| 2 Rule24/25 | NOT_EXECUTED | 0 |
| 3 stage/publisher | NOT_EXECUTED | 0 |
| 4 public URL | NOT_EXECUTED | 0 |
| 5 seven services | NOT_EXECUTED | 0 |
| 6 four-lane smoke | NOT_EXECUTED | 0 |

## Mutation seal

Production/content/queue/state/ledger/manifest/plist bytes前後一致。Provider、Writer、Reviewer、Publisher、service load/unload、commit、tag、push與public request全為0。只有本卡evidence新增。

`GO_FOUR_LANE_CURRENT_ACTOR_ACCEPTED` 不成立。
"""
    (EVIDENCE / "RESULT.md").write_text(result, encoding="utf-8")
    print(json.dumps({"status": "BLOCKED", "stop_condition": "SECOND_SOURCE_SEAM_REQUIRED", "protected_bytes_unchanged": unchanged, "production_mutation": 0}, sort_keys=True))
    return 0 if unchanged and blocker["error"] == "preserved run identity envelope is missing or invalid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
