from __future__ import annotations

import copy
import os
import plistlib
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import agy_gemini_reviewer_cutover as cutover
from scripts.agy_gemini_outbox import build_external_request


def _coordinator_plist() -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[1]
    plist = plistlib.loads(
        (
            repo_root
            / "ops"
            / "launchd"
            / "com.pantheon.agy-gemini-coordinator.plist.example"
        ).read_bytes()
    )
    plist["EnvironmentVariables"]["AGY_WRITER_MODEL"] = "gemini-writer-stable"
    plist["EnvironmentVariables"]["AGY_REVIEWER_MODEL"] = "gemini-reviewer-limited"
    return plist


def test_render_cutover_changes_only_reviewer_model(tmp_path: Path) -> None:
    source = tmp_path / "coordinator.plist"
    output = tmp_path / "cutover.plist"
    original = _coordinator_plist()
    source.write_bytes(plistlib.dumps(original))

    summary = cutover.render_reviewer_cutover(
        source,
        output,
        "gemini-3.5-flash",
    )

    rendered = plistlib.loads(output.read_bytes())
    expected = copy.deepcopy(original)
    expected["EnvironmentVariables"]["AGY_REVIEWER_MODEL"] = "gemini-3.5-flash"
    assert rendered == expected
    assert summary == {
        "label": "com.pantheon.agy-gemini-coordinator",
        "previous_reviewer_model": "gemini-reviewer-limited",
        "reviewer_model": "gemini-3.5-flash",
        "writer_model": "gemini-writer-stable",
    }


@pytest.mark.parametrize(
    "model",
    ["", "gemini reviewer", "gemini/reviewer", "gemini-reviewer;touch"],
)
def test_render_cutover_rejects_unsafe_model_identifier(
    tmp_path: Path,
    model: str,
) -> None:
    source = tmp_path / "coordinator.plist"
    source.write_bytes(plistlib.dumps(_coordinator_plist()))

    with pytest.raises(ValueError, match="safe model identifier"):
        cutover.render_reviewer_cutover(
            source,
            tmp_path / "cutover.plist",
            model,
        )


def test_render_cutover_rejects_non_coordinator_plist(tmp_path: Path) -> None:
    source = tmp_path / "lane.plist"
    plist = _coordinator_plist()
    plist["Label"] = "com.pantheon.agy-gemini-new"
    source.write_bytes(plistlib.dumps(plist))

    with pytest.raises(ValueError, match="coordinator plist"):
        cutover.render_reviewer_cutover(
            source,
            tmp_path / "cutover.plist",
            "gemini-3.5-flash",
        )


def test_reviewer_cutover_changes_only_reviewer_request_identity() -> None:
    common = {
        "namespace": "reviewer-cutover",
        "prompt": "公開 prompt",
        "response_schema": {
            "type": "object",
            "properties": {"verdict": {"type": "string"}},
            "required": ["verdict"],
        },
    }
    writer_before = build_external_request(
        role="writer",
        model="gemini-writer-stable",
        **common,
    )
    writer_after = build_external_request(
        role="writer",
        model="gemini-writer-stable",
        **common,
    )
    reviewer_before = build_external_request(
        role="reviewer",
        model="gemini-reviewer-limited",
        **common,
    )
    reviewer_after = build_external_request(
        role="reviewer",
        model="gemini-3.5-flash",
        **common,
    )

    assert writer_after["job_id"] == writer_before["job_id"]
    assert reviewer_after["job_id"] != reviewer_before["job_id"]


def _cutover_runtime(
    tmp_path: Path,
    *,
    loaded: bool,
    fail_first_bootstrap: bool = False,
) -> tuple[dict[str, str], Path, Path, dict[Path, bytes]]:
    fake_bin = tmp_path / "bin"
    fake_home = tmp_path / "home"
    launch_agents = fake_home / "Library" / "LaunchAgents"
    fake_bin.mkdir()
    launch_agents.mkdir(parents=True)

    coordinator = launch_agents / "com.pantheon.agy-gemini-coordinator.plist"
    coordinator.write_bytes(plistlib.dumps(_coordinator_plist()))
    lane_contents: dict[Path, bytes] = {}
    for lane in ("new", "rewrite", "i18n-new", "i18n-rewrite"):
        path = launch_agents / f"com.pantheon.agy-gemini-{lane}.plist"
        content = f"unchanged-{lane}\n".encode()
        path.write_bytes(content)
        lane_contents[path] = content

    dscl = fake_bin / "dscl"
    dscl.write_text(
        f"#!/bin/sh\nprintf '%s\\n' 'NFSHomeDirectory: {fake_home}'\n",
        encoding="utf-8",
    )
    dscl.chmod(0o700)

    launchctl_log = tmp_path / "launchctl.log"
    bootstrap_count = tmp_path / "bootstrap-count"
    launchctl = fake_bin / "launchctl"
    launchctl.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$*\" >> '{launchctl_log}'\n"
        f"if [ \"$1\" = print ]; then exit {0 if loaded else 1}; fi\n"
        "if [ \"$1\" = bootstrap ]; then\n"
        f"  count=$(cat '{bootstrap_count}' 2>/dev/null || printf 0)\n"
        "  count=$((count + 1))\n"
        f"  printf '%s\\n' \"$count\" > '{bootstrap_count}'\n"
        f"  if [ \"$count\" -eq 1 ]; then exit {1 if fail_first_bootstrap else 0}; fi\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)

    env = os.environ.copy()
    env.update(
        {
            "PANTHEON_PYTHON_PATH": sys.executable,
            "PATH": f"{fake_bin}:/usr/bin:/bin",
            "TMPDIR": str(tmp_path),
        }
    )
    return env, coordinator, launchctl_log, lane_contents


@pytest.mark.parametrize("loaded", [False, True])
def test_cutover_script_preserves_runtime_state_and_lane_plists(
    tmp_path: Path,
    loaded: bool,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env, coordinator, launchctl_log, lane_contents = _cutover_runtime(
        tmp_path,
        loaded=loaded,
    )

    completed = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/cutover_agy_gemini_reviewer_launchd.sh"),
            "gemini-3.5-flash",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    installed = plistlib.loads(coordinator.read_bytes())
    variables = installed["EnvironmentVariables"]
    assert variables["AGY_WRITER_MODEL"] == "gemini-writer-stable"
    assert variables["AGY_REVIEWER_MODEL"] == "gemini-3.5-flash"
    for path, content in lane_contents.items():
        assert path.read_bytes() == content

    control_calls = launchctl_log.read_text(encoding="utf-8").splitlines()
    assert control_calls[0] == "print gui/501/com.pantheon.agy-gemini-coordinator"
    if loaded:
        assert [call.split()[0] for call in control_calls] == [
            "print",
            "bootout",
            "bootstrap",
        ]
    else:
        assert [call.split()[0] for call in control_calls] == ["print"]


def test_cutover_script_rolls_back_when_bootstrap_fails(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env, coordinator, launchctl_log, lane_contents = _cutover_runtime(
        tmp_path,
        loaded=True,
        fail_first_bootstrap=True,
    )
    original = coordinator.read_bytes()

    completed = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/cutover_agy_gemini_reviewer_launchd.sh"),
            "gemini-3.5-flash",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert coordinator.read_bytes() == original
    for path, content in lane_contents.items():
        assert path.read_bytes() == content
    assert [call.split()[0] for call in launchctl_log.read_text().splitlines()] == [
        "print",
        "bootout",
        "bootstrap",
        "bootout",
        "bootstrap",
    ]
