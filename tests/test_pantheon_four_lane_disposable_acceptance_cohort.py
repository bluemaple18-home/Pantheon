from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import plistlib
import sys

import pytest

from scripts import pantheon_content_runtime_manifest as runtime_manifest
from scripts import pantheon_four_lane_disposable_acceptance_cohort as cohort

NONCE = "d" * 64
GENERATION = f"acceptance-{NONCE[:32]}"


@pytest.fixture(autouse=True)
def _supply_external_session_plan(monkeypatch: pytest.MonkeyPatch):
    """既有 projection cases 都經由 caller supplied 的 immutable plan。"""
    original = cohort.render_plists

    def render_with_plan(**kwargs):
        acceptance = Path(kwargs["acceptance_root"])
        kwargs["manifest_path"] = acceptance / "manifest.json"
        plan = acceptance / "session-plan.json"
        kwargs.setdefault("session_plan_path", plan)
        kwargs.setdefault("expected_session_plan_digest", hashlib.sha256(plan.read_bytes()).hexdigest())
        return original(**kwargs)

    monkeypatch.setattr(cohort, "render_plists", render_with_plan)
    return original


def _fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[dict[str, object], list[dict[str, str]], Path, dict[str, Path]]:
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
    for name in ("plists", "readiness", "barriers", "locks", "evidence"):
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
    bindings: list[dict[str, str]] = []
    for index, lane in enumerate(cohort.LANES):
        bundle = tmp_path / f"{lane}.bundle.json"
        bundle.write_text('{"bundle":true}\n', encoding="utf-8")
        bundle.chmod(0o600)
        bindings.append({
            "lane": lane,
            "run_id": f"exact-{lane}-{index}",
            "bundle": str(bundle.resolve()),
            "bundle_digest": hashlib.sha256(bundle.read_bytes()).hexdigest(),
            "actor_digest": manifest["runtime_digest"],
            "generation": manifest["generation"],
            "identity_digest": manifest["runtime_identity_digest"],
        })
    plan = {
        "schema_version": 1,
        "session_id": f"four-lane-acceptance-{NONCE[:32]}",
        "session_nonce_digest": NONCE,
        "generation": GENERATION,
        "actor_sha": manifest["actor_head"],
        "manifest_digest": manifest["manifest_digest"],
        "runtime_identity_digest": manifest["runtime_identity_digest"],
        "service_labels": list(cohort.SERVICE_LABELS),
        "exact_runs": [{"lane": item["lane"], "run_id": item["run_id"], "bundle_digest": item["bundle_digest"]} for item in bindings],
        "publisher_run_id": "exact-publisher-run",
        "roots": {
            "acceptance_root": str(acceptance.resolve()), "actor_root": manifest["actor_root"],
            "queue_root": manifest["queue_root"], "publisher_state_root": manifest["publisher_state_root"], "log_root": manifest["log_root"],
            **{f"production_{name}": str(path.resolve()) for name, path in production.items()},
        },
    }
    plan_path = acceptance / "session-plan.json"
    plan_path.write_text(json.dumps(plan, sort_keys=True) + "\n", encoding="utf-8")
    plan_path.chmod(0o600)
    return manifest, bindings, acceptance.resolve(), production


