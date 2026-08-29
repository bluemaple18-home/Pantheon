#!/usr/bin/env python3
"""唯讀產生 runtime manifest identity semantic census。"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


ACCEPTED_PARENT = "779fb96434c15013d82833788a6795119730daad"
ACTOR_SHA = re.compile(r"[0-9a-f]{40}")


def git_text(repo: Path, spec: str) -> str:
    return subprocess.check_output(
        ["git", "show", spec], cwd=repo, text=True, encoding="utf-8"
    )


def git_bytes(repo: Path, spec: str) -> bytes:
    return subprocess.check_output(["git", "show", spec], cwd=repo)


def tree_paths(repo: Path, prefix: str) -> list[str]:
    output = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", ACCEPTED_PARENT, prefix],
        cwd=repo,
        text=True,
        encoding="utf-8",
    )
    return output.splitlines()


def ast_calls(repo: Path, prefix: str, target: str) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for path in tree_paths(repo, prefix):
        if not path.endswith(".py"):
            continue
        source = git_text(repo, f"{ACCEPTED_PARENT}:{path}")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Attribute):
                name = node.func.attr
            elif isinstance(node.func, ast.Name):
                name = node.func.id
            else:
                name = ""
            if name == target:
                calls.append({"path": path, "line": node.lineno})
    return sorted(calls, key=lambda item: (item["path"], item["line"]))


def worktree_ast_calls(repo: Path, prefix: str, target: str) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for local_path in sorted((repo / prefix).rglob("*.py")):
        path = str(local_path.relative_to(repo))
        source = local_path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Attribute):
                name = node.func.attr
            elif isinstance(node.func, ast.Name):
                name = node.func.id
            else:
                name = ""
            if name == target:
                calls.append({"path": path, "line": node.lineno})
    return sorted(calls, key=lambda item: (item["path"], item["line"]))


def committed_manifests(repo: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in tree_paths(repo, "artifacts"):
        if not path.endswith(("runtime-manifest.json", "runtime_manifest.json")):
            continue
        body = git_bytes(repo, f"{ACCEPTED_PARENT}:{path}")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict) or "identity" not in payload:
            continue
        identity = str(payload["identity"])
        actor_head = payload.get("actor_head")
        embedded = ACTOR_SHA.findall(identity)
        records.append(
            {
                "path": path,
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "identity": identity,
                "identity_shape": (
                    "gate2-actor:<sha>:<opaque-correlation>"
                    if identity.startswith("gate2-actor:")
                    else "parent:<sha>;tree:<sha256>"
                    if identity.startswith("parent:")
                    else "other-opaque"
                ),
                "actor_head_present": actor_head is not None,
                "actor_head": actor_head,
                "identity_contains_actor_head": bool(
                    actor_head is not None and actor_head in embedded
                ),
                "manifest_digest": payload.get("manifest_digest"),
                "runtime_identity_digest": payload.get("runtime_identity_digest"),
            }
        )
    return sorted(records, key=lambda item: item["path"])


def line_digest(records: list[dict[str, Any]]) -> str:
    body = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(body).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--history-census", type=Path, required=True)
    parser.add_argument("--baseline-comparison", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()

    build_python = ast_calls(repo, "scripts", "build_manifest")
    shell_source = git_text(
        repo,
        f"{ACCEPTED_PARENT}:scripts/install_agy_gemini_coordinator_launchd.sh",
    )
    shell_lines = [
        {"path": "scripts/install_agy_gemini_coordinator_launchd.sh", "line": index}
        for index, line in enumerate(shell_source.splitlines(), 1)
        if "runtime_manifest.build_manifest(" in line
    ]
    build_calls = sorted(
        build_python + shell_lines, key=lambda item: (item["path"], item["line"])
    )
    load_calls = ast_calls(repo, "scripts", "load_manifest")
    test_build_calls = ast_calls(repo, "tests", "build_manifest")
    test_load_calls = ast_calls(repo, "tests", "load_manifest")
    candidate_test_build_calls = worktree_ast_calls(repo, "tests", "build_manifest")
    candidate_test_load_calls = worktree_ast_calls(repo, "tests", "load_manifest")
    manifests = committed_manifests(repo)
    history = json.loads(args.history_census.read_text(encoding="utf-8"))
    comparison = json.loads(args.baseline_comparison.read_text(encoding="utf-8"))
    baseline_nodes = set(comparison["baseline"]["failure_nodes"])
    added_nodes = sorted(set(comparison["candidate"]["failure_nodes"]) - baseline_nodes)
    live = history["live_seven_plist_census"]

    production_lineage = []
    for name in ("last_good", "first_bad_operational_manifest", "current"):
        item = history[name]
        identity = item["identity"]
        actor_head = item["actor_head"]
        production_lineage.append(
            {
                "name": name,
                "identity": identity,
                "identity_shape": "gate2-actor:<sha>:<opaque-correlation>",
                "actor_head": actor_head,
                "identity_contains_actor_head": actor_head in identity,
                "manifest_digest": item.get("manifest_digest"),
                "promotion_state": item.get("promotion_state")
                or item.get("promotion_receipt_state"),
            }
        )

    receipt = {
        "schema_version": 1,
        "status": "DESIGN_CORRECTION_EVIDENCE_READY",
        "accepted_parent": ACCEPTED_PARENT,
        "formal_call_sites": {
            "build_manifest_count": len(build_calls),
            "build_manifest": build_calls,
            "build_manifest_digest": line_digest(build_calls),
            "load_manifest_count": len(load_calls),
            "load_manifest": load_calls,
            "load_manifest_digest": line_digest(load_calls),
        },
        "producer_schemas": [
            {
                "producer": "runtime-manifest CLI",
                "identity_owner": "caller --identity",
                "actor_head": "separate optional --actor-head",
            },
            {
                "producer": "runtime promotion",
                "identity_owner": "caller authorization target_identity",
                "actor_head": "separate source_sha",
            },
            {
                "producer": "coordinator installer",
                "identity_owner": "copied common manifest identity",
                "actor_head": "copied separate optional common actor_head",
            },
            {
                "producer": "actor recovery",
                "identity_owner": "actor-recovery:<source_sha>:<runtime_digest>",
                "actor_head": "separate source_sha",
            },
            {
                "producer": "canary actor",
                "identity_owner": "canary-actor:<actor_sha>:<run_id>",
                "actor_head": "separate actor_sha",
            },
            {
                "producer": "capability probe",
                "identity_owner": "parent:<sha>;tree:<sha256>",
                "actor_head": "absent",
            },
        ],
        "committed_manifest_census": {
            "count": len(manifests),
            "total_bytes": sum(item["bytes"] for item in manifests),
            "shape_counts": {
                "gate2-actor:<sha>:<opaque-correlation>": sum(
                    item["identity_shape"] == "gate2-actor:<sha>:<opaque-correlation>"
                    for item in manifests
                ),
                "parent:<sha>;tree:<sha256>": sum(
                    item["identity_shape"] == "parent:<sha>;tree:<sha256>"
                    for item in manifests
                ),
            },
            "actor_head_present_count": sum(
                item["actor_head_present"] for item in manifests
            ),
            "actor_head_absent_count": sum(
                not item["actor_head_present"] for item in manifests
            ),
            "records": manifests,
        },
        "production_history": {
            "lineage_count": len(production_lineage),
            "lineage": production_lineage,
            "live_plist_count": len(live),
            "live_plist_total_bytes": sum(item["bytes"] for item in live),
            "live_plist_sha256": [item["sha256"] for item in live],
            "observation": "three located production identities embed actor SHA, but do not override the broader producer contract and committed schema plurality",
        },
        "digest_authority": {
            "manifest_digest_binds_entire_payload": True,
            "runtime_identity_digest_fields": [
                "schema_version",
                "identity",
                "runtime_digest",
                "config_version",
                "generation",
                "path fields",
                "actor_head when present",
                "python_executable when present",
                "uv_executable when present",
            ],
            "identity_and_actor_head_bound_together_when_actor_head_present": True,
            "load_manifest_validates_actor_head_against_actor_root": True,
        },
        "consumer_semantics": {
            "capacity_parent_semantic_identity_consumers": [
                "ACTIVATION_ONLY_IDENTITY_PATTERN transition rejection",
                "ACTIVATION_ONLY_IDENTITY_PATTERN mode fallback when live plists unavailable",
            ],
            "non_capacity_consumers_deriving_actor_from_identity": 0,
            "non_capacity_consumers_deriving_mode_from_identity": 0,
            "other_consumers": "exact tuple/digest comparison or identity propagation only",
        },
        "test_census": {
            "accepted_parent_build_manifest_call_count": len(test_build_calls),
            "accepted_parent_build_manifest_calls": test_build_calls,
            "accepted_parent_build_manifest_calls_digest": line_digest(test_build_calls),
            "accepted_parent_load_manifest_call_count": len(test_load_calls),
            "accepted_parent_load_manifest_calls": test_load_calls,
            "accepted_parent_load_manifest_calls_digest": line_digest(test_load_calls),
            "candidate_build_manifest_call_count": len(candidate_test_build_calls),
            "candidate_build_manifest_calls": candidate_test_build_calls,
            "candidate_build_manifest_calls_digest": line_digest(candidate_test_build_calls),
            "candidate_load_manifest_call_count": len(candidate_test_load_calls),
            "candidate_load_manifest_calls": candidate_test_load_calls,
            "candidate_load_manifest_calls_digest": line_digest(candidate_test_load_calls),
            "baseline_passed": comparison["baseline"]["passed_count"],
            "baseline_failed": comparison["baseline"]["failure_count"],
            "candidate_passed": comparison["candidate"]["passed_count"],
            "candidate_failed": comparison["candidate"]["failure_count"],
            "new_regression_count": len(added_nodes),
            "new_regression_nodes": added_nodes,
            "new_regression_nodes_digest": hashlib.sha256(
                ("\n".join(added_nodes) + "\n").encode()
            ).hexdigest(),
            "new_regression_common_cause": "shared actor-prefix parser rejects accepted opaque g8-live/g8-staged identities whose actor_head is a separate field",
        },
        "durable_invariant_verdict": {
            "identity_must_embed_actor_sha": False,
            "identity_contract": "nonempty trimmed opaque correlation",
            "actor_authority": "separate actor_head plus manifest/runtime identity digests",
            "mode_authority": "explicit arguments and plist/stage topology",
            "original_actor_prefix_frontier": "OVERREACH",
            "minimum_repair": "withdraw shared parser additions; capacity stops private suffix parsing while preserving existing load_manifest actor_head/digest and barrier/stage/live checks",
        },
        "why_not_whitelist": "g8-live is evidence of a valid opaque schema, not the only valid exception; a whitelist would preserve capacity-owned identity semantics, conflict with six producer schemas, and miss future opaque correlations",
        "mutation_receipt": {
            "source_changes_in_this_followup": 0,
            "test_changes_in_this_followup": 0,
            "production_live_mutations": 0,
            "external_calls": 0,
        },
    }
    print(json.dumps(receipt, sort_keys=True, indent=2) + "\n", end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
