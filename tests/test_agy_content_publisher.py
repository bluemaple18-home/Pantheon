from __future__ import annotations

import ast
import fcntl
import json
import plistlib
from pathlib import Path
import subprocess
import sys

import pytest

from scripts import agy_content_publisher as publisher
from scripts import agy_gemini_coordinator as coordinator
from scripts import pantheon_content_runtime_manifest as runtime_manifest
from scripts.agy_seo_copy_pipeline import article_sha256, body_sha256


def make_publication_policy(
    *,
    canonical: str,
    published: str,
    modified: str,
    change_type: str,
) -> dict[str, object]:
    identity = publisher.pipeline.load_article_publication_policy()["identity"]
    return {
        "policyVersion": publisher.pipeline.publication_policy_version(),
        "canonical": canonical,
        "author": {
            "name": identity["author_name"],
            "url": identity["author_url"],
            "id": identity["author_id"],
        },
        "editorialResponsibility": identity["editorial_responsibility"],
        "evidence": {
            "mode": "cultural_reflection",
            "sources": [],
            "disclosure": "本文屬文化脈絡與反思整理，不主張可驗證的預測結果。",
        },
        "published": published,
        "modified": modified,
        "changeType": change_type,
    }


def test_formal_publisher_rejects_manifest_drift_before_state_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    state = tmp_path / "state"
    logs = tmp_path / "logs"
    for path in (actor, queue, state, logs):
        path.mkdir()
    manifest = runtime_manifest.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity="formal-publisher",
        runtime_digest="3" * 64,
        generation="generation-publisher",
    )
    manifest_path = tmp_path / "manifest.json"
    runtime_manifest.write_manifest(manifest_path, manifest)
    monkeypatch.setenv("PANTHEON_FORMAL_RUNTIME", "1")
    monkeypatch.setenv("PANTHEON_RUNTIME_MANIFEST", str(manifest_path))
    monkeypatch.setenv("PANTHEON_RUNTIME_MANIFEST_DIGEST", manifest["manifest_digest"])
    monkeypatch.setenv("PANTHEON_RUNTIME_GENERATION", manifest["generation"])
    monkeypatch.setenv(
        "PANTHEON_RUNTIME_IDENTITY_DIGEST", manifest["runtime_identity_digest"]
    )
    monkeypatch.setenv(
        "PANTHEON_RUNTIME_SERVICE_LABEL", "com.pantheon.agy-content-publisher"
    )
    manifest_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(runtime_manifest.RuntimeManifestError):
        publisher.publish_ready_runs(
            actor,
            queue,
            state,
            dry_run=True,
            git=lambda *_args: pytest.fail("git must not run"),
        )

    assert not (state / "publisher.lock").exists()


def test_formal_publisher_rejects_forged_bounded_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    state = tmp_path / "state"
    transaction = state / "transaction-test" / "repo"
    for path in (actor, queue, transaction):
        path.mkdir(parents=True)
    _write_runtime_manifest_fixture(actor)
    _write_runtime_manifest_fixture(transaction)
    monkeypatch.setenv("PANTHEON_FORMAL_RUNTIME", "1")
    monkeypatch.setenv("PANTHEON_RUNTIME_ACTOR_ROOT", str(actor))
    def fake_validate_runtime_tick(
        _label: str,
        *,
        actor_root: Path,
        **_kwargs: object,
    ) -> dict[str, object]:
        if actor_root != actor:
            raise runtime_manifest.RuntimeManifestError(
                "formal runtime actor_root mismatch"
            )
        return {"status": "valid"}

    monkeypatch.setattr(
        publisher.formal_runtime,
        "validate_runtime_tick",
        fake_validate_runtime_tick,
    )

    with pytest.raises(
        runtime_manifest.RuntimeManifestError,
        match="actor_root mismatch",
    ):
        publisher._validate_formal_runtime(transaction, queue, state)


def _long(text: str) -> str:
    value = text
    while len(value) < 96:
        value += "再核對一項具體資料，避免把通用描述當成個人結論。"
    return value[:108]


def make_publishable_article(article_id: str = "AUTO-001") -> dict[str, object]:
    keyword = "測試關鍵字"
    paragraphs = [_long(f"{keyword}在第{index + 1}個場景中，先整理事實、限制與可行選項。") for index in range(15)]
    article = {
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
    article["publicationPolicy"] = make_publication_policy(
        canonical=f"https://www.mysticpantheon.com/articles/personality/{article['urlSlug']}",
        published=str(article["published"]),
        modified=str(article["updated"]),
        change_type="created",
    )
    return article


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


def _write_exhausted_create_retry(
    state_root: Path,
    run_id: str,
    *,
    error: str = "test_web hub display fixture marker not found",
) -> Path:
    evidence_path = state_root / "evidence" / f"failed-create-{run_id}" / "failure.json"
    _write_json(
        evidence_path,
        {
            "schema_version": 1,
            "status": "FAILED_RECOVERED",
            "phase": "create",
            "run_ids": [run_id],
            "error_type": "PublishBlocked",
            "repo_recovered": True,
            "retry_status": "candidate_preserved",
            "concurrent_write_conflicts": [],
            "status_after_recovery": [],
        },
    )
    retry_path = publisher._retry_path(state_root, "create", run_id)
    _write_json(
        retry_path,
        {
            "schema_version": 1,
            "phase": "create",
            "run_id": run_id,
            "attempts": publisher.MAX_RETRY_ATTEMPTS,
            "max_attempts": publisher.MAX_RETRY_ATTEMPTS,
            "error_type": "PublishBlocked",
            "error": error,
            "evidence": str(evidence_path),
            "last_attempt_at": "2026-07-30T12:00:00+08:00",
            "next_eligible_at": "2026-07-30T12:20:00+08:00",
            "eligibility": "exhausted",
            "candidate_preserved": True,
        },
    )
    return retry_path


def make_rewrite_article(article_id: str = "LEGACY-001", slug: str = "legacy-001") -> dict[str, object]:
    body_sections = [
        {
            "heading": f"舊文重寫段落 {section + 1}",
            "paragraphs": [_long(f"這是第{section + 1}段第{index + 1}則舊文重寫內容，保留原主題但改成更貼近使用者的說法。") for index in range(3)],
        }
        for section in range(5)
    ]
    body_sections[0]["paragraphs"][0] = _long(
        "舊文測試先回答讀者的問題：這份文化反思不能取代個人判斷，仍要回到具體情境。"
    )
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
        "publicationPolicy": make_publication_policy(
            canonical=f"https://www.mysticpantheon.com/articles/astrology/{slug}",
            published="2026-07-01",
            modified="2026-07-25",
            change_type="substantive_rewrite",
        ),
    }


