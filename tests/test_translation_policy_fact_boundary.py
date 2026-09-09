"""本地文章 facts 投影回歸；不代表 normalized 四 consumer 已接通。"""
from __future__ import annotations

import copy
import json

import pytest

from scripts import agy_multilingual_pipeline as m
from test_agy_source_authority_contract import new_brief
from test_agy_multilingual_pipeline import external_locale_plan, translation_candidate


def visible_fields(source):
    fields = [(key, source[key]) for key in ("title", "description", "answer")]
    fields.extend((f"tags[{i}]", text) for i, text in enumerate(source["tags"]))
    fields.extend((f"faq[{i}].{key}", item[key]) for i, item in enumerate(source["faq"]) for key in ("question", "answer"))
    for i, section in enumerate(source["bodySections"]):
        fields.append((f"bodySections[{i}].heading", section["heading"]))
        fields.extend((f"bodySections[{i}].paragraphs[{j}]", text) for j, text in enumerate(section["paragraphs"]))
    return fields


@pytest.mark.parametrize("locale", ["en", "ja", "ko"])
@pytest.mark.parametrize("policy_part", ["global_policy", "article_policy"])
def test_policy_stays_in_source_but_outside_article_facts(locale, policy_part):
    brief = new_brief(locale)
    source = brief["articles"][0]["source"]
    boundary = "  不得據此診斷疾病或自行停藥；若症狀持續，請就醫。\n"
    source["bodySections"][0]["paragraphs"].extend([boundary, source["answer"]])
    brief["articles"][0]["source_sha256"] = m.source_sha256(source)
    original = copy.deepcopy(brief)
    expected = dict(visible_fields(source))
    assert dict(m._source_text_fields(source)) == expected
    package = m._source_fact_package(brief)["articles"][0]
    facts = package["facts"]
    assert {fact["field_path"]: fact["text"] for fact in facts} == expected
    assert all(not fact["field_path"].startswith("publication_policy.") for fact in facts)
    assert any(fact["text"] == boundary and fact["safety_boundary"] for fact in facts)
    repeated = [fact for fact in facts if fact["text"] == source["answer"]]
    assert len(repeated) == 2
    assert len({fact["fact_id"] for fact in repeated}) == len(repeated)
    assert package["source"] == source

    changed = copy.deepcopy(brief)
    changed_source = changed["articles"][0]["source"]
    policy = changed_source["publication_policy"]
    marker = "本地政策快照變動測試"
    if policy_part == "global_policy":
        policy["global_policy"]["levels"]["required"] += marker
    else:
        policy["article_policy"]["evidence"]["disclosure"] += marker
    changed["articles"][0]["source_sha256"] = m.source_sha256(changed_source)
    m.validate_source_contract(changed_source)
    changed_package = m._source_fact_package(changed)["articles"][0]
    assert changed_package["facts"] == facts
    assert changed_package["source_sha256"] != package["source_sha256"]
    assert changed_package["source"] == changed_source

    external = external_locale_plan(changed)
    plan = m._hydrate_locale_plan(changed, external, generation=1, prior_plan=None, rebuild_by_slot={"article-01": False})
    mappings = plan["articles"][0]["coverage_mapping"]
    assert len(mappings) == len(expected)
    assert {item["source_fact_id"] for item in mappings} == {fact["fact_id"] for fact in facts}
    broken = copy.deepcopy(plan)
    broken["articles"][0]["coverage_mapping"].pop()
    with pytest.raises(ValueError, match="coverage"):
        m.validate_locale_plan(changed, broken)

    refs = m._request_local_source_ref_maps(changed, plan)
    expected_provider_source = copy.deepcopy(changed_source)
    effective_global = expected_provider_source["publication_policy"]["global_policy"]
    effective_global.pop("presentation_constraints")
    effective_global["writing_contract"].pop("section_flow")
    assert m._source_fact_package_for_prompt(changed, refs)["articles"][0]["source"] == expected_provider_source
    assert m._public_brief(changed)["articles"][0]["source"] == expected_provider_source
    assert m._public_brief(changed)["articles"][0]["source_sha256"] == changed["articles"][0]["source_sha256"]
    prompts = [
        m._plan_prompt(changed, generation=1, prior_plan=None, findings=[], rebuild_by_slot={"article-01": False}),
        m._article_prompt(changed, plan, []),
        m._reviewer_prompt(changed, translation_candidate(locale), []),
    ]
    for prompt in prompts:
        assert marker in prompt
        assert '"global_policy"' in prompt and '"article_policy"' in prompt
        assert json.dumps(boundary, ensure_ascii=False) in prompt
    assert brief == original
