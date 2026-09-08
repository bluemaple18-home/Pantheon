from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import agy_multilingual_pipeline as m
from scripts import agy_gemini_coordinator as c
from test_agy_multilingual_pipeline import source_article, translation_brief, external_locale_plan, translation_candidate


def article_policy():
    return {
        "policyVersion": m.pipeline.publication_policy_version(),
        "canonical": "https://www.mysticpantheon.com/articles/tarot/tarot-0001",
        "author": {"name": "Pantheon 編輯部", "url": "https://www.mysticpantheon.com/#organization", "id": "https://www.mysticpantheon.com/#organization"},
        "editorialResponsibility": "Pantheon 編輯部",
        "evidence": {"mode": "cultural_reflection", "sources": [], "disclosure": "  本文不能診斷疾病，也不能建議停藥。\n請保留條件。  "},
        "published": "2026-09-08", "modified": "2026-09-08", "changeType": "created",
    }


def test_loader_policy_only_changes_identity(monkeypatch):
    policy = article_policy()
    def run(*args, **kwargs):
        return SimpleNamespace(stdout=json.dumps({**source_article(), "publication_policy": {"contract_version": 1, "global_policy": m.pipeline.load_article_publication_policy(), "article_policy": policy}}))
    monkeypatch.setattr(m.subprocess, "run", run)
    before = m.load_source_article(Path.cwd(), "TEST-001")
    policy["evidence"]["disclosure"] += "另一項限制。"
    after = m.load_source_article(Path.cwd(), "TEST-001")
    assert m.source_sha256(before) != m.source_sha256(after)


def new_brief(locale="ja"):
    brief = translation_brief(locale)
    source = brief["articles"][0]["source"]
    source["publication_policy"] = m.source_publication_policy(article_policy())
    source["answer"] = source["publication_policy"]["article_policy"]["evidence"]["disclosure"]
    brief["articles"][0]["source_sha256"] = m.source_sha256(source)
    return brief


def test_article_disclosure_fact_keeps_policy_provenance_in_source():
    brief = new_brief()
    facts = m._source_fact_package(brief)["articles"][0]["facts"]
    disclosure = article_policy()["evidence"]["disclosure"]
    matching = [fact for fact in facts if fact["text"] == disclosure]
    assert len(matching) == 1
    assert {fact["field_path"] for fact in matching} == {"answer"}
    assert brief["articles"][0]["source"]["publication_policy"]["article_policy"]["evidence"]["disclosure"] == disclosure
    assert len({fact["fact_id"] for fact in facts}) == len(facts)
    assert all(fact["provenance"] == "source" for fact in facts)
    assert any(fact["safety_boundary"] for fact in matching)


def test_new_contract_all_consumers_and_semantic_owner():
    brief = new_brief()
    plan = m._hydrate_locale_plan(brief, external_locale_plan(brief), generation=1, prior_plan=None, rebuild_by_slot={"article-01": False})
    prompts = [m._plan_prompt(brief, generation=1, prior_plan=None, findings=[], rebuild_by_slot={"article-01": False}), m._article_prompt(brief, plan, []), m._reviewer_prompt(brief, translation_candidate("ja"), [])]
    for prompt in prompts:
        assert json.dumps(article_policy()["evidence"]["disclosure"], ensure_ascii=False) in prompt
        assert '"global_policy"' in prompt and '"article_policy"' in prompt
        assert "JA field-by-field protected boundary checklist" not in prompt
        assert "是 boundary coverage authority" not in prompt
    assert m._ja_boundary_findings(brief, translation_candidate("ja")["articles"][0], brief["articles"][0]["source"]) == []
    broken = copy.deepcopy(plan)
    broken["articles"][0]["coverage_mapping"].pop()
    with pytest.raises(ValueError, match="coverage"):
        m.validate_locale_plan(brief, broken)
    review = m._review_generated_candidate(brief, translation_candidate("ja"), {"articles": [{"slot": "article-01", "verdict": "REJECT", "findings": [{"code": "BOUNDARY_MEANING_MISSING", "message": "停藥限制遺失"}]}]}, [])
    assert not m._review_approved(review)
    with pytest.raises((ValueError, KeyError)):
        m._review_generated_candidate(brief, translation_candidate("ja"), {"articles": []}, [])


