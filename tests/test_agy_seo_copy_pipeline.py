from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
import scripts.agy_seo_copy_pipeline as pipeline

from scripts.agy_gemini_outbox import build_external_request
from scripts.agy_seo_copy_pipeline import (
    CandidateValidationError,
    GeminiClient,
    apply_approved_candidates,
    article_sha256,
    body_sha256,
    build_approval,
    build_matrix_backlog,
    invalid_review_payload,
    prepare_matrix_runs,
    prepare_rewrite_batch,
    render_review_markdown,
    review_schema,
    validate_apply_gate,
    validate_candidate,
    validate_new_brief,
    validate_optimize_brief,
    validate_rewrite_brief,
    validate_review,
)
from scripts.gsc_opportunity_brief import (
    BriefSizeError,
    choose_single_property,
    select_opportunities,
    write_bounded_json,
)
from scripts.generate_content_matrix_v2 import build_payload as build_matrix_v2_payload
from scripts.generate_content_matrix_v2 import build_rows as build_matrix_v2_rows


AGY_V1_MATRIX_IDS = {
    "MBTI-INTP-AH",
    "MBTI-INTP-AC",
    "MBTI-INTP-OH",
    "MBTI-INTP-OC",
    "CHART-CYCLE-DECADE",
    "ASC-ARIES",
    "ASC-TAURUS",
    "ASC-GEMINI",
}

AGY_ASC_BATCH_02_IDS = {
    "ASC-CANCER",
    "ASC-LEO",
    "ASC-VIRGO",
    "ASC-LIBRA",
    "ASC-SCORPIO",
}

AGY_ASC_VENUS_BATCH_03_IDS = {
    "ASC-SAGITTARIUS",
    "ASC-CAPRICORN",
    "ASC-AQUARIUS",
    "ASC-PISCES",
    "VENUS-ARIES",
}

AGY_VENUS_BATCH_04_IDS = {
    "VENUS-TAURUS",
    "VENUS-GEMINI",
    "VENUS-CANCER",
    "VENUS-LEO",
    "VENUS-VIRGO",
}

AGY_MATRIX_IDS = AGY_V1_MATRIX_IDS | AGY_ASC_BATCH_02_IDS | AGY_ASC_VENUS_BATCH_03_IDS | AGY_VENUS_BATCH_04_IDS


def test_model_route_config_is_versioned_ordered_and_canonical() -> None:
    route = pipeline.load_model_route_config(pipeline.MODEL_ROUTE_CONFIG_PATH)

    assert route.schema_version == 1
    assert route.routes == {
        "writer": ("gemini-3.5-flash",),
        "reviewer": ("gemini-3.1-pro",),
    }
    assert route.digest == pipeline.load_model_route_config(
        pipeline.MODEL_ROUTE_CONFIG_PATH
    ).digest
    assert pipeline.DEFAULT_WRITER_MODEL == route.routes["writer"][0]
    assert pipeline.DEFAULT_REVIEWER_MODEL == route.routes["reviewer"][0]


def test_model_route_config_digest_is_format_independent(tmp_path: Path) -> None:
    path = tmp_path / "route.json"
    path.write_text(
        json.dumps(
            {
                "routes": {
                    "reviewer": list(pipeline.MODEL_ROUTE_CONFIG.routes["reviewer"]),
                    "writer": list(pipeline.MODEL_ROUTE_CONFIG.routes["writer"]),
                },
                "schema_version": 1,
            },
            indent=4,
        ),
        encoding="utf-8",
    )

    assert pipeline.load_model_route_config(path).digest == (
        pipeline.MODEL_ROUTE_CONFIG_DIGEST
    )


def test_gemini_client_environment_rejects_route_digest_and_model_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGY_GEMINI_MODEL_ROUTE_CONFIG_DIGEST", "0" * 64)
    with pytest.raises(ValueError, match="model route config digest mismatch"):
        GeminiClient.from_environment()

    monkeypatch.setenv(
        "AGY_GEMINI_MODEL_ROUTE_CONFIG_DIGEST",
        pipeline.MODEL_ROUTE_CONFIG_DIGEST,
    )
    monkeypatch.setenv("AGY_WRITER_MODEL", "gemini-drift")
    with pytest.raises(ValueError, match="model route environment drift"):
        GeminiClient.from_environment()


def test_formal_model_route_environment_requires_path_and_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PANTHEON_FORMAL_RUNTIME", "1")
    monkeypatch.delenv("AGY_GEMINI_MODEL_ROUTE_CONFIG", raising=False)
    monkeypatch.delenv("AGY_GEMINI_MODEL_ROUTE_CONFIG_DIGEST", raising=False)

    with pytest.raises(ValueError, match="formal model route config identity is incomplete"):
        pipeline.model_route_config_from_environment()


@pytest.mark.parametrize(
    "payload",
    [
        {"schema_version": True, "routes": {"writer": ["gemini-a"], "reviewer": ["gemini-b"]}},
        {"schema_version": False, "routes": {"writer": ["gemini-a"], "reviewer": ["gemini-b"]}},
        {"schema_version": 1.0, "routes": {"writer": ["gemini-a"], "reviewer": ["gemini-b"]}},
        {"schema_version": "1", "routes": {"writer": ["gemini-a"], "reviewer": ["gemini-b"]}},
        {"schema_version": None, "routes": {"writer": ["gemini-a"], "reviewer": ["gemini-b"]}},
        {"schema_version": 2, "routes": {"writer": ["gemini-a"], "reviewer": ["gemini-b"]}},
        {"schema_version": 1, "routes": {"writer": ["../unsafe"], "reviewer": ["gemini-b"]}},
        {"schema_version": 1, "routes": {"writer": ["gemini-a", "gemini-a"], "reviewer": ["gemini-b"]}},
        {"schema_version": 1, "routes": {"writer": ["gemini-a"], "reviewer": ["gemini-a"]}},
        {"schema_version": 1, "routes": {"writer": [], "reviewer": ["gemini-b"]}},
    ],
)
def test_model_route_config_rejects_invalid_contract(
    tmp_path: Path,
    payload: dict[str, object],
) -> None:
    path = tmp_path / "route.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="model route"):
        pipeline.load_model_route_config(path)
DAILY_QUEUE_IDS = {
    "ASTRO-SCENARIO-SATURN-RETURN",
    "ASTRO-SCENARIO-SEVENTH-HOUSE-EMPTY",
    "ASTRO-SCENARIO-MOON-RISING-DIFFERENCE",
    "ASTRO-SCENARIO-BIG-THREE",
    "ASTRO-SCENARIO-RETROGRADE-PLANETS",
    "ASTRO-SCENARIO-MANY-ASPECTS",
    "ASTRO-SCENARIO-SYNASTRY-ASPECTS",
}
V2_MATRIX_IDS = {row["id"] for row in build_matrix_v2_rows()}


def make_publication_policy(
    *,
    canonical: str = "https://www.mysticpantheon.com/articles/personality/personality-9999",
    published: str = "2026-07-17",
    modified: str = "2026-07-17",
    change_type: str = "created",
    evidence_mode: str = "cultural_reflection",
) -> dict[str, object]:
    identity = pipeline.load_article_publication_policy()["identity"]
    return {
        "policyVersion": pipeline.publication_policy_version(),
        "canonical": canonical,
        "author": {
            "name": identity["author_name"],
            "url": identity["author_url"],
            "id": identity["author_id"],
        },
        "editorialResponsibility": identity["editorial_responsibility"],
        "evidence": {
            "mode": evidence_mode,
            "sources": (
                [
                    {
                        "title": "測試方法來源",
                        "url": "https://example.com/source",
                        "supports": ["測試方法的定義"],
                    }
                ]
                if evidence_mode == "sources"
                else []
            ),
            "disclosure": (
                "本文屬文化脈絡與反思整理，不主張可驗證的預測結果。"
                if evidence_mode == "cultural_reflection"
                else ""
            ),
        },
        "published": published,
        "modified": modified,
        "changeType": change_type,
    }


def test_content_matrix_v2_has_1720_atomic_unique_topics() -> None:
    payload = build_matrix_v2_payload()
    rows = payload["rows"]
    artifact = (
        Path(__file__).resolve().parents[1]
        / "artifacts/fortune_council/content_seo_execution/evidence/content_matrix_v2/content-matrix-v2.json"
    )

    assert payload["total"] == 1720
    assert json.loads(artifact.read_text(encoding="utf-8")) == payload
    assert payload["familyCounts"] == {
        "zodiac": 60,
        "mbti": 80,
        "tarot": 390,
        "ziwei": 70,
        "bazi": 50,
        "mbti_pair": 680,
        "zodiac_pair": 390,
    }
    assert len({row["id"] for row in rows}) == len(rows)
    assert len({row["primaryKeyword"] for row in rows}) == len(rows)
    assert len({row["title"] for row in rows}) == len(rows)
    assert all(20 <= len(row["title"]) <= 45 for row in rows)
    assert all(row["primaryKeyword"] in row["title"] for row in rows)

    atomic_keys = [
        (row["family"], row["entity"], row.get("pairedEntity", ""), row["scenario"])
        for row in rows
    ]
    pair_keys = [
        (row["family"], frozenset((row["entity"], row["pairedEntity"])), row["scenario"])
        for row in rows
        if row["family"].endswith("_pair")
    ]
    assert len(atomic_keys) == len(set(atomic_keys))
    assert len(pair_keys) == len(set(pair_keys))
    assert all("、" not in row["scenario"] for row in rows)


def make_article(article_id: str = "TEST-001") -> dict[str, object]:
    article = {
        "id": article_id,
        "section": "mbti",
        "product": "personality",
        "slug": article_id.lower(),
        "serial": "personality-9999",
        "urlSlug": "personality-9999",
        "primaryKeyword": "測試關鍵字",
        "secondaryKeywords": ["次要詞一", "次要詞二"],
        "title": "測試關鍵字是什麼？用具體場景理解限制與選擇",
        "description": "測試關鍵字適合整理具體情境、可觀察行動與使用限制；本文只提供通用理解，不替個人下結論，也不承諾任何結果。",
        "answer": "測試關鍵字提供通用觀察角度，不能替個人下結論。",
        "tags": ["人格", "自我理解"],
        "published": "2026-07-17",
        "updated": "2026-07-17",
        "faq": [
            {"question": "測試關鍵字能直接判定結果嗎？", "answer": "不能，仍要回到實際情境與行動。"},
            {"question": "應該先看什麼？", "answer": "先分開記錄事實、推測與期待。"},
            {"question": "什麼時候不適用？", "answer": "需要專業判斷時不應只靠這篇文章。"},
        ],
        "bodySections": [
            {
                "heading": "測試關鍵字先看什麼",
                "paragraphs": [
                    "測試關鍵字先用來整理眼前選項；收到合作邀請時，先確認期限、責任與退出條件，再決定是否答應。",
                    "如果對方沒有回覆，先記錄已知事實，不把沉默直接解讀成拒絕。",
                ],
            },
            {
                "heading": "測試關鍵字不能代表什麼",
                "paragraphs": [
                    "這個概念不能預測事件，也不能取代醫療、法律或財務專業意見。",
                    "可以把文章留下的問題改成今天能確認的資料、對話或界線。",
                ],
            },
        ],
    }
    article["publicationPolicy"] = make_publication_policy()
    return article


def make_external_create_article(article: dict[str, object]) -> dict[str, object]:
    return {
        "slot": "article-01",
        "primaryKeyword": article["primaryKeyword"],
        **{
            field: article[field]
            for field in pipeline.PUBLIC_CREATE_FIELDS - {"publicationPolicy"}
        },
    }


def make_deterministic_green_create_article(
    article_id: str = "DETERMINISTIC-GREEN",
) -> dict[str, object]:
    def sized_text(seed: str, size: int) -> str:
        return (seed + "逐項記錄可觀察資料與限制。" * size)[:size]

    article = make_article(article_id)
    article["tags"] = sorted(pipeline.REQUIRED_PUBLIC_TAGS | {"人格", "自我理解"})
    article["description"] = sized_text(
        "測試關鍵字適合整理具體情境與可觀察行動；本文只提供通用理解，不能替個人下結論。",
        84,
    )
    article["bodySections"] = [
        {
            "heading": f"測試關鍵字的具體觀察 {section + 1}",
            "paragraphs": [
                sized_text(
                    (
                        "測試關鍵字先核對情境與限制，再決定下一步。"
                        if section == 0 and paragraph == 0
                        else f"第{section + 1}節第{paragraph + 1}段先核對情境與限制。"
                    ),
                    100,
                )
                for paragraph in range(3)
            ],
        }
        for section in range(5)
    ]
    if article_id in {
        "MBTI-INTP-AH",
        "MBTI-INTP-AC",
        "MBTI-INTP-OH",
        "MBTI-INTP-OC",
    }:
        article["bodySections"][0]["paragraphs"][0] = sized_text(
            "測試關鍵字屬於 Pantheon 64 分支內容；先核對情境與限制，再決定下一步。",
            100,
        )
    assert pipeline.quality_findings([article]) == []
    return article


def test_create_candidate_serialization_is_stable_across_python_hash_seeds() -> None:
    target = make_article()
    brief = {
        "schema_version": 1,
        "run_id": "stable-create-run",
        "mode": "create",
        "articles": [
            {
                "matrix": {"id": target["id"], "title": target["title"], "intent": "公開搜尋意圖"},
                "target": target,
            }
        ],
    }
    external = {"articles": [make_external_create_article(target)]}
    code = (
        "import json,sys; "
        "from scripts.agy_seo_copy_pipeline import hydrate_candidate,public_model_candidate; "
        "brief=json.loads(sys.argv[1]); external=json.loads(sys.argv[2]); "
        "candidate=hydrate_candidate(brief,external); "
        "print(json.dumps(public_model_candidate(brief,candidate),ensure_ascii=False,separators=(',',':')))"
    )

    outputs = []
    for seed in ("1", "2"):
        completed = subprocess.run(
            [sys.executable, "-c", code, json.dumps(brief, ensure_ascii=False), json.dumps(external, ensure_ascii=False)],
            cwd=Path(__file__).resolve().parents[1],
            env={**os.environ, "PYTHONHASHSEED": seed},
            check=True,
            capture_output=True,
            text=True,
        )
        outputs.append(completed.stdout)

    assert outputs[0] == outputs[1]


def make_rewrite_sections(keyword: str = "測試關鍵字", variant: str = "甲") -> list[dict[str, object]]:
    paragraphs: list[str] = []
    seeds = [
        f"{keyword}先回答讀者眼前的疑問：它是一個整理資訊與選擇的角度，不能代替個人判斷。{variant}在會議收到臨時任務時，先記錄期限與責任，再確認自己缺少哪些資料。",
        f"{variant}下班回家看到帳單與課程通知同時出現時，可以列出本月支出、比較時間成本，並詢問承辦人退出條件；這個場景讓抽象概念回到可核對的生活細節。",
        f"另一個例外是資料不足卻急著定案；此時應暫停推測、寫下已知事實，再安排一次短對話。這不代表所有人都要採取相同步驟，仍要觀察情境與後果。",
    ]
    for index in range(15):
        text = f"{seeds[index % len(seeds)]}第{index + 1}段只處理一個具體問題。"
        while len(text) < 96:
            text += "再核對一項可觀察資料。"
        paragraphs.append(text[:118])
    return [
        {"heading": f"{variant}的具體判讀角度 {section + 1}", "paragraphs": paragraphs[section * 3 : section * 3 + 3]}
        for section in range(5)
    ]


def make_rewrite_brief(article_id: str = "REWRITE-001") -> dict[str, object]:
    current = [{"heading": "舊小標", "paragraphs": ["舊正文第一段。", "舊正文第二段。"]}]
    identity = {
        "id": article_id,
        "product": "personality",
        "category": "personality",
        "serial": "personality-0001",
        "slug": "personality-0001",
        "primaryKeyword": "測試關鍵字",
        "title": "測試關鍵字的既有標題",
    }
    immutable = {
        "id": article_id,
        "product": "personality",
        "slug": "personality-0001",
        "serial": "personality-0001",
        "title": "測試關鍵字的既有標題",
        "description": "既有描述",
        "answer": "既有答案",
        "faq": [{"question": "既有問題", "answer": "既有回答"}],
        "tags": ["既有標籤"],
        "published": "2026-07-01",
        "updated": "2026-07-02",
        "urlSlug": "personality-0001",
        "primaryKeyword": "測試關鍵字",
    }
    return {
        "schema_version": 1,
        "run_id": "private-rewrite-run",
        "mode": "rewrite_existing_body",
        "source_commit": "0" * 40,
        "sort_contract": "fixed",
        "articles": [
            {
                "slot": "article-01",
                "article_id": article_id,
                "identity": identity,
                "immutable_fields": immutable,
                "current_body": current,
                "current_body_sha256": body_sha256(current),
                "rewrite_brief": ["先回答搜尋問題", "加入生活場景"],
                "source_file": "app/private-registry.js",
                "body_source": "app/private-body.js",
            }
        ],
    }


def make_rewrite_publication_policy(source: dict[str, object]) -> dict[str, object]:
    identity = source["identity"]
    immutable = source["immutable_fields"]
    return make_publication_policy(
        canonical=(
            "https://www.mysticpantheon.com/articles/"
            f"{identity['category']}/{identity['slug']}"
        ),
        published=str(immutable["published"]),
        modified="2026-07-25",
        change_type="substantive_rewrite",
    )


def make_repair_brief() -> dict[str, object]:
    brief = make_rewrite_brief(pipeline.REWRITE_REPAIR_ARTICLE_IDS[0])
    articles = []
    for index, article_id in enumerate(pipeline.REWRITE_REPAIR_ARTICLE_IDS, start=1):
        item = json.loads(json.dumps(brief["articles"][0], ensure_ascii=False))
        item["slot"] = f"article-{index:02d}"
        item["article_id"] = article_id
        item["identity"]["id"] = article_id
        item["identity"]["serial"] = f"personality-{index:04d}"
        item["identity"]["slug"] = f"personality-{index:04d}"
        item["identity"]["primaryKeyword"] = f"測試關鍵字{index}"
        item["identity"]["title"] = f"測試關鍵字{index}的既有標題"
        item["immutable_fields"]["id"] = article_id
        item["immutable_fields"]["serial"] = f"personality-{index:04d}"
        item["immutable_fields"]["slug"] = f"personality-{index:04d}"
        item["immutable_fields"]["urlSlug"] = f"personality-{index:04d}"
        item["immutable_fields"]["primaryKeyword"] = f"測試關鍵字{index}"
        item["immutable_fields"]["title"] = f"測試關鍵字{index}的既有標題"
        articles.append(item)
    brief["run_id"] = "gemini_rewrite_batch_001_repair_001"
    brief["articles"] = articles
    return brief


def make_batch_002_brief() -> dict[str, object]:
    brief = make_rewrite_brief(pipeline.REWRITE_BATCH_002_ARTICLES[0][1])
    articles = []
    for index, contract in enumerate(pipeline.REWRITE_BATCH_002_ARTICLES, start=1):
        slot, article_id, product, category, serial, slug, keyword, title = contract
        item = json.loads(json.dumps(brief["articles"][0], ensure_ascii=False))
        item["slot"] = slot
        item["article_id"] = article_id
        item["identity"].update({"id": article_id, "product": product, "category": category, "serial": serial, "slug": slug, "primaryKeyword": keyword, "title": title})
        item["immutable_fields"].update({"id": article_id, "product": product, "serial": serial, "slug": slug, "urlSlug": slug, "primaryKeyword": keyword, "title": title})
        articles.append(item)
    brief["run_id"] = "gemini_rewrite_audit_001_batch_02"
    brief["articles"] = articles
    return brief


def test_gsc_selects_at_most_five_rank_4_to_20_low_ctr_pages() -> None:
    rows = []
    for index in range(8):
        rows.append(
            {
                "keys": [f"https://www.mysticpantheon.com/articles/test-{index}", f"query-{index}"],
                "clicks": index,
                "impressions": 1000 - index * 50,
                "ctr": index / 1000,
                "position": 4 + index,
            }
        )
    rows.extend(
        [
            {"keys": ["https://www.mysticpantheon.com/articles/rank-3", "q"], "clicks": 0, "impressions": 5000, "ctr": 0, "position": 3.9},
            {"keys": ["https://www.mysticpantheon.com/articles/high-ctr", "q"], "clicks": 100, "impressions": 1000, "ctr": 0.1, "position": 8},
        ]
    )

    selected = select_opportunities(rows, min_impressions=100, max_ctr=0.03)

    assert len(selected) == 5
    assert all(4 <= item["position"] <= 20 for item in selected)
    assert all(item["ctr"] <= 0.03 for item in selected)
    assert selected[0]["page"].endswith("test-0")


def test_gsc_requires_exactly_one_accessible_property() -> None:
    assert choose_single_property([{"siteUrl": "sc-domain:mysticpantheon.com"}]) == "sc-domain:mysticpantheon.com"
    with pytest.raises(ValueError, match="exactly one"):
        choose_single_property([])
    with pytest.raises(ValueError, match="exactly one"):
        choose_single_property([{"siteUrl": "a"}, {"siteUrl": "b"}])