def make_schema_conformant_rewrite_article(
    article_id: str = "LEGACY-SCHEMA-CONFORMANT",
    slug: str = "legacy-schema-conformant",
) -> dict[str, object]:
    article = make_rewrite_article(article_id, slug)
    keyword = str(article["identity"]["primaryKeyword"])
    seeds = [
        (
            f"{keyword}先回答讀者眼前的疑問：它是一個整理資訊與選擇的角度，"
            "不能代替個人判斷。下班在會議收到臨時任務時，先記錄期限與責任，再確認缺少哪些資料。"
        ),
        (
            "回家看到帳單與進修通知同時出現時，可以列出本月支出、比較時間成本，"
            "並詢問承辦人退出條件；這個場景讓抽象概念回到可核對的生活細節。"
        ),
        (
            "另一個例外是資料不足卻急著定案；此時應暫停推測、寫下已知事實，"
            "再安排一次短對話。這不代表所有人都要採取相同步驟，仍要觀察情境與後果。"
        ),
    ]
    paragraphs: list[str] = []
    for index in range(15):
        text = f"{seeds[index % len(seeds)]}第{index + 1}段只處理一個具體問題。"
        while len(text) < 96:
            text += "再核對一項可觀察資料。"
        paragraphs.append(text[:118])
    article["bodySections"] = [
        {
            "heading": f"具體判讀角度 {section + 1}",
            "paragraphs": paragraphs[section * 3 : section * 3 + 3],
        }
        for section in range(5)
    ]
    return article


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
    web = repo_root / "app" / "web"
    static = web / "static"
    static.mkdir(parents=True)
    (web / "articles.html").write_text(
        '<meta property="article:published_time" content="2026-07-10" />\n'
        '<meta property="article:modified_time" content="2026-07-16" />\n'
        '"datePublished": "2026-07-10",\n'
        '"dateModified": "2026-07-16",\n'
        '<time datetime="2026-07-10" data-articles-published>2026-07-10</time>\n'
        '<time datetime="2026-07-16" data-articles-updated>2026-07-16</time>\n'
        '<script type="module" src="/static/articles.js?v=old-token"></script>\n',
        encoding="utf-8",
    )
    (static / "article-registry.js").write_text(
        "export const ARTICLE_REGISTRY = [\n];\n"
        "function getArticleSectionRecord() { return {}; }\n"
        "function enforceArticlePolicy(article) { return article; }\n"
        "export function getActiveArticlePolicyOverride(article) {\n"
        "  const customPolicy = {};\n"
        "  return customPolicy;\n"
        "}\n"
        "function resolveArticleRecord(article) {\n"
        "  return enforceArticlePolicy({ ...article, ...getActiveArticlePolicyOverride(article) }, getArticleSectionRecord(article.section));\n"
        "}\n"
        "export function listArticleRecords() {\n"
        "  return ARTICLE_REGISTRY.map(resolveArticleRecord);\n"
        "}\n"
        "export function getArticleRecord() {\n"
        "  const article = ARTICLE_REGISTRY[0];\n"
        "  return article ? resolveArticleRecord(article) : null;\n"
        "}\n",
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


def test_collect_ready_runs_exact_selector_excludes_unlisted_ready_run(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    old_run = tmp_path / "runs" / "old-ready-run"
    target_run = tmp_path / "runs" / "target-ja-run"
    _write_run(
        queue_root,
        old_run,
        make_publishable_article("AUTO-OLD"),
        verdict="REJECT",
    )
    _write_run(queue_root, target_run, make_publishable_article("AUTO-TARGET"))

    ready = publisher.collect_ready_runs(
        queue_root,
        state_root,
        limit=10,
        exact_run_ids=[target_run.name],
    )

    assert [state["run_id"] for state, _candidate, _review in ready] == [
        target_run.name
    ]
    assert not (state_root / "ledger.json").exists()


def test_collect_ready_runs_without_exact_selector_keeps_existing_selection(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    target_run = tmp_path / "runs" / "target-ja-run"
    _write_run(queue_root, target_run, make_publishable_article("AUTO-TARGET"))

    ready = publisher.collect_ready_runs(queue_root, tmp_path / "state", limit=10)

    assert [state["run_id"] for state, _candidate, _review in ready] == [
        target_run.name,
    ]


def _write_exact_fresh_ja_translation_run(
    queue_root: Path,
    run_dir: Path,
    *,
    run_id: str = "auto-i18n-ja-fresh-001",
    locale: str = "ja",
    source_article_id: str = "V2-NEW-001",
    replacement_of: str | None = None,
) -> None:
    _write_json(
        run_dir / "brief.json",
        {
            "schema_version": 1,
            "run_id": run_id,
            "mode": "translate_existing",
            "articles": [
                {
                    "translation_id": f"{source_article_id}:{locale}",
                    "locale": locale,
                    "source_article_id": source_article_id,
                    "source_path": "/articles/mbti/v2-new-001",
                    "source_sha256": "a" * 64,
                    "source": {
                        "article_id": source_article_id,
                        "canonical_path": "/articles/mbti/v2-new-001",
                        "title": "元記事",
                        "description": "元記事の説明です。",
                        "answer": "元記事の回答です。",
                        "tags": ["性格"],
                        "faq": [{"question": "質問ですか？", "answer": "回答です。"}],
                        "bodySections": [
                            {"heading": "概要", "paragraphs": ["元記事の段落です。"]}
                        ],
                    },
                }
            ],
        },
    )
    state: dict[str, object] = {
        "schema_version": 1,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "status": "complete",
        "result": {"candidate": str(run_dir / "candidate.json")},
    }
    if replacement_of is not None:
        state["replacement_of"] = replacement_of
    _write_json(
        queue_root / "runs" / f"{run_id}.json",
        state,
    )


@pytest.mark.parametrize(
    ("run_id", "locale", "source_article_id", "replacement_of", "error"),
    [
        ("auto-i18n-ko-fresh-001", "ko", "V2-NEW-001", None, "must be JA"),
        ("auto-i18n-ja-fresh-001-replacement-01", "ja", "V2-NEW-001", None, "replacement lineage"),
        ("auto-i18n-ja-fresh-001", "ja", "LEGACY-001", None, "i18n-new"),
        ("auto-i18n-ja-fresh-001", "ja", "V2-NEW-001", "prior-run", "replacement lineage"),
    ],
)
def test_exact_fresh_ja_selector_rejects_non_fresh_or_wrong_lane(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    run_id: str,
    locale: str,
    source_article_id: str,
    replacement_of: str | None,
    error: str,
) -> None:
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    run_dir = tmp_path / "runs" / run_id
    _write_exact_fresh_ja_translation_run(
        queue_root,
        run_dir,
        run_id=run_id,
        locale=locale,
        source_article_id=source_article_id,
        replacement_of=replacement_of,
    )
    monkeypatch.setattr(publisher, "legacy_article_ids", lambda _repo: {"LEGACY-001"})

    with pytest.raises(publisher.PublishBlocked, match=error):
        publisher.publish_exact_fresh_ja_translation_run(
            tmp_path,
            queue_root,
            state_root,
            run_id,
        )


def test_exact_fresh_ja_selector_requires_one_existing_fresh_run(
    tmp_path: Path,
) -> None:
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"

    with pytest.raises(publisher.PublishBlocked, match="must name exactly one"):
        publisher.publish_exact_fresh_ja_translation_run(
            tmp_path, queue_root, state_root, None
        )

    with pytest.raises(publisher.PublishBlocked, match="not found"):
        publisher.publish_exact_fresh_ja_translation_run(
            tmp_path, queue_root, state_root, "auto-i18n-ja-missing-001"
        )

    with pytest.raises(publisher.PublishBlocked, match="must name exactly one"):
        publisher.publish_exact_fresh_ja_translation_run(
            tmp_path,
            queue_root,
            state_root,
            ["auto-i18n-ja-first-001", "auto-i18n-ja-second-001"],  # type: ignore[arg-type]
        )


def test_exact_fresh_ja_selector_rejects_old_retry_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    run_id = "auto-i18n-ja-fresh-001"
    _write_exact_fresh_ja_translation_run(queue_root, tmp_path / "runs" / run_id)
    _write_json(publisher._retry_path(state_root, "translation", run_id), {"attempts": 1})
    monkeypatch.setattr(publisher, "legacy_article_ids", lambda _repo: set())

    with pytest.raises(publisher.PublishBlocked, match="old retry"):
        publisher.publish_exact_fresh_ja_translation_run(
            tmp_path, queue_root, state_root, run_id
        )


def test_exact_fresh_ja_selector_uses_existing_publisher_transaction_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    run_id = "auto-i18n-ja-fresh-001"
    _write_exact_fresh_ja_translation_run(queue_root, tmp_path / "runs" / run_id)
    monkeypatch.setattr(publisher, "legacy_article_ids", lambda _repo: set())
    calls: list[dict[str, object]] = []

    def publish_transaction(*args: object, **kwargs: object) -> dict[str, object]:
        calls.append(kwargs)
        return {
            "status": "PUBLISHED_TRANSLATION",
            "run_ids": [run_id],
            "commit_sha": "c" * 40,
            "pushed": True,
        }

    monkeypatch.setattr(publisher, "publish_ready_translation_runs", publish_transaction)

    evidence = publisher.publish_exact_fresh_ja_translation_run(
        tmp_path,
        queue_root,
        state_root,
        run_id,
        push=True,
    )

    assert calls == [
        {
            "max_runs": 1,
            "dry_run": False,
            "push": True,
            "run_tests": True,
            "release_gate": True,
            "exact_run_ids": [run_id],
        }
    ]
    assert evidence["status"] == "PUBLISHED_TRANSLATION"
    assert evidence["run_ids"] == [run_id]
    assert evidence["commit_sha"] == "c" * 40
    assert evidence["pushed"] is True


@pytest.mark.parametrize(
    ("source_run_id", "article_id", "error"),
    [
        ("", "V2-NEW-001", "source run id"),
        ("source-run-001", "LEGACY-001", "i18n-new"),
        ("source-replacement-01", "V2-NEW-001", "replacement lineage"),
    ],
)
def test_prepare_exact_fresh_ja_run_rejects_other_selectors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_run_id: str,
    article_id: str,
    error: str,
) -> None:
    monkeypatch.setattr(publisher, "legacy_article_ids", lambda _repo: {"LEGACY-001"})

    with pytest.raises(publisher.PublishBlocked, match=error):
        publisher.prepare_exact_fresh_ja_translation_run(
            tmp_path,
            tmp_path / "queue",
            tmp_path / "state",
            source_run_id,
            article_id,
        )


def test_prepare_exact_fresh_ja_run_uses_existing_queue_registration(
    tmp_path: Path,
) -> None:
    queue_root = tmp_path / "queue"
    repo_root = Path(__file__).resolve().parents[1]
    source_run_id = "ja-topology-canary-20260806-01"
    article_id = "V2-MBTI-PAIR-ISFJ-ESTJ-LOVE"
    expected_run_id = publisher.multilingual.translation_run_id(source_run_id, article_id, "ja")

    record = publisher.prepare_exact_fresh_ja_translation_run(
        repo_root,
        queue_root,
        tmp_path / "state",
        source_run_id,
        article_id,
    )

    assert record["run_id"] == expected_run_id
    assert record["locale"] == "ja"
    state_path = next((queue_root / "runs").glob("*.json"))
    state = publisher._read_json(state_path)
    assert state["run_id"] == expected_run_id
    brief = publisher._read_json(Path(record["run_dir"]) / "brief.json")
    assert brief["run_id"] == expected_run_id
    assert [article["locale"] for article in brief["articles"]] == ["ja"]


def test_publish_ready_runs_exact_selector_does_not_seed_unlisted_translations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    repo_root.mkdir()
    ledger = publisher._load_ledger(state_root)
    ledger["published_runs"] = [
        {
            "run_id": "unlisted-published-run",
            "article_ids": ["UNLISTED-001"],
            "translation_seed_status": "pending",
        }
    ]
    ledger_path = publisher._ledger_path(state_root)
    _write_json(ledger_path, ledger)
    ledger_before = ledger_path.read_bytes()
    unlisted_queue_marker = queue_root / "unlisted-translation-run.json"
    seed_calls: list[tuple[str, str]] = []

    def seed_unlisted_translation(
        _repo_root: Path,
        _queue_root: Path,
        *,
        source_run_id: str,
        article_id: str,
    ) -> list[dict[str, str]]:
        seed_calls.append((source_run_id, article_id))
        _write_json(unlisted_queue_marker, {"run_id": "unlisted-translation-run"})
        return [
            {
                "run_id": "unlisted-translation-run",
                "locale": "ja",
                "run_dir": str(tmp_path / "runs" / "unlisted-translation-run"),
            }
        ]

    monkeypatch.setattr(
        publisher.multilingual,
        "enqueue_article_translations",
        seed_unlisted_translation,
    )
    monkeypatch.setattr(
        publisher.pipeline,
        "load_publication_reference_corpus",
        lambda _repo_root: [],
    )

    def fake_git(
        _repo_root: Path,
        args: list[str],
        _input_text: str | None = None,
    ) -> str:
        if args == ["rev-parse", "--git-common-dir"]:
            return ".git"
        if args == ["status", "--porcelain"]:
            return ""
        if args in (["rev-parse", "HEAD"], ["rev-parse", "origin/main"]):
            return "a" * 40
        return ""

    result = publisher.publish_ready_runs(
        repo_root,
        queue_root,
        state_root,
        git=fake_git,
        run_tests=False,
        release_gate=False,
        exact_run_ids=["target-ja-run"],
    )

    assert result["status"] == "idle"
    assert result["seeded_translation_runs"] == []
    assert seed_calls == []
    assert ledger_path.read_bytes() == ledger_before
    assert not unlisted_queue_marker.exists()


def test_recover_exhausted_create_retry_dry_run_is_read_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    run_dir = tmp_path / "runs" / "run-exhausted"
    _write_run(queue_root, run_dir, make_publishable_article())
    retry_path = _write_exhausted_create_retry(state_root, run_dir.name)
    before = retry_path.read_bytes()
    monkeypatch.setattr(
        publisher.pipeline,
        "load_publication_reference_corpus",
        lambda _repo: [],
    )

    result = publisher.recover_exhausted_create_retries(
        repo_root,
        queue_root,
        state_root,
        run_ids=[run_dir.name],
        expected_error="test_web hub display fixture marker not found",
        reason="fixture contract repaired by ac042b42b",
        dry_run=True,
    )

    assert result["status"] == "dry-run"
    assert result["recoverable_runs"] == [run_dir.name]
    assert len(result["recovery_digest"]) == 64
    assert retry_path.read_bytes() == before
    assert not (state_root / "evidence/retry-recovery").exists()
    assert not (state_root / "publisher.lock").exists()


def test_recover_exhausted_create_retry_resets_budget_with_audit_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    run_dir = tmp_path / "runs" / "run-exhausted"
    _write_run(queue_root, run_dir, make_publishable_article())
    retry_path = _write_exhausted_create_retry(state_root, run_dir.name)
    before = retry_path.read_bytes()
    monkeypatch.setattr(
        publisher.pipeline,
        "load_publication_reference_corpus",
        lambda _repo: [],
    )

    preview = publisher.recover_exhausted_create_retries(
        repo_root,
        queue_root,
        state_root,
        run_ids=[run_dir.name],
        expected_error="test_web hub display fixture marker not found",
        reason="fixture contract repaired by ac042b42b",
        dry_run=True,
    )
    result = publisher.recover_exhausted_create_retries(
        repo_root,
        queue_root,
        state_root,
        run_ids=[run_dir.name],
        expected_error="test_web hub display fixture marker not found",
        reason="fixture contract repaired by ac042b42b",
        expected_recovery_digest=preview["recovery_digest"],
    )

    assert result["status"] == "RECOVERED"
    assert result["recovered_runs"] == [run_dir.name]
    retry = publisher._read_json(retry_path)
    assert retry["attempts"] == 0
    assert retry["eligibility"] == "recovered"
    assert retry["candidate_preserved"] is True
    assert retry["recovered_from_retry_sha256"] == publisher._bytes_sha256(before)
    receipt = publisher._read_json(Path(retry["evidence"]))
    assert receipt["status"] == "RECOVERED"
    assert receipt["run_id"] == run_dir.name
    assert receipt["source_retry_sha256"] == publisher._bytes_sha256(before)
    assert receipt["reason"] == "fixture contract repaired by ac042b42b"
    ready = publisher.collect_ready_runs(
        queue_root,
        state_root,
        repo_root=repo_root,
    )
    assert [state["run_id"] for state, _candidate, _review in ready] == [
        run_dir.name
    ]


@pytest.mark.parametrize(
    ("invalid_field", "invalid_value", "message"),
    [
        ("status", "RECOVERY_PENDING", "failure evidence is not fully recovered"),
        ("repo_recovered", False, "failure evidence is not fully recovered"),
        ("retry_status", "unknown", "candidate preservation is not proven"),
        ("error_type", "OSError", "failure type is not bound"),
    ],
)
def test_recover_exhausted_create_retry_rejects_invalid_failure_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_field: str,
    invalid_value: object,
    message: str,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    run_dir = tmp_path / "runs" / "run-exhausted"
    _write_run(queue_root, run_dir, make_publishable_article())
    retry_path = _write_exhausted_create_retry(state_root, run_dir.name)
    retry = publisher._read_json(retry_path)
    evidence_path = Path(retry["evidence"])
    evidence = publisher._read_json(evidence_path)
    evidence[invalid_field] = invalid_value
    _write_json(evidence_path, evidence)
    before = retry_path.read_bytes()
    monkeypatch.setattr(
        publisher.pipeline,
        "load_publication_reference_corpus",
        lambda _repo: [],
    )

    with pytest.raises(publisher.PublishBlocked, match=message):
        publisher.recover_exhausted_create_retries(
            repo_root,
            queue_root,
            state_root,
            run_ids=[run_dir.name],
            expected_error="test_web hub display fixture marker not found",
            reason="fixture contract repaired by ac042b42b",
            expected_recovery_digest="0" * 64,
        )

    assert retry_path.read_bytes() == before


def test_recover_exhausted_create_retry_rejects_error_or_ledger_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    run_dir = tmp_path / "runs" / "run-exhausted"
    _write_run(queue_root, run_dir, make_publishable_article())
    retry_path = _write_exhausted_create_retry(state_root, run_dir.name)
    before = retry_path.read_bytes()
    monkeypatch.setattr(
        publisher.pipeline,
        "load_publication_reference_corpus",
        lambda _repo: [],
    )

    with pytest.raises(publisher.PublishBlocked, match="retry error differs"):
        publisher.recover_exhausted_create_retries(
            repo_root,
            queue_root,
            state_root,
            run_ids=[run_dir.name],
            expected_error="different failure",
            reason="fixture contract repaired by ac042b42b",
            expected_recovery_digest="0" * 64,
        )

    ledger = publisher._load_ledger(state_root)
    ledger["published_runs"].append({"run_id": run_dir.name})
    _write_json(publisher._ledger_path(state_root), ledger)
    with pytest.raises(publisher.PublishBlocked, match="already published"):
        publisher.recover_exhausted_create_retries(
            repo_root,
            queue_root,
            state_root,
            run_ids=[run_dir.name],
            expected_error="test_web hub display fixture marker not found",
            reason="fixture contract repaired by ac042b42b",
            expected_recovery_digest="0" * 64,
        )

    assert retry_path.read_bytes() == before


def test_recover_exhausted_create_retry_rejects_post_dry_run_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    run_dir = tmp_path / "runs" / "run-exhausted"
    _write_run(queue_root, run_dir, make_publishable_article())
    retry_path = _write_exhausted_create_retry(state_root, run_dir.name)
    monkeypatch.setattr(
        publisher.pipeline,
        "load_publication_reference_corpus",
        lambda _repo: [],
    )
    preview = publisher.recover_exhausted_create_retries(
        repo_root,
        queue_root,
        state_root,
        run_ids=[run_dir.name],
        expected_error="test_web hub display fixture marker not found",
        reason="fixture contract repaired by ac042b42b",
        dry_run=True,
    )
    retry = publisher._read_json(retry_path)
    retry["last_attempt_at"] = "2026-07-30T12:01:00+08:00"
    _write_json(retry_path, retry)
    changed = retry_path.read_bytes()

    with pytest.raises(
        publisher.PublishBlocked,
        match="state differs from approved dry-run",
    ):
        publisher.recover_exhausted_create_retries(
            repo_root,
            queue_root,
            state_root,
            run_ids=[run_dir.name],
            expected_error="test_web hub display fixture marker not found",
            reason="fixture contract repaired by ac042b42b",
            expected_recovery_digest=preview["recovery_digest"],
        )

    assert retry_path.read_bytes() == changed
    assert not (state_root / "evidence/retry-recovery").exists()


def test_policy_v2_scheduler_rejection_is_terminal_and_never_enters_retry_loop(
    tmp_path: Path,
) -> None:
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    run_dir = tmp_path / "runs" / "policy-reject"
    article = make_publishable_article("POLICY-REJECT")
    _write_run(queue_root, run_dir, article)
    candidate_path = run_dir / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate["articles"][0]["publicationPolicy"]["author"]["name"] = "不明作者"
    _write_json(candidate_path, candidate)

    assert publisher.collect_ready_runs(queue_root, state_root) == []
    evidence_path = publisher._policy_rejection_path(state_root, "create", "policy-reject")
    first = evidence_path.read_bytes()
    assert publisher.collect_ready_runs(queue_root, state_root) == []

    evidence = json.loads(first)
    assert evidence["status"] == "POLICY_REJECTED"
    assert evidence["terminal"] is True
    assert evidence["retry_eligible"] is False
    assert evidence["policy_version"] == publisher.pipeline.publication_policy_version()
    assert evidence["validator_result"] == "FAIL"
    assert evidence["article_ids"] == ["POLICY-REJECT"]
    assert evidence["input_hash"]
    assert evidence_path.read_bytes() == first
    assert not publisher._retry_path(state_root, "create", "policy-reject").exists()


def test_policy_v2_required_finding_cannot_use_publisher_override() -> None:
    article = make_publishable_article("POLICY-OVERRIDE")
    article["publicationPolicy"]["author"]["url"] = "https://example.com/untrusted"
    review = {
        "schema_version": 1,
        "run_id": "policy-override",
        "articles": [
            {
                "article_id": article["id"],
                "candidate_sha256": article_sha256(article),
                "verdict": "REJECT",
                "findings": [{"code": "author_identity", "message": "作者 identity 不一致"}],
            }
        ],
    }
    approval = publisher.pipeline.build_approval(
        "policy-override",
        [article],
        review,
        {str(article["id"]): "OVERRIDE_APPROVE"},
        "publisher-test",
        {str(article["id"]): "人工 override"},
    )

    with pytest.raises(ValueError, match="cannot be overridden"):
        publisher.pipeline.validate_apply_gate([article], review, approval)


def test_policy_v2_run_prerender_passes_explicit_rewrite_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []
    monkeypatch.setattr(
        publisher,
        "_run_checked",
        lambda _repo, command, **_kwargs: commands.append(command),
    )

    publisher._run_prerender(
        tmp_path,
        required_article_modes={"LEGACY-001": "rewrite_existing_body"},
    )

    assert len(commands) == 1
    assert "--required-article-mode" in commands[0]
    assert "LEGACY-001=rewrite_existing_body" in commands[0]


def test_run_prerender_times_out_with_observable_fail_closed_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command: list[str] = []

    def never_finishes(
        args: list[str],
        *,
        cwd: Path,
        check: bool,
        timeout: float | None = None,
    ) -> None:
        command.extend(args)
        assert cwd == tmp_path
        assert check is True
        assert timeout == 300
        raise subprocess.TimeoutExpired(args, timeout)

    monkeypatch.setattr(publisher.subprocess, "run", never_finishes)

    with pytest.raises(publisher.PrerenderTimeout) as raised:
        publisher._run_prerender(tmp_path)

    assert raised.value.diagnostic == {
        "command": command,
        "cwd": str(tmp_path),
        "elapsed_seconds": pytest.approx(0.0, abs=1.0),
        "timeout_seconds": 300,
        "process_outcome": "timed_out",
    }


def test_run_prerender_preserves_policy_rejection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_for_policy(_repo: Path, command: list[str], **_kwargs: object) -> None:
        output_index = command.index("--policy-failure-output") + 1
        Path(command[output_index]).write_text(
            json.dumps(
                {
                    "article_ids": ["LEGACY-001"],
                    "failure_codes": ["initial_html_complete"],
                }
            ),
            encoding="utf-8",
        )
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(publisher, "_run_checked", reject_for_policy)

    with pytest.raises(publisher.PolicyRejected, match="initial_html_complete"):
        publisher._run_prerender(tmp_path)


def test_policy_v2_noop_rewrite_apply_fails_before_modified_is_written(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    article = make_rewrite_article("LEGACY-NOOP")
    article["current_body_sha256"] = body_sha256(article["bodySections"])
    candidate = {
        "schema_version": 1,
        "run_id": "rewrite-noop",
        "mode": "rewrite_existing_body",
        "articles": [article],
    }
    monkeypatch.setattr(publisher, "_assert_rewrite_source_matches", lambda *_args: None)
    monkeypatch.setattr(
        publisher.pipeline,
        "load_publication_reference_corpus",
        lambda _repo: [],
    )

    with pytest.raises(publisher.PublishBlocked, match="no_substantive_change"):
        publisher.apply_rewrite_release(tmp_path, "rewrite-noop", [candidate])

    assert not (tmp_path / "app/web/static").exists()


def test_apply_rewrite_release_uses_inventory_slug_for_body_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _minimal_article_static(tmp_path)
    article = make_rewrite_article("EXPANSION-50D-FORTUNE-0039", "fortune-0039")
    candidate = {
        "schema_version": 1,
        "run_id": "rewrite-split-slug",
        "mode": "rewrite_existing_body",
        "articles": [article],
    }
    monkeypatch.setattr(
        publisher.pipeline,
        "_existing_rewrite_inventory",
        lambda _repo: {
            "EXPANSION-50D-FORTUNE-0039": {
                "record": {
                    "id": "EXPANSION-50D-FORTUNE-0039",
                    "product": "astrology",
                    "articleCategory": "astrology",
                    "serial": "astrology-0001",
                    "slug": "yongshen-meaning",
                    "urlSlug": "fortune-0039",
                    "primaryKeyword": "舊文測試",
                    "title": "舊文測試標題",
                },
                "currentBody": [
                    {
                        "heading": "舊內容",
                        "paragraphs": [_long("舊文原始內容。")],
                    }
                ],
            }
        },
    )
    monkeypatch.setattr(
        publisher.pipeline,
        "load_publication_reference_corpus",
        lambda _repo: [],
    )
    monkeypatch.setattr(
        publisher.pipeline,
        "required_policy_findings",
        lambda _findings: [],
    )

    changed = publisher.apply_rewrite_release(
        tmp_path,
        "rewrite-split-slug",
        [candidate],
    )

    module = tmp_path / "app/web/static/article-rewrite-rewrite-split-slug.js"
    assert module in changed
    text = module.read_text(encoding="utf-8")
    assert '"yongshen-meaning": [' in text
    assert '"fortune-0039": [' not in text
    policy_marker = (
        "export const AGY_REWRITE_SPLIT_SLUG_REWRITE_POLICY_OVERRIDES = "
    )
    policy_payload = json.loads(
        text.split(policy_marker, maxsplit=1)[1].strip().removesuffix(";")
    )
    override = policy_payload["EXPANSION-50D-FORTUNE-0039"]
    assert set(override) == {"updated", "publicationPolicy"}
    assert override["updated"] == "2026-07-25"
    assert override["publicationPolicy"]["published"] == "2026-07-01"
    assert override["publicationPolicy"]["modified"] == override["updated"]
    assert override["publicationPolicy"]["changeType"] == "substantive_rewrite"
    registry = (tmp_path / "app/web/static/article-registry.js").read_text(
        encoding="utf-8"
    )
    assert "REWRITE_POLICY_OVERRIDES[article.id] || {}" in registry
    assert "ARTICLE_REGISTRY.map(resolveArticleRecord)" in registry
    assert "return article ? resolveArticleRecord(article) : null" in registry


def test_apply_rewrite_release_refuses_to_overwrite_existing_release_module(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _minimal_article_static(tmp_path)
    article = make_rewrite_article("EXPANSION-50D-FORTUNE-0039", "fortune-0039")
    candidate = {
        "schema_version": 1,
        "run_id": "rewrite-collision",
        "mode": "rewrite_existing_body",
        "articles": [article],
    }
    monkeypatch.setattr(
        publisher,
        "_assert_rewrite_source_matches",
        lambda _repo, _candidates: {
            article["article_id"]: {
                "record": {"slug": "yongshen-meaning"},
            }
        },
    )
    monkeypatch.setattr(
        publisher.pipeline,
        "load_publication_reference_corpus",
        lambda _repo: [],
    )
    monkeypatch.setattr(
        publisher.pipeline,
        "required_policy_findings",
        lambda _findings: [],
    )
    module = (
        tmp_path
        / "app/web/static/article-rewrite-agy-rewrite-20260731-01.js"
    )
    module.write_text("existing release\n", encoding="utf-8")

    with pytest.raises(
        publisher.PublishBlocked,
        match="rewrite release id already exists",
    ):
        publisher.apply_rewrite_release(
            tmp_path,
            "agy-rewrite-20260731-01",
            [candidate],
        )

    assert module.read_text(encoding="utf-8") == "existing release\n"


def test_apply_rewrite_release_reuses_validated_inventory_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _minimal_article_static(tmp_path)
    article = make_rewrite_article("EXPANSION-50D-FORTUNE-0039", "fortune-0039")
    candidate = {
        "schema_version": 1,
        "run_id": "rewrite-inventory-snapshot",
        "mode": "rewrite_existing_body",
        "articles": [article],
    }
    current_body = [
        {
            "heading": "舊內容",
            "paragraphs": [_long("舊文原始內容。")],
        }
    ]
    valid_record = {
        "id": "EXPANSION-50D-FORTUNE-0039",
        "product": "astrology",
        "articleCategory": "astrology",
        "serial": "astrology-0001",
        "slug": "yongshen-meaning",
        "urlSlug": "fortune-0039",
        "primaryKeyword": "舊文測試",
        "title": "舊文測試標題",
    }
    loads: list[Path] = []

    def load_inventory(repo_root: Path) -> dict[str, object]:
        loads.append(repo_root)
        record = dict(valid_record)
        if len(loads) > 1:
            record["slug"] = "unverified-drift"
        return {
            "EXPANSION-50D-FORTUNE-0039": {
                "record": record,
                "currentBody": current_body,
            }
        }

    monkeypatch.setattr(
        publisher.pipeline,
        "_existing_rewrite_inventory",
        load_inventory,
    )
    monkeypatch.setattr(
        publisher.pipeline,
        "load_publication_reference_corpus",
        lambda _repo: [],
    )
    monkeypatch.setattr(
        publisher.pipeline,
        "required_policy_findings",
        lambda _findings: [],
    )

    changed = publisher.apply_rewrite_release(
        tmp_path,
        "rewrite-inventory-snapshot",
        [candidate],
    )

    module = tmp_path / "app/web/static/article-rewrite-rewrite-inventory-snapshot.js"
    assert module in changed
    assert loads == [tmp_path]
    text = module.read_text(encoding="utf-8")
    assert '"yongshen-meaning": [' in text
    assert '"unverified-drift": [' not in text


@pytest.mark.parametrize(
    ("invalid_source", "message"),
    [
        ("missing_article", "rewrite source article no longer exists"),
        ("missing_record", "rewrite source record is missing"),
        ("missing_slug", "rewrite source body slug is missing"),
        ("blank_slug", "rewrite source body slug is missing"),
    ],
)
def test_apply_rewrite_release_invalid_inventory_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_source: str,
    message: str,
) -> None:
    article_id = "EXPANSION-50D-FORTUNE-0039"
    article = make_rewrite_article(article_id, "fortune-0039")
    candidate = {
        "schema_version": 1,
        "run_id": "rewrite-invalid-inventory",
        "mode": "rewrite_existing_body",
        "articles": [article],
    }
    record = {
        "id": article_id,
        "product": "astrology",
        "articleCategory": "astrology",
        "serial": "astrology-0001",
        "slug": "yongshen-meaning",
        "urlSlug": "fortune-0039",
        "primaryKeyword": "舊文測試",
        "title": "舊文測試標題",
    }
    source: dict[str, object] = {
        "record": record,
        "currentBody": [
            {
                "heading": "舊內容",
                "paragraphs": [_long("舊文原始內容。")],
            }
        ],
    }
    inventory = {article_id: source}
    if invalid_source == "missing_article":
        inventory = {}
    elif invalid_source == "missing_record":
        source.pop("record")
    elif invalid_source == "missing_slug":
        record.pop("slug")
    else:
        record["slug"] = " \t"

    monkeypatch.setattr(
        publisher.pipeline,
        "_existing_rewrite_inventory",
        lambda _repo: inventory,
    )
    monkeypatch.setattr(
        publisher.pipeline,
        "load_publication_reference_corpus",
        lambda _repo: [],
    )
    monkeypatch.setattr(
        publisher.pipeline,
        "required_policy_findings",
        lambda _findings: [],
    )

    with pytest.raises(publisher.PublishBlocked, match=message):
        publisher.apply_rewrite_release(
            tmp_path,
            "rewrite-invalid-inventory",
            [candidate],
        )


def test_policy_v2_rewrite_prerender_rejection_is_terminal_without_transport_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root, queue_root, state_root, base_sha = _init_recovery_repo(tmp_path)
    run_id = "rewrite-prerender-policy-reject"
    run_dir = tmp_path / "runs" / run_id
    candidate = {
        "schema_version": 1,
        "run_id": run_id,
        "mode": "rewrite_existing_body",
        "articles": [make_rewrite_article("LEGACY-PRERENDER-REJECT")],
    }
    _write_json(run_dir / "candidate.json", candidate)
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
    monkeypatch.setattr(
        publisher,
        "_assert_clean_origin_head",
        lambda _repo, _git: base_sha,
    )

    @publisher._recoverable_publish("rewrite", "rewritten")
    def failing_rewrite(
        repo: Path,
        _queue: Path,
        _state: Path,
        *,
        git: publisher.GitRunner = publisher.run_git,
        _transaction_base_sha: str | None = None,
        _mutation_journal: publisher.MutationJournal | None = None,
    ) -> dict[str, object]:
        assert _mutation_journal is not None
        _mutation_journal.select_runs([run_id])
        _mutation_journal.begin()
        _mutation_journal.capture(
            lambda: (repo / "app/web/owned.txt").write_text(
                "rewrite mutation\n",
                encoding="utf-8",
            )
        )
        raise publisher.PolicyRejected(
            [
                publisher.pipeline._policy_finding(
                    "LEGACY-PRERENDER-REJECT",
                    "initial_html_complete",
                    "rewrite prerender policy rejection",
                )
            ]
        )

    result = failing_rewrite(repo_root, queue_root, state_root)

    assert result["status"] == "policy_rejected"
    assert result["status"] in publisher.SUCCESS_STATUSES
    assert result["retry_eligible"] is False
    rejection = publisher._read_json(
        publisher._policy_rejection_path(state_root, "rewrite", run_id)
    )
    assert rejection["terminal"] is True
    assert rejection["failure_codes"] == ["initial_html_complete"]
    assert not publisher._retry_path(state_root, "rewrite", run_id).exists()
    assert subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout == ""


def test_rewrite_full_test_failure_rolls_back_updated_date_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root, queue_root, state_root, base_sha = _init_recovery_repo(tmp_path)
    run_id = "rewrite-updated-date-full-test-failure"
    owned = repo_root / "app/web/owned.txt"
    monkeypatch.setattr(
        publisher,
        "_assert_clean_origin_head",
        lambda _repo, _git: base_sha,
    )
    test_commands: list[list[str]] = []

    def fail_full_test(_repo: Path, command: list[str]) -> None:
        test_commands.append(command)
        if command == publisher.TEST_COMMAND:
            raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(publisher, "_run_checked", fail_full_test)

    @publisher._recoverable_publish("rewrite", "rewritten")
    def failing_rewrite(
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
        _mutation_journal.select_runs([run_id])
        _mutation_journal.begin()
        _mutation_journal.capture(
            lambda: owned.write_text(
                "published=2026-07-16\nupdated=2026-08-03\n",
                encoding="utf-8",
            )
        )
        publisher._run_release_tests(repo)
        raise AssertionError("full test failure should abort the transaction")

    result = failing_rewrite(repo_root, queue_root, state_root)

    assert test_commands == [publisher.PREFLIGHT_TEST_COMMAND, publisher.TEST_COMMAND]
    assert result["status"] == "failed_recovered"
    assert result["error_type"] == "CalledProcessError"
    assert owned.read_bytes() == b"base\n"
    assert subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout == ""
    failure = json.loads(Path(str(result["evidence"])).read_text(encoding="utf-8"))
    assert failure["run_ids"] == [run_id]
    assert failure["repo_recovered"] is True
    assert failure["retry_status"] == "candidate_preserved"


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
    monkeypatch.setattr(publisher, "_run_prerender", lambda _repo, **_kwargs: None)
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
    monkeypatch.setattr(publisher.pipeline, "load_publication_reference_corpus", lambda _repo: [])
    monkeypatch.setattr(publisher, "_run_prerender", lambda _repo, **_kwargs: None)
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
    hub = (repo_root / "app/web/articles.html").read_text(encoding="utf-8")
    expected_updated = str(article["updated"])
    assert f'<meta property="article:modified_time" content="{expected_updated}" />' in hub
    assert f'"dateModified": "{expected_updated}"' in hub
    assert f'<time datetime="{expected_updated}" data-articles-updated>{expected_updated}</time>' in hub
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


def test_schema_conformant_rewrite_passes_offline_generation_to_publisher_eligibility(
    tmp_path: Path,
) -> None:
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    run_dir = tmp_path / "runs" / "rewrite-schema-conformant"
    article = make_schema_conformant_rewrite_article()
    current_body = [{"heading": "舊內容", "paragraphs": [_long("舊文原始內容。")]}]
    article["current_body_sha256"] = body_sha256(current_body)
    identity = article["identity"]
    brief = {
        "schema_version": 1,
        "run_id": run_dir.name,
        "mode": "rewrite_existing_body",
        "source_commit": "0" * 40,
        "sort_contract": "fixed",
        "articles": [
            {
                "slot": "article-01",
                "article_id": article["article_id"],
                "identity": identity,
                "immutable_fields": {
                    **identity,
                    "description": "原 description",
                    "answer": "原 answer",
                    "faq": [{"question": "原問題？", "answer": "原回答。"}],
                    "tags": ["測試"],
                    "published": "2026-07-01",
                    "updated": "2026-07-01",
                    "urlSlug": identity["slug"],
                },
                "current_body": current_body,
                "current_body_sha256": article["current_body_sha256"],
                "rewrite_brief": ["改得更口語，但保留使用者情境與限制。"],
                "source_file": "synthetic/article-meta.js",
                "body_source": "synthetic/article-body.js",
            }
        ],
    }
    _write_json(run_dir / "brief.json", brief)

    class OfflineApprovedClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def generate_json(
            self,
            role: str,
            _prompt: str,
            _schema: dict[str, object],
        ) -> dict[str, object]:
            if role == "writer":
                return {
                    "articles": [
                        {
                            "slot": "article-01",
                            "bodySections": article["bodySections"],
                            "publicationPolicy": article["publicationPolicy"],
                        }
                    ]
                }
            return {
                "articles": [
                    {
                        "slot": "article-01",
                        "semantic_verdict": "APPROVE",
                        "semantic_findings": [],
                        "objective_observations": [],
                    }
                ]
            }

    candidate, review = publisher.pipeline.run_writer_reviewer(
        run_dir,
        OfflineApprovedClient(),
        max_repairs=1,
    )
    publisher.pipeline.validate_candidate(candidate)
    assert publisher.pipeline.rewrite_quality_findings(
        brief,
        candidate["articles"],
    ) == []
    assert review["articles"][0]["verdict"] == "APPROVE"
    _write_json(
        queue_root / "runs" / f"{run_dir.name}.json",
        {
            "schema_version": 1,
            "run_id": run_dir.name,
            "run_dir": str(run_dir),
            "status": "complete",
            "result": {
                "status": "complete",
                "run_id": run_dir.name,
                "candidate": str(run_dir / "candidate.json"),
            },
        },
    )

    ready = publisher.collect_ready_rewrite_runs(
        queue_root,
        state_root,
        limit=1,
        allowed_article_ids={str(article["article_id"])},
    )

    assert len(ready) == 1
    assert ready[0][1] == candidate
    assert ready[0][2] == review


def test_collect_ready_rewrite_runs_skips_non_legacy_articles(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    _write_rewrite_run(queue_root, tmp_path / "runs" / "rewrite-newer", make_rewrite_article("NEW-AUTO-001", "new-auto-001"))
    monkeypatch.setattr(publisher.pipeline, "rewrite_aggregate_findings", lambda _brief, _articles: ([], []))

    ready = publisher.collect_ready_rewrite_runs(queue_root, state_root, limit=10, allowed_article_ids={"LEGACY-001"})

    assert ready == []


@pytest.mark.parametrize(
    "drift",
    ["title", "primary_keyword", "serial", "category", "url_slug"],
)
def test_publish_ready_rewrite_runs_quarantines_identity_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    drift: str,
) -> None:
    monkeypatch.setattr(publisher.pipeline, "load_publication_reference_corpus", lambda _repo: [])
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    candidate_slug = "yongshen-meaning" if drift == "url_slug" else "legacy-001"
    inventory_url_slug = "fortune-0039" if drift == "url_slug" else "legacy-001"
    article = make_rewrite_article("LEGACY-001", candidate_slug)
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
                    "articleCategory": "fortune" if drift == "category" else "astrology",
                    "serial": "astrology-9999" if drift == "serial" else "astrology-0001",
                    "slug": "yongshen-meaning" if drift == "url_slug" else "legacy-001",
                    "urlSlug": inventory_url_slug,
                    "primaryKeyword": "已變動的關鍵字" if drift == "primary_keyword" else "舊文測試",
                    "title": "已變動的舊文標題" if drift == "title" else "舊文測試標題",
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


def test_legacy_rewrite_backlog_classifies_retry_terminal_states_without_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    run_specs = {
        "rewrite-fresh": ("LEGACY-FRESH", "legacy-fresh", "APPROVE"),
        "rewrite-deferred": ("LEGACY-DEFERRED", "legacy-deferred", "APPROVE"),
        "rewrite-exhausted": (
            "LEGACY-EXHAUSTED",
            "legacy-exhausted",
            "APPROVE",
        ),
        "rewrite-invalid": ("LEGACY-INVALID", "legacy-invalid", "APPROVE"),
        "rewrite-rejected": ("LEGACY-REJECTED", "legacy-rejected", "REJECT"),
        "rewrite-published": (
            "LEGACY-PUBLISHED",
            "legacy-published",
            "APPROVE",
        ),
    }
    for run_id, (article_id, slug, verdict) in run_specs.items():
        _write_rewrite_run(
            queue_root,
            tmp_path / "runs" / run_id,
            make_rewrite_article(article_id, slug),
            verdict=verdict,
        )
    _write_json(
        publisher._ledger_path(state_root),
        {
            **publisher._load_ledger(state_root),
            "rewrite_released_runs": [{"run_id": "rewrite-published"}],
        },
    )
    retry_payloads = {
        "rewrite-deferred": {
            "attempts": 1,
            "next_eligible_at": "2999-01-01T00:00:00+08:00",
            "eligibility": "deferred",
        },
        "rewrite-exhausted": {
            "attempts": publisher.MAX_RETRY_ATTEMPTS,
            "next_eligible_at": "2026-07-30T12:20:00+08:00",
            "eligibility": "exhausted",
        },
        "rewrite-invalid": {
            "attempts": 1,
            "next_eligible_at": "not-a-timestamp",
            "eligibility": "deferred",
        },
    }
    retry_before: dict[Path, bytes] = {}
    for run_id, payload in retry_payloads.items():
        retry_path = publisher._retry_path(state_root, "rewrite", run_id)
        _write_json(
            retry_path,
            {
                "schema_version": 1,
                "phase": "rewrite",
                "run_id": run_id,
                "max_attempts": publisher.MAX_RETRY_ATTEMPTS,
                "candidate_preserved": True,
                **payload,
            },
        )
        retry_before[retry_path] = retry_path.read_bytes()
    monkeypatch.setattr(
        publisher.pipeline,
        "rewrite_aggregate_findings",
        lambda *_args, **_kwargs: ([], []),
    )
    legacy_records = [
        {
            "id": article_id,
            "serial": f"astrology-{index:04d}",
            "articleCategory": "astrology",
        }
        for index, (article_id, _slug, _verdict) in enumerate(
            run_specs.values(),
            start=1,
        )
    ]
    allowed_article_ids = {str(record["id"]) for record in legacy_records}

    first = publisher.summarize_legacy_rewrite_backlog(
        queue_root,
        state_root,
        allowed_article_ids=allowed_article_ids,
        legacy_records=legacy_records,
    )
    second = publisher.summarize_legacy_rewrite_backlog(
        queue_root,
        state_root,
        allowed_article_ids=allowed_article_ids,
        legacy_records=legacy_records,
    )
    ready = publisher.collect_ready_rewrite_runs(
        queue_root,
        state_root,
        limit=10,
        allowed_article_ids=allowed_article_ids,
    )

    assert first == second
    assert first["released"] == 1
    assert first["reject"] == 1
    assert first["clean_approve"] == 4
    assert first["publish_ready_run_ids"] == ["rewrite-fresh"]
    assert first["retry_deferred_run_ids"] == ["rewrite-deferred"]
    assert first["retry_exhausted_run_ids"] == ["rewrite-exhausted"]
    assert first["retry_invalid_run_ids"] == ["rewrite-invalid"]
    assert [state["run_id"] for state, _candidate, _review, _brief in ready] == [
        "rewrite-fresh"
    ]
    assert {
        path: path.read_bytes() for path in retry_before
    } == retry_before


@pytest.mark.parametrize("retry_payload", [[], {"attempts": None}])
def test_malformed_rewrite_retry_blocks_coordinator_without_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    retry_payload: object,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    run_root = tmp_path / "private-runs"
    repo_root.mkdir()
    run_id = "rewrite-malformed"
    article_id = "LEGACY-MALFORMED"
    _write_rewrite_run(
        queue_root,
        tmp_path / "runs" / run_id,
        make_rewrite_article(article_id, "legacy-malformed"),
    )
    retry_path = publisher._retry_path(state_root, "rewrite", run_id)
    _write_json(retry_path, retry_payload)
    retry_before = retry_path.read_bytes()
    legacy_records = [
        {
            "id": article_id,
            "serial": "astrology-0001",
            "articleCategory": "astrology",
        },
        {
            "id": "LEGACY-UNATTEMPTED",
            "serial": "astrology-0002",
            "articleCategory": "astrology",
        },
    ]
    monkeypatch.setattr(
        publisher.pipeline,
        "rewrite_aggregate_findings",
        lambda *_args, **_kwargs: ([], []),
    )
    monkeypatch.setattr(
        publisher,
        "legacy_article_records",
        lambda _repo: legacy_records,
    )

    first = publisher.summarize_legacy_rewrite_backlog(
        queue_root,
        state_root,
        allowed_article_ids={str(record["id"]) for record in legacy_records},
        legacy_records=legacy_records,
    )
    result = coordinator.seed_legacy_rewrite_runs(
        repo_root,
        queue_root,
        state_root,
        run_root,
        source_commit="a" * 40,
    )
    second = publisher.summarize_legacy_rewrite_backlog(
        queue_root,
        state_root,
        allowed_article_ids={str(record["id"]) for record in legacy_records},
        legacy_records=legacy_records,
    )

    assert first == second
    assert first["retry_invalid"] == 1
    assert first["retry_invalid_run_ids"] == [run_id]
    assert result["status"] == "rewrite_retry_blocked"
    assert result["backlog"]["retry_invalid"] == 1
    assert retry_path.read_bytes() == retry_before
    assert not run_root.exists()


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
    monkeypatch.setattr(publisher.pipeline, "load_publication_reference_corpus", lambda _repo: [])
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
    prior_release = (
        repo_root
        / "app/web/static"
        / f"article-rewrite-agy-rewrite-{publisher.date.today().strftime('%Y%m%d')}-01.js"
    )
    prior_release.write_text("existing release\n", encoding="utf-8")
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
                    "slug": "legacy-001",
                    "urlSlug": "legacy-001",
                    "primaryKeyword": "舊文測試",
                    "title": "舊文測試標題",
                },
                "currentBody": [{"heading": "舊內容", "paragraphs": [_long("舊文原始內容。")]}],
            }
        },
    )
    monkeypatch.setattr(publisher, "_public_article_count", lambda _repo: 353)
    prerender_commands: list[list[str]] = []
    monkeypatch.setattr(
        publisher,
        "_run_checked",
        lambda _repo, command, **_kwargs: prerender_commands.append(command),
    )
    monkeypatch.setattr(publisher, "_run_feed", lambda _repo: None)
    seeded: list[tuple[str, str]] = []
    monkeypatch.setattr(
        publisher.multilingual,
        "enqueue_article_translations",
        lambda _repo, _queue, *, source_run_id, article_id: seeded.append((source_run_id, article_id))
        or [
            {"run_id": f"{article_id}-{locale}", "locale": locale, "run_dir": f"/tmp/{locale}"}
            for locale in ("en", "ja", "ko")
        ],
    )
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
    hub = (repo_root / "app/web/articles.html").read_text(encoding="utf-8")
    expected_updated = str(article["publicationPolicy"]["modified"])
    assert f'<meta property="article:modified_time" content="{expected_updated}" />' in hub
    assert f'"dateModified": "{expected_updated}"' in hub
    assert f'<time datetime="{expected_updated}" data-articles-updated>{expected_updated}</time>' in hub
    modules = list((repo_root / "app/web/static").glob("article-rewrite-agy-rewrite-*.js"))
    assert len(modules) == 2
    assert prior_release.read_text(encoding="utf-8") == "existing release\n"
    assert (
        repo_root
        / "app/web/static"
        / f"article-rewrite-agy-rewrite-{publisher.date.today().strftime('%Y%m%d')}-02.js"
    ).is_file()
    meta = (repo_root / "app/web/static/article-meta.js").read_text(encoding="utf-8")
    assert "REWRITE_BODY_OVERRIDES[article.slug] || ARTICLE_BODY_LIBRARY[article.slug]" in meta
    ledger = json.loads((state_root / "ledger.json").read_text(encoding="utf-8"))
    assert ledger["rewrite_released_runs"][0]["run_id"] == "rewrite-approved"
    assert ledger["rewrite_released_runs"][0]["article_ids"] == ["LEGACY-001"]
    assert ledger["rewrite_released_runs"][0]["translation_seed_status"] == "seeded"
    assert ledger["rewrite_released_runs"][0]["translation_run_ids"] == [
        "LEGACY-001-en",
        "LEGACY-001-ja",
        "LEGACY-001-ko",
    ]
    assert seeded == [("rewrite-approved", "LEGACY-001")]
    assert result["seeded_translation_runs"] == [
        "LEGACY-001-en",
        "LEGACY-001-ja",
        "LEGACY-001-ko",
    ]
    assert any(
        "LEGACY-001=rewrite_existing_body" in command
        for command in prerender_commands
    )
    assert ["push", "origin", "HEAD:main", "v0.3.1"] not in git_calls


