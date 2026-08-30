#!/usr/bin/env python3
"""將 Phase 0 production-shape stop condition 封存為完整 BLOCKED receipt。"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path("/Users/mattkuo/Documents/Pantheon")
EVIDENCE = ROOT / "artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-FOUR-LANE-4237-FINAL-ACTIVATION-ACCEPTANCE-20260830"
COLLECTOR = EVIDENCE / "collect_phase0.py"


def load_collector():
    spec = importlib.util.spec_from_file_location("phase0_collector", COLLECTOR)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(name: str, payload: dict) -> None:
    (EVIDENCE / name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    collector = load_collector()
    before = json.loads((EVIDENCE / "protected-bytes-before.json").read_text(encoding="utf-8"))
    after = {
        "schema_version": 1,
        "snapshot_phase": "after_block",
        "queue": collector.tree(collector.QUEUE),
        "state": collector.tree(collector.STATE),
        "runtime_manifest": {
            "path": str(collector.MANIFEST),
            "sha256": collector.sha(collector.MANIFEST),
            "bytes": collector.MANIFEST.stat().st_size,
        },
        "stage": collector.tree(collector.STAGE),
        "live_plists": {
            label: (
                {"sha256": collector.sha(collector.LIVE / f"{label}.plist"), "bytes": (collector.LIVE / f"{label}.plist").stat().st_size}
                if (collector.LIVE / f"{label}.plist").is_file()
                else None
            )
            for label in collector.LABELS
        },
        "production_static": collector.tree(collector.SOURCE / "app/web/static"),
    }
    write("protected-bytes-after.json", after)
    comparable_before = dict(before)
    comparable_after = dict(after)
    comparable_before.pop("snapshot_phase", None)
    comparable_after.pop("snapshot_phase", None)
    unchanged = comparable_before == comparable_after
    red = json.loads((EVIDENCE / "phase-0-exact-stage-red.json").read_text(encoding="utf-8"))
    common = {
        "schema_version": 1,
        "status": "NOT_EXECUTED",
        "blocked_by": "REPLACEMENT_EMPTY_CONTINUATION_DIRECTORY_GUARD_MISMATCH",
        "stop_condition": "SECOND_SOURCE_SEAM_REQUIRED",
        "production_mutation": 0,
    }
    for name in (
        "phase-1-promotion-plan.json",
        "phase-1-promotion-apply.json",
        "phase-1-promotion-finalize.json",
        "phase-1-promotion-status.json",
        "phase-2-rule24-receipt.json",
        "phase-2-rule25-receipt.json",
        "phase-3-stage-receipt.json",
        "phase-3-publisher-plan.json",
        "phase-3-publisher-result.json",
        "phase-3-remote-ledger-evidence-closure.json",
        "phase-4-public-en-http.json",
        "phase-4-public-en-rendered-validation.json",
        "phase-4-carry-forward-public-recheck.json",
        "phase-5-seven-service-activation.json",
        "phase-6-four-lane-current-actor-smoke.json",
    ):
        write(name, {**common, "phase_artifact": name})
    write(
        "phase-3-stage-plan.json",
        {
            "schema_version": 1,
            "status": "PLAN_ONLY_RED_CONFIRMED",
            "blocked_by": "REPLACEMENT_EMPTY_CONTINUATION_DIRECTORY_GUARD_MISMATCH",
            "exact_red_receipt": "phase-0-exact-stage-red.json",
            "exact_red_receipt_sha256": digest(EVIDENCE / "phase-0-exact-stage-red.json"),
            "red_status": red["status"],
            "red_error": "replacement attempt lineage differs",
            "production_mutation": 0,
        },
    )
    write(
        "mutation-accounting.json",
        {
            "schema_version": 1,
            "status": "SEALED_ZERO_PRODUCTION_MUTATION",
            "production_mutation": 0,
            "provider_calls": 0,
            "writer_calls": 0,
            "reviewer_calls": 0,
            "publisher_calls": 0,
            "service_load_unload": 0,
            "commit": 0,
            "tag": 0,
            "push": 0,
            "public_requests": 0,
            "evidence_files_only": True,
            "protected_bytes_unchanged": unchanged,
            "before_sha256": digest(EVIDENCE / "protected-bytes-before.json"),
            "after_sha256": digest(EVIDENCE / "protected-bytes-after.json"),
        },
    )
    result = """# Pantheon 四線 4237 最終 Activation Acceptance 結果