def test_gsc_brief_enforces_utf8_byte_limit(tmp_path: Path) -> None:
    target = tmp_path / "brief.json"
    with pytest.raises(BriefSizeError):
        write_bounded_json(target, {"text": "字" * 3000}, max_bytes=8192)
    assert not target.exists()


def test_new_brief_limits_each_article_and_batch_size() -> None:
    article = {"matrix": {"id": "A", "title": "題目"}, "policy": "規範"}
    validate_new_brief({"mode": "create", "run_id": "run", "articles": [article] * 5})
    with pytest.raises(ValueError, match="at most 5"):
        validate_new_brief({"mode": "create", "run_id": "run", "articles": [article] * 6})
    with pytest.raises(ValueError, match="8192"):
        validate_new_brief({"mode": "create", "run_id": "run", "articles": [{"matrix": {"id": "A"}, "policy": "字" * 3000}]})

    individually_valid = {"matrix": {"id": "A"}, "policy": "字" * 650}
    with pytest.raises(ValueError, match="whole brief exceeds 8192"):
        validate_new_brief({"mode": "create", "run_id": "run", "articles": [individually_valid] * 5})


def test_gsc_optimize_brief_is_whole_run_bounded() -> None:
    article = {
        "article_id": "A",
        "canonical_path": "/articles/a",
        "source_file": "app/web/static/article-registry.js",
        "current": {"title": "舊標題", "description": "舊描述", "answer": "舊答案"},
    }
    brief = {
        "mode": "optimize",
        "run_id": "gsc",
        "allowed_fields": ["title", "description", "answer"],
        "articles": [article],
    }
    validate_optimize_brief(brief)
    brief["padding"] = "字" * 3000
    with pytest.raises(ValueError, match="8192"):
        validate_optimize_brief(brief)


def test_candidate_is_strict_and_hash_changes_after_tampering() -> None:
    article = make_article()
    validate_candidate({"schema_version": 1, "run_id": "run", "mode": "create", "articles": [article]})
    original = article_sha256(article)
    article["title"] = f"{article['title']}改"
    assert article_sha256(article) != original

    article["unexpected"] = "not allowed"
    with pytest.raises(CandidateValidationError, match="unexpected"):
        validate_candidate({"schema_version": 1, "run_id": "run", "mode": "create", "articles": [article]})


def test_policy_v2_positive_create_and_cultural_disclosure_pass() -> None:
    article = make_article("POLICY-CULTURE-001")
    validate_candidate(
        {
            "schema_version": 1,
            "run_id": "policy-culture-create",
            "mode": "create",
            "articles": [article],
        }
    )
    assert article["publicationPolicy"]["evidence"]["mode"] == "cultural_reflection"
    assert article["publicationPolicy"]["evidence"]["sources"] == []


@pytest.mark.parametrize(
    "claim",
    [
        "某項研究顯示，採用這個方法的人有 73％表示壓力降低。",
        "統計資料指出，這套練習能提高判斷正確率。",
        "這套方法已被證實能降低焦慮並改善決策品質。",
    ],
)
def test_policy_v2_cultural_reflection_with_verifiable_claim_requires_real_source(
    claim: str,
) -> None:
    article = make_article("POLICY-CULTURE-CLAIM")
    article["bodySections"][0]["paragraphs"].append(claim)

    with pytest.raises(CandidateValidationError, match="article_level_evidence"):
        validate_candidate(
            {
                "schema_version": 1,
                "run_id": "policy-culture-claim",
                "mode": "create",
                "articles": [article],
            }
        )


def test_policy_v2_positive_rewrite_passes_same_validator() -> None:
    brief = make_rewrite_brief("POLICY-REWRITE-001")
    source = brief["articles"][0]
    article = {
        "article_id": source["article_id"],
        "identity": source["identity"],
        "current_body_sha256": source["current_body_sha256"],
        "bodySections": make_rewrite_sections(),
        "publicationPolicy": make_rewrite_publication_policy(source),
    }
    validate_candidate(
        {
            "schema_version": 1,
            "run_id": "policy-rewrite",
            "mode": "rewrite_existing_body",
            "articles": [article],
        }
    )


def test_policy_v2_noop_rewrite_fails_even_when_declared_substantive() -> None:
    brief = make_rewrite_brief("POLICY-NOOP")
    source = brief["articles"][0]
    current_body = make_rewrite_sections(variant="原")
    source["current_body"] = current_body
    source["current_body_sha256"] = body_sha256(current_body)
    article = {
        "article_id": source["article_id"],
        "identity": source["identity"],
        "current_body_sha256": source["current_body_sha256"],
        "bodySections": current_body,
        "publicationPolicy": make_rewrite_publication_policy(source),
    }

    with pytest.raises(CandidateValidationError, match="no_substantive_change"):
        validate_candidate(
            {
                "schema_version": 1,
                "run_id": "policy-noop",
                "mode": "rewrite_existing_body",
                "articles": [article],
            }
        )


def test_policy_v2_presentation_constraints_are_loaded_for_create_and_rewrite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy = json.loads(
        json.dumps(pipeline.load_article_publication_policy(), ensure_ascii=False)
    )
    create_profile = policy["presentation_constraints"]["profiles"]["create"]
    create_profile.update(
        {
            "title_characters": {"minimum": 1, "maximum": 1000},
            "description_characters": {"minimum": 1, "maximum": 1000},
            "answer_characters": {"maximum": 1000},
            "faq_items": {"minimum": 1, "maximum": 10},
            "body_characters": {"minimum": 1, "maximum": 10000},
            "body_sections": {"minimum": 1},
            "paragraphs_per_section": {"minimum": 1, "maximum": 10},
            "paragraph_characters": {"minimum": 1, "maximum": 1000},
        }
    )
    policy["presentation_constraints"]["profiles"]["rewrite_existing_body"][
        "paragraph_characters"
    ] = {"minimum": 1, "maximum": 100}
    monkeypatch.setattr(pipeline, "_POLICY_V2_CACHE", policy)

    create_codes = {
        finding["code"]
        for finding in pipeline.quality_findings([make_article("POLICY-PROFILE-CREATE")])
    }
    assert not create_codes & {
        "title_length",
        "description_length",
        "answer_length",
        "body_length",
        "section_count",
        "paragraph_count",
        "paragraph_length",
    }

    brief = make_rewrite_brief("POLICY-PROFILE-REWRITE")
    source = brief["articles"][0]
    rewrite = {
        "article_id": source["article_id"],
        "identity": source["identity"],
        "current_body_sha256": source["current_body_sha256"],
        "bodySections": make_rewrite_sections(),
        "publicationPolicy": make_rewrite_publication_policy(source),
    }
    rewrite_codes = {
        finding["code"]
        for finding in pipeline.rewrite_quality_findings(brief, [rewrite])
    }
    assert "paragraph_length" in rewrite_codes
    rewrite_schema = pipeline.candidate_schema("rewrite_existing_body")
    paragraph_schema = rewrite_schema["properties"]["articles"]["items"][
        "properties"
    ]["bodySections"]["items"]["properties"]["paragraphs"]
    assert paragraph_schema["items"]["maxLength"] == 100


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("author", "author_identity"),
        ("fallback_date", "truthful_dates"),
        ("fact_without_source", "article_level_evidence"),
    ],
)
def test_policy_v2_required_negative_contracts_fail_closed(
    mutation: str,
    expected_code: str,
) -> None:
    article = make_article(f"POLICY-NEG-{mutation}")
    if mutation == "author":
        article["publicationPolicy"]["author"]["name"] = "無法識別的作者"
    elif mutation == "fallback_date":
        article["updated"] = "fallback-date"
        article["publicationPolicy"]["modified"] = "2026-07-10"
    else:
        article["publicationPolicy"]["evidence"] = {
            "mode": "sources",
            "sources": [],
            "disclosure": "",
        }
    with pytest.raises(CandidateValidationError, match=expected_code):
        validate_candidate(
            {
                "schema_version": 1,
                "run_id": f"policy-neg-{mutation}",
                "mode": "create",
                "articles": [article],
            }
        )


def test_policy_v2_cross_corpus_duplicate_is_required() -> None:
    article = make_article("POLICY-NEW")
    reference = json.loads(json.dumps(article, ensure_ascii=False))
    reference["id"] = "POLICY-EXISTING"
    reference["urlSlug"] = "personality-8888"
    reference["serial"] = "personality-8888"
    findings = pipeline.article_publication_policy_findings(
        article,
        mode="create",
        reference_articles=[reference],
    )
    assert "cross_corpus_originality" in {finding["code"] for finding in findings}


def test_policy_v2_rewrite_cannot_bypass_publication_contract() -> None:
    brief = make_rewrite_brief("POLICY-BYPASS")
    source = brief["articles"][0]
    article = {
        "article_id": source["article_id"],
        "identity": source["identity"],
        "current_body_sha256": source["current_body_sha256"],
        "bodySections": make_rewrite_sections(),
    }
    with pytest.raises(CandidateValidationError, match="publicationPolicy"):
        validate_candidate(
            {
                "schema_version": 1,
                "run_id": "policy-bypass",
                "mode": "rewrite_existing_body",
                "articles": [article],
            }
        )


def test_invalid_reviewer_json_becomes_deterministic_rejection() -> None:
    article = make_article()
    rejected = invalid_review_payload("run", [article], "invalid_reviewer_json")
    validate_review(rejected, [article])
    assert rejected["articles"][0]["verdict"] == "REJECT"
    markdown = render_review_markdown(rejected)
    assert "REJECT" in markdown
    assert "invalid_reviewer_json" in markdown
    detailed = render_review_markdown(rejected, [article])
    assert str(article["title"]) in detailed
    assert str(article["bodySections"][0]["paragraphs"][0]) in detailed


def test_review_must_bind_each_candidate_hash() -> None:
    article = make_article()
    review = {
        "schema_version": 1,
        "run_id": "run",
        "articles": [
            {
                "article_id": article["id"],
                "candidate_sha256": "0" * 64,
                "verdict": "APPROVE",
                "findings": [],
            }
        ],
    }
    with pytest.raises(ValueError, match="candidate hash"):
        validate_review(review, [article])


def test_writer_and_reviewer_requests_have_independent_contexts() -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def transport(model: str, payload: dict[str, object]) -> dict[str, object]:
        calls.append((model, payload))
        return {"ok": True}

    client = GeminiClient(api_key="redacted", transport=transport)
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}
    client.generate_json("writer", "writer prompt", schema)
    client.generate_json("reviewer", "reviewer prompt", schema)

    assert calls[0][0] != calls[1][0]
    assert calls[0][1]["contents"] != calls[1][1]["contents"]
    assert "previous_interaction_id" not in calls[0][1]
    assert "previous_interaction_id" not in calls[1][1]
    assert calls[0][1]["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "LOW"}
    assert calls[1][1]["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "LOW"}
    assert "hard_failure" not in review_schema()["properties"]["articles"]["items"]["properties"]


@pytest.mark.parametrize("model", ["gemini-2.5-flash", "gemini-2.5-flash-lite"])
def test_gemini_25_flash_models_use_compatible_generation_config(model: str) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def transport(model: str, payload: dict[str, object]) -> dict[str, object]:
        calls.append((model, payload))
        return {"ok": True}

    client = GeminiClient(
        api_key="redacted",
        writer_model=model,
        transport=transport,
    )
    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "minItems": 1,
                "maxItems": 5,
                "items": {
                    "type": "string",
                    "minLength": 20,
                    "maxLength": 160,
                },
            }
        },
        "required": ["items"],
    }
    client.generate_json("writer", "writer prompt", schema)

    generation_config = calls[0][1]["generationConfig"]
    assert generation_config["thinkingConfig"] == {"thinkingBudget": 0}
    assert "thinkingLevel" not in generation_config["thinkingConfig"]
    assert generation_config["responseJsonSchema"] == {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {"type": "string"},
            }
        },
        "required": ["items"],
    }
    assert schema["properties"]["items"]["minItems"] == 1
    assert schema["properties"]["items"]["items"]["minLength"] == 20


@pytest.mark.parametrize("model", ["gemini-3.5-flash-lite", "gemini-3.6-flash"])
def test_latest_gemini_models_omit_deprecated_sampling_parameters(model: str) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def transport(model: str, payload: dict[str, object]) -> dict[str, object]:
        calls.append((model, payload))
        return {"ok": True}

    client = GeminiClient(
        api_key="redacted",
        writer_model=model,
        transport=transport,
    )
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}
    client.generate_json("writer", "writer prompt", schema)

    generation_config = calls[0][1]["generationConfig"]
    assert "temperature" not in generation_config
    assert "topP" not in generation_config
    assert "topK" not in generation_config
    assert generation_config["thinkingConfig"] == {"thinkingLevel": "LOW"}
    assert generation_config["responseJsonSchema"] is schema


def test_gemini_35_flash_lite_strips_only_large_provider_enums() -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def transport(model: str, payload: dict[str, object]) -> dict[str, object]:
        calls.append((model, payload))
        return {"ok": True}

    client = GeminiClient(
        api_key="redacted",
        writer_model="gemini-3.5-flash-lite",
        transport=transport,
    )
    schema = {
        "type": "object",
        "properties": {
            "outline_slot": {
                "type": "string",
                "enum": ["h2-1", "h2-2", "h2-3", "h2-4"],
            },
            "source_fact_id": {
                "type": "string",
                "enum": [f"fact-{index:02d}" for index in range(17)],
            },
        },
        "required": ["outline_slot", "source_fact_id"],
    }

    client.generate_json("writer", "writer prompt", schema)

    provider_schema = calls[0][1]["generationConfig"]["responseJsonSchema"]
    assert provider_schema["properties"]["outline_slot"]["enum"] == [
        "h2-1",
        "h2-2",
        "h2-3",
        "h2-4",
    ]
    assert "enum" not in provider_schema["properties"]["source_fact_id"]
    assert len(schema["properties"]["source_fact_id"]["enum"]) == 17


def test_antigravity_cli_transport_uses_low_models_and_fresh_processes(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_run(args: list[str], **kwargs: object) -> object:
        cwd = Path(str(kwargs["cwd"]))
        calls.append({"args": args, "cwd": cwd})
        return pipeline.subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=json.dumps({"ok": True}),
            stderr="",
        )

    monkeypatch.setenv("AGY_GEMINI_CLI", "/opt/tools/agy-1.1.3")
    monkeypatch.setattr(pipeline.subprocess, "run", fake_run)
    client = GeminiClient.from_environment()
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}

    assert client.generate_json("writer", "write", schema) == {"ok": True}
    assert client.generate_json("reviewer", "review", schema) == {"ok": True}

    assert len(calls) == 2
    assert calls[0]["cwd"] != calls[1]["cwd"]
    for call in calls:
        args = call["args"]
        assert args[0] == "/opt/tools/agy-1.1.3"
        assert "--print" in args
        assert "--mode" in args and "plan" in args
        assert "--sandbox" in args
        assert "--resume" not in args
        assert "--continue" not in args
        assert "--conversation" not in args
    assert calls[0]["args"][2] == "Gemini 3.5 Flash (Low)"
    assert calls[1]["args"][2] == "Gemini 3.1 Pro (Low)"


def test_antigravity_cli_capability_preflight_checks_both_models() -> None:
    calls: list[list[str]] = []

    def fake_run(args: list[str], **_kwargs: object) -> object:
        calls.append(args)
        if args[-1] == "models":
            return pipeline.subprocess.CompletedProcess(
                args,
                0,
                "gemini-3.5-flash-low\tGemini 3.5 Flash (Low)\n"
                "gemini-3.1-pro-low\tGemini 3.1 Pro (Low)\n",
                "",
            )
        return pipeline.subprocess.CompletedProcess(args, 0, "{}\n", "")

    receipt = pipeline.validate_antigravity_cli_capabilities(
        ["/opt/tools/agy-1.1.3"],
        runner=fake_run,
    )

    assert receipt == {
        "status": "PASS",
        "writer_model": "gemini-3.5-flash",
        "reviewer_model": "gemini-3.1-pro",
    }
    assert calls[0] == ["/opt/tools/agy-1.1.3", "models"]
    assert [call[2] for call in calls[1:]] == [
        "Gemini 3.5 Flash (Low)",
        "Gemini 3.1 Pro (Low)",
    ]


def test_antigravity_cli_capability_preflight_rejects_missing_model() -> None:
    def fake_run(args: list[str], **_kwargs: object) -> object:
        return pipeline.subprocess.CompletedProcess(
            args,
            0,
            "gemini-3.5-flash-low\tGemini 3.5 Flash (Low)\n",
            "",
        )

    with pytest.raises(ValueError, match="reviewer model is unavailable"):
        pipeline.validate_antigravity_cli_capabilities(
            ["/opt/tools/agy-1.1.3"],
            runner=fake_run,
        )


def test_antigravity_cli_capability_preflight_reports_closed_smoke_diagnostic() -> None:
    private_detail = "/Users/example/private GEMINI_API_KEY=must-not-persist"

    def fake_run(args: list[str], **_kwargs: object) -> object:
        if args[-1] == "models":
            return pipeline.subprocess.CompletedProcess(
                args,
                0,
                "gemini-3.5-flash-low\tGemini 3.5 Flash (Low)\n"
                "gemini-3.1-pro-low\tGemini 3.1 Pro (Low)\n",
                "",
            )
        return pipeline.subprocess.CompletedProcess(
            args,
            1,
            "",
            "Error: Eligibility check failed: UNAVAILABLE (code 503): " + private_detail,
        )

    with pytest.raises(ValueError) as raised:
        pipeline.validate_antigravity_cli_capabilities(
            ["/opt/tools/agy-1.1.3"],
            runner=fake_run,
        )

    assert "category=ELIGIBILITY_UNAVAILABLE" in str(raised.value)
    assert "http_status=503" in str(raised.value)
    assert "stderr_sha256=" in str(raised.value)
    assert private_detail not in str(raised.value)


def test_content_cli_transport_is_independent_from_v4_broker_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(args: list[str], **_kwargs: object) -> object:
        calls.append(args)
        return pipeline.subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=json.dumps({"ok": True}),
            stderr="",
        )

    monkeypatch.setenv("AGY_GEMINI_TRANSPORT", "cli")
    monkeypatch.setenv("AGY_GEMINI_V4_BROKER", "1")
    monkeypatch.delenv("AGY_GEMINI_V4_EXECUTABLE", raising=False)
    monkeypatch.delenv("AGY_GEMINI_V4_EXECUTABLE_SHA256", raising=False)
    monkeypatch.setenv("AGY_GEMINI_CLI", "/opt/tools/agy-1.1.3")
    monkeypatch.setattr(pipeline.subprocess, "run", fake_run)

    client = GeminiClient.from_environment()
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}

    assert client.generate_json("writer", "write", schema) == {"ok": True}
    assert len(calls) == 1
    assert calls[0][0] == "/opt/tools/agy-1.1.3"


def test_production_single_request_transport_disables_redirects() -> None:
    handler = pipeline._NoRedirectHandler()

    assert (
        handler.redirect_request(
            pipeline.urllib.request.Request("https://example.invalid"),
            None,
            302,
            "must not follow",
            {},
            "https://redirect.invalid",
        )
        is None
    )


@pytest.mark.parametrize(
    ("http_status", "expected_code", "expected_status_class"),
    [
        (400, "API_HTTP_ERROR", "4xx"),
        (401, "API_AUTH", "4xx"),
        (403, "API_AUTH", "4xx"),
        (404, "API_MODEL_UNAVAILABLE", "4xx"),
        (429, "API_RATE_LIMITED", "4xx"),
        (500, "API_HTTP_ERROR", "5xx"),
        (503, "API_HTTP_ERROR", "5xx"),
    ],
)
def test_production_http_failure_exposes_only_sanitized_status_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
    http_status: int,
    expected_code: str,
    expected_status_class: str,
) -> None:
    private_body = b"GEMINI_API_KEY=must-not-persist provider response body"

    def fail_provider(provider_request: object, **_kwargs: object) -> object:
        raise pipeline.urllib.error.HTTPError(
            getattr(provider_request, "full_url", "https://example.invalid"),
            http_status,
            "private-provider-detail",
            {},
            io.BytesIO(private_body),
        )

    monkeypatch.setattr(pipeline, "_single_request_urlopen", fail_provider)
    client = GeminiClient(api_key="redacted")

    with pytest.raises(pipeline.GeminiApiFailure) as raised:
        client._single_request_http_transport("gemini-test", {"safe": True})

    assert raised.value.error_code == expected_code
    assert raised.value.http_status == http_status
    assert raised.value.http_status_class == expected_status_class
    assert private_body.decode() not in str(raised.value)


