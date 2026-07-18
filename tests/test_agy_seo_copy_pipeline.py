from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
import scripts.agy_seo_copy_pipeline as pipeline

from scripts.agy_seo_copy_pipeline import (
    CandidateValidationError,
    GeminiClient,
    apply_approved_candidates,
    article_sha256,
    build_approval,
    build_matrix_backlog,
    invalid_review_payload,
    prepare_matrix_runs,
    render_review_markdown,
    review_schema,
    validate_apply_gate,
    validate_candidate,
    validate_new_brief,
    validate_optimize_brief,
    validate_review,
)
from scripts.gsc_opportunity_brief import (
    BriefSizeError,
    choose_single_property,
    select_opportunities,
    write_bounded_json,
)


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

AGY_MATRIX_IDS = AGY_V1_MATRIX_IDS | AGY_ASC_BATCH_02_IDS


def make_article(article_id: str = "TEST-001") -> dict[str, object]:
    return {
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
                    "收到合作邀請時，先確認期限、責任與退出條件，再決定是否答應。",
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


def test_gsc_selects_at_most_five_rank_4_to_20_low_ctr_pages() -> None:
    rows = []
    for index in range(8):
        rows.append(
            {
                "keys": [f"https://mysticpantheon.com/articles/test-{index}", f"query-{index}"],
                "clicks": index,
                "impressions": 1000 - index * 50,
                "ctr": index / 1000,
                "position": 4 + index,
            }
        )
    rows.extend(
        [
            {"keys": ["https://mysticpantheon.com/articles/rank-3", "q"], "clicks": 0, "impressions": 5000, "ctr": 0, "position": 3.9},
            {"keys": ["https://mysticpantheon.com/articles/high-ctr", "q"], "clicks": 100, "impressions": 1000, "ctr": 0.1, "position": 8},
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
    external = {
        "articles": [
            {"slot": "article-01", "primaryKeyword": complete["primaryKeyword"]}
            | {field: complete[field] for field in pipeline.PUBLIC_CREATE_FIELDS}
        ]
    }

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
    assert (body["minItems"], body["maxItems"]) == (5, 5)
    paragraphs = body["items"]["properties"]["paragraphs"]
    assert (paragraphs["minItems"], paragraphs["maxItems"]) == (3, 3)


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
    assert "英文殘字與錯別字" in prompt


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


def test_matrix_backlog_uses_semantic_aliases_and_avoids_duplicates(monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    integrated_inventory = pipeline._registry_inventory(repo_root)
    baseline_inventory = [item for item in integrated_inventory if str(item.get("id")) not in AGY_MATRIX_IDS]
    monkeypatch.setattr(pipeline, "_registry_inventory", lambda _: baseline_inventory)
    backlog = build_matrix_backlog(repo_root)
    ids = {item["id"] for item in backlog}

    assert "CHART-PALACE-CAREER" not in ids  # 既有文章使用「事業宮」名稱。
    assert "CHART-CYCLE-YEAR" not in ids  # 既有八字流年文章已覆蓋泛用主關鍵字。
    assert {"MBTI-INTP-AH", "MBTI-INTP-AC", "MBTI-INTP-OH", "MBTI-INTP-OC"} <= ids
    assert {"ASC-ARIES", "ASC-TAURUS", "ASC-GEMINI"} <= ids
    assert "CHART-CYCLE-DECADE" in ids
    assert ids == AGY_MATRIX_IDS


def test_matrix_prepare_allocates_final_unique_identity_before_writer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    integrated_inventory = pipeline._registry_inventory(repo_root)
    baseline_inventory = [item for item in integrated_inventory if str(item.get("id")) not in AGY_MATRIX_IDS]
    monkeypatch.setattr(pipeline, "_registry_inventory", lambda _: baseline_inventory)
    paths = prepare_matrix_runs(repo_root, "identity-test", output_root=tmp_path)
    briefs = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    items = [item for brief in briefs for item in brief["articles"]]
    serials = [item["target"]["serial"] for item in items]

    assert len(items) == 13
    assert len(serials) == len(set(serials))
    assert all(item["target"]["published"] == date.today().isoformat() for item in items)
    assert all(item["target"]["primaryKeyword"] == item["matrix"]["primaryKeyword"] for item in items)
    assert all(len(json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")) <= 8192 for item in items)

    remaining_paths = prepare_matrix_runs(
        repo_root,
        "identity-remaining",
        output_root=tmp_path,
        exclude_ids={"MBTI-INTP-AH"},
    )
    remaining = [item for path in remaining_paths for item in json.loads(path.read_text(encoding="utf-8"))["articles"]]
    original_targets = {item["matrix"]["id"]: item["target"] for item in items}
    assert len(remaining) == 12
    assert all(item["target"] == original_targets[item["matrix"]["id"]] for item in remaining)


def test_integrated_matrix_backlog_is_empty() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    assert build_matrix_backlog(repo_root) == []


def test_apply_writes_only_approved_articles_without_git_actions(tmp_path: Path) -> None:
    static = tmp_path / "app" / "web" / "static"
    static.mkdir(parents=True)
    (static / "article-registry.js").write_text(
        'export const ARTICLE_REGISTRY = [\n  ...EXISTING_RECORDS,\n];\n',
        encoding="utf-8",
    )
    (static / "article-meta.js").write_text(
        'const ARTICLE_BODY_LIBRARY = {\n  ...EXISTING_BODIES,\n};\n',
        encoding="utf-8",
    )
    article = make_article()
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
    assert not (tmp_path / ".git").exists()


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
