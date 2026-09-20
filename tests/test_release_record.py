import subprocess

import pytest

from scripts import check_release_record as release_record

from scripts.check_release_record import (
    ReleaseContractError,
    is_article_release_path,
    release_section,
    semantic_version,
)


def test_semantic_version_requires_three_numeric_parts() -> None:
    assert semantic_version("0.2.0") == (0, 2, 0)
    with pytest.raises(ReleaseContractError):
        semantic_version("2026.07")


def test_release_section_requires_latest_complete_record() -> None:
    changelog = """# Log

## [0.2.0] - 2026-07-20

- Release tag：`v0.2.0`
- 公開文章總數：352
- 發布範圍：新增文章。
- 驗證：tests passed。
- 證據：`artifacts/evidence/`
"""
    assert "公開文章總數：352" in release_section(changelog, "0.2.0")
    with pytest.raises(ReleaseContractError):
        release_section(changelog, "0.3.0")


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("app/web/static/article-expansion-50e-astro.js", True),
        ("app/web/static/article-registry.js", True),
        ("app/web/seo/articles/astrology/astrology-0114/index.html", True),
        ("app/web/static/article.js", False),
        ("docs/pantheon_deployment_workflow.md", False),
    ],
)
def test_article_release_path_scope(path: str, expected: bool) -> None:
    assert is_article_release_path(path) is expected


def test_release_git_helpers_pass_inherited_runtime_work_lease(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[dict[str, object]] = []

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        observed.append(kwargs)
        stdout: str | bytes = "ok\n" if kwargs.get("text") else b"payload"
        return subprocess.CompletedProcess(args, 0, stdout, b"" if isinstance(stdout, bytes) else "")

    monkeypatch.setattr(release_record.formal_runtime, "runtime_work_pass_fds", lambda: (77,))
    monkeypatch.setattr(release_record.subprocess, "run", fake_run)

    assert release_record.run_git("status") == "ok"
    assert release_record.file_at("HEAD", "pyproject.toml") == b"payload"
    assert [item.get("pass_fds") for item in observed] == [(77,), (77,)]
