from __future__ import annotations

import json
import plistlib
from pathlib import Path
import subprocess

import pytest

from scripts import agy_content_publisher as publisher
from scripts.agy_seo_copy_pipeline import article_sha256, body_sha256


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


def make_rewrite_article(article_id: str = "LEGACY-001", slug: str = "legacy-001") -> dict[str, object]:
    body_sections = [
        {
            "heading": f"舊文重寫段落 {section + 1}",
            "paragraphs": [_long(f"這是第{section + 1}段第{index + 1}則舊文重寫內容，保留原主題但改成更貼近使用者的說法。") for index in range(3)],
        }
        for section in range(5)
    ]
    return {
        "article_id": article_id,
        "identity": {
            "id": article_id,
            "product": "astrology",
            "category": "astrology",
            "serial": "astrology-0001",
            "slug": slug,
            "primaryKeyword": "舊文測試",
            "title": "舊文測試標題",
        },
        "current_body_sha256": body_sha256([{"heading": "舊內容", "paragraphs": [_long("舊文原始內容。")]}]),
        "bodySections": body_sections,
    }


def _write_rewrite_run(queue_root: Path, run_dir: Path, article: dict[str, object], verdict: str = "APPROVE") -> None:
    candidate = {"schema_version": 1, "run_id": run_dir.name, "mode": "rewrite_existing_body", "articles": [article]}
    review = {
        "schema_version": 1,
        "run_id": run_dir.name,
        "articles": [
            {
                "article_id": article["article_id"],
                "candidate_sha256": article_sha256(article),
                "verdict": verdict,
                "hard_failure": verdict != "APPROVE",
                "findings": [] if verdict == "APPROVE" else [{"code": "reject", "message": "退件"}],
            }
        ],
    }
    brief = {
        "schema_version": 1,
        "run_id": run_dir.name,
        "mode": "rewrite_existing_body",
        "articles": [
            {
                "slot": "article-01",
                "article_id": article["article_id"],
                "identity": article["identity"],
                "immutable_fields": {
                    **article["identity"],
                    "description": "原 description",
                    "answer": "原 answer",
                    "faq": [{"question": "原問題？", "answer": "原回答。"}],
                    "tags": ["測試"],
                    "published": "2026-07-01",
                    "updated": "2026-07-01",
                    "urlSlug": article["identity"]["slug"],
                    "canonical_path": f"/articles/astrology/{article['identity']['slug']}",
                    "source_file": "app/web/static/article-meta.js",
                },
                "current_body": [{"heading": "舊內容", "paragraphs": [_long("舊文原始內容。")]}],
                "current_body_sha256": article["current_body_sha256"],
                "rewrite_brief": ["改得更口語，但保留使用者情境與限制。"],
                "source_file": "app/web/static/article-meta.js",
                "body_source": "ARTICLE_BODY_LIBRARY",
            }
        ],
    }
    _write_json(run_dir / "candidate.json", candidate)
    _write_json(run_dir / "review.json", review)
    _write_json(run_dir / "brief.json", brief)
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


def _write_active_rewrite_run(queue_root: Path, run_dir: Path, article: dict[str, object]) -> None:
    brief = {
        "schema_version": 1,
        "run_id": run_dir.name,
        "mode": "rewrite_existing_body",
        "articles": [
            {
                "slot": "article-01",
                "article_id": article["article_id"],
                "identity": article["identity"],
                "immutable_fields": {
                    **article["identity"],
                    "description": "原 description",
                    "answer": "原 answer",
                    "faq": [{"question": "原問題？", "answer": "原回答。"}],
                    "tags": ["測試"],
                    "published": "2026-07-01",
                    "updated": "2026-07-01",
                    "urlSlug": article["identity"]["slug"],
                },
                "current_body": [{"heading": "舊內容", "paragraphs": [_long("舊文原始內容。")]}],
                "current_body_sha256": article["current_body_sha256"],
                "rewrite_brief": ["改得更口語，但保留使用者情境與限制。"],
                "source_file": "app/web/static/article-meta.js",
                "body_source": "ARTICLE_BODY_LIBRARY",
            }
        ],
    }
    _write_json(run_dir / "brief.json", brief)
    _write_json(
        queue_root / "runs" / f"{run_dir.name}.json",
        {
            "schema_version": 1,
            "run_id": run_dir.name,
            "run_dir": str(run_dir),
            "status": "active",
            "last_job_id": "pending-job",
        },
    )


def _write_active_create_run(queue_root: Path, run_dir: Path, article_id: str = "V2-NEW-001") -> None:
    _write_json(
        run_dir / "brief.json",
        {
            "schema_version": 1,
            "run_id": run_dir.name,
            "mode": "create",
            "articles": [{"target": {"id": article_id}}],
        },
    )
    _write_json(
        queue_root / "runs" / f"{run_dir.name}.json",
        {
            "schema_version": 1,
            "run_id": run_dir.name,
            "run_dir": str(run_dir),
            "status": "active",
            "last_job_id": "pending-create-job",
        },
    )


def _minimal_article_static(repo_root: Path) -> None:
    static = repo_root / "app" / "web" / "static"
    static.mkdir(parents=True)
    (static / "article-registry.js").write_text(
        'export const ARTICLE_REGISTRY = [\n];\nfunction listArticleRecords() { return []; }\n',
        encoding="utf-8",
    )
    (static / "article-meta.js").write_text(
        "const ARTICLE_BODY_LIBRARY = {\n};\n\n"
        "export function buildArticleContent() {\n"
        '  const article = { slug: "legacy-001" };\n'
        "  const customBody = ARTICLE_BODY_LIBRARY[article.slug];\n"
        "  return customBody;\n"
        "}\n",
        encoding="utf-8",
    )
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


def test_collect_ready_translation_runs_keeps_reject_deferred_without_blocking_approve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    queue_root = tmp_path / "queue"
    for locale, verdict in [("en", "APPROVE"), ("ja", "REJECT")]:
        run_id = f"translate-{locale}"
        run_dir = tmp_path / "runs" / run_id
        article = {
            "article_id": f"AUTO-001:{locale}",
            "locale": locale,
            "source_article_id": "AUTO-001",
        }
        _write_json(
            run_dir / "brief.json",
            {
                "schema_version": 1,
                "run_id": run_id,
                "mode": "translate_existing",
                "articles": [{"source_article_id": "AUTO-001", "source_sha256": "same"}],
            },
        )
        _write_json(run_dir / "candidate.json", {"run_id": run_id, "mode": "translate_existing", "articles": [article]})
        _write_json(
            run_dir / "review.json",
            {
                "run_id": run_id,
                "articles": [
                    {
                        "article_id": article["article_id"],
                        "verdict": verdict,
                        "hard_failure": verdict != "APPROVE",
                        "findings": [] if verdict == "APPROVE" else [{"code": "reject", "message": "退件"}],
                    }
                ],
            },
        )
        _write_json(
            queue_root / "runs" / f"{run_id}.json",
            {
                "schema_version": 1,
                "run_id": run_id,
                "run_dir": str(run_dir),
                "status": "complete",
                "result": {"candidate": str(run_dir / "candidate.json")},
            },
        )
    monkeypatch.setattr(publisher.multilingual, "validate_translation_candidate", lambda _brief, _candidate: None)
    monkeypatch.setattr(publisher.pipeline, "validate_review", lambda _review, _articles: None)
    monkeypatch.setattr(publisher.multilingual, "translation_findings", lambda _brief, _articles: [])
    monkeypatch.setattr(publisher.multilingual, "load_source_article", lambda _repo, _article_id: {"source": "same"})
    monkeypatch.setattr(publisher.multilingual, "source_sha256", lambda _source: "same")

    state_root = tmp_path / "state"
    assert publisher.collect_ready_runs(queue_root, state_root, limit=10) == []
    ready = publisher.collect_ready_translation_runs(tmp_path, queue_root, state_root, limit=10)

    assert [state["run_id"] for state, _, _, _ in ready] == ["translate-en"]
    ledger = json.loads((state_root / "ledger.json").read_text(encoding="utf-8"))
    assert ledger["translation_deferred_runs"][0]["run_id"] == "translate-ja"
    assert ledger["quarantined_runs"] == []