def test_seed_pending_translations_backfills_recovered_rewrite_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    run_dir = tmp_path / "runs" / "rewrite-recovered"
    _write_rewrite_run(queue_root, run_dir, make_rewrite_article("LEGACY-RECOVERED"))
    _write_json(
        state_root / "ledger.json",
        {
            "schema_version": 1,
            "published_runs": [],
            "quarantined_runs": [],
            "rewrite_released_runs": [
                {
                    "run_id": "rewrite-recovered",
                    "recovered_from": "CHANGELOG.md",
                }
            ],
            "translation_published_runs": [],
            "translation_deferred_runs": [],
        },
    )
    seeded: list[tuple[str, str]] = []
    monkeypatch.setattr(
        publisher.multilingual,
        "enqueue_article_translations",
        lambda _repo, _queue, *, source_run_id, article_id: seeded.append((source_run_id, article_id))
        or [
            {"run_id": f"{article_id}-{locale}", "locale": locale, "run_dir": f"/tmp/{locale}"}
            for locale in ("en", "ja", "ko")
        ],
    )

    run_ids = publisher._seed_pending_translations(tmp_path, queue_root, state_root)

    assert seeded == [("rewrite-recovered", "LEGACY-RECOVERED")]
    assert run_ids == [
        "LEGACY-RECOVERED-en",
        "LEGACY-RECOVERED-ja",
        "LEGACY-RECOVERED-ko",
    ]
    ledger = json.loads((state_root / "ledger.json").read_text(encoding="utf-8"))
    rewrite = ledger["rewrite_released_runs"][0]
    assert rewrite["article_ids"] == ["LEGACY-RECOVERED"]
    assert rewrite["translation_seed_status"] == "seeded"


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