def test_rendered_cohort_has_seven_exact_plists_and_no_provider_or_publish_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, bindings, acceptance, _production = _fixture(tmp_path, monkeypatch)
    rendered = cohort.render_plists(
        manifest_path=tmp_path / "manifest.json",
        expected_manifest_digest="a" * 64,
        acceptance_root=acceptance,
        bindings=bindings,
        publisher_run_id="exact-publisher-run", production_paths=_production,
    )
    assert [path.stem for path in rendered["plist_paths"]] == list(cohort.SERVICE_LABELS)
    shared = {"PANTHEON_RUNTIME_MANIFEST_DIGEST", "PANTHEON_RUNTIME_IDENTITY_DIGEST", "PANTHEON_RUNTIME_GENERATION", "PANTHEON_RUNTIME_ACTIVATION_TOKEN"}
    for path in rendered["plist_paths"]:
        assert path.parent == acceptance / "plists" / GENERATION
        assert path.stat().st_mode & 0o777 == 0o600
        payload = plistlib.loads(path.read_bytes())
        env = payload["EnvironmentVariables"]
        assert {name: env[name] for name in shared} == {
                "PANTHEON_RUNTIME_MANIFEST_DIGEST": manifest["manifest_digest"],
                "PANTHEON_RUNTIME_IDENTITY_DIGEST": manifest["runtime_identity_digest"],
                "PANTHEON_RUNTIME_GENERATION": manifest["generation"],
                "PANTHEON_RUNTIME_ACTIVATION_TOKEN": str(acceptance / "barriers" / f"{GENERATION}.json"),
            }
        arguments = payload["ProgramArguments"]
        assert "--push" not in arguments and "deploy" not in arguments and "provider" not in " ".join(arguments)
    coordinator_payload = plistlib.loads((acceptance / "plists" / GENERATION / f"{cohort.COORDINATOR}.plist").read_bytes())
    coordinator_args = coordinator_payload["ProgramArguments"]
    assert coordinator_args.count("--exact-run-id") == 4
    assert "--external-workers-only" in coordinator_args
    publisher_args = plistlib.loads((acceptance / "plists" / GENERATION / f"{cohort.PUBLISHER}.plist").read_bytes())["ProgramArguments"]
    assert "--activation-only" in publisher_args[: publisher_args.index("--")]
    assert publisher_args.count("--exact-run-id") == 1 and "--max-runs" in publisher_args
    for binding in bindings:
        path = acceptance / "plists" / GENERATION / f"com.pantheon.agy-gemini-{binding['lane']}.plist"
        arguments = plistlib.loads(path.read_bytes())["ProgramArguments"]
        assert "sealed-replay-bundle-process-once" in arguments
        assert "process-once" not in arguments and "operator-exact-process-once" not in arguments
        assert str(Path(manifest["queue_root"]) / "lanes" / binding["lane"]) in arguments


def test_run_once_releases_barrier_and_boots_out_all_services_without_production_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    third = tmp_path / "third"
    third.mkdir(mode=0o700)
    _manifest, bindings, acceptance, production = _fixture(third, monkeypatch)
    rendered = cohort.render_plists(
        manifest_path=tmp_path / "manifest.json", expected_manifest_digest="a" * 64,
        acceptance_root=acceptance, bindings=bindings, publisher_run_id="exact-publisher-run", production_paths=production,
    )
    launches: list[str] = []
    bootouts: list[str] = []

    result = cohort.run_once(
        rendered,
        launch=lambda label, _path: launches.append(label) or runtime_manifest.write_readiness_ack(rendered["ready_root"], rendered["manifest"], label),
        bootout=lambda label: bootouts.append(label),
        production_service_state=lambda: {},
    )
    assert result["status"] == "PASS"
    assert launches == list(cohort.SERVICE_LABELS)
    assert bootouts == list(reversed(cohort.SERVICE_LABELS))
    assert not (acceptance / "barriers" / f"{GENERATION}.json").exists()
    assert not (acceptance / "locks" / f"{GENERATION}.lock").exists()
    assert not (acceptance / "readiness" / GENERATION).exists()
    assert not (acceptance / "plists" / GENERATION).exists()
    evidence = acceptance / "evidence" / GENERATION / "one-shot-session-receipt.json"
    assert evidence.is_file()
    receipt = json.loads(evidence.read_text(encoding="utf-8"))
    assert receipt["launched"] == list(cohort.SERVICE_LABELS)
    assert receipt["bootouts"] == list(reversed(cohort.SERVICE_LABELS))
    assert receipt["before_fingerprint"] == receipt["after_fingerprint"]
    assert receipt["session_id"] == f"four-lane-acceptance-{NONCE[:32]}"
    assert receipt["service_labels"] == list(cohort.SERVICE_LABELS)
    assert receipt["ack_digests"] and len(receipt["ack_digests"]) == 7
    assert set(receipt["production_root_identities"]) == cohort.PRODUCTION_ROOT_KEYS