def test_translation_gate_failure_restores_clean_repo_and_preserves_candidate_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = tmp_path / "repo"
    run_dir = tmp_path / "runs" / "translate-ko"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "publisher-state"
    static = repo_root / "app/web/static"
    tests_dir = repo_root / "tests"
    static.mkdir(parents=True)
    tests_dir.mkdir()
    run_dir.mkdir(parents=True)
    (static / "article-locales.js").write_text("export const ARTICLE_LOCALE_REGISTRY = [];\n", encoding="utf-8")
    (repo_root / "app/web/article.html").write_text(
        '<script type="module" src="static/article.js?v=old-token"></script>\n',
        encoding="utf-8",
    )
    (tests_dir / "test_web.py").write_text('ARTICLE_CACHE_TOKEN = "old-token"\n', encoding="utf-8")
    (repo_root / "pyproject.toml").write_text('[project]\nversion = "0.3.58"\n', encoding="utf-8")
    (repo_root / "package.json").write_text('{"version":"0.3.58"}\n', encoding="utf-8")
    (repo_root / "CHANGELOG.md").write_text(
        "# Pantheon Release Log\n\n## [0.3.58] - 2026-07-24\n\n- baseline\n",
        encoding="utf-8",
    )
    candidate = {
        "run_id": "translate-ko",
        "articles": [{"article_id": "AUTO-001:ko", "source_article_id": "AUTO-001", "locale": "ko"}],
    }
    _write_json(
        run_dir / "brief.json",
        {"run_id": "translate-ko", "mode": "translate_existing", "articles": []},
    )
    _write_json(run_dir / "candidate.json", candidate)
    state = {"run_id": "translate-ko", "run_dir": str(run_dir)}
    _write_json(
        queue_root / "runs" / "translate-ko.json",
        {**state, "status": "complete", "result": {"candidate": str(run_dir / "candidate.json")}},
    )
    subprocess.run(["git", "init", "-q"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.email", "publisher-test@example.invalid"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.name", "Publisher Test"], cwd=repo_root, check=True)
    subprocess.run(["git", "add", "."], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=repo_root, check=True)
    base_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    monkeypatch.setattr(publisher, "_assert_clean_origin_head", lambda _repo, _git: base_sha)
    monkeypatch.setattr(
        publisher,
        "collect_ready_translation_runs",
        lambda *_args, **_kwargs: [(state, {"run_id": "translate-ko"}, candidate, {"run_id": "translate-ko"})],
    )

    def apply_translation(repo: Path, run: Path, _approver: str) -> list[Path]:
        run_id = run.name
        _write_json(run / "approval.json", {"run_id": run_id, "status": "approved"})
        module = repo / f"app/web/static/article-locale-{run_id}.js"
        module.write_text("export const KO = [];\n", encoding="utf-8")
        manifest = repo / "app/web/static/article-locales.js"
        manifest.write_text(f"import './article-locale-{run_id}.js';\n", encoding="utf-8")
        return [module, manifest]

    monkeypatch.setattr(publisher.multilingual, "approve_and_apply_translation_run", apply_translation)
    monkeypatch.setattr(publisher, "_public_article_count", lambda _repo: 440)
    monkeypatch.setattr(publisher, "_run_prerender", lambda _repo: None)
    monkeypatch.setattr(publisher, "_run_feed", lambda _repo: None)
    monkeypatch.setattr(
        publisher,
        "_run_checked",
        lambda _repo, args: (_ for _ in ()).throw(subprocess.CalledProcessError(1, args)),
    )

    result = publisher.publish_ready_translation_runs(
        repo_root,
        queue_root,
        state_root,
        run_tests=True,
        release_gate=True,
    )

    assert result["status"] == "failed_recovered"
    assert result["error_type"] == "CalledProcessError"
    assert subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout == ""
    assert (run_dir / "candidate.json").is_file()
    assert (run_dir / "approval.json").is_file()
    assert (queue_root / "runs" / "translate-ko.json").is_file()
    failure = json.loads(Path(str(result["evidence"])).read_text(encoding="utf-8"))
    assert failure["base_sha"] == base_sha
    assert failure["run_ids"] == ["translate-ko"]
    assert failure["repo_recovered"] is True
    assert failure["retry_status"] == "candidate_preserved"

    next_run_dir = tmp_path / "runs" / "translate-en"
    next_run_dir.mkdir()
    next_candidate = {
        "run_id": "translate-en",
        "articles": [{"article_id": "AUTO-002:en", "source_article_id": "AUTO-002", "locale": "en"}],
    }
    _write_json(next_run_dir / "candidate.json", next_candidate)
    next_state = {"run_id": "translate-en", "run_dir": str(next_run_dir)}
    monkeypatch.setattr(
        publisher,
        "collect_ready_translation_runs",
        lambda *_args, **_kwargs: [(next_state, {"run_id": "translate-en"}, next_candidate, {"run_id": "translate-en"})],
    )
    monkeypatch.setattr(publisher, "_run_checked", lambda _repo, _args: None)

    next_result = publisher.publish_ready_translation_runs(
        repo_root,
        queue_root,
        state_root,
        run_tests=True,
        release_gate=False,
    )

    assert next_result["status"] == "PUBLISHED_TRANSLATION"
    assert next_result["run_ids"] == ["translate-en"]
    assert (next_run_dir / "approval.json").is_file()


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
    seeded: list[tuple[str, str]] = []
    monkeypatch.setattr(
        publisher.multilingual,
        "enqueue_article_translations",
        lambda _repo, _queue, *, source_run_id, article_id: seeded.append((source_run_id, article_id))
        or [{"run_id": f"{article_id}-en", "locale": "en", "run_dir": "/tmp/en"}],
    )
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
    assert seeded == [("run-approved", "AUTO-001")]
    ledger = json.loads((state_root / "ledger.json").read_text(encoding="utf-8"))
    assert ledger["published_runs"][0]["translation_seed_status"] == "seeded"
    assert ledger["published_runs"][0]["translation_run_ids"] == ["AUTO-001-en"]