@pytest.mark.parametrize("lane", ["new", "rewrite"])
def test_producers_same_shape_and_identity(lane, monkeypatch):
    visible = source_article()
    policy = article_policy()
    item = {"article_id": visible["article_id"], "lane": lane, "candidate": {"articles": [{**visible, "publicationPolicy": policy}]}, "brief": {"articles": [{"immutable_fields": visible}]}}
    campaign = c._campaign_translation_source(item)
    monkeypatch.setattr(m.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout=json.dumps({**visible, "publication_policy": m.source_publication_policy(policy)})))
    loaded = m.load_source_article(Path.cwd(), visible["article_id"])
    assert campaign == loaded
    assert m.source_sha256(campaign) == m.source_sha256(loaded)
    policy["evidence"]["disclosure"] += "修改"
    assert campaign["publication_policy"]["article_policy"] != policy


@pytest.mark.parametrize("mutation", [
    lambda s: s.pop("publication_policy"),
    lambda s: s.update(publication_policy=None),
    lambda s: s["publication_policy"].update(contract_version=0),
    lambda s: s["publication_policy"].update(contract_version=True),
    lambda s: s["publication_policy"].update(global_policy={}),
    lambda s: s["publication_policy"]["global_policy"].update(policy_version="old"),
    lambda s: s["publication_policy"]["article_policy"].update(policyVersion="old"),
    lambda s: s["publication_policy"]["article_policy"]["evidence"].update(disclosure=[]),
    lambda s: s["publication_policy"]["article_policy"]["evidence"].pop("sources"),
])
def test_formal_loader_rejects_missing_old_or_malformed(mutation, monkeypatch):
    source = new_brief()["articles"][0]["source"]
    mutation(source)
    monkeypatch.setattr(m.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout=json.dumps(source)))
    with pytest.raises(ValueError):
        m.load_source_article(Path.cwd(), "TEST-001")


def test_global_policy_only_digest_and_legacy():
    source = new_brief()["articles"][0]["source"]
    before = m.source_sha256(source)
    source["publication_policy"]["global_policy"]["levels"]["required"] += "新增限制"
    m.validate_source_contract(source)
    assert m.source_sha256(source) != before
    assert m._validate_source(source_article()) == source_article()
    with pytest.raises(ValueError):
        m.validate_source_contract(source_article())


@pytest.mark.parametrize("locale", ["en", "ja", "ko"])
def test_every_source_leaf_reaches_every_consumer(locale):
    brief = new_brief(locale)
    source = brief["articles"][0]["source"]
    source["publication_policy"]["article_policy"]["evidence"]["mode"] = "sources"
    source["publication_policy"]["article_policy"]["evidence"]["sources"] = [{"title": "限制證據", "url": "https://example.com/reference", "supports": ["不得據此診斷或停藥"]}]
    brief["articles"][0]["source_sha256"] = m.source_sha256(source)
    plan = m._hydrate_locale_plan(brief, external_locale_plan(brief), generation=1, rebuild_by_slot={"article-01": False})
    public = m._public_brief(brief)["articles"][0]["source"]
    package = m._source_fact_package_for_prompt(brief, m._request_local_source_ref_maps(brief, plan))["articles"][0]
    assert public == package["source"] == source
    def leaves(value):
        if isinstance(value, dict):
            return [text for child in value.values() for text in leaves(child)]
        if isinstance(value, list):
            return [text for child in value for text in leaves(child)]
        return [value]
    expected = [text for key, value in source.items() if key not in {"article_id", "canonical_path"} for text in leaves(value)]
    article_expected = [text for key, value in source.items() if key not in {"article_id", "canonical_path", "publication_policy"} for text in leaves(value)]
    assert sorted(f["text"] for f in package["facts"]) == sorted(article_expected)
    assert all("field_path" in fact for fact in package["facts"])
    prompts = [m._plan_prompt(brief, generation=1, prior_plan=None, findings=[], rebuild_by_slot={"article-01": False}), m._article_prompt(brief, plan, []), m._reviewer_prompt(brief, translation_candidate(locale), [])]
    for prompt in prompts:
        for text in expected:
            assert json.dumps(text, ensure_ascii=False) in prompt