@pytest.mark.parametrize(
    ("reason", "expected_code"),
    [
        ("RATE_LIMIT_EXCEEDED", "API_RATE_LIMITED"),
        ("QUOTA_EXCEEDED", "API_RATE_LIMITED"),
        ("UNRECOGNIZED_REASON", "API_RATE_LIMITED"),
    ],
)
def test_production_429_does_not_infer_daily_quota_from_error_info_reason(
    monkeypatch: pytest.MonkeyPatch,
    reason: str,
    expected_code: str,
) -> None:
    private_marker = "private-quota-detail-must-not-persist"
    body = json.dumps(
        {
            "error": {
                "details": [
                    {
                        "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                        "reason": reason,
                        "metadata": {"private": private_marker},
                    }
                ]
            }
        }
    ).encode()

    def fail_provider(provider_request: object, **_kwargs: object) -> object:
        raise pipeline.urllib.error.HTTPError(
            getattr(provider_request, "full_url", "https://example.invalid"),
            429,
            "private-provider-detail",
            {},
            io.BytesIO(body),
        )

    monkeypatch.setattr(pipeline, "_single_request_urlopen", fail_provider)
    client = GeminiClient(api_key="redacted")

    with pytest.raises(pipeline.GeminiApiFailure) as raised:
        client._single_request_http_transport("gemini-test", {"safe": True})

    assert raised.value.error_code == expected_code
    assert raised.value.http_status == 429
    assert private_marker not in str(raised.value)


@pytest.mark.parametrize(
    ("quota_id", "expected_code"),
    [
        (
            "GenerateRequestsPerDayPerProjectPerModel-FreeTier",
            "API_QUOTA",
        ),
        (
            "GenerateRequestsPerMinutePerProjectPerModel-FreeTier",
            "API_RATE_LIMITED",
        ),
    ],
)
def test_production_429_classifies_real_generate_content_quota_failure(
    quota_id: str,
    expected_code: str,
) -> None:
    body = json.dumps(
        {
            "error": {
                "code": 429,
                "status": "RESOURCE_EXHAUSTED",
                "details": [
                    {
                        "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                        "reason": "QUOTA_EXCEEDED",
                    },
                    {
                        "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                        "violations": [
                            {
                                "quotaMetric": "private-metric-must-not-persist",
                                "quotaId": quota_id,
                                "quotaDimensions": {
                                    "model": "private-model-detail"
                                },
                            }
                        ],
                    }
                ],
            }
        }
    ).encode()
    error = pipeline.urllib.error.HTTPError(
        "https://example.invalid",
        429,
        "private-provider-detail",
        {},
        io.BytesIO(body),
    )

    assert pipeline._gemini_error_code_for_http_error(error) == expected_code


@pytest.mark.parametrize(
    ("failure", "expected_code"),
    [
        ("nonzero", "CLI_NONZERO"),
        ("timeout", "CLI_TIMEOUT"),
        ("not-found", "CLI_NOT_FOUND"),
        ("envelope", "CLI_ENVELOPE_ERROR"),
    ],
)
def test_cli_transport_exposes_only_closed_failure_code(
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    expected_code: str,
) -> None:
    private_detail = "/Users/example/private prompt GEMINI_API_KEY=must-not-persist"

    def fake_run(args: list[str], **_kwargs: object) -> object:
        if failure == "timeout":
            raise subprocess.TimeoutExpired(args, timeout=1, stderr=private_detail)
        if failure == "not-found":
            raise FileNotFoundError(private_detail)
        if failure == "nonzero":
            return pipeline.subprocess.CompletedProcess(args, 7, "", private_detail)
        return pipeline.subprocess.CompletedProcess(
            args,
            0,
            json.dumps({"error": private_detail}),
            "",
        )

    monkeypatch.setenv("AGY_GEMINI_CLI", "/opt/tools/gemini")
    monkeypatch.setattr(pipeline.subprocess, "run", fake_run)
    client = GeminiClient.from_environment()

    with pytest.raises(RuntimeError) as raised:
        client.generate_json("writer", private_detail, {"type": "object"})

    assert getattr(raised.value, "error_code", None) == expected_code
    assert private_detail not in str(raised.value)


def test_external_model_brief_excludes_private_repo_metadata() -> None:
    brief = {
        "schema_version": 1,
        "run_id": "private-run-id",
        "mode": "create",
        "source": {"type": "matrix", "path": "private/cluster_plan.md"},
        "articles": [
            {
                "matrix": {
                    "id": "PRIVATE-ID",
                    "primaryKeyword": "公開主題",
                    "title": "公開主題是什麼？公開標題方向",
                    "intent": "公開搜尋意圖",
                },
                "target": {
                    "id": "PRIVATE-ID",
                    "section": "mbti",
                    "product": "personality",
                    "slug": "private-slug",
                    "serial": "personality-9999",
                    "urlSlug": "private-url",
                    "primaryKeyword": "公開主題",
                    "published": "2026-07-18",
                    "updated": "2026-07-18",
                },
                "policy": pipeline.compact_publication_policy(),
            }
        ],
    }

    public = pipeline.public_model_brief(brief)
    encoded = json.dumps(public, ensure_ascii=False)

    assert public["articles"][0]["slot"] == "article-01"
    assert public["articles"][0]["primaryKeyword"] == "公開主題"
    assert public["articles"][0]["titleDirection"] == "公開主題是什麼？公開標題方向"
    assert public["articles"][0]["searchIntent"] == "公開搜尋意圖"
    for secret in ["private-run-id", "PRIVATE-ID", "private-slug", "personality-9999", "private-url", "cluster_plan.md"]:
        assert secret not in encoded


def test_create_writer_prompt_requires_description_local_boundary() -> None:
    brief = {
        "schema_version": 1,
        "run_id": "prompt-boundary",
        "mode": "create",
        "articles": [
            {
                "matrix": {
                    "id": "PROMPT-BOUNDARY",
                    "primaryKeyword": "土星回歸",
                    "title": "土星回歸是什麼？",
                    "intent": "理解人生階段",
                },
                "target": {
                    "id": "PROMPT-BOUNDARY",
                    "section": "astrology",
                    "product": "astrology",
                    "slug": "saturn-return",
                    "serial": "astrology-0115",
                    "urlSlug": "saturn-return",
                    "primaryKeyword": "土星回歸",
                    "published": "2026-07-23",
                    "updated": "2026-07-23",
                },
                "policy": pipeline.compact_publication_policy(),
            }
        ],
    }

    prompt = pipeline._writer_prompt(brief)

    assert "meta description 欄位本身必須明寫" in prompt
    assert "不得只把限制放在正文" in prompt
    assert "正文第一段第一句必須完整且連續包含該篇 primaryKeyword" in prompt
    assert pipeline.publication_presentation_instruction("create") in prompt
    assert "publicationPolicy 由本機可信資料補齊" in prompt
    assert "不得寫入研究、統計、百分比或方法型主張" in prompt
    assert "每節2 到 4段" in prompt
    assert "每節以 3 段為初稿目標" in prompt
    assert "description 以 80 到 90 個中文字為初稿目標" in prompt
    assert "初稿每段以 95 到 110 字為生成目標" in prompt
    assert "即使是否定句也改用其他說法" in prompt


def test_create_repair_prompt_includes_measured_targets_for_lite_writer() -> None:
    article = make_article("PROMPT-REPAIR")
    article["description"] = "這段描述太短，不能替個人下結論。"
    article["bodySections"] = article["bodySections"][:1]
    brief = {
        "schema_version": 1,
        "run_id": "prompt-repair",
        "mode": "create",
        "articles": [
            {
                "matrix": {
                    "id": article["id"],
                    "primaryKeyword": article["primaryKeyword"],
                    "title": article["title"],
                    "intent": "公開搜尋意圖",
                },
                "target": {
                    field: article[field]
                    for field in ["id", "section", "product", "slug", "serial", "urlSlug", "primaryKeyword", "published", "updated"]
                },
                "policy": pipeline.compact_publication_policy(),
            }
        ],
    }
    candidate = {
        "schema_version": 1,
        "run_id": brief["run_id"],
        "mode": "create",
        "articles": [article],
    }
    findings = [
        {"article_id": article["id"], "code": "description_length", "message": "meta description 必須為 70 到 95 字"},
        {"article_id": article["id"], "code": "body_length", "message": "正文不足"},
        {"article_id": article["id"], "code": "paragraph_length", "message": "段落不足"},
        {"article_id": article["id"], "code": "banned_phrase", "message": "命中禁詞：保證"},
    ]

    prompt = pipeline._writer_prompt(brief, candidate, findings)

    assert '"description_characters":' in prompt
    assert '"body_characters":' in prompt
    assert '"section_count":' in prompt
    assert '"paragraph_characters":' in prompt
    assert "description 修復目標為 80 到 90 字" in prompt
    assert "正文修復目標為 5 節、每節 3 段、每段 95 到 110 字" in prompt
    assert "逐一移除 findings 指出的禁詞" in prompt
    assert pipeline.publication_presentation_instruction("create") in prompt
    assert "description 以 80 到 90 個中文字為初稿目標" in prompt


def test_rewrite_initial_and_repair_prompts_include_generation_contract() -> None:
    brief = make_rewrite_brief()
    source = brief["articles"][0]
    article = {
        "article_id": source["article_id"],
        "identity": source["identity"],
        "current_body_sha256": source["current_body_sha256"],
        "bodySections": make_rewrite_sections(),
        "publicationPolicy": make_rewrite_publication_policy(source),
    }
    candidate = {
        "schema_version": 1,
        "run_id": brief["run_id"],
        "mode": "rewrite_existing_body",
        "articles": [article],
    }
    finding = {
        "article_id": source["article_id"],
        "code": "paragraph_length",
        "message": "第 1 節第 1 段為 131 字；必須 90 到 130 字",
    }

    prompts = [
        pipeline._writer_prompt(brief),
        pipeline._writer_prompt(brief, candidate, [finding]),
    ]

    for prompt in prompts:
        assert pipeline.publication_presentation_instruction(
            "rewrite_existing_body"
        ) in prompt
        assert "正文以 1500 到 1800 字為生成目標" in prompt
        assert "每段以 95 到 110 字為生成目標" in prompt
        assert "130 字是硬上限" in prompt
        assert "不得在同一篇內逐字重複完整段落" in prompt


def test_standalone_answer_repair_fields_only_authorize_answer() -> None:
    article = make_article("STANDALONE-ANSWER-REPAIR")
    article["answer"] = "太短"
    finding = {
        "article_id": article["id"],
        "code": "standalone_answer",
        "message": "answer 必須可獨立理解",
    }

    fields = pipeline._create_repair_fields(article, [finding])
    contract = pipeline._create_repair_contract(
        {
            "schema_version": 1,
            "run_id": "standalone-answer-repair",
            "mode": "create",
            "articles": [article],
        },
        [finding],
    )
    properties = pipeline.external_create_repair_schema(contract)["properties"][
        "articles"
    ]["items"]["properties"]

    assert fields == {"answer"}
    assert contract == {"article-01": ("answer",)}
    assert set(properties) == {"slot", "answer"}


def test_repair_fields_cover_all_repairable_deterministic_create_codes() -> None:
    article = make_article("DETERMINISTIC-REPAIR-FIELDS")
    expected = {
        "answer_length": {"answer"},
        "body_length": {"bodySections"},
        "body_length_insufficient": {"bodySections"},
        "cross_corpus_originality": {"bodySections"},
        "description_boundary": {"description"},
        "description_context_and_limit": {"description"},
        "description_length": {"description"},
        "explicit_limit_or_counterexample": {"bodySections"},
        "missing_boundary": {"description"},
        "missing_pantheon_context": {"bodySections"},
        "opening_keyword": {"bodySections"},
        "opening_primary_intent": {"bodySections"},
        "paragraph_count": {"bodySections"},
        "paragraph_length": {"bodySections"},
        "paragraph_length_violation": {"bodySections"},
        "repeated_sentence": {"bodySections"},
        "required_tags": {"tags"},
        "section_count": {"bodySections"},
        "standalone_answer": {"answer"},
        "title_keyword": {"title"},
        "title_length": {"title"},
        "title_primary_intent": {"title"},
    }

    actual = {
        code: pipeline._create_repair_fields(
            article,
            [{"article_id": article["id"], "code": code, "message": code}],
            deterministic_findings=True,
        )
        for code in expected
    }

    assert actual == expected


def test_false_social_origin_repair_fields_follow_actual_matching_fields() -> None:
    def with_false_origin(*fields: str) -> dict[str, object]:
        article = make_deterministic_green_create_article("MBTI-INTP-AH")
        if "title" in fields:
            article["title"] = "測試關鍵字不是網路論壇俗稱，仍須核對具體情境與限制"
        if "description" in fields:
            seed = "測試關鍵字並非網路論壇俗稱；本文只提供通用理解，不能替個人下結論。"
            article["description"] = (seed + "仍須核對情境與資料限制。" * 10)[:84]
        if "answer" in fields:
            article["answer"] = "測試關鍵字並非網路論壇俗稱，不能替個人下結論。"
        if "bodySections" in fields:
            seed = "測試關鍵字屬於 Pantheon 64 分支內容，並非網路論壇俗稱；先核對具體情境與限制。"
            article["bodySections"][0]["paragraphs"][0] = (
                seed + "逐項記錄可觀察資料。" * 20
            )[:100]
        return article

    for field in ["title", "description", "answer", "bodySections"]:
        article = with_false_origin(field)
        findings = pipeline.quality_findings([article])
        assert {finding["code"] for finding in findings} == {
            "false_social_origin"
        }
        assert pipeline._create_repair_fields(
            article,
            findings,
            deterministic_findings=True,
        ) == {field}

    article = with_false_origin("title", "answer")
    findings = pipeline.quality_findings([article])
    assert pipeline._create_repair_fields(
        article,
        findings,
        deterministic_findings=True,
    ) == {"title", "answer"}

    unlocatable = make_deterministic_green_create_article("MBTI-INTP-AH")
    unlocatable["title"] = "測試關鍵字的具體情境與限制需逐項查證於網友"
    seed = "常被俗稱的說法仍須核對具體情境；本文只提供通用理解，不能替個人下結論。"
    unlocatable["description"] = (seed + "仍須核對資料與使用限制。" * 10)[:84]
    findings = pipeline.quality_findings([unlocatable])
    assert {finding["code"] for finding in findings} == {"false_social_origin"}
    with pytest.raises(
        CandidateValidationError,
        match="unmapped deterministic create finding: false_social_origin",
    ):
        pipeline._create_repair_fields(
            unlocatable,
            findings,
            deterministic_findings=True,
        )


def test_false_social_origin_bounded_create_repair_is_strict_and_byte_stable() -> None:
    article = make_deterministic_green_create_article("MBTI-INTP-AH")
    article["title"] = "測試關鍵字不是網路論壇俗稱，仍須核對具體情境與限制"
    findings = pipeline.quality_findings([article])
    candidate = {
        "schema_version": 1,
        "run_id": "false-social-origin-repair",
        "mode": "create",
        "articles": [article],
    }
    unchanged_bytes = {
        field: pipeline.compact_json_bytes(value)
        for field, value in article.items()
        if field != "title"
    }
    contract = pipeline._create_repair_contract(
        candidate,
        findings,
        deterministic_findings=True,
    )
    properties = pipeline.external_create_repair_schema(contract)["properties"][
        "articles"
    ]["items"]["properties"]

    assert contract == {"article-01": ("title",)}
    assert set(properties) == {"slot", "title"}
    repaired = pipeline.hydrate_create_repair(
        candidate,
        {
            "articles": [
                {
                    "slot": "article-01",
                    "title": "測試關鍵字的具體情境與限制：先核對資料再做選擇",
                }
            ]
        },
        contract,
    )
    assert pipeline.quality_findings(repaired["articles"]) == []
    assert {
        field: pipeline.compact_json_bytes(value)
        for field, value in repaired["articles"][0].items()
        if field != "title"
    } == unchanged_bytes
    with pytest.raises(
        CandidateValidationError,
        match="external create repair fields differ from contract",
    ):
        pipeline.hydrate_create_repair(
            candidate,
            {
                "articles": [
                    {
                        "slot": "article-01",
                        "title": "測試關鍵字的具體情境與限制：先核對資料再做選擇",
                        "answer": article["answer"],
                    }
                ]
            },
            contract,
        )


def test_repair_fields_locate_dynamic_deterministic_create_codes() -> None:
    cases = [
        ("banned_phrase", "命中禁詞：自訂禁詞", "answer", "自訂禁詞"),
        (
            "generic_ai_phrase",
            "命中模板或假場景詞：自訂模板詞",
            "description",
            "自訂模板詞",
        ),
        (
            "article_level_evidence",
            "文化/反思內容偵測到需 evidence 的主張",
            "title",
            "某項研究顯示",
        ),
        (
            "no_outcome_guarantee",
            "禁止結果保證：自訂結果保證",
            "answer",
            "自訂結果保證",
        ),
        (
            "no_professional_advice_substitution",
            "禁止專業替代建議：自訂專業替代",
            "bodySections",
            "自訂專業替代",
        ),
    ]

    for code, message, field, phrase in cases:
        article = make_article(f"DYNAMIC-{code}")
        if field == "bodySections":
            article[field][0]["paragraphs"][0] = phrase
        else:
            article[field] = phrase
        assert pipeline._create_repair_fields(
            article,
            [{"article_id": article["id"], "code": code, "message": message}],
            deterministic_findings=True,
        ) == {field}


def test_repair_fields_fail_closed_only_for_deterministic_unmapped_findings() -> None:
    article = make_article("UNMAPPED-DETERMINISTIC-REPAIR")
    deterministic_unmapped_codes = {
        "author_identity",
        "canonical_consistency",
        "cultural_reflection_disclosure",
        "future_deterministic_code",
        "invalid_policy_contract",
        "missing_policy_contract",
        "policy_version",
        "substantive_modified_date",
        "truthful_dates",
    }

    for code in deterministic_unmapped_codes:
        with pytest.raises(
            CandidateValidationError,
            match=f"unmapped deterministic create finding: {code}",
        ):
            pipeline._create_repair_contract(
                {
                    "schema_version": 1,
                    "run_id": "unmapped-deterministic-repair",
                    "mode": "create",
                    "articles": [article],
                },
                [{"article_id": article["id"], "code": code, "message": code}],
                deterministic_findings=True,
            )

    for code in ["copy", "TEMPLATE_STRUCTURE", "search_intent_mismatch"]:
        assert pipeline._create_repair_contract(
            {
                "schema_version": 1,
                "run_id": "reviewer-directed-repair",
                "mode": "create",
                "articles": [article],
            },
            [{"article_id": article["id"], "code": code, "message": code}],
        ) == {"article-01": ("bodySections",)}


def test_bounded_create_repair_answer_merge_preserves_unauthorized_field_bytes() -> None:
    article = make_article("PARTIAL-ANSWER-REPAIR")
    article["answer"] = "太短"
    candidate = {
        "schema_version": 1,
        "run_id": "partial-answer-repair",
        "mode": "create",
        "articles": [article],
    }
    finding = {
        "article_id": article["id"],
        "code": "standalone_answer",
        "message": "answer 必須可獨立理解",
    }
    unchanged_bytes = {
        field: pipeline.compact_json_bytes(value)
        for field, value in article.items()
        if field != "answer"
    }
    contract = pipeline._create_repair_contract(
        candidate,
        [finding],
        deterministic_findings=True,
    )

    repaired = pipeline.hydrate_create_repair(
        candidate,
        {
            "articles": [
                {
                    "slot": "article-01",
                    "answer": "測試關鍵字提供通用觀察角度，不能替個人下結論。",
                }
            ]
        },
        contract,
    )

    assert {
        field: pipeline.compact_json_bytes(value)
        for field, value in repaired["articles"][0].items()
        if field != "answer"
    } == unchanged_bytes
    with pytest.raises(
        CandidateValidationError,
        match="external create repair fields differ from contract",
    ):
        pipeline.hydrate_create_repair(
            candidate,
            {
                "articles": [
                    {
                        "slot": "article-01",
                        "answer": "測試關鍵字提供通用觀察角度，不能替個人下結論。",
                        "bodySections": article["bodySections"],
                    }
                ]
            },
            contract,
        )


def test_bounded_create_repair_clears_short_answer_before_reviewer_gate() -> None:
    article = make_deterministic_green_create_article("SHORT-ANSWER-GATE")
    article["answer"] = "太短"
    candidate = {
        "schema_version": 1,
        "run_id": "short-answer-gate",
        "mode": "create",
        "articles": [article],
    }
    findings = pipeline.quality_findings([article])
    assert {finding["code"] for finding in findings} == {"standalone_answer"}
    contract = pipeline._create_repair_contract(
        candidate,
        findings,
        deterministic_findings=True,
    )

    repaired = pipeline.hydrate_create_repair(
        candidate,
        {
            "articles": [
                {
                    "slot": "article-01",
                    "answer": "測試關鍵字提供通用觀察角度，不能替個人下結論。",
                }
            ]
        },
        contract,
    )

    assert pipeline.quality_findings(repaired["articles"]) == []


