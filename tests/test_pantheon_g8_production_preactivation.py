from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

from scripts import agy_content_publisher as publisher
from scripts import pantheon_content_runtime_manifest as runtime_manifest
from scripts import pantheon_g8_production_preactivation as preactivation
from tests.test_agy_content_publisher import make_publishable_article
from tests.test_agy_content_publisher import _write_json
from tests.test_agy_content_publisher import _write_run


CARD_ID = "CARD-PANTHEON-G8-PRODUCTION-PREACTIVATION-RECONCILIATION-REPAIR-20260820"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def _commit(repo: Path, path: str, body: str, message: str) -> str:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    _git(repo, "add", path)
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _make_repo(root: Path) -> tuple[Path, str, str]:
    repo = root / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / "package.json").write_text('{"type":"module"}\n', encoding="utf-8")
    registry = repo / "app" / "web" / "static" / "article-registry.js"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        "export function getArticlePath(article) { return `/articles/test/${article.urlSlug || article.id}`; }\n"
        "export function listArticleRecords() { return []; }\n",
        encoding="utf-8",
    )
    (registry.parent / "article-meta.js").write_text(
        "export function buildArticleContent() { return {answer: '', bodySections: []}; }\n",
        encoding="utf-8",
    )
    required = _commit(repo, "README.md", "base\n", "base")
    origin_main = _commit(
        repo,
        "artifacts/fortune_council/four_lane_runtime_execution/allowed.md",
        "allowed\n",
        "allowed drift",
    )
    _git(repo, "checkout", "--detach", required)
    return repo, required, origin_main


def _clone_actor(root: Path, repo: Path, origin_main: str) -> Path:
    actor = root / "actor"
    _git(root, "clone", str(repo), str(actor))
    _git(actor, "checkout", "--detach", origin_main)
    return actor


def _runtime_dirs(root: Path, actor: Path, queue: Path, state: Path, logs: Path) -> tuple[Path, Path, Path, dict[str, Any]]:
    live = root / "live"
    staged = root / "staged"
    live.mkdir()
    staged.mkdir()
    live_manifest = runtime_manifest.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity="g8-live",
        runtime_digest="1" * 64,
        generation="g8-live",
        actor_head="1" * 40,
    )
    staged_manifest = runtime_manifest.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity="g13-stage",
        runtime_digest="2" * 64,
        generation="g13-stage",
        actor_head=_git(actor, "rev-parse", "HEAD"),
    )
    manifest_path = root / "runtime-manifest.json"
    runtime_manifest.write_manifest(manifest_path, staged_manifest)
    for label in runtime_manifest.SERVICE_LABELS:
        _write_json(live / f"{label}.json", runtime_manifest.receipt_for_label(live_manifest, label))
        _write_json(staged / f"{label}.json", runtime_manifest.receipt_for_label(staged_manifest, label))
    (staged / "publisher-exact-run-id").write_text("target-run\n", encoding="utf-8")
    return live, staged, manifest_path, staged_manifest


def _fixture(tmp_path: Path) -> dict[str, Any]:
    repo, required, origin_main = _make_repo(tmp_path)
    actor = _clone_actor(tmp_path, repo, origin_main)
    queue = tmp_path / "queue"
    state = tmp_path / "state"
    logs = tmp_path / "logs"
    tx = state / "transactions"
    for path in (queue, state, logs, tx):
        path.mkdir(parents=True)
    live, staged, manifest_path, manifest = _runtime_dirs(tmp_path, actor, queue, state, logs)
    _write_run(queue, tmp_path / "runs" / "target-run", make_publishable_article("AUTO-TARGET"))
    return {
        "repo": repo,
        "actor": actor,
        "queue": queue,
        "state": state,
        "tx": tx,
        "live": live,
        "staged": staged,
        "manifest_path": manifest_path,
        "manifest": manifest,
        "required": required,
        "origin_main": origin_main,
        "evidence": tmp_path / "evidence" / "receipt.json",
    }


