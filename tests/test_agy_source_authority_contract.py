from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import agy_multilingual_pipeline as m
from scripts import agy_gemini_coordinator as c
from scripts import agy_gemini_runner as runner
from scripts.agy_gemini_outbox import create_external_request
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
def test_every_applicable_source_leaf_reaches_every_consumer(locale):
    brief = new_brief(locale)
    source = brief["articles"][0]["source"]
    source["publication_policy"]["article_policy"]["evidence"]["mode"] = "sources"
    source["publication_policy"]["article_policy"]["evidence"]["sources"] = [{"title": "限制證據", "url": "https://example.com/reference", "supports": ["不得據此診斷或停藥"]}]
    brief["articles"][0]["source_sha256"] = m.source_sha256(source)
    plan = m._hydrate_locale_plan(brief, external_locale_plan(brief), generation=1, rebuild_by_slot={"article-01": False})
    public = m._public_brief(brief)["articles"][0]["source"]
    package = m._source_fact_package_for_prompt(brief, m._request_local_source_ref_maps(brief, plan))["articles"][0]
    expected_source = json.loads(json.dumps(source))
    policy = expected_source["publication_policy"]["global_policy"]
    policy.pop("presentation_constraints")
    policy["writing_contract"].pop("section_flow")
    assert public == package["source"] == expected_source
    assert m._source_fact_package(brief)["articles"][0]["source"] == source
    assert m._public_brief(brief)["articles"][0]["source_sha256"] == m.source_sha256(source)
    def leaves(value):
        if isinstance(value, dict):
            return [text for child in value.values() for text in leaves(child)]
        if isinstance(value, list):
            return [text for child in value for text in leaves(child)]
        return [value]
    expected = [text for key, value in expected_source.items() if key not in {"article_id", "canonical_path"} for text in leaves(value)]
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


@pytest.mark.parametrize('version', ['pantheon-article-publication-v2.0.0', 'pantheon-article-publication-v2.1.0'])
def test_handoff_historical_article_policy_preserves_source_identity(version):
    source = new_brief()['articles'][0]['source']
    source['publication_policy']['article_policy']['policyVersion'] = version
    raw = m.pipeline.compact_json_bytes(source)
    expected_hash = hashlib.sha256(raw).hexdigest()
    assert m.validate_source_contract(source) is source
    assert m.pipeline.compact_json_bytes(source) == raw
    assert m.source_sha256(source) == expected_hash
    article = source['publication_policy']['article_policy']
    assert article['evidence']['disclosure'].encode() == article_policy()['evidence']['disclosure'].encode()
    source['publication_policy']['global_policy']['policy_version'] = 'pantheon-article-publication-v2.0.0'
    with pytest.raises(ValueError, match='unsupported source publication policy version'):
        m.validate_source_contract(source)


@pytest.mark.parametrize('version', ['pantheon-article-publication-v1.0.0', 'pantheon-article-publication-v2.2.0', 'unknown'])
def test_handoff_unknown_article_policy_is_not_upgraded(version):
    source = new_brief()['articles'][0]['source']
    source['publication_policy']['article_policy']['policyVersion'] = version
    raw = m.pipeline.compact_json_bytes(source)
    with pytest.raises(ValueError, match='unsupported source publication policy version'):
        m.validate_source_contract(source)
    assert m.pipeline.compact_json_bytes(source) == raw