def test_run_writer_reviewer_repairs_standalone_answer_before_review(
    tmp_path: Path,
) -> None:
    article = make_deterministic_green_create_article("SHORT-ANSWER-E2E")
    article["answer"] = "太短"
    repaired_answer = "測試關鍵字提供通用觀察角度，不能替個人下結論。"
    unchanged_bytes = {
        field: pipeline.compact_json_bytes(value)
        for field, value in article.items()
        if field != "answer"
    }
    brief = {
        "schema_version": 1,
        "run_id": "short-answer-e2e",
        "mode": "create",
        "articles": [
            {
                "matrix": {
                    "id": article["id"],
                    "primaryKeyword": article["primaryKeyword"],
                    "title": article["title"],
                    "intent": "公開搜尋意圖",
                },
                "target": {
                    field: article[field]
                    for field in [
                        "id",
                        "section",
                        "product",
                        "slug",
                        "serial",
                        "urlSlug",
                        "primaryKeyword",
                        "published",
                        "updated",
                    ]
                },
                "policy": pipeline.compact_publication_policy(),
            }
        ],
    }
    pipeline.write_json(tmp_path / "brief.json", brief)

    class RecordingClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def __init__(self) -> None:
            self.calls: list[str] = []

        def generate_json(
            self,
            role: str,
            prompt: str,
            schema: dict[str, object],
        ) -> dict[str, object]:
            self.calls.append(role)
            if role == "writer" and self.calls.count("writer") == 1:
                return {"articles": [make_external_create_article(article)]}
            if role == "writer":
                properties = schema["properties"]["articles"]["items"]["properties"]  # type: ignore[index]
                assert set(properties) == {"slot", "answer"}
                assert '"standalone_answer"' in prompt
                return {
                    "articles": [
                        {
                            "slot": "article-01",
                            "answer": repaired_answer,
                        }
                    ]
                }
            assert self.calls == ["writer", "writer", "reviewer"]
            assert repaired_answer in prompt
            assert "public deterministic findings:\n[]" in prompt
            return {
                "articles": [
                    {
                        "slot": "article-01",
                        "verdict": "APPROVE",
                        "findings": [],
                    }
                ]
            }

    client = RecordingClient()
    candidate, review = pipeline.run_writer_reviewer(
        tmp_path,
        client,
        max_repairs=1,
    )
    evidence = json.loads((tmp_path / "run-evidence.json").read_text())
    repaired = candidate["articles"][0]

    assert client.calls == ["writer", "writer", "reviewer"]
    assert repaired["answer"] == repaired_answer
    assert {
        field: pipeline.compact_json_bytes(value)
        for field, value in repaired.items()
        if field != "answer"
    } == unchanged_bytes
    assert pipeline.quality_findings([repaired]) == []
    assert review["articles"][0]["verdict"] == "APPROVE"
    assert evidence["schema_repairs_used"] == 0
    assert evidence["content_repairs_used"] == 1
    assert evidence["attempts"] == 2


def test_create_machine_length_repair_is_field_bounded_and_reviews_only_after_green(
    tmp_path: Path,
) -> None:
    def sized_paragraph(label: str, size: int) -> str:
        seed = f"{label}先核對具體情境、已知資料與可調整限制，再決定下一步。"
        return (seed + "逐項記錄觀察與行動。" * size)[:size]

    def sized_description(size: int) -> str:
        seed = "測試關鍵字用來整理具體情境與可觀察行動；本文只提供通用理解，不能替個人下結論。"
        return (seed + "仍須回到現況與資料判斷。" * size)[:size]

    article = make_article("BOUNDED-CREATE-REPAIR")
    article["tags"] = sorted(pipeline.REQUIRED_PUBLIC_TAGS | {"人格", "自我理解"})
    article["description"] = sized_description(61)
    article["bodySections"] = [
        {
            "heading": f"測試關鍵字的具體觀察 {section + 1}",
            "paragraphs": [
                sized_paragraph(
                    (
                        "測試關鍵字"
                        if section == 0 and paragraph == 0
                        else f"第{section + 1}節第{paragraph + 1}段"
                    ),
                    116 if section == 0 and paragraph < 2 else 117,
                )
                for paragraph in range(4 if section < 3 else 3)
            ],
        }
        for section in range(5)
    ]
    assert len(str(article["description"])) == 61
    assert sum(
        len(str(paragraph))
        for section in article["bodySections"]
        for paragraph in section["paragraphs"]
    ) == 2104
    repaired_description = sized_description(84)
    repaired_body = [
        {
            "heading": f"測試關鍵字的修復觀察 {section + 1}",
            "paragraphs": [
                sized_paragraph(
                    (
                        "測試關鍵字"
                        if section == 0 and paragraph == 0
                        else f"修復第{section + 1}節第{paragraph + 1}段"
                    ),
                    100,
                )
                for paragraph in range(3)
            ],
        }
        for section in range(5)
    ]
    initial_findings = pipeline.quality_findings([article])
    assert {finding["code"] for finding in initial_findings} == {
        "body_length",
        "description_length",
    }

    brief = {
        "schema_version": 1,
        "run_id": "bounded-create-repair",
        "mode": "create",
        "articles": [
            {
                "matrix": {
                    "id": article["id"],
                    "primaryKeyword": article["primaryKeyword"],
                    "title": article["title"],
                    "intent": "公開搜尋意圖",
                },
                "target": {
                    field: article[field]
                    for field in [
                        "id",
                        "section",
                        "product",
                        "slug",
                        "serial",
                        "urlSlug",
                        "primaryKeyword",
                        "published",
                        "updated",
                    ]
                },
                "policy": pipeline.compact_publication_policy(),
            }
        ],
    }
    run_dir = tmp_path / "bounded-create-repair"
    run_dir.mkdir()
    pipeline.write_json(run_dir / "brief.json", brief)

    class BoundedClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def __init__(self) -> None:
            self.writer_calls = 0
            self.reviewer_calls = 0

        def generate_json(
            self,
            role: str,
            prompt: str,
            schema: dict[str, object],
        ) -> dict[str, object]:
            if role == "writer":
                self.writer_calls += 1
                if self.writer_calls == 1:
                    return {"articles": [make_external_create_article(article)]}
                repair_properties = schema["properties"]["articles"]["items"]["properties"]  # type: ignore[index]
                assert set(repair_properties) == {
                    "slot",
                    "description",
                    "bodySections",
                }
                assert "bounded field repair" in prompt
                assert "不得輸出完整 candidate" in prompt
                assert "產生完整文章內容" not in prompt
                return {
                    "articles": [
                        {
                            "slot": "article-01",
                            "description": repaired_description,
                            "bodySections": repaired_body,
                        }
                    ]
                }
            self.reviewer_calls += 1
            return {
                "articles": [
                    {
                        "slot": "article-01",
                        "verdict": "APPROVE",
                        "findings": [],
                    }
                ]
            }

    client = BoundedClient()
    candidate, review = pipeline.run_writer_reviewer(
        run_dir,
        client,
        max_repairs=1,
    )

    repaired = candidate["articles"][0]
    assert repaired["description"] == repaired_description
    assert repaired["bodySections"] == repaired_body
    for field in pipeline.PUBLIC_CREATE_FIELDS - {
        "description",
        "bodySections",
    }:
        assert repaired[field] == article[field]
    assert pipeline.quality_findings([repaired]) == []
    assert review["articles"][0]["verdict"] == "APPROVE"
    assert client.writer_calls == 2
    assert client.reviewer_calls == 1


def test_create_transport_schema_excludes_deterministic_publication_envelope() -> None:
    article_schema = pipeline.external_candidate_schema("create")["properties"]["articles"]["items"]

    assert "publicationPolicy" not in article_schema["properties"]
    assert "evidence" not in article_schema["properties"]


def test_run_cli_accepts_zero_content_repairs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["agy_seo_copy_pipeline.py", "run", ".work/gsc-copy/daily", "--max-repairs", "0"],
    )

    args = pipeline.parse_args()

    assert args.command == "run"
    assert args.max_repairs == 0


def test_external_gsc_brief_drops_metrics_paths_and_internal_ids() -> None:
    brief = {
        "schema_version": 1,
        "run_id": "gsc-private",
        "mode": "optimize",
        "source": {"type": "gsc", "property": "sc-domain:private.example"},
        "allowed_fields": ["title", "description", "answer"],
        "articles": [
            {
                "article_id": "INTERNAL-001",
                "canonical_path": "/articles/private/path",
                "source_file": "app/web/static/private.js",
                "clicks": 1,
                "impressions": 999,
                "ctr": 0.001,
                "position": 8.2,
                "queries": [{"query": "公開搜尋詞", "impressions": 999, "clicks": 1}],
                "current": {"title": "公開標題", "description": "公開描述", "answer": "公開答案"},
            }
        ],
    }

    public = pipeline.public_model_brief(brief)
    encoded = json.dumps(public, ensure_ascii=False)

    assert public["articles"][0] == {
        "slot": "article-01",
        "focusPhrases": ["公開搜尋詞"],
        "current": {"title": "公開標題", "description": "公開描述", "answer": "公開答案"},
    }
    for secret in ["gsc-private", "private.example", "INTERNAL-001", "/articles/private/path", "private.js", "999", "0.001", "8.2"]:
        assert secret not in encoded


def test_rewrite_public_brief_keeps_content_contract_but_drops_private_paths_and_run() -> None:
    brief = make_rewrite_brief()

    validate_rewrite_brief(brief)
    public = pipeline.public_model_brief(brief)
    encoded = json.dumps(public, ensure_ascii=False)

    assert public["mode"] == "rewrite_existing_body"
    assert public["articles"][0]["identity"]["id"] == "REWRITE-001"
    assert public["articles"][0]["currentBody"] == brief["articles"][0]["current_body"]
    assert public["articles"][0]["rewriteBrief"] == ["先回答搜尋問題", "加入生活場景"]
    assert "immutableFields" in public
    for private in ["private-rewrite-run", "private-registry.js", "private-body.js", "source_commit", "app/"]:
        assert private not in encoded


def test_rewrite_writer_can_return_only_body_and_local_hydration_locks_identity() -> None:
    brief = make_rewrite_brief()
    body = make_rewrite_sections()
    external = {
        "articles": [
            {
                "slot": "article-01",
                "bodySections": body,
                "publicationPolicy": make_rewrite_publication_policy(brief["articles"][0]),
            }
        ]
    }

    schema_fields = set(pipeline.external_candidate_schema("rewrite_existing_body")["properties"]["articles"]["items"]["properties"])
    candidate = pipeline.hydrate_candidate(brief, external)

    assert schema_fields == {"slot", "bodySections", "publicationPolicy"}
    assert candidate["mode"] == "rewrite_existing_body"
    assert candidate["articles"][0]["identity"] == brief["articles"][0]["identity"]
    assert candidate["articles"][0]["current_body_sha256"] == brief["articles"][0]["current_body_sha256"]
    assert candidate["articles"][0]["bodySections"] == body
    with pytest.raises(CandidateValidationError, match="slot, bodySections"):
        pipeline.hydrate_candidate(
            brief,
            {
                "articles": [
                    {
                        "slot": "article-01",
                        "bodySections": body,
                        "publicationPolicy": make_rewrite_publication_policy(brief["articles"][0]),
                        "title": "企圖改標題",
                    }
                ]
            },
        )


def test_rewrite_provider_schema_removes_only_string_length_keywords() -> None:
    canonical_body = pipeline.candidate_schema("rewrite_existing_body")[
        "properties"
    ]["articles"]["items"]["properties"]["bodySections"]
    provider_body = pipeline.external_candidate_schema(
        "rewrite_existing_body"
    )["properties"]["articles"]["items"]["properties"]["bodySections"]
    expected_provider_body = json.loads(
        json.dumps(canonical_body, ensure_ascii=False)
    )
    canonical_paragraph = expected_provider_body["items"]["properties"][
        "paragraphs"
    ]["items"]
    minimum = canonical_paragraph.pop("minLength")
    maximum = canonical_paragraph.pop("maxLength")

    assert provider_body == expected_provider_body
    assert (minimum, maximum) == pipeline._range_bounds(
        pipeline.publication_presentation_profile("rewrite_existing_body"),
        "paragraph_characters",
    )
    canonical_create_body = pipeline.candidate_schema("create")[
        "properties"
    ]["articles"]["items"]["properties"]["bodySections"]
    provider_create_body = pipeline.external_candidate_schema("create")[
        "properties"
    ]["articles"]["items"]["properties"]["bodySections"]
    expected_create_provider_body = json.loads(
        json.dumps(canonical_create_body, ensure_ascii=False)
    )
    canonical_create_paragraph = expected_create_provider_body["items"][
        "properties"
    ]["paragraphs"]["items"]
    create_minimum = canonical_create_paragraph.pop("minLength")
    create_maximum = canonical_create_paragraph.pop("maxLength")

    assert provider_create_body == expected_create_provider_body
    assert (create_minimum, create_maximum) == pipeline._range_bounds(
        pipeline.publication_presentation_profile("create"),
        "paragraph_characters",
    )


def test_create_transport_short_paragraph_reaches_local_repair_gate() -> None:
    target = make_deterministic_green_create_article("CREATE-SHORT-PARAGRAPH")
    brief = {
        "schema_version": 1,
        "run_id": "create-short-paragraph-transport",
        "mode": "create",
        "articles": [
            {
                "matrix": {
                    "id": target["id"],
                    "primaryKeyword": target["primaryKeyword"],
                    "title": target["title"],
                    "intent": "公開搜尋意圖",
                },
                "target": {
                    field: target[field]
                    for field in [
                        "id",
                        "section",
                        "product",
                        "slug",
                        "serial",
                        "urlSlug",
                        "primaryKeyword",
                        "published",
                        "updated",
                    ]
                },
                "policy": pipeline.compact_publication_policy(),
            }
        ],
    }
    external = {"articles": [make_external_create_article(target)]}
    external["articles"][0]["bodySections"][0]["paragraphs"][0] = "太短"

    candidate = pipeline.hydrate_candidate(brief, external, enforce_policy=False)
    findings = pipeline.quality_findings(candidate["articles"])

    assert any(finding["code"] == "paragraph_length" for finding in findings)
    assert pipeline._create_repair_fields(candidate["articles"][0], findings) == {
        "bodySections"
    }
    assert pipeline.candidate_schema("create")["properties"]["articles"]["items"][
        "properties"
    ]["bodySections"]["items"]["properties"]["paragraphs"]["items"]["minLength"] > 0


def test_create_normalization_reads_paragraph_bounds_from_canonical_schema() -> None:
    target = make_deterministic_green_create_article("CREATE-NORMALIZE-PARAGRAPH")
    response_schema = pipeline.external_candidate_schema("create")
    paragraph_items = response_schema["properties"]["articles"]["items"][
        "properties"
    ]["bodySections"]["items"]["properties"]["paragraphs"]["items"]
    assert "minLength" not in paragraph_items
    assert "maxLength" not in paragraph_items
    payload = {"articles": [make_external_create_article(target)]}
    section = payload["articles"][0]["bodySections"][0]
    original = "".join(section["paragraphs"])
    section["paragraphs"] = [original[:100], original[100:]]

    normalized = pipeline.normalize_new_output_contract(payload, response_schema)

    assert normalized is not None
    paragraphs = normalized["articles"][0]["bodySections"][0]["paragraphs"]
    assert 2 <= len(paragraphs) <= 4
    assert all(80 <= len(paragraph) <= 160 for paragraph in paragraphs)
    assert "".join(paragraphs) == original


def test_rewrite_hydration_locks_publication_metadata_and_preserves_evidence() -> None:
    brief = make_rewrite_brief()
    source = brief["articles"][0]
    source["identity"]["slug"] = "semantic-personality-slug"
    generated_policy = make_rewrite_publication_policy(source)
    generated_policy.update(
        {
            "policyVersion": "writer-guessed-policy",
            "canonical": "https://example.com/guessed-route",
            "author": {
                "name": "Writer 猜測作者",
                "url": "https://example.com/authors/writer",
                "id": "writer",
            },
            "editorialResponsibility": "Writer 猜測責任文字",
            "published": "2020-01-01",
            "modified": "2020-01-02",
            "changeType": "created",
        }
    )
    candidate = pipeline.hydrate_candidate(
        brief,
        {
            "articles": [
                {
                    "slot": "article-01",
                    "bodySections": make_rewrite_sections(),
                    "publicationPolicy": generated_policy,
                }
            ]
        },
    )

    hydrated = candidate["articles"][0]["publicationPolicy"]
    policy = pipeline.load_article_publication_policy()
    identity = policy["identity"]
    assert hydrated == {
        "policyVersion": policy["policy_version"],
        "canonical": "https://www.mysticpantheon.com/articles/personality/personality-0001",
        "author": {
            "name": identity["author_name"],
            "url": identity["author_url"],
            "id": identity["author_id"],
        },
        "editorialResponsibility": identity["editorial_responsibility"],
        "evidence": generated_policy["evidence"],
        "published": source["immutable_fields"]["published"],
        "modified": pipeline.date.today().isoformat(),
        "changeType": "substantive_rewrite",
    }
    findings = pipeline.rewrite_quality_findings(brief, candidate["articles"])
    assert not [
        finding
        for finding in findings
        if finding["code"] == "canonical_consistency"
    ]


def test_rewrite_deterministic_gate_enforces_shape_intent_scenarios_actions_and_uniqueness() -> None:
    first_brief = make_rewrite_brief("REWRITE-001")
    second_brief = make_rewrite_brief("REWRITE-002")
    second_item = second_brief["articles"][0]
    second_item["slot"] = "article-02"
    second_item["identity"]["serial"] = "personality-0002"
    second_item["identity"]["slug"] = "personality-0002"
    second_item["immutable_fields"]["serial"] = "personality-0002"
    second_item["immutable_fields"]["slug"] = "personality-0002"
    second_item["immutable_fields"]["urlSlug"] = "personality-0002"
    brief = first_brief
    brief["articles"].append(second_item)
    first_body = make_rewrite_sections(variant="甲")
    second_body = make_rewrite_sections(variant="乙")
    second_body[0]["paragraphs"][0] = first_body[0]["paragraphs"][0]
    candidates = [
        {
            "article_id": "REWRITE-001",
            "identity": brief["articles"][0]["identity"],
            "current_body_sha256": brief["articles"][0]["current_body_sha256"],
            "bodySections": first_body,
        },
        {
            "article_id": "REWRITE-002",
            "identity": second_item["identity"],
            "current_body_sha256": second_item["current_body_sha256"],
            "bodySections": second_body,
        },
    ]

    findings = pipeline.rewrite_quality_findings(brief, candidates)
    codes = {item["code"] for item in findings}

    assert "cross_article_sentence" in codes
    assert "opening_keyword" not in {item["code"] for item in findings if item["article_id"] == "REWRITE-001"}
    assert "concrete_verbs" not in codes
    assert "scenario_density" not in codes