def test_launch_failure_and_partial_readiness_converge_through_teardown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    third = tmp_path / "third"
    third.mkdir(mode=0o700)
    _manifest, bindings, acceptance, production = _fixture(third, monkeypatch)
    rendered = cohort.render_plists(
        manifest_path=tmp_path / "manifest.json", expected_manifest_digest="a" * 64,
        acceptance_root=acceptance, bindings=bindings, publisher_run_id="exact-publisher-run", production_paths=production,
    )
    bootouts: list[str] = []
    with pytest.raises(RuntimeError, match="launch"):
        cohort.run_once(
            rendered,
            launch=lambda label, _path: (_ for _ in ()).throw(RuntimeError("launch")) if label == cohort.COORDINATOR else runtime_manifest.write_readiness_ack(rendered["ready_root"], rendered["manifest"], label),
            bootout=lambda label: bootouts.append(label), production_service_state=lambda: {},
        )
    assert bootouts == [cohort.PUBLISHER]
    assert not (acceptance / "barriers" / f"{GENERATION}.json").exists() and not (acceptance / "locks" / f"{GENERATION}.lock").exists()
    bootouts.clear()
    rendered = cohort.render_plists(
        manifest_path=tmp_path / "manifest.json", expected_manifest_digest="a" * 64,
        acceptance_root=acceptance, bindings=bindings, publisher_run_id="exact-publisher-run", production_paths=production,
    )
    with pytest.raises(cohort.AcceptanceBlocked, match="readiness"):
        cohort.run_once(
            rendered,
            launch=lambda *_args: None, bootout=lambda label: bootouts.append(label), production_service_state=lambda: {}, monotonic=iter((0.0, 2.0)).__next__,
        )
    assert bootouts == list(reversed(cohort.SERVICE_LABELS))


def test_residual_token_or_lock_rejects_before_launch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _manifest, bindings, acceptance, production = _fixture(tmp_path, monkeypatch)
    rendered = cohort.render_plists(
        manifest_path=tmp_path / "manifest.json", expected_manifest_digest="a" * 64,
        acceptance_root=acceptance, bindings=bindings, publisher_run_id="exact-publisher-run", production_paths=production,
    )
    (acceptance / "locks" / f"{GENERATION}.lock").write_text("residue", encoding="utf-8")
    with pytest.raises(cohort.AcceptanceBlocked, match="residue"):
        cohort.run_once(
            rendered,
            launch=lambda *_args: pytest.fail("launch must not run"), bootout=lambda *_args: pytest.fail("bootout must not run"), production_service_state=lambda: {},
        )


def test_production_fingerprint_drift_fails_after_bounded_teardown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    third = tmp_path / "third"
    third.mkdir(mode=0o700)
    _manifest, bindings, acceptance, production = _fixture(third, monkeypatch)
    rendered = cohort.render_plists(
        manifest_path=tmp_path / "manifest.json", expected_manifest_digest="a" * 64,
        acceptance_root=acceptance, bindings=bindings, publisher_run_id="exact-publisher-run", production_paths=production,
    )
    bootouts: list[str] = []

    def mutate_production(label: str, _path: Path) -> None:
        if label == cohort.COORDINATOR:
            (production["queue"] / "forbidden-write").write_text("x", encoding="utf-8")
        runtime_manifest.write_readiness_ack(rendered["ready_root"], rendered["manifest"], label)

    with pytest.raises(cohort.AcceptanceBlocked, match="fingerprint"):
        cohort.run_once(
            rendered, launch=mutate_production,
            bootout=lambda label: bootouts.append(label), production_service_state=lambda: {},
        )
    assert bootouts == list(reversed(cohort.SERVICE_LABELS))
    assert not (acceptance / "barriers" / f"{GENERATION}.json").exists() and not (acceptance / "locks" / f"{GENERATION}.lock").exists()
    assert not (acceptance / "evidence" / GENERATION / "one-shot-session-receipt.json").exists()


