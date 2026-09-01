from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import plistlib
import sys
from typing import Any, Callable, Mapping
from unittest.mock import patch

import pytest

from scripts import pantheon_content_runtime_manifest as runtime_manifest
from scripts import agy_content_publisher as publisher
from scripts import agy_gemini_coordinator as coordinator
from scripts import agy_gemini_runner as runner
from scripts import agy_multilingual_pipeline as multilingual
from scripts import pantheon_four_lane_disposable_acceptance_cohort as cohort

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
    executable = tmp_path / f"{lane}-sealed-executable.py"
    executable.write_text("# deterministic sealed executable\n", encoding="utf-8")
    executable.chmod(0o600)
    namespace = runner._expected_namespace_for_run_id(run_id)
    raw_entries = []
    for index, (entry_id, required) in enumerate(entries):
        raw_entries.append(
            {
                "session_id": f"four-lane-{lane}",
                "entry_id": entry_id,
                "job_id": hashlib.sha256(f"{lane}:{entry_id}:job".encode()).hexdigest()[:40],
                "request_sha256": hashlib.sha256(
                    f"{lane}:{entry_id}:request".encode()
                ).hexdigest(),
                "namespace": namespace,
                "lane": lane,
                "run_id": run_id,
                "role": "writer" if index == 0 else "reviewer",
                "model": "gemini-test",
                "schema_sha256": hashlib.sha256(
                    f"{lane}:{entry_id}:schema".encode()
                ).hexdigest(),
                "sealed_result_sha256": hashlib.sha256(
                    f"{lane}:{entry_id}:result".encode()
                ).hexdigest(),
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
        "queue_root": str((queue_root or tmp_path / "queue").resolve()),
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
    monkeypatch.setattr(runtime_manifest, "load_manifest", lambda *_args: dict(manifest))
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


def _callbacks(
    rendered: Mapping[str, Any],
    *,
    override: Callable[[str, dict[str, Any], Mapping[str, Any] | None], dict[str, Any] | None] | None = None,
) -> dict[str, Any]:
    by_lane = {item["lane"]: item for item in rendered["bindings"]}
    cb_by_target = {
        item["target_run_id"]: item
        for item in rendered["session_plan"]["c_b_materializations"]
    }
    plist_by_label = {path.stem: path for path in rendered["plist_paths"]}
    loaded_bundles = {
        lane: runner._load_acceptance_sealed_replay_bundle(
            Path(binding["bundle"]),
            binding["bundle_digest"],
            Path(rendered["manifest"]["actor_root"]),
            Path(rendered["manifest"]["queue_root"]) / "lanes" / lane,
            lane,
            binding["run_id"],
        )
        for lane, binding in by_lane.items()
    }
    delivered_entries: dict[str, list[str]] = {lane: [] for lane in by_lane}
    materialized_targets: set[str] = set()
    print_counts: dict[str, int] = {}

    def maybe(
        name: str, receipt: dict[str, Any], step: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        changed = override(name, dict(receipt), step) if override else None
        return changed if changed is not None else receipt

    def launch(label: str, path: Path) -> Mapping[str, Any]:
        runtime_manifest.write_readiness_ack(
            Path(rendered["ready_root"]), dict(rendered["manifest"]), label
        )
        return maybe(
            "launch",
            cohort._launch_expectation(label, path, rendered["manifest"]),
            {"label": label},
        )

    def bootout(label: str) -> Mapping[str, Any]:
        return maybe(
            "bootout",
            cohort._bootout_expectation(label, plist_by_label[label], rendered["manifest"]),
            {"label": label},
        )

    def print_service(label: str) -> Mapping[str, Any]:
        print_counts[label] = print_counts.get(label, 0) + 1
        phase = "preflight-print" if print_counts[label] == 1 else "final-print"
        return maybe(
            "print_service",
            cohort._print_not_found_expectation(
                label,
                phase,
                plist_by_label[label],
                rendered["manifest"],
            ),
            {"label": label, "count": print_counts[label]},
        )

    def coordinator_cycle(step: Mapping[str, Any]) -> Mapping[str, Any]:
        terminal = bool(step.get("terminal", False))
        complete = sum(
            all(entry in delivered_entries[str(lane)] for entry in by_lane[str(lane)]["required_entries"])
            for lane in step["lanes"]
        )
        active = 0 if terminal else len(step["run_ids"])
        if terminal and complete != len(step["run_ids"]):
            active = len(step["run_ids"]) - complete
        return maybe(
            "coordinator_cycle",
            {
                "owner": "scripts.agy_gemini_coordinator:cycle_once",
                "command": cohort._coordinator_command(
                    rendered["manifest"], list(step["run_ids"])
                ),
                "cycle_once": {
                    "status": "ok",
                    "active": active,
                    "complete": complete if terminal else 0,
                    "failed": 0,
                    "runner": {"status": "external_workers_only"},
                    "new_matrix_sweep": None,
                    "legacy_sweep": None,
                    "observed_from": "deterministic-fake-lane-state",
                },
            },
            step,
        )

    def runner_once(step: Mapping[str, Any]) -> Mapping[str, Any]:
        binding = by_lane[str(step["lane"])]
        bundle = loaded_bundles[str(step["lane"])]
        entry = next(
            (
                candidate
                for candidate in bundle.entries
                if candidate.entry_id == step["entry_id"]
            ),
            None,
        )
        if entry is None or not entry.required:
            raise AssertionError("runner fake selected a non-required bundle entry")
        delivered_entries[str(step["lane"])].append(entry.entry_id)
        return maybe(
            "runner_once",
            {
                "owner": "scripts.agy_gemini_runner:sealed_replay_bundle_process_once",
                "command": cohort._runner_command(rendered["manifest"], binding),
                "sealed_replay_bundle_process_once": {
                    "status": "processed",
                    "sealed_replay_bundle": {
                        "bundle_digest": bundle.bundle_digest,
                        "expected_bundle_digest": bundle.expected_bundle_digest,
                        "lane": bundle.lane,
                        "run_id": bundle.run_id,
                        "entry_id": entry.entry_id,
                        "required": entry.required,
                        "observed_from": "runner-bundle-loader",
                    },
                },
            },
            step,
        )

    def materialize_translation(step: Mapping[str, Any]) -> Mapping[str, Any]:
        pins = cb_by_target[str(step["target_run_id"])]
        pending_path = Path(pins["pending_receipt"])
        pending_payload = json.loads(pending_path.read_text(encoding="utf-8"))
        pending, _existing = coordinator._translation_pending_payload(
            pending_payload,
            expected_source_run_id=str(step["source_run_id"]),
        )
        before_digest = coordinator._canonical_json_file_sha256(pending)
        if before_digest != pins["pending_digest"]:
            raise AssertionError("translation pending fake observed digest drift")
        proof = {
            "run_id": str(step["target_run_id"]),
            "source_run_id": str(step["source_run_id"]),
            "lane": str(step["target_lane"]),
            "brief_sha256": hashlib.sha256(
                f"brief:{step['target_run_id']}".encode()
            ).hexdigest(),
            "plan_digest": pins["plan_digest"],
            "pending_digest_before": before_digest,
            "registration_identity_digest": hashlib.sha256(
                f"registration:{step['target_run_id']}".encode()
            ).hexdigest(),
        }
        after_basis = {
            **pending,
            "status": "materialized",
            "materialized": proof,
        }
        terminal = {
            **after_basis,
            "materialized": {
                **proof,
                "pending_digest_after": coordinator._create_run_adapter_digest(after_basis),
            },
        }
        _pending, materialized = coordinator._translation_pending_payload(
            terminal,
            expected_source_run_id=str(step["source_run_id"]),
        )
        materialized_targets.add(str(step["target_run_id"]))
        return maybe(
            "materialize_translation",
            {
                "owner": "scripts.agy_gemini_coordinator:materialize_translation_pending_dependency",
                "command": cohort._materializer_command(
                    rendered["manifest"], step, pins
                ),
                "materialize_translation_pending_dependency": {
                    "status": "materialized",
                    "run_id": step["target_run_id"],
                    "source_run_id": step["source_run_id"],
                    "lane": step["target_lane"],
                    "pending_digest_before": materialized["pending_digest_before"],
                    "pending_digest_after": materialized["pending_digest_after"],
                    "plan_digest": pins["plan_digest"],
                    "brief_sha256": materialized["brief_sha256"],
                    "registration_identity_digest": materialized[
                        "registration_identity_digest"
                    ],
                    "queue_mutation": True,
                    "public_mutation": False,
                },
            },
            step,
        )

    def bundle_close(step: Mapping[str, Any]) -> Mapping[str, Any]:
        binding = by_lane[str(step["lane"])]
        lane = str(step["lane"])
        bundle = loaded_bundles[lane]

        def classify(
            _queue_root: Path,
            _bundle: runner.AcceptanceSealedReplayBundle,
            entry: runner.AcceptanceSealedReplayEntry,
        ) -> dict[str, object]:
            state = "DELIVERED" if entry.entry_id in delivered_entries[lane] else "UNUSED"
            if entry.required and state != "DELIVERED":
                state = "INCOMPLETE"
            return {
                "state": state,
                "reason": "deterministic_fake_delivery_state",
                "paths": {
                    "archive": state == "DELIVERED",
                    "inbox": state == "DELIVERED",
                    "ledger": state == "DELIVERED",
                    "anchor": state == "DELIVERED",
                    "outbox": False,
                    "processing": False,
                    "failed": False,
                },
            }

        with (
            patch.object(runner, "_bundle_namespace_job_ids", return_value={}),
            patch.object(runner, "_classify_bundle_entry_delivery", side_effect=classify),
        ):
            close_receipt = runner.sealed_replay_bundle_close(
                queue_root=Path(rendered["manifest"]["queue_root"]) / "lanes" / lane,
                lane=lane,
                exact_run_id=str(step["run_id"]),
                bundle_path=Path(binding["bundle"]),
                expected_bundle_digest=str(binding["bundle_digest"]),
            )
        return maybe(
            "bundle_close",
            {
                "owner": "scripts.agy_gemini_runner:sealed_replay_bundle_close",
                "command": [
                    *cohort._runner_command(rendered["manifest"], binding)[:-5],
                    "sealed-replay-bundle-close",
                    "--bundle",
                    binding["bundle"],
                    "--expected-bundle-digest",
                    binding["bundle_digest"],
                ],
                "sealed_replay_bundle_close": close_receipt,
            },
            step,
        )

    def publisher_plan_only(step: Mapping[str, Any]) -> Mapping[str, Any]:
        selected = sorted(publisher._normalize_exact_run_ids([str(step["run_id"])]) or ())
        if selected != [step["run_id"]]:
            raise AssertionError("publisher fake selector drifted")
        owner_function, count_field, _fields = cohort._publisher_owner_for_lane(
            str(step["lane"])
        )
        native: dict[str, Any] = {
            "schema_version": publisher.SCHEMA_VERSION,
            "status": "dry-run",
            count_field: 0,
            "ready_runs": selected,
            "base_sha": rendered["session_plan"]["actor_sha"],
            "release_plan": {},
        }
        if step["lane"] == "rewrite":
            native.update(
                {
                    "article_ids": ["legacy-article"],
                    "legacy_cutoff_count": publisher.LEGACY_ARTICLE_COUNT_CUTOFF,
                    "legacy_rewrite_backlog": {"status": "empty"},
                }
            )
        if str(step["lane"]).startswith("i18n-"):
            native["replacement_plans"] = []
        return maybe(
            "publisher_plan_only",
            {
                "owner": f"scripts.agy_content_publisher:{owner_function}",
                "command": cohort._publisher_command(
                    rendered["manifest"], str(step["run_id"]), str(step["lane"])
                ),
                owner_function: native,
            },
            step,
        )

    def drain_counts() -> Mapping[str, Any]:
        if any(
            binding["required_entries"] != delivered_entries[lane]
            for lane, binding in by_lane.items()
        ) or materialized_targets != set(cb_by_target):
            return maybe(
                "drain_counts",
                {"status": "blocked", "pending": 1, "processing": 0},
                None,
            )
        return maybe(
            "drain_counts", {"status": "drained", "pending": 0, "processing": 0}, None
        )

    return {
        "launch": launch,
        "bootout": bootout,
        "print_service": print_service,
        "production_service_state": lambda: _production_state(),
        "coordinator_cycle": coordinator_cycle,
        "runner_once": runner_once,
        "materialize_translation": materialize_translation,
        "bundle_close": bundle_close,
        "publisher_plan_only": publisher_plan_only,
        "drain_counts": drain_counts,
    }


def _run(rendered: Mapping[str, Any], **callbacks: Any) -> dict[str, Any]:
    return cohort.run_once(rendered, **{**_callbacks(rendered), **callbacks})


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
        item["owner_receipt"]["observed_from"] == "deterministic-fake-lane-state"
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
        item["owner_receipt"]["sealed_replay_bundle"]["observed_from"]
        == "runner-bundle-loader"
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
    assert result["preflight_prints"][0]["command"][0:2] == ["launchctl", "print"]
    assert result["preflight_prints"][0]["returncode"] == 113
    assert result["launchctl_receipts"][0]["phase"] == "bootstrap"
    assert result["launchctl_receipts"][0]["kickstart"]["command"][0:2] == [
        "launchctl",
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
    native = {
        "status": "materialized",
        "run_id": step["target_run_id"],
        "source_run_id": step["source_run_id"],
        "lane": step["target_lane"],
        "pending_digest_before": pins["pending_digest"],
        "pending_digest_after": hashlib.sha256(b"materialized").hexdigest(),
        "plan_digest": pins["plan_digest"],
        "brief_sha256": hashlib.sha256(b"brief").hexdigest(),
        "registration_identity_digest": hashlib.sha256(b"registration").hexdigest(),
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
    with pytest.raises(cohort.AcceptanceBlocked, match="residue"):
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

    def launch(label: str, path: Path) -> Mapping[str, Any]:
        if label in {cohort.PUBLISHER, cohort.COORDINATOR}:
            runtime_manifest.write_readiness_ack(
                Path(rendered["ready_root"]), dict(rendered["manifest"]), label
            )
        return cohort._launch_expectation(label, path, rendered["manifest"])

    with pytest.raises(cohort.AcceptanceBlocked, match="readiness"):
        _run(rendered, launch=launch, monotonic=iter((0.0, 2.0)).__next__)
    with pytest.raises(cohort.AcceptanceBlocked, match="residue"):
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

    def bootout(label: str) -> Mapping[str, Any]:
        if label == cohort.CAPACITY:
            raise RuntimeError("bootout failure")
        return {"status": "booted_out", "label": label}

    with pytest.raises(cohort.AcceptanceBlocked, match="bootout"):
        _run(rendered, bootout=bootout)
    with pytest.raises(cohort.AcceptanceBlocked, match="residue"):
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
    callbacks = _callbacks(rendered)
    original_launch = callbacks["launch"]
    original_bootout = callbacks["bootout"]
    original_print = callbacks["print_service"]
    booted_out: list[str] = []
    final_printed: list[str] = []

    def launch(label: str, path: Path) -> Mapping[str, Any]:
        receipt = dict(original_launch(label, path))
        if label == cohort.PUBLISHER:
            receipt["extra"] = "strict-schema-regression"
        return receipt

    def bootout(label: str) -> Mapping[str, Any]:
        booted_out.append(label)
        return original_bootout(label)

    def print_service(label: str) -> Mapping[str, Any]:
        receipt = original_print(label)
        if len(final_printed) < len(cohort.SERVICE_LABELS) and receipt["phase"] == "final-print":
            final_printed.append(label)
        return receipt

    with pytest.raises(cohort.AcceptanceBlocked, match="launchctl"):
        cohort.run_once(
            rendered,
            **{
                **callbacks,
                "launch": launch,
                "bootout": bootout,
                "print_service": print_service,
            },
        )

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
    ("name", "mutate", "message"),
    [
        ("coordinator_cycle", lambda receipt, _step: {**receipt, "command": [token for token in receipt["command"] if token != "--lane-mode"]}, "coordinator"),
        ("coordinator_cycle", lambda receipt, step: {**receipt, "cycle_once": {**receipt["cycle_once"], "active": 1}} if step.get("terminal") else receipt, "coordinator"),
        ("bootout", lambda _receipt, _step: {}, "bootout"),
        ("runner_once", lambda receipt, step: {**receipt, "sealed_replay_bundle_process_once": {**receipt["sealed_replay_bundle_process_once"], "status": "pending"}} if step["lane"] == "new" else receipt, "runner"),
        ("materialize_translation", lambda receipt, _step: {**receipt, "materialize_translation_pending_dependency": {**receipt["materialize_translation_pending_dependency"], "pending_digest_before": "0" * 64}}, "materialization"),
        ("runner_once", lambda receipt, step: {**receipt, "sealed_replay_bundle_process_once": {**receipt["sealed_replay_bundle_process_once"], "status": "pending"}} if step["lane"] == "i18n-new" else receipt, "runner"),
        ("bundle_close", lambda receipt, _step: {**receipt, "sealed_replay_bundle_close": {**receipt["sealed_replay_bundle_close"], "sealed_replay_bundle_session": {**receipt["sealed_replay_bundle_close"]["sealed_replay_bundle_session"], "delivered_entries": receipt["sealed_replay_bundle_close"]["sealed_replay_bundle_session"]["delivered_entries"][:1]}}}, "bundle"),
        ("publisher_plan_only", lambda receipt, _step: {**receipt, "publish_ready_runs": {**receipt["publish_ready_runs"], "ready_runs": []}}, "publisher"),
        ("publisher_plan_only", lambda receipt, _step: {**receipt, "publish_ready_runs": {**receipt["publish_ready_runs"], "ready_runs": [receipt["publish_ready_runs"]["ready_runs"][0], "extra"]}}, "publisher"),
        ("publisher_plan_only", lambda receipt, step: {"status": "missing"} if step["lane"] == "i18n-rewrite" else receipt, "publisher"),
        ("drain_counts", lambda receipt, _step: {**receipt, "pending": 1}, "drain"),
        ("launch", lambda receipt, _step: {**receipt, "generation": "wrong"}, "launchctl"),
        ("print_service", lambda receipt, step: {**receipt, "status": "loaded"} if step["count"] == 2 and step["label"] == cohort.COORDINATOR else receipt, "print"),
        ("publisher_plan_only", lambda receipt, _step: {**receipt, "publish_ready_runs": {**receipt["publish_ready_runs"], "push": True}}, "publisher"),
        ("publisher_plan_only", lambda receipt, _step: {**receipt, "publish_ready_runs": {**receipt["publish_ready_runs"], "public_mutation": True}}, "publisher"),
    ],
)
def test_runtime_receipt_regressions_cannot_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    mutate: Callable[[dict[str, Any], Mapping[str, Any]], dict[str, Any] | None],
    message: str,
) -> None:
    rendered, _acceptance = _render(tmp_path, monkeypatch)

    def override(
        observed: str, receipt: dict[str, Any], step: Mapping[str, Any] | None
    ) -> dict[str, Any] | None:
        if observed != name:
            return receipt
        return mutate(receipt, step or {})

    with pytest.raises(cohort.AcceptanceBlocked, match=message):
        cohort.run_once(rendered, **_callbacks(rendered, override=override))


def test_callback_only_readiness_ack_cannot_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rendered, _acceptance = _render(tmp_path, monkeypatch)

    def launch(label: str, _path: Path) -> Mapping[str, Any]:
        runtime_manifest.write_readiness_ack(
            Path(rendered["ready_root"]), dict(rendered["manifest"]), label
        )
        return {}

    with pytest.raises(cohort.AcceptanceBlocked, match="launchctl"):
        _run(rendered, launch=launch)


def test_empty_or_extra_production_fingerprint_schema_rejects_before_bootstrap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rendered, _acceptance = _render(tmp_path, monkeypatch)
    with pytest.raises(cohort.AcceptanceBlocked, match="production service state"):
        _run(rendered, production_service_state=lambda: {})
    with pytest.raises(cohort.AcceptanceBlocked, match="production service state"):
        _run(
            rendered,
            production_service_state=lambda: {
                **_production_state(),
                "extra": "not-authorized",
            },
        )
    with pytest.raises(cohort.AcceptanceBlocked, match="loaded acceptance"):
        _run(
            rendered,
            production_service_state=lambda: _production_state(
                {"loaded_service_snapshot": [cohort.COORDINATOR]}
            ),
        )


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