def approval_for(candidate):
    review = {"schema_version": 1, "run_id": candidate["run_id"], "articles": [{"article_id": article["article_id"], "candidate_sha256": m.pipeline.article_sha256(article), "verdict": "APPROVE", "hard_failure": False, "findings": []} for article in candidate["articles"]]}
    approval = m.pipeline.build_approval(candidate["run_id"], candidate["articles"], review, {article["article_id"]: "APPROVE" for article in candidate["articles"]}, "test")
    return review, approval


def test_apply_refuses_legacy_before_loading_or_writing(tmp_path):
    candidate = translation_candidate()
    review, approval = approval_for(candidate)
    static = tmp_path / "app/web/static"
    static.mkdir(parents=True)
    (static / "article-locales.js").write_text("export const ARTICLE_LOCALE_REGISTRY = [\n];\n")
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    calls = []
    def loader(*args):
        calls.append(args)
        return source_article()
    with pytest.raises(ValueError, match="publication_policy"):
        m.apply_approved_translations(tmp_path, "legacy", translation_brief(), candidate, review, approval, source_loader=loader)
    assert calls == []
    assert {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before


def test_snapshot_reads_current_file_despite_warm_cache(tmp_path, monkeypatch):
    current = copy.deepcopy(m.pipeline.load_article_publication_policy())
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(current))
    original = m.pipeline.load_article_publication_policy
    monkeypatch.setattr(m.pipeline, "load_article_publication_policy", lambda supplied=None: original(path) if supplied is not None else current)
    before = m.source_publication_policy(article_policy())
    changed = copy.deepcopy(current)
    changed["levels"]["required"] += "同版本新增限制"
    path.write_text(json.dumps(changed))
    after = m.source_publication_policy(article_policy())
    assert before != after


def test_real_loader_record_policy_and_uncached_global(tmp_path):
    static = tmp_path / "app/web/static"
    static.mkdir(parents=True)
    visible = source_article()
    policy = article_policy()
    record = {"id": visible["article_id"], "publicationPolicy": policy}
    (static / "article-registry.js").write_text("export const getArticlePath = () => " + json.dumps(visible["canonical_path"]) + "; export const listArticleRecords = () => " + json.dumps([record], ensure_ascii=False) + ";")
    (static / "article-meta.js").write_text("export const buildArticleContent = () => (" + json.dumps({**visible, "displayTags": visible["tags"]}, ensure_ascii=False) + ");")
    path = tmp_path / m.pipeline.POLICY_V2_PATH
    path.parent.mkdir(parents=True)
    global_policy = copy.deepcopy(m.pipeline.load_article_publication_policy())
    path.write_text(json.dumps(global_policy))
    loaded = m.load_source_article(tmp_path, visible["article_id"])
    campaign = c._campaign_translation_source({"article_id": visible["article_id"], "lane": "new", "candidate": {"articles": [{**visible, "publicationPolicy": policy}]}})
    assert loaded == campaign
    # 真正 Node producer 的逐篇 policy-only 與無 policy 對照，不以 mock JSON 取代。
    policy["evidence"]["disclosure"] += "逐篇新增限制。"
    registry = static / "article-registry.js"
    registry.write_text("export const getArticlePath = () => " + json.dumps(visible["canonical_path"]) + "; export const listArticleRecords = () => " + json.dumps([record], ensure_ascii=False) + ";")
    policy_after = m.load_source_article(tmp_path, visible["article_id"])
    assert m.source_sha256(policy_after) != m.source_sha256(loaded)
    saved = registry.read_bytes()
    registry.write_text("export const getArticlePath = () => " + json.dumps(visible["canonical_path"]) + "; export const listArticleRecords = () => " + json.dumps([{"id": visible["article_id"]}]) + ";")
    with pytest.raises(ValueError, match="publication policy fields"):
        m.load_source_article(tmp_path, visible["article_id"])
    registry.write_bytes(saved)
    global_policy["levels"]["required"] += "同版本新增約束"
    path.write_text(json.dumps(global_policy))
    after = m.load_source_article(tmp_path, visible["article_id"])
    assert m.source_sha256(after) != m.source_sha256(policy_after)