def _write_runtime_manifest_fixture(repo_root: Path) -> None:
    for relative in publisher.TRANSACTION_RUNTIME_PATHS:
        path = repo_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"runtime fixture: {relative}\n", encoding="utf-8")


def test_runtime_manifest_digest_is_path_ordered_and_byte_sensitive(
    tmp_path: Path,
) -> None:
    actor = tmp_path / "actor"
    actor.mkdir()
    _write_runtime_manifest_fixture(actor)

    manifest = publisher.runtime_manifest(actor)
    digest = publisher.runtime_manifest_digest(actor)

    assert manifest["schema_version"] == publisher.RUNTIME_MANIFEST_SCHEMA_VERSION
    assert [item["path"] for item in manifest["files"]] == sorted(
        publisher.TRANSACTION_RUNTIME_PATHS
    )
    assert len(digest) == 64
    changed = actor / publisher.TRANSACTION_RUNTIME_PATHS[0]
    changed.write_bytes(changed.read_bytes() + b"drift\n")
    assert publisher.runtime_manifest_digest(actor) != digest


def test_runtime_manifest_digest_is_path_set_sensitive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = tmp_path / "actor"
    actor.mkdir()
    _write_runtime_manifest_fixture(actor)
    digest = publisher.runtime_manifest_digest(actor)
    extra = actor / "scripts/runtime-membership-marker.py"
    extra.parent.mkdir(parents=True, exist_ok=True)
    extra.write_text("RUNTIME_MARKER = True\n", encoding="utf-8")

    monkeypatch.setattr(
        publisher,
        "TRANSACTION_RUNTIME_PATHS",
        (*publisher.TRANSACTION_RUNTIME_PATHS, "scripts/runtime-membership-marker.py"),
    )

    assert publisher.runtime_manifest_digest(actor) != digest