@pytest.fixture
def published_dispatch(tmp_path, monkeypatch):
    """真實本地 Git／Node，只有 provider 使用無網路替身。"""
    for key in list(os.environ):
        if key.startswith(("AGY_GEMINI_", "PANTHEON_RUNTIME_", "PANTHEON_FORMAL_")):
            monkeypatch.delenv(key)

    def build(lane="i18n-new", historical=False):
        actor = tmp_path / "actor"
        actor.mkdir()
        queue = tmp_path / "queue"
        state_root = tmp_path / "state"
        state_root.mkdir()
        source = copy.deepcopy(new_brief("en")["articles"][0]["source"])
        static = actor / "app/web/static"
        static.mkdir(parents=True)
        policy_path = actor / m.pipeline.POLICY_V2_PATH
        policy_path.parent.mkdir(parents=True)
        policy_path.write_text(json.dumps(source["publication_policy"]["global_policy"]))
        (actor / "package.json").write_text('{"type":"module"}')

        def git(*args):
            return subprocess.run(
                ["git", "-c", "core.hooksPath=/dev/null", "-c", "user.name=測試",
                 "-c", "user.email=fixture@example.invalid", *args],
                cwd=actor, check=True, capture_output=True, text=True,
            ).stdout.strip()

        def write_source(value, *, present=True, policy=True):
            records = [{"id": value["article_id"]}]
            if policy:
                records[0]["publicationPolicy"] = value["publication_policy"]["article_policy"]
            (static / "article-registry.js").write_text(
                "export const getArticlePath = () => " + json.dumps(value["canonical_path"])
                + "; export const listArticleRecords = () => "
                + json.dumps(records if present else []) + ";"
            )
            (static / "article-meta.js").write_text(
                "export const buildArticleContent = () => ("
                + json.dumps({**value, "displayTags": value["tags"]}) + ");"
            )
            policy_path.write_text(json.dumps(value["publication_policy"]["global_policy"]))

        def commit():
            git("add", ".")
            git("commit", "--quiet", "--allow-empty", "-m", "來源 fixture")
            return git("rev-parse", "HEAD")

        git("init", "--quiet")
        write_source(source, present=lane != "i18n-new", policy=False)
        old = commit()
        write_source(source)
        published = commit()
        git("update-ref", "refs/remotes/origin/main", published)
        source_run = "published-source-01"
        run = m.enqueue_article_translations(
            actor, queue, source_run_id=source_run, article_id=source["article_id"],
            locales=["en"], lane=lane,
        )[0]
        namespace = hashlib.sha256(run["run_id"].encode()).hexdigest()[:24]
        job_root = queue / "lanes" / lane
        request = create_external_request(
            job_root, namespace=namespace, role="writer", model="gemini-3.5-flash-lite",
            prompt="離線來源驗證", response_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
        )
        key = "published_runs" if lane == "i18n-new" else "rewrite_released_runs"
        entry = {"run_id": source_run, "article_ids": [source["article_id"]],
                 "translation_run_ids": [run["run_id"]], "commit_sha": published,
                 "version": "0.3.396", "published_at": "2026-09-10T16:37:33+08:00"}
        ledger = {"schema_version": 1, "published_runs": [], "rewrite_released_runs": []}
        ledger[key].append(entry)

        def save_ledger():
            (state_root / "ledger.json").write_text(json.dumps(ledger))

        save_ledger()
        base = published if historical else old
        git("checkout", "--quiet", "--detach", base)
        monkeypatch.setenv("PANTHEON_RUNTIME_ACTOR_ROOT", str(actor))
        monkeypatch.setenv("PANTHEON_RUNTIME_QUEUE_ROOT", str(queue))
        monkeypatch.setenv("PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT", str(state_root))
        loaded_paths = []
        original_loader = m.load_source_article

        def observe(root, article):
            loaded_paths.append(root)
            return original_loader(root, article)

        monkeypatch.setattr(m, "load_source_article", observe)
        calls = []

        def dispatch():
            before = (git("rev-parse", "HEAD"), git("status", "--porcelain"), (actor / ".git/index").read_bytes())
            result = runner.process_once(job_root, lane=lane, generate_json=lambda *args: calls.append(args) or {"ok": True})
            assert (git("rev-parse", "HEAD"), git("status", "--porcelain"), (actor / ".git/index").read_bytes()) == before
            assert all(not path.exists() for path in loaded_paths if path != actor)
            return result

        def advance(value):
            git("checkout", "--quiet", "--detach", published)
            write_source(value)
            tip = commit()
            git("update-ref", "refs/remotes/origin/main", tip)
            git("checkout", "--quiet", "--detach", base)
            return tip

        return SimpleNamespace(**locals())

    return build


@pytest.mark.parametrize("lane", ["i18n-new", "i18n-rewrite"])
@pytest.mark.parametrize("historical", [False, True])
def test_published_dispatch_reads_committed_source(published_dispatch, lane, historical):
    f = published_dispatch(lane, historical)
    assert f.dispatch()["status"] == "processed"
    assert len(f.calls) == 1
    assert f.loaded_paths and all(path != f.actor for path in f.loaded_paths)


@pytest.mark.parametrize("field", ["body", "policy", "global_policy"])
def test_published_dispatch_rejects_later_source_drift(published_dispatch, field):
    f = published_dispatch(historical=True)
    changed = copy.deepcopy(f.source)
    if field == "body":
        changed["bodySections"][0]["paragraphs"][0] += "發布後更新。"
    elif field == "policy":
        changed["publication_policy"]["article_policy"]["evidence"]["disclosure"] += "新增限制。"
    else:
        changed["publication_policy"]["global_policy"]["levels"]["required"] += "新增限制。"
    f.advance(changed)
    assert f.dispatch()["status"] == "failed"
    assert not f.calls


