#!/usr/bin/env python3
"""G8 production preactivation reconciliation without production mutation."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import agy_content_publisher as publisher
from scripts import pantheon_content_runtime_manifest as runtime_manifest


SCHEMA_VERSION = 1
READY_STATUS = "READY_FOR_PRODUCTION_AUTHORIZATION"
BLOCKED_STATUS = "BLOCKED"
AUTHORITY_READY = "PLANNED_FAST_FORWARD"
RUNTIME_READY = "OLD_LIVE_TO_NEW_STAGE_READY"
SELECTOR_READY = "CURRENT_EXACT_SELECTOR_READY"
MUTATION_DETECTED = "MUTATION_DETECTED"
SHA1_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SERVICE_LABELS = runtime_manifest.SERVICE_LABELS
RELEASE_STATE_CONTRACT = ROOT / "artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-G8-RELEASE-STATE-CONTRACT-V1-20260821.md"
TRANSITION_EDGE_MAP = ROOT / "artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-G8-TRANSITION-EDGE-MAP-V1-20260821.md"
RELEASE_STATE_CONTRACT_ID = "PANTHEON-G8-RELEASE-STATE-CONTRACT-V1-20260821"
TRANSITION_EDGE_MAP_ID = "PANTHEON-G8-TRANSITION-EDGE-MAP-V1-20260821"
RECONCILIATION_STATUSES = {"CONVERGED", "DIVERGED", "UNKNOWN", "AMBIGUOUS"}
IDENTITY_FIELDS = (
    "identity",
    "manifest_digest",
    "runtime_identity_digest",
    "runtime_digest",
    "config_version",
    "generation",
    "actor_root",
    "queue_root",
    "publisher_state_root",
    "log_root",
    "actor_head",
    "python_executable",
    "uv_executable",
)


class ReconciliationBlocked(RuntimeError):
    def __init__(self, code: str, reason: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason
        self.details = details or {}


def _absolute_lexical(path: Path) -> Path:
    return Path(os.path.abspath(path))


def _canonical_existing(path: Path, field: str) -> Path:
    try:
        return _absolute_lexical(path).resolve(strict=True)
    except OSError as error:
        raise ReconciliationBlocked(
            "PROTECTED_PATH_UNAVAILABLE",
            f"{field} must be canonicalizable",
            {"path": str(path)},
        ) from error


def _canonical_intended(path: Path, field: str) -> Path:
    raw = _absolute_lexical(path)
    try:
        resolved = raw.resolve(strict=False)
    except OSError as error:
        raise ReconciliationBlocked(
            "PATH_CANONICALIZATION_FAILED",
            f"{field} must be canonicalizable",
            {"path": str(path)},
        ) from error
    if raw != resolved:
        raise ReconciliationBlocked(
            "EVIDENCE_PATH_ALIAS",
            "evidence path must not use a symlink or realpath alias",
            {"path": str(raw), "canonical_path": str(resolved)},
        )
    return resolved


def _canonicalize_protected_args(args: argparse.Namespace) -> argparse.Namespace:
    args.repo_root = _canonical_existing(args.repo_root, "repo_root")
    args.actor_root = _canonical_existing(args.actor_root, "actor_root")
    args.queue_root = _canonical_existing(args.queue_root, "queue_root")
    args.state_root = _canonical_existing(args.state_root, "state_root")
    args.transaction_root = _canonical_intended(args.transaction_root, "transaction_root")
    args.live_root = _canonical_existing(args.live_root, "live_root")
    args.staged_root = _canonical_existing(args.staged_root, "staged_root")
    args.manifest = _canonical_existing(args.manifest, "manifest")
    args.release_observation = _canonical_existing(args.release_observation, "release_observation")
    args.release_state_contract = _canonical_existing(args.release_state_contract, "release_state_contract")
    args.transition_edge_map = _canonical_existing(args.transition_edge_map, "transition_edge_map")
    return args


def _is_at_or_inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _validate_evidence_path(args: argparse.Namespace) -> None:
    evidence_path = _canonical_intended(args.evidence_path, "evidence_path")
    if evidence_path.exists() and evidence_path.is_dir():
        raise ReconciliationBlocked(
            "EVIDENCE_PATH_INVALID",
            "evidence path must be a file path",
            {"evidence_path": str(evidence_path)},
        )
    git_common = _canonical_existing(_git_common_dir(args.repo_root), "git_common_dir")
    protected_roots = {
        "queue_root": args.queue_root,
        "state_root": args.state_root,
        "transaction_root": args.transaction_root,
        "live_root": args.live_root,
        "staged_root": args.staged_root,
        "git_common_dir": git_common,
    }
    for label, root in protected_roots.items():
        if _is_at_or_inside(evidence_path, root):
            raise ReconciliationBlocked(
                "EVIDENCE_PATH_PROTECTED",
                "evidence path must not be inside a protected production root",
                {"evidence_path": str(evidence_path), "protected_root": label, "protected_path": str(root)},
            )
    protected_exact = {
        "publisher_lock": args.state_root / "publisher.lock",
        "manifest": args.manifest,
    }
    for label, exact_path in protected_exact.items():
        if evidence_path == exact_path:
            raise ReconciliationBlocked(
                "EVIDENCE_PATH_PROTECTED",
                "evidence path must not target a protected production artifact",
                {"evidence_path": str(evidence_path), "protected_artifact": label, "protected_path": str(exact_path)},
            )
    args.evidence_path = evidence_path


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReconciliationBlocked("INVALID_JSON", f"{path} is unreadable") from error
    if not isinstance(payload, dict):
        raise ReconciliationBlocked("INVALID_JSON", f"{path} must contain a JSON object")
    return payload


def _frontmatter(text: str, path: Path) -> dict[str, str]:
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ReconciliationBlocked("CONTRACT_INVALID", "contract frontmatter is missing", {"path": str(path)})
    block = text[4 : text.index("\n---\n", 4)]
    fields: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields


def _markdown_tables(text: str) -> list[tuple[list[str], list[list[str]]]]:
    lines = text.splitlines()
    tables: list[tuple[list[str], list[list[str]]]] = []
    index = 0
    while index + 1 < len(lines):
        if lines[index].startswith("|") and lines[index + 1].startswith("| ---"):
            header = [cell.strip().strip("`") for cell in lines[index].strip("|").split("|")]
            rows: list[list[str]] = []
            index += 2
            while index < len(lines) and lines[index].startswith("|"):
                rows.append([cell.strip().strip("`") for cell in lines[index].strip("|").split("|")])
                index += 1
            tables.append((header, rows))
            continue
        index += 1
    return tables


def _table(tables: list[tuple[list[str], list[list[str]]]], required: tuple[str, ...], path: Path) -> tuple[list[str], list[list[str]]]:
    for header, rows in tables:
        if all(field in header for field in required):
            return header, rows
    raise ReconciliationBlocked(
        "CONTRACT_INVALID",
        "required contract table is missing",
        {"path": str(path), "expected": list(required), "actual": [header for header, _rows in tables]},
    )


def _row_dict(header: list[str], row: list[str]) -> dict[str, str]:
    return dict(zip(header, row, strict=False))


def _load_release_contracts(state_path: Path, edge_path: Path) -> dict[str, Any]:
    try:
        state_text = state_path.read_text(encoding="utf-8")
        edge_text = edge_path.read_text(encoding="utf-8")
    except OSError as error:
        raise ReconciliationBlocked("CONTRACT_UNAVAILABLE", "release contract is unreadable") from error
    state_meta = _frontmatter(state_text, state_path)
    edge_meta = _frontmatter(edge_text, edge_path)
    for meta, expected_id, path in (
        (state_meta, RELEASE_STATE_CONTRACT_ID, state_path),
        (edge_meta, TRANSITION_EDGE_MAP_ID, edge_path),
    ):
        if meta.get("id") != expected_id or meta.get("version") != "1":
            raise ReconciliationBlocked(
                "CONTRACT_IDENTITY_MISMATCH",
                "release contract identity mismatch",
                {"path": str(path), "expected": {"id": expected_id, "version": "1"}, "actual": meta},
            )
    state_tables = _markdown_tables(state_text)
    group_header, group_rows = _table(state_tables, ("service group", "labels"), state_path)
    groups: dict[str, list[str]] = {}
    for raw in group_rows:
        row = _row_dict(group_header, raw)
        groups[row["service group"]] = [value.strip().strip("`") for value in row["labels"].split("、")]
    if set(groups) != {"SVC-PUBLISHER", "SVC-CORE", "SVC-CAPACITY"} or len(groups["SVC-CORE"]) != 5:
        raise ReconciliationBlocked("CONTRACT_INVALID", "service group expansion is invalid", {"path": str(state_path), "actual": groups})
    matrix_header, matrix_rows = _table(
        state_tables,
        ("state_id", "service_group", "scope", "activation_mode", "required_receipt_set"),
        state_path,
    )
    matrix = [_row_dict(matrix_header, raw) for raw in matrix_rows]
    states = list(dict.fromkeys(row["state_id"] for row in matrix))
    if len(states) != 8 or any(state == "TRANSITIONING" for state in states):
        raise ReconciliationBlocked("CONTRACT_INVALID", "release state vocabulary is invalid", {"path": str(state_path), "actual": states})
    edge_tables = _markdown_tables(edge_text)
    edge_header, edge_rows = _table(edge_tables, ("edge_id", "from", "to", "unique mutation authority"), edge_path)
    edges = [_row_dict(edge_header, raw) for raw in edge_rows]
    if len({edge["edge_id"] for edge in edges}) != len(edges) or any(edge["from"] not in states or edge["to"] not in states for edge in edges):
        raise ReconciliationBlocked("CONTRACT_INVALID", "transition edge references are invalid", {"path": str(edge_path)})
    return {"states": states, "groups": groups, "matrix": matrix, "edges": edges}


def _expected_values(value: str) -> set[str]:
    if value.startswith("one_of(") and value.endswith(")"):
        return {item.strip() for item in value[7:-1].split(",")}
    return {value}


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _observation_normative_fields(contracts: dict[str, Any]) -> set[str]:
    fields = {"path"}
    for row in contracts["matrix"]:
        fields.update(
            field
            for field in row
            if field not in {"state_id", "service_group", "scope", "required_receipt_set"}
        )
    fields.update(
        {
            "receipt",
            "receipts",
            "receipt_path",
            "receipt_paths",
            "current_receipt",
            "current_receipts",
            "required_receipt_set",
        }
    )
    return fields


def _evidence_path(item: dict[str, Any], fallback: Path) -> str:
    path = item.get("path")
    return str(path) if path else str(fallback)


def _index_observed_services(
    services: list[Any],
    *,
    normative_fields: set[str],
    fallback_path: Path,
) -> tuple[dict[tuple[Any, Any], dict[str, Any]], list[dict[str, Any]]]:
    observed: dict[tuple[Any, Any], dict[str, Any]] = {}
    conflicts: list[dict[str, Any]] = []
    for item in (value for value in services if isinstance(value, dict)):
        key = (item.get("service"), item.get("scope"))
        existing = observed.get(key)
        if existing is None:
            observed[key] = item
            continue
        if item == existing:
            continue
        conflict_fields = sorted(
            field
            for field in normative_fields
            if (field in existing or field in item)
            and _stable_json(existing.get(field)) != _stable_json(item.get(field))
        )
        if not conflict_fields:
            conflict_fields = ["observation"]
        conflicts.append(
            {
                "service": str(key[0]),
                "scope": str(key[1]),
                "fields": conflict_fields,
                "paths": [
                    _evidence_path(existing, fallback_path),
                    _evidence_path(item, fallback_path),
                ],
            }
        )
    return observed, conflicts


def _edge_effector_action(authority: str, effector: str) -> tuple[str | None, str | None]:
    try:
        tokens = shlex.split(authority)
    except ValueError:
        return None, None
    for index, token in enumerate(tokens):
        if token == effector:
            action = tokens[index + 1] if index + 1 < len(tokens) else None
            return token, action
    return None, None


def evaluate_release_state(args: argparse.Namespace) -> dict[str, Any]:
    contracts = _load_release_contracts(args.release_state_contract, args.transition_edge_map)
    observation = _read_json(args.release_observation)
    if observation.get("schema_version") != 1 or observation.get("contract_id") != RELEASE_STATE_CONTRACT_ID or observation.get("edge_map_id") != TRANSITION_EDGE_MAP_ID:
        raise ReconciliationBlocked(
            "OBSERVATION_IDENTITY_MISMATCH",
            "release observation identity mismatch",
            {"path": str(args.release_observation), "expected": {"schema_version": 1, "contract_id": RELEASE_STATE_CONTRACT_ID, "edge_map_id": TRANSITION_EDGE_MAP_ID}, "actual": {key: observation.get(key) for key in ("schema_version", "contract_id", "edge_map_id")}},
        )
    evidence_scopes = observation.get("evidence_scopes")
    services = observation.get("services")
    if not isinstance(evidence_scopes, list) or not isinstance(services, list):
        raise ReconciliationBlocked("OBSERVATION_INVALID", "release observation fields are invalid", {"path": str(args.release_observation)})
    observed, duplicate_conflicts = _index_observed_services(
        services,
        normative_fields=_observation_normative_fields(contracts),
        fallback_path=args.release_observation,
    )
    if duplicate_conflicts:
        return {
            "reconciliation_status": "AMBIGUOUS",
            "matched_state": None,
            "divergences": [
                {
                    "service": conflict["service"],
                    "scope": conflict["scope"],
                    "path": ", ".join(conflict["paths"]),
                    "field": "duplicate_service_scope",
                    "expected": "single unambiguous current evidence",
                    "actual": conflict["fields"],
                }
                for conflict in duplicate_conflicts
            ],
            "missing": [],
            "next_edge": None,
            "effector_mapping": None,
            "invalidations": [],
            "duplicate_conflicts": duplicate_conflicts,
            "production_mutation": False,
        }
    if observation.get("state") == "TRANSITIONING" and not observation.get("explicit_transition_execution"):
        return {
            "reconciliation_status": "DIVERGED",
            "matched_state": None,
            "divergences": [{"service": "release-control-plane", "path": str(args.release_observation), "field": "state", "expected": contracts["states"], "actual": "TRANSITIONING"}],
            "missing": [],
            "next_edge": None,
            "effector_mapping": None,
            "invalidations": [],
            "production_mutation": False,
        }
    if "current" in evidence_scopes and "historical" in evidence_scopes:
        status = "AMBIGUOUS"
        matches: list[str] = []
        evaluations: dict[str, dict[str, Any]] = {}
    else:
        receipts = set(observation.get("current_receipts") or [])
        evaluations = {}
        for state in contracts["states"]:
            divergences: list[dict[str, Any]] = []
            missing: list[dict[str, Any]] = []
            required_receipts: set[str] = set()
            for row in (item for item in contracts["matrix"] if item["state_id"] == state):
                for service in contracts["groups"][row["service_group"]]:
                    item = observed.get((service, row["scope"]))
                    path = item.get("path") if item else str(args.release_observation)
                    if item is None:
                        missing.append({"service": service, "path": path, "field": "service_scope", "expected": row["scope"], "actual": None})
                        continue
                    for field, expected in row.items():
                        if field in {"state_id", "service_group", "scope", "required_receipt_set"}:
                            continue
                        actual = item.get(field)
                        if actual is None:
                            missing.append({"service": service, "path": path, "field": field, "expected": expected, "actual": None})
                        elif str(actual) not in _expected_values(expected):
                            divergences.append({"service": service, "path": path, "field": field, "expected": expected, "actual": actual})
                    required_receipts.add(row["required_receipt_set"])
            for receipt in required_receipts - {"RR-NONE"} - receipts:
                missing.append({"service": "release-control-plane", "path": str(args.release_observation), "field": "required_receipt_set", "expected": receipt, "actual": None})
            evaluations[state] = {"divergences": divergences, "missing": missing}
        matches = [state for state, result in evaluations.items() if not result["divergences"] and not result["missing"]]
        if len(matches) > 1:
            status = "AMBIGUOUS"
        elif len(matches) == 1:
            status = "CONVERGED"
        elif any(not result["divergences"] for result in evaluations.values()):
            status = "UNKNOWN"
        else:
            status = "DIVERGED"
    matched_state = matches[0] if len(matches) == 1 else None
    selected = evaluations.get(matched_state or str(observation.get("expected_state_id")), {"divergences": [], "missing": []})
    outgoing = [edge for edge in contracts["edges"] if edge["from"] == matched_state]
    desired_target = observation.get("desired_target_state")
    if desired_target:
        outgoing = [edge for edge in outgoing if edge["to"] == desired_target]
    next_edge = outgoing[0] if len(outgoing) == 1 else None
    result = {
        "reconciliation_status": status,
        "matched_state": matched_state,
        "divergences": selected["divergences"],
        "missing": selected["missing"],
        "next_edge": None if next_edge is None else {"edge_id": next_edge["edge_id"], "from": next_edge["from"], "to": next_edge["to"]},
        "effector_mapping": None if next_edge is None else next_edge["unique mutation authority"],
        "invalidations": [] if next_edge is None else [value.strip() for value in next_edge["evidence invalidated"].split(",")],
        "production_mutation": False,
    }
    if result["reconciliation_status"] not in RECONCILIATION_STATUSES:
        raise ReconciliationBlocked("CONTRACT_INVALID", "unexpected reconciliation status")
    return result


def validate_effector_edge(edge_id: str, action: str) -> dict[str, Any]:
    contracts = _load_release_contracts(RELEASE_STATE_CONTRACT, TRANSITION_EDGE_MAP)
    edge = next((item for item in contracts["edges"] if item["edge_id"] == edge_id), None)
    authority = "" if edge is None else edge["unique mutation authority"].replace("`", "")
    effector = "scripts/install_agy_gemini_coordinator_launchd.sh"
    authorized_effector, authorized_action = _edge_effector_action(authority, effector)
    if edge is None or authorized_effector != effector or authorized_action != action:
        raise ReconciliationBlocked(
            "EDGE_EFFECTOR_MISMATCH",
            "release edge does not authorize the requested effector",
            {
                "service": "com.pantheon.agy-gemini-coordinator",
                "path": str(TRANSITION_EDGE_MAP),
                "expected": {
                    "authority": authority or "known canonical edge",
                    "effector": authorized_effector,
                    "action": authorized_action,
                },
                "actual": {"edge_id": edge_id, "effector": effector, "action": action},
            },
        )
    return {
        "status": "PASS",
        "edge_id": edge_id,
        "effector": effector,
        "action": action,
        "production_mutation": False,
    }


def _read_manifest_identity(path: Path, expected_digest: str) -> dict[str, Any]:
    manifest = _read_json(path)
    if manifest.get("manifest_digest") != expected_digest:
        raise ReconciliationBlocked("MANIFEST_DIGEST_MISMATCH", "runtime manifest digest mismatch")
    return manifest


def _run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _require_sha1(value: str, field: str) -> str:
    if SHA1_PATTERN.fullmatch(value) is None:
        raise ReconciliationBlocked("INVALID_INPUT", f"{field} must be an exact git sha")
    return value


def _git_head(repo: Path) -> str:
    result = _run_git(repo, "rev-parse", "HEAD")
    if result.returncode != 0:
        raise ReconciliationBlocked("GIT_UNAVAILABLE", "repo HEAD is unavailable", {"stderr": result.stderr.strip()})
    return _require_sha1(result.stdout.strip(), "HEAD")


def _git_common_dir(repo: Path) -> Path:
    result = _run_git(repo, "rev-parse", "--git-common-dir")
    if result.returncode != 0:
        raise ReconciliationBlocked("GIT_UNAVAILABLE", "git common dir is unavailable", {"stderr": result.stderr.strip()})
    path = Path(result.stdout.strip())
    return path if path.is_absolute() else (repo / path)


def _path_digest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "digest": None, "files": 0}
    if path.is_file():
        return {
            "exists": True,
            "digest": hashlib.sha256(path.read_bytes()).hexdigest(),
            "files": 1,
        }
    digest = hashlib.sha256()
    files = 0
    for child in sorted(item for item in path.rglob("*") if item.is_file()):
        rel = child.relative_to(path).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(child.read_bytes())
        digest.update(b"\0")
        files += 1
    return {"exists": True, "digest": digest.hexdigest(), "files": files}


def _snapshot(args: argparse.Namespace) -> dict[str, Any]:
    git_common = _git_common_dir(args.repo_root)
    return {
        "queue_root": _path_digest(args.queue_root),
        "state_root": _path_digest(args.state_root),
        "transaction_root": _path_digest(args.transaction_root),
        "publisher_lock": _path_digest(args.state_root / "publisher.lock"),
        "git_refs": _path_digest(git_common / "refs"),
        "git_packed_refs": _path_digest(git_common / "packed-refs"),
        "live_root": _path_digest(args.live_root),
        "staged_root": _path_digest(args.staged_root),
        "manifest": _path_digest(args.manifest),
    }


def _changed_snapshot(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    return [name for name, before_value in before.items() if after.get(name) != before_value]


def _matches_allowlist(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def evaluate_authority(args: argparse.Namespace, manifest: dict[str, Any]) -> dict[str, Any]:
    required = _require_sha1(args.required_source, "required_source")
    origin_main = _require_sha1(args.origin_main, "origin_main")
    head = _git_head(args.repo_root)
    if head != required:
        raise ReconciliationBlocked(
            "LOCAL_HEAD_MISMATCH",
            "local HEAD is not the required source",
            {"head": head, "required_source": required},
        )
    ancestor = _run_git(args.repo_root, "merge-base", "--is-ancestor", required, origin_main)
    if ancestor.returncode != 0:
        raise ReconciliationBlocked(
            "REMOTE_DIVERGED",
            "origin main is not a descendant of the required source",
            {"required_source": required, "origin_main": origin_main},
        )
    diff = _run_git(args.repo_root, "diff", "--name-only", f"{required}..{origin_main}")
    if diff.returncode != 0:
        raise ReconciliationBlocked("GIT_DIFF_FAILED", "source authority diff is unavailable", {"stderr": diff.stderr.strip()})
    changed_paths = [line.strip() for line in diff.stdout.splitlines() if line.strip()]
    forbidden = [path for path in changed_paths if not _matches_allowlist(path, args.allow_source_drift)]
    if forbidden:
        raise ReconciliationBlocked(
            "SOURCE_DRIFT",
            "origin main contains non-allowlisted source drift",
            {"changed_paths": changed_paths, "forbidden_paths": forbidden},
        )
    actor_head = _git_head(args.actor_root)
    manifest_actor_head = str(manifest.get("actor_head") or "")
    if actor_head != origin_main or manifest_actor_head != origin_main:
        raise ReconciliationBlocked(
            "ACTOR_MANIFEST_AUTHORITY_MISMATCH",
            "actor checkout and runtime manifest must both bind to origin main",
            {
                "actor_head": actor_head,
                "manifest_actor_head": manifest_actor_head,
                "origin_main": origin_main,
            },
        )
    return {
        "status": AUTHORITY_READY,
        "required_source": required,
        "origin_main": origin_main,
        "local_head": head,
        "actor_head": actor_head,
        "allowlisted_paths": changed_paths,
    }


def _load_receipts(root: Path) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for label in SERVICE_LABELS:
        path = root / f"{label}.json"
        receipt = _read_json(path)
        if receipt.get("label") != label or receipt.get("service_label") != label:
            raise ReconciliationBlocked(
                "RUNTIME_LABEL_MISMATCH",
                "runtime receipt label mismatch",
                {"path": str(path), "label": label},
            )
        receipts.append(receipt)
    return receipts


def _identity(receipt: dict[str, Any]) -> dict[str, Any]:
    return {field: receipt.get(field) for field in IDENTITY_FIELDS if field in receipt}


def _coherent_identity(receipts: list[dict[str, Any]], code: str) -> dict[str, Any]:
    identities = [_identity(receipt) for receipt in receipts]
    if not identities:
        raise ReconciliationBlocked(code, "runtime receipts are incomplete")
    first = identities[0]
    if any(identity != first for identity in identities[1:]):
        raise ReconciliationBlocked(code, "runtime receipts are mixed", {"identities": identities})
    missing = [field for field in ("identity", "manifest_digest", "runtime_identity_digest", "runtime_digest", "generation", "actor_head") if not first.get(field)]
    if missing:
        raise ReconciliationBlocked(code, "runtime identity is incomplete", {"missing": missing})
    return first


def evaluate_runtime(args: argparse.Namespace, manifest: dict[str, Any]) -> dict[str, Any]:
    live_receipts = _load_receipts(args.live_root)
    staged_receipts = _load_receipts(args.staged_root)
    live_identity = _coherent_identity(live_receipts, "LIVE_RUNTIME_MIXED")
    runtime_manifest.validate_receipts(manifest, staged_receipts)
    staged_identity = _coherent_identity(staged_receipts, "STAGED_RUNTIME_MIXED")
    if staged_identity["actor_head"] != args.origin_main:
        raise ReconciliationBlocked(
            "STAGED_AUTHORITY_MISMATCH",
            "staged runtime does not bind to origin main",
            {"staged_actor_head": staged_identity["actor_head"], "origin_main": args.origin_main},
        )
    if live_identity == staged_identity:
        raise ReconciliationBlocked(
            "NO_PACTIVE_TRANSITION",
            "live and staged runtime identities are identical; expected old-live to new-stage transition",
        )
    exact_receipt = args.staged_root / "publisher-exact-run-id"
    staged_exact_run = exact_receipt.read_text(encoding="utf-8").strip() if exact_receipt.is_file() else ""
    if staged_exact_run != args.exact_run_id:
        raise ReconciliationBlocked(
            "STAGED_SELECTOR_MISMATCH",
            "staged publisher exact run id must match the requested selector",
            {"staged_exact_run_id": staged_exact_run, "exact_run_id": args.exact_run_id},
        )
    return {
        "status": RUNTIME_READY,
        "live_identity": live_identity,
        "staged_identity": staged_identity,
        "staged_exact_run_id": staged_exact_run,
    }


def _copy_snapshot_root(source: Path, target: Path) -> None:
    if source.exists():
        shutil.copytree(source, target)
    else:
        target.mkdir(parents=True)


def evaluate_selector(args: argparse.Namespace) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="pantheon-g8-selector-") as sandbox_name:
        sandbox = Path(sandbox_name)
        sandbox_queue = sandbox / "queue"
        sandbox_state = sandbox / "state"
        _copy_snapshot_root(args.queue_root, sandbox_queue)
        _copy_snapshot_root(args.state_root, sandbox_state)
        try:
            ready = publisher.collect_ready_runs(
                sandbox_queue,
                sandbox_state,
                limit=max(args.selector_limit, 2),
                repo_root=args.repo_root,
                exact_run_ids=[args.exact_run_id],
            )
        except publisher.PublishBlocked as error:
            raise ReconciliationBlocked(
                "SELECTOR_CARDINALITY",
                "exact selector must resolve to exactly one ready run",
                {
                    "exact_run_id": args.exact_run_id,
                    "collector_error": str(error),
                    "selector_isolation": "queue_state_snapshot",
                },
            ) from error
    if len(ready) != 1:
        raise ReconciliationBlocked(
            "SELECTOR_CARDINALITY",
            "exact selector must resolve to exactly one ready run",
            {
                "exact_run_id": args.exact_run_id,
                "count": len(ready),
                "selector_isolation": "queue_state_snapshot",
            },
        )
    state, candidate, review = ready[0]
    run_id = str(state.get("run_id") or "")
    candidate_run_id = str(candidate.get("run_id") or "")
    review_run_id = str(review.get("run_id") or "")
    if {run_id, candidate_run_id, review_run_id} != {args.exact_run_id}:
        raise ReconciliationBlocked(
            "SELECTOR_IDENTITY_DRIFT",
            "selector state, candidate, and review must bind to the exact run",
            {
                "state_run_id": run_id,
                "candidate_run_id": candidate_run_id,
                "review_run_id": review_run_id,
                "exact_run_id": args.exact_run_id,
            },
        )
    if state.get("status") != "complete" or candidate.get("mode") != "create":
        raise ReconciliationBlocked(
            "SELECTOR_NOT_READY",
            "selector run is not complete create mode",
            {"run_id": run_id, "state_status": state.get("status"), "candidate_mode": candidate.get("mode")},
        )
    return {
        "status": SELECTOR_READY,
        "exact_run_id": args.exact_run_id,
        "state_path": str(args.queue_root / "runs" / f"{args.exact_run_id}.json"),
        "selector_isolation": "queue_state_snapshot",
        "candidate_article_count": len(candidate.get("articles", [])),
    }


def reconcile(args: argparse.Namespace) -> dict[str, Any]:
    before = _snapshot(args)
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": READY_STATUS,
        "production_mutation": False,
        "card_id": args.card_id,
    }
    try:
        manifest_identity = _read_manifest_identity(args.manifest, args.expected_manifest_digest)
        result["authority"] = evaluate_authority(args, manifest_identity)
        manifest = runtime_manifest.load_manifest(args.manifest, args.expected_manifest_digest)
        result["runtime_transition"] = evaluate_runtime(args, manifest)
        result["selector"] = evaluate_selector(args)
        result["release_reconciliation"] = evaluate_release_state(args)
        result.update(result["release_reconciliation"])
        if result["reconciliation_status"] != "CONVERGED":
            result["status"] = BLOCKED_STATUS
            result["blocked_code"] = f"RELEASE_{result['reconciliation_status']}"
    except (runtime_manifest.RuntimeManifestError, publisher.PublishBlocked, ReconciliationBlocked) as error:
        code = error.code if isinstance(error, ReconciliationBlocked) else type(error).__name__
        details = error.details if isinstance(error, ReconciliationBlocked) else {}
        result.update(
            {
                "status": BLOCKED_STATUS,
                "blocked_code": code,
                "reasons": [str(error)],
                "details": details,
            }
        )
    after = _snapshot(args)
    changed = _changed_snapshot(before, after)
    result["mutation_tripwire"] = {
        "status": "PASS" if not changed else MUTATION_DETECTED,
        "changed": changed,
        "before": before,
        "after": after,
    }
    if changed:
        result.update(
            {
                "status": BLOCKED_STATUS,
                "blocked_code": MUTATION_DETECTED,
                "production_mutation": True,
                "reasons": [f"protected roots changed: {', '.join(changed)}"],
            }
        )
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--card-id", required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--actor-root", type=Path, required=True)
    parser.add_argument("--queue-root", type=Path, required=True)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--transaction-root", type=Path, required=True)
    parser.add_argument("--live-root", type=Path, required=True)
    parser.add_argument("--staged-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expected-manifest-digest", required=True)
    parser.add_argument("--required-source", required=True)
    parser.add_argument("--origin-main", required=True)
    parser.add_argument("--exact-run-id", required=True)
    parser.add_argument("--evidence-path", type=Path, required=True)
    parser.add_argument("--release-observation", type=Path, required=True)
    parser.add_argument("--release-state-contract", type=Path, default=RELEASE_STATE_CONTRACT)
    parser.add_argument("--transition-edge-map", type=Path, default=TRANSITION_EDGE_MAP)
    parser.add_argument("--allow-source-drift", action="append", default=[])
    parser.add_argument("--selector-limit", type=int, default=2)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    effective_argv = sys.argv[1:] if argv is None else argv
    if effective_argv[:1] == ["--validate-effector-edge"]:
        parser = argparse.ArgumentParser(description="驗證 canonical edge 的既有 effector mapping。")
        parser.add_argument("--validate-effector-edge", action="store_true")
        parser.add_argument("--edge-id", required=True)
        parser.add_argument("--action", required=True)
        edge_args = parser.parse_args(effective_argv)
        try:
            payload = validate_effector_edge(edge_args.edge_id, edge_args.action)
        except ReconciliationBlocked as error:
            payload = {
                "status": BLOCKED_STATUS,
                "blocked_code": error.code,
                "reasons": [error.reason],
                "details": error.details,
                "production_mutation": False,
            }
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 0 if payload["status"] == "PASS" else 1
    args = parse_args(argv)
    try:
        _canonicalize_protected_args(args)
        _validate_evidence_path(args)
    except ReconciliationBlocked as error:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "status": BLOCKED_STATUS,
            "blocked_code": error.code,
            "reasons": [error.reason],
            "details": error.details,
            "production_mutation": False,
        }
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 1
    if not args.allow_source_drift and args.required_source != args.origin_main:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "status": BLOCKED_STATUS,
            "blocked_code": "ALLOWLIST_REQUIRED",
            "reasons": ["planned fast-forward requires at least one explicit allowlist pattern"],
        }
    else:
        payload = reconcile(args)
    args.evidence_path.parent.mkdir(parents=True, exist_ok=True)
    args.evidence_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if payload.get("status") == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