def test_deployment_preflight_returns_read_only_plan_without_mutation(
    tmp_path: Path,
) -> None:
    actor = tmp_path / "actor"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    actor.mkdir()
    (queue_root / "runs").mkdir(parents=True)
    state_root.mkdir()
    _write_runtime_manifest_fixture(actor)
    runtime_sha = "a" * 40
    runtime_digest = publisher.runtime_manifest_digest(actor)
    git_calls: list[list[str]] = []

    def fake_git(_repo_root: Path, args: list[str], _input_text: str | None = None) -> str:
        git_calls.append(args)
        if args == ["status", "--porcelain"]:
            return ""
        if args in (["rev-parse", "HEAD"], ["rev-parse", "origin/main"]):
            return runtime_sha
        raise AssertionError(f"unexpected git command: {args}")

    before = sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*"))
    plan = publisher.deployment_preflight(
        actor,
        queue_root,
        state_root,
        expected_repo_root=actor,
        expected_queue_root=queue_root,
        expected_state_root=state_root,
        expected_runtime_sha=runtime_sha,
        expected_runtime_digest=runtime_digest,
        push=True,
        expected_push_mode="push",
        git=fake_git,
    )
    after = sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*"))

    assert plan == {
        "schema_version": publisher.SCHEMA_VERSION,
        "status": "ready",
        "operation": "deployment-preflight",
        "mode": "read-only",
        "dry_run": True,
        "mutation_permitted": False,
        "actor": "matched",
        "queue": "matched",
        "state": "matched",
        "runtime_sha": runtime_sha,
        "runtime_manifest_schema_version": publisher.RUNTIME_MANIFEST_SCHEMA_VERSION,
        "runtime_digest": runtime_digest,
        "origin_main_sha": runtime_sha,
        "push_mode": "push",
    }
    assert git_calls == [
        ["status", "--porcelain"],
        ["rev-parse", "HEAD"],
        ["rev-parse", "origin/main"],
    ]
    assert after == before


def test_deployment_preflight_allows_descendant_content_only_origin_advance(
    tmp_path: Path,
) -> None:
    actor = tmp_path / "actor"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    actor.mkdir()
    (queue_root / "runs").mkdir(parents=True)
    state_root.mkdir()
    _write_runtime_manifest_fixture(actor)
    runtime_sha = "a" * 40
    runtime_digest = publisher.runtime_manifest_digest(actor)
    origin_main_sha = "b" * 40

    def fake_git(_repo_root: Path, args: list[str], _input_text: str | None = None) -> str:
        if args == ["status", "--porcelain"]:
            return ""
        if args == ["rev-parse", "HEAD"]:
            return runtime_sha
        if args == ["rev-parse", "origin/main"]:
            return origin_main_sha
        if args == ["merge-base", runtime_sha, origin_main_sha]:
            return runtime_sha
        if args == [
            "diff",
            "--name-only",
            runtime_sha,
            origin_main_sha,
            "--",
            *publisher.TRANSACTION_RUNTIME_PATHS,
        ]:
            return ""
        raise AssertionError(f"unexpected git command: {args}")

    plan = publisher.deployment_preflight(
        actor,
        queue_root,
        state_root,
        expected_repo_root=actor,
        expected_queue_root=queue_root,
        expected_state_root=state_root,
        expected_runtime_sha=runtime_sha,
        expected_runtime_digest=runtime_digest,
        push=True,
        expected_push_mode="push",
        git=fake_git,
    )

    assert plan["status"] == "ready"
    assert plan["runtime_sha"] == runtime_sha
    assert plan["runtime_digest"] == runtime_digest
    assert plan["origin_main_sha"] == origin_main_sha


def test_deployment_preflight_manifest_authority_accepts_promoted_production_tuple(
    tmp_path: Path,
) -> None:
    actor = tmp_path / "actor"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    actor.mkdir()
    (queue_root / "runs").mkdir(parents=True)
    state_root.mkdir()
    _write_runtime_manifest_fixture(actor)
    runtime_sha = "28b8b84b6dfa319d8151aac3bc1a6a819ae82aa1"
    origin_main_sha = "79bdc809b0b7e17005c5420236dfb71e2bf794c2"
    runtime_digest = publisher.runtime_manifest_digest(actor)
    manifest_authority = {
        "actor_root": str(actor.resolve()),
        "actor_head": runtime_sha,
        "runtime_digest": runtime_digest,
        "manifest_digest": "c57a95aa72d8e01c676e50a9a54156da04ef1f9c3b4c86fa788819200df586a2",
    }

    def manifest_git(
        _repo_root: Path,
        args: list[str],
        _input_text: str | None = None,
    ) -> str:
        if args == ["status", "--porcelain"]:
            return ""
        if args == ["rev-parse", "HEAD"]:
            return runtime_sha
        raise AssertionError(f"manifest authority must not query remote refs: {args}")

    plan = publisher.deployment_preflight(
        actor,
        queue_root,
        state_root,
        expected_repo_root=actor,
        expected_queue_root=queue_root,
        expected_state_root=state_root,
        expected_runtime_sha=runtime_sha,
        expected_runtime_digest=runtime_digest,
        push=True,
        expected_push_mode="push",
        manifest_authority=manifest_authority,
        expected_manifest_digest=manifest_authority["manifest_digest"],
        git=manifest_git,
    )

    assert plan["status"] == "ready"
    assert plan["authority_mode"] == "manifest"
    assert plan["manifest_digest"] == manifest_authority["manifest_digest"]
    assert "origin_main_sha" not in plan

    def normal_git(
        _repo_root: Path,
        args: list[str],
        _input_text: str | None = None,
    ) -> str:
        if args == ["status", "--porcelain"]:
            return ""
        if args == ["rev-parse", "HEAD"]:
            return runtime_sha
        if args == ["rev-parse", "origin/main"]:
            return origin_main_sha
        if args == ["merge-base", runtime_sha, origin_main_sha]:
            return "0" * 40
        raise AssertionError(f"unexpected git command: {args}")

    with pytest.raises(
        publisher.PublishBlocked,
        match="origin/main is not a descendant",
    ):
        publisher.deployment_preflight(
            actor,
            queue_root,
            state_root,
            expected_repo_root=actor,
            expected_queue_root=queue_root,
            expected_state_root=state_root,
            expected_runtime_sha=runtime_sha,
            expected_runtime_digest=runtime_digest,
            push=True,
            expected_push_mode="push",
            git=normal_git,
        )


@pytest.mark.parametrize(
    "drift",
    ["actor-root", "actor-head", "runtime-digest", "manifest-digest"],
)
def test_deployment_preflight_manifest_authority_fails_closed_on_tuple_drift(
    tmp_path: Path,
    drift: str,
) -> None:
    actor = tmp_path / "actor"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    actor.mkdir()
    (queue_root / "runs").mkdir(parents=True)
    state_root.mkdir()
    _write_runtime_manifest_fixture(actor)
    runtime_sha = "a" * 40
    runtime_digest = publisher.runtime_manifest_digest(actor)
    manifest_digest = "b" * 64
    manifest_authority = {
        "actor_root": str(actor.resolve()),
        "actor_head": runtime_sha,
        "runtime_digest": runtime_digest,
        "manifest_digest": manifest_digest,
    }
    field = drift.replace("-", "_")
    manifest_authority[field] = (
        str(tmp_path.resolve())
        if drift == "actor-root"
        else "c" * (40 if drift == "actor-head" else 64)
    )

    def fake_git(
        _repo_root: Path,
        args: list[str],
        _input_text: str | None = None,
    ) -> str:
        if args == ["status", "--porcelain"]:
            return ""
        if args == ["rev-parse", "HEAD"]:
            return runtime_sha
        raise AssertionError(f"manifest authority must not query remote refs: {args}")

    with pytest.raises(
        publisher.PublishBlocked,
        match="manifest authority differs from deployment contract",
    ):
        publisher.deployment_preflight(
            actor,
            queue_root,
            state_root,
            expected_repo_root=actor,
            expected_queue_root=queue_root,
            expected_state_root=state_root,
            expected_runtime_sha=runtime_sha,
            expected_runtime_digest=runtime_digest,
            push=True,
            expected_push_mode="push",
            manifest_authority=manifest_authority,
            expected_manifest_digest=manifest_digest,
            git=fake_git,
        )


def test_deployment_preflight_rejects_incomplete_manifest_authority(
    tmp_path: Path,
) -> None:
    actor = tmp_path / "actor"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    actor.mkdir()
    (queue_root / "runs").mkdir(parents=True)
    state_root.mkdir()
    _write_runtime_manifest_fixture(actor)
    runtime_sha = "a" * 40
    runtime_digest = publisher.runtime_manifest_digest(actor)

    def fake_git(
        _repo_root: Path,
        args: list[str],
        _input_text: str | None = None,
    ) -> str:
        if args == ["status", "--porcelain"]:
            return ""
        if args == ["rev-parse", "HEAD"]:
            return runtime_sha
        raise AssertionError(f"incomplete authority must not query remote refs: {args}")

    with pytest.raises(
        publisher.PublishBlocked,
        match="manifest authority contract is incomplete",
    ):
        publisher.deployment_preflight(
            actor,
            queue_root,
            state_root,
            expected_repo_root=actor,
            expected_queue_root=queue_root,
            expected_state_root=state_root,
            expected_runtime_sha=runtime_sha,
            expected_runtime_digest=runtime_digest,
            push=True,
            expected_push_mode="push",
            manifest_authority={"actor_root": str(actor.resolve())},
            git=fake_git,
        )


def test_deployment_preflight_canary_requires_exact_single_run(
    tmp_path: Path,
) -> None:
    actor = tmp_path / "actor"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    actor.mkdir()
    (queue_root / "runs").mkdir(parents=True)
    state_root.mkdir()
    _write_runtime_manifest_fixture(actor)
    runtime_sha = "a" * 40
    runtime_digest = publisher.runtime_manifest_digest(actor)

    def fake_git(_repo_root: Path, args: list[str], _input_text: str | None = None) -> str:
        if args == ["status", "--porcelain"]:
            return ""
        if args in (["rev-parse", "HEAD"], ["rev-parse", "origin/main"]):
            return runtime_sha
        raise AssertionError(f"unexpected git command: {args}")

    plan = publisher.deployment_preflight(
        actor,
        queue_root,
        state_root,
        expected_repo_root=actor,
        expected_queue_root=queue_root,
        expected_state_root=state_root,
        expected_runtime_sha=runtime_sha,
        expected_runtime_digest=runtime_digest,
        push=True,
        expected_push_mode="push",
        max_runs=1,
        expected_exact_run_ids=["canary-run-001"],
        git=fake_git,
    )

    assert plan["exact_run_ids"] == ["canary-run-001"]
    assert plan["max_runs"] == 1

    with pytest.raises(publisher.PublishBlocked, match="max-runs 1"):
        publisher.deployment_preflight(
            actor,
            queue_root,
            state_root,
            expected_repo_root=actor,
            expected_queue_root=queue_root,
            expected_state_root=state_root,
            expected_runtime_sha=runtime_sha,
            expected_runtime_digest=runtime_digest,
            push=True,
            expected_push_mode="push",
            max_runs=2,
            expected_exact_run_ids=["canary-run-001"],
            git=fake_git,
        )
    with pytest.raises(publisher.PublishBlocked, match="one exact run"):
        publisher.deployment_preflight(
            actor,
            queue_root,
            state_root,
            expected_repo_root=actor,
            expected_queue_root=queue_root,
            expected_state_root=state_root,
            expected_runtime_sha=runtime_sha,
            expected_runtime_digest=runtime_digest,
            push=True,
            expected_push_mode="push",
            max_runs=1,
            expected_exact_run_ids=["canary-run-001", "canary-run-002"],
            git=fake_git,
        )


def test_main_deployment_preflight_returns_before_state_or_publish_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    actor = tmp_path / "actor"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    actor.mkdir()
    queue_root.mkdir()
    runtime_sha = "a" * 40
    expected_plan = {
        "schema_version": publisher.SCHEMA_VERSION,
        "status": "ready",
        "operation": "deployment-preflight",
        "mode": "read-only",
    }
    monkeypatch.setattr(
        publisher,
        "deployment_preflight",
        lambda *_args, **_kwargs: expected_plan,
    )
    monkeypatch.setattr(
        publisher,
        "publish_ready_all",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("deployment preflight must not publish")
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "agy_content_publisher.py",
            "--repo-root",
            str(actor),
            "--queue-root",
            str(queue_root),
            "--state-root",
            str(state_root),
            "--include-rewrites",
            "--push",
            "--deployment-preflight",
            "--expected-repo-root",
            str(actor),
            "--expected-queue-root",
            str(queue_root),
            "--expected-state-root",
            str(state_root),
            "--expected-runtime-sha",
            runtime_sha,
            "--expected-runtime-digest",
            "d" * 64,
            "--expected-push-mode",
            "push",
        ],
    )

    assert publisher.main() == 0
    assert json.loads(capsys.readouterr().out) == expected_plan
    assert not state_root.exists()