@pytest.mark.parametrize("mutation", ["directory", "mode", "file", "symlink", "service"])
def test_production_fingerprint_detects_filesystem_and_service_state_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    _manifest, _bindings, _acceptance, production = _fixture(tmp_path, monkeypatch)
    state = {"loaded": []}
    before = cohort.production_fingerprint(production, lambda: state)
    root = production["queue"]
    if mutation == "directory":
        (root / "created").mkdir()
    elif mutation == "mode":
        root.chmod(0o755)
    elif mutation == "file":
        (root / "changed").write_text("changed", encoding="utf-8")
    elif mutation == "symlink":
        (root / "link").symlink_to("missing")
    else:
        state["loaded"] = ["unexpected"]
    assert cohort.production_fingerprint(production, lambda: state) != before


def test_stale_ack_and_atomic_projection_failure_leave_no_final_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
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
        cohort.render_plists(manifest_path=tmp_path / "manifest.json", expected_manifest_digest="a" * 64, acceptance_root=acceptance, bindings=bindings, publisher_run_id="exact-publisher-run", production_paths=production)
    assert not (acceptance / "plists" / GENERATION).exists() and not (acceptance / f".plists-staging.{GENERATION}").exists()
    assert not (acceptance / "readiness" / GENERATION).exists() and not (acceptance / "evidence" / GENERATION).exists()
    monkeypatch.setattr(cohort, "_write_plist", original)
    rendered = cohort.render_plists(manifest_path=tmp_path / "manifest.json", expected_manifest_digest="a" * 64, acceptance_root=acceptance, bindings=bindings, publisher_run_id="exact-publisher-run", production_paths=production)
    runtime_manifest.write_readiness_ack(rendered["ready_root"], rendered["manifest"], cohort.PUBLISHER)
    with pytest.raises(cohort.AcceptanceBlocked, match="generation residue"):
        cohort.run_once(rendered, launch=lambda *_args: pytest.fail("stale ack must reject before launch"), bootout=lambda *_args: pytest.fail("stale ack must not teardown"), production_service_state=lambda: {})


@pytest.mark.parametrize("kind", ["empty", "missing", "extra", "substitution"])
def test_render_requires_exact_four_disjoint_production_roots_before_projection_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    _manifest, bindings, acceptance, production = _fixture(tmp_path, monkeypatch)
    supplied = dict(production)
    if kind == "empty":
        supplied = {}
    elif kind == "missing":
        supplied.pop("public")
    elif kind == "extra":
        supplied["extra"] = tmp_path / "production-extra"
        supplied["extra"].mkdir(mode=0o700)
    else:
        supplied["queue"] = supplied["ledger"]
    with pytest.raises(cohort.AcceptanceBlocked, match="production"):
        cohort.render_plists(
            manifest_path=tmp_path / "manifest.json", expected_manifest_digest="a" * 64,
            acceptance_root=acceptance, bindings=bindings, publisher_run_id="exact-publisher-run", production_paths=supplied,
        )
    assert not (acceptance / "plists" / GENERATION).exists()
    assert not (acceptance / "readiness" / GENERATION).exists()
    assert not (acceptance / "evidence" / GENERATION).exists()