@pytest.mark.parametrize("fault", [None, "no_ledger", "unpublished", "wrong_lane", "wrong_article",
                                   "missing_commit", "lagging", "body", "policy", "auto_id", "replacement", "later_release"])
def test_native_registered_published_rewrite_without_auto_ledger_id(published_dispatch, fault):
    """原生註冊不回填 publisher 的 auto run 清單，仍須讀取已發布來源。"""
    f = published_dispatch("i18n-rewrite", historical=True)
    run_id = "registered-published-rewrite-ja"
    if fault == "auto_id":
        run_id = "auto-i18n-ja-" + "0" * 20
    path = m.prepare_translation_run(f.actor, run_id, f.source["article_id"], ["ja"], f.queue / "translation-runs")
    brief = json.loads(path.read_text())
    brief["lane"] = "i18n-rewrite"
    path.write_text(json.dumps(brief))
    state = c.register_run(path.parent, f.queue)
    assert state["status"] == "active"
    assert run_id not in f.entry["translation_run_ids"]
    (f.job_root / "outbox" / (f.request["job_id"] + ".json")).unlink()
    create_external_request(f.job_root, namespace=hashlib.sha256(run_id.encode()).hexdigest()[:24],
                            role="reviewer", model="fake-model", prompt="原生已發布來源",
                            response_schema=f.request["response_schema"])
    if fault in {"body", "policy"}:
        changed = copy.deepcopy(f.source)
        if fault == "body":
            changed["bodySections"][0]["paragraphs"][0] += "已發布更新。"
        else:
            changed["publication_policy"]["article_policy"]["evidence"]["disclosure"] += "政策更新。"
        f.advance(changed)
    elif fault == "lagging":
        f.git("update-ref", "refs/remotes/origin/main", f.old)
    elif fault == "replacement":
        state["replacement_of"] = f.run["run_id"]
        (f.queue / "runs" / (hashlib.sha256(run_id.encode()).hexdigest()[:24] + ".json")).write_text(json.dumps(state))
    elif fault == "unpublished":
        f.ledger[f.key] = []
    elif fault == "wrong_lane":
        f.ledger["published_runs"] = f.ledger.pop(f.key)
        f.ledger[f.key] = []
    elif fault == "wrong_article":
        f.entry["article_ids"] = ["OTHER"]
    elif fault == "missing_commit":
        f.entry["commit_sha"] = "f" * 40
    elif fault == "later_release":
        f.ledger[f.key].append({**f.entry, "run_id": "later-published-source", "translation_run_ids": []})
    f.save_ledger()
    ledger_path = f.state_root / "ledger.json"
    if fault == "no_ledger":
        ledger_path.unlink()
    ledger_before = ledger_path.read_bytes() if ledger_path.exists() else None
    f.loaded_paths.clear()
    accepted = fault in {None, "later_release"}
    assert f.dispatch()["status"] == ("processed" if accepted else "failed")
    assert len(f.calls) == (1 if accepted else 0)
    assert (ledger_path.read_bytes() if ledger_path.exists() else None) == ledger_before


@pytest.mark.parametrize("fault", ["lagging", "missing", "nonancestor", "unpublished", "wrong_lane", "wrong_article", "later_ledger", "no_ref", "no_ledger", "duplicate"])
def test_published_dispatch_requires_published_ancestry(published_dispatch, fault):
    f = published_dispatch(historical=True)
    if fault == "lagging":
        f.git("update-ref", "refs/remotes/origin/main", f.old)
    elif fault == "missing":
        f.entry["commit_sha"] = "f" * 40
    elif fault in {"nonancestor", "later_ledger"}:
        unrelated = f.git("commit-tree", f.git("rev-parse", "HEAD^{tree}"), "-m", "未合併來源")
        if fault == "nonancestor":
            f.entry["commit_sha"] = unrelated
        else:
            f.ledger["rewrite_released_runs"].append({**f.entry, "run_id": "later-source", "translation_run_ids": [], "commit_sha": unrelated})
    elif fault == "unpublished":
        f.entry["translation_run_ids"] = []
    elif fault == "no_ref":
        f.git("update-ref", "-d", "refs/remotes/origin/main")
    elif fault == "no_ledger":
        (f.state_root / "ledger.json").unlink()
    elif fault == "duplicate":
        f.ledger[f.key].append(copy.deepcopy(f.entry))
    elif fault == "wrong_lane":
        f.ledger["rewrite_released_runs"] = f.ledger.pop("published_runs")
        f.ledger["published_runs"] = []
    else:
        f.entry["article_ids"] = ["OTHER"]
    if fault != "no_ledger":
        f.save_ledger()
    assert f.dispatch()["status"] == "failed"
    assert not f.calls