@pytest.mark.parametrize(
    ("drift", "message"),
    [
        ("actor", "actor root"),
        ("queue", "queue root"),
        ("state", "state root"),
        ("runtime", "runtime SHA"),
        ("runtime-digest", "runtime digest"),
        ("dirty", "worktree is not clean"),
        ("origin", "origin/main is not a descendant"),
        ("origin-runtime", "publisher runtime differs from origin/main"),
        ("push", "push mode"),
    ],
)
def test_deployment_preflight_fails_closed_on_contract_drift(
    tmp_path: Path,
    drift: str,
    message: str,
) -> None:
    actor = tmp_path / "actor"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    actor.mkdir()
    (queue_root / "runs").mkdir(parents=True)
    state_root.mkdir()
    _write_runtime_manifest_fixture(actor)
    runtime_sha = "a" * 40
    runtime_digest = publisher.runtime_manifest_digest(actor)

    def fake_git(_repo_root: Path, args: list[str], _input_text: str | None = None) -> str:
        if args == ["status", "--porcelain"]:
            return "M drift" if drift == "dirty" else ""
        if args == ["rev-parse", "HEAD"]:
            return runtime_sha
        if args == ["rev-parse", "origin/main"]:
            return "b" * 40 if drift in {"origin", "origin-runtime"} else runtime_sha
        if args == ["merge-base", runtime_sha, "b" * 40]:
            return "c" * 40 if drift == "origin" else runtime_sha
        if args == [
            "diff",
            "--name-only",
            runtime_sha,
            "b" * 40,
            "--",
            *publisher.TRANSACTION_RUNTIME_PATHS,
        ]:
            return publisher.TRANSACTION_RUNTIME_PATHS[0] if drift == "origin-runtime" else ""
        raise AssertionError(f"unexpected git command: {args}")

    with pytest.raises(publisher.PublishBlocked, match=message):
        publisher.deployment_preflight(
            actor,
            queue_root,
            state_root,
            expected_repo_root=tmp_path / "other-actor" if drift == "actor" else actor,
            expected_queue_root=tmp_path / "other-queue" if drift == "queue" else queue_root,
            expected_state_root=tmp_path / "other-state" if drift == "state" else state_root,
            expected_runtime_sha="b" * 40 if drift == "runtime" else runtime_sha,
            expected_runtime_digest="d" * 64 if drift == "runtime-digest" else runtime_digest,
            push=drift != "push",
            expected_push_mode="push",
            git=fake_git,
        )


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
    installer = (repo_root / "scripts/install_agy_content_publisher_launchd.sh").read_text(encoding="utf-8")
    plist = plistlib.loads((repo_root / "ops/launchd/com.pantheon.agy-content-publisher.plist.example").read_bytes())
    arguments = plist["ProgramArguments"]

    assert publisher.DEFAULT_MAX_RUNS == 3
    assert 'MAX_RUNS="${PANTHEON_PUBLISH_MAX_RUNS:-3}"' in installer
    assert 'EXACT_RUN_ID="${PANTHEON_PUBLISH_EXACT_RUN_ID:-}"' in installer
    assert "Canary exact run 必須搭配 PANTHEON_PUBLISH_MAX_RUNS=1" in installer
    assert 'NEW_ONLY="${PANTHEON_PUBLISH_NEW_ONLY:-0}"' in installer
    assert "四軌 recovery 禁止 new-only" in installer
    assert arguments[1:3] == ["-m", "scripts.pantheon_content_runtime_manifest"]
    separator = arguments.index("--")
    service_arguments = arguments[separator + 1 :]
    assert service_arguments[1:3] == ["-m", "scripts.agy_content_publisher"]
    assert service_arguments[3:11] == [
        "--repo-root",
        "__REPO_ROOT__",
        "--queue-root",
        "__QUEUE_ROOT__",
        "--state-root",
        "__REPO_ROOT__/.work/content-publisher",
        "--max-runs",
        "__MAX_RUNS__",
    ]
    assert service_arguments[11:] == [
        "--include-rewrites",
        "--push",
        "--expected-repo-root",
        "__REPO_ROOT__",
        "--expected-queue-root",
        "__QUEUE_ROOT__",
        "--expected-state-root",
        "__REPO_ROOT__/.work/content-publisher",
        "--expected-runtime-sha",
        "__RUNTIME_SHA__",
        "--expected-runtime-digest",
        "__RUNTIME_DIGEST__",
        "--expected-push-mode",
        "push",
    ]
    assert 'ACTION="${1:---install}"' in installer
    assert 'USER_HOME_DIR="${PANTHEON_USER_HOME_DIR:-}"' in installer
    assert 'if [[ "${ACTION}" == "--preflight" ]]' in installer
    assert "--deployment-preflight" in installer
    assert "--manifest-authorized-deployment-preflight" in installer
    assert "--runtime-manifest-authority" in installer
    assert "--expected-manifest-digest" in installer
    assert "--exact-run-id" in installer
    assert "runtime_manifest_digest" in installer
    assert "--expected-runtime-digest" in installer
    assert "--expected-python-executable" in installer
    assert 'PYTHON_BIN="${PYTHON_REALPATH}"' in installer
    assert "ProgramArguments:0 ${PYTHON_BIN}" in installer
    assert "ProgramArguments:17 ${PYTHON_BIN}" in installer
    assert 'run_preflight >/dev/null' in installer
    assert 'launchctl bootstrap "gui/${USER_ID}"' not in installer
    assert ".pantheon-four-lane-stage" in installer
    assert plist["EnvironmentVariables"]["PATH"] == "__PATH__"
    assert (
        plist["EnvironmentVariables"]["PANTHEON_PUBLISHER_STDOUT_LOG"]
        == "__STDOUT_LOG__"
    )
    assert (
        plist["EnvironmentVariables"]["PANTHEON_PUBLISHER_STDERR_LOG"]
        == "__STDERR_LOG__"
    )
    assert "PANTHEON_PUBLISHER_STDOUT_LOG" in installer
    assert "PANTHEON_PUBLISHER_STDERR_LOG" in installer
    assert "manifest_field actor_head" in installer
    assert "optional_manifest_field python_executable" in installer
    assert "manifest_field uv_executable" in installer
    assert 'ORIGIN_MAIN_SHA=' not in installer
    assert "PANTHEON_RUNTIME_ACTOR_HEAD" in installer
    assert "PANTHEON_RUNTIME_PYTHON_EXECUTABLE" in installer
    assert "PANTHEON_RUNTIME_UV_EXECUTABLE" in installer
    assert plist["StartInterval"] == 60
    completed = subprocess.run(
        ["bash", "-n", "scripts/install_agy_content_publisher_launchd.sh"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_project_python_command_uses_manifest_bound_uv_with_restricted_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    uv_target = tmp_path / "uv"
    uv_target.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    uv_target.chmod(0o755)
    actor = tmp_path / "actor"
    queue = tmp_path / "queue"
    state = tmp_path / "state"
    logs = tmp_path / "logs"
    for path in (actor, queue, state, logs):
        path.mkdir()
    manifest = runtime_manifest.build_manifest(
        actor_root=actor,
        queue_root=queue,
        publisher_state_root=state,
        log_root=logs,
        identity="publisher-uv-bound",
        uv_executable=uv_target,
    )
    manifest_path = tmp_path / "manifest.json"
    runtime_manifest.write_manifest(manifest_path, manifest)
    formal_environment = {
        "PANTHEON_FORMAL_RUNTIME": "1",
        "PANTHEON_RUNTIME_MANIFEST": str(manifest_path),
        "PANTHEON_RUNTIME_MANIFEST_DIGEST": manifest["manifest_digest"],
        "PANTHEON_RUNTIME_IDENTITY": manifest["identity"],
        "PANTHEON_RUNTIME_IDENTITY_DIGEST": manifest["runtime_identity_digest"],
        "PANTHEON_RUNTIME_CODE_DIGEST": manifest["runtime_digest"],
        "PANTHEON_RUNTIME_CONFIG_VERSION": manifest["config_version"],
        "PANTHEON_RUNTIME_GENERATION": manifest["generation"],
        "PANTHEON_RUNTIME_SERVICE_LABEL": "com.pantheon.agy-content-publisher",
        "PANTHEON_RUNTIME_ACTOR_ROOT": manifest["actor_root"],
        "PANTHEON_RUNTIME_QUEUE_ROOT": manifest["queue_root"],
        "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT": manifest["publisher_state_root"],
        "PANTHEON_RUNTIME_LOG_ROOT": manifest["log_root"],
        "PANTHEON_RUNTIME_UV_EXECUTABLE": manifest["uv_executable"],
    }
    for key, value in formal_environment.items():
        monkeypatch.setenv(key, str(value))
    assert runtime_manifest.validate_runtime_tick(
        "com.pantheon.agy-content-publisher",
        queue_root=queue,
        state_root=state,
        actor_root=actor,
        log_root=logs,
        require_activation_token=False,
    )["status"] == "PASS"
    env = {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "PANTHEON_RUNTIME_UV_EXECUTABLE": str(uv_target),
    }

    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import subprocess; from scripts import agy_content_publisher as p; "
            "subprocess.run(p.PROJECT_PYTHON_COMMAND + ['--version'], check=True)",
        ],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_project_python_command_fails_closed_without_uv_on_restricted_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import subprocess; from scripts import agy_content_publisher as p; "
            "subprocess.run(p.PROJECT_PYTHON_COMMAND + ['--version'], check=True)",
        ],
        cwd=repo_root,
        env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "No such file or directory" in completed.stderr