def test_production_root_safety_and_existing_evidence_reject_before_render_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _manifest, bindings, acceptance, production = _fixture(tmp_path, monkeypatch)
    production["public"].chmod(0o720)
    with pytest.raises(cohort.AcceptanceBlocked, match="owner-safe"):
        cohort.render_plists(
            manifest_path=tmp_path / "manifest.json", expected_manifest_digest="a" * 64,
            acceptance_root=acceptance, bindings=bindings, publisher_run_id="exact-publisher-run", production_paths=production,
        )
    production["public"].chmod(0o700)
    evidence = acceptance / "evidence" / GENERATION
    evidence.mkdir(mode=0o700)
    (evidence / "foreign.json").write_text("{}", encoding="utf-8")
    with pytest.raises(cohort.AcceptanceBlocked, match="residue"):
        cohort.render_plists(
            manifest_path=tmp_path / "manifest.json", expected_manifest_digest="a" * 64,
            acceptance_root=acceptance, bindings=bindings, publisher_run_id="exact-publisher-run", production_paths=production,
        )
    assert not (acceptance / "plists" / GENERATION).exists()


def test_external_plan_digest_and_prelaunch_generation_residue_reject(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _supply_external_session_plan
) -> None:
    _manifest, bindings, acceptance, production = _fixture(tmp_path, monkeypatch)
    original = _supply_external_session_plan
    plan_path = acceptance / "session-plan.json"
    with pytest.raises(cohort.AcceptanceBlocked, match="plan digest"):
        original(
            manifest_path=acceptance / "manifest.json", expected_manifest_digest="a" * 64,
            acceptance_root=acceptance, bindings=bindings, publisher_run_id="exact-publisher-run", production_paths=production,
            session_plan_path=plan_path, expected_session_plan_digest="0" * 64,
        )
    rendered = cohort.render_plists(
        manifest_path=tmp_path / "manifest.json", expected_manifest_digest="a" * 64,
        acceptance_root=acceptance, bindings=bindings, publisher_run_id="exact-publisher-run", production_paths=production,
    )
    assert rendered["barrier"].name == f"{GENERATION}.json"
    assert rendered["lock"].name == f"{GENERATION}.lock"
    rendered["ready_root"].mkdir(mode=0o700)
    with pytest.raises(cohort.AcceptanceBlocked, match="generation residue"):
        cohort.run_once(
            rendered,
            launch=lambda *_args: pytest.fail("generation residue must reject before launch"),
            bootout=lambda *_args: pytest.fail("generation residue must not bootout before launch"),
            production_service_state=lambda: {},
        )


def test_completed_one_shot_session_rejects_second_render_before_any_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _manifest, bindings, acceptance, production = _fixture(tmp_path, monkeypatch)
    rendered = cohort.render_plists(
        manifest_path=tmp_path / "manifest.json", expected_manifest_digest="a" * 64,
        acceptance_root=acceptance, bindings=bindings, publisher_run_id="exact-publisher-run", production_paths=production,
    )
    cohort.run_once(
        rendered,
        launch=lambda label, _path: runtime_manifest.write_readiness_ack(rendered["ready_root"], rendered["manifest"], label),
        bootout=lambda _label: None,
        production_service_state=lambda: {},
    )
    with pytest.raises(cohort.AcceptanceBlocked, match="residue"):
        cohort.render_plists(
            manifest_path=tmp_path / "manifest.json", expected_manifest_digest="a" * 64,
            acceptance_root=acceptance, bindings=bindings, publisher_run_id="exact-publisher-run", production_paths=production,
        )


