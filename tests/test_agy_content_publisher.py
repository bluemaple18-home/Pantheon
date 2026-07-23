from __future__ import annotations

import json
import plistlib
from pathlib import Path
import subprocess

import pytest

from scripts import agy_content_publisher as publisher
from scripts.agy_seo_copy_pipeline import article_sha256


def _long(text: str) -> str:
    value = text
    while len(value) < 96:
        value += "再核對一項具體資料，避免把通用描述當成個人結論。"
    return value[:108]


def make_publishable_article(article_id: str = "AUTO-001") -> dict[str, object]:
    keyword = "測試關鍵字"
    paragraphs = [_long(f"{keyword}在第{index + 1}個場景中，先整理事實、限制與可行選項。") for index in range(15)]
    return {
        "id": article_id,
        "section": "mbti",
        "product": "personality",
        "slug": article_id.lower(),
        "serial": "personality-9999",
        "urlSlug": f"{article_id.lower()}-9999",
        "primaryKeyword": keyword,
        "secondaryKeywords": ["具體場景", "通用觀察"],
        "title": "測試關鍵字是什麼？用生活場景理解限制與選擇",
        "description": "測試關鍵字適合整理具體情境、可觀察行動與使用限制；本文只提供通用理解，不替個人下結論，也不承諾任何結果，仍需回到現況判斷與實際資料再做選擇。",
        "answer": "測試關鍵字提供通用觀察，不能替個人下結論。",
        "tags": ["AEO", "GEO", "Pantheon", "SEO", "公開文章", "繁體中文", "通用知識", "人格", "自我理解"],
        "published": "2026-07-23",
        "updated": "2026-07-23",
        "faq": [
            {"question": "測試關鍵字能直接判定結果嗎？", "answer": "不能，仍要回到實際情境與行動。"},
            {"question": "應該先看什麼？", "answer": "先分開記錄事實、推測與期待。"},
            {"question": "什麼時候不適用？", "answer": "需要專業判斷時不應只靠這篇文章。"},
        ],
        "bodySections": [
            {"heading": f"測試關鍵字的觀察角度 {section + 1}", "paragraphs": paragraphs[section * 3 : section * 3 + 3]}
            for section in range(5)
        ],
    }


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def _write_run(queue_root: Path, run_dir: Path, article: dict[str, object], verdict: str = "APPROVE") -> None:
    candidate = {"schema_version": 1, "run_id": run_dir.name, "mode": "create", "articles": [article]}
    review = {
        "schema_version": 1,
        "run_id": run_dir.name,
        "articles": [
            {
                "article_id": article["id"],
                "candidate_sha256": article_sha256(article),
                "verdict": verdict,
                "hard_failure": verdict != "APPROVE",
                "findings": [] if verdict == "APPROVE" else [{"code": "reject", "message": "退件"}],
            }
        ],
    }
    _write_json(run_dir / "candidate.json", candidate)
    _write_json(run_dir / "review.json", review)
    _write_json(
        queue_root / "runs" / f"{run_dir.name}.json",
        {
            "schema_version": 1,
            "run_id": run_dir.name,
            "run_dir": str(run_dir),
            "status": "complete",
            "result": {"status": "complete", "run_id": run_dir.name, "candidate": str(run_dir / "candidate.json")},
        },
    )


def _minimal_article_static(repo_root: Path) -> None:
    static = repo_root / "app" / "web" / "static"
    static.mkdir(parents=True)
    (static / "article-registry.js").write_text(
        'export const ARTICLE_REGISTRY = [\n];\nfunction listArticleRecords() { return []; }\n',
        encoding="utf-8",
    )
    (static / "article-meta.js").write_text('const ARTICLE_BODY_LIBRARY = {\n};\n', encoding="utf-8")
    tests = repo_root / "tests"
    tests.mkdir()
    (tests / "test_web.py").write_text(
        'ARTICLE_CACHE_TOKEN = "old-token"\n\n'
        "DAILY_PUBLIC_ARTICLE_PATHS = [\n"
        "]\n\n"
        "PUBLIC_ARTICLE_PATHS = [\n"
        "    *DAILY_PUBLIC_ARTICLE_PATHS,\n"
        "]\n",
        encoding="utf-8",
    )