def test_content_publisher_installer_rejects_python_symlink_to_non_executable(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    python_target = tmp_path / "python-target"
    python_target.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    python_alias = tmp_path / "python-alias"
    python_alias.symlink_to(python_target)
    env = {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "PANTHEON_USER_HOME_DIR": str(tmp_path / "home"),
        "PANTHEON_PYTHON_PATH": str(python_alias),
        "PANTHEON_EXPECTED_RUNTIME_MANIFEST_DIGEST": "a" * 64,
        "TMPDIR": str(tmp_path),
    }

    completed = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts/install_agy_content_publisher_launchd.sh"), "--preflight"],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "找不到 Pantheon Python" in completed.stderr
    assert not (tmp_path / "home").exists()


def _run_content_publisher_installer_authority_case(
    tmp_path: Path,
    *,
    actor_head: str | None,
    local_head: str,
    origin_main: str,
    manifest_runtime_digest: str,
    actual_runtime_digest: str,
    dirty: bool = False,
    manifest_valid: bool = True,
    formal_preflight: bool = False,
) -> subprocess.CompletedProcess[str]:
    repo_root = Path(__file__).resolve().parents[1]
    queue = tmp_path / "queue"
    state = tmp_path / "state"
    logs = tmp_path / "logs"
    fake_bin = tmp_path / "bin"
    for path in (queue / "runs", state, logs, fake_bin):
        path.mkdir(parents=True)
    python_target = tmp_path / "python-target"
    uv_target = tmp_path / "uv-target"
    manifest = tmp_path / "runtime-manifest.json"
    fields = {
        "actor_root": str(repo_root),
        "queue_root": str(queue),
        "publisher_state_root": str(state),
        "log_root": str(logs),
        "manifest_digest": "a" * 64,
        "identity": "gate2-authority-test",
        "runtime_identity_digest": "b" * 64,
        "runtime_digest": manifest_runtime_digest,
        "config_version": "formal-runtime-v2-gate2",
        "generation": "g2-authority-test",
        "python_executable": str(python_target),
        "uv_executable": str(uv_target),
    }
    if actor_head is not None:
        fields["actor_head"] = actor_head
    if formal_preflight:
        python_target.write_text(
            f"#!/bin/sh\nexec {json.dumps(sys.executable)} \"$@\"\n",
            encoding="utf-8",
        )
    else:
        python_target.write_text(
            "\n".join(
                [
                    "#!/bin/sh",
                    "if [ \"$1\" = \"-m\" ] && [ \"$2\" = \"scripts.pantheon_content_runtime_manifest\" ]; then",
                    "  if [ \"$3\" = \"validate\" ]; then",
                    f"    {'exit 0' if manifest_valid else 'echo runtime manifest expected digest mismatch >&2; exit 9'}",
                    "  fi",
                    "  if [ \"$3\" = \"field\" ]; then",
                    "    name=\"\"",
                    "    while [ \"$#\" -gt 0 ]; do",
                    "      if [ \"$1\" = \"--name\" ]; then name=\"$2\"; fi",
                    "      shift",
                    "    done",
                    "    case \"$name\" in",
                    *[
                        f"      {name}) echo \"{value}\" ;;"
                        for name, value in fields.items()
                    ],
                    "      *) echo runtime manifest field missing >&2; exit 8 ;;",
                    "    esac",
                    "    exit 0",
                    "  fi",
                    "fi",
                    "if [ \"$1\" = \"-c\" ]; then",
                    f"  echo \"{actual_runtime_digest}\"",
                    "  exit 0",
                    "fi",
                    "if [ \"$1\" = \"-m\" ] && [ \"$2\" = \"scripts.agy_content_publisher\" ]; then",
                    "  echo '{\"schema_version\":1,\"status\":\"ready\"}'",
                    "  exit 0",
                    "fi",
                    "exit 7",
                    "",
                ]
            ),
            encoding="utf-8",
        )
    python_target.chmod(0o755)
    uv_target.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    uv_target.chmod(0o755)
    if formal_preflight:
        formal_manifest = runtime_manifest.build_manifest(
            actor_root=repo_root,
            queue_root=queue,
            publisher_state_root=state,
            log_root=logs,
            identity="gate2-authority-test",
            runtime_digest=manifest_runtime_digest,
            config_version="formal-runtime-v2-gate2",
            generation="g2-authority-test",
            actor_head=local_head,
            python_executable=python_target,
            uv_executable=uv_target,
        )
        runtime_manifest.write_manifest(manifest, formal_manifest)
        fields = {name: str(value) for name, value in formal_manifest.items()}
    fake_git = fake_bin / "git"
    fake_git.write_text(
        "\n".join(
            [
                "#!/bin/sh",
                "if [ \"$1\" = \"-C\" ]; then shift 2; fi",
                "if [ \"$1\" = \"status\" ] && [ \"$2\" = \"--porcelain\" ]; then",
                f"  {'echo dirty' if dirty else 'exit 0'}",
                "  exit 0",
                "fi",
                "if [ \"$1\" = \"rev-parse\" ] && [ \"$2\" = \"--show-toplevel\" ]; then",
                f"  echo \"{repo_root}\"",
                "  exit 0",
                "fi",
                "if [ \"$1\" = \"rev-parse\" ] && [ \"$2\" = \"HEAD\" ]; then",
                f"  echo \"{local_head}\"",
                "  exit 0",
                "fi",
                "if [ \"$1\" = \"rev-parse\" ] && [ \"$2\" = \"origin/main\" ]; then",
                f"  echo \"{origin_main}\"",
                "  exit 0",
                "fi",
                "exit 6",
                "",
            ]
        ),
        encoding="utf-8",
    )
    fake_git.chmod(0o755)
    env = {
        "PATH": f"{fake_bin}:/usr/bin:/bin:/usr/sbin:/sbin",
        "PANTHEON_USER_HOME_DIR": str(tmp_path / "home"),
        "PANTHEON_PYTHON_PATH": str(python_target),
        "PANTHEON_RUNTIME_MANIFEST_FILE": str(manifest),
        "PANTHEON_EXPECTED_RUNTIME_MANIFEST_DIGEST": fields["manifest_digest"],
        "TMPDIR": str(tmp_path),
    }
    return subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_content_publisher_launchd.sh"),
            "--preflight",
        ],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.mark.skipif(
    not Path("/usr/libexec/PlistBuddy").exists(),
    reason="content publisher installer preflight is macOS launchd specific",
)
def test_content_publisher_installer_accepts_manifest_authorized_detached_actor(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    local_head = "28b8b84b6dfa319d8151aac3bc1a6a819ae82aa1"
    runtime_digest = publisher.runtime_manifest_digest(repo_root)
    completed = _run_content_publisher_installer_authority_case(
        tmp_path,
        actor_head=local_head,
        local_head=local_head,
        origin_main="79bdc809b0b7e17005c5420236dfb71e2bf794c2",
        manifest_runtime_digest=runtime_digest,
        actual_runtime_digest=runtime_digest,
        formal_preflight=True,
    )

    assert completed.returncode == 0, completed.stderr


@pytest.mark.skipif(
    not Path("/usr/libexec/PlistBuddy").exists(),
    reason="content publisher installer preflight is macOS launchd specific",
)
@pytest.mark.parametrize(
    ("overrides", "expected_error"),
    [
        ({"dirty": True}, "publisher actor worktree 不乾淨"),
        ({"local_head": "f" * 40}, "runtime manifest actor_head 不一致"),
        ({"actor_head": None}, "runtime manifest field missing"),
        ({"actor_head": ""}, "runtime manifest actor_head 無效"),
        ({"actor_head": "not-a-sha"}, "runtime manifest actor_head 無效"),
        ({"actual_runtime_digest": "f" * 64}, "publisher runtime digest 與 runtime manifest 不一致"),
        ({"manifest_valid": False}, "runtime manifest expected digest mismatch"),
    ],
)
def test_content_publisher_installer_manifest_authority_fails_closed(
    tmp_path: Path,
    overrides: dict[str, object],
    expected_error: str,
) -> None:
    values: dict[str, object] = {
        "actor_head": "c" * 40,
        "local_head": "c" * 40,
        "origin_main": "d" * 40,
        "manifest_runtime_digest": "e" * 64,
        "actual_runtime_digest": "e" * 64,
    }
    values.update(overrides)

    completed = _run_content_publisher_installer_authority_case(
        tmp_path,
        **values,
    )

    assert completed.returncode != 0
    assert expected_error in completed.stderr


@pytest.mark.skipif(
    not Path("/usr/libexec/PlistBuddy").exists(),
    reason="content publisher installer preflight is macOS launchd specific",
)
def test_content_publisher_installer_accepts_python_symlink_and_uses_realpath(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    queue = tmp_path / "queue"
    state = tmp_path / "state"
    logs = tmp_path / "logs"
    fake_bin = tmp_path / "bin"
    for path in (queue / "runs", state, logs, fake_bin):
        path.mkdir(parents=True)
    python_target = tmp_path / "python-target"
    python_alias = tmp_path / "python-alias"
    manifest = tmp_path / "runtime-manifest.json"
    invocations = tmp_path / "python-invocations.log"
    runtime_digest = "d" * 64
    runtime_sha = "e" * 40
    fields = {
        "actor_root": str(repo_root),
        "queue_root": str(queue),
        "publisher_state_root": str(state),
        "log_root": str(logs),
        "manifest_digest": "a" * 64,
        "identity": "canary-symlink-positive",
        "runtime_identity_digest": "b" * 64,
        "runtime_digest": runtime_digest,
        "config_version": "formal-runtime-v2-canary",
        "generation": "canary-symlink-positive",
        "actor_head": runtime_sha,
        "uv_executable": str(python_target),
    }
    python_target.write_text(
        "\n".join(
            [
                "#!/bin/sh",
                f"echo \"$0 $*\" >> {invocations}",
                "if [ \"$1\" = \"-m\" ] && [ \"$2\" = "
                "\"scripts.pantheon_content_runtime_manifest\" ]; then",
                "  if [ \"$3\" = \"validate\" ]; then",
                "    expected=\"\"",
                "    while [ \"$#\" -gt 0 ]; do",
                "      if [ \"$1\" = \"--expected-python-executable\" ]; then",
                "        expected=\"$2\"",
                "      fi",
                "      shift",
                "    done",
                "    [ \"$expected\" = \"$0\" ] || exit 9",
                "    exit 0",
                "  fi",
                "  if [ \"$3\" = \"field\" ]; then",
                "    name=\"\"",
                "    optional=0",
                "    while [ \"$#\" -gt 0 ]; do",
                "      if [ \"$1\" = \"--name\" ]; then",
                "        name=\"$2\"",
                "      fi",
                "      if [ \"$1\" = \"--optional\" ]; then",
                "        optional=1",
                "      fi",
                "      shift",
                "    done",
                "    case \"$name\" in",
                *[
                    f"      {name}) echo \"{value}\" ;;"
                    for name, value in fields.items()
                ],
                "      *) [ \"$optional\" = 1 ] || exit 8 ;;",
                "    esac",
                "    exit 0",
                "  fi",
                "fi",
                "if [ \"$1\" = \"-c\" ]; then",
                f"  echo \"{runtime_digest}\"",
                "  exit 0",
                "fi",
                "if [ \"$1\" = \"-m\" ] && [ \"$2\" = "
                "\"scripts.agy_content_publisher\" ]; then",
                "  echo '{\"schema_version\":1,\"status\":\"ready\"}'",
                "  exit 0",
                "fi",
                "exit 7",
                "",
            ]
        ),
        encoding="utf-8",
    )
    python_target.chmod(0o755)
    python_alias.symlink_to(python_target)
    fake_git = fake_bin / "git"
    fake_git.write_text(
        "\n".join(
            [
                "#!/bin/sh",
                "if [ \"$1\" = \"-C\" ]; then shift 2; fi",
                "if [ \"$1\" = \"status\" ] && [ \"$2\" = \"--porcelain\" ]; then",
                "  exit 0",
                "fi",
                "if [ \"$1\" = \"rev-parse\" ]; then",
                f"  echo \"{runtime_sha}\"",
                "  exit 0",
                "fi",
                "exit 6",
                "",
            ]
        ),
        encoding="utf-8",
    )
    fake_git.chmod(0o755)
    env = {
        "PATH": f"{fake_bin}:/usr/bin:/bin:/usr/sbin:/sbin",
        "PANTHEON_USER_HOME_DIR": str(tmp_path / "home"),
        "PANTHEON_PYTHON_PATH": str(python_alias),
        "PANTHEON_RUNTIME_MANIFEST_FILE": str(manifest),
        "PANTHEON_EXPECTED_RUNTIME_MANIFEST_DIGEST": "a" * 64,
        "PANTHEON_PUBLISH_EXACT_RUN_ID": "canary-run-001",
        "PANTHEON_PUBLISH_MAX_RUNS": "1",
        "TMPDIR": str(tmp_path),
    }

    completed = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_content_publisher_launchd.sh"),
            "--preflight",
        ],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    lines = invocations.read_text(encoding="utf-8").splitlines()
    assert lines
    assert all(line.startswith(str(python_target)) for line in lines)
    assert any(
        f"--expected-python-executable {python_target}" in line
        for line in lines
    )
    publisher_invocations = [
        line for line in lines if " -m scripts.agy_content_publisher " in line
    ]
    assert len(publisher_invocations) == 1
    assert publisher_invocations[0].count("--exact-run-id") == 1
    assert "canary-run-001" in publisher_invocations[0]
    assert not any(line.startswith(str(python_alias)) for line in lines)


@pytest.mark.skipif(
    not Path("/usr/libexec/PlistBuddy").exists(),
    reason="content publisher installer preflight is macOS launchd specific",
)
@pytest.mark.parametrize("action", ["--preflight", "--install"])
def test_content_publisher_installer_omits_unset_exact_run_args_under_bash32_set_u(
    tmp_path: Path,
    action: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    queue = tmp_path / "queue"
    state = tmp_path / "state"
    logs = tmp_path / "logs"
    fake_bin = tmp_path / "bin"
    home = tmp_path / "home"
    for path in (queue / "runs", state, logs, fake_bin, home / "Library" / "LaunchAgents"):
        path.mkdir(parents=True)
    python_target = tmp_path / "python-target"
    manifest = tmp_path / "runtime-manifest.json"
    invocations = tmp_path / "python-invocations.log"
    runtime_digest = "d" * 64
    runtime_sha = "e" * 40
    fields = {
        "actor_root": str(repo_root),
        "queue_root": str(queue),
        "publisher_state_root": str(state),
        "log_root": str(logs),
        "manifest_digest": "a" * 64,
        "identity": "canary-exact-unset",
        "runtime_identity_digest": "b" * 64,
        "runtime_digest": runtime_digest,
        "config_version": "formal-runtime-v2-canary",
        "generation": "canary-exact-unset",
        "actor_head": runtime_sha,
        "uv_executable": str(python_target),
    }
    python_target.write_text(
        "\n".join(
            [
                "#!/bin/sh",
                f"echo \"$0 $*\" >> {invocations}",
                "if [ \"$1\" = \"-m\" ] && [ \"$2\" = "
                "\"scripts.pantheon_content_runtime_manifest\" ]; then",
                "  if [ \"$3\" = \"validate\" ]; then exit 0; fi",
                "  if [ \"$3\" = \"field\" ]; then",
                "    name=\"\"",
                "    optional=0",
                "    while [ \"$#\" -gt 0 ]; do",
                "      if [ \"$1\" = \"--name\" ]; then name=\"$2\"; fi",
                "      if [ \"$1\" = \"--optional\" ]; then optional=1; fi",
                "      shift",
                "    done",
                "    case \"$name\" in",
                *[
                    f"      {name}) echo \"{value}\" ;;"
                    for name, value in fields.items()
                ],
                "      *) [ \"$optional\" = 1 ] || exit 8 ;;",
                "    esac",
                "    exit 0",
                "  fi",
                "fi",
                "if [ \"$1\" = \"-c\" ]; then",
                f"  echo \"{runtime_digest}\"",
                "  exit 0",
                "fi",
                "if [ \"$1\" = \"-m\" ] && [ \"$2\" = "
                "\"scripts.agy_content_publisher\" ]; then",
                "  case \" $* \" in *\" --exact-run-id \"*) exit 11 ;; esac",
                "  echo '{\"schema_version\":1,\"status\":\"ready\"}'",
                "  exit 0",
                "fi",
                "exit 7",
                "",
            ]
        ),
        encoding="utf-8",
    )
    python_target.chmod(0o755)
    fake_git = fake_bin / "git"
    fake_git.write_text(
        "\n".join(
            [
                "#!/bin/sh",
                "if [ \"$1\" = \"-C\" ]; then shift 2; fi",
                "if [ \"$1\" = \"status\" ] && [ \"$2\" = \"--porcelain\" ]; then exit 0; fi",
                "if [ \"$1\" = \"rev-parse\" ]; then",
                f"  echo \"{runtime_sha}\"",
                "  exit 0",
                "fi",
                "exit 6",
                "",
            ]
        ),
        encoding="utf-8",
    )
    fake_git.chmod(0o755)
    env = {
        "PATH": f"{fake_bin}:/usr/bin:/bin:/usr/sbin:/sbin",
        "PANTHEON_USER_HOME_DIR": str(home),
        "PANTHEON_PYTHON_PATH": str(python_target),
        "PANTHEON_RUNTIME_MANIFEST_FILE": str(manifest),
        "PANTHEON_EXPECTED_RUNTIME_MANIFEST_DIGEST": "a" * 64,
        "TMPDIR": str(tmp_path),
    }

    completed = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_content_publisher_launchd.sh"),
            action,
        ],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    lines = invocations.read_text(encoding="utf-8").splitlines()
    publisher_invocations = [
        line for line in lines if " -m scripts.agy_content_publisher " in line
    ]
    assert len(publisher_invocations) == 1
    assert all("--exact-run-id" not in line for line in publisher_invocations)
    if action == "--install":
        staged = home / "Library" / "LaunchAgents" / ".pantheon-four-lane-stage"
        assert (staged / "com.pantheon.agy-content-publisher.plist").is_file()


def test_four_lane_recovery_publisher_rejects_new_only_before_mutation(
    tmp_path: Path,
) -> None:
    """REG-PANTHEON-FOUR-LANE-REJECT-NEW-ONLY-001。"""
    repo_root = Path(__file__).resolve().parents[1]
    queue = tmp_path / "queue"
    (queue / "runs").mkdir(parents=True)
    env = {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "PANTHEON_USER_HOME_DIR": str(tmp_path / "home"),
        "PANTHEON_PYTHON_PATH": "/usr/bin/true",
        "PANTHEON_GEMINI_QUEUE_ROOT": str(queue),
        "PANTHEON_PUBLISH_NEW_ONLY": "1",
        "TMPDIR": str(tmp_path),
    }

    completed = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts/install_agy_content_publisher_launchd.sh"), "--preflight"],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "四軌 recovery 禁止 new-only" in completed.stderr
    assert not (tmp_path / "home").exists()


def test_publish_ready_runs_new_only_does_not_seed_translations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        publisher,
        "_seed_pending_translations",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("new-only must not seed translations")
        ),
    )
    monkeypatch.setattr(publisher, "collect_ready_runs", lambda *_args, **_kwargs: [])

    def fake_git(
        _repo_root: Path,
        args: list[str],
        _input_text: str | None = None,
    ) -> str:
        if args == ["status", "--porcelain"]:
            return ""
        if args in (["rev-parse", "HEAD"], ["rev-parse", "origin/main"]):
            return "a" * 40
        return ""

    result = publisher.publish_ready_runs(
        tmp_path,
        tmp_path / "queue",
        tmp_path / "state",
        git=fake_git,
        run_tests=False,
        release_gate=False,
        seed_translations=False,
    )

    assert result["status"] == "idle"
    assert result["seeded_translation_runs"] == []