@pytest.mark.parametrize("field", ["generation", "manifest_digest", "runtime_identity_digest", "service_labels", "exact_runs", "publisher_run_id", "roots"])
def test_pinned_session_plan_drift_rejects_before_generation_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, _supply_external_session_plan
) -> None:
    _manifest, bindings, acceptance, production = _fixture(tmp_path, monkeypatch)
    original = _supply_external_session_plan
    path = acceptance / "session-plan.json"
    plan = json.loads(path.read_text(encoding="utf-8"))
    if field == "generation":
        plan[field] = "acceptance-" + "0" * 32
    elif field == "service_labels":
        plan[field] = list(reversed(plan[field]))
    elif field == "exact_runs":
        plan[field][0]["bundle_digest"] = "0" * 64
    elif field == "roots":
        plan[field]["production_public"] = str(tmp_path / "wrong-public")
    else:
        plan[field] = "wrong" if field == "publisher_run_id" else "0" * 64
    path.write_text(json.dumps(plan, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(0o600)
    with pytest.raises(cohort.AcceptanceBlocked, match="plan|generation"):
        original(
            manifest_path=acceptance / "manifest.json", expected_manifest_digest="a" * 64,
            acceptance_root=acceptance, bindings=bindings, publisher_run_id="exact-publisher-run", production_paths=production,
            session_plan_path=path, expected_session_plan_digest=hashlib.sha256(path.read_bytes()).hexdigest(),
        )
    assert not (acceptance / "plists" / GENERATION).exists()


def test_plan_revalidation_and_foreign_ack_reject_before_or_during_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    second = tmp_path / "second"
    second.mkdir(mode=0o700)
    _manifest, bindings, acceptance, production = _fixture(second, monkeypatch)
    rendered = cohort.render_plists(
        manifest_path=tmp_path / "manifest.json", expected_manifest_digest="a" * 64,
        acceptance_root=acceptance, bindings=bindings, publisher_run_id="exact-publisher-run", production_paths=production,
    )
    path = acceptance / "session-plan.json"
    plan = json.loads(path.read_text(encoding="utf-8")); plan["publisher_run_id"] = "tampered"
    path.write_text(json.dumps(plan, sort_keys=True) + "\n", encoding="utf-8"); path.chmod(0o600)
    with pytest.raises(cohort.AcceptanceBlocked, match="plan"):
        cohort.run_once(rendered, launch=lambda *_args: pytest.fail("plan drift must reject before launch"), bootout=lambda *_args: pytest.fail("plan drift must not bootout"), production_service_state=lambda: {})

    foreign_case = tmp_path / "foreign-case"
    foreign_case.mkdir(mode=0o700)
    _manifest, bindings, acceptance, production = _fixture(foreign_case, monkeypatch)
    rendered = cohort.render_plists(
        manifest_path=tmp_path / "manifest.json", expected_manifest_digest="a" * 64,
        acceptance_root=acceptance, bindings=bindings, publisher_run_id="exact-publisher-run", production_paths=production,
    )
    bootouts: list[str] = []
    def service_emulator(label: str, _path: Path) -> None:
        runtime_manifest.write_readiness_ack(rendered["ready_root"], rendered["manifest"], label)
        if label == cohort.CAPACITY:
            (rendered["ready_root"] / "foreign.json").write_text("{}", encoding="utf-8")
    with pytest.raises(cohort.AcceptanceBlocked, match="acknowledgement set"):
        cohort.run_once(rendered, launch=service_emulator, bootout=lambda label: bootouts.append(label), production_service_state=lambda: {})
    assert bootouts == list(reversed(cohort.SERVICE_LABELS))


def test_existing_barrier_validator_rejects_prior_generation_ack_variants(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, _bindings, acceptance, _production = _fixture(tmp_path, monkeypatch)
    old = dict(manifest); old["generation"] = "acceptance-" + "c" * 32
    current_ready = acceptance / "readiness" / GENERATION
    old_ready = acceptance / "old-ready"
    for label in cohort.SERVICE_LABELS:
        runtime_manifest.write_readiness_ack(old_ready, old, label)
        target = current_ready / f"{label}.json"
        target.parent.mkdir(mode=0o700, exist_ok=True)
        target.write_bytes((old_ready / f"{label}.json").read_bytes())
        target.chmod(0o600)
    with pytest.raises(runtime_manifest.RuntimeManifestError):
        runtime_manifest.activate_barrier(acceptance / "barriers" / "wrong.json", current_ready, manifest)
    payload = json.loads((current_ready / f"{cohort.PUBLISHER}.json").read_text(encoding="utf-8"))
    payload["generation"] = manifest["generation"]
    payload["runtime_identity_digest"] = "0" * 64
    payload["ack_digest"] = runtime_manifest._manifest_digest({key: value for key, value in payload.items() if key != "ack_digest"})
    (current_ready / f"{cohort.PUBLISHER}.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(runtime_manifest.RuntimeManifestError):
        runtime_manifest.activate_barrier(acceptance / "barriers" / "wrong.json", current_ready, manifest)


@pytest.mark.parametrize("label", [cohort.COORDINATOR, "com.pantheon.agy-gemini-new", cohort.PUBLISHER, cohort.CAPACITY])
def test_local_child_contract_validator_rejects_one_tampered_token_per_service_class(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, label: str
) -> None:
    manifest, bindings, acceptance, production = _fixture(tmp_path, monkeypatch)
    rendered = cohort.render_plists(
        manifest_path=tmp_path / "manifest.json", expected_manifest_digest="a" * 64,
        acceptance_root=acceptance, bindings=bindings, publisher_run_id="exact-publisher-run", production_paths=production,
    )
    path = next(path for path in rendered["plist_paths"] if path.stem == label)
    plist = plistlib.loads(path.read_bytes())
    arguments = plist["ProgramArguments"]
    child_start = arguments.index("--") + 1
    if label == cohort.COORDINATOR:
        arguments[arguments.index("--external-workers-only", child_start)] = "--worker-pool"
    elif label.endswith("-new"):
        arguments[arguments.index("sealed-replay-bundle-process-once", child_start)] = "process-once"
    elif label == cohort.PUBLISHER:
        arguments[arguments.index("exact-publisher-run", child_start)] = "wrong-publisher-run"
    else:
        arguments[-1] = "capacity-sweep"
    path.write_bytes(plistlib.dumps(plist, fmt=plistlib.FMT_XML, sort_keys=True))
    with pytest.raises(cohort.AcceptanceBlocked):
        cohort._validate_children(rendered["plist_paths"], rendered["bindings"], manifest, "exact-publisher-run")


def test_unknown_ready_residue_and_bootout_failure_never_write_success_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _manifest, bindings, acceptance, production = _fixture(tmp_path, monkeypatch)
    rendered = cohort.render_plists(
        manifest_path=tmp_path / "manifest.json", expected_manifest_digest="a" * 64,
        acceptance_root=acceptance, bindings=bindings, publisher_run_id="exact-publisher-run", production_paths=production,
    )
    bootouts: list[str] = []

    def service_emulator_with_residue(label: str, _path: Path) -> None:
        runtime_manifest.write_readiness_ack(rendered["ready_root"], rendered["manifest"], label)
        if label == cohort.CAPACITY:
            (rendered["ready_root"] / "unknown.txt").write_text("residue", encoding="utf-8")

    with pytest.raises(cohort.AcceptanceBlocked, match="teardown"):
        cohort.run_once(rendered, launch=service_emulator_with_residue, bootout=lambda label: bootouts.append(label), production_service_state=lambda: {})
    assert bootouts == list(reversed(cohort.SERVICE_LABELS))
    assert not (acceptance / "evidence" / GENERATION / "one-shot-session-receipt.json").exists()
    (rendered["ready_root"] / "unknown.txt").unlink()
    rendered["ready_root"].rmdir()

    rendered = cohort.render_plists(
        manifest_path=tmp_path / "manifest.json", expected_manifest_digest="a" * 64,
        acceptance_root=acceptance, bindings=bindings, publisher_run_id="exact-publisher-run", production_paths=production,
    )
    attempted: list[str] = []

    def failing_bootout(label: str) -> None:
        attempted.append(label)
        if label == cohort.CAPACITY:
            raise RuntimeError("bootout failure")

    with pytest.raises(cohort.AcceptanceBlocked, match="teardown or fingerprint"):
        cohort.run_once(
            rendered,
            launch=lambda label, _path: runtime_manifest.write_readiness_ack(rendered["ready_root"], rendered["manifest"], label),
            bootout=failing_bootout,
            production_service_state=lambda: {},
        )
    assert attempted == list(reversed(cohort.SERVICE_LABELS))
    assert not (acceptance / "evidence" / GENERATION / "one-shot-session-receipt.json").exists()
