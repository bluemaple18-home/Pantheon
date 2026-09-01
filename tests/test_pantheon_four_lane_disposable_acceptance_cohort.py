from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import time
from typing import Any, Callable, Mapping
from unittest.mock import patch

import pytest

from scripts import pantheon_content_runtime_manifest as runtime_manifest
from scripts import agy_content_publisher as publisher
from scripts import agy_gemini_coordinator as coordinator
from scripts import agy_gemini_runner as runner
from scripts import agy_multilingual_pipeline as multilingual
from scripts import pantheon_four_lane_disposable_acceptance_cohort as cohort
from scripts.agy_gemini_outbox import build_external_request

NONCE = "d" * 64
GENERATION = f"acceptance-{NONCE[:32]}"


def _canonical_digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _actual_bundle_file(
    tmp_path: Path,
    *,
    lane: str,
    run_id: str,
    queue_root: Path | None = None,
    entries: list[tuple[str, bool]],
) -> Path:
    lane_queue = (queue_root or tmp_path / "queue").resolve()
    lane_queue.mkdir(parents=True, mode=0o700, exist_ok=True)
    executable = tmp_path / f"{lane}-sealed-executable.py"
    executable.write_text(
        "#!/usr/bin/env python3\n"
        "import json,sys\n"
        "sys.stdin.buffer.read()\n"
        "print(json.dumps({'ok': True}, sort_keys=True))\n",
        encoding="utf-8",
    )
    executable.chmod(0o700)
    namespace = runner._expected_namespace_for_run_id(run_id)
    raw_entries = []
    for index, (entry_id, required) in enumerate(entries):
        role = "writer" if index == 0 else "reviewer"
        request = build_external_request(
            namespace=namespace,
            role=role,
            model="gemini-test",
            prompt=f"{lane}:{entry_id}",
            response_schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {"ok": {"type": "boolean"}},
                "required": ["ok"],
            },
        )
        raw_entries.append(
            {
                "session_id": f"four-lane-{lane}",
                "entry_id": entry_id,
                "job_id": request["job_id"],
                "request_sha256": request["request_sha256"],
                "namespace": namespace,
                "lane": lane,
                "run_id": run_id,
                "role": role,
                "model": request["model"],
                "schema_sha256": request["schema_sha256"],
                "sealed_result_sha256": _canonical_digest({"ok": True}),
                "executable_path": str(executable.resolve()),
                "executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
                "required": required,
            }
        )
    body = {
        "schema_version": 1,
        "mode": runner.ACCEPTANCE_SEALED_REPLAY_BUNDLE_MODE,
        "session_id": f"four-lane-{lane}",
        "accepted_base_sha": "8" * 40,
        "actor_sha": "e" * 40,
        "generation": GENERATION,
        "queue_root": str(lane_queue),
        "lane": lane,
        "run_id": run_id,
        "namespace": namespace,
        "provider_call_budget": sum(1 for _entry_id, required in entries if required),
        "entries": raw_entries,
    }
    bundle = {**body, "bundle_digest": _canonical_digest(body)}
    bundle_path = tmp_path / f"{lane}.bundle.json"
    bundle_path.write_text(json.dumps(bundle, sort_keys=True) + "\n", encoding="utf-8")
    bundle_path.chmod(0o600)
    return bundle_path


def test_bundle_authority_required_entries_follow_actual_runner_schema(
    tmp_path: Path,
) -> None:
    (tmp_path / "queue").mkdir(mode=0o700)
    bundle = _actual_bundle_file(
        tmp_path,
        lane="new",
        run_id="exact-new-actual-schema",
        entries=[
            ("new-required-writer", True),
            ("new-optional-diagnostic", False),
            ("new-required-reviewer", True),
        ],
    )

    assert cohort._bundle_required_entries(bundle) == [
        "new-required-writer",
        "new-required-reviewer",
    ]


@pytest.fixture(autouse=True)
def _supply_external_session_plan(monkeypatch: pytest.MonkeyPatch):
    original = cohort.render_plists
    monkeypatch.setenv("PANTHEON_FORMAL_RUNTIME", "1")
    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", GENERATION)
    monkeypatch.setattr(runner, "_git_head", lambda _actor: "e" * 40)
    monkeypatch.setattr(runner, "_assert_git_ancestor", lambda *_args: None)
    monkeypatch.setattr(
        runner.formal_runtime,
        "validate_runtime_tick",
        lambda *_args, **_kwargs: {"activation_token_digest": "f" * 64},
    )

    def render_with_plan(**kwargs):
        acceptance = Path(kwargs["acceptance_root"])
        plan = acceptance / "session-plan.json"
        kwargs["manifest_path"] = acceptance / "manifest.json"
        kwargs.setdefault("session_plan_path", plan)
        kwargs.setdefault(
            "expected_session_plan_digest",
            hashlib.sha256(plan.read_bytes()).hexdigest(),
        )
        return original(**kwargs)

    monkeypatch.setattr(cohort, "render_plists", render_with_plan)
    return original


def _phase_schedule(bindings: list[dict[str, Any]]) -> list[dict[str, object]]:
    by_lane = {item["lane"]: item for item in bindings}
    schedule: list[dict[str, object]] = []

    def append_phase(phase: str, lanes: tuple[str, ...]) -> None:
        run_ids = [by_lane[lane]["run_id"] for lane in lanes]
        max_entries = max(len(by_lane[lane]["required_entries"]) for lane in lanes)
        for entry_index in range(max_entries):
            schedule.append(
                {
                    "phase": phase,
                    "action": "coordinator-cycle",
                    "lanes": list(lanes),
                    "run_ids": run_ids,
                    "round": entry_index + 1,
                }
            )
            schedule.extend(
                {
                    "phase": phase,
                    "action": "runner-process-once",
                    "lane": lane,
                    "run_id": by_lane[lane]["run_id"],
                    "entry_id": by_lane[lane]["required_entries"][entry_index],
                }
                for lane in lanes
                if entry_index < len(by_lane[lane]["required_entries"])
            )
        schedule.append(
            {
                "phase": phase,
                "action": "coordinator-cycle",
                "lanes": list(lanes),
                "run_ids": run_ids,
                "terminal": True,
            }
        )

    append_phase("source", ("new", "rewrite"))
    schedule.extend(
        {
            "phase": "materialization",
            "action": "c-b-materialize",
            "source_lane": source,
            "source_run_id": by_lane[source]["run_id"],
            "target_lane": target,
            "target_run_id": by_lane[target]["run_id"],
        }
        for source, target in (("new", "i18n-new"), ("rewrite", "i18n-rewrite"))
    )
    append_phase("translation", ("i18n-new", "i18n-rewrite"))
    schedule.extend(
        {
            "phase": "bundle-close",
            "action": "bundle-close",
            "lane": lane,
            "run_id": by_lane[lane]["run_id"],
        }
        for lane in cohort.LANES
    )
    schedule.extend(
        {
            "phase": "publisher",
            "action": "publisher-plan-only",
            "lane": lane,
            "run_id": by_lane[lane]["run_id"],
        }
        for lane in cohort.LANES
    )
    schedule.append(
        {"phase": "closeout", "action": "queue-drain", "pending": 0, "processing": 0}
    )
    return schedule