def test_apply_new_contract_positive_and_current_legacy_rejected(tmp_path):
    brief = new_brief("en")
    source = brief["articles"][0]["source"]
    candidate = translation_candidate()
    candidate["articles"][0]["source_sha256"] = m.source_sha256(source)
    review, approval = approval_for(candidate)
    static = tmp_path / "app/web/static"
    static.mkdir(parents=True)
    (static / "article-locales.js").write_text("export const ARTICLE_LOCALE_REGISTRY = [\n];\n")
    before = (static / "article-locales.js").read_bytes()
    with pytest.raises(ValueError, match="publication_policy"):
        m.apply_approved_translations(tmp_path, candidate["run_id"], brief, candidate, review, approval, source_loader=lambda *args: source_article())
    assert (static / "article-locales.js").read_bytes() == before
    assert len(list(static.iterdir())) == 1
    changed = m.apply_approved_translations(tmp_path, candidate["run_id"], brief, candidate, review, approval, source_loader=lambda *args: source)
    assert changed and all(path.is_file() for path in changed)


@pytest.mark.parametrize("value", [None, {}, {"policyVersion": "old"}])
def test_campaign_rejects_missing_policy(value):
    with pytest.raises(ValueError):
        c._campaign_translation_source({"article_id": "TEST-001", "lane": "new", "candidate": {"articles": [{**source_article(), "publicationPolicy": value}]}})


@pytest.mark.parametrize("replacement", [False, True])
def test_stage_fixture_optional_contract_rebuilds_valid_seal(tmp_path, replacement):
    from test_agy_multilingual_pipeline import approved_stage_fixture, replacement_approved_stage_fixture
    source = new_brief()["articles"][0]["source"]
    factory = replacement_approved_stage_fixture if replacement else approved_stage_fixture
    fixture = factory(tmp_path, source_contract=source)
    plan = m.plan_approved_edited_candidate_stage(**fixture["kwargs"])
    m.apply_approved_edited_candidate_stage(**fixture["kwargs"], expected_plan_digest=plan["plan_digest"])
    loaded = m.load_approved_edited_candidate_stage(fixture["run_dir"])
    assert loaded["candidate"]["articles"][0]["source_sha256"] == m.source_sha256(source)


@pytest.mark.parametrize("evidence", [
    {"mode": "cultural_reflection", "sources": [], "disclosure": "   "},
    {"mode": "sources", "sources": [], "disclosure": "有來源"},
    {"mode": "cultural_reflection", "sources": [{"title": "來源", "url": "https://example.com", "supports": ["限制"]}], "disclosure": "文化反思"},
])
def test_source_rejects_missing_required_policy_evidence(evidence):
    source = new_brief()["articles"][0]["source"]
    source["publication_policy"]["article_policy"]["evidence"] = evidence
    with pytest.raises(ValueError, match="source evidence"):
        m.validate_source_contract(source)


def test_large_current_source_ref_map_roundtrip(tmp_path):
    brief = new_brief()
    source = brief["articles"][0]["source"]
    source["bodySections"][0]["paragraphs"].extend(f"第{index}個具體文章觀察。" for index in range(100))
    brief["articles"][0]["source_sha256"] = m.source_sha256(source)
    path = tmp_path / "source-refs.json"
    args = {"generation": 2, "external_plan_path": tmp_path / "external.json"}
    first = m._load_or_create_source_ref_maps(path, brief, {}, **args)
    assert len(first["article-01"]) > 99
    assert m._load_or_create_source_ref_maps(path, brief, {}, **args) == first
