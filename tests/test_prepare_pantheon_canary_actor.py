from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts import agy_content_publisher as publisher
from scripts import pantheon_content_runtime_manifest as runtime
from scripts import prepare_pantheon_canary_actor as canary


def _run(command: list[str], cwd: Path) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _write_runtime_manifest_fixture(repo_root: Path) -> None:
    for relative in publisher.TRANSACTION_RUNTIME_PATHS:
        path = repo_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"runtime fixture: {relative}\n", encoding="utf-8")


def _repo_with_origin_main(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init", "--initial-branch", "main"], repo)
    _run(["git", "config", "user.email", "canary@example.com"], repo)
    _run(["git", "config", "user.name", "Pantheon Canary"], repo)
    _write_runtime_manifest_fixture(repo)
    _run(["git", "add", "."], repo)
    _run(["git", "commit", "-m", "runtime"], repo)
    sha = _run(["git", "rev-parse", "HEAD"], repo)
    _run(["git", "branch", "origin/main", sha], repo)
    return repo, sha


def _paths(tmp_path: Path, repo: Path, sha: str) -> dict[str, Path | str]:
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    return {
        "repo_root": repo,
        "sandbox_root": sandbox,
        "actor_root": sandbox / "actor",
        "queue_root": sandbox / "queue",
        "publisher_state_root": sandbox / "state",
        "log_root": sandbox / "logs",
        "manifest_path": sandbox / "runtime-manifest.json",
        "python": Path(sys.executable).resolve(),
        "actor_sha": sha,
        "remote_ref": "origin/main",
        "exact_run_id": "canary-run-001",
    }


def test_canary_actor_preflight_blocks_missing_actor_and_selector(
    tmp_path: Path,
) -> None:
    repo, sha = _repo_with_origin_main(tmp_path)
    args = _paths(tmp_path, repo, sha)

    with pytest.raises(canary.CanaryActorError, match="full 40-character"):
        canary.build_plan(**{**args, "actor_sha": sha[:12]})  # type: ignore[arg-type]
    with pytest.raises(canary.CanaryActorError, match="exact run id"):
        canary.build_plan(**{**args, "exact_run_id": ""})  # type: ignore[arg-type]


def test_canary_actor_prepare_then_repreflight_is_deterministic(
    tmp_path: Path,
) -> None:
    repo, sha = _repo_with_origin_main(tmp_path)
    args = _paths(tmp_path, repo, sha)

    plan = canary.build_plan(**args)  # type: ignore[arg-type]
    result = canary.prepare(plan)
    replan = canary.build_plan(**args)  # type: ignore[arg-type]
    manifest = runtime.load_manifest(
        Path(str(args["manifest_path"])),
        result["manifest_digest"],
    )

    assert result["status"] == "prepared"
    assert result["actor_head"] == sha
    assert result["actor_clean"] is True
    assert replan["plan_digest"] == plan["plan_digest"]
    assert manifest["actor_head"] == sha
    assert manifest["python_executable"] == str(args["python"])
    assert plan["publisher_command"].count("--exact-run-id") == 1
    assert plan["publisher_command"][
        plan["publisher_command"].index("--max-runs") + 1
    ] == "1"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("state-non-empty", "publisher state root must be empty"),
        ("symlink-escape", "must not be a symlink alias"),
        ("same-checkout", "current checkout"),
        ("non-descendant", "descendant"),
        ("duplicate-plan-selector", "exactly one exact run selector"),
        ("max-runs", "bounded to one run"),
    ],
)
def test_canary_actor_negative_matrix_fails_closed(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    repo, sha = _repo_with_origin_main(tmp_path)
    args = _paths(tmp_path, repo, sha)
    if mutation == "state-non-empty":
        state = Path(args["publisher_state_root"])  # type: ignore[arg-type]
        state.mkdir()
        (state / "ledger.json").write_text("{}\n", encoding="utf-8")
        with pytest.raises(canary.CanaryActorError, match=message):
            canary.build_plan(**args)  # type: ignore[arg-type]
        return
    if mutation == "symlink-escape":
        outside = tmp_path / "outside"
        outside.mkdir()
        Path(args["log_root"]).symlink_to(outside, target_is_directory=True)  # type: ignore[arg-type]
        with pytest.raises(canary.CanaryActorError, match=message):
            canary.build_plan(**args)  # type: ignore[arg-type]
        return
    if mutation == "same-checkout":
        args["actor_root"] = repo
        with pytest.raises(canary.CanaryActorError, match=message):
            canary.build_plan(**args)  # type: ignore[arg-type]
        return
    if mutation == "non-descendant":
        other = _run(["git", "commit-tree", sha + "^{tree}", "-m", "other"], repo)
        with pytest.raises(canary.CanaryActorError, match=message):
            canary.build_plan(**{**args, "actor_sha": other})  # type: ignore[arg-type]
        return

    plan = canary.build_plan(**args)  # type: ignore[arg-type]
    if mutation == "duplicate-plan-selector":
        plan["publisher_command"].extend(["--exact-run-id", "second-run"])
    else:
        plan["publisher_command"][
            plan["publisher_command"].index("--max-runs") + 1
        ] = "2"
    with pytest.raises(canary.CanaryActorError, match=message):
        canary.prepare(plan)


def test_canary_actor_cli_writes_no_go_receipt(tmp_path: Path) -> None:
    repo, sha = _repo_with_origin_main(tmp_path)
    args = _paths(tmp_path, repo, sha)
    receipt = tmp_path / "receipt.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.prepare_pantheon_canary_actor",
            "preflight",
            "--repo-root",
            str(args["repo_root"]),
            "--sandbox-root",
            str(args["sandbox_root"]),
            "--actor-root",
            str(args["actor_root"]),
            "--queue-root",
            str(args["queue_root"]),
            "--publisher-state-root",
            str(args["publisher_state_root"]),
            "--log-root",
            str(args["log_root"]),
            "--runtime-manifest",
            str(args["manifest_path"]),
            "--python",
            str(args["python"]),
            "--actor-sha",
            "bad-sha",
            "--remote-ref",
            str(args["remote_ref"]),
            "--exact-run-id",
            str(args["exact_run_id"]),
            "--receipt",
            str(receipt),
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert json.loads(receipt.read_text(encoding="utf-8"))["status"] == "NO-GO"