def _args(fixture: dict[str, Any], **overrides: Any) -> list[str]:
    values = {
        "card_id": CARD_ID,
        "repo_root": fixture["repo"],
        "actor_root": fixture["actor"],
        "queue_root": fixture["queue"],
        "state_root": fixture["state"],
        "transaction_root": fixture["tx"],
        "live_root": fixture["live"],
        "staged_root": fixture["staged"],
        "manifest": fixture["manifest_path"],
        "expected_manifest_digest": fixture["manifest"]["manifest_digest"],
        "required_source": fixture["required"],
        "origin_main": fixture["origin_main"],
        "exact_run_id": "target-run",
        "evidence_path": fixture["evidence"],
        "allow_source_drift": ["artifacts/fortune_council/four_lane_runtime_execution/**"],
    }
    values.update(overrides)
    args = [
        "--card-id",
        values["card_id"],
        "--repo-root",
        str(values["repo_root"]),
        "--actor-root",
        str(values["actor_root"]),
        "--queue-root",
        str(values["queue_root"]),
        "--state-root",
        str(values["state_root"]),
        "--transaction-root",
        str(values["transaction_root"]),
        "--live-root",
        str(values["live_root"]),
        "--staged-root",
        str(values["staged_root"]),
        "--manifest",
        str(values["manifest"]),
        "--expected-manifest-digest",
        values["expected_manifest_digest"],
        "--required-source",
        values["required_source"],
        "--origin-main",
        values["origin_main"],
        "--exact-run-id",
        values["exact_run_id"],
        "--evidence-path",
        str(values["evidence_path"]),
    ]
    for pattern in values["allow_source_drift"]:
        args.extend(["--allow-source-drift", pattern])
    return args


def _run(fixture: dict[str, Any], **overrides: Any) -> tuple[int, dict[str, Any]]:
    code = preactivation.main(_args(fixture, **overrides))
    receipt = json.loads(fixture["evidence"].read_text(encoding="utf-8"))
    return code, receipt