def test_rewrite_machine_length_repair_reviews_only_after_green(tmp_path: Path) -> None:
    brief = make_rewrite_brief()
    pipeline.write_json(tmp_path / "brief.json", brief)
    source = brief["articles"][0]
    initial_body = make_rewrite_sections()
    initial_body[0]["paragraphs"][0] = (
        str(initial_body[0]["paragraphs"][0]) + "補" * 131
    )[:131]
    repaired_body = make_rewrite_sections(variant="修")
    assert any(
        finding["code"] == "paragraph_length"
        for finding in pipeline.rewrite_quality_findings(
            brief,
            [
                {
                    "article_id": source["article_id"],
                    "identity": source["identity"],
                    "current_body_sha256": source["current_body_sha256"],
                    "bodySections": initial_body,
                    "publicationPolicy": make_rewrite_publication_policy(source),
                }
            ],
        )
    )

    class RecordingClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def __init__(self) -> None:
            self.calls: list[str] = []
            self.writer_prompts: list[str] = []
            self.writer_schemas: list[dict[str, object]] = []

        def generate_json(
            self,
            role: str,
            prompt: str,
            schema: dict[str, object],
        ) -> dict[str, object]:
            self.calls.append(role)
            if role == "writer":
                self.writer_prompts.append(prompt)
                self.writer_schemas.append(
                    json.loads(json.dumps(schema, ensure_ascii=False))
                )
                body = initial_body if self.calls.count("writer") == 1 else repaired_body
                return {
                    "articles": [
                        {
                            "slot": "article-01",
                            "bodySections": body,
                            "publicationPolicy": make_rewrite_publication_policy(source),
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

    client = RecordingClient()
    candidate, review = pipeline.run_writer_reviewer(
        tmp_path,
        client,
        max_repairs=1,
    )

    assert client.calls == ["writer", "writer", "reviewer"]
    assert "paragraph_length" not in client.writer_prompts[0]
    assert "paragraph_length" in client.writer_prompts[1]
    repair_requests = [
        build_external_request(
            namespace="rewrite-length-repair",
            role="writer",
            model=client.writer_model,
            prompt=prompt,
            response_schema=schema,
        )
        for prompt, schema in zip(
            client.writer_prompts,
            client.writer_schemas,
            strict=True,
        )
    ]
    assert (
        repair_requests[0]["request_sha256"]
        != repair_requests[1]["request_sha256"]
    )
    assert pipeline.rewrite_quality_findings(brief, candidate["articles"]) == []
    assert review["articles"][0]["verdict"] == "APPROVE"
    evidence = json.loads((tmp_path / "run-evidence.json").read_text())
    assert evidence["content_repairs_used"] == 1
    assert not (tmp_path / "attempts/03").exists()


def test_rewrite_ignores_false_body_shape_review_without_spending_writer_repair(
    tmp_path: Path,
) -> None:
    brief = make_rewrite_brief("CHART-ZIWEI-11")
    brief["run_id"] = "legacy-auto-sweep-v1-fortune-0013-chart-ziwei-11"
    pipeline.write_json(tmp_path / "brief.json", brief)
    source = brief["articles"][0]
    body = make_rewrite_sections(
        str(source["identity"]["primaryKeyword"]),
        variant="紫微",
    )
    production_lengths = [
        127,
        125,
        125,
        118,
        120,
        116,
        119,
        117,
        112,
        122,
        115,
        111,
        116,
        110,
        109,
    ]
    paragraphs = [
        paragraph
        for section in body
        for paragraph in section["paragraphs"]
    ]
    for index, target_length in enumerate(production_lengths):
        paragraphs[index] = (str(paragraphs[index]) + "補" * target_length)[
            :target_length
        ]
    for index, section in enumerate(body):
        section["paragraphs"] = paragraphs[index * 3 : index * 3 + 3]
    candidate_article = {
        "article_id": source["article_id"],
        "identity": source["identity"],
        "current_body_sha256": source["current_body_sha256"],
        "bodySections": body,
        "publicationPolicy": make_rewrite_publication_policy(source),
    }
    assert sum(len(paragraph) for paragraph in paragraphs) == 1762
    assert [len(paragraph) for paragraph in paragraphs] == production_lengths
    assert pipeline.rewrite_quality_findings(brief, [candidate_article]) == []

    class FalseBodyShapeReviewer:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def __init__(self) -> None:
            self.writer_calls = 0
            self.reviewer_calls = 0

        def generate_json(
            self,
            role: str,
            _prompt: str,
            _schema: dict[str, object],
        ) -> dict[str, object]:
            if role == "writer":
                self.writer_calls += 1
                return {
                    "articles": [
                        {
                            "slot": "article-01",
                            "bodySections": body,
                            "publicationPolicy": make_rewrite_publication_policy(
                                source
                            ),
                        }
                    ]
                }
            self.reviewer_calls += 1
            review_item_schema = _schema["properties"]["articles"]["items"]  # type: ignore[index]
            assert set(review_item_schema["properties"]) == {
                "slot",
                "semantic_verdict",
                "semantic_findings",
                "objective_observations",
            }
            return {
                "articles": [
                    {
                        "slot": "article-01",
                        "semantic_verdict": "REJECT",
                        "semantic_findings": [
                            {
                                "code": "body_shape_violation",
                                "message": "錯誤聲稱正文約 1150 字",
                            },
                            {
                                "code": "paragraph_length_violation",
                                "message": "錯誤聲稱多數段落不足 90 到 130 字",
                            },
                        ],
                        "objective_observations": [],
                    }
                ]
            }

    client = FalseBodyShapeReviewer()
    _candidate, review = pipeline.run_writer_reviewer(
        tmp_path,
        client,
        max_repairs=1,
    )

    assert client.writer_calls == 1
    assert client.reviewer_calls == 1
    assert review["articles"][0]["verdict"] == "APPROVE"
    assert review["articles"][0]["findings"] == []
    external_review = json.loads(
        (tmp_path / "attempts/01/external-review.json").read_text()
    )
    assert len(external_review["articles"][0]["semantic_findings"]) == 2


def test_rewrite_review_schema_uses_canonical_objective_code_enum() -> None:
    item_schema = pipeline.rewrite_external_review_schema()["properties"][
        "articles"
    ]["items"]
    semantic_code_schema = item_schema["properties"]["semantic_findings"][
        "items"
    ]["properties"]["code"]
    objective_code_schema = item_schema["properties"]["objective_observations"][
        "items"
    ]["properties"]["code"]

    assert semantic_code_schema == {"type": "string"}
    assert objective_code_schema == {
        "type": "string",
        "enum": sorted(pipeline.REWRITE_MACHINE_OWNED_REVIEW_CODES),
    }
    assert "section_count_valid" not in objective_code_schema["enum"]
    assert "total_length_valid" not in objective_code_schema["enum"]


def test_hydrate_rewrite_review_removes_only_machine_owned_semantic_findings() -> None:
    brief = make_rewrite_brief("MIXED-REWRITE-REVIEW")
    source = brief["articles"][0]
    article = {
        "article_id": source["article_id"],
        "identity": source["identity"],
        "current_body_sha256": source["current_body_sha256"],
        "bodySections": make_rewrite_sections(variant="混合"),
        "publicationPolicy": make_rewrite_publication_policy(source),
    }
    candidate = {
        "schema_version": 1,
        "run_id": brief["run_id"],
        "mode": "rewrite_existing_body",
        "articles": [article],
    }

    review = pipeline.hydrate_rewrite_review(
        brief,
        candidate,
        {
            "articles": [
                {
                    "slot": "article-01",
                    "semantic_verdict": "REJECT",
                    "semantic_findings": [
                        {
                            "code": "body_shape_violation",
                            "message": "錯誤聲稱正文尺寸不合格",
                        },
                        {
                            "code": "search_intent_mismatch",
                            "message": "沒有回答搜尋者的核心問題",
                        },
                    ],
                    "objective_observations": [],
                }
            ]
        },
    )

    assert review["articles"][0]["verdict"] == "REJECT"
    assert review["articles"][0]["findings"] == [
        {
            "code": "search_intent_mismatch",
            "message": "沒有回答搜尋者的核心問題",
        }
    ]


def test_hydrate_rewrite_review_requires_exact_objective_code() -> None:
    brief = make_rewrite_brief("INVALID-OBJECTIVE-CODE")
    source = brief["articles"][0]
    article = {
        "article_id": source["article_id"],
        "identity": source["identity"],
        "current_body_sha256": source["current_body_sha256"],
        "bodySections": make_rewrite_sections(variant="精確"),
        "publicationPolicy": make_rewrite_publication_policy(source),
    }
    candidate = {
        "schema_version": 1,
        "run_id": brief["run_id"],
        "mode": "rewrite_existing_body",
        "articles": [article],
    }

    with pytest.raises(ValueError, match="objective observation is invalid"):
        pipeline.hydrate_rewrite_review(
            brief,
            candidate,
            {
                "articles": [
                    {
                        "slot": "article-01",
                        "semantic_verdict": "APPROVE",
                        "semantic_findings": [],
                        "objective_observations": [
                            {
                                "code": "BODY_SHAPE_VIOLATION",
                                "message": "非 canonical 大小寫",
                            }
                        ],
                    }
                ]
            },
        )


def test_rewrite_reviewer_prompts_require_exact_review_contract() -> None:
    brief = make_rewrite_brief("REWRITE-PROMPT-CONTRACT")
    source = brief["articles"][0]
    candidate = {
        "schema_version": 1,
        "run_id": brief["run_id"],
        "mode": "rewrite_existing_body",
        "articles": [
            {
                "article_id": source["article_id"],
                "identity": source["identity"],
                "current_body_sha256": source["current_body_sha256"],
                "bodySections": make_rewrite_sections(variant="契約"),
                "publicationPolicy": make_rewrite_publication_policy(source),
            }
        ],
    }

    prompts = [
        pipeline._reviewer_prompt(brief, candidate, []),
        pipeline._repair_reviewer_prompt(brief, candidate, []),
    ]
    expected_objective_contract = (
        "objective_observations.code 只允許以下精確值："
        + ", ".join(sorted(pipeline.REWRITE_MACHINE_OWNED_REVIEW_CODES))
        + "；若沒有客觀觀察，objective_observations 必須輸出 []。"
    )

    for prompt in prompts:
        assert "semantic_findings 只可放阻塞核准的問題" in prompt
        assert (
            "semantic_verdict=APPROVE 時 semantic_findings 必須精確為 []"
            in prompt
        )
        assert "semantic_findings 非空時 semantic_verdict 必須為 REJECT" in prompt
        assert (
            "不得把正面評語、通過項目、摘要或建議放入 semantic_findings"
            in prompt
        )
        assert expected_objective_contract in prompt


def test_rewrite_provider_approve_with_positive_findings_fails_closed(
    tmp_path: Path,
) -> None:
    brief = make_rewrite_brief("CHART-BAZI-05")
    brief["run_id"] = "legacy-auto-sweep-v1-fortune-0026-chart-bazi-05"
    pipeline.write_json(tmp_path / "brief.json", brief)
    source = brief["articles"][0]
    body = make_rewrite_sections(
        str(source["identity"]["primaryKeyword"]),
        variant="八字",
    )
    production_lengths = [
        127,
        125,
        125,
        118,
        120,
        116,
        119,
        117,
        112,
        122,
        115,
        111,
        116,
        110,
        109,
    ]
    paragraphs = [
        paragraph
        for section in body
        for paragraph in section["paragraphs"]
    ]
    for index, target_length in enumerate(production_lengths):
        paragraphs[index] = (str(paragraphs[index]) + "補" * target_length)[
            :target_length
        ]
    for index, section in enumerate(body):
        section["paragraphs"] = paragraphs[index * 3 : index * 3 + 3]
    candidate_article = {
        "article_id": source["article_id"],
        "identity": source["identity"],
        "current_body_sha256": source["current_body_sha256"],
        "bodySections": body,
        "publicationPolicy": make_rewrite_publication_policy(source),
    }
    assert sum(len(paragraph) for paragraph in paragraphs) == 1762
    assert pipeline.rewrite_quality_findings(brief, [candidate_article]) == []

    positive_findings = [
        {
            "code": "SEARCH_INTENT_ALIGNED",
            "message": "內容完整回應搜尋意圖。",
        },
        {
            "code": "SCENARIOS_ARE_CONCRETE",
            "message": "生活場景具體且可觀察。",
        },
        {
            "code": "BOUNDARIES_ARE_CLEAR",
            "message": "限制與安全邊界交代清楚。",
        },
        {
            "code": "LANGUAGE_IS_NATURAL",
            "message": "繁體中文自然，沒有模板感。",
        },
    ]
    objective_observations = [
        {"code": "BODY_LENGTH", "message": "正文長度符合規範。"},
        {"code": "SECTION_COUNT", "message": "section 數量符合規範。"},
        {"code": "PARAGRAPH_COUNT", "message": "paragraph 數量符合規範。"},
        {"code": "PARAGRAPH_LENGTH", "message": "各段長度符合規範。"},
    ]

    class PositiveFindingsReviewer:
        writer_model = "writer-test"
        reviewer_model = "gemini-3.1-flash-lite"

        def __init__(self) -> None:
            self.writer_calls = 0
            self.reviewer_calls = 0

        def generate_json(
            self,
            role: str,
            _prompt: str,
            _schema: dict[str, object],
        ) -> dict[str, object]:
            if role == "writer":
                self.writer_calls += 1
                return {
                    "articles": [
                        {
                            "slot": "article-01",
                            "bodySections": body,
                            "publicationPolicy": make_rewrite_publication_policy(
                                source
                            ),
                        }
                    ]
                }
            self.reviewer_calls += 1
            return {
                "articles": [
                    {
                        "slot": "article-01",
                        "semantic_verdict": "APPROVE",
                        "semantic_findings": positive_findings,
                        "objective_observations": objective_observations,
                    }
                ]
            }

    client = PositiveFindingsReviewer()
    _candidate, review = pipeline.run_writer_reviewer(
        tmp_path,
        client,
        max_repairs=1,
    )

    assert client.writer_calls == 1
    assert client.reviewer_calls == 1
    assert review["articles"][0]["verdict"] == "REJECT"
    assert review["articles"][0]["hard_failure"] is True
    assert review["articles"][0]["findings"] == [
        {
            "code": "invalid_reviewer_json:ValueError",
            "message": "invalid_reviewer_json:ValueError",
        }
    ]
    external_review = json.loads(
        (tmp_path / "attempts/01/external-review.json").read_text()
    )
    assert (
        external_review["articles"][0]["semantic_findings"]
        == positive_findings
    )


def test_rewrite_provider_valid_suffix_objective_codes_fail_closed(
    tmp_path: Path,
) -> None:
    article_id = "EXPANSION-50D-FORTUNE-0031"
    brief = make_rewrite_brief(article_id)
    brief["run_id"] = (
        "legacy-auto-sweep-v1-fortune-0031-expansion-50d-fortune-0031"
    )
    pipeline.write_json(tmp_path / "brief.json", brief)
    source = brief["articles"][0]
    body = make_rewrite_sections(
        str(source["identity"]["primaryKeyword"]),
        variant="擴充",
    )
    candidate_article = {
        "article_id": source["article_id"],
        "identity": source["identity"],
        "current_body_sha256": source["current_body_sha256"],
        "bodySections": body,
        "publicationPolicy": make_rewrite_publication_policy(source),
    }
    assert pipeline.rewrite_quality_findings(brief, [candidate_article]) == []

    objective_observations = [
        {"code": "SECTION_COUNT_VALID", "message": "section 數量符合規範。"},
        {
            "code": "PARAGRAPH_COUNT_VALID",
            "message": "paragraph 數量符合規範。",
        },
        {
            "code": "PARAGRAPH_LENGTH_VALID",
            "message": "各段長度符合規範。",
        },
        {"code": "TOTAL_LENGTH_VALID", "message": "正文總長符合規範。"},
    ]

    class ValidSuffixReviewer:
        writer_model = "writer-test"
        reviewer_model = "gemini-3.1-flash-lite"

        def __init__(self) -> None:
            self.writer_calls = 0
            self.reviewer_calls = 0

        def generate_json(
            self,
            role: str,
            _prompt: str,
            _schema: dict[str, object],
        ) -> dict[str, object]:
            if role == "writer":
                self.writer_calls += 1
                return {
                    "articles": [
                        {
                            "slot": "article-01",
                            "bodySections": body,
                            "publicationPolicy": make_rewrite_publication_policy(
                                source
                            ),
                        }
                    ]
                }
            self.reviewer_calls += 1
            return {
                "articles": [
                    {
                        "slot": "article-01",
                        "semantic_verdict": "APPROVE",
                        "semantic_findings": [],
                        "objective_observations": objective_observations,
                    }
                ]
            }

    client = ValidSuffixReviewer()
    _candidate, review = pipeline.run_writer_reviewer(
        tmp_path,
        client,
        max_repairs=1,
    )

    assert client.writer_calls == 1
    assert client.reviewer_calls == 1
    assert review["articles"][0]["verdict"] == "REJECT"
    assert review["articles"][0]["hard_failure"] is True
    assert review["articles"][0]["findings"] == [
        {
            "code": "invalid_reviewer_json:ValueError",
            "message": "invalid_reviewer_json:ValueError",
        }
    ]
    external_review = json.loads(
        (tmp_path / "attempts/01/external-review.json").read_text()
    )
    assert (
        external_review["articles"][0]["objective_observations"]
        == objective_observations
    )


def test_rewrite_cached_legacy_review_payload_fails_closed(
    tmp_path: Path,
) -> None:
    brief = make_rewrite_brief("CACHED-LEGACY-REVIEW")
    source = brief["articles"][0]
    candidate = {
        "schema_version": 1,
        "run_id": brief["run_id"],
        "mode": "rewrite_existing_body",
        "articles": [
            {
                "article_id": source["article_id"],
                "identity": source["identity"],
                "current_body_sha256": source["current_body_sha256"],
                "bodySections": make_rewrite_sections(variant="快取"),
                "publicationPolicy": make_rewrite_publication_policy(source),
            }
        ],
    }
    cached_path = tmp_path / "external-review.json"
    pipeline.write_json(
        cached_path,
        {
            "articles": [
                {
                    "slot": "article-01",
                    "verdict": "APPROVE",
                    "findings": [],
                }
            ]
        },
    )
    cached_payload = json.loads(cached_path.read_text())

    with pytest.raises(ValueError, match="rewrite review fields are strict"):
        pipeline.hydrate_rewrite_review(brief, candidate, cached_payload)


def test_rewrite_semantic_reject_survives_machine_owned_code_label(
    tmp_path: Path,
) -> None:
    brief = make_rewrite_brief("HOSTILE-SEMANTIC-MISLABEL")
    pipeline.write_json(tmp_path / "brief.json", brief)
    source = brief["articles"][0]
    body = make_rewrite_sections(variant="誤標")
    candidate_article = {
        "article_id": source["article_id"],
        "identity": source["identity"],
        "current_body_sha256": source["current_body_sha256"],
        "bodySections": body,
        "publicationPolicy": make_rewrite_publication_policy(source),
    }
    assert pipeline.rewrite_quality_findings(brief, [candidate_article]) == []

    class HostileMislabelReviewer:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def __init__(self) -> None:
            self.writer_calls = 0
            self.reviewer_calls = 0

        def generate_json(
            self,
            role: str,
            _prompt: str,
            _schema: dict[str, object],
        ) -> dict[str, object]:
            if role == "writer":
                self.writer_calls += 1
                return {
                    "articles": [
                        {
                            "slot": "article-01",
                            "bodySections": body,
                            "publicationPolicy": make_rewrite_publication_policy(
                                source
                            ),
                        }
                    ]
                }
            self.reviewer_calls += 1
            return {
                "articles": [
                    {
                        "slot": "article-01",
                        "semantic_verdict": "REJECT",
                        "semantic_findings": [
                            {
                                "code": "BODY_SHAPE_VIOLATION",
                                "message": "文章完全誤解搜尋意圖，且把文化反思寫成個人定論",
                            }
                        ],
                        "objective_observations": [],
                    }
                ]
            }

    client = HostileMislabelReviewer()
    _candidate, review = pipeline.run_writer_reviewer(
        tmp_path,
        client,
        max_repairs=0,
    )

    assert client.writer_calls == 1
    assert client.reviewer_calls == 1
    assert review["articles"][0]["verdict"] == "REJECT"
    assert review["articles"][0]["hard_failure"] is False
    assert review["articles"][0]["findings"] == [
        {
            "code": "BODY_SHAPE_VIOLATION",
            "message": "文章完全誤解搜尋意圖，且把文化反思寫成個人定論",
        }
    ]


def test_rewrite_malformed_machine_owned_finding_fails_closed(
    tmp_path: Path,
) -> None:
    brief = make_rewrite_brief("MALFORMED-REVIEW")
    pipeline.write_json(tmp_path / "brief.json", brief)
    source = brief["articles"][0]
    body = make_rewrite_sections()
    candidate_article = {
        "article_id": source["article_id"],
        "identity": source["identity"],
        "current_body_sha256": source["current_body_sha256"],
        "bodySections": body,
        "publicationPolicy": make_rewrite_publication_policy(source),
    }
    assert pipeline.rewrite_quality_findings(brief, [candidate_article]) == []

    class MalformedReviewer:
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
                            "bodySections": body,
                            "publicationPolicy": make_rewrite_publication_policy(
                                source
                            ),
                        }
                    ]
                }
            return {
                "articles": [
                    {
                        "slot": "article-01",
                        "semantic_verdict": "APPROVE",
                        "semantic_findings": [],
                        "objective_observations": [
                            {"code": "BODY_SHAPE_VIOLATION"}
                        ],
                    }
                ]
            }

    _candidate, review = pipeline.run_writer_reviewer(
        tmp_path,
        MalformedReviewer(),
        max_repairs=0,
    )

    assert review["articles"][0]["verdict"] == "REJECT"
    assert review["articles"][0]["hard_failure"] is True
    assert review["articles"][0]["findings"] == [
        {
            "code": "invalid_reviewer_json:ValueError",
            "message": "invalid_reviewer_json:ValueError",
        }
    ]


@pytest.mark.parametrize("max_repairs", [0, 1, 2])
def test_rewrite_semantic_rejection_keeps_writer_reviewer_calls_bounded(
    tmp_path: Path,
    max_repairs: int,
) -> None:
    run_dir = tmp_path / f"semantic-repair-{max_repairs}"
    run_dir.mkdir()
    brief = make_rewrite_brief(f"SEMANTIC-{max_repairs}")
    pipeline.write_json(run_dir / "brief.json", brief)
    source = brief["articles"][0]
    body = make_rewrite_sections(variant=f"語意{max_repairs}")
    candidate_article = {
        "article_id": source["article_id"],
        "identity": source["identity"],
        "current_body_sha256": source["current_body_sha256"],
        "bodySections": body,
        "publicationPolicy": make_rewrite_publication_policy(source),
    }
    assert pipeline.rewrite_quality_findings(brief, [candidate_article]) == []

    class SemanticReviewer:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def __init__(self) -> None:
            self.writer_calls = 0
            self.reviewer_calls = 0
            self.reviewer_prompts: list[str] = []

        def generate_json(
            self,
            role: str,
            prompt: str,
            _schema: dict[str, object],
        ) -> dict[str, object]:
            if role == "writer":
                self.writer_calls += 1
                return {
                    "articles": [
                        {
                            "slot": "article-01",
                            "bodySections": body,
                            "publicationPolicy": make_rewrite_publication_policy(
                                source
                            ),
                        }
                    ]
                }
            self.reviewer_calls += 1
            self.reviewer_prompts.append(prompt)
            return {
                "articles": [
                    {
                        "slot": "article-01",
                        "semantic_verdict": "REJECT",
                        "semantic_findings": [
                            {
                                "code": "search_intent_mismatch",
                                "message": "沒有回答搜尋者的核心問題",
                            }
                        ],
                        "objective_observations": [],
                    }
                ]
            }

    client = SemanticReviewer()
    _candidate, review = pipeline.run_writer_reviewer(
        run_dir,
        client,
        max_repairs=max_repairs,
    )
    evidence = json.loads((run_dir / "run-evidence.json").read_text())

    assert client.writer_calls == max_repairs + 1
    assert client.reviewer_calls == max_repairs + 1
    assert evidence["content_repairs_used"] == max_repairs
    assert review["articles"][0]["verdict"] == "REJECT"
    assert review["articles"][0]["findings"] == [
        {
            "code": "search_intent_mismatch",
            "message": "沒有回答搜尋者的核心問題",
        }
    ]
    assert all(
        "你仍必須獨立審查搜尋意圖、語意品質、場景、動詞、限制、安全邊界、錯別字與模板感"
        in prompt
        for prompt in client.reviewer_prompts
    )