@pytest.mark.parametrize("broken", [False, True])
def test_published_dispatch_checks_replacement_lineage(published_dispatch, broken):
    f = published_dispatch(historical=True)
    parent_path = f.queue / "runs" / (f.namespace + ".json")
    parent = json.loads(parent_path.read_text())
    parent["status"] = "failed"
    parent_path.write_text(json.dumps(parent))
    replacement = m.enqueue_translation_replacement(
        f.actor, f.queue, terminal_state=parent,
        recovery_reason=next(iter(m.TRANSLATION_REPLACEMENT_REASONS)),
    )
    namespace = hashlib.sha256(replacement["run_id"].encode()).hexdigest()[:24]
    (f.job_root / "outbox" / (f.request["job_id"] + ".json")).unlink()
    create_external_request(f.job_root, namespace=namespace, role="writer", model="gemini-3.5-flash-lite", prompt="替換來源", response_schema=f.request["response_schema"])
    if broken:
        parent["identity_envelope"] = m.translation_identity_envelope("OTHER", f.lane)
        parent_path.write_text(json.dumps(parent))
    f.loaded_paths.clear()
    result = f.dispatch()
    assert result["status"] == ("failed" if broken else "processed")
    assert len(f.calls) == (0 if broken else 1)


def test_published_dispatch_pins_ref_for_entire_provider_admission(published_dispatch, monkeypatch):
    f = published_dispatch()
    bad = copy.deepcopy(f.source)
    bad["bodySections"][0]["paragraphs"][0] += "下一版不同內容。"
    newer = f.advance(bad)
    f.git("update-ref", "refs/remotes/origin/main", f.published)
    original = subprocess.run
    resolutions = []
    commands = []

    def moving_ref(args, *a, **kw):
        if args[0] == "git":
            commands.append(args)
        result = original(args, *a, **kw)
        if args[0] == "git" and "rev-parse" in args and any("origin/main" in arg for arg in args):
            resolutions.append(args)
            original(["git", "update-ref", "refs/remotes/origin/main", newer], cwd=f.actor, check=True, capture_output=True)
        return result

    monkeypatch.setattr(subprocess, "run", moving_ref)
    assert f.dispatch()["status"] == "processed"
    assert len(resolutions) == 1
    assert len(f.calls) == 1
    assert not any(command in args for args in commands for command in ("fetch", "checkout", "worktree", "update-ref"))


@pytest.mark.parametrize("fault", ["dependency", "symlink", "oversize"])
def test_published_dispatch_snapshot_failure_cleans_up(published_dispatch, fault):
    f = published_dispatch(historical=True)
    f.git("checkout", "--quiet", "--detach", f.published)
    if fault == "dependency":
        (f.static / "article-meta.js").write_text('import "./missing.js"; export const buildArticleContent = () => ({});')
    elif fault == "symlink":
        path = f.static / "article-meta.js"
        path.unlink()
        path.symlink_to("../../../../outside.js")
    else:
        (f.static / "large.js").write_bytes(b" " * (17 * 1024 * 1024))
    bad = f.commit()
    f.git("update-ref", "refs/remotes/origin/main", bad)
    f.git("checkout", "--quiet", "--detach", f.base)
    assert f.dispatch()["status"] == "failed"
    assert not f.calls


def test_published_dispatch_projection_rejects_path_escape(published_dispatch, monkeypatch):
    f = published_dispatch(historical=True)
    original = subprocess.run

    def corrupt_listing(args, *a, **kw):
        result = original(args, *a, **kw)
        if args[0] == "git" and "ls-tree" in args:
            row = result.stdout.split(b"\0")[0].split(b"\t")[0]
            result.stdout += row + b"\tapp/web/static/../../../escaped.js\0"
        return result

    monkeypatch.setattr(subprocess, "run", corrupt_listing)
    assert f.dispatch()["status"] == "failed"
    assert not f.calls and not f.loaded_paths


def test_published_dispatch_projection_write_error_cleans_up(published_dispatch, monkeypatch):
    f = published_dispatch(historical=True)
    original = Path.open
    snapshots = []

    def fail_second_file(path, mode="r", *args, **kwargs):
        if mode == "xb" and any(part.startswith("agy-translation-source-") for part in path.parts):
            snapshots.extend(parent for parent in path.parents if parent.name.startswith("agy-translation-source-"))
            if len(snapshots) == 2:
                raise OSError("離線模擬投影寫入失敗")
        return original(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_second_file)
    assert f.dispatch()["status"] == "failed"
    assert snapshots and all(not path.exists() for path in snapshots)
    assert not f.calls