def _run_cli(fixture: dict[str, Any], **overrides: Any) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    completed = subprocess.run(
        [sys.executable, "scripts/pantheon_g8_production_preactivation.py", *_args(fixture, **overrides)],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed, json.loads(completed.stdout)


def _protected_snapshot(fixture: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    return preactivation._snapshot(preactivation.parse_args(_args(fixture, **overrides)))


def _assert_protected_unchanged(
    fixture: dict[str, Any],
    before: dict[str, Any],
    receipt: dict[str, Any],
    **overrides: Any,
) -> None:
    after = _protected_snapshot(fixture, **overrides)
    assert after == before
    assert receipt["mutation_tripwire"]["status"] == "PASS"
    assert receipt["mutation_tripwire"]["changed"] == []


def test_positive_planned_fast_forward_old_live_to_new_stage_exact_selector(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)

    code, receipt = _run(fixture)

    assert code == 0
    assert receipt["status"] == "READY_FOR_PRODUCTION_AUTHORIZATION"
    assert receipt["authority"]["status"] == "PLANNED_FAST_FORWARD"
    assert receipt["runtime_transition"]["status"] == "OLD_LIVE_TO_NEW_STAGE_READY"
    assert receipt["selector"]["status"] == "CURRENT_EXACT_SELECTOR_READY"
    assert receipt["mutation_tripwire"]["status"] == "PASS"
    assert not (fixture["state"] / "publisher.lock").exists()


def test_remote_diverged_blocks(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)

    code, receipt = _run(fixture, origin_main="0" * 40)

    assert code == 1
    assert receipt["status"] == "BLOCKED"
    assert receipt["blocked_code"] == "REMOTE_DIVERGED"


def test_non_allowlisted_source_drift_blocks(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)

    code, receipt = _run(fixture, allow_source_drift=["docs/**"])

    assert code == 1
    assert receipt["blocked_code"] == "SOURCE_DRIFT"


def test_actor_manifest_mismatch_blocks(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    _git(fixture["actor"], "checkout", "--detach", fixture["required"])

    code, receipt = _run(fixture)

    assert code == 1
    assert receipt["blocked_code"] == "ACTOR_MANIFEST_AUTHORITY_MISMATCH"


def test_live_mixed_identity_blocks(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    path = fixture["live"] / f"{runtime_manifest.SERVICE_LABELS[1]}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["generation"] = "other-live"
    _write_json(path, payload)

    code, receipt = _run(fixture)

    assert code == 1
    assert receipt["blocked_code"] == "LIVE_RUNTIME_MIXED"


def test_staged_missing_service_blocks(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    (fixture["staged"] / f"{runtime_manifest.SERVICE_LABELS[-1]}.json").unlink()

    code, receipt = _run(fixture)

    assert code == 1
    assert receipt["blocked_code"] in {"FileNotFoundError", "INVALID_JSON"}


def test_staged_drift_blocks(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    path = fixture["staged"] / f"{runtime_manifest.SERVICE_LABELS[0]}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["actor_head"] = fixture["required"]
    _write_json(path, payload)

    code, receipt = _run(fixture)

    assert code == 1
    assert receipt["blocked_code"] == "RuntimeManifestError"


def test_selector_zero_blocks(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    (fixture["staged"] / "publisher-exact-run-id").write_text("missing-run\n", encoding="utf-8")

    code, receipt = _run(fixture, exact_run_id="missing-run")

    assert code == 1
    assert receipt["blocked_code"] == "SELECTOR_CARDINALITY"


def test_selector_two_blocks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = _fixture(tmp_path)
    state = {"run_id": "target-run", "status": "complete"}
    candidate = {"run_id": "target-run", "mode": "create", "articles": [make_publishable_article("AUTO-A")]}
    review = {"run_id": "target-run", "articles": []}
    monkeypatch.setattr(
        preactivation.publisher,
        "collect_ready_runs",
        lambda *_args, **_kwargs: [(state, candidate, review), (state, candidate, review)],
    )

    code, receipt = _run(fixture)

    assert code == 1
    assert receipt["blocked_code"] == "SELECTOR_CARDINALITY"
    assert receipt["details"]["count"] == 2


def test_wrong_exact_run_blocks(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    (fixture["staged"] / "publisher-exact-run-id").write_text("other-run\n", encoding="utf-8")

    code, receipt = _run(fixture)

    assert code == 1
    assert receipt["blocked_code"] == "STAGED_SELECTOR_MISMATCH"


def test_run_identity_drift_blocks_without_mutation(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    candidate_path = tmp_path / "runs" / "target-run" / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate["run_id"] = "other-run"
    _write_json(candidate_path, candidate)

    code, receipt = _run(fixture)

    assert code == 1
    assert receipt["status"] == "BLOCKED"
    assert receipt["blocked_code"] == "SELECTOR_CARDINALITY"
    assert receipt["mutation_tripwire"]["status"] == "PASS"


def test_mutation_tripwire_blocks_collect_ready_runs_side_effect(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    before = _protected_snapshot(fixture)
    review_path = tmp_path / "runs" / "target-run" / "review.json"
    review = json.loads(review_path.read_text(encoding="utf-8"))
    review["articles"][0]["verdict"] = "REJECT"
    review["articles"][0]["hard_failure"] = True
    review["articles"][0]["findings"] = [{"code": "reject", "message": "blocked"}]
    _write_json(review_path, review)

    code, receipt = _run(fixture)

    assert code == 1
    assert receipt["blocked_code"] == "SELECTOR_CARDINALITY"
    _assert_protected_unchanged(fixture, before, receipt)


@pytest.mark.parametrize("state_case", ["ledger", "retry", "policy_rejection"])
def test_selector_snapshot_preserves_existing_production_state_parity(
    tmp_path: Path,
    state_case: str,
) -> None:
    fixture = _fixture(tmp_path)
    if state_case == "ledger":
        ledger = publisher._load_ledger(fixture["state"])
        ledger["published_runs"].append({"run_id": "target-run"})
        _write_json(publisher._ledger_path(fixture["state"]), ledger)
    elif state_case == "retry":
        _write_json(
            publisher._retry_path(fixture["state"], "create", "target-run"),
            {
                "schema_version": publisher.SCHEMA_VERSION,
                "phase": "create",
                "run_id": "target-run",
                "attempts": publisher.MAX_RETRY_ATTEMPTS,
                "max_attempts": publisher.MAX_RETRY_ATTEMPTS,
                "error_type": "PublishBlocked",
                "error": "existing exhausted retry",
                "next_eligible_at": "2099-01-01T00:00:00+00:00",
                "eligibility": "exhausted",
            },
        )
    else:
        candidate_path = tmp_path / "runs" / "target-run" / "candidate.json"
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        candidate["articles"][0]["publicationPolicy"]["author"]["name"] = "不明作者"
        _write_json(candidate_path, candidate)
        assert publisher.collect_ready_runs(fixture["queue"], fixture["state"]) == []
        assert publisher._policy_rejection_path(fixture["state"], "create", "target-run").is_file()
    before = _protected_snapshot(fixture)

    code, receipt = _run(fixture)

    assert code == 1
    assert receipt["blocked_code"] == "SELECTOR_CARDINALITY"
    _assert_protected_unchanged(fixture, before, receipt)


def test_cli_writes_machine_readable_receipt_and_exit_code(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)

    completed, stdout_receipt = _run_cli(fixture)

    assert completed.returncode == 0
    file_receipt = json.loads(fixture["evidence"].read_text(encoding="utf-8"))
    assert stdout_receipt["status"] == "READY_FOR_PRODUCTION_AUTHORIZATION"
    assert file_receipt == stdout_receipt


@pytest.mark.parametrize(
    ("label", "path_factory", "created_parent_factory"),
    [
        (
            "state_child",
            lambda fixture, tmp_path: fixture["state"] / "blocked-evidence" / "receipt.json",
            lambda fixture, tmp_path: fixture["state"] / "blocked-evidence",
        ),
        (
            "queue_child",
            lambda fixture, tmp_path: fixture["queue"] / "blocked-evidence" / "receipt.json",
            lambda fixture, tmp_path: fixture["queue"] / "blocked-evidence",
        ),
        (
            "manifest_exact",
            lambda fixture, tmp_path: fixture["manifest_path"],
            lambda fixture, tmp_path: None,
        ),
        (
            "symlink_alias",
            lambda fixture, tmp_path: tmp_path / "state-link" / "receipt.json",
            lambda fixture, tmp_path: tmp_path / "state-link" / "receipt.json",
        ),
    ],
)
def test_cli_rejects_protected_evidence_paths_without_side_effect(
    tmp_path: Path,
    label: str,
    path_factory: object,
    created_parent_factory: object,
) -> None:
    fixture = _fixture(tmp_path)
    if label == "symlink_alias":
        (tmp_path / "state-link").symlink_to(fixture["state"], target_is_directory=True)
    evidence_path = path_factory(fixture, tmp_path)  # type: ignore[operator]
    created_parent = created_parent_factory(fixture, tmp_path)  # type: ignore[operator]
    before = _protected_snapshot(fixture, evidence_path=evidence_path)
    manifest_before = fixture["manifest_path"].read_bytes()

    completed, receipt = _run_cli(fixture, evidence_path=evidence_path)

    assert completed.returncode == 1
    assert receipt["status"] == "BLOCKED"
    assert receipt["blocked_code"] in {"EVIDENCE_PATH_PROTECTED", "EVIDENCE_PATH_ALIAS"}
    assert _protected_snapshot(fixture, evidence_path=evidence_path) == before
    assert fixture["manifest_path"].read_bytes() == manifest_before
    if label == "manifest_exact":
        assert json.loads(fixture["manifest_path"].read_text(encoding="utf-8"))["manifest_digest"] == fixture["manifest"]["manifest_digest"]
    elif created_parent is not None:
        assert not created_parent.exists()


def test_cli_writes_legal_external_evidence_path(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    evidence_path = tmp_path / "external-evidence" / "receipt.json"
    before = _protected_snapshot(fixture, evidence_path=evidence_path)

    completed, receipt = _run_cli(fixture, evidence_path=evidence_path)

    assert completed.returncode == 0
    assert receipt["status"] == "READY_FOR_PRODUCTION_AUTHORIZATION"
    assert evidence_path.is_file()
    assert json.loads(evidence_path.read_text(encoding="utf-8")) == receipt
    assert _protected_snapshot(fixture, evidence_path=evidence_path) == before