def test_collect_ready_runs_skips_reviewer_reject(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    run_dir = tmp_path / "runs" / "run-rejected"
    _write_run(queue_root, run_dir, make_publishable_article(), verdict="REJECT")

    ready = publisher.collect_ready_runs(queue_root, tmp_path / "state")

    assert ready == []
    ledger = json.loads((tmp_path / "state" / "ledger.json").read_text(encoding="utf-8"))
    assert ledger["quarantined_runs"][0]["reason"] == "reviewer did not cleanly approve every article"


def test_publish_ready_runs_applies_approved_candidate_without_push(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path
    queue_root = tmp_path / "queue"
    state_root = tmp_path / ".work" / "content-publisher"
    _minimal_article_static(repo_root)
    (repo_root / "pyproject.toml").write_text('[project]\nversion = "0.3.0"\n', encoding="utf-8")
    (repo_root / "package.json").write_text('{"version":"0.3.0"}\n', encoding="utf-8")
    (repo_root / "CHANGELOG.md").write_text(
        "# Pantheon Release Log\n\n## [0.3.0] - 2026-07-23\n\n- Release tag：`v0.3.0`\n- 公開文章總數：353\n- 發布範圍：測試。\n- 驗證：測試。\n- 證據：`test`\n",
        encoding="utf-8",
    )
    article = make_publishable_article()
    run_dir = tmp_path / "runs" / "run-approved"
    _write_run(queue_root, run_dir, article)
    monkeypatch.setattr(publisher.pipeline, "_registry_inventory", lambda _repo: [])
    monkeypatch.setattr(publisher, "_run_prerender", lambda _repo: None)
    monkeypatch.setattr(publisher, "_run_feed", lambda _repo: None)
    git_calls: list[list[str]] = []

    def fake_git(_repo_root: Path, args: list[str], _input_text: str | None = None) -> str:
        git_calls.append(args)
        if args == ["status", "--porcelain"]:
            return ""
        if args == ["rev-parse", "HEAD"] or args == ["rev-parse", "origin/main"]:
            return "a" * 40
        if args == ["rev-parse", "HEAD"]:
            return "b" * 40
        return ""

    result = publisher.publish_ready_runs(repo_root, queue_root, state_root, git=fake_git, push=False, run_tests=False, release_gate=False)

    assert result["status"] == "PUBLISHED"
    assert result["version"] == "0.3.1"
    assert (repo_root / "app/web/static/article-expansion-agy-run-approved.js").exists()
    assert (run_dir / "approval.json").exists()
    assert ["push", "origin", "HEAD:main", "v0.3.1"] not in git_calls
    assert "## [0.3.1]" in (repo_root / "CHANGELOG.md").read_text(encoding="utf-8")


def test_publish_blocks_when_head_differs_from_origin(tmp_path: Path) -> None:
    def fake_git(_repo_root: Path, args: list[str], _input_text: str | None = None) -> str:
        if args == ["status", "--porcelain"]:
            return ""
        if args == ["fetch", "origin", "main"]:
            return ""
        if args == ["rev-parse", "HEAD"]:
            return "a" * 40
        if args == ["rev-parse", "origin/main"]:
            return "b" * 40
        return ""

    with pytest.raises(publisher.PublishBlocked, match="local HEAD differs"):
        publisher.publish_ready_runs(tmp_path, tmp_path / "queue", tmp_path / "state", git=fake_git, run_tests=False, release_gate=False)


def test_launchd_template_runs_content_publisher_and_installer_is_valid_shell() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    plist = plistlib.loads((repo_root / "ops/launchd/com.pantheon.agy-content-publisher.plist.example").read_bytes())
    arguments = plist["ProgramArguments"]

    assert arguments[1:3] == ["-m", "scripts.agy_content_publisher"]
    assert arguments[3:11] == [
        "--repo-root",
        "__REPO_ROOT__",
        "--queue-root",
        "__QUEUE_ROOT__",
        "--state-root",
        "__REPO_ROOT__/.work/content-publisher",
        "--max-runs",
        "__MAX_RUNS__",
    ]
    assert arguments[-1] == "--push"
    assert plist["EnvironmentVariables"]["PATH"] == "__PATH__"
    completed = subprocess.run(
        ["bash", "-n", "scripts/install_agy_content_publisher_launchd.sh"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_sync_web_test_release_fixture_updates_cache_token_and_paths(tmp_path: Path) -> None:
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    (test_dir / "test_web.py").write_text(
        'ARTICLE_CACHE_TOKEN = "old-token"\n\n'
        "DAILY_PUBLIC_ARTICLE_PATHS = [\n"
        '    "/articles/astrology/astrology-0115",\n'
        "]\n\n"
        "PUBLIC_ARTICLE_PATHS = [\n"
        "    *DAILY_PUBLIC_ARTICLE_PATHS,\n"
        "]\n",
        encoding="utf-8",
    )
    article = make_publishable_article("AUTO-NEW")
    article["serial"] = "astrology-0139"
    article["urlSlug"] = "astrology-0139"

    publisher._sync_web_test_release_fixture(tmp_path, cache_token="new-token", articles=[article])
    text = (test_dir / "test_web.py").read_text(encoding="utf-8")

    assert 'ARTICLE_CACHE_TOKEN = "new-token"' in text
    assert '    "/articles/astrology/astrology-0139",\n' in text