def test_main_new_only_passes_translation_seed_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    captured: dict[str, object] = {}

    def fake_publish(*_args: object, **kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"schema_version": 1, "status": "idle", "published": 0}

    monkeypatch.setattr(
        publisher,
        "parse_args",
        lambda: publisher.argparse.Namespace(
            repo_root=tmp_path,
            queue_root=queue_root,
            state_root=state_root,
            max_runs=3,
            exact_run_id=None,
            exact_fresh_ja_run_id=None,
            prepare_exact_fresh_ja_source_run_id=None,
            prepare_exact_fresh_ja_article_id=None,
            dry_run=True,
            rewrite_release=False,
            include_rewrites=False,
            new_only=True,
            legacy_report=False,
            push=False,
            deployment_preflight=False,
            recover_exhausted_create_run=[],
            skip_tests=False,
            skip_release_gate=False,
            expected_repo_root=None,
            expected_queue_root=None,
            expected_state_root=None,
            expected_runtime_sha=None,
            expected_runtime_digest=None,
            expected_push_mode=None,
        ),
    )
    monkeypatch.setattr(publisher, "publish_ready_runs", fake_publish)

    assert publisher.main() == 0
    assert captured["seed_translations"] is False
    assert json.loads(capsys.readouterr().out)["status"] == "idle"


def test_stage_commit_pushes_release_commit_and_tag_atomically(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    checked: list[list[str]] = []

    def fake_git(_repo_root: Path, args: list[str], _input_text: str | None = None) -> str:
        calls.append(args)
        return "c" * 40 if args == ["rev-parse", "HEAD"] else ""

    monkeypatch.setattr(publisher, "_run_checked", lambda _repo, args: checked.append(args))

    publisher._stage_commit_tag_push(
        Path("/synthetic/repo"),
        "0.3.59",
        fake_git,
        push=True,
        release_gate=True,
    )

    assert checked == [
        [*publisher.PROJECT_PYTHON_COMMAND, "scripts/verify_host_canonical.py"],
        [
            *publisher.PROJECT_PYTHON_COMMAND,
            "scripts/check_release_record.py",
            "--base-ref",
            "origin/main",
            "--require-head-tag",
        ],
    ]
    assert calls[-1] == ["push", "--atomic", "origin", "HEAD:main", "v0.3.59"]


def test_push_checks_live_canonical_host_before_git_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[tuple[str, list[str]]] = []

    def fake_checked(_repo_root: Path, args: list[str]) -> None:
        events.append(("check", args))

    def fake_git(_repo_root: Path, args: list[str], _input_text: str | None = None) -> str:
        events.append(("git", args))
        return "c" * 40 if args == ["rev-parse", "HEAD"] else ""

    monkeypatch.setattr(publisher, "_run_checked", fake_checked)

    publisher._stage_commit_tag_push(
        Path("/synthetic/repo"),
        "0.3.59",
        fake_git,
        push=True,
        release_gate=False,
    )

    assert events[0] == (
        "check",
        [*publisher.PROJECT_PYTHON_COMMAND, "scripts/verify_host_canonical.py"],
    )
    assert events[1][0] == "git"


def test_local_release_does_not_require_live_canonical_host(monkeypatch: pytest.MonkeyPatch) -> None:
    checked: list[list[str]] = []

    monkeypatch.setattr(publisher, "_run_checked", lambda _repo, args: checked.append(args))

    publisher._stage_commit_tag_push(
        Path("/synthetic/repo"),
        "0.3.59",
        lambda _repo, args, _input=None: "c" * 40 if args == ["rev-parse", "HEAD"] else "",
        push=False,
        release_gate=False,
    )

    assert checked == []


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
    monkeypatch.setattr(publisher.pipeline, "load_publication_reference_corpus", lambda _repo: [])
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
    retry_path = publisher._retry_path(state_root, "create", "run-bad")
    retry_state = publisher._read_json(retry_path)
    retry_state["next_eligible_at"] = "2000-01-01T00:00:00+08:00"
    _write_json(retry_path, retry_state)

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
    monkeypatch.setattr(
        publisher,
        "_seed_pending_translations",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("new-only must not seed translations after publish")
        ),
    )
    monkeypatch.setattr(publisher.pipeline, "build_approval", lambda *_args, **_kwargs: {"status": "approved"})

    def apply_good(repo: Path, *_args: object, **_kwargs: object) -> list[Path]:
        target = repo / "app/web/published.txt"
        target.write_text("run-good\n", encoding="utf-8")
        return [target]

    monkeypatch.setattr(publisher.pipeline, "apply_approved_candidates", apply_good)
    monkeypatch.setattr(publisher, "_bump_patch_version", lambda _repo: "0.3.59")
    monkeypatch.setattr(publisher, "_public_article_count", lambda _repo: 1)
    monkeypatch.setattr(publisher, "_run_prerender", lambda _repo, **_kwargs: None)
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
        seed_translations=False,
    )

    assert result["status"] == "PUBLISHED"
    assert result["run_ids"] == ["run-good"]
    assert result["seeded_translation_runs"] == []
    assert published_path.read_text(encoding="utf-8") == "run-good\n"


def test_recovery_retry_uses_collector_selected_run_and_leaves_third_publishable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        publisher.pipeline,
        "load_publication_reference_corpus",
        lambda _repo: [],
    )
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


def test_sync_web_test_release_fixture_does_not_require_public_paths_to_be_adjacent(
    tmp_path: Path,
) -> None:
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    middle_block = (
        "EMERGENCY_PUBLIC_ARTICLE_PATHS = [\n"
        '    "/articles/astrology/astrology-emergency",\n'
        "]\n\n"
        'PUBLIC_ARTICLE_DATE = "2026-07-29"\n\n'
    )
    public_block = (
        "PUBLIC_ARTICLE_PATHS = [\n"
        "    *DAILY_PUBLIC_ARTICLE_PATHS,\n"
        "]\n"
    )
    (test_dir / "test_web.py").write_text(
        'ARTICLE_CACHE_TOKEN = "old-token"\n\n'
        "DAILY_PUBLIC_ARTICLE_PATHS = [\n"
        '    "/articles/astrology/astrology-0115",\n'
        "]\n\n"
        f"{middle_block}"
        f"{public_block}",
        encoding="utf-8",
    )
    article = make_publishable_article("AUTO-NEW")
    article["serial"] = "astrology-0139"
    article["urlSlug"] = "astrology-0139"

    publisher._sync_web_test_release_fixture(
        tmp_path,
        cache_token="new-token",
        articles=[article],
    )
    text = (test_dir / "test_web.py").read_text(encoding="utf-8")

    assert 'ARTICLE_CACHE_TOKEN = "new-token"' in text
    assert text.count('    "/articles/astrology/astrology-0139",\n') == 1
    assert middle_block in text
    assert public_block in text
    assert text.index('    "/articles/astrology/astrology-0139",\n') < text.index(
        "EMERGENCY_PUBLIC_ARTICLE_PATHS"
    )


def test_sync_web_test_release_fixture_preserves_runtime_hub_assertions(
    tmp_path: Path,
) -> None:
    test_dir = tmp_path / "tests"
    static_dir = tmp_path / "app/web/static"
    test_dir.mkdir()
    static_dir.mkdir(parents=True)
    runtime_assertions = (
        "def test_articles_hub_uses_balanced_display_order() -> None:\n"
        '    baseline_paths = [record["path"] for record in data["baseline"]["records"]]\n'
        '    rewritten_paths = [record["path"] for record in data["rewritten"]["records"]]\n'
        "    assert len(baseline_paths) == len(rewritten_paths) == data[\"limit\"]\n"
    )
    (test_dir / "test_web.py").write_text(
        'ARTICLE_CACHE_TOKEN = "old-token"\n\n'
        "DAILY_PUBLIC_ARTICLE_PATHS = [\n"
        '    "/articles/astrology/astrology-0115",\n'
        "]\n\n"
        f"{runtime_assertions}",
        encoding="utf-8",
    )
    (static_dir / "article-registry.js").write_text(
        "export const listArticleRecords = () => [\n"
        '  { serial: "astrology-0115", articleCategory: "astrology" },\n'
        "];\n"
        "export const getArticlePath = (article) => "
        "`/articles/${article.articleCategory}/${article.serial}`;\n",
        encoding="utf-8",
    )
    (static_dir / "articles.js").write_text(
        "export const pickLatestArticles = (articles) => articles;\n",
        encoding="utf-8",
    )
    article = make_publishable_article("AUTO-NEW")
    article["serial"] = "astrology-0139"
    article["urlSlug"] = "astrology-0139"

    publisher._sync_web_test_release_fixture(
        tmp_path,
        cache_token="new-token",
        articles=[article],
    )
    text = (test_dir / "test_web.py").read_text(encoding="utf-8")

    assert 'ARTICLE_CACHE_TOKEN = "new-token"' in text
    assert '    "/articles/astrology/astrology-0139",\n' in text
    assert runtime_assertions in text


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
        '<meta property="article:modified_time" content="2026-07-23" />\n'
        '"dateModified": "2026-07-23",\n'
        '<time datetime="2026-07-23" data-articles-updated>2026-07-23</time>\n'
        '<script type="module" src="/static/articles.js?v=old-token"></script>\n',
        encoding="utf-8",
    )

    publisher._sync_web_test_cache_token(tmp_path, cache_token="agy-i18n-0-3-59")

    assert 'ARTICLE_CACHE_TOKEN = "agy-i18n-0-3-59"' in (test_dir / "test_web.py").read_text(encoding="utf-8")
    assert "static/article.js?v=agy-i18n-0-3-59" in (web_dir / "article.html").read_text(encoding="utf-8")
    hub = (web_dir / "articles.html").read_text(encoding="utf-8")
    assert "static/articles.js?v=agy-i18n-0-3-59" in hub
    assert '<meta property="article:modified_time" content="2026-07-23" />' in hub
    assert '"dateModified": "2026-07-23"' in hub
    assert '<time datetime="2026-07-23" data-articles-updated>2026-07-23</time>' in hub


def test_run_release_tests_runs_fast_preflight_before_full_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(publisher, "_run_checked", lambda _repo, args: calls.append(args))

    publisher._run_release_tests(tmp_path)

    assert calls == [publisher.PREFLIGHT_TEST_COMMAND, publisher.TEST_COMMAND]


def test_preflight_test_command_selectors_resolve_to_top_level_tests() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    functions_by_path: dict[str, set[str]] = {}
    selectors = [argument for argument in publisher.PREFLIGHT_TEST_COMMAND if "::" in argument]

    assert selectors
    for selector in selectors:
        path_text, function_name = selector.split("::", maxsplit=1)
        if path_text not in functions_by_path:
            tree = ast.parse((repo_root / path_text).read_text(encoding="utf-8"))
            functions_by_path[path_text] = {
                node.name
                for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
        assert function_name in functions_by_path[path_text], selector


def test_run_release_tests_skips_full_gate_when_preflight_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []

    def fail_preflight(_repo: Path, args: list[str]) -> None:
        calls.append(args)
        raise subprocess.CalledProcessError(1, args)

    monkeypatch.setattr(publisher, "_run_checked", fail_preflight)

    with pytest.raises(subprocess.CalledProcessError):
        publisher._run_release_tests(tmp_path)

    assert calls == [publisher.PREFLIGHT_TEST_COMMAND]


def test_isolated_transaction_never_mutates_actor_concurrent_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    _write_runtime_manifest_fixture(seed)
    (seed / ".gitignore").write_text(".venv\nnode_modules/\n.work/\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=seed, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=seed, check=True)
    subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=seed, check=True)
    subprocess.run(["git", "push", "-q", "-u", "origin", "main"], cwd=seed, check=True)
    subprocess.run(["git", "clone", "-q", "-b", "main", str(remote), str(actor)], check=True)

    state_root = actor / ".work/content-publisher"
    state_root.mkdir(parents=True)
    actor_venv_python = actor / ".venv/bin/python"
    actor_venv_python.parent.mkdir(parents=True)
    actor_venv_python.write_text("#!/bin/sh\n", encoding="utf-8")
    (actor / "node_modules").mkdir()
    actor_target = actor / "app/web/owned.txt"
    observed_runtime_roots: list[Path] = []

    def fake_validate_runtime_tick(
        _label: str,
        *,
        actor_root: Path,
        **_kwargs: object,
    ) -> dict[str, object]:
        observed_runtime_roots.append(actor_root)
        return {"status": "valid"}

    monkeypatch.setattr(
        publisher.formal_runtime,
        "validate_runtime_tick",
        fake_validate_runtime_tick,
    )
    orphan_parent = state_root / "transaction-orphan"
    orphan_root = orphan_parent / "repo"
    subprocess.run(
        ["git", "worktree", "add", "--detach", str(orphan_root), "origin/main"],
        cwd=actor,
        check=True,
        capture_output=True,
        text=True,
    )
    incomplete_parent = state_root / "transaction-incomplete"
    incomplete_parent.mkdir()
    (incomplete_parent / "partial").write_bytes(b"incomplete\n")

    with publisher._isolated_transaction_worktree(actor, state_root) as transaction_root:
        assert not orphan_parent.exists()
        assert not incomplete_parent.exists()
        assert transaction_root != actor
        assert (transaction_root / "app/web/owned.txt").read_bytes() == b"base\n"
        assert (transaction_root / ".venv").resolve() == (actor / ".venv").resolve()
        assert (transaction_root / "node_modules").is_dir()
        assert publisher._repo_clean(transaction_root)
        publisher._validate_formal_runtime(transaction_root, tmp_path / "queue", state_root)
        assert observed_runtime_roots == [actor]
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


def test_transaction_lifecycle_lock_blocks_concurrent_scavenger(tmp_path: Path) -> None:
    actor = tmp_path / "actor"
    subprocess.run(["git", "init", "-q", str(actor)], check=True)
    lock_path = actor / ".git/agy-content-publisher.lifecycle.lock"

    with lock_path.open("a+") as held_lock:
        fcntl.flock(held_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(publisher.PublishBlocked, match="transaction is busy"):
            with publisher._transaction_lifecycle_lock(actor):
                pytest.fail("busy lifecycle lock must not be entered")


def test_trim_log_file_keeps_only_bounded_tail(tmp_path: Path) -> None:
    log_path = tmp_path / "publisher.log"
    payload = b"old-prefix\n" + b"x" * 96 + b"\nkept-tail\n"
    log_path.write_bytes(payload)

    assert publisher._trim_log_file(log_path, max_bytes=64, retain_bytes=24) is True
    assert log_path.read_bytes() == payload[-24:]
    assert publisher._trim_log_file(log_path, max_bytes=64, retain_bytes=24) is False


def test_isolated_transaction_blocks_stale_actor_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        publisher,
        "TRANSACTION_RUNTIME_PATHS",
        ("scripts/agy_content_publisher.py",),
    )
    actor = tmp_path / "actor"
    transaction = tmp_path / "transaction"
    for root, body in ((actor, b"old\n"), (transaction, b"new\n")):
        path = root / "scripts/agy_content_publisher.py"
        path.parent.mkdir(parents=True)
        path.write_bytes(body)

    with pytest.raises(publisher.PublishBlocked, match="runtime digest differs"):
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
    _write_runtime_manifest_fixture(seed)
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