def test_rewrite_deterministic_reject_never_calls_reviewer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    brief = make_rewrite_brief("DETERMINISTIC-REJECT")
    pipeline.write_json(tmp_path / "brief.json", brief)
    source = brief["articles"][0]
    body = make_rewrite_sections()
    finding = {
        "article_id": source["article_id"],
        "code": "paragraph_length",
        "message": "第 1 節第 1 段為 131 字；必須 90 到 130 字",
    }
    monkeypatch.setattr(
        pipeline,
        "rewrite_quality_findings",
        lambda *_args: [finding],
    )

    class DeterministicRejectClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def __init__(self) -> None:
            self.writer_calls = 0
            self.reviewer_calls = 0

        def generate_json(
            self,
            role: str,
            _prompt: str,
            _schema: dict[str, object],
        ) -> dict[str, object]:
            if role == "reviewer":
                self.reviewer_calls += 1
                raise AssertionError("deterministic rejection must skip Reviewer")
            self.writer_calls += 1
            return {
                "articles": [
                    {
                        "slot": "article-01",
                        "bodySections": body,
                        "publicationPolicy": make_rewrite_publication_policy(source),
                    }
                ]
            }

    client = DeterministicRejectClient()
    _candidate, review = pipeline.run_writer_reviewer(
        tmp_path,
        client,
        max_repairs=0,
    )

    assert client.writer_calls == 1
    assert client.reviewer_calls == 0
    assert review["articles"][0]["verdict"] == "REJECT"
    assert review["articles"][0]["findings"] == [
        {"code": finding["code"], "message": finding["message"]}
    ]


def test_rewrite_unknown_reviewer_finding_fails_closed(tmp_path: Path) -> None:
    brief = make_rewrite_brief("UNKNOWN-REVIEW")
    pipeline.write_json(tmp_path / "brief.json", brief)
    source = brief["articles"][0]
    body = make_rewrite_sections()

    class UnknownFindingReviewer:
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
                            "bodySections": body,
                            "publicationPolicy": make_rewrite_publication_policy(
                                source
                            ),
                        }
                    ]
                }
            return {
                "articles": [
                    {
                        "slot": "article-01",
                        "semantic_verdict": "REJECT",
                        "semantic_findings": [
                            {
                                "code": "UNKNOWN_REVIEW_AUTHORITY",
                                "message": "無法分類的 Reviewer finding",
                            }
                        ],
                        "objective_observations": [],
                    }
                ]
            }

    _candidate, review = pipeline.run_writer_reviewer(
        tmp_path,
        UnknownFindingReviewer(),
        max_repairs=0,
    )

    assert review["articles"][0]["verdict"] == "REJECT"
    assert review["articles"][0]["findings"] == [
        {
            "code": "UNKNOWN_REVIEW_AUTHORITY",
            "message": "無法分類的 Reviewer finding",
        }
    ]


def test_rewrite_deterministic_gate_locates_exact_duplicate_paragraph() -> None:
    brief = make_rewrite_brief()
    source = brief["articles"][0]
    body = make_rewrite_sections()
    body[0]["paragraphs"][1] = body[0]["paragraphs"][0]
    findings = pipeline.rewrite_quality_findings(
        brief,
        [
            {
                "article_id": source["article_id"],
                "identity": source["identity"],
                "current_body_sha256": source["current_body_sha256"],
                "bodySections": body,
                "publicationPolicy": make_rewrite_publication_policy(source),
            }
        ],
    )

    duplicates = [
        finding for finding in findings if finding["code"] == "duplicate_paragraph"
    ]

    assert duplicates == [
        {
            "article_id": source["article_id"],
            "code": "duplicate_paragraph",
            "message": "第 1 節第 2 段與第 1 節第 1 段逐字重複",
            "severity": "required",
            "policy_version": pipeline.publication_policy_version(),
        }
    ]


def test_rewrite_uniqueness_gate_checks_shared_h2_long_ngram_and_paragraph_opening() -> None:
    brief = make_repair_brief()
    articles = []
    for index, source in enumerate(brief["articles"]):
        body = make_rewrite_sections(str(source["identity"]["primaryKeyword"]), variant=chr(0x7532 + index))
        articles.append(
            {
                "article_id": source["article_id"],
                "identity": source["identity"],
                "current_body_sha256": source["current_body_sha256"],
                "bodySections": body,
            }
        )
    shared = "這段開頭完全相同而且後面保留一段足夠長的共同文字用來檢查跨篇片段，接著才放入各自內容。"
    articles[0]["bodySections"][0]["heading"] = "測試關鍵字1共同判讀步驟"
    articles[1]["bodySections"][0]["heading"] = "測試關鍵字2共同判讀步驟"
    articles[0]["bodySections"][0]["paragraphs"][0] = shared
    articles[1]["bodySections"][0]["paragraphs"][0] = shared

    findings = pipeline.rewrite_uniqueness_findings(brief, articles)
    codes = {finding["code"] for finding in findings}

    assert {"shared_h2", "long_ngram", "repeated_paragraph_opening"} <= codes


def test_rewrite_uniqueness_gate_checks_abstract_patterns_and_paragraph_skeletons() -> None:
    brief = make_repair_brief()
    articles = []
    for index, source in enumerate(brief["articles"]):
        body = make_rewrite_sections(str(source["identity"]["primaryKeyword"]), variant=chr(0x7532 + index))
        articles.append({"article_id": source["article_id"], "identity": source["identity"], "current_body_sha256": source["current_body_sha256"], "bodySections": body})
    articles[0]["bodySections"][0]["paragraphs"][0] = "當你在會議卡住時，這個主題可以幫你拆題。你可以列出問題並確認資料。這不代表答案已經確定。"
    articles[1]["bodySections"][0]["paragraphs"][0] = "當你在工作猶豫時，另一個主題能幫你整理。你可以寫下選項並核對數字。這不代表結果已經注定。"

    codes = {item["code"] for item in pipeline.rewrite_uniqueness_findings(brief, articles)}

    assert "shared_abstract_pattern" in codes
    assert "shared_paragraph_skeleton" in codes


def test_prepare_rewrite_repair_locks_source_finding_and_fixed_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, check=True, capture_output=True, text=True
    ).stdout.strip()
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    brief = make_repair_brief()
    brief["run_id"] = "previous-run"
    candidate_articles = []
    for index, source in enumerate(brief["articles"]):
        candidate_articles.append(
            {
                "article_id": source["article_id"],
                "identity": source["identity"],
                "current_body_sha256": source["current_body_sha256"],
                "bodySections": make_rewrite_sections(str(source["identity"]["primaryKeyword"]), chr(0x7532 + index)),
                "publicationPolicy": make_rewrite_publication_policy(source),
            }
        )
    candidate = {"schema_version": 1, "run_id": "previous-run", "mode": "rewrite_existing_body", "articles": candidate_articles}
    review = {
        "schema_version": 1,
        "run_id": "previous-run",
        "articles": [
            {
                "article_id": article["article_id"],
                "candidate_sha256": article_sha256(article),
                "verdict": "REJECT",
                "findings": [{"code": "TEMPLATE_USAGE", "message": "跨篇句型相似"}],
            }
            for article in candidate_articles
        ],
    }
    pipeline.write_json(source_dir / "brief.json", brief)
    pipeline.write_json(source_dir / "candidate.json", candidate)
    pipeline.write_json(source_dir / "review.json", review)
    monkeypatch.setattr(pipeline, "rewrite_quality_findings", lambda *_: [])

    path = pipeline.prepare_rewrite_repair(repo_root, source_dir, target_dir, source_commit)

    prepared = json.loads(path.read_text(encoding="utf-8"))
    repair_source = json.loads((target_dir / "repair-source.json").read_text(encoding="utf-8"))
    assert prepared["run_id"] == "gemini_rewrite_batch_001_repair_001"
    assert [item["article_id"] for item in prepared["articles"]] == list(pipeline.REWRITE_REPAIR_ARTICLE_IDS)
    assert repair_source["repair_generation"] == 1
    review["articles"][0]["findings"][0]["code"] = "OTHER"
    pipeline.write_json(source_dir / "review.json", review)
    with pytest.raises(ValueError, match="outside TEMPLATE_USAGE"):
        pipeline.prepare_rewrite_repair(repo_root, source_dir, tmp_path / "invalid", source_commit)