def test_collect_ready_rewrite_runs_ignores_create_quarantine_and_reject(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    approved = make_rewrite_article("LEGACY-APPROVED", "legacy-approved")
    rejected = make_rewrite_article("LEGACY-REJECTED", "legacy-rejected")
    _write_rewrite_run(queue_root, tmp_path / "runs" / "rewrite-approved", approved)
    _write_rewrite_run(queue_root, tmp_path / "runs" / "rewrite-rejected", rejected, verdict="REJECT")
    _write_json(
        state_root / "ledger.json",
        {
            "schema_version": 1,
            "published_runs": [],
            "quarantined_runs": [{"run_id": "rewrite-approved", "reason": "publisher only supports create mode"}],
        },
    )
    monkeypatch.setattr(publisher.pipeline, "rewrite_aggregate_findings", lambda _brief, _articles: ([], []))

    ready = publisher.collect_ready_rewrite_runs(queue_root, state_root, limit=10)

    assert [state["run_id"] for state, _, _, _ in ready] == ["rewrite-approved"]


def test_collect_ready_rewrite_runs_skips_non_legacy_articles(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    _write_rewrite_run(queue_root, tmp_path / "runs" / "rewrite-newer", make_rewrite_article("NEW-AUTO-001", "new-auto-001"))
    monkeypatch.setattr(publisher.pipeline, "rewrite_aggregate_findings", lambda _brief, _articles: ([], []))

    ready = publisher.collect_ready_rewrite_runs(queue_root, state_root, limit=10, allowed_article_ids={"LEGACY-001"})

    assert ready == []


def test_publish_ready_rewrite_runs_quarantines_identity_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    article = make_rewrite_article("LEGACY-001", "legacy-001")
    _write_rewrite_run(queue_root, tmp_path / "runs" / "rewrite-drift", article)
    _write_json(
        state_root / "ledger.json",
        {
            "schema_version": 1,
            "published_runs": [],
            "quarantined_runs": [{"run_id": "rewrite-drift", "reason": "publisher only supports create mode"}],
            "rewrite_released_runs": [],
        },
    )

    def fake_git(_repo_root: Path, args: list[str], _input_text: str | None = None) -> str:
        if args == ["status", "--porcelain"]:
            return ""
        if args == ["rev-parse", "HEAD"] or args == ["rev-parse", "origin/main"]:
            return "a" * 40
        return ""

    monkeypatch.setattr(publisher.pipeline, "rewrite_aggregate_findings", lambda _brief, _articles: ([], []))
    monkeypatch.setattr(publisher, "legacy_article_records", lambda _repo: [{"id": "LEGACY-001", "serial": "astrology-0001", "articleCategory": "astrology"}])
    monkeypatch.setattr(
        publisher.pipeline,
        "_existing_rewrite_inventory",
        lambda _repo: {
            "LEGACY-001": {
                "record": {
                    "id": "LEGACY-001",
                    "product": "astrology",
                    "articleCategory": "astrology",
                    "serial": "astrology-0001",
                    "urlSlug": "legacy-001",
                    "primaryKeyword": "舊文測試",
                    "title": "已變動的舊文標題",
                },
                "currentBody": [{"heading": "舊內容", "paragraphs": [_long("舊文原始內容。")]}],
            }
        },
    )

    result = publisher.publish_ready_rewrite_runs(
        tmp_path,
        queue_root,
        state_root,
        git=fake_git,
        run_tests=False,
        release_gate=False,
    )

    assert result["status"] == "idle"
    assert result["legacy_rewrite_backlog"]["quarantined"] == 1
    ledger = json.loads((state_root / "ledger.json").read_text(encoding="utf-8"))
    assert ledger["quarantined_runs"][-1]["run_id"] == "rewrite-drift"
    assert ledger["quarantined_runs"][-1]["reason"] == "rewrite identity drift for LEGACY-001"


def test_legacy_rewrite_backlog_blocks_reject_repair_until_all_legacy_attempted(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    rejected = make_rewrite_article("LEGACY-REJECTED", "legacy-rejected")
    _write_rewrite_run(queue_root, tmp_path / "runs" / "rewrite-rejected", rejected, verdict="REJECT")
    legacy_records = [
        {"id": "LEGACY-REJECTED", "serial": "astrology-0001", "articleCategory": "astrology"},
        {"id": "LEGACY-UNATTEMPTED", "serial": "astrology-0002", "articleCategory": "astrology"},
    ]

    summary = publisher.summarize_legacy_rewrite_backlog(
        queue_root,
        state_root,
        allowed_article_ids={"LEGACY-REJECTED", "LEGACY-UNATTEMPTED"},
        legacy_records=legacy_records,
    )

    assert summary["clean_approve"] == 0
    assert summary["reject"] == 1
    assert summary["attempted"] == 1
    assert summary["unattempted"] == 1
    assert summary["unattempted_articles"][0]["serial"] == "astrology-0002"
    assert summary["repair_rejects_allowed"] is False


def test_legacy_rewrite_backlog_counts_active_runs_as_attempted(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    rejected = make_rewrite_article("LEGACY-REJECTED", "legacy-rejected")
    active = make_rewrite_article("LEGACY-ACTIVE", "legacy-active")
    _write_rewrite_run(queue_root, tmp_path / "runs" / "rewrite-rejected", rejected, verdict="REJECT")
    _write_active_rewrite_run(queue_root, tmp_path / "runs" / "rewrite-active", active)
    legacy_records = [
        {"id": "LEGACY-REJECTED", "serial": "astrology-0001", "articleCategory": "astrology"},
        {"id": "LEGACY-ACTIVE", "serial": "astrology-0002", "articleCategory": "astrology"},
    ]

    summary = publisher.summarize_legacy_rewrite_backlog(
        queue_root,
        state_root,
        allowed_article_ids={"LEGACY-REJECTED", "LEGACY-ACTIVE"},
        legacy_records=legacy_records,
    )

    assert summary["attempted"] == 2
    assert summary["unattempted"] == 0
    assert summary["active_or_incomplete"] == 1
    assert summary["repair_rejects_allowed"] is False


def test_legacy_rewrite_backlog_ignores_active_create_runs(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    active = make_rewrite_article("LEGACY-ACTIVE", "legacy-active")
    _write_active_rewrite_run(queue_root, tmp_path / "runs" / "rewrite-active", active)
    _write_active_create_run(queue_root, tmp_path / "runs" / "create-active")
    legacy_records = [{"id": "LEGACY-ACTIVE", "serial": "astrology-0001", "articleCategory": "astrology"}]

    summary = publisher.summarize_legacy_rewrite_backlog(
        queue_root,
        state_root,
        allowed_article_ids={"LEGACY-ACTIVE"},
        legacy_records=legacy_records,
    )

    assert summary["attempted"] == 1
    assert summary["unattempted"] == 0
    assert summary["active_or_incomplete"] == 1
    assert summary["non_legacy"] == 0


def test_legacy_rewrite_backlog_allows_reject_repair_after_all_legacy_attempted(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    rejected = make_rewrite_article("LEGACY-REJECTED", "legacy-rejected")
    _write_rewrite_run(queue_root, tmp_path / "runs" / "rewrite-rejected", rejected, verdict="REJECT")
    legacy_records = [{"id": "LEGACY-REJECTED", "serial": "astrology-0001", "articleCategory": "astrology"}]

    summary = publisher.summarize_legacy_rewrite_backlog(
        queue_root,
        state_root,
        allowed_article_ids={"LEGACY-REJECTED"},
        legacy_records=legacy_records,
    )

    assert summary["unattempted"] == 0
    assert summary["repair_rejects_allowed"] is True


def test_legacy_serial_report_uses_pre_automated_gemini_cutoff(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    records = [
        {"id": f"OLD-{index}", "serial": f"astrology-{index:04d}", "articleCategory": "astrology"}
        for index in range(1, publisher.LEGACY_ARTICLE_COUNT_CUTOFF + 1)
    ]
    records.append({"id": "NEW-001", "serial": "astrology-0999", "articleCategory": "astrology"})
    monkeypatch.setattr(publisher.pipeline, "_registry_inventory", lambda _repo: records)

    report = publisher.legacy_serial_report(tmp_path)

    assert report["legacy_article_count"] == publisher.LEGACY_ARTICLE_COUNT_CUTOFF
    assert "astrology-0001" in report["serials_by_category"]["astrology"]
    assert "astrology-0999" not in report["serials_by_category"]["astrology"]


def test_publish_ready_rewrite_runs_applies_body_override_without_push(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    article = make_rewrite_article()
    run_dir = tmp_path / "runs" / "rewrite-approved"
    _write_rewrite_run(queue_root, run_dir, article)
    monkeypatch.setattr(publisher.pipeline, "rewrite_aggregate_findings", lambda _brief, _articles: ([], []))
    monkeypatch.setattr(publisher, "legacy_article_records", lambda _repo: [{"id": "LEGACY-001", "serial": "astrology-0001", "articleCategory": "astrology"}])
    monkeypatch.setattr(
        publisher.pipeline,
        "_existing_rewrite_inventory",
        lambda _repo: {
            "LEGACY-001": {
                "record": {
                    "id": "LEGACY-001",
                    "product": "astrology",
                    "articleCategory": "astrology",
                    "serial": "astrology-0001",
                    "urlSlug": "legacy-001",
                    "primaryKeyword": "舊文測試",
                    "title": "舊文測試標題",
                },
                "currentBody": [{"heading": "舊內容", "paragraphs": [_long("舊文原始內容。")]}],
            }
        },
    )
    monkeypatch.setattr(publisher, "_public_article_count", lambda _repo: 353)
    monkeypatch.setattr(publisher, "_run_prerender", lambda _repo: None)
    monkeypatch.setattr(publisher, "_run_feed", lambda _repo: None)
    git_calls: list[list[str]] = []

    def fake_git(_repo_root: Path, args: list[str], _input_text: str | None = None) -> str:
        git_calls.append(args)
        if args == ["status", "--porcelain"]:
            return ""
        if args == ["rev-parse", "HEAD"] or args == ["rev-parse", "origin/main"]:
            return "a" * 40
        return ""

    result = publisher.publish_ready_rewrite_runs(repo_root, queue_root, state_root, git=fake_git, push=False, run_tests=False, release_gate=False)

    assert result["status"] == "PUBLISHED_REWRITE"
    assert result["public_article_count"] == 353
    modules = list((repo_root / "app/web/static").glob("article-rewrite-agy-rewrite-*.js"))
    assert len(modules) == 1
    meta = (repo_root / "app/web/static/article-meta.js").read_text(encoding="utf-8")
    assert "REWRITE_BODY_OVERRIDES[article.slug] || ARTICLE_BODY_LIBRARY[article.slug]" in meta
    ledger = json.loads((state_root / "ledger.json").read_text(encoding="utf-8"))
    assert ledger["rewrite_released_runs"][0]["run_id"] == "rewrite-approved"
    assert ["push", "origin", "HEAD:main", "v0.3.1"] not in git_calls


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


def test_publish_ready_all_runs_create_then_rewrite_then_translation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, bool, bool, bool]] = []

    def fake_create(
        _repo_root: Path,
        _queue_root: Path,
        _state_root: Path,
        *,
        max_runs: int,
        dry_run: bool,
        push: bool,
        run_tests: bool,
        release_gate: bool,
        git: publisher.GitRunner,
    ) -> dict[str, object]:
        calls.append(("create", push, run_tests, release_gate))
        assert max_runs == 3
        assert dry_run is True
        assert git is publisher.run_git
        return {"schema_version": 1, "status": "idle", "published": 0}

    def fake_rewrite(
        _repo_root: Path,
        _queue_root: Path,
        _state_root: Path,
        *,
        max_runs: int,
        dry_run: bool,
        push: bool,
        run_tests: bool,
        release_gate: bool,
        git: publisher.GitRunner,
    ) -> dict[str, object]:
        calls.append(("rewrite", push, run_tests, release_gate))
        assert max_runs == 3
        assert dry_run is True
        assert git is publisher.run_git
        return {"schema_version": 1, "status": "idle_rejects_only", "rewritten": 0}

    def fake_translation(
        _repo_root: Path,
        _queue_root: Path,
        _state_root: Path,
        *,
        max_runs: int,
        dry_run: bool,
        push: bool,
        run_tests: bool,
        release_gate: bool,
        git: publisher.GitRunner,
    ) -> dict[str, object]:
        calls.append(("translation", push, run_tests, release_gate))
        assert max_runs == 3
        assert dry_run is True
        assert git is publisher.run_git
        return {"schema_version": 1, "status": "idle", "translated": 0}

    monkeypatch.setattr(publisher, "publish_ready_runs", fake_create)
    monkeypatch.setattr(publisher, "publish_ready_rewrite_runs", fake_rewrite)
    monkeypatch.setattr(publisher, "publish_ready_translation_runs", fake_translation)

    result = publisher.publish_ready_all(
        tmp_path,
        tmp_path / "queue",
        tmp_path / "state",
        max_runs=3,
        dry_run=True,
        push=True,
        run_tests=False,
        release_gate=False,
    )

    assert result["status"] == "ok"
    assert calls == [
        ("create", True, False, False),
        ("rewrite", True, False, False),
        ("translation", True, False, False),
    ]


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
    assert arguments[-2:] == ["--include-rewrites", "--push"]
    assert plist["EnvironmentVariables"]["PATH"] == "__PATH__"
    completed = subprocess.run(
        ["bash", "-n", "scripts/install_agy_content_publisher_launchd.sh"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_stage_commit_pushes_release_commit_and_tag_atomically(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_git(_repo_root: Path, args: list[str], _input_text: str | None = None) -> str:
        calls.append(args)
        return "c" * 40 if args == ["rev-parse", "HEAD"] else ""

    monkeypatch.setattr(publisher, "_run_checked", lambda _repo, _args: None)

    publisher._stage_commit_tag_push(
        Path("/synthetic/repo"),
        "0.3.59",
        fake_git,
        push=True,
        release_gate=True,
    )

    assert calls[-1] == ["push", "--atomic", "origin", "HEAD:main", "v0.3.59"]


def test_recovery_removes_unpushed_commit_and_tag_but_preserves_failure_evidence(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    state_root = tmp_path / "state"
    (repo_root / "app/web").mkdir(parents=True)
    article_html = repo_root / "app/web/article.html"
    article_html.write_text("old\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.email", "publisher-test@example.invalid"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.name", "Publisher Test"], cwd=repo_root, check=True)
    subprocess.run(["git", "add", "."], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=repo_root, check=True)
    base_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    article_html.write_text("new\n", encoding="utf-8")
    subprocess.run(["git", "add", "app/web/article.html"], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-qm", "candidate"], cwd=repo_root, check=True)
    subprocess.run(["git", "tag", "-a", "v0.3.59", "-m", "candidate"], cwd=repo_root, check=True)

    evidence = publisher._recover_failed_publish(
        repo_root,
        state_root,
        base_sha=base_sha,
        phase="translation",
        run_ids=["translate-ko"],
        error=subprocess.CalledProcessError(1, ["release-gate"]),
        git=publisher.run_git,
    )

    assert subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip() == base_sha
    assert subprocess.run(
        ["git", "tag", "--list", "v0.3.59"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout == ""
    assert subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout == ""
    failure = json.loads(evidence.read_text(encoding="utf-8"))
    assert failure["removed_local_tags"] == ["v0.3.59"]
    assert failure["repo_recovered"] is True


def _init_recovery_repo(tmp_path: Path) -> tuple[Path, Path, Path, str]:
    repo_root = tmp_path / "repo"
    state_root = tmp_path / "state"
    queue_root = tmp_path / "queue"
    owned = repo_root / "app/web/owned.txt"
    owned.parent.mkdir(parents=True)
    owned.write_bytes(b"base\n")
    (repo_root / "app/web/untouched.txt").write_bytes(b"untouched\n")
    subprocess.run(["git", "init", "-q"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.email", "publisher-test@example.invalid"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.name", "Publisher Test"], cwd=repo_root, check=True)
    subprocess.run(["git", "add", "."], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=repo_root, check=True)
    base_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return repo_root, queue_root, state_root, base_sha


def test_transaction_preserves_owned_change_between_clean_check_and_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root, queue_root, state_root, base_sha = _init_recovery_repo(tmp_path)
    owned = repo_root / "app/web/owned.txt"

    def clean_check(_repo: Path, _git: publisher.GitRunner) -> str:
        owned.write_bytes(b"concurrent-before-mutation\n")
        return base_sha

    monkeypatch.setattr(publisher, "_assert_clean_origin_head", clean_check)

    @publisher._recoverable_publish("create", "published")
    def failing_publish(
        repo: Path,
        _queue: Path,
        _state: Path,
        *,
        git: publisher.GitRunner = publisher.run_git,
        _transaction_base_sha: str | None = None,
        _mutation_journal: publisher.MutationJournal | None = None,
    ) -> dict[str, object]:
        assert _transaction_base_sha == base_sha
        assert _mutation_journal is not None
        _mutation_journal.begin()
        _mutation_journal.capture(
            lambda: (repo / "app/web/owned.txt").write_bytes(b"publisher\n")
        )
        raise RuntimeError("candidate-specific failure")

    with pytest.raises(publisher.PublishBlocked, match="did not restore a clean repo"):
        failing_publish(repo_root, queue_root, state_root)

    assert owned.read_bytes() == b"concurrent-before-mutation\n"
    failure = json.loads(next((state_root / "evidence").glob("failed-create-*/failure.json")).read_text(encoding="utf-8"))
    assert failure["status_after_recovery"] == ["M app/web/owned.txt"]


def test_recovery_never_overwrites_concurrent_post_image_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root, queue_root, state_root, base_sha = _init_recovery_repo(tmp_path)
    owned = repo_root / "app/web/owned.txt"
    monkeypatch.setattr(publisher, "_assert_clean_origin_head", lambda _repo, _git: base_sha)

    @publisher._recoverable_publish("create", "published")
    def failing_publish(
        repo: Path,
        _queue: Path,
        _state: Path,
        *,
        git: publisher.GitRunner = publisher.run_git,
        _transaction_base_sha: str | None = None,
        _mutation_journal: publisher.MutationJournal | None = None,
    ) -> dict[str, object]:
        assert _mutation_journal is not None
        _mutation_journal.begin()
        (repo / "app/web/owned.txt").write_bytes(b"publisher\n")
        _mutation_journal.checkpoint(["app/web/owned.txt"])
        (repo / "app/web/owned.txt").write_bytes(b"concurrent-after-mutation\n")
        raise RuntimeError("candidate-specific failure")

    with pytest.raises(publisher.PublishBlocked, match="did not restore a clean repo"):
        failing_publish(repo_root, queue_root, state_root)

    assert owned.read_bytes() == b"concurrent-after-mutation\n"
    failure = json.loads(next((state_root / "evidence").glob("failed-create-*/failure.json")).read_text(encoding="utf-8"))
    assert failure["concurrent_write_conflicts"] == ["app/web/owned.txt"]


def test_recovery_preserves_concurrent_owned_write_before_unattributed_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root, queue_root, state_root, base_sha = _init_recovery_repo(tmp_path)
    owned = repo_root / "app/web/owned.txt"
    monkeypatch.setattr(publisher, "_assert_clean_origin_head", lambda _repo, _git: base_sha)

    @publisher._recoverable_publish("create", "published")
    def failing_publish(
        repo: Path,
        _queue: Path,
        _state: Path,
        *,
        git: publisher.GitRunner = publisher.run_git,
        _transaction_base_sha: str | None = None,
        _mutation_journal: publisher.MutationJournal | None = None,
    ) -> dict[str, object]:
        assert _mutation_journal is not None
        _mutation_journal.begin()
        (repo / "app/web/owned.txt").write_bytes(b"publisher\n")
        (repo / "app/web/owned.txt").write_bytes(b"concurrent-before-checkpoint\n")
        _mutation_journal.checkpoint(["app/web/owned.txt"])
        raise RuntimeError("candidate-specific failure")

    with pytest.raises(publisher.PublishBlocked, match="did not restore a clean repo"):
        failing_publish(repo_root, queue_root, state_root)

    assert owned.read_bytes() == b"concurrent-before-checkpoint\n"
    failure = json.loads(next((state_root / "evidence").glob("failed-create-*/failure.json")).read_text(encoding="utf-8"))
    assert failure["concurrent_write_conflicts"] == ["app/web/owned.txt"]
    assert failure["repo_recovered"] is False


@pytest.mark.parametrize(
    ("remote_main", "remote_tag", "expected"),
    [
        ("base", "", "rollback"),
        ("candidate", "candidate", "committed"),
        ("candidate", "", "unknown"),
    ],
)
def test_atomic_push_exception_reconciles_remote_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    remote_main: str,
    remote_tag: str,
    expected: str,
) -> None:
    candidate = "c" * 40
    base = "b" * 40
    evidence_dir = tmp_path / "evidence"

    def fake_git(_repo: Path, args: list[str], _input: str | None = None) -> str:
        if args[:2] == ["push", "--atomic"]:
            raise subprocess.CalledProcessError(1, args)
        if args == ["rev-parse", "HEAD"]:
            return candidate
        if args == ["rev-parse", "origin/main"]:
            return candidate if remote_main == "candidate" else base
        if args == ["rev-parse", "refs/agy-publisher-reconcile/v0.3.59^{}"]:
            return candidate if remote_tag == "candidate" else base
        if args[:2] == ["ls-remote", "origin"]:
            return f"{candidate}\trefs/tags/v0.3.59^{{}}\n" if remote_tag == "candidate" else ""
        return ""

    monkeypatch.setattr(publisher, "_run_checked", lambda _repo, _args: None)
    if expected == "rollback":
        with pytest.raises(subprocess.CalledProcessError):
            publisher._stage_commit_tag_push(
                tmp_path,
                "0.3.59",
                fake_git,
                push=True,
                release_gate=False,
                outcome_evidence_dir=evidence_dir,
            )
    elif expected == "unknown":
        with pytest.raises(publisher.PushOutcomeUnknown):
            publisher._stage_commit_tag_push(
                tmp_path,
                "0.3.59",
                fake_git,
                push=True,
                release_gate=False,
                outcome_evidence_dir=evidence_dir,
            )
        unknown = json.loads((evidence_dir / "push-outcome-unknown.json").read_text(encoding="utf-8"))
        assert unknown["status"] == "PUSH_OUTCOME_UNKNOWN"
        assert unknown["remote_main"] == candidate
        assert unknown["remote_tag"] is None
    else:
        assert publisher._stage_commit_tag_push(
            tmp_path,
            "0.3.59",
            fake_git,
            push=True,
            release_gate=False,
            outcome_evidence_dir=evidence_dir,
        ) == candidate


def test_unresolved_push_record_blocks_next_full_publish_before_clean_origin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = "c" * 40
    base = "b" * 40
    state_root = tmp_path / "state"
    evidence_dir = state_root / "evidence" / "publish-0.3.59"

    def fake_git(_repo: Path, args: list[str], _input: str | None = None) -> str:
        if args[:2] == ["push", "--atomic"]:
            raise subprocess.CalledProcessError(1, args)
        if args == ["rev-parse", "HEAD"]:
            return candidate
        if args == ["rev-parse", "origin/main"]:
            return candidate
        if args[:2] == ["ls-remote", "origin"]:
            return ""
        if args == ["rev-parse", "--git-common-dir"]:
            return str(tmp_path / "git-common")
        return ""

    monkeypatch.setattr(publisher, "_run_checked", lambda _repo, _args: None)
    with pytest.raises(publisher.PushOutcomeUnknown):
        publisher._stage_commit_tag_push(
            tmp_path,
            "0.3.59",
            fake_git,
            push=True,
            release_gate=False,
            outcome_evidence_dir=evidence_dir,
            state_root=state_root,
            phase="create",
            run_ids=["run-failed"],
        )

    control_path = publisher._unresolved_push_path(state_root)
    control = json.loads(control_path.read_text(encoding="utf-8"))
    assert control["status"] == "PUSH_OUTCOME_UNKNOWN"
    assert control["candidate_sha"] == candidate
    assert control["remote_main"] == candidate
    assert control["remote_tag"] is None

    clean_origin_called = False

    def fail_if_clean_origin_runs(_repo: Path, _git: publisher.GitRunner) -> str:
        nonlocal clean_origin_called
        clean_origin_called = True
        raise AssertionError("clean-origin must not run while push control is unresolved")

    monkeypatch.setattr(publisher, "_assert_clean_origin_head", fail_if_clean_origin_runs)
    with pytest.raises(publisher.PublishBlocked, match="unresolved push"):
        publisher.publish_ready_runs(
            tmp_path,
            tmp_path / "queue",
            state_root,
            git=fake_git,
            push=False,
            run_tests=False,
            release_gate=False,
        )

    assert clean_origin_called is False
    assert control_path.is_file()
    with pytest.raises(publisher.PublishBlocked, match="remote refs have not converged"):
        publisher._reconcile_unresolved_push(tmp_path, state_root, fake_git)
    assert control_path.is_file()


def test_failed_first_queue_run_is_deferred_and_second_run_remains_publishable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    run_dirs: dict[str, Path] = {}
    states: dict[str, dict[str, object]] = {}
    for index, run_id in enumerate(("run-bad", "run-good"), start=1):
        run_dir = tmp_path / "runs" / run_id
        run_dir.mkdir(parents=True)
        run_dirs[run_id] = run_dir
        _write_json(run_dir / "brief.json", {"run_id": run_id, "mode": "create"})
        _write_json(
            run_dir / "candidate.json",
            {
                "run_id": run_id,
                "mode": "create",
                "articles": [
                    {
                        "id": f"AUTO-{index:03d}",
                        "serial": f"astrology-{index:04d}",
                        "urlSlug": f"queue-{index}",
                        "bodySections": [],
                    }
                ],
            },
        )
        _write_json(run_dir / "review.json", {"run_id": run_id})
        state = {
            "run_id": run_id,
            "run_dir": str(run_dir),
            "status": "complete",
            "result": {"candidate": str(run_dir / "candidate.json")},
        }
        states[run_id] = state
        _write_json(queue_root / "runs" / f"{index:02d}-{run_id}.json", state)

    monkeypatch.setattr(
        publisher,
        "_load_completed_run",
        lambda path: (
            states["run-bad" if "run-bad" in path.name else "run-good"],
            publisher._read_json(run_dirs["run-bad" if "run-bad" in path.name else "run-good"] / "candidate.json"),
            {"run_id": "run-bad" if "run-bad" in path.name else "run-good"},
        ),
    )
    monkeypatch.setattr(publisher, "_review_is_clean_approve", lambda _review: True)
    monkeypatch.setattr(publisher.pipeline, "quality_findings", lambda _articles: [])
    failure_evidence = state_root / "evidence" / "failed-run-bad" / "failure.json"
    _write_json(failure_evidence, {"status": "FAILED_RECOVERED"})
    publisher._record_retry_failure(state_root, "create", ["run-bad"], RuntimeError("bad candidate"), failure_evidence)

    ready = publisher.collect_ready_runs(queue_root, state_root, limit=1)

    assert [state["run_id"] for state, _candidate, _review in ready] == ["run-good"]
    assert (queue_root / "runs" / "01-run-bad.json").is_file()
    assert (run_dirs["run-bad"] / "candidate.json").is_file()
    retry = publisher._read_json(publisher._retry_path(state_root, "create", "run-bad"))
    assert retry["attempts"] == 1
    assert retry["candidate_preserved"] is True

    repo_root = tmp_path / "repo"
    published_path = repo_root / "app/web/published.txt"
    published_path.parent.mkdir(parents=True)
    published_path.write_text("base\n", encoding="utf-8")
    (repo_root / "tests").mkdir()
    (repo_root / "tests/test_web.py").write_text("baseline\n", encoding="utf-8")
    for relative, content in (
        ("pyproject.toml", '[project]\nversion = "0.3.58"\n'),
        ("package.json", '{"version":"0.3.58"}\n'),
        ("CHANGELOG.md", "# changelog\n"),
    ):
        (repo_root / relative).write_text(content, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.email", "publisher-test@example.invalid"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.name", "Publisher Test"], cwd=repo_root, check=True)
    subprocess.run(["git", "add", "."], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=repo_root, check=True)
    base_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    monkeypatch.setattr(publisher, "_assert_clean_origin_head", lambda _repo, _git: base_sha)
    monkeypatch.setattr(publisher, "_seed_pending_translations", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(publisher.pipeline, "build_approval", lambda *_args, **_kwargs: {"status": "approved"})

    def apply_good(repo: Path, *_args: object, **_kwargs: object) -> list[Path]:
        target = repo / "app/web/published.txt"
        target.write_text("run-good\n", encoding="utf-8")
        return [target]

    monkeypatch.setattr(publisher.pipeline, "apply_approved_candidates", apply_good)
    monkeypatch.setattr(publisher, "_bump_patch_version", lambda _repo: "0.3.59")
    monkeypatch.setattr(publisher, "_public_article_count", lambda _repo: 1)
    monkeypatch.setattr(publisher, "_run_prerender", lambda _repo: None)
    monkeypatch.setattr(publisher, "_run_feed", lambda _repo: None)
    monkeypatch.setattr(publisher, "_prepend_changelog", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(publisher, "_sync_web_test_release_fixture", lambda *_args, **_kwargs: repo_root / "tests/test_web.py")
    monkeypatch.setattr(publisher, "_stage_commit_tag_push", lambda *_args, **_kwargs: "d" * 40)

    result = publisher.publish_ready_runs(
        repo_root,
        queue_root,
        state_root,
        max_runs=1,
        push=False,
        run_tests=False,
        release_gate=False,
    )

    assert result["status"] == "PUBLISHED"
    assert result["run_ids"] == ["run-good"]
    assert published_path.read_text(encoding="utf-8") == "run-good\n"


def test_recovery_retry_uses_collector_selected_run_and_leaves_third_publishable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    repo_root = tmp_path / "repo"
    target = repo_root / "app/web/published.txt"
    target.parent.mkdir(parents=True)
    target.write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.email", "publisher-test@example.invalid"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.name", "Publisher Test"], cwd=repo_root, check=True)
    subprocess.run(["git", "add", "."], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=repo_root, check=True)
    base_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    run_ids = ("run-published", "run-failing", "run-healthy")
    completed: dict[str, tuple[dict[str, object], dict[str, object], dict[str, object]]] = {}
    for index, run_id in enumerate(run_ids, start=1):
        run_dir = tmp_path / "runs" / run_id
        run_dir.mkdir(parents=True)
        _write_json(run_dir / "brief.json", {"run_id": run_id, "mode": "create"})
        state = {"run_id": run_id, "run_dir": str(run_dir), "status": "complete"}
        candidate = {
            "run_id": run_id,
            "mode": "create",
            "articles": [
                {
                    "id": f"AUTO-{index:03d}",
                    "serial": f"astrology-{index:04d}",
                    "urlSlug": f"queue-{index}",
                    "bodySections": [],
                }
            ],
        }
        review = {"run_id": run_id, "articles": []}
        completed[run_id] = (state, candidate, review)
        _write_json(queue_root / "runs" / f"{index:02d}-{run_id}.json", state)

    _write_json(
        publisher._ledger_path(state_root),
        {
            **publisher._load_ledger(state_root),
            "published_runs": [
                {
                    "run_id": "run-published",
                    "version": "0.3.58",
                    "commit_sha": base_sha,
                    "published_at": "2026-07-24T00:00:00+08:00",
                }
            ],
        },
    )

    def load_completed(path: Path) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
        run_id = path.stem.split("-", 1)[1]
        return completed[run_id]

    monkeypatch.setattr(publisher, "_load_completed_run", load_completed)
    monkeypatch.setattr(publisher, "_review_is_clean_approve", lambda _review: True)
    monkeypatch.setattr(publisher.pipeline, "quality_findings", lambda _articles: [])
    monkeypatch.setattr(publisher, "_assert_clean_origin_head", lambda _repo, _git: base_sha)
    monkeypatch.setattr(publisher, "_seed_pending_translations", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(publisher.pipeline, "build_approval", lambda *_args, **_kwargs: {"status": "approved"})

    def fail_selected(repo: Path, run_id: str, *_args: object, **_kwargs: object) -> list[Path]:
        assert run_id == "run-failing"
        changed = repo / "app/web/published.txt"
        changed.write_text("run-failing\n", encoding="utf-8")
        raise RuntimeError("selected candidate failed")

    monkeypatch.setattr(publisher.pipeline, "apply_approved_candidates", fail_selected)

    result = publisher.publish_ready_runs(
        repo_root,
        queue_root,
        state_root,
        max_runs=1,
        push=False,
        run_tests=False,
        release_gate=False,
    )

    assert result["status"] == "failed_recovered"
    assert not publisher._retry_path(state_root, "create", "run-published").exists()
    retry = publisher._read_json(publisher._retry_path(state_root, "create", "run-failing"))
    assert retry["run_id"] == "run-failing"
    assert target.read_text(encoding="utf-8") == "base\n"
    failure = json.loads(Path(str(result["evidence"])).read_text(encoding="utf-8"))
    assert failure["run_ids"] == ["run-failing"]

    ready = publisher.collect_ready_runs(queue_root, state_root, limit=1)
    assert [state["run_id"] for state, _candidate, _review in ready] == ["run-healthy"]


@pytest.mark.parametrize(
    "fault",
    ["archive-copy", "update-ref", "restore", "unlink", "tag-delete", "final-evidence-write"],
)
def test_recovery_fault_always_has_pre_cleanup_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    repo_root, _queue_root, state_root, base_sha = _init_recovery_repo(tmp_path)
    owned = repo_root / "app/web/owned.txt"
    owned.write_bytes(b"publisher\n")
    subprocess.run(["git", "add", "."], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-qm", "candidate"], cwd=repo_root, check=True)
    subprocess.run(["git", "tag", "-a", "v0.3.59", "-m", "candidate"], cwd=repo_root, check=True)
    untracked = repo_root / "app/web/untracked.txt"
    untracked.write_bytes(b"untracked\n")

    original_git = publisher.run_git
    original_write_json = publisher._write_json
    original_unlink = Path.unlink

    def fault_git(repo: Path, args: list[str], input_text: str | None = None) -> str:
        operation = (
            "update-ref"
            if args and args[0] == "update-ref"
            else "restore"
            if args and args[0] == "restore"
            else "tag-delete"
            if args[:2] == ["tag", "-d"]
            else ""
        )
        if operation == fault:
            raise subprocess.CalledProcessError(70, ["git", *args])
        return original_git(repo, args, input_text)

    if fault == "archive-copy":
        monkeypatch.setattr(publisher.shutil, "copy2", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("archive fault")))
    if fault == "unlink":
        monkeypatch.setattr(
            Path,
            "unlink",
            lambda self, *args, **kwargs: (_ for _ in ()).throw(OSError("unlink fault"))
            if self == untracked
            else original_unlink(self, *args, **kwargs),
        )
    if fault == "final-evidence-write":
        monkeypatch.setattr(
            publisher,
            "_write_json",
            lambda path, payload: (_ for _ in ()).throw(OSError("evidence fault"))
            if path.name == "failure.json"
            else original_write_json(path, payload),
        )

    with pytest.raises(Exception):
        publisher._recover_failed_publish(
            repo_root,
            state_root,
            base_sha=base_sha,
            phase="create",
            run_ids=["run-bad"],
            error=RuntimeError("publish failed"),
            git=fault_git,
        )

    attempts = list((state_root / "evidence").glob("failed-create-*/failure-attempt.json"))
    assert len(attempts) == 1
    attempt = json.loads(attempts[0].read_text(encoding="utf-8"))
    assert attempt["base_sha"] == base_sha
    assert attempt["run_ids"] == ["run-bad"]
    assert attempt["status_before_recovery"]
    recovery = json.loads(attempts[0].with_name("recovery-result.json").read_text(encoding="utf-8"))
    assert recovery["steps"][-1]["step"] == fault
    assert recovery["steps"][-1]["status"] == "failed"


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


def test_sync_web_test_cache_token_updates_runtime_templates_from_same_token(tmp_path: Path) -> None:
    test_dir = tmp_path / "tests"
    web_dir = tmp_path / "app/web"
    test_dir.mkdir(parents=True)
    web_dir.mkdir(parents=True)
    (test_dir / "test_web.py").write_text('ARTICLE_CACHE_TOKEN = "old-token"\n', encoding="utf-8")
    (web_dir / "article.html").write_text(
        '<script type="module" src="static/article.js?v=old-token"></script>\n',
        encoding="utf-8",
    )
    (web_dir / "articles.html").write_text(
        '<script type="module" src="/static/articles.js?v=old-token"></script>\n',
        encoding="utf-8",
    )

    publisher._sync_web_test_cache_token(tmp_path, cache_token="agy-i18n-0-3-59")

    assert 'ARTICLE_CACHE_TOKEN = "agy-i18n-0-3-59"' in (test_dir / "test_web.py").read_text(encoding="utf-8")
    assert "static/article.js?v=agy-i18n-0-3-59" in (web_dir / "article.html").read_text(encoding="utf-8")
    assert "static/articles.js?v=agy-i18n-0-3-59" in (web_dir / "articles.html").read_text(encoding="utf-8")


def test_isolated_transaction_never_mutates_actor_concurrent_bytes(tmp_path: Path) -> None:
    remote = tmp_path / "remote.git"
    seed = tmp_path / "seed"
    actor = tmp_path / "actor"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(seed)], check=True)
    subprocess.run(["git", "config", "user.email", "publisher-test@example.invalid"], cwd=seed, check=True)
    subprocess.run(["git", "config", "user.name", "Publisher Test"], cwd=seed, check=True)
    target = seed / "app/web/owned.txt"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"base\n")
    subprocess.run(["git", "add", "."], cwd=seed, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=seed, check=True)
    subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=seed, check=True)
    subprocess.run(["git", "push", "-q", "-u", "origin", "main"], cwd=seed, check=True)
    subprocess.run(["git", "clone", "-q", "-b", "main", str(remote), str(actor)], check=True)

    state_root = actor / ".work/content-publisher"
    state_root.mkdir(parents=True)
    actor_target = actor / "app/web/owned.txt"
    with publisher._isolated_transaction_worktree(actor, state_root) as transaction_root:
        assert transaction_root != actor
        assert (transaction_root / "app/web/owned.txt").read_bytes() == b"base\n"
        actor_target.write_bytes(b"concurrent-user\n")
        (transaction_root / "app/web/owned.txt").write_bytes(b"publisher\n")

    assert actor_target.read_bytes() == b"concurrent-user\n"
    assert subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=actor,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip() == "M app/web/owned.txt"
    assert not list(state_root.glob("transaction-*"))


def test_isolated_transaction_blocks_stale_actor_runtime(tmp_path: Path) -> None:
    actor = tmp_path / "actor"
    transaction = tmp_path / "transaction"
    for root, body in ((actor, b"old\n"), (transaction, b"new\n")):
        path = root / "scripts/agy_content_publisher.py"
        path.parent.mkdir(parents=True)
        path.write_bytes(body)

    with pytest.raises(publisher.PublishBlocked, match="deploy actor before publishing"):
        publisher._assert_transaction_runtime_matches(actor, transaction)


def test_main_runs_real_publish_in_isolated_worktree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    remote = tmp_path / "remote.git"
    seed = tmp_path / "seed"
    actor = tmp_path / "actor"
    queue_root = tmp_path / "queue"
    state_root = actor / ".work/content-publisher"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(seed)], check=True)
    subprocess.run(["git", "config", "user.email", "publisher-test@example.invalid"], cwd=seed, check=True)
    subprocess.run(["git", "config", "user.name", "Publisher Test"], cwd=seed, check=True)
    target = seed / "app/web/owned.txt"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"base\n")
    subprocess.run(["git", "add", "."], cwd=seed, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=seed, check=True)
    subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=seed, check=True)
    subprocess.run(["git", "push", "-q", "-u", "origin", "main"], cwd=seed, check=True)
    subprocess.run(["git", "clone", "-q", "-b", "main", str(remote), str(actor)], check=True)

    transaction_roots: list[Path] = []

    def fake_publish(repo_root: Path, *_args: object, **_kwargs: object) -> dict[str, object]:
        transaction_roots.append(repo_root)
        (actor / "app/web/owned.txt").write_bytes(b"concurrent-user\n")
        (repo_root / "app/web/owned.txt").write_bytes(b"publisher\n")
        return {"schema_version": publisher.SCHEMA_VERSION, "status": "idle", "published": 0}

    monkeypatch.setattr(
        publisher,
        "parse_args",
        lambda: publisher.argparse.Namespace(
            repo_root=actor,
            queue_root=queue_root,
            state_root=state_root,
            max_runs=1,
            dry_run=False,
            rewrite_release=False,
            include_rewrites=False,
            legacy_report=False,
            push=False,
            skip_tests=True,
            skip_release_gate=True,
        ),
    )
    monkeypatch.setattr(publisher, "publish_ready_runs", fake_publish)

    assert publisher.main() == 0
    assert len(transaction_roots) == 1
    assert transaction_roots[0] != actor
    assert not transaction_roots[0].exists()
    assert (actor / "app/web/owned.txt").read_bytes() == b"concurrent-user\n"