## 最終狀態

`BLOCKED`

唯一 production stop condition：`SECOND_SOURCE_SEAM_REQUIRED`。

Phase 0 snapshot 與 production-shaped stage plan-only RED 均未造成 production mutation；Phase 1 promotion、Phase 2 Rule24/25、Phase 3 stage/publisher、Phase 4 public acceptance、Phase 5 service activation、Phase 6 smoke 全部未執行。

## Phase verdict

| Phase | Verdict | Mutation |
|---|---|---:|
| 0 current authority snapshot | BLOCKED_ON_PRODUCTION_SHAPE | 0 |
| 0a production-shaped stage diagnostic | RED_CONFIRMED | 0 |
| 1 fresh 4237 promotion | NOT_EXECUTED | 0 |
| 2 fresh Rule24/25 | NOT_EXECUTED | 0 |
| 3 exact EN replacement | NOT_EXECUTED | 0 |
| 4 public URL | NOT_EXECUTED | 0 |
| 5 seven services | NOT_EXECUTED | 0 |
| 6 four-lane smoke | NOT_EXECUTED | 0 |

## 唯一 blocker

真實 replacement run 有 attempts `01/02/03`、無 generations，但保留空的 `continuation/` 目錄。4237 的 `_approved_stage_terminal_owner` 以目錄存在本身判定混入 continuation authority，因此 exact stage plan-only 回傳 `replacement attempt lineage differs`。

accepted test fixture `replacement_approved_stage_fixture` 在建立 replacement shape 時先執行 `shutil.rmtree(run_dir / "continuation")`，排除了 production 真實 residue，故 455 tests PASS 沒有覆蓋此 shape。

### 根因閉包

- last-good：g75 replacement lifecycle、manual repaired candidate 與 Formal Reviewer APPROVE 均成立；stage transaction 從未在 production-shaped replacement 上成功。
- first-bad：`4237d7c282` 首次引入 replacement stage guard，並將「continuation 目錄存在」等同於 continuation authority；同 commit 的 fixture 又刪除該目錄。
- durable invariant：replacement authority 應由 exact attempts `01/02/03`、root candidate/review、queue replacement lineage決定；空且無 state/artifact 的 directory 不能單獨成為另一 lifecycle owner。
- exact RED：`phase-0-exact-stage-red.json`，return code 1、error `replacement attempt lineage differs`、protected bytes before==after、所有 business calls 0。

此 gap 需要修改既有 source guard/test fixture，符合卡片「second source seam/new Repair needed」stop condition。本卡不得刪 production residue、不得修改 code、不得繼續 promotion。

## Mutation seal

- production/content/queue/state/ledger/manifest/plist bytes：前後一致。
- provider／Writer／Reviewer／Publisher calls：0。
- service load／unload：0。
- commit／tag／push：0。
- public request：0。
- 只有本卡 evidence files 新增。

## Evidence

- `phase-0-current-authority-snapshot.json`
- `phase-0-exact-stage-red.json`
- `protected-bytes-before.json`
- `protected-bytes-after.json`
- `mutation-accounting.json`

`GO_FOUR_LANE_CURRENT_ACTOR_ACCEPTED` 不成立。
"""
    (EVIDENCE / "RESULT.md").write_text(result, encoding="utf-8")
    print(json.dumps({"status": "BLOCKED", "stop_condition": "SECOND_SOURCE_SEAM_REQUIRED", "protected_bytes_unchanged": unchanged, "production_mutation": 0}, sort_keys=True))
    return 0 if unchanged else 1


if __name__ == "__main__":
    raise SystemExit(main())