def test_rewrite_repair_uses_single_article_writers_and_one_aggregate_repair(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brief = make_repair_brief()
    pipeline.write_json(tmp_path / "brief.json", brief)
    pipeline.write_json(
        tmp_path / "repair-source.json",
        {
            "chain_id": "CONTENT-GEMINI-REWRITE-BATCH-001",
            "repair_generation": 1,
            "exact_findings": [
                {"article_id": article_id, "findings": [{"code": "TEMPLATE_USAGE", "message": "跨篇相似"}]}
                for article_id in pipeline.REWRITE_REPAIR_ARTICLE_IDS
            ],
        },
    )
    monkeypatch.setattr(pipeline, "rewrite_aggregate_findings", lambda *_: ([], []))

    class RecordingClient:
        writer_model = "test-writer"
        reviewer_model = "test-reviewer"

        def __init__(self) -> None:
            self.writer_prompts: list[str] = []
            self.reviewer_calls = 0

        def generate_json(self, role: str, prompt: str, schema: dict[str, object]) -> dict[str, object]:
            if role == "writer":
                self.writer_prompts.append(prompt)
                index = len(self.writer_prompts)
                source = brief["articles"][0 if index > 5 else index - 1]
                return {
                    "articles": [
                        {
                            "slot": "article-01",
                            "bodySections": make_rewrite_sections(
                                str(source["identity"]["primaryKeyword"]),
                                f"稿{index}",
                            ),
                            "publicationPolicy": make_rewrite_publication_policy(source),
                        }
                    ]
                }
            self.reviewer_calls += 1
            return {
                "articles": [
                    {
                        "slot": f"article-{index:02d}",
                        "semantic_verdict": (
                            "REJECT"
                            if self.reviewer_calls == 1 and index == 1
                            else "APPROVE"
                        ),
                        "semantic_findings": (
                            [{"code": "TEMPLATE_USAGE", "message": "仍相似"}]
                            if self.reviewer_calls == 1 and index == 1
                            else []
                        ),
                        "objective_observations": [],
                    }
                    for index in range(1, 6)
                ]
            }

    client = RecordingClient()
    candidate, review = pipeline.run_rewrite_repair(tmp_path, client)

    assert len(client.writer_prompts) == 6
    assert all(prompt.count('"currentBody"') == 1 for prompt in client.writer_prompts)
    assert all(
        "正文以 1500 到 1800 字為生成目標" in prompt
        and "每段以 95 到 110 字為生成目標" in prompt
        and "130 字是硬上限" in prompt
        and "不得在同一篇內逐字重複完整段落" in prompt
        for prompt in client.writer_prompts
    )
    assert client.reviewer_calls == 2
    assert [article["article_id"] for article in candidate["articles"]] == list(pipeline.REWRITE_REPAIR_ARTICLE_IDS)
    assert all(item["verdict"] == "APPROVE" for item in review["articles"])
    evidence = json.loads((tmp_path / "run-evidence.json").read_text(encoding="utf-8"))
    assert evidence["internal_repairs_used"] == 1
    assert evidence["writer_processes"] == 6
    assert evidence["reviewer_processes"] == 2


def test_rewrite_repair_machine_reject_skips_reviewer_until_green(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    brief = make_repair_brief()
    pipeline.write_json(tmp_path / "brief.json", brief)
    pipeline.write_json(
        tmp_path / "repair-source.json",
        {
            "chain_id": "CONTENT-GEMINI-REWRITE-BATCH-001",
            "repair_generation": 1,
            "exact_findings": [
                {
                    "article_id": article_id,
                    "findings": [
                        {"code": "TEMPLATE_USAGE", "message": "跨篇相似"}
                    ],
                }
                for article_id in pipeline.REWRITE_REPAIR_ARTICLE_IDS
            ],
        },
    )
    deterministic_calls = 0

    def aggregate_findings(
        _brief: dict[str, object],
        _articles: list[dict[str, object]],
    ) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        nonlocal deterministic_calls
        deterministic_calls += 1
        if deterministic_calls == 1:
            return (
                [
                    {
                        "article_id": pipeline.REWRITE_REPAIR_ARTICLE_IDS[0],
                        "code": "paragraph_length",
                        "message": "第 1 節第 1 段為 131 字；必須 90 到 130 字",
                    }
                ],
                [],
            )
        return [], []

    monkeypatch.setattr(pipeline, "rewrite_aggregate_findings", aggregate_findings)

    class RecordingClient:
        writer_model = "test-writer"
        reviewer_model = "test-reviewer"

        def __init__(self) -> None:
            self.writer_calls = 0
            self.reviewer_calls = 0

        def generate_json(
            self,
            role: str,
            _prompt: str,
            _schema: dict[str, object],
        ) -> dict[str, object]:
            if role == "writer":
                self.writer_calls += 1
                source = brief["articles"][
                    0 if self.writer_calls > 5 else self.writer_calls - 1
                ]
                return {
                    "articles": [
                        {
                            "slot": "article-01",
                            "bodySections": make_rewrite_sections(
                                str(source["identity"]["primaryKeyword"]),
                                f"稿{self.writer_calls}",
                            ),
                            "publicationPolicy": make_rewrite_publication_policy(
                                source
                            ),
                        }
                    ]
                }
            self.reviewer_calls += 1
            return {
                "articles": [
                    {
                        "slot": f"article-{index:02d}",
                        "semantic_verdict": "APPROVE",
                        "semantic_findings": [],
                        "objective_observations": [],
                    }
                    for index in range(1, 6)
                ]
            }

    client = RecordingClient()
    _candidate, review = pipeline.run_rewrite_repair(tmp_path, client)

    assert client.writer_calls == 6
    assert client.reviewer_calls == 1
    assert all(item["verdict"] == "APPROVE" for item in review["articles"])


def test_batch_002_isolated_runner_uses_five_single_article_writers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brief = make_batch_002_brief()
    pipeline.write_json(tmp_path / "brief.json", brief)
    pipeline.write_json(
        tmp_path / "batch-contract.json",
        {
            "chain_id": "CONTENT-GEMINI-REWRITE-BATCH-002",
            "article_order": [item[1] for item in pipeline.REWRITE_BATCH_002_ARTICLES],
            "exact_findings": [
                {"article_id": item[1], "findings": [{"code": "TEMPLATE_STRUCTURE", "message": "audit finding"}]}
                for item in pipeline.REWRITE_BATCH_002_ARTICLES
            ],
            "variation_contracts": pipeline.REWRITE_BATCH_002_STYLE_CONTRACTS,
            "max_internal_repairs": 1,
        },
    )
    monkeypatch.setattr(pipeline, "rewrite_aggregate_findings", lambda *_: ([], []))

    class RecordingClient:
        writer_model = "test-writer"
        reviewer_model = "test-reviewer"

        def __init__(self) -> None:
            self.writer_prompts: list[str] = []
            self.reviewer_calls = 0

        def generate_json(self, role: str, prompt: str, schema: dict[str, object]) -> dict[str, object]:
            if role == "writer":
                self.writer_prompts.append(prompt)
                keyword = pipeline.REWRITE_BATCH_002_ARTICLES[len(self.writer_prompts) - 1][6]
                source = brief["articles"][len(self.writer_prompts) - 1]
                return {
                    "articles": [
                        {
                            "slot": "article-01",
                            "bodySections": make_rewrite_sections(keyword, f"稿{len(self.writer_prompts)}"),
                            "publicationPolicy": make_rewrite_publication_policy(source),
                        }
                    ]
                }
            self.reviewer_calls += 1
            return {
                "articles": [
                    {
                        "slot": f"article-{index:02d}",
                        "semantic_verdict": (
                            "REJECT" if index == 1 else "APPROVE"
                        ),
                        "semantic_findings": (
                            [
                                {
                                    "code": "body_shape_violation",
                                    "message": "錯誤聲稱正文尺寸不合格",
                                }
                            ]
                            if index == 1
                            else []
                        ),
                        "objective_observations": [],
                    }
                    for index in range(1, 6)
                ]
            }

    client = RecordingClient()
    candidate, review = pipeline.run_rewrite_repair(tmp_path, client)

    assert len(client.writer_prompts) == 5
    assert client.reviewer_calls == 1
    assert all(prompt.count('"currentBody"') == 1 for prompt in client.writer_prompts)
    assert [article["article_id"] for article in candidate["articles"]] == [item[1] for item in pipeline.REWRITE_BATCH_002_ARTICLES]
    assert all(item["verdict"] == "APPROVE" for item in review["articles"])
    evidence = json.loads((tmp_path / "run-evidence.json").read_text())
    assert evidence["internal_repairs_used"] == 0


def test_rewrite_repair_closure_changes_only_two_authorized_paragraphs_and_never_calls_writer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    brief = make_repair_brief()
    candidate_articles = []
    for index, source in enumerate(brief["articles"]):
        candidate_articles.append(
            {
                "article_id": source["article_id"],
                "identity": source["identity"],
                "current_body_sha256": source["current_body_sha256"],
                "bodySections": make_rewrite_sections(str(source["identity"]["primaryKeyword"]), f"稿{index}"),
                "publicationPolicy": make_rewrite_publication_policy(source),
            }
        )
    candidate_articles[0]["bodySections"][4]["paragraphs"][1] = pipeline.REWRITE_CLOSURE_EDITS[("MBTI-BASE-01", 5, 2)][0]
    candidate_articles[1]["bodySections"][3]["paragraphs"][0] = pipeline.REWRITE_CLOSURE_EDITS[("THEME-LIFE-03", 4, 1)][0]
    candidate = {
        "schema_version": 1,
        "run_id": brief["run_id"],
        "mode": "rewrite_existing_body",
        "articles": candidate_articles,
    }
    prior_review = {
        "schema_version": 1,
        "run_id": brief["run_id"],
        "articles": [
            {
                "article_id": article["article_id"],
                "candidate_sha256": article_sha256(article),
                "verdict": "REJECT" if index < 2 else "APPROVE",
                "findings": (
                    [{"code": "paragraph_length", "message": "89 字"}]
                    if index == 0
                    else [{"code": "banned_phrase", "message": "保證"}]
                    if index == 1
                    else []
                ),
            }
            for index, article in enumerate(candidate_articles)
        ],
    }
    pipeline.write_json(tmp_path / "brief.json", brief)
    pipeline.write_json(tmp_path / "candidate.json", candidate)
    pipeline.write_json(tmp_path / "review.json", prior_review)
    pipeline.write_json(tmp_path / "run-evidence.json", {"reviewer_processes": 2})
    monkeypatch.setattr(pipeline, "rewrite_aggregate_findings", lambda *_: ([], []))

    class ReviewerOnly:
        reviewer_model = "test-reviewer"

        def generate_json(self, role: str, prompt: str, schema: dict[str, object]) -> dict[str, object]:
            assert role == "reviewer"
            assert prompt.count('"currentBody"') == 5
            return {
                "articles": [
                    {
                        "slot": f"article-{index:02d}",
                        "semantic_verdict": "APPROVE",
                        "semantic_findings": [],
                        "objective_observations": [],
                    }
                    for index in range(1, 6)
                ]
            }

    before_hashes = [article_sha256(article) for article in candidate_articles]
    closed, review = pipeline.run_rewrite_repair_closure(tmp_path, ReviewerOnly())

    after_hashes = [article_sha256(article) for article in closed["articles"]]
    assert before_hashes[2:] == after_hashes[2:]
    assert before_hashes[:2] != after_hashes[:2]
    assert len(closed["articles"][0]["bodySections"][4]["paragraphs"][1]) == 91
    assert "保證" not in closed["articles"][1]["bodySections"][3]["paragraphs"][0]
    assert all(item["verdict"] == "APPROVE" for item in review["articles"])
    closure = json.loads((tmp_path / "closure-01" / "closure-evidence.json").read_text(encoding="utf-8"))
    assert closure["writer_processes"] == 0
    assert closure["unchanged_paragraphs"] == 73
    with pytest.raises(RuntimeError, match="already been used"):
        pipeline.run_rewrite_repair_closure(tmp_path, ReviewerOnly())


def test_rewrite_apply_is_disabled_even_with_approval() -> None:
    brief = make_rewrite_brief()
    article = pipeline.hydrate_candidate(
        brief,
        {
            "articles": [
                {
                    "slot": "article-01",
                    "bodySections": make_rewrite_sections(),
                    "publicationPolicy": make_rewrite_publication_policy(brief["articles"][0]),
                }
            ]
        },
    )["articles"][0]
    review = {
        "schema_version": 1,
        "run_id": brief["run_id"],
        "articles": [{"article_id": article["article_id"], "candidate_sha256": article_sha256(article), "verdict": "APPROVE", "findings": []}],
    }
    approval = build_approval(str(brief["run_id"]), [article], review, {str(article["article_id"]): "APPROVE"}, "user")

    with pytest.raises(ValueError, match="apply is disabled"):
        apply_approved_candidates(Path.cwd(), str(brief["run_id"]), [article], review, approval)


def test_external_content_is_hydrated_and_hashed_only_after_return() -> None:
    complete = make_article("PRIVATE-ID")
    target_fields = {
        field: complete[field]
        for field in ["id", "section", "product", "slug", "serial", "urlSlug", "primaryKeyword", "published", "updated"]
    }
    brief = {
        "schema_version": 1,
        "run_id": "private-run",
        "mode": "create",
        "articles": [
            {
                "matrix": {"id": "PRIVATE-ID", "primaryKeyword": complete["primaryKeyword"]},
                "target": target_fields,
                "policy": pipeline.compact_publication_policy(),
            }
        ],
    }
    external = {"articles": [make_external_create_article(complete)]}

    candidate = pipeline.hydrate_candidate(brief, external)
    reviewer_prompt = pipeline._reviewer_prompt(brief, candidate, [])
    review = pipeline.hydrate_review(
        brief,
        candidate,
        {"articles": [{"slot": "article-01", "verdict": "APPROVE", "findings": []}]},
    )

    assert candidate["articles"][0] == complete
    assert "PRIVATE-ID" not in reviewer_prompt
    assert "private-run" not in reviewer_prompt
    assert review["articles"][0]["article_id"] == "PRIVATE-ID"
    assert review["articles"][0]["candidate_sha256"] == article_sha256(complete)


def test_publication_quality_gate_uses_full_standard_and_humanizer_rules() -> None:
    article = make_article("MBTI-INTP-AC")
    article["title"] = "測試關鍵字"
    article["bodySections"][0]["paragraphs"][0] += "小明可以游刃有餘地找到最佳平衡點。"

    findings = pipeline.quality_findings([article])
    codes = {finding["code"] for finding in findings}

    assert {"body_length", "section_count", "paragraph_length", "title_length", "required_tags"} <= codes
    assert "missing_pantheon_context" in codes
    assert "generic_ai_phrase" in codes
    assert pipeline._contains_banned_phrase("結果不一定相同，也不能保證成功", "一定") is False
    assert pipeline._contains_banned_phrase("結果不一定相同，也不能保證成功", "保證") is False
    assert pipeline._contains_banned_phrase("這一定成功", "一定") is True
    external_article = pipeline.external_candidate_schema("create")["properties"]["articles"]["items"]
    assert external_article["properties"]["description"]["minLength"] == 70
    assert external_article["properties"]["description"]["maxLength"] == 95
    body = external_article["properties"]["bodySections"]
    assert body["minItems"] == 5
    assert "maxItems" not in body
    paragraphs = body["items"]["properties"]["paragraphs"]
    assert (paragraphs["minItems"], paragraphs["maxItems"]) == (2, 4)


def test_reviewer_prompt_distinguishes_hard_boundaries_from_preferences() -> None:
    article = make_article("ASC-LEO")
    article["title"] = "上升獅子是什麼？外在氣質、表達方式與被看見需求怎麼看"
    brief = {
        "schema_version": 1,
        "run_id": "private-run",
        "mode": "create",
        "articles": [
            {
                "matrix": {"id": "ASC-LEO", "primaryKeyword": article["primaryKeyword"]},
                "target": {
                    field: article[field]
                    for field in ["id", "section", "product", "slug", "serial", "urlSlug", "primaryKeyword", "published", "updated"]
                },
                "policy": pipeline.compact_publication_policy(),
            }
        ],
    }
    candidate = {"schema_version": 1, "run_id": "private-run", "mode": "create", "articles": [article]}

    prompt = pipeline._reviewer_prompt(brief, candidate, [])

    assert "20 到 45 字才是標題硬性安全邊界" in prompt
    assert "28 到 36 字只是偏好" in prompt
    assert "不得只因未落在偏好區間而退件" in prompt
    assert "1300 到 2000 字才是正文硬性邊界" in prompt
    assert "1500 到 1800 字只是生成目標" in prompt
    assert "不得只因正文未落在生成目標區間而退件" in prompt
    assert "英文殘字與錯別字" in prompt


def test_run_writer_reviewer_ignores_false_machine_check_from_external_reviewer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    article = make_article("FALSE-MACHINE-REVIEW")
    brief = {
        "schema_version": 1,
        "run_id": "false-machine-review",
        "mode": "create",
        "articles": [
            {
                "matrix": {
                    "id": article["id"],
                    "primaryKeyword": article["primaryKeyword"],
                },
                "target": {
                    field: article[field]
                    for field in ["id", "section", "product", "slug", "serial", "urlSlug", "primaryKeyword", "published", "updated"]
                },
                "policy": pipeline.compact_publication_policy(),
            }
        ],
    }
    run_dir = tmp_path / "false-machine-review"
    run_dir.mkdir()
    pipeline.write_json(run_dir / "brief.json", brief)
    monkeypatch.setattr(pipeline, "quality_findings", lambda _articles: [])

    class FalseMachineReviewer:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def generate_json(self, role: str, _prompt: str, _schema: dict[str, object]) -> dict[str, object]:
            if role == "writer":
                return {"articles": [make_external_create_article(article)]}
            return {
                "articles": [
                    {
                        "slot": "article-01",
                        "verdict": "REJECT",
                        "findings": [
                            {"code": "body_length_insufficient", "message": "錯誤聲稱正文不足 1300 字"},
                            {"code": "paragraph_length_violation", "message": "錯誤聲稱段落不足 80 字"},
                            {
                                "code": "banned_phrase_usage",
                                "message": "錯誤把 policy 未禁止的文字判成禁詞",
                            },
                        ],
                    }
                ]
            }

    _candidate, review = pipeline.run_writer_reviewer(
        run_dir,
        FalseMachineReviewer(),
        max_repairs=0,
    )

    assert review["articles"][0]["verdict"] == "APPROVE"
    assert review["articles"][0]["findings"] == []

    trusted_finding = {
        "article_id": article["id"],
        "code": "body_length",
        "message": "本機 deterministic gate 確認正文不足",
    }
    monkeypatch.setattr(
        pipeline,
        "quality_findings",
        lambda _articles: [trusted_finding],
    )
    trusted_run_dir = tmp_path / "trusted-machine-review"
    trusted_run_dir.mkdir()
    pipeline.write_json(trusted_run_dir / "brief.json", brief)

    _candidate, trusted_review = pipeline.run_writer_reviewer(
        trusted_run_dir,
        FalseMachineReviewer(),
        max_repairs=0,
    )

    assert trusted_review["articles"][0]["verdict"] == "REJECT"
    assert trusted_review["articles"][0]["findings"] == [
        {"code": trusted_finding["code"], "message": trusted_finding["message"]}
    ]


def test_machine_gate_reconciliation_preserves_semantic_reviewer_rejection() -> None:
    review = {
        "schema_version": 1,
        "run_id": "semantic-review",
        "articles": [
            {
                "article_id": "SEMANTIC-REVIEW",
                "candidate_sha256": "a" * 64,
                "verdict": "REJECT",
                "findings": [
                    {"code": "body_length_insufficient", "message": "錯誤的機械字數判定"},
                    {"code": "search_intent_mismatch", "message": "沒有回答搜尋者的核心問題"},
                ],
            }
        ],
    }

    reconciled = pipeline.reconcile_external_review_with_machine_gate(review)

    assert reconciled["articles"][0]["verdict"] == "REJECT"
    assert reconciled["articles"][0]["findings"] == [
        {"code": "search_intent_mismatch", "message": "沒有回答搜尋者的核心問題"}
    ]


def test_description_requires_its_own_boundary_statement() -> None:
    article = make_article("ASC-CANCER")
    article["description"] = "本文整理上升巨蟹的第一印象、安全感與關係互動，適合想理解社交防衛與慢熱節奏的讀者，並提供日常可觀察的行動線索與溝通方向。"

    findings = pipeline.quality_findings([article])

    assert any(finding["code"] == "description_boundary" for finding in findings)


def test_review_existing_reuses_candidate_without_writer_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    article = make_article("EXISTING-001")
    brief = {
        "schema_version": 1,
        "run_id": "existing-run",
        "mode": "create",
        "articles": [
            {
                "matrix": {"id": article["id"], "primaryKeyword": article["primaryKeyword"]},
                "target": {
                    field: article[field]
                    for field in ["id", "section", "product", "slug", "serial", "urlSlug", "primaryKeyword", "published", "updated"]
                },
                "policy": pipeline.compact_publication_policy(),
            }
        ],
    }
    candidate = {"schema_version": 1, "run_id": "existing-run", "mode": "create", "articles": [article]}
    pipeline.write_json(tmp_path / "brief.json", brief)
    pipeline.write_json(tmp_path / "candidate.json", candidate)
    monkeypatch.setattr(pipeline, "quality_findings", lambda _: [])

    class ReviewerOnly:
        def generate_json(self, role: str, prompt: str, schema: dict[str, object]) -> dict[str, object]:
            assert role == "reviewer"
            return {"articles": [{"slot": "article-01", "verdict": "APPROVE", "findings": []}]}

    review = pipeline.review_existing_candidate(tmp_path, ReviewerOnly())

    assert review["articles"][0]["verdict"] == "APPROVE"
    assert json.loads((tmp_path / "candidate.json").read_text()) == candidate


def test_review_existing_rewrite_reconciles_misplaced_machine_finding(
    tmp_path: Path,
) -> None:
    brief = make_rewrite_brief("EXISTING-REWRITE-001")
    source = brief["articles"][0]
    article = {
        "article_id": source["article_id"],
        "identity": source["identity"],
        "current_body_sha256": source["current_body_sha256"],
        "bodySections": make_rewrite_sections(variant="既有"),
        "publicationPolicy": make_rewrite_publication_policy(source),
    }
    candidate = {
        "schema_version": 1,
        "run_id": brief["run_id"],
        "mode": "rewrite_existing_body",
        "articles": [article],
    }
    assert pipeline.rewrite_quality_findings(brief, [article]) == []
    pipeline.write_json(tmp_path / "brief.json", brief)
    pipeline.write_json(tmp_path / "candidate.json", candidate)

    class ReviewerOnly:
        reviewer_model = "reviewer-test"

        def generate_json(
            self,
            role: str,
            _prompt: str,
            _schema: dict[str, object],
        ) -> dict[str, object]:
            assert role == "reviewer"
            return {
                "articles": [
                    {
                        "slot": "article-01",
                        "semantic_verdict": "REJECT",
                        "semantic_findings": [
                            {
                                "code": "body_shape_violation",
                                "message": "錯誤聲稱既有正文尺寸不合格",
                            }
                        ],
                        "objective_observations": [],
                    }
                ]
            }

    review = pipeline.review_existing_candidate(tmp_path, ReviewerOnly())

    assert review["articles"][0]["verdict"] == "APPROVE"
    assert review["articles"][0]["findings"] == []
    assert json.loads((tmp_path / "candidate.json").read_text()) == candidate


def test_review_existing_rewrite_deterministic_reject_skips_reviewer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    brief = make_rewrite_brief("EXISTING-DETERMINISTIC-REJECT")
    source = brief["articles"][0]
    article = {
        "article_id": source["article_id"],
        "identity": source["identity"],
        "current_body_sha256": source["current_body_sha256"],
        "bodySections": make_rewrite_sections(variant="確定"),
        "publicationPolicy": make_rewrite_publication_policy(source),
    }
    candidate = {
        "schema_version": 1,
        "run_id": brief["run_id"],
        "mode": "rewrite_existing_body",
        "articles": [article],
    }
    finding = {
        "article_id": source["article_id"],
        "code": "paragraph_length",
        "message": "本機確認第 1 節第 1 段超過 130 字",
    }
    monkeypatch.setattr(
        pipeline,
        "rewrite_quality_findings",
        lambda *_args: [finding],
    )
    pipeline.write_json(tmp_path / "brief.json", brief)
    pipeline.write_json(tmp_path / "candidate.json", candidate)

    class ReviewerMustNotRun:
        def generate_json(
            self,
            _role: str,
            _prompt: str,
            _schema: dict[str, object],
        ) -> dict[str, object]:
            raise AssertionError("deterministic rejection must skip Reviewer")

    review = pipeline.review_existing_candidate(tmp_path, ReviewerMustNotRun())

    assert review["articles"][0]["verdict"] == "REJECT"
    assert review["articles"][0]["findings"] == [
        {"code": finding["code"], "message": finding["message"]}
    ]
    assert not (tmp_path / "review-existing-operation.json").exists()


def test_partial_approval_and_human_override_are_bound_to_article_hashes() -> None:
    first = make_article("FIRST")
    second = make_article("SECOND")
    review = {
        "schema_version": 1,
        "run_id": "run",
        "articles": [
            {"article_id": "FIRST", "candidate_sha256": article_sha256(first), "verdict": "APPROVE", "findings": []},
            {"article_id": "SECOND", "candidate_sha256": article_sha256(second), "verdict": "REJECT", "findings": [{"code": "voice", "message": "模板感"}]},
        ],
    }
    approval = build_approval(
        "run",
        [first, second],
        review,
        decisions={"FIRST": "APPROVE", "SECOND": "OVERRIDE_APPROVE"},
        approved_by="user",
        override_reasons={"SECOND": "人工確認內容可接受"},
    )
    assert {item["decision"] for item in approval["articles"]} == {"APPROVE", "OVERRIDE_APPROVE"}
    validate_apply_gate([first, second], review, approval)


def test_hard_gate_cannot_be_overridden() -> None:
    article = make_article()
    review = invalid_review_payload("run", [article], "invalid_reviewer_json", hard_failure=True)
    approval = {
        "schema_version": 1,
        "run_id": "run",
        "approved_by": "user",
        "approved_at": "2026-07-17T00:00:00+08:00",
        "articles": [
            {
                "article_id": article["id"],
                "candidate_sha256": article_sha256(article),
                "decision": "OVERRIDE_APPROVE",
                "override_reason": "still no",
            }
        ],
    }
    with pytest.raises(ValueError, match="hard failure"):
        validate_apply_gate([article], review, approval)


def test_create_apply_gate_still_requires_publication_policy() -> None:
    article = make_article("CREATE-POLICY")
    article.pop("publicationPolicy")
    review = {
        "schema_version": 1,
        "run_id": "run",
        "articles": [
            {
                "article_id": article["id"],
                "candidate_sha256": article_sha256(article),
                "verdict": "APPROVE",
                "findings": [],
            }
        ],
    }
    approval = build_approval(
        "run",
        [article],
        review,
        decisions={article["id"]: "APPROVE"},
        approved_by="user",
    )

    with pytest.raises(ValueError, match="missing_policy_contract"):
        validate_apply_gate(
            [article],
            review,
            approval,
            candidate_mode="create",
        )


def test_matrix_backlog_uses_semantic_aliases_and_avoids_duplicates(monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    integrated_inventory = pipeline._registry_inventory(repo_root)
    baseline_inventory = [
        item
        for item in integrated_inventory
        if str(item.get("id")) not in AGY_MATRIX_IDS | DAILY_QUEUE_IDS
    ]
    monkeypatch.setattr(pipeline, "_registry_inventory", lambda _: baseline_inventory)
    backlog = build_matrix_backlog(repo_root)
    ids = {item["id"] for item in backlog}

    assert "CHART-PALACE-CAREER" not in ids  # 既有文章使用「事業宮」名稱。
    assert "CHART-CYCLE-YEAR" not in ids  # 既有八字流年文章已覆蓋泛用主關鍵字。
    assert {"MBTI-INTP-AH", "MBTI-INTP-AC", "MBTI-INTP-OH", "MBTI-INTP-OC"} <= ids
    assert {"ASC-ARIES", "ASC-TAURUS", "ASC-GEMINI"} <= ids
    assert "CHART-CYCLE-DECADE" in ids
    assert AGY_MATRIX_IDS | DAILY_QUEUE_IDS <= ids
    assert len(ids & V2_MATRIX_IDS) >= 1000
    assert len(ids) == len(backlog)


def test_registry_inventory_uses_bounded_process_without_pipes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    class FakeProcess:
        pid = 4321

        def __init__(self, command: list[str], **kwargs: object) -> None:
            observed["command"] = command
            observed.update(kwargs)
            kwargs["stdout"].write('[{"id":"ARTICLE-1"}]')  # type: ignore[union-attr]

        def wait(self, timeout: float | None = None) -> int:
            observed["timeout"] = timeout
            return 0

    monkeypatch.setattr(pipeline.subprocess, "Popen", FakeProcess)

    assert pipeline._registry_inventory(tmp_path) == [{"id": "ARTICLE-1"}]
    assert observed["timeout"] == pipeline.REGISTRY_NODE_TIMEOUT_SECONDS == 300
    assert observed["start_new_session"] is True
    assert observed["stdout"] is not pipeline.subprocess.PIPE
    assert observed["stderr"] is not pipeline.subprocess.PIPE


def test_registry_node_timeout_kills_process_group(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    killed: list[tuple[int, int]] = []

    class FakeProcess:
        pid = 4321

        def __init__(self, _command: list[str], **_kwargs: object) -> None:
            self.wait_count = 0

        def wait(self, timeout: float | None = None) -> int:
            self.wait_count += 1
            if self.wait_count == 1:
                raise subprocess.TimeoutExpired("node", timeout)
            return -9

    monkeypatch.setattr(pipeline.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(pipeline.os, "killpg", lambda pid, sig: killed.append((pid, sig)))

    with pytest.raises(subprocess.TimeoutExpired):
        pipeline._run_registry_node_script(tmp_path, "console.log('never')")

    assert killed == [(4321, pipeline.signal.SIGKILL)]


def test_matrix_prepare_allocates_final_unique_identity_before_writer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    integrated_inventory = pipeline._registry_inventory(repo_root)
    baseline_inventory = [
        item
        for item in integrated_inventory
        if str(item.get("id")) not in AGY_MATRIX_IDS | DAILY_QUEUE_IDS
    ]
    monkeypatch.setattr(pipeline, "_registry_inventory", lambda _: baseline_inventory)
    sample = build_matrix_backlog(repo_root)[:30]
    monkeypatch.setattr(pipeline, "build_matrix_backlog", lambda _: sample)
    paths = prepare_matrix_runs(repo_root, "identity-test", output_root=tmp_path)
    briefs = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    items = [item for brief in briefs for item in brief["articles"]]
    serials = [item["target"]["serial"] for item in items]

    assert len(items) == 30
    assert len(serials) == len(set(serials))
    assert all(item["target"]["published"] == date.today().isoformat() for item in items)
    assert all(item["target"]["primaryKeyword"] == item["matrix"]["primaryKeyword"] for item in items)
    assert all(len(json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")) <= 8192 for item in items)
    assert all(path.stat().st_size <= 8192 for path in paths)

    remaining_paths = prepare_matrix_runs(
        repo_root,
        "identity-remaining",
        output_root=tmp_path,
        exclude_ids={"MBTI-INTP-AH"},
    )
    remaining = [item for path in remaining_paths for item in json.loads(path.read_text(encoding="utf-8"))["articles"]]
    original_targets = {item["matrix"]["id"]: item["target"] for item in items}
    assert len(remaining) == 29
    assert all(item["target"] == original_targets[item["matrix"]["id"]] for item in remaining)


def test_matrix_prepare_can_isolate_every_article_in_its_own_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.setattr(pipeline, "_registry_inventory", lambda _: [])

    paths = prepare_matrix_runs(
        repo_root,
        "isolated-writer",
        output_root=tmp_path,
        limit=5,
        max_articles_per_run=1,
    )

    assert len(paths) == 5
    assert all(len(json.loads(path.read_text(encoding="utf-8"))["articles"]) == 1 for path in paths)


def test_matrix_prepare_reserves_exact_run_identity_before_writing_brief(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    exact_run_id = "auto-new-v1-20260812-001-02"
    monkeypatch.setattr(pipeline, "_registry_inventory", lambda _: [])

    paths = prepare_matrix_runs(
        repo_root,
        exact_run_id,
        output_root=tmp_path,
        limit=1,
        max_articles_per_run=1,
        exact_run_id=exact_run_id,
    )

    assert paths == [tmp_path / exact_run_id / "brief.json"]
    assert json.loads(paths[0].read_text(encoding="utf-8"))["run_id"] == exact_run_id
    with pytest.raises(ValueError, match="exact run identity is already in use"):
        prepare_matrix_runs(
            repo_root,
            exact_run_id,
            output_root=tmp_path,
            limit=1,
            max_articles_per_run=1,
            exact_run_id=exact_run_id,
        )


def test_matrix_prepare_rejects_unclosed_exact_identity_before_writing_brief(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    exact_run_id = "auto-new-v1-20260812-001-02"
    monkeypatch.setattr(pipeline, "_registry_inventory", lambda _: [])

    with pytest.raises(ValueError, match="exact run identity must resolve to exactly one run"):
        prepare_matrix_runs(
            repo_root,
            exact_run_id,
            output_root=tmp_path,
            limit=2,
            max_articles_per_run=1,
            exact_run_id=exact_run_id,
        )

    assert not (tmp_path / exact_run_id).exists()


def test_prepare_matrix_cli_accepts_exact_run_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["agy_seo_copy_pipeline.py", "prepare-matrix", "--exact-run-id", "auto-new-v1-20260812-001-02"],
    )

    args = pipeline.parse_args()

    assert args.run_prefix is None
    assert args.exact_run_id == "auto-new-v1-20260812-001-02"


def test_prepare_rewrite_batch_reads_exact_audit_order_and_current_bodies(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, check=True, capture_output=True, text=True
    ).stdout.strip()
    queue = repo_root / "artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_audit_001/gemini_queue.md"

    brief_path = prepare_rewrite_batch(repo_root, queue, 1, tmp_path, source_commit)
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    public = json.loads((tmp_path / "public-brief.json").read_text(encoding="utf-8"))

    assert [item["article_id"] for item in brief["articles"]] == [
        "MBTI-BASE-01",
        "THEME-LIFE-03",
        "THEME-INTERPERSONAL-03",
        "THEME-LIFE-04",
        "THEME-WEALTH-04",
    ]
    assert all(item["current_body"] for item in brief["articles"])
    assert all(item["current_body_sha256"] == body_sha256(item["current_body"]) for item in brief["articles"])
    encoded_public = json.dumps(public, ensure_ascii=False)
    assert "app/" not in encoded_public
    assert source_commit not in encoded_public

    with pytest.raises(ValueError, match="source commit mismatch"):
        prepare_rewrite_batch(repo_root, queue, 1, tmp_path / "wrong", "f" * 40)


def test_prepare_rewrite_batch_002_locks_audit_identity_order_and_variation_contracts(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, check=True, capture_output=True, text=True
    ).stdout.strip()
    queue = repo_root / "artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_audit_001/gemini_queue.md"

    brief_path = prepare_rewrite_batch(repo_root, queue, 2, tmp_path, source_commit)
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    contract = json.loads((tmp_path / "batch-contract.json").read_text(encoding="utf-8"))

    assert [item["article_id"] for item in brief["articles"]] == [item[1] for item in pipeline.REWRITE_BATCH_002_ARTICLES]
    assert contract["article_order"] == [item[1] for item in pipeline.REWRITE_BATCH_002_ARTICLES]
    assert contract["variation_contracts"] == pipeline.REWRITE_BATCH_002_STYLE_CONTRACTS
    assert contract["max_internal_repairs"] == 1


@pytest.mark.parametrize("batch_number", range(3, 11))
def test_prepare_rewrite_batches_003_010_lock_card_order_and_unique_shapes(tmp_path: Path, batch_number: int) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, check=True, capture_output=True, text=True
    ).stdout.strip()
    queue = repo_root / "artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_audit_001/gemini_queue.md"

    prepare_rewrite_batch(repo_root, queue, batch_number, tmp_path, source_commit)
    brief = json.loads((tmp_path / "brief.json").read_text(encoding="utf-8"))
    contract = json.loads((tmp_path / "batch-contract.json").read_text(encoding="utf-8"))

    expected = [item[0] for item in pipeline.REWRITE_BATCH_003_010_IDS[batch_number]]
    assert [item["article_id"] for item in brief["articles"]] == expected
    assert contract["batch_number"] == batch_number
    assert contract["article_order"] == expected
    assert len({item["argumentOrder"] for item in contract["variation_contracts"].values()}) == 5
    assert contract["max_internal_repairs"] == 1


def test_rewrite_range_fails_closed_on_partial_batch(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    partial = tmp_path / "gemini_rewrite_batch_003"
    partial.mkdir()
    (partial / "brief.json").write_text("{}", encoding="utf-8")

    with pytest.raises(RuntimeError, match="partial and cannot resume"):
        pipeline.run_rewrite_range(
            repo_root,
            repo_root / "artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_audit_001/gemini_queue.md",
            tmp_path,
            subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root, check=True, capture_output=True, text=True).stdout.strip(),
            object(),
        )


def test_runtime_retry_preserves_failed_operation_receipt(tmp_path: Path) -> None:
    class FlakyClient:
        writer_model = "test-writer"

        def __init__(self) -> None:
            self.calls = 0

        def generate_json(self, role: str, prompt: str, schema: dict[str, object]) -> dict[str, object]:
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("sandbox unavailable")
            return {"value": "ok"}

    client = FlakyClient()
    receipt = tmp_path / "writer-operation.json"
    with pytest.raises(RuntimeError, match="sandbox unavailable"):
        pipeline._generate_with_receipt(client, "writer", "prompt", {"type": "object"}, receipt)
    original = receipt.read_bytes()

    result = pipeline._generate_with_receipt(client, "writer", "prompt", {"type": "object"}, receipt)

    assert result == {"value": "ok"}
    assert receipt.read_bytes() == original
    retry = json.loads((tmp_path / "writer-operation-runtime-retry-01.json").read_text(encoding="utf-8"))
    assert retry["status"] == "success"


def test_operation_receipt_records_selected_fallback_model(tmp_path: Path) -> None:
    class RoutedClient:
        writer_model = pipeline.DEFAULT_WRITER_MODEL

        def generate_json(
            self,
            role: str,
            prompt: str,
            schema: dict[str, object],
        ) -> dict[str, object]:
            return {"value": "ok"}

        def active_model(self, role: str) -> str:
            assert role == "writer"
            return "gemini-selected-fallback"

    receipt_path = tmp_path / "writer-operation.json"

    pipeline._generate_with_receipt(
        RoutedClient(),
        "writer",
        "public prompt",
        {"type": "object"},
        receipt_path,
    )

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["model"] == "gemini-selected-fallback"


def test_operation_receipt_persists_closed_cli_code_without_exception_text(
    tmp_path: Path,
) -> None:
    private_detail = "/Users/example/private GEMINI_API_KEY=must-not-persist raw stderr"

    class FailedClient:
        writer_model = "test-writer"

        def generate_json(
            self,
            role: str,
            prompt: str,
            schema: dict[str, object],
        ) -> dict[str, object]:
            raise pipeline.GeminiCliFailure("CLI_TIMEOUT") from RuntimeError(private_detail)

    receipt_path = tmp_path / "writer-operation.json"
    with pytest.raises(pipeline.GeminiCliFailure):
        pipeline._generate_with_receipt(
            FailedClient(),
            "writer",
            "public prompt",
            {"type": "object"},
            receipt_path,
        )

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["error_type"] == "GeminiCliFailure"
    assert receipt["error_code"] == "CLI_TIMEOUT"
    persisted = receipt_path.read_text(encoding="utf-8")
    for forbidden in ("response", "stdout", "stderr", "GEMINI_API_KEY", "/Users/"):
        assert forbidden not in persisted


def test_operation_receipt_persists_only_closed_http_diagnostic(
    tmp_path: Path,
) -> None:
    private_detail = "/Users/example/private GEMINI_API_KEY=must-not-persist provider body"

    class FailedClient:
        writer_model = "test-writer"

        def generate_json(
            self,
            role: str,
            prompt: str,
            schema: dict[str, object],
        ) -> dict[str, object]:
            raise pipeline.GeminiApiFailure(
                "API_HTTP_ERROR",
                http_status=503,
            ) from RuntimeError(private_detail)

    receipt_path = tmp_path / "writer-operation.json"
    with pytest.raises(pipeline.GeminiApiFailure):
        pipeline._generate_with_receipt(
            FailedClient(),
            "writer",
            "public prompt",
            {"type": "object"},
            receipt_path,
        )

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["error_type"] == "GeminiApiFailure"
    assert receipt["error_code"] == "API_HTTP_ERROR"
    assert receipt["http_status"] == 503
    assert receipt["http_status_class"] == "5xx"
    persisted = receipt_path.read_text(encoding="utf-8")
    for forbidden in ("response", "body", "GEMINI_API_KEY", "/Users/"):
        assert forbidden not in persisted


@pytest.mark.parametrize(
    "unsafe_error_code",
    [
        ["CLI_TIMEOUT"],
        {"error_code": "CLI_TIMEOUT"},
        7,
        None,
        "UNKNOWN_ERROR_CODE",
    ],
)
def test_operation_receipt_ignores_non_string_unhashable_or_unknown_error_code(
    tmp_path: Path,
    unsafe_error_code: object,
) -> None:
    original_error = RuntimeError("synthetic closed failure")
    original_error.error_code = unsafe_error_code  # type: ignore[attr-defined]

    class FailedClient:
        writer_model = "test-writer"

        def generate_json(
            self,
            role: str,
            prompt: str,
            schema: dict[str, object],
        ) -> dict[str, object]:
            raise original_error

    receipt_path = tmp_path / "writer-operation.json"
    with pytest.raises(RuntimeError) as raised:
        pipeline._generate_with_receipt(
            FailedClient(),
            "writer",
            "public prompt",
            {"type": "object"},
            receipt_path,
        )

    assert raised.value is original_error
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["error_type"] == "RuntimeError"
    assert "error_code" not in receipt


def test_writer_schema_retry_does_not_consume_content_repair_budget(tmp_path: Path) -> None:
    run_dir = tmp_path / "schema-budget"
    run_dir.mkdir()
    brief = {
        "schema_version": 1,
        "run_id": "schema-budget-run",
        "mode": "optimize",
        "allowed_fields": ["title", "description", "answer"],
        "articles": [
            {
                "article_id": "PUBLIC-001",
                "canonical_path": "/articles/astrology/astrology-0001",
                "source_file": "app/web/static/article-registry.js",
                "current": {"title": "舊標題", "description": "舊描述", "answer": "舊答案"},
                "queries": [{"query": "公開搜尋詞"}],
            }
        ],
    }
    (run_dir / "brief.json").write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
    proposed = {
        "title": "公開搜尋詞怎麼看？整理使用情境與限制",
        "description": "公開搜尋詞適合用來整理讀者真正想確認的情境、可觀察資訊與下一步選擇；本文只提供一般說明，不能替個人判斷，也不承諾任何特定結果，仍須回到實際資料與互動再決定。",
        "answer": "先確認具體情境與資料；這項說明不能替個人下結論。",
    }
    writer_results = [
        {"articles": [{"slot": "article-01", "proposed": proposed}]},
        {"articles": [{"slot": "article-01"}]},
        {"articles": [{"slot": "article-01", "proposed": proposed}]},
    ]
    reviewer_results = [
        {"articles": [{"slot": "article-01", "verdict": "REJECT", "findings": [{"code": "copy", "message": "請再具體"}]}]},
        {"articles": [{"slot": "article-01", "verdict": "APPROVE", "findings": []}]},
    ]

    class SequenceClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def generate_json(self, role: str, _prompt: str, _schema: dict[str, object]) -> dict[str, object]:
            return (writer_results if role == "writer" else reviewer_results).pop(0)

    candidate, review = pipeline.run_writer_reviewer(run_dir, SequenceClient(), max_repairs=1)
    evidence = json.loads((run_dir / "run-evidence.json").read_text())

    assert candidate["articles"][0]["proposed"] == proposed
    assert review["articles"][0]["verdict"] == "APPROVE"
    assert evidence["content_repairs_used"] == 1
    assert evidence["schema_repairs_used"] == 1
    assert evidence["attempts"] == 3


def test_rewrite_050_summary_requires_50_unique_candidates(tmp_path: Path) -> None:
    sources = ["gemini_rewrite_batch_001_repair_001", "gemini_rewrite_batch_002", *[f"gemini_rewrite_batch_{batch:03d}" for batch in range(3, 11)]]
    for batch_index, name in enumerate(sources, start=1):
        run_dir = tmp_path / name
        articles = [{"article_id": f"ARTICLE-{batch_index:02d}-{index:02d}"} for index in range(1, 6)]
        pipeline.write_json(run_dir / "candidate.json", {"articles": articles})
        pipeline.write_json(run_dir / "review.json", {"articles": [{"verdict": "APPROVE"} for _ in articles]})
        pipeline.write_json(run_dir / "run-evidence.json", {"candidate_sha256": str(batch_index), "writer_processes": 5, "reviewer_processes": 1})
        pipeline.write_json(run_dir / "deterministic-quality-findings.json", [])
        pipeline.write_json(run_dir / "uniqueness-findings.json", [])

    summary = pipeline._write_rewrite_050_summary(tmp_path)

    assert summary["status"] == "CANDIDATES_050_READY"
    assert summary["candidate_count"] == 50
    assert summary["unique_candidate_count"] == 50
    assert summary["formal_apply"] is False
    assert (tmp_path / "gemini_rewrite_to_050" / "summary.md").is_file()


def test_prepare_rewrite_release_targets_only_rejected_articles(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = repo_root / "artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_batch_002"
    run_dir = tmp_path / "batch_002" / "generation_01"

    path = pipeline.prepare_rewrite_release_generation(source_dir, run_dir, 2, 1)

    assert path == run_dir / "brief.json"
    contract = json.loads((run_dir / "release-contract.json").read_text(encoding="utf-8"))
    source_candidate = json.loads((source_dir / "candidate.json").read_text(encoding="utf-8"))
    copied_candidate = json.loads((run_dir / "source-candidate.json").read_text(encoding="utf-8"))
    assert contract["target_article_ids"] == ["THEME-CAREER-05", "THEME-WEALTH-05", "THEME-INTERPERSONAL-05"]
    assert contract["max_attempts"] == 2
    assert copied_candidate == source_candidate
    assert set(contract["variation_contracts"]) == set(contract["article_order"])

    second_run_dir = tmp_path / "batch_002" / "generation_02"
    pipeline.write_json(run_dir / "candidate.json", source_candidate)
    pipeline.write_json(
        run_dir / "review.json",
        json.loads((source_dir / "review.json").read_text(encoding="utf-8")),
    )
    pipeline.prepare_rewrite_release_generation(run_dir, second_run_dir, 2, 2)
    second_contract = json.loads((second_run_dir / "release-contract.json").read_text(encoding="utf-8"))
    assert second_contract["variation_contracts"] == contract["variation_contracts"]


def test_release_batch1_local_closure_rejects_pre_v2_candidate_without_policy_contract(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = repo_root / "artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_release_001/batch_001/generation_03"
    run_dir = tmp_path / "batch_001" / "generation_04"
    pipeline.prepare_rewrite_release_generation(source_dir, run_dir, 1, 4)

    with pytest.raises(CandidateValidationError, match="publicationPolicy"):
        pipeline.run_release_batch1_local_closure(run_dir)


def test_apply_rewrite_release_fails_closed_before_ready(tmp_path: Path) -> None:
    release_root = tmp_path / "release"
    pipeline.write_json(release_root / "summary.json", {"status": "BLOCKED"})

    with pytest.raises(ValueError, match="not ready for apply"):
        pipeline.apply_rewrite_release(tmp_path, release_root)


def test_integrated_matrix_backlog_keeps_daily_queue_first_then_v2() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    backlog = build_matrix_backlog(repo_root)
    backlog_ids = [item["id"] for item in backlog]
    legacy_rows = pipeline._matrix_rows((repo_root / pipeline.MATRIX_PLAN).read_text(encoding="utf-8"))
    remaining_daily = [row["id"] for row in legacy_rows if row["id"] in DAILY_QUEUE_IDS and row["id"] in backlog_ids]

    assert backlog_ids[: len(remaining_daily)] == remaining_daily
    assert len(backlog) >= 1000
    assert len(set(backlog_ids)) == len(backlog)
    assert any(item["id"].startswith("V2-") for item in backlog[len(remaining_daily) :])


def test_apply_writes_only_approved_articles_without_git_actions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    web = tmp_path / "app" / "web"
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
        'export const ARTICLE_REGISTRY = [\n  ...EXISTING_RECORDS,\n];\nfunction listArticleRecords() { return []; }\n',
        encoding="utf-8",
    )
    (static / "article-meta.js").write_text(
        'const ARTICLE_BODY_LIBRARY = {\n  ...EXISTING_BODIES,\n};\n',
        encoding="utf-8",
    )
    article = make_article()
    monkeypatch.setattr(pipeline, "_registry_inventory", lambda _: [])
    monkeypatch.setattr(pipeline, "load_publication_reference_corpus", lambda _: [])
    review = {
        "schema_version": 1,
        "run_id": "run-one",
        "articles": [
            {"article_id": article["id"], "candidate_sha256": article_sha256(article), "verdict": "APPROVE", "findings": []}
        ],
    }
    approval = build_approval("run-one", [article], review, {str(article["id"]): "APPROVE"}, "user")

    changed = apply_approved_candidates(tmp_path, "run-one", [article], review, approval)

    module = static / "article-expansion-agy-run-one.js"
    assert module in changed
    assert str(article["title"]) in module.read_text(encoding="utf-8")
    assert "article-expansion-agy-run-one.js" in (static / "article-registry.js").read_text(encoding="utf-8")
    assert "article-expansion-agy-run-one.js" in (static / "article-meta.js").read_text(encoding="utf-8")
    hub = (web / "articles.html").read_text(encoding="utf-8")
    expected_updated = str(article["updated"])
    assert f'<meta property="article:modified_time" content="{expected_updated}" />' in hub
    assert f'"dateModified": "{expected_updated}"' in hub
    assert f'<time datetime="{expected_updated}" data-articles-updated>{expected_updated}</time>' in hub
    assert not (tmp_path / ".git").exists()

    (web / "articles.html").write_text(
        hub.replace(expected_updated, "2026-07-18"),
        encoding="utf-8",
    )
    article["title"] = "測試關鍵字是什麼？同一批修稿後可安全重放"
    review = {
        "schema_version": 1,
        "run_id": "run-one",
        "articles": [
            {"article_id": article["id"], "candidate_sha256": article_sha256(article), "verdict": "APPROVE", "findings": []}
        ],
    }
    approval = build_approval("run-one", [article], review, {str(article["id"]): "APPROVE"}, "user")
    monkeypatch.setattr(
        pipeline,
        "_registry_inventory",
        lambda _: [{"id": article["id"], "path": "/articles/personality/personality-9999"}],
    )

    changed = apply_approved_candidates(tmp_path, "run-one", [article], review, approval)
    assert module in changed
    assert str(article["title"]) in module.read_text(encoding="utf-8")
    assert "2026-07-18" in (web / "articles.html").read_text(encoding="utf-8")

    other_review = {**review, "run_id": "run-two"}
    other_approval = build_approval("run-two", [article], other_review, {str(article["id"]): "APPROVE"}, "user")
    with pytest.raises(ValueError, match="identity already exists"):
        apply_approved_candidates(tmp_path, "run-two", [article], other_review, other_approval)


def test_optimize_apply_uses_three_field_override_and_rejects_source_drift(tmp_path: Path) -> None:
    static = tmp_path / "app" / "web" / "static"
    static.mkdir(parents=True)
    registry = static / "article-registry.js"
    registry.write_text(
        """
export const ARTICLE_REGISTRY = [{
  id: "OLD-001", section: "mbti", slug: "old", product: "personality",
  title: "舊標題", description: "舊描述", answer: "舊答案",
}];
function getArticleSectionRecord() { return {}; }
function enforceArticlePolicy(article) { return article; }
export function listArticleRecords() {
  return ARTICLE_REGISTRY.map((article) => enforceArticlePolicy(article, getArticleSectionRecord(article.section)));
}
export function getArticlePath() { return "/articles/personality/personality-0001"; }
""".strip()
        + "\n",
        encoding="utf-8",
    )
    article = {
        "article_id": "OLD-001",
        "canonical_path": "/articles/personality/personality-0001",
        "source_file": "app/web/static/article-registry.js",
        "current": {"title": "舊標題", "description": "舊描述", "answer": "舊答案"},
        "proposed": {"title": "新標題", "description": "新描述", "answer": "新答案"},
    }
    candidate = {"schema_version": 1, "run_id": "gsc-one", "mode": "optimize", "articles": [article]}
    validate_candidate(candidate)
    review = {
        "schema_version": 1,
        "run_id": "gsc-one",
        "articles": [{"article_id": "OLD-001", "candidate_sha256": article_sha256(article), "verdict": "APPROVE", "findings": []}],
    }
    approval = build_approval("gsc-one", [article], review, {"OLD-001": "APPROVE"}, "user")

    changed = apply_approved_candidates(tmp_path, "gsc-one", [article], review, approval)

    assert changed == [registry]
    updated = registry.read_text(encoding="utf-8")
    assert '"title": "新標題"' in updated
    assert '"description": "新描述"' in updated
    assert '"answer": "新答案"' in updated
    assert "ARTICLE_SEO_COPY_OVERRIDES[article.id]" in updated

    drifted = json.loads(json.dumps(article, ensure_ascii=False))
    drifted["current"]["title"] = "不是目前標題"
    drift_review = {
        "schema_version": 1,
        "run_id": "gsc-two",
        "articles": [{"article_id": "OLD-001", "candidate_sha256": article_sha256(drifted), "verdict": "APPROVE", "findings": []}],
    }
    drift_approval = build_approval("gsc-two", [drifted], drift_review, {"OLD-001": "APPROVE"}, "user")
    with pytest.raises(ValueError, match="source drift"):
        apply_approved_candidates(tmp_path, "gsc-two", [drifted], drift_review, drift_approval)