def _fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[dict[str, object], list[dict[str, Any]], Path, dict[str, Path]]:
    actor = tmp_path / "actor"
    acceptance = tmp_path / "acceptance"
    queue = acceptance / "queue"
    state = acceptance / "state"
    logs = acceptance / "logs"
    production = {
        "queue": tmp_path / "production-queue",
        "ledger": tmp_path / "production-ledger",
        "publisher": tmp_path / "production-publisher",
        "public": tmp_path / "production-public",
    }
    acceptance.mkdir(mode=0o700)
    for path in (actor, queue, state, logs, *production.values()):
        path.mkdir(mode=0o700)
    for name in ("plists", "readiness", "barriers", "locks", "evidence", "consumed"):
        (acceptance / name).mkdir(mode=0o700)
    registry_path = actor / cohort.PRODUCTION_ARTICLE_REGISTRY_RELATIVE_PATH
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text("export const ARTICLE_REGISTRY = [];\n", encoding="utf-8")
    registry_path.chmod(0o600)
    production_manifest = tmp_path / "production-runtime-manifest.json"
    production_identity = runtime_manifest.build_manifest(
        actor_root=actor,
        queue_root=production["queue"],
        publisher_state_root=production["publisher"],
        log_root=production["ledger"],
        identity="production-current",
        runtime_digest="2" * 64,
        generation="production-current",
    )
    runtime_manifest.write_manifest(production_manifest, production_identity)
    production_plists = tmp_path / "production-launch-agents"
    production_plists.mkdir(mode=0o700)
    for label in cohort.SERVICE_LABELS:
        plist = production_plists / f"{label}.plist"
        receipt = runtime_manifest.receipt_for_label(production_identity, label)
        environment = {
            "PANTHEON_RUNTIME_MANIFEST": str(production_manifest.resolve()),
            "PANTHEON_RUNTIME_MANIFEST_DIGEST": production_identity["manifest_digest"],
            "PANTHEON_RUNTIME_SERVICE_LABEL": label,
            "PANTHEON_RUNTIME_IDENTITY": receipt["identity"],
            "PANTHEON_RUNTIME_IDENTITY_DIGEST": receipt["runtime_identity_digest"],
            "PANTHEON_RUNTIME_CODE_DIGEST": receipt["runtime_digest"],
            "PANTHEON_RUNTIME_CONFIG_VERSION": receipt["config_version"],
            "PANTHEON_RUNTIME_GENERATION": receipt["generation"],
            "PANTHEON_RUNTIME_ACTOR_ROOT": receipt["actor_root"],
            "PANTHEON_RUNTIME_QUEUE_ROOT": receipt["queue_root"],
            "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT": receipt["publisher_state_root"],
            "PANTHEON_RUNTIME_LOG_ROOT": receipt["log_root"],
        }
        plist.write_bytes(
            plistlib.dumps(
                {
                    "Label": label,
                    "EnvironmentVariables": environment,
                    "ProgramArguments": [],
                    "WorkingDirectory": receipt["actor_root"],
                },
                fmt=plistlib.FMT_XML,
                sort_keys=True,
            )
        )
        plist.chmod(0o600)
    production_registry = tmp_path / "production-registry.json"
    production_registry.write_text(
        json.dumps(
            {
                "identity": "production-registry",
                "count": 0,
                "digest": hashlib.sha256(b"production-registry").hexdigest(),
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    production_registry.chmod(0o600)
    monkeypatch.setenv(
        "PANTHEON_PRODUCTION_RUNTIME_MANIFEST",
        str(production_manifest.resolve()),
    )
    monkeypatch.setenv(
        "PANTHEON_PRODUCTION_LAUNCH_PLIST_ROOT",
        str(production_plists.resolve()),
    )
    monkeypatch.setenv(
        "PANTHEON_PRODUCTION_REGISTRY_IDENTITY",
        str(production_registry.resolve()),
    )
    monkeypatch.setattr(cohort, "PRODUCTION_LAUNCH_PLIST_ROOT", production_plists.resolve())
    manifest_path = acceptance / "manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")
    manifest = {
        "manifest_digest": "a" * 64,
        "runtime_identity_digest": "b" * 64,
        "runtime_digest": "c" * 64,
        "identity": "disposable-cct",
        "config_version": "runtime-v2",
        "generation": GENERATION,
        "actor_head": "e" * 40,
        "actor_root": str(actor.resolve()),
        "queue_root": str(queue.resolve()),
        "publisher_state_root": str(state.resolve()),
        "log_root": str(logs.resolve()),
        "python_executable": str(Path(sys.executable).resolve()),
        "uv_executable": str(Path(sys.executable).resolve()),
    }
    original_load_manifest = runtime_manifest.load_manifest

    def load_manifest(path: Path, *args: Any, **kwargs: Any) -> dict[str, Any]:
        if Path(path) == manifest_path:
            return dict(manifest)
        return original_load_manifest(path, *args, **kwargs)

    monkeypatch.setattr(runtime_manifest, "load_manifest", load_manifest)
    pending_root = queue / "translation-pending-dependencies"
    pending_root.mkdir(mode=0o700)
    cb_plan_root = queue / "c-b-plans"
    cb_plan_root.mkdir(mode=0o700)
    bindings: list[dict[str, Any]] = []
    source_article_id = "article-cct-source"
    run_ids = {
        "new": "exact-new-0",
        "rewrite": "exact-rewrite-1",
    }
    run_ids["i18n-new"] = multilingual.translation_run_id(
        run_ids["new"], source_article_id, "ja"
    )
    run_ids["i18n-rewrite"] = multilingual.translation_run_id(
        run_ids["rewrite"], source_article_id, "ja"
    )
    for index, lane in enumerate(cohort.LANES):
        required_entries = [f"{lane}-writer", f"{lane}-reviewer"]
        bundle = _actual_bundle_file(
            tmp_path,
            lane=lane,
            run_id=run_ids[lane],
            queue_root=queue / "lanes" / lane,
            entries=[
                (required_entries[0], True),
                (f"{lane}-optional-diagnostic", False),
                (required_entries[1], True),
            ],
        )
        binding: dict[str, Any] = {
            "lane": lane,
            "run_id": run_ids[lane],
            "bundle": str(bundle.resolve()),
            "bundle_digest": hashlib.sha256(bundle.read_bytes()).hexdigest(),
            "actor_digest": manifest["runtime_digest"],
            "generation": manifest["generation"],
            "identity_digest": manifest["runtime_identity_digest"],
            "required_entries": required_entries,
        }
        if lane.startswith("i18n-"):
            source_run_id = run_ids["new" if lane == "i18n-new" else "rewrite"]
            plan_digest = hashlib.sha256(f"c-b-plan:{binding['run_id']}".encode()).hexdigest()
            pending_body = {
                "schema_version": 1,
                "status": "pending_source_completion",
                "owner": "scripts.agy_gemini_coordinator:create_campaign_run_adapter",
                "plan_digest": plan_digest,
                "campaign_version": "cct-test",
                "lane": lane,
                "run_id": binding["run_id"],
                "work_id": f"work-{binding['run_id']}",
                "source_article_id": source_article_id,
                "locale": "ja",
                "depends_on": [source_run_id],
                "source_completion_required": True,
            }
            pending_payload = {
                **pending_body,
                "payload_digest": coordinator._create_run_adapter_digest(pending_body),
            }
            pending = pending_root / f"{binding['run_id']}.json"
            pending.write_text(
                json.dumps(pending_payload, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            pending.chmod(0o600)
            cb_plan = cb_plan_root / f"{binding['run_id']}.json"
            cb_plan.write_text(
                json.dumps({"target_run_id": binding["run_id"], "plan_digest": plan_digest}, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            cb_plan.chmod(0o600)
            binding.update(
                {
                    "pending_receipt": str(pending.resolve()),
                    "pending_digest": hashlib.sha256(pending.read_bytes()).hexdigest(),
                    "c_b_plan_digest": plan_digest,
                }
            )
        bindings.append(binding)
    root = acceptance.resolve()
    run_records = [
        {
            "lane": item["lane"],
            "run_id": item["run_id"],
            "bundle_path": item["bundle"],
            "bundle_digest": item["bundle_digest"],
            "required_entries": item["required_entries"],
        }
        for item in bindings
    ]
    by_lane = {item["lane"]: item for item in bindings}
    plan = {
        "schema_version": 1,
        "accepted_parent_sha": cohort.ACCEPTED_PARENT_SHA,
        "session_id": f"four-lane-acceptance-{NONCE[:32]}",
        "session_nonce_digest": NONCE,
        "generation": GENERATION,
        "actor_sha": manifest["actor_head"],
        "manifest_path": str(manifest_path.resolve()),
        "manifest_digest": manifest["manifest_digest"],
        "runtime_identity_digest": manifest["runtime_identity_digest"],
        "service_labels": list(cohort.SERVICE_LABELS),
        "plist_paths": [
            str(root / "plists" / GENERATION / f"{label}.plist")
            for label in cohort.SERVICE_LABELS
        ],
        "ready_root": str(root / "readiness" / GENERATION),
        "barrier": str(root / "barriers" / f"{GENERATION}.json"),
        "lock": str(root / "locks" / f"{GENERATION}.lock"),
        "evidence_root": str(root / "evidence" / GENERATION),
        "consumed_marker": str(root / "consumed" / f"{GENERATION}.json"),
        "publisher_activation_run_id": "exact-publisher-run",
        "roots": {
            "acceptance_root": str(root),
            "actor_root": manifest["actor_root"],
            "queue_root": manifest["queue_root"],
            "publisher_state_root": manifest["publisher_state_root"],
            "log_root": manifest["log_root"],
            **{f"production_{name}": str(path.resolve()) for name, path in production.items()},
        },
        "exact_runs": run_records,
        "dependency_graph": [
            {"source_lane": "new", "translation_lane": "i18n-new"},
            {"source_lane": "rewrite", "translation_lane": "i18n-rewrite"},
        ],
        "c_b_materializations": [
            {
                "source_run_id": by_lane[source]["run_id"],
                "target_run_id": by_lane[target]["run_id"],
                "pending_receipt": by_lane[target]["pending_receipt"],
                "pending_digest": by_lane[target]["pending_digest"],
                "plan_digest": by_lane[target]["c_b_plan_digest"],
            }
            for source, target in (("new", "i18n-new"), ("rewrite", "i18n-rewrite"))
        ],
        "bundle_closeouts": run_records,
        "phase_schedule": _phase_schedule(bindings),
        "publisher_plan_only": [
            {
                "lane": item["lane"],
                "run_id": item["run_id"],
                "max_runs": 1,
                "selector_cardinality": 1,
                "dry_run": True,
                "push": False,
                "public_mutation": False,
            }
            for item in run_records
        ],
        "budgets": {
            "provider_production_calls": 0,
            "public_mutation": 0,
            "production_queue_mutation": 0,
            "production_ledger_mutation": 0,
            "production_publisher_state_mutation": 0,
            "tag_push_deploy": 0,
        },
        "teardown": {
            "initial_loaded_acceptance_labels": 0,
            "final_absent_acceptance_labels": 7,
            "allowed_residue": ["consumed_marker", "evidence_receipt"],
            "forbidden_residue": ["plists", "readiness", "barrier", "lock"],
        },
        "production_fingerprint_contract": [
            "root_identities",
            "runtime_manifest_identity",
            "production_launch_plists",
            "loaded_service_snapshot",
            "registry",
        ],
    }
    plan_path = acceptance / "session-plan.json"
    plan_path.write_text(json.dumps(plan, sort_keys=True) + "\n", encoding="utf-8")
    plan_path.chmod(0o600)
    return manifest, bindings, root, production


def _production_state(extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    state: dict[str, Any] = {
        "runtime_manifest_identity": {
            "manifest_path": "/Library/LaunchAgents/pantheon-production-runtime.json",
            "manifest_digest": "1" * 64,
            "runtime_identity_digest": "2" * 64,
            "generation": "production-current",
        },
        "production_launch_plists": [
            {
                "label": label,
                "plist_path": f"/Library/LaunchAgents/{label}.plist",
                "plist_digest": hashlib.sha256(label.encode()).hexdigest(),
            }
            for label in cohort.SERVICE_LABELS
        ],
        "loaded_service_snapshot": [],
        "registry": {
            "identity": "production-registry",
            "count": 0,
            "digest": hashlib.sha256(b"production-registry").hexdigest(),
        },
    }
    if extra:
        state.update(extra)
    return state


def _render(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[dict[str, Any], Path]:
    _manifest, bindings, acceptance, production = _fixture(tmp_path, monkeypatch)
    return (
        cohort.render_plists(
            manifest_path=acceptance / "manifest.json",
            expected_manifest_digest="a" * 64,
            acceptance_root=acceptance,
            bindings=bindings,
            publisher_run_id="exact-publisher-run",
            production_paths=production,
        ),
        acceptance,
    )


def _completed(
    command: list[str],
    returncode: int,
    payload: Mapping[str, Any] | None = None,
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    stdout = "" if payload is None else json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return subprocess.CompletedProcess(command, returncode, stdout, stderr)


def _state_path_for_run_id(queue_root: Path, run_id: str) -> Path:
    return queue_root / "runs" / f"{hashlib.sha256(run_id.encode()).hexdigest()[:24]}.json"


def _raw_process_for(
    rendered: Mapping[str, Any],
    *,
    override: Callable[[str, list[str], subprocess.CompletedProcess[str]], subprocess.CompletedProcess[str] | None] | None = None,
) -> Callable[[list[str]], subprocess.CompletedProcess[str]]:
    by_lane = {item["lane"]: item for item in rendered["bindings"]}
    cb_by_target = {
        item["target_run_id"]: item
        for item in rendered["session_plan"]["c_b_materializations"]
    }
    plist_by_label = {path.stem: path for path in rendered["plist_paths"]}
    loaded: set[str] = set()
    issued_entries: dict[str, int] = {lane: 0 for lane in by_lane}

    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {"ok": {"type": "boolean"}},
        "required": ["ok"],
    }

    def maybe(
        name: str,
        command: list[str],
        completed: subprocess.CompletedProcess[str],
    ) -> subprocess.CompletedProcess[str]:
        changed = override(name, list(command), completed) if override else None
        return changed if changed is not None else completed

    def delivered_entries(lane: str) -> list[str]:
        binding = by_lane[lane]
        bundle = runner._load_acceptance_sealed_replay_bundle(
            Path(binding["bundle"]),
            binding["bundle_digest"],
            Path(rendered["manifest"]["actor_root"]),
            Path(rendered["manifest"]["queue_root"]) / "lanes" / lane,
            lane,
            binding["run_id"],
        ).with_activation_token_digest("f" * 64)
        delivered: list[str] = []
        for entry in bundle.entries:
            state = runner._classify_bundle_entry_delivery(
                Path(rendered["manifest"]["queue_root"]) / "lanes" / lane,
                bundle,
                entry,
            )
            if state["state"] == "DELIVERED":
                delivered.append(entry.entry_id)
        return delivered

    def issue_next_request(lane: str) -> None:
        binding = by_lane[lane]
        bundle_payload = json.loads(Path(binding["bundle"]).read_text(encoding="utf-8"))
        required = [entry for entry in bundle_payload["entries"] if entry["required"]]
        entry = required[issued_entries[lane]]
        issued_entries[lane] += 1
        request = build_external_request(
            namespace=entry["namespace"],
            role=entry["role"],
            model=entry["model"],
            prompt=f"{lane}:{entry['entry_id']}",
            response_schema=schema,
        )
        assert request["job_id"] == entry["job_id"]
        outbox = Path(rendered["manifest"]["queue_root"]) / "lanes" / lane / "outbox"
        outbox.mkdir(parents=True, exist_ok=True)
        (outbox / f"{entry['job_id']}.json").write_text(
            json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )

    def transport(command: list[str]) -> subprocess.CompletedProcess[str]:
        if command[:2] == [cohort.LAUNCHCTL, "print"]:
            label = command[-1].rsplit("/", 1)[-1]
            completed = (
                _completed(command, 0, None, "")
                if label in loaded
                else _completed(command, 113, None, "not found")
            )
            if label in loaded:
                completed = subprocess.CompletedProcess(command, 0, f"{label}\n", "")
            return maybe("launchctl-print", command, completed)
        if command[:2] == [cohort.LAUNCHCTL, "bootstrap"]:
            label = Path(command[-1]).stem
            overridden = override and override("launchctl-bootstrap", command, _completed(command, 0))
            if overridden is not None:
                return overridden
            loaded.add(label)
            return _completed(command, 0)
        if command[:2] == [cohort.LAUNCHCTL, "kickstart"]:
            label = command[-1].rsplit("/", 1)[-1]
            overridden = override and override("launchctl-kickstart", command, _completed(command, 0))
            if overridden is not None:
                return overridden
            runtime_manifest.write_readiness_ack(
                Path(rendered["ready_root"]), dict(rendered["manifest"]), label
            )
            return _completed(command, 0)
        if command[:2] == [cohort.LAUNCHCTL, "bootout"]:
            label = command[-1].rsplit("/", 1)[-1]
            overridden = override and override("launchctl-bootout", command, _completed(command, 0))
            if overridden is not None:
                return overridden
            loaded.discard(label)
            return _completed(command, 0)
        if "-m" in command and "scripts.agy_gemini_runner" in command:
            lane = command[command.index("--lane") + 1]
            bundle_path = Path(command[command.index("--bundle") + 1])
            bundle_digest = command[command.index("--expected-bundle-digest") + 1]
            if "sealed-replay-bundle-process-once" in command:
                issue_next_request(lane)
                payload = runner.sealed_replay_bundle_process_once(
                    queue_root=Path(command[command.index("--queue-root") + 1]),
                    lane=lane,
                    exact_run_id=command[command.index("--exact-run-id") + 1],
                    bundle_path=bundle_path,
                    expected_bundle_digest=bundle_digest,
                )
                return maybe("runner", command, _completed(command, 0, payload))
            payload = runner.sealed_replay_bundle_close(
                queue_root=Path(command[command.index("--queue-root") + 1]),
                lane=lane,
                exact_run_id=command[command.index("--exact-run-id") + 1],
                bundle_path=bundle_path,
                expected_bundle_digest=bundle_digest,
            )
            return maybe("bundle-close", command, _completed(command, 0, payload))
        if "-m" in command and "scripts.agy_gemini_coordinator" in command and "materialize-translation-pending" in command:
            target = command[command.index("--expected-target-run-id") + 1]
            source = command[command.index("--source-run-id") + 1]
            pins = cb_by_target[target]
            pending_path = Path(pins["pending_receipt"])
            pending, _existing = coordinator._translation_pending_payload(
                json.loads(pending_path.read_text(encoding="utf-8")),
                expected_source_run_id=source,
            )
            proof = {
                "run_id": target,
                "source_run_id": source,
                "lane": pending["lane"],
                "brief_sha256": hashlib.sha256(f"brief:{target}".encode()).hexdigest(),
                "plan_digest": pins["plan_digest"],
                "pending_digest_before": pins["pending_digest"],
                "registration_identity_digest": hashlib.sha256(f"registration:{target}".encode()).hexdigest(),
            }
            terminal_basis = {**pending, "status": "materialized", "materialized": proof}
            terminal = {
                **terminal_basis,
                "materialized": {
                    **proof,
                    "pending_digest_after": coordinator._create_run_adapter_digest(terminal_basis),
                },
            }
            pending_path.write_text(
                json.dumps(terminal, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            payload = {
                "status": "materialized",
                "run_id": target,
                "source_run_id": source,
                "lane": pending["lane"],
                "pending_digest_before": pins["pending_digest"],
                "pending_digest_after": terminal["materialized"]["pending_digest_after"],
                "plan_digest": pins["plan_digest"],
                "brief_sha256": proof["brief_sha256"],
                "registration_identity_digest": proof["registration_identity_digest"],
                "queue_mutation": True,
                "public_mutation": False,
            }
            return maybe("materialize", command, _completed(command, 0, payload))
        if "-m" in command and "scripts.agy_gemini_coordinator" in command and "cycle" in command:
            run_ids = [
                command[index + 1]
                for index, token in enumerate(command[:-1])
                if token == "--exact-run-id"
            ]
            complete = 0
            for lane, binding in by_lane.items():
                if binding["run_id"] in run_ids and delivered_entries(lane) == binding["required_entries"]:
                    complete += 1
                    state_path = _state_path_for_run_id(
                        Path(rendered["manifest"]["queue_root"]),
                        binding["run_id"],
                    )
                    state_path.parent.mkdir(parents=True, exist_ok=True)
                    state_path.write_text(
                        json.dumps(
                            {
                                "schema_version": 1,
                                "run_id": binding["run_id"],
                                "lane": lane,
                                "status": "complete",
                            },
                            sort_keys=True,
                            separators=(",", ":"),
                        )
                        + "\n",
                        encoding="utf-8",
                    )
            payload = {
                "status": "ok",
                "active": 0 if complete == len(run_ids) else len(run_ids),
                "complete": complete,
                "failed": 0,
                "runner": {"status": "external_workers_only"},
                "new_matrix_sweep": None,
                "legacy_sweep": None,
                "observed_from": "raw-process-owner-state",
            }
            return maybe("coordinator", command, _completed(command, 0, payload))
        raise AssertionError(f"unexpected command: {command}")

    return transport


def _patch_publisher_plan_only(rendered: Mapping[str, Any]):
    class NamespacePlan:
        def receipt(self) -> dict[str, Any]:
            return {}

    def selected(kwargs: Mapping[str, Any]) -> str:
        run_ids = sorted(publisher._normalize_exact_run_ids(kwargs["exact_run_ids"]) or ())
        assert len(run_ids) == 1
        return run_ids[0]

    def ready_new(*_args: Any, **kwargs: Any) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]:
        return [({"run_id": selected(kwargs)}, {}, {})]

    def ready_rewrite(*_args: Any, **kwargs: Any) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]]:
        return [
            (
                {"run_id": selected(kwargs)},
                {"articles": [{"article_id": "legacy-article"}]},
                {},
                {},
            )
        ]

    def ready_translation(*_args: Any, **kwargs: Any) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]]:
        return [
            (
                {"run_id": selected(kwargs)},
                {},
                {"articles": [{"source_article_id": "source", "locale": "ja"}]},
                {},
            )
        ]

    state_root = Path(str(rendered["manifest"]["publisher_state_root"]))
    return (
        patch.object(publisher, "_validate_formal_runtime", return_value=None),
        patch.object(publisher, "_repo_lock_path", return_value=state_root / "repo.lock"),
        patch.object(
            publisher,
            "_assert_clean_origin_head",
            return_value=str(rendered["session_plan"]["actor_sha"]),
        ),
        patch.object(publisher, "plan_release_namespace", return_value=NamespacePlan()),
        patch.object(publisher, "collect_ready_runs", side_effect=ready_new),
        patch.object(publisher, "legacy_article_records", return_value=[{"id": "legacy-article"}]),
        patch.object(
            publisher,
            "summarize_legacy_rewrite_backlog",
            return_value={"status": "empty"},
        ),
        patch.object(publisher, "collect_ready_rewrite_runs", side_effect=ready_rewrite),
        patch.object(
            publisher,
            "_filter_rewrite_runs_with_current_sources",
            side_effect=lambda _repo, _state, ready, **_kwargs: ready,
        ),
        patch.object(
            publisher,
            "collect_ready_translation_runs",
            side_effect=ready_translation,
        ),
    )


def _run(
    rendered: Mapping[str, Any],
    *,
    override: Callable[[str, list[str], subprocess.CompletedProcess[str]], subprocess.CompletedProcess[str] | None] | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    publisher_patches = _patch_publisher_plan_only(rendered)
    with patch.object(
        cohort,
        "_run_process",
        side_effect=_raw_process_for(rendered, override=override),
    ), publisher_patches[0], publisher_patches[1], publisher_patches[2], publisher_patches[3], publisher_patches[4], publisher_patches[5], publisher_patches[6], publisher_patches[7], publisher_patches[8], publisher_patches[9]:
        return cohort.run_once(rendered, monotonic=monotonic)


def _legacy_callbacks_for_forged_red(rendered: Mapping[str, Any]) -> dict[str, Any]:
    """保留 RED 的攻擊形狀：caller 準備完整 receipts 但 formal run_once 不得接受。"""
    def never_called(*_args: Any, **_kwargs: Any) -> Mapping[str, Any]:
        raise AssertionError("formal run_once accepted caller receipt callback")

    return {
        "launch": never_called,
        "bootout": never_called,
        "print_service": never_called,
        "production_service_state": never_called,
        "coordinator_cycle": never_called,
        "runner_once": never_called,
        "materialize_translation": never_called,
        "bundle_close": never_called,
        "publisher_plan_only": never_called,
        "drain_counts": never_called,
    }


def test_formal_run_once_rejects_caller_supplied_owner_receipts_without_readback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rendered, _acceptance = _render(tmp_path, monkeypatch)

    with pytest.raises(TypeError, match="unexpected keyword argument|got an unexpected"):
        cohort.run_once(rendered, **_legacy_callbacks_for_forged_red(rendered))


def test_positive_fixed_schedule_reaches_one_pass_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rendered, acceptance = _render(tmp_path, monkeypatch)
    result = _run(rendered)
    assert result["status"] == "PASS"
    assert len(result["workload_receipts"]) == 25
    terminal_coordinator = [
        item
        for item in result["workload_receipts"]
        if item.get("action") == "coordinator-cycle" and item.get("terminal") is True
    ]
    assert len(terminal_coordinator) == 2
    assert all(
        item["owner_receipt"]["observed_from"] == "raw-process-owner-state"
        and item["owner_receipt"]["active"] == 0
        and item["owner_receipt"]["complete"] == len(item["run_ids"])
        for item in terminal_coordinator
    )
    assert len([item for item in result["workload_receipts"] if item.get("action") == "publisher-plan-only"]) == 4
    assert len([item for item in result["workload_receipts"] if item.get("action") == "bundle-close"]) == 4
    assert {
        item["entry_id"]
        for item in result["workload_receipts"]
        if item.get("action") == "runner-process-once"
    } == {
        "new-writer",
        "new-reviewer",
        "rewrite-writer",
        "rewrite-reviewer",
        "i18n-new-writer",
        "i18n-new-reviewer",
        "i18n-rewrite-writer",
        "i18n-rewrite-reviewer",
    }
    assert all(
        item["owner_readback"]["paths"]["ledger"] is True
        and item["owner_readback"]["paths"]["anchor"] is True
        for item in result["workload_receipts"]
        if item.get("action") == "runner-process-once"
    )
    assert all(
        item["owner_receipt"]["queue_mutation"] is True
        and item["owner_receipt"]["public_mutation"] is False
        for item in result["workload_receipts"]
        if item.get("action") == "c-b-materialize"
    )
    assert {
        item["owner"]
        for item in result["workload_receipts"]
        if item.get("action") == "publisher-plan-only"
    } == {
        "scripts.agy_content_publisher:publish_ready_runs",
        "scripts.agy_content_publisher:publish_ready_rewrite_runs",
        "scripts.agy_content_publisher:publish_ready_translation_runs",
    }
    assert all(
        item["owner_receipt"]["sealed_replay_bundle_session"][
            "activation_token_digest"
        ]
        == "f" * 64
        for item in result["workload_receipts"]
        if item.get("action") == "bundle-close"
    )
    assert result["preflight_prints"][0]["phase"] == "preflight-print"
    assert result["preflight_prints"][0]["command"][0:2] == [cohort.LAUNCHCTL, "print"]
    assert result["preflight_prints"][0]["returncode"] == 113
    assert result["launchctl_receipts"][0]["phase"] == "bootstrap"
    assert result["launchctl_receipts"][0]["kickstart"]["command"][0:2] == [
        cohort.LAUNCHCTL,
        "kickstart",
    ]
    assert result["bootouts"][0]["phase"] == "bootout"
    assert result["final_prints"][0]["phase"] == "final-print"
    assert result["before_fingerprint"] == result["after_fingerprint"]
    assert (acceptance / "consumed" / f"{GENERATION}.json").is_file()
    receipt = acceptance / "evidence" / GENERATION / "one-shot-session-receipt.json"
    assert receipt.is_file()
    assert json.loads(receipt.read_text(encoding="utf-8"))["status"] == "PASS"


def test_materialization_accepts_new_owner_receipt_with_isolated_queue_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rendered, _acceptance = _render(tmp_path, monkeypatch)
    step = next(
        item
        for item in rendered["session_plan"]["phase_schedule"]
        if item["action"] == "c-b-materialize"
    )
    pins = next(
        item
        for item in rendered["session_plan"]["c_b_materializations"]
        if item["target_run_id"] == step["target_run_id"]
    )
    pending_path = Path(str(pins["pending_receipt"]))
    pending = json.loads(pending_path.read_text(encoding="utf-8"))
    proof = {
        "run_id": step["target_run_id"],
        "source_run_id": step["source_run_id"],
        "lane": step["target_lane"],
        "brief_sha256": hashlib.sha256(b"brief").hexdigest(),
        "plan_digest": pins["plan_digest"],
        "pending_digest_before": pins["pending_digest"],
        "registration_identity_digest": hashlib.sha256(b"registration").hexdigest(),
    }
    terminal_basis = {**pending, "status": "materialized", "materialized": proof}
    terminal = {
        **terminal_basis,
        "materialized": {
            **proof,
            "pending_digest_after": coordinator._create_run_adapter_digest(terminal_basis),
        },
    }
    pending_path.write_text(
        json.dumps(terminal, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    native = {
        "status": "materialized",
        "run_id": step["target_run_id"],
        "source_run_id": step["source_run_id"],
        "lane": step["target_lane"],
        "pending_digest_before": pins["pending_digest"],
        "pending_digest_after": terminal["materialized"]["pending_digest_after"],
        "plan_digest": pins["plan_digest"],
        "brief_sha256": proof["brief_sha256"],
        "registration_identity_digest": proof["registration_identity_digest"],
        "queue_mutation": True,
        "public_mutation": False,
    }

    accepted = cohort._expect_materialization_receipt(
        {
            "owner": "scripts.agy_gemini_coordinator:materialize_translation_pending_dependency",
            "command": cohort._materializer_command(rendered["manifest"], step, pins),
            "materialize_translation_pending_dependency": native,
        },
        step,
        rendered["manifest"],
        pins,
    )

    assert accepted["owner_receipt"] == native


@pytest.mark.parametrize(
    ("lane", "owner_function", "count_field", "extra_fields"),
    [
        ("new", "publish_ready_runs", "published", {}),
        (
            "rewrite",
            "publish_ready_rewrite_runs",
            "rewritten",
            {
                "article_ids": ["legacy-article"],
                "legacy_cutoff_count": publisher.LEGACY_ARTICLE_COUNT_CUTOFF,
                "legacy_rewrite_backlog": {"status": "empty"},
            },
        ),
        (
            "i18n-new",
            "publish_ready_translation_runs",
            "translated",
            {"replacement_plans": []},
        ),
    ],
)
def test_publisher_plan_only_accepts_lane_specific_owner_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    lane: str,
    owner_function: str,
    count_field: str,
    extra_fields: dict[str, Any],
) -> None:
    rendered, _acceptance = _render(tmp_path, monkeypatch)
    step = next(
        item
        for item in rendered["session_plan"]["phase_schedule"]
        if item["action"] == "publisher-plan-only" and item["lane"] == lane
    )
    native = {
        "schema_version": publisher.SCHEMA_VERSION,
        "status": "dry-run",
        count_field: 0,
        "ready_runs": [step["run_id"]],
        "base_sha": rendered["session_plan"]["actor_sha"],
        "release_plan": {},
        **extra_fields,
    }

    accepted = cohort._expect_publisher_receipt(
        {
            "owner": f"scripts.agy_content_publisher:{owner_function}",
            "command": cohort._publisher_command(
                rendered["manifest"], str(step["run_id"]), str(step["lane"])
            ),
            owner_function: native,
        },
        step,
        rendered["manifest"],
    )

    assert accepted["owner_receipt"] == native


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda receipt: {
                **receipt,
                "owner": "scripts.agy_content_publisher:publish_ready_runs",
            },
            "publisher",
        ),
        (
            lambda receipt: {
                **receipt,
                "publish_ready_rewrite_runs": {
                    **receipt["publish_ready_rewrite_runs"],
                    "ready_runs": [],
                },
            },
            "publisher",
        ),
        (
            lambda receipt: {
                **receipt,
                "publish_ready_rewrite_runs": {
                    **receipt["publish_ready_rewrite_runs"],
                    "push": False,
                },
            },
            "publisher",
        ),
    ],
)
def test_publisher_plan_only_rejects_wrong_owner_selector_or_extra_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutate: Callable[[dict[str, Any]], dict[str, Any]],
    message: str,
) -> None:
    rendered, _acceptance = _render(tmp_path, monkeypatch)
    step = next(
        item
        for item in rendered["session_plan"]["phase_schedule"]
        if item["action"] == "publisher-plan-only" and item["lane"] == "rewrite"
    )
    native = {
        "schema_version": publisher.SCHEMA_VERSION,
        "status": "dry-run",
        "rewritten": 0,
        "ready_runs": [step["run_id"]],
        "article_ids": ["legacy-article"],
        "base_sha": rendered["session_plan"]["actor_sha"],
        "legacy_cutoff_count": publisher.LEGACY_ARTICLE_COUNT_CUTOFF,
        "legacy_rewrite_backlog": {"status": "empty"},
        "release_plan": {},
    }
    receipt = {
        "owner": "scripts.agy_content_publisher:publish_ready_rewrite_runs",
        "command": cohort._publisher_command(
            rendered["manifest"], str(step["run_id"]), str(step["lane"])
        ),
        "publish_ready_rewrite_runs": native,
    }

    with pytest.raises(cohort.AcceptanceBlocked, match=message):
        cohort._expect_publisher_receipt(mutate(receipt), step, rendered["manifest"])


def test_rendered_cohort_binds_source_only_coordinator_lane_mode_and_dry_run_publisher(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rendered, acceptance = _render(tmp_path, monkeypatch)
    coordinator_args = plistlib.loads(
        (acceptance / "plists" / GENERATION / f"{cohort.COORDINATOR}.plist").read_bytes()
    )["ProgramArguments"]
    child = coordinator_args[coordinator_args.index("--") + 1 :]
    assert "--lane-mode" in child
    assert child.count("--exact-run-id") == 2
    assert all(
        item["run_id"] not in child
        for item in rendered["bindings"]
        if str(item["lane"]).startswith("i18n-")
    )
    publisher_args = plistlib.loads(
        (acceptance / "plists" / GENERATION / f"{cohort.PUBLISHER}.plist").read_bytes()
    )["ProgramArguments"]
    assert "--activation-only" in publisher_args[: publisher_args.index("--")]
    assert "--dry-run" in publisher_args[publisher_args.index("--") + 1 :]
    assert "--push" not in publisher_args


def test_failed_projection_consumes_generation_and_blocks_same_generation_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _supply_external_session_plan
) -> None:
    _manifest, bindings, acceptance, production = _fixture(tmp_path, monkeypatch)
    original = cohort._write_plist
    calls = 0

    def fail_third(path: Path, payload: dict[str, object]) -> None:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise RuntimeError("staging failure")
        original(path, payload)

    monkeypatch.setattr(cohort, "_write_plist", fail_third)
    with pytest.raises(RuntimeError, match="staging"):
        _supply_external_session_plan(
            manifest_path=acceptance / "manifest.json",
            expected_manifest_digest="a" * 64,
            acceptance_root=acceptance,
            bindings=bindings,
            publisher_run_id="exact-publisher-run",
            production_paths=production,
            session_plan_path=acceptance / "session-plan.json",
            expected_session_plan_digest=hashlib.sha256((acceptance / "session-plan.json").read_bytes()).hexdigest(),
        )
    assert (acceptance / "consumed" / f"{GENERATION}.json").is_file()
    monkeypatch.setattr(cohort, "_write_plist", original)
    with pytest.raises(cohort.AcceptanceBlocked, match="residue|C-B external pins"):
        cohort.render_plists(
            manifest_path=acceptance / "manifest.json",
            expected_manifest_digest="a" * 64,
            acceptance_root=acceptance,
            bindings=bindings,
            publisher_run_id="exact-publisher-run",
            production_paths=production,
        )


def test_partial_readiness_consumes_generation_and_blocks_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _manifest, bindings, acceptance, production = _fixture(tmp_path, monkeypatch)
    rendered = cohort.render_plists(
        manifest_path=acceptance / "manifest.json",
        expected_manifest_digest="a" * 64,
        acceptance_root=acceptance,
        bindings=bindings,
        publisher_run_id="exact-publisher-run",
        production_paths=production,
    )

    def no_ack_for_non_control_services(
        name: str,
        command: list[str],
        completed: subprocess.CompletedProcess[str],
    ) -> subprocess.CompletedProcess[str] | None:
        if name != "launchctl-kickstart":
            return None
        label = command[-1].rsplit("/", 1)[-1]
        if label in {cohort.PUBLISHER, cohort.COORDINATOR}:
            return None
        return completed

    with pytest.raises(cohort.AcceptanceBlocked, match="readiness"):
        _run(
            rendered,
            override=no_ack_for_non_control_services,
            monotonic=iter((0.0, 2.0)).__next__,
        )
    with pytest.raises(cohort.AcceptanceBlocked, match="residue|C-B external pins"):
        cohort.render_plists(
            manifest_path=acceptance / "manifest.json",
            expected_manifest_digest="a" * 64,
            acceptance_root=acceptance,
            bindings=bindings,
            publisher_run_id="exact-publisher-run",
            production_paths=production,
        )


def test_teardown_failure_consumes_generation_and_blocks_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _manifest, bindings, acceptance, production = _fixture(tmp_path, monkeypatch)
    rendered = cohort.render_plists(
        manifest_path=acceptance / "manifest.json",
        expected_manifest_digest="a" * 64,
        acceptance_root=acceptance,
        bindings=bindings,
        publisher_run_id="exact-publisher-run",
        production_paths=production,
    )

    def fail_capacity_bootout(
        name: str,
        command: list[str],
        _completed: subprocess.CompletedProcess[str],
    ) -> subprocess.CompletedProcess[str] | None:
        if name == "launchctl-bootout" and command[-1].rsplit("/", 1)[-1] == cohort.CAPACITY:
            return subprocess.CompletedProcess(command, 1, "", "bootout failure")
        return None

    with pytest.raises(cohort.AcceptanceBlocked, match="bootout"):
        _run(rendered, override=fail_capacity_bootout)
    with pytest.raises(cohort.AcceptanceBlocked, match="residue|C-B external pins"):
        cohort.render_plists(
            manifest_path=acceptance / "manifest.json",
            expected_manifest_digest="a" * 64,
            acceptance_root=acceptance,
            bindings=bindings,
            publisher_run_id="exact-publisher-run",
            production_paths=production,
        )


def test_malformed_launch_receipt_still_boots_out_and_proves_final_absence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rendered, _acceptance = _render(tmp_path, monkeypatch)
    booted_out: list[str] = []
    final_printed: list[str] = []
    publisher_bootstrapped = False

    def malformed_loaded_identity_after_bootstrap(
        name: str,
        command: list[str],
        completed: subprocess.CompletedProcess[str],
    ) -> subprocess.CompletedProcess[str] | None:
        nonlocal publisher_bootstrapped
        if name == "launchctl-bootstrap" and Path(command[-1]).stem == cohort.PUBLISHER:
            publisher_bootstrapped = True
            return None
        if name == "launchctl-print":
            label = command[-1].rsplit("/", 1)[-1]
            if publisher_bootstrapped and label == cohort.PUBLISHER and completed.returncode == 0:
                return subprocess.CompletedProcess(command, 0, "wrong-label\n", "")
            if (
                publisher_bootstrapped
                and len(final_printed) < len(cohort.SERVICE_LABELS)
                and completed.returncode == 113
            ):
                final_printed.append(label)
        if name == "launchctl-bootout":
            booted_out.append(command[-1].rsplit("/", 1)[-1])
        return None

    with pytest.raises(cohort.AcceptanceBlocked, match="launchctl"):
        _run(rendered, override=malformed_loaded_identity_after_bootstrap)

    assert cohort.PUBLISHER in booted_out
    assert final_printed == list(cohort.SERVICE_LABELS)


def test_source_phase_rejects_i18n_exact_run_ids_before_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _manifest, bindings, acceptance, production = _fixture(tmp_path, monkeypatch)
    path = acceptance / "session-plan.json"
    plan = json.loads(path.read_text(encoding="utf-8"))
    plan["phase_schedule"][0]["run_ids"].append(bindings[2]["run_id"])
    path.write_text(json.dumps(plan, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(cohort.AcceptanceBlocked, match="schedule"):
        cohort.render_plists(
            manifest_path=acceptance / "manifest.json",
            expected_manifest_digest="a" * 64,
            acceptance_root=acceptance,
            bindings=bindings,
            publisher_run_id="exact-publisher-run",
            production_paths=production,
        )


@pytest.mark.parametrize(
    ("target", "mutate", "message"),
    [
        ("coordinator", lambda payload: {**payload, "active": 1}, "coordinator"),
        ("runner", lambda payload: {**payload, "status": "pending"}, "runner"),
        (
            "materialize",
            lambda payload: {**payload, "pending_digest_before": "0" * 64},
            "materialization",
        ),
        (
            "bundle-close",
            lambda payload: {
                **payload,
                "sealed_replay_bundle_session": {
                    **payload["sealed_replay_bundle_session"],
                    "delivered_entries": payload["sealed_replay_bundle_session"]["delivered_entries"][:1],
                },
            },
            "bundle",
        ),
    ],
)
def test_runtime_receipt_regressions_cannot_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    mutate: Callable[[dict[str, Any]], dict[str, Any]],
    message: str,
) -> None:
    rendered, _acceptance = _render(tmp_path, monkeypatch)

    def override(
        observed: str,
        command: list[str],
        completed: subprocess.CompletedProcess[str],
    ) -> subprocess.CompletedProcess[str] | None:
        if observed != target:
            return None
        payload = json.loads(completed.stdout)
        return _completed(command, completed.returncode, mutate(payload), completed.stderr)

    with pytest.raises(cohort.AcceptanceBlocked, match=message):
        _run(rendered, override=override)


def test_callback_only_readiness_ack_cannot_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rendered, _acceptance = _render(tmp_path, monkeypatch)

    def ack_without_launchctl_side_effect(
        name: str,
        _command: list[str],
        completed: subprocess.CompletedProcess[str],
    ) -> subprocess.CompletedProcess[str] | None:
        if name == "launchctl-bootstrap":
            for label in cohort.SERVICE_LABELS:
                runtime_manifest.write_readiness_ack(
                    Path(rendered["ready_root"]), dict(rendered["manifest"]), label
                )
            return completed
        return None

    with pytest.raises(cohort.AcceptanceBlocked, match="launchctl"):
        _run(rendered, override=ack_without_launchctl_side_effect)


def test_production_plist_missing_manifest_identity_rejects_before_bootstrap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rendered, _acceptance = _render(tmp_path, monkeypatch)
    plist_path = cohort.PRODUCTION_LAUNCH_PLIST_ROOT / f"{cohort.SERVICE_LABELS[0]}.plist"
    with plist_path.open("rb") as stream:
        payload = plistlib.load(stream)
    del payload["EnvironmentVariables"]["PANTHEON_RUNTIME_MANIFEST"]
    plist_path.write_bytes(plistlib.dumps(payload, fmt=plistlib.FMT_XML, sort_keys=True))
    plist_path.chmod(0o600)
    with pytest.raises(cohort.AcceptanceBlocked, match="production runtime manifest identity"):
        _run(rendered)


def test_production_service_state_derives_from_plists_not_caller_env_or_self_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _manifest, _bindings, _acceptance, _production = _fixture(tmp_path, monkeypatch)
    expected_manifest = Path(os.environ["PANTHEON_PRODUCTION_RUNTIME_MANIFEST"])
    malicious_manifest = tmp_path / "malicious-runtime-manifest.json"
    malicious_manifest.write_text(
        json.dumps(
            {
                "runtime_identity_digest": "3" * 64,
                "generation": "caller-controlled",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    forged_registry = tmp_path / "forged-registry.json"
    forged_registry.write_text(
        json.dumps(
            {"identity": "forged", "count": 999, "digest": "0" * 64},
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PANTHEON_PRODUCTION_RUNTIME_MANIFEST", str(malicious_manifest))
    monkeypatch.setenv("PANTHEON_PRODUCTION_REGISTRY_IDENTITY", str(forged_registry))
    monkeypatch.setattr(
        cohort,
        "_run_process",
        lambda command: subprocess.CompletedProcess(command, 113, "", "not found"),
    )

    state = cohort._production_service_state()

    assert state["runtime_manifest_identity"]["manifest_path"] == str(expected_manifest)
    assert state["registry"]["identity"] != "forged"
    assert state["registry"]["digest"] != "0" * 64


def test_positive_run_uses_real_publisher_owner_functions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rendered, _acceptance = _render(tmp_path, monkeypatch)
    with (
        patch.object(publisher, "publish_ready_runs", wraps=publisher.publish_ready_runs) as new_spy,
        patch.object(
            publisher,
            "publish_ready_rewrite_runs",
            wraps=publisher.publish_ready_rewrite_runs,
        ) as rewrite_spy,
        patch.object(
            publisher,
            "publish_ready_translation_runs",
            wraps=publisher.publish_ready_translation_runs,
        ) as translation_spy,
    ):
        _run(rendered)

    assert new_spy.call_count == 1
    assert rewrite_spy.call_count == 1
    assert translation_spy.call_count == 2


def test_coordinator_terminal_stdout_without_run_state_readback_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rendered, _acceptance = _render(tmp_path, monkeypatch)
    queue_root = Path(rendered["manifest"]["queue_root"])
    corrupted = False

    def corrupt_completed_run_state_after_terminal_stdout(
        name: str,
        command: list[str],
        completed: subprocess.CompletedProcess[str],
    ) -> subprocess.CompletedProcess[str] | None:
        nonlocal corrupted
        if name != "coordinator" or corrupted:
            return None
        payload = json.loads(completed.stdout)
        run_ids = [
            command[index + 1]
            for index, token in enumerate(command[:-1])
            if token == "--exact-run-id"
        ]
        if payload.get("active") != 0 or payload.get("complete") != len(run_ids):
            return None
        state_path = _state_path_for_run_id(queue_root, run_ids[0])
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["status"] = "active"
        state_path.write_text(
            json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        corrupted = True
        return completed

    with pytest.raises(cohort.AcceptanceBlocked, match="coordinator"):
        _run(rendered, override=corrupt_completed_run_state_after_terminal_stdout)


def test_plan_missing_or_drifting_fields_reject_before_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _manifest, bindings, acceptance, production = _fixture(tmp_path, monkeypatch)
    path = acceptance / "session-plan.json"
    plan = json.loads(path.read_text(encoding="utf-8"))
    del plan["dependency_graph"]
    path.write_text(json.dumps(plan, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(cohort.AcceptanceBlocked, match="plan fields"):
        cohort.render_plists(
            manifest_path=acceptance / "manifest.json",
            expected_manifest_digest="a" * 64,
            acceptance_root=acceptance,
            bindings=bindings,
            publisher_run_id="exact-publisher-run",
            production_paths=production,
        )


def test_local_child_validator_rejects_missing_lane_mode_or_i18n_source_selector(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rendered, acceptance = _render(tmp_path, monkeypatch)
    path = acceptance / "plists" / GENERATION / f"{cohort.COORDINATOR}.plist"
    payload = plistlib.loads(path.read_bytes())
    args = payload["ProgramArguments"]
    args.remove("--lane-mode")
    path.write_bytes(plistlib.dumps(payload, fmt=plistlib.FMT_XML, sort_keys=True))
    with pytest.raises(cohort.AcceptanceBlocked, match="coordinator"):
        cohort._validate_children(
            rendered["plist_paths"],
            rendered["bindings"],
            rendered["manifest"],
            "exact-publisher-run",
        )

    args.insert(args.index("cycle"), "--lane-mode")
    child_start = args.index("--") + 1
    args.insert(args.index("--external-workers-only", child_start), "--exact-run-id")
    args.insert(args.index("--external-workers-only", child_start), rendered["bindings"][2]["run_id"])
    path.write_bytes(plistlib.dumps(payload, fmt=plistlib.FMT_XML, sort_keys=True))
    with pytest.raises(cohort.AcceptanceBlocked, match="coordinator"):
        cohort._validate_children(
            rendered["plist_paths"],
            rendered["bindings"],
            rendered["manifest"],
            "exact-publisher-run",
        )
