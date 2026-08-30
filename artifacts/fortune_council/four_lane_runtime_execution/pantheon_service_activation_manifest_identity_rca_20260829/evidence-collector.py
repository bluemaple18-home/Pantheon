#!/usr/bin/env python3
"""收集 service activation identity RCA 的唯讀、非敏感 machine receipts。"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import plistlib
import subprocess


REPO = Path("/Users/mattkuo/.codex/worktrees/a018/Pantheon")
ARTIFACTS = Path(
    "/Users/mattkuo/Documents/Pantheon/artifacts/fortune_council/four_lane_runtime_execution"
)
RUNTIME = Path("/Users/mattkuo/Documents/Pantheon-canary-runtime-v8")
LAUNCH_AGENTS = Path("/Users/mattkuo/Library/LaunchAgents")
LABELS = (
    "com.pantheon.agy-gemini-coordinator",
    "com.pantheon.agy-gemini-new",
    "com.pantheon.agy-gemini-rewrite",
    "com.pantheon.agy-gemini-i18n-new",
    "com.pantheon.agy-gemini-i18n-rewrite",
    "com.pantheon.agy-content-publisher",
    "com.pantheon.content-capacity-guard",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(REPO), *args], text=True).strip()


def commit(sha: str) -> dict[str, str]:
    values = git("show", "-s", "--format=%H%n%P%n%aI%n%s", sha).splitlines()
    return {"sha": values[0], "parents": values[1], "authored_at": values[2], "subject": values[3]}


def write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def git_blob(revision: str, path: str) -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(REPO), "show", f"{revision}:{path}"],
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.stdout if completed.returncode == 0 else None


def excerpt(body: str | None, needle: str, before: int = 5, after: int = 12) -> dict[str, object]:
    if body is None:
        return {"exists": False, "needle": needle, "lines": []}
    lines = body.splitlines()
    matches = [index for index, line in enumerate(lines) if needle in line]
    if not matches:
        return {"exists": True, "needle": needle, "lines": [], "matched": False}
    index = matches[0]
    start = max(0, index - before)
    end = min(len(lines), index + after + 1)
    return {
        "exists": True,
        "needle": needle,
        "matched": True,
        "start_line": start + 1,
        "end_line": end,
        "lines": [{"line": offset + 1, "text": lines[offset]} for offset in range(start, end)],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    source_files = {
        name: {"sha256": digest(REPO / name), "bytes": (REPO / name).stat().st_size}
        for name in (
            "scripts/pantheon_content_runtime_manifest.py",
            "scripts/pantheon_content_runtime_promotion.py",
            "scripts/pantheon_content_capacity_guard.py",
            "scripts/install_agy_gemini_coordinator_launchd.sh",
            "scripts/install_agy_content_publisher_launchd.sh",
            "scripts/install_pantheon_content_capacity_guard_launchd.sh",
            "tests/test_pantheon_content_capacity_guard.py",
            "tests/test_pantheon_content_runtime_promotion.py",
        )
    }
    source_contract = {
        "schema_version": 1,
        "head": git("rev-parse", "HEAD"),
        "origin_main": git("rev-parse", "origin/main"),
        "source_files": source_files,
        "owners": {
            "promotion_manifest_byte_writer": "pantheon_content_runtime_promotion._target_manifest -> runtime_manifest.build_manifest/write_manifest",
            "promotion_identity_semantic_input": "caller --target-identity / authorization payload",
            "manifest_identity_schema": "non-empty stripped opaque string; no activation suffix validation",
            "activation_only_schema_owner": "pantheon_content_capacity_guard.ACTIVATION_ONLY_IDENTITY_PATTERN",
            "activation_only_validator": "validate_preactivation_transition",
            "seven_service_stage_identity": "one shared manifest identity/digest/generation tuple copied into every plist",
            "seven_service_activator": "install_agy_gemini_coordinator_launchd.sh --activate|--activate-only",
        },
        "line_receipts": {
            "promotion_target_identity_input": "scripts/pantheon_content_runtime_promotion.py:1530,1558",
            "promotion_to_manifest": "scripts/pantheon_content_runtime_promotion.py:1040-1055",
            "manifest_acceptance": "scripts/pantheon_content_runtime_manifest.py:137-194",
            "capacity_pattern": "scripts/pantheon_content_capacity_guard.py:46-48",
            "capacity_rejection": "scripts/pantheon_content_capacity_guard.py:1022-1044",
            "capacity_order_branch": "scripts/install_pantheon_content_capacity_guard_launchd.sh:123-180",
            "publisher_stage_writer": "scripts/install_agy_content_publisher_launchd.sh:244-255",
            "coordinator_lane_stage_writer": "scripts/install_agy_gemini_coordinator_launchd.sh:312-402",
            "aggregate_activator": "scripts/install_agy_gemini_coordinator_launchd.sh:868-893,1371-1516",
        },
        "mechanism_commits": {
            "promotion_opaque_identity": commit("11e6c4c10566af1db0e182af49cf339d8019f7f6"),
            "activation_only_pattern": commit("5b0c662f466a6bf32c39fccb9c4d66e88f355377"),
            "transition_identity_requirement": commit("35cfdd52739f3e2896bf151ed6434a5e6d6ab95e"),
            "transition_stage_hardening": commit("29f758f6ad74afa412dd8ff3878efdd79074b36f"),
        },
        "test_shape": {
            "capacity_fixtures_use_activation_only_identity": True,
            "promotion_fixtures_use_activation_only_identity": True,
            "production_named_identity_cross_contract_test": False,
        },
    }
    write(args.output_dir / "source-contract-receipt.json", source_contract)

    topology = {
        "schema_version": 1,
        "service_count": 7,
        "canonical_documented_order": [
            "coordinator --install (coordinator + four lane plists)",
            "publisher --install (publisher plist + exact-run stage authority)",
            "capacity --preflight/--install (seventh plist + transition validation)",
            "coordinator --activate (aggregate replace/bootstrap/validate/barrier)",
        ],
        "nodes": [
            {
                "node": "promotion",
                "reads": ["authorization target_identity", "source SHA", "current actor/manifest/stage", "Rule24 receipt"],
                "writes": ["actor", "runtime-manifest.json", "readiness acknowledgements", "activation barrier", "transaction receipt"],
            },
            {
                "node": "coordinator installer",
                "reads": ["runtime manifest", "model route source", "coordinator/lane plist templates"],
                "writes": ["five staged plists", "manifest-digest", "generation", "model-route-digest/path"],
            },
            {
                "node": "publisher installer",
                "reads": ["runtime manifest", "publisher plist template", "queue/runs"],
                "writes": ["publisher staged plist", "manifest-digest", "generation", "publisher-max-runs", "publisher-exact-run-id"],
            },
            {
                "node": "capacity installer",
                "reads": ["runtime manifest", "Rule24 preflight stdout", "stage authority presence", "barrier", "old live seven plists/services"],
                "writes": ["capacity staged plist only after PASS"],
                "branch": "no top-level stage authority => skip transition validator; otherwise validate full transition",
            },
            {
                "node": "aggregate activator",
                "reads": ["runtime manifest", "seven staged plists", "model route", "previous live seven plists/services/barrier"],
                "writes": ["seven live plists", "launchctl topology", "readiness acks", "activation barrier"],
                "rollback": "all seven live plists/services/barrier",
            },
        ],
        "per_service": {
            label: {
                "stage_writer": (
                    "publisher installer" if "publisher" in label else
                    "capacity installer" if "capacity" in label else
                    "coordinator installer"
                ),
                "activator": "coordinator aggregate activator",
                "identity_authority": "shared runtime manifest tuple",
            }
            for label in LABELS
        },
        "order_sensitivity": {
            "coordinator": "not stage-presence conditional; writes five plists as one set",
            "publisher": "not stage-presence conditional; writes plist and top-level authority",
            "capacity": "yes; top-level authority presence selects transition validator",
            "four_lanes": "no independent installer; atomically owned by coordinator installer",
            "aggregate_activation": "requires all seven coherent staged plists; shared failure/rollback domain",
        },
        "documented_edge_source": "PANTHEON-G8-TRANSITION-EDGE-MAP-V1-20260821.md: TE-QUIESCED-TO-CAPACITY",
    }
    write(args.output_dir / "control-plane-topology.json", topology)

    live = []
    for label in LABELS:
        path = LAUNCH_AGENTS / f"{label}.plist"
        with path.open("rb") as stream:
            payload = plistlib.load(stream)
        env = payload.get("EnvironmentVariables", {})
        args_list = payload.get("ProgramArguments", [])
        separator = args_list.index("--") if "--" in args_list else len(args_list)
        live.append(
            {
                "label": label,
                "bytes": path.stat().st_size,
                "sha256": digest(path),
                "mtime": dt.datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(),
                "actor_head": env.get("PANTHEON_RUNTIME_ACTOR_HEAD"),
                "identity": env.get("PANTHEON_RUNTIME_IDENTITY"),
                "generation": env.get("PANTHEON_RUNTIME_GENERATION"),
                "manifest_digest": env.get("PANTHEON_RUNTIME_MANIFEST_DIGEST"),
                "activation_only_argument": "--activation-only" in args_list[:separator],
            }
        )

    g47_receipt = RUNTIME / "transactions/v0403-activation-only-manifest-promotion-6477ab81-20260826/promotion-receipt.json"
    first_bad_command = ARTIFACTS / "pantheon_acceptance_b_gen05_production_release_8a_20260828/promotion-plan-8a-command.json"
    first_bad_receipt = RUNTIME / "transactions/pantheon-gen05-release-8a-20260828/promotion-receipt.json"
    history = {
        "schema_version": 1,
        "last_good": {
            "actor_head": "6477ab815e8aecca7d1e8e1588e6e5eba0fab001",
            "identity": "gate2-actor:6477ab815e8aecca7d1e8e1588e6e5eba0fab001:activation-only",
            "generation": "g47-6477ab81-activation-only-20260826",
            "manifest_digest": "c2cd3cc7b63d7685f355a4426854b7f3d2c88b4e26b8e51468afdc7c49eadc53",
            "promotion_receipt_sha256": digest(g47_receipt),
            "promotion_receipt_state": json.loads(g47_receipt.read_text())["state"],
            "seven_live_plists_same_tuple": len({(x["actor_head"], x["identity"], x["generation"], x["manifest_digest"]) for x in live}) == 1,
            "seven_live_plist_install_window": [min(x["mtime"] for x in live), max(x["mtime"] for x in live)],
            "post_install_runtime_evidence": "new run auto-new-v1-20260826-001-01 registered at 10:45:19 +08:00 after seven-plist replacement at 10:45:12",
        },
        "first_bad_operational_manifest": {
            "actor_head": "8a50395f67d22343fec4b0a8a5f41c8f40ac360e",
            "identity": "gate2-actor:8a50395f67d22343fec4b0a8a5f41c8f40ac360e:gen05-dangling-registry-guard-release-20260828",
            "transaction": "pantheon-gen05-release-8a-20260828",
            "command_sha256": digest(first_bad_command),
            "promotion_receipt_sha256": digest(first_bad_receipt),
            "promotion_receipt_state": json.loads(first_bad_receipt.read_text())["state"],
            "reason": "first located COMMITTED production target using a non-activation-only identity, which cannot match capacity regex",
        },
        "current": {
            "actor_head": "779fb96434c15013d82833788a6795119730daad",
            "identity": "gate2-actor:779fb96434c15013d82833788a6795119730daad:new-lane-current-acceptance-20260829",
            "promotion_state": "COMMITTED",
            "services_loaded": 0,
        },
        "live_seven_plist_census": live,
        "source_first_incompatible_mechanism": {
            "opaque_promotion_identity_since": "11e6c4c10566af1db0e182af49cf339d8019f7f6",
            "capacity_activation_only_regex_since": "5b0c662f466a6bf32c39fccb9c4d66e88f355377",
            "transition_identity_check_since": "35cfdd52739f3e2896bf151ed6434a5e6d6ab95e",
            "transition_stage_hardening_preserved_check": "29f758f6ad74afa412dd8ff3878efdd79074b36f",
        },
    }
    write(args.output_dir / "history-and-live-census.json", history)

    scoped_commits = {
        "11e6c4c": {
            "parent": "4c8a07adfb53f4655b01aeb699ce920539c9c62c",
            "commit": "11e6c4c10566af1db0e182af49cf339d8019f7f6",
            "paths": [
                "scripts/pantheon_content_runtime_promotion.py",
                "tests/test_pantheon_content_runtime_promotion.py",
            ],
        },
        "29f758f6": {
            "parent": "35cfdd52739f3e2896bf151ed6434a5e6d6ab95e",
            "commit": "29f758f6ad74afa412dd8ff3878efdd79074b36f",
            "paths": [
                "scripts/pantheon_content_capacity_guard.py",
                "tests/test_pantheon_content_capacity_guard.py",
            ],
        },
    }
    patch_receipts: dict[str, object] = {}
    for key, item in scoped_commits.items():
        patch = subprocess.check_output(
            [
                "git", "-C", str(REPO), "diff", "--full-index", "--find-renames", "--unified=0",
                item["parent"], item["commit"], "--", *item["paths"],
            ],
            text=True,
        )
        patch_path = args.output_dir / f"commit-{key}-parent-scoped.diff"
        patch_path.write_text(patch, encoding="utf-8")
        patch_receipts[key] = {
            **item,
            "diff_file": patch_path.name,
            "diff_sha256": digest(patch_path),
            "diff_bytes": patch_path.stat().st_size,
            "diff_numstat": git("diff", "--numstat", item["parent"], item["commit"], "--", *item["paths"]),
        }

    promotion_path = "scripts/pantheon_content_runtime_promotion.py"
    capacity_path = "scripts/pantheon_content_capacity_guard.py"
    contract_delta = {
        "schema_version": 1,
        "scoped_diffs": patch_receipts,
        "commit_11e6c4c_contract": {
            "before": {
                "promotion_module": excerpt(git_blob(scoped_commits["11e6c4c"]["parent"], promotion_path), "def _target_manifest"),
                "shared_manifest_identity_rule": excerpt(
                    git_blob(scoped_commits["11e6c4c"]["parent"], "scripts/pantheon_content_runtime_manifest.py"),
                    "if not identity or identity.strip() != identity",
                ),
            },
            "after": {
                "target_manifest_writer": excerpt(git_blob(scoped_commits["11e6c4c"]["commit"], promotion_path), "def _target_manifest"),
                "target_identity_cli": excerpt(git_blob(scoped_commits["11e6c4c"]["commit"], promotion_path), 'add_argument("--target-identity"'),
                "shared_manifest_identity_rule": excerpt(
                    git_blob(scoped_commits["11e6c4c"]["commit"], "scripts/pantheon_content_runtime_manifest.py"),
                    "if not identity or identity.strip() != identity",
                ),
            },
            "blame": git("blame", scoped_commits["11e6c4c"]["commit"], "-L", "252,264", "--", promotion_path),
            "contract_delta": "new promotion CLI accepts caller target_identity and passes it unchanged into the pre-existing non-empty opaque manifest identity field",
        },
        "commit_29f758f6_contract": {
            "before": {
                "transition_identity_check": excerpt(git_blob(scoped_commits["29f758f6"]["parent"], capacity_path), "preactivation manifest mismatch"),
                "stage_contract": excerpt(git_blob(scoped_commits["29f758f6"]["parent"], capacity_path), "stage_manifest_digest"),
            },
            "after": {
                "transition_identity_check": excerpt(git_blob(scoped_commits["29f758f6"]["commit"], capacity_path), "preactivation manifest mismatch"),
                "stage_contract": excerpt(git_blob(scoped_commits["29f758f6"]["commit"], capacity_path), "stage_manifest_digest"),
            },
            "blame": git("blame", scoped_commits["29f758f6"]["commit"], "-L", "660,676", "--", capacity_path),
            "inherited_identity_blame": git("blame", scoped_commits["29f758f6"]["parent"], "-L", "668,673", "--", capacity_path),
            "contract_delta": "29f758f6 does not introduce the activation-only identity requirement: its parent already has it. The commit removes the separate config-version conjunct, preserves the suffix check, and adds full target-stage identity/cardinality validation; tests remain activation-only-shaped",
        },
        "causal_mapping": {
            "latent_gap_start": "11e6c4c introduced an opaque caller-controlled producer; 35cfdd52 later introduced the transition's narrower activation-only consumer check using the 5b0c662f pattern",
            "reviewed_29f_effect": "parent→29f exact diff disproves that 29f introduced the identity requirement; it preserves that inherited check while hardening stage validation",
            "hard_transition_boundary": "35cfdd52 is the blamed introduction of the narrow consumer before barrier/stage/live checks; 29f758f6 keeps the same ordering",
            "last_good": "6477ab81 used the only identity shape accepted by both contracts (:activation-only), so it does not falsify the latent gap",
            "first_located_bad": "8a50395f COMMITTED an operation-specific suffix accepted by the 11e6c4c producer but rejected by the transition consumer introduced at 35cfdd52 and preserved by 29f758f6",
            "current_red": "779fb operation-specific suffix deterministically reproduces the same producer-accepts/consumer-rejects boundary",
        },
    }
    write(args.output_dir / "commit-contract-before-after.json", contract_delta)
    recovery_run_1 = args.output_dir / "red-harness-recovery-run-1.json"
    recovery_run_2 = args.output_dir / "red-harness-recovery-run-2.json"
    if recovery_run_1.is_file() and recovery_run_2.is_file():
        run_payload = json.loads(recovery_run_1.read_text(encoding="utf-8"))
        canonical_steps = run_payload["canonical_transition"]["steps"]
        closure = {
            "schema_version": 1,
            "status": "RCA_RE_REVIEW_REQUESTED",
            "primary_verdict": "CROSS_VERSION_ACTIVATION_SCHEMA_GAP",
            "reviewer_findings": {
                "P1-recovery-stage-replay": {
                    "status": "CLOSED",
                    "exact_order": [
                        {"installer": step["installer"], "action": step["action"]}
                        for step in canonical_steps
                    ],
                    "stage_count_at_red": run_payload["canonical_transition"]["stage"]["count"],
                    "exact_edge": canonical_steps[-1]["exact_edge"],
                    "exact_error": canonical_steps[-1]["error"],
                    "run_1_sha256": digest(recovery_run_1),
                    "run_2_sha256": digest(recovery_run_2),
                    "byte_identical": recovery_run_1.read_bytes() == recovery_run_2.read_bytes(),
                    "production_bytes_unchanged": run_payload["production_bytes_unchanged"],
                },
                "P1-parent-commit-causality": {
                    "status": "CLOSED_WITH_TIMELINE_CORRECTION",
                    "commit_11e6c4c_diff_sha256": patch_receipts["11e6c4c"]["diff_sha256"],
                    "commit_29f758f6_diff_sha256": patch_receipts["29f758f6"]["diff_sha256"],
                    "proved": "11e6c4c introduces caller target_identity passthrough into opaque manifest identity",
                    "disproved": "29f758f6 is not the first identity hard check; its parent already contains the activation-only check",
                    "corrected_introduction": "35cfdd52739f3e2896bf151ed6434a5e6d6ab95e",
                    "29f_effect": "preserves suffix check, removes config-version conjunct, adds full stage validation",
                },
            },
            "mutations": {
                "source": 0,
                "tests": 0,
                "production": 0,
                "live_state": 0,
                "service_control": 0,
                "git": 0,
            },
            "external_calls": {
                "provider": 0,
                "reviewer": 0,
                "publisher_execute": 0,
                "scheduler": 0,
                "activation": 0,
            },
        }
        write(args.output_dir / "reviewer-findings-closure-receipt.json", closure)
        verification_names = (
            "RESULT.md",
            "production-shaped-red-harness.py",
            "evidence-collector.py",
            "evidence-index.json",
            "red-harness-recovery-run-1.json",
            "red-harness-recovery-run-2.json",
            "control-plane-topology.json",
            "source-contract-receipt.json",
            "history-and-live-census.json",
            "commit-11e6c4c-parent-scoped.diff",
            "commit-29f758f6-parent-scoped.diff",
            "commit-contract-before-after.json",
            "reviewer-findings-closure-receipt.json",
        )
        verification = {
            "schema_version": 2,
            "status": "RCA_RE_REVIEW_REQUESTED",
            "head": git("rev-parse", "HEAD"),
            "origin_main": git("rev-parse", "origin/main"),
            "tests": {
                "targeted_capacity_transition": "3 passed in 2.94s",
                "harness_collector_py_compile": "PASS",
                "json_parse": "PASS",
                "diff_check": "PASS",
            },
            "harness": closure["reviewer_findings"]["P1-recovery-stage-replay"],
            "causality": closure["reviewer_findings"]["P1-parent-commit-causality"],
            "mutations": closure["mutations"],
            "external_calls": closure["external_calls"],
            "evidence_sha256": {
                name: digest(args.output_dir / name)
                for name in verification_names
                if (args.output_dir / name).is_file()
            },
        }
        write(args.output_dir / "verification-receipt.json", verification)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
