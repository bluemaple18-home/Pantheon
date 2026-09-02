from __future__ import annotations

import hashlib
import json
import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import agy_gemini_coordinator as coordinator
from scripts import agy_gemini_runner as runner
from scripts import agy_seo_copy_pipeline as pipeline
from scripts import pantheon_content_runtime_manifest as runtime_manifest
from scripts.agy_gemini_coordinator import build_campaign_dry_run_workset, cycle_once, read_run_state, register_run, seed_legacy_rewrite_runs, seed_new_matrix_runs
from scripts.agy_gemini_outbox import ExternalJobPending, consume_external_response, create_external_request


def _article_brief_v2(run_id: str, article_id: str) -> dict[str, object]:
    return {
        "version": "ArticleBriefV2", "run_id": run_id,
        "article_identity": {"id": article_id, "canonical_path": f"/{article_id.lower()}/"},
        "reader_question": "這個概念應如何用在選擇上？", "target_reader": "正在比較選項的讀者",
        "search_intent": "informational", "thesis": "先查證事實，再判斷適用性。",
        "reader_outcome": "讀者能列出下一步。", "scope": "一般資訊整理",
        "anti_goals": ["不替讀者決定"], "evidence_policy": "cite-verifiable-claims", "risk_class": "medium",
    }


def _campaign_item(source_kind: str, article_id: str, campaign_version: str = "apf-002-v1") -> dict[str, str]:
    lane = "new" if source_kind == "matrix" else "rewrite"
    return {
        "source_kind": source_kind, "article_id": article_id, "locale": "zh-TW",
        "campaign_version": campaign_version,
        "work_id": coordinator._campaign_work_id(source_kind, article_id, "zh-TW", campaign_version),
        "lane": lane, "reason": "fixture",
    }


def _publication_policy(*, canonical: str, change_type: str) -> dict[str, object]:
    identity = coordinator.pipeline.load_article_publication_policy()["identity"]
    return {
        "policyVersion": coordinator.pipeline.publication_policy_version(),
        "canonical": canonical,
        "author": {"name": identity["author_name"], "url": identity["author_url"], "id": identity["author_id"]},
        "editorialResponsibility": identity["editorial_responsibility"],
        "evidence": {"mode": "cultural_reflection", "sources": [], "disclosure": "本文屬文化脈絡與反思整理，不主張可驗證的預測結果。"},
        "published": "2026-07-23", "modified": "2026-07-23", "changeType": change_type,
    }


def _long_paragraph(seed: str) -> str:
    return (seed + "再核對一項具體資料，避免把通用描述當成個人結論。" * 8)[:108]


def _valid_campaign_candidate(brief: dict[str, object]) -> dict[str, object]:
    article_id = str(brief["article_identity"]["id"])
    run_id = str(brief["run_id"])
    keyword = "測試關鍵字" if article_id.startswith("NEW") else "舊文測試"
    paragraphs = [_long_paragraph(f"{keyword}在第{index + 1}個工作場景中，不能代替個人判斷，先整理事實、限制與可行選項。") for index in range(15)]
    if article_id.startswith("NEW"):
        article = {
            "id": article_id, "section": "mbti", "product": "personality", "slug": article_id.lower(),
            "serial": "personality-9999", "urlSlug": f"{article_id.lower()}-9999", "primaryKeyword": "測試關鍵字",
            "secondaryKeywords": ["具體場景", "通用觀察"], "title": "測試關鍵字是什麼？用生活場景理解限制與選擇",
            "description": "測試關鍵字適合整理具體情境、可觀察行動與使用限制；本文只提供通用理解，不替個人下結論，也不承諾任何結果，仍需回到現況判斷與實際資料再做選擇。",
            "answer": "測試關鍵字提供通用觀察，不能替個人下結論。", "tags": ["AEO", "GEO", "Pantheon", "SEO", "公開文章", "繁體中文", "通用知識", "人格", "自我理解"],
            "published": "2026-07-23", "updated": "2026-07-23",
            "faq": [{"question": "能直接判定結果嗎？", "answer": "不能，仍要回到實際情境與行動。"}, {"question": "應該先看什麼？", "answer": "先分開記錄事實、推測與期待。"}, {"question": "什麼時候不適用？", "answer": "需要專業判斷時不應只靠這篇文章。"}],
            "bodySections": [{"heading": f"測試關鍵字的觀察角度 {index + 1}", "paragraphs": paragraphs[index * 3 : index * 3 + 3]} for index in range(5)],
            "publicationPolicy": _publication_policy(canonical=f"https://www.mysticpantheon.com/articles/personality/{article_id.lower()}-9999", change_type="created"),
        }
        return {"schema_version": 1, "run_id": run_id, "mode": "create", "articles": [article]}
    scenes = ["工作會議", "轉職面試", "家人聚會", "收入盤點", "伴侶溝通"]
    rewrite_paragraphs = [
        f"舊文測試在{scenes[index // 3]}的第{index % 3 + 1}次情境裡，先記錄可確認的事實，再列出兩個選項並比較差異；不能預先承諾結果，仍要寫下下一步、詢問相關的人並回顧時間，再核對可用資源與設定期限，避免只憑一時感受做決定。"
        for index in range(15)
    ]
    body_sections = [{"heading": f"具體判讀角度 {index + 1}", "paragraphs": rewrite_paragraphs[index * 3 : index * 3 + 3]} for index in range(5)]
    article = {
        "article_id": article_id,
        "identity": {"id": article_id, "product": "astrology", "category": "astrology", "serial": "astrology-0001", "slug": article_id.lower(), "primaryKeyword": "舊文測試", "title": "舊文測試標題"},
        "current_body_sha256": coordinator.pipeline.body_sha256([{"heading": "舊內容", "paragraphs": [_long_paragraph("舊文原始內容。")] }]),
        "bodySections": body_sections,
        "publicationPolicy": _publication_policy(canonical=f"https://www.mysticpantheon.com/articles/astrology/{article_id.lower()}", change_type="substantive_rewrite"),
    }
    return {"schema_version": 1, "run_id": run_id, "mode": "rewrite_existing_body", "articles": [article]}


def _clean_review(brief: dict[str, object], candidate: dict[str, object]) -> dict[str, object]:
    article = candidate["articles"][0]
    article_id = str(article.get("id", article.get("article_id")))
    return {"schema_version": 1, "run_id": brief["run_id"], "articles": [{"article_id": article_id, "candidate_sha256": coordinator.pipeline.article_sha256(article), "verdict": "APPROVE", "hard_failure": False, "findings": []}]}


def _publisher_rewrite_brief(candidate: dict[str, object]) -> dict[str, object]:
    article = candidate["articles"][0]
    current_body = [{"heading": "舊內容", "paragraphs": [_long_paragraph("舊文原始內容。")]}]
    identity = article["identity"]
    return {
        "schema_version": 1,
        "run_id": candidate["run_id"],
        "mode": "rewrite_existing_body",
        "articles": [{
            "slot": "article-01",
            "article_id": article["article_id"],
            "identity": identity,
            "immutable_fields": {
                "id": identity["id"], "product": identity["product"], "slug": identity["slug"],
                "serial": identity["serial"], "title": identity["title"], "description": "舊文描述",
                "answer": "舊文回答", "faq": [{"question": "要直接下結論嗎？", "answer": "不要，先核對實際情況。"}],
                "tags": ["占星", "自我理解"], "published": "2026-07-23",
                "updated": "2026-07-23", "urlSlug": identity["slug"], "primaryKeyword": identity["primaryKeyword"],
            },
            "current_body": current_body,
            "current_body_sha256": coordinator.pipeline.body_sha256(current_body),
            "rewrite_brief": ["保留原本搜尋意圖與主題邊界，不承諾任何結果。"],
            "source_file": "app/web/static/article-meta.js",
            "body_source": "buildArticleContent",
        }],
    }


def test_campaign_editorial_workset_executes_new_and_rewrite_with_real_contracts(tmp_path: Path) -> None:
    calls = {"brief": 0, "writer": 0, "reviewer": 0}
    workset = {"schema_version": 1, "campaign_version": "apf-002-v1", "lanes": ["new", "rewrite"], "items": [_campaign_item("matrix", "NEW-001"), _campaign_item("legacy", "LEGACY-001")], "summary": {}}

    def make_brief(item: dict[str, object]) -> dict[str, object]:
        calls["brief"] += 1
        return _article_brief_v2(f"{item['lane']}-run-001", str(item["article_id"]))

    def write_candidate(brief: dict[str, object]) -> dict[str, object]:
        calls["writer"] += 1
        return _valid_campaign_candidate(brief)

    def write_review(brief: dict[str, object], candidate: dict[str, object]) -> dict[str, object]:
        calls["reviewer"] += 1
        return _clean_review(brief, candidate)

    first = coordinator.execute_campaign_editorial_workset(workset, tmp_path / "runs", brief_factory=make_brief, writer=write_candidate, reviewer=write_review)
    second = coordinator.execute_campaign_editorial_workset(workset, tmp_path / "runs", brief_factory=make_brief, writer=write_candidate, reviewer=write_review)

    assert first["work_ids"] == second["work_ids"] == [item["work_id"] for item in workset["items"]]
    assert calls == {"brief": 2, "writer": 2, "reviewer": 2}


def test_campaign_editorial_workset_replays_both_lanes_through_real_publisher_collectors(tmp_path: Path) -> None:
    workset = {"schema_version": 1, "campaign_version": "apf-002-v1", "lanes": ["new", "rewrite"], "items": [_campaign_item("matrix", "NEW-001"), _campaign_item("legacy", "LEGACY-001")], "summary": {}}
    result = coordinator.execute_campaign_editorial_workset(
        workset,
        tmp_path / "runs",
        brief_factory=lambda item: _article_brief_v2(f"{item['lane']}-run-001", str(item["article_id"])),
        writer=_valid_campaign_candidate,
        reviewer=_clean_review,
    )
    rewrite = next(run for run in result["runs"] if run["lane"] == "rewrite")
    state_root = tmp_path / "publisher-state"
    before = {str(path.relative_to(tmp_path)): path.read_bytes() for path in sorted(tmp_path.rglob("*")) if path.is_file()}

    replay = coordinator.replay_campaign_editorial_workset_through_publisher(
        result,
        tmp_path / "queue",
        state_root,
        rewrite_briefs={rewrite["run_id"]: _publisher_rewrite_brief(rewrite["candidate"])},
    )

    after = {str(path.relative_to(tmp_path)): path.read_bytes() for path in sorted(tmp_path.rglob("*")) if path.is_file()}
    assert replay == {"status": "dry-run", "published": 0, "new_run_id": "new-run-001", "rewrite_run_id": "rewrite-run-001"}
    assert not (state_root / "ledger.json").exists()
    assert all(path.startswith(("runs/", "queue/")) for path in set(after) - set(before))


@pytest.mark.parametrize("field, expected", [("candidate_sha256", "campaign candidate SHA drift"), ("review_sha256", "campaign review SHA drift")])
def test_campaign_editorial_publisher_replay_fails_closed_for_artifact_drift(
    tmp_path: Path, field: str, expected: str,
) -> None:
    workset = {"schema_version": 1, "campaign_version": "apf-002-v1", "lanes": ["new", "rewrite"], "items": [_campaign_item("matrix", "NEW-001"), _campaign_item("legacy", "LEGACY-001")], "summary": {}}
    result = coordinator.execute_campaign_editorial_workset(
        workset,
        tmp_path / "runs",
        brief_factory=lambda item: _article_brief_v2(f"{item['lane']}-run-001", str(item["article_id"])),
        writer=_valid_campaign_candidate,
        reviewer=_clean_review,
    )
    result["runs"][0][field] = "0" * 64
    rewrite = next(run for run in result["runs"] if run["lane"] == "rewrite")

    with pytest.raises(ValueError, match=expected):
        coordinator.replay_campaign_editorial_workset_through_publisher(
            result,
            tmp_path / "queue",
            tmp_path / "publisher-state",
            rewrite_briefs={rewrite["run_id"]: _publisher_rewrite_brief(rewrite["candidate"])},
        )
    assert not (tmp_path / "queue").exists()


def test_campaign_editorial_publisher_replay_fails_closed_for_identity_drift(tmp_path: Path) -> None:
    workset = {"schema_version": 1, "campaign_version": "apf-002-v1", "lanes": ["new", "rewrite"], "items": [_campaign_item("matrix", "NEW-001"), _campaign_item("legacy", "LEGACY-001")], "summary": {}}
    result = coordinator.execute_campaign_editorial_workset(
        workset,
        tmp_path / "runs",
        brief_factory=lambda item: _article_brief_v2(f"{item['lane']}-run-001", str(item["article_id"])),
        writer=_valid_campaign_candidate,
        reviewer=_clean_review,
    )
    result["runs"][0]["article_identity"] = {"id": "IDENTITY-DRIFT"}
    rewrite = next(run for run in result["runs"] if run["lane"] == "rewrite")

    with pytest.raises(ValueError, match="campaign article identity drift"):
        coordinator.replay_campaign_editorial_workset_through_publisher(
            result,
            tmp_path / "queue",
            tmp_path / "publisher-state",
            rewrite_briefs={rewrite["run_id"]: _publisher_rewrite_brief(rewrite["candidate"])},
        )
    assert not (tmp_path / "queue").exists()


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("candidate_sha", "campaign candidate SHA drift"),
        ("identity", "campaign article identity drift"),
        ("work_id", "campaign work identity drift"),
        ("missing_rewrite_brief", "rewrite publisher brief is required"),
    ],
)
def test_campaign_editorial_publisher_replay_preflights_every_lane_before_writing(
    tmp_path: Path, mutation: str, expected: str,
) -> None:
    workset = {"schema_version": 1, "campaign_version": "apf-002-v1", "lanes": ["new", "rewrite"], "items": [_campaign_item("matrix", "NEW-001"), _campaign_item("legacy", "LEGACY-001")], "summary": {}}
    result = coordinator.execute_campaign_editorial_workset(
        workset,
        tmp_path / "runs",
        brief_factory=lambda item: _article_brief_v2(f"{item['lane']}-run-001", str(item["article_id"])),
        writer=_valid_campaign_candidate,
        reviewer=_clean_review,
    )
    rewrite = next(run for run in result["runs"] if run["lane"] == "rewrite")
    briefs = {rewrite["run_id"]: _publisher_rewrite_brief(rewrite["candidate"])}
    if mutation == "candidate_sha":
        rewrite["candidate_sha256"] = "0" * 64
    elif mutation == "identity":
        rewrite["article_identity"] = {"id": "IDENTITY-DRIFT"}
    elif mutation == "work_id":
        rewrite["work_id"] = "apf-work-drift"
    else:
        briefs = {}

    with pytest.raises(ValueError, match=expected):
        coordinator.replay_campaign_editorial_workset_through_publisher(
            result,
            tmp_path / "queue",
            tmp_path / "publisher-state",
            rewrite_briefs=briefs,
        )
    assert not (tmp_path / "queue").exists()
    assert all(not (Path(run["run_dir"]) / "publisher-dry-run").exists() for run in result["runs"])


def _campaign_translation_fixture(
    tmp_path: Path,
) -> tuple[dict[str, object], dict[str, dict[str, object]], list[dict[str, object]]]:
    workset = {
        "schema_version": 1,
        "campaign_version": "apf-003-v1",
        "lanes": ["new", "rewrite"],
        "items": [
            _campaign_item("matrix", "NEW-001", "apf-003-v1"),
            _campaign_item("legacy", "LEGACY-001", "apf-003-v1"),
        ],
        "summary": {},
    }
    result = coordinator.execute_campaign_editorial_workset(
        workset,
        tmp_path / "campaign-runs",
        brief_factory=lambda item: _article_brief_v2(
            f"{item['lane']}-run-003",
            str(item["article_id"]),
        ),
        writer=_valid_campaign_candidate,
        reviewer=_clean_review,
    )
    rewrite = next(run for run in result["runs"] if run["lane"] == "rewrite")
    rewrite_briefs = {
        str(rewrite["run_id"]): _publisher_rewrite_brief(rewrite["candidate"])
    }
    prepared, _by_lane = coordinator._preflight_campaign_editorial_handoffs(
        result,
        rewrite_briefs=rewrite_briefs,
    )
    briefs = [
        coordinator._campaign_translation_brief(
            item,
            coordinator._campaign_translation_source(item),
            "ja",
        )
        for item in prepared
    ]
    return result, rewrite_briefs, briefs


class _CampaignTranslationClient:
    writer_model = "writer-test"
    reviewer_model = "reviewer-test"

    def __init__(self, briefs: list[dict[str, object]]) -> None:
        self.briefs = briefs
        self.index = 0
        self.calls: list[str] = []
        self.outline: list[str] = []

    def generate_json(
        self,
        role: str,
        _prompt: str,
        schema: dict[str, object],
    ) -> dict[str, object]:
        self.calls.append(role)
        brief = self.briefs[self.index]
        if "native_search_intent" in json.dumps(schema):
            target = coordinator.multilingual._source_fact_package(brief)["articles"][0]
            self.outline = [
                "判断の前に確認する情報",
                "事実と推測を分ける方法",
                "選択肢を比べる手順",
                "結論を急がないための限界",
            ]
            return {
                "articles": [{
                    "slot": "article-01",
                    "locale": "ja",
                    "source_sha256": brief["articles"][0]["source_sha256"],
                    "native_search_intent": "状況を整理して判断する方法と限界を知りたい",
                    "native_query_phrasings": ["状況を整理する方法", "判断するときの注意点"],
                    "article_angle": "事実を確認しながら選択肢を比較する順序と限界を説明する",
                    "ordered_h2_outline": self.outline,
                    "coverage_mapping": [
                        {
                            "source_fact_id": fact["fact_id"],
                            "planned_h2_slot": f"h2-{index % 4 + 1}",
                            "coverage_note": "この事実と制限を該当する節で説明する",
                            "safety_boundary": fact["safety_boundary"],
                        }
                        for index, fact in enumerate(target["facts"])
                    ],
                    "source_structure_not_copied": [
                        section["heading"]
                        for section in brief["articles"][0]["source"]["bodySections"]
                    ],
                    "rebuild_outline": False,
                }]
            }
        if role == "writer":
            return {
                "articles": [{
                    "slot": "article-01",
                    "title": "状況を整理して選択肢を比べるには？",
                    "description": "確認できる事実と推測を分け、複数の選択肢を比較する手順を説明します。結果を保証したり、本人に代わって判断したりするものではありません。",
                    "answer": "まず事実と制限を確認し、その後で実行できる選択肢を比べます。",
                    "tags": ["状況整理", "選択肢", "自己理解"],
                    "faq": [{
                        "question": "すぐに一つの結論を選ぶべきですか？",
                        "answer": "いいえ。確認できる情報と制限を整理してから比較します。",
                    }],
                    "bodySections": [
                        {
                            "heading": heading,
                            "paragraphs": [
                                paragraph,
                                "この手順だけで結果を保証することはできず、実際の状況を確認する必要があります。",
                            ] if index == 0 else [paragraph],
                        }
                        for index, (heading, paragraph) in enumerate(zip(
                            self.outline,
                            [
                                "最初に確認できる情報、現在の制限、まだ不明な点を分けて書き出します。",
                                "見聞きした事実と自分の推測を別々に記録し、混同しないようにします。",
                                "実行できる選択肢を二つ以上並べ、それぞれの違いと次の一歩を確認します。",
                                "一般的な整理方法は個別の判断を代行しないため、必要なら関係者や専門家に確認します。",
                            ],
                        ))
                    ],
                }]
            }
        self.index += 1
        return {
            "articles": [{
                "slot": "article-01",
                "verdict": "APPROVE",
                "findings": [],
            }]
        }


def _tree_bytes(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_campaign_translation_runs_new_and_rewrite_through_real_vertical_chain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, rewrite_briefs, briefs = _campaign_translation_fixture(tmp_path)
    client = _CampaignTranslationClient(briefs)
    queue_root = tmp_path / "translation-queue"
    state_root = tmp_path / "publisher-state"
    original_loader = coordinator.multilingual.load_source_article
    original_enqueue = coordinator.multilingual.enqueue_article_translations
    enqueue_lanes: list[str] = []

    def tracking_enqueue_article_translations(
        repo_root: Path,
        queue: Path,
        *,
        source_run_id: str,
        article_id: str,
        locales: list[str] | None = None,
        lane: str,
        source_loader=coordinator.multilingual.load_source_article,
    ) -> list[dict[str, str]]:
        enqueue_lanes.append(lane)
        return original_enqueue(
            repo_root,
            queue,
            source_run_id=source_run_id,
            article_id=article_id,
            locales=locales,
            lane=lane,
            source_loader=source_loader,
        )

    monkeypatch.setattr(
        coordinator.multilingual,
        "enqueue_article_translations",
        tracking_enqueue_article_translations,
    )

    first = coordinator.replay_campaign_editorial_workset_through_translation(
        Path(__file__).resolve().parents[1],
        result,
        queue_root,
        state_root,
        client,
        rewrite_briefs=rewrite_briefs,
        locale="ja",
        max_repairs=0,
    )
    after_first = _tree_bytes(queue_root)
    second = coordinator.replay_campaign_editorial_workset_through_translation(
        Path(__file__).resolve().parents[1],
        result,
        queue_root,
        state_root,
        client,
        rewrite_briefs=rewrite_briefs,
        locale="ja",
        max_repairs=0,
    )

    assert first == second
    assert first["status"] == "dry-run"
    assert first["published"] == 0
    assert first["locale"] == "ja"
    assert {item["lane"] for item in first["translation_runs"]} == {
        "i18n-new",
        "i18n-rewrite",
    }
    assert enqueue_lanes == ["i18n-new", "i18n-rewrite", "i18n-new", "i18n-rewrite"]
    assert len({item["translation_run_id"] for item in first["translation_runs"]}) == 2
    assert all(
        item["translation_article_id"]
        == f"{item['source_article_id']}:ja"
        for item in first["translation_runs"]
    )
    assert len(client.calls) == 6
    assert _tree_bytes(queue_root) == after_first
    assert len(list((queue_root / "runs").glob("*.json"))) == 2
    assert not (state_root / "ledger.json").exists()
    assert coordinator.multilingual.load_source_article is original_loader


def test_private_campaign_e2e_composes_four_lanes_without_publishing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workset = {
        "schema_version": 1,
        "campaign_version": "checkpoint-a-v1",
        "lanes": ["new", "rewrite", "i18n-new", "i18n-rewrite"],
        "items": [
            _campaign_item("matrix", "NEW-001", "checkpoint-a-v1"),
            _campaign_item("legacy", "LEGACY-001", "checkpoint-a-v1"),
            {
                **_campaign_item("matrix", "NEW-001", "checkpoint-a-v1"),
                "locale": "ja",
                "work_id": coordinator._campaign_work_id("matrix", "NEW-001", "ja", "checkpoint-a-v1"),
                "lane": "i18n-new",
            },
            {
                **_campaign_item("legacy", "LEGACY-001", "checkpoint-a-v1"),
                "locale": "ja",
                "work_id": coordinator._campaign_work_id("legacy", "LEGACY-001", "ja", "checkpoint-a-v1"),
                "lane": "i18n-rewrite",
            },
        ],
        "summary": {},
    }
    briefs = [
        coordinator._campaign_translation_brief(
            {"run_id": f"{lane}-run-001", "article_id": article_id, "lane": lane},
            coordinator._campaign_translation_source({
                "candidate": _valid_campaign_candidate(_article_brief_v2(f"{lane}-run-001", article_id)),
                "article_id": article_id,
                "lane": lane,
                "brief": _publisher_rewrite_brief(_valid_campaign_candidate(_article_brief_v2(f"{lane}-run-001", article_id))) if lane == "rewrite" else {"articles": []},
            }),
            "ja",
        )
        for lane, article_id in (("new", "NEW-001"), ("rewrite", "LEGACY-001"))
    ]
    client = _CampaignTranslationClient(briefs)
    builder_calls: list[tuple[Path, Path, Path, str, tuple[str, ...]]] = []

    def build_workset(
        repo_root: Path,
        queue_root: Path,
        state_root: Path,
        *,
        campaign_version: str,
        locales: tuple[str, ...],
    ) -> dict[str, object]:
        builder_calls.append((repo_root, queue_root, state_root, campaign_version, locales))
        return workset

    monkeypatch.setattr(coordinator, "build_campaign_dry_run_workset", build_workset)

    first = coordinator.execute_private_campaign_e2e(
        Path(__file__).resolve().parents[1],
        tmp_path / "runs",
        tmp_path / "queue",
        tmp_path / "publisher-state",
        client,
        campaign_version="checkpoint-a-v1",
        brief_factory=lambda item: _article_brief_v2(f"{item['lane']}-run-001", str(item["article_id"])),
        writer=_valid_campaign_candidate,
        reviewer=_clean_review,
        rewrite_brief_factory=_publisher_rewrite_brief,
        locale="ja",
        max_repairs=0,
    )

    assert first["status"] == "dry-run"
    assert first["published"] == 0
    assert first["lanes"] == ["new", "rewrite", "i18n-new", "i18n-rewrite"]
    assert len(client.calls) == 6
    assert not (tmp_path / "publisher-state" / "ledger.json").exists()

    second = coordinator.execute_private_campaign_e2e(
        Path(__file__).resolve().parents[1],
        tmp_path / "runs",
        tmp_path / "queue",
        tmp_path / "publisher-state",
        client,
        campaign_version="checkpoint-a-v1",
        brief_factory=lambda item: _article_brief_v2(f"{item['lane']}-run-001", str(item["article_id"])),
        writer=_valid_campaign_candidate,
        reviewer=_clean_review,
        rewrite_brief_factory=_publisher_rewrite_brief,
        locale="ja",
        max_repairs=0,
    )
    assert second == first
    assert len(client.calls) == 6
    assert [call[3:] for call in builder_calls] == [
        ("checkpoint-a-v1", ("ja",)),
        ("checkpoint-a-v1", ("ja",)),
    ]


def test_private_campaign_e2e_rejects_capacity_and_rolls_back_translation_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    workset = {
        "schema_version": 1,
        "campaign_version": "checkpoint-a-v1",
        "lanes": ["new", "rewrite", "i18n-new", "i18n-rewrite"],
        "items": [
            _campaign_item("matrix", "NEW-001", "checkpoint-a-v1"),
            _campaign_item("legacy", "LEGACY-001", "checkpoint-a-v1"),
            {**_campaign_item("matrix", "NEW-001", "checkpoint-a-v1"), "locale": "ja", "work_id": coordinator._campaign_work_id("matrix", "NEW-001", "ja", "checkpoint-a-v1"), "lane": "i18n-new"},
            {**_campaign_item("legacy", "LEGACY-001", "checkpoint-a-v1"), "locale": "ja", "work_id": coordinator._campaign_work_id("legacy", "LEGACY-001", "ja", "checkpoint-a-v1"), "lane": "i18n-rewrite"},
        ],
        "summary": {},
    }
    editorial_over_capacity = {
        **workset,
        "items": [*workset["items"], _campaign_item("matrix", "NEW-002", "checkpoint-a-v1")],
    }
    with pytest.raises(ValueError, match="capacity exceeds two editorial"):
        coordinator._private_campaign_e2e_workset(editorial_over_capacity, "ja")

    over_capacity = {**workset, "items": [*workset["items"], dict(workset["items"][2])]}
    monkeypatch.setattr(coordinator, "build_campaign_dry_run_workset", lambda *_args, **_kwargs: over_capacity)
    with pytest.raises(ValueError, match="invalid translation selection"):
        coordinator.execute_private_campaign_e2e(
            Path(__file__).resolve().parents[1], tmp_path / "runs", tmp_path / "queue", tmp_path / "state", object(),
            campaign_version="checkpoint-a-v1",
            brief_factory=lambda item: _article_brief_v2(f"{item['lane']}-run-001", str(item["article_id"])), writer=_valid_campaign_candidate,
            reviewer=_clean_review, rewrite_brief_factory=_publisher_rewrite_brief,
        )
    assert not (tmp_path / "runs").exists()
    assert not (tmp_path / "queue").exists()

    def fail_translation(*_args: object, **_kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        raise ValueError("injected translation failure")

    monkeypatch.setattr(coordinator.multilingual, "run_writer_reviewer", fail_translation)
    monkeypatch.setattr(coordinator, "build_campaign_dry_run_workset", lambda *_args, **_kwargs: workset)

    with pytest.raises(ValueError, match="injected translation failure"):
        coordinator.execute_private_campaign_e2e(
            Path(__file__).resolve().parents[1], tmp_path / "failed-runs", tmp_path / "failed-queue", tmp_path / "failed-state", object(),
            campaign_version="checkpoint-a-v1",
            brief_factory=lambda item: _article_brief_v2(f"{item['lane']}-run-001", str(item["article_id"])), writer=_valid_campaign_candidate,
            reviewer=_clean_review, rewrite_brief_factory=_publisher_rewrite_brief,
        )
    assert not (tmp_path / "failed-runs").exists()
    assert not (tmp_path / "failed-queue").exists()
    assert not (tmp_path / "failed-state").exists()


def test_private_campaign_e2e_resumes_seeded_partial_state_without_repeating_completed_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workset = {
        "schema_version": 1,
        "campaign_version": "checkpoint-a-v1",
        "lanes": ["new", "rewrite", "i18n-new", "i18n-rewrite"],
        "items": [
            _campaign_item("matrix", "NEW-001", "checkpoint-a-v1"),
            _campaign_item("legacy", "LEGACY-001", "checkpoint-a-v1"),
            {**_campaign_item("matrix", "NEW-001", "checkpoint-a-v1"), "locale": "ja", "work_id": coordinator._campaign_work_id("matrix", "NEW-001", "ja", "checkpoint-a-v1"), "lane": "i18n-new"},
            {**_campaign_item("legacy", "LEGACY-001", "checkpoint-a-v1"), "locale": "ja", "work_id": coordinator._campaign_work_id("legacy", "LEGACY-001", "ja", "checkpoint-a-v1"), "lane": "i18n-rewrite"},
        ],
        "summary": {},
    }
    briefs = [
        coordinator._campaign_translation_brief(
            {"run_id": f"{lane}-run-001", "article_id": article_id, "lane": lane},
            coordinator._campaign_translation_source({
                "candidate": _valid_campaign_candidate(_article_brief_v2(f"{lane}-run-001", article_id)),
                "article_id": article_id,
                "lane": lane,
                "brief": _publisher_rewrite_brief(_valid_campaign_candidate(_article_brief_v2(f"{lane}-run-001", article_id))) if lane == "rewrite" else {"articles": []},
            }),
            "ja",
        )
        for lane, article_id in (("new", "NEW-001"), ("rewrite", "LEGACY-001"))
    ]
    client = _CampaignTranslationClient(briefs)
    calls = {"writer": 0, "reviewer": 0}

    def writer(brief: dict[str, object]) -> dict[str, object]:
        calls["writer"] += 1
        return _valid_campaign_candidate(brief)

    def reviewer(brief: dict[str, object], candidate: dict[str, object]) -> dict[str, object]:
        calls["reviewer"] += 1
        return _clean_review(brief, candidate)

    monkeypatch.setattr(coordinator, "build_campaign_dry_run_workset", lambda *_args, **_kwargs: workset)
    arguments = (
        Path(__file__).resolve().parents[1],
        tmp_path / "runs",
        tmp_path / "queue",
        tmp_path / "publisher-state",
        client,
    )
    options = {
        "campaign_version": "checkpoint-a-v1",
        "brief_factory": lambda item: _article_brief_v2(f"{item['lane']}-run-001", str(item["article_id"])),
        "writer": writer,
        "reviewer": reviewer,
        "rewrite_brief_factory": _publisher_rewrite_brief,
        "locale": "ja",
        "max_repairs": 0,
    }
    first = coordinator.execute_private_campaign_e2e(*arguments, **options)
    rewrite = next(run for run in first["editorial_runs"] if run["lane"] == "rewrite")
    rewrite_dir = tmp_path / "runs" / rewrite["work_id"] / "editorial-vnext"
    for name in ("legacy-candidate.json", "legacy-review.json", "editorial-manifest-v1.json"):
        (rewrite_dir / name).unlink()

    second = coordinator.execute_private_campaign_e2e(*arguments, **options)

    assert calls == {"writer": 3, "reviewer": 3}
    assert len(client.calls) == 6
    assert second["lanes"] == ["new", "rewrite", "i18n-new", "i18n-rewrite"]
    assert second["published"] == 0
    assert all((rewrite_dir / name).is_file() for name in ("legacy-candidate.json", "legacy-review.json", "editorial-manifest-v1.json"))
    states = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((tmp_path / "queue" / "runs").glob("*.json"))]
    run_ids = [str(state["run_id"]) for state in states]
    assert len(run_ids) == len(set(run_ids)) == 4


def _apf_004_item(
    source_kind: str,
    article_id: str,
    locale: str,
    lane: str,
) -> dict[str, str]:
    campaign_version = "apf-001-v1"
    return {
        "source_kind": source_kind,
        "article_id": article_id,
        "locale": locale,
        "campaign_version": campaign_version,
        "work_id": coordinator._campaign_work_id(
            source_kind,
            article_id,
            locale,
            campaign_version,
        ),
        "lane": lane,
        "reason": "apf-004-confirmed-payload",
    }


def _apf_004_workset() -> dict[str, object]:
    return {
        "schema_version": 1,
        "campaign_version": "apf-001-v1",
        "lanes": ["new", "rewrite", "i18n-new", "i18n-rewrite"],
        "items": [
            _apf_004_item("matrix", "ASTRO-SCENARIO-BIG-THREE", "zh-TW", "new"),
            _apf_004_item("matrix", "ASTRO-SCENARIO-BIG-THREE", "ja", "i18n-new"),
            _apf_004_item("legacy", "ASC-AQUARIUS", "zh-TW", "rewrite"),
            _apf_004_item("legacy", "ASC-AQUARIUS", "ja", "i18n-rewrite"),
        ],
        "summary": {"fixture": "apf-004"},
    }


def _apf_004_exact_tuples(workset: dict[str, object] | None = None) -> list[dict[str, str]]:
    source = workset or _apf_004_workset()
    return [
        {
            "lane": str(item["lane"]),
            "work_id": str(item["work_id"]),
            "article_id": str(item["article_id"]),
            "locale": str(item["locale"]),
        }
        for item in source["items"]
    ]


def _apf_004_digest(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _apf_004_kwargs(tmp_path: Path, workset: dict[str, object] | None = None) -> dict[str, object]:
    selected = workset or _apf_004_workset()
    return {
        "repo_root": Path(__file__).resolve().parents[1],
        "workset": selected,
        "exact_tuples": _apf_004_exact_tuples(selected),
        "run_root": tmp_path / "runs",
        "queue_root": tmp_path / "queue",
        "state_root": tmp_path / "publisher-state",
        "campaign_version": "apf-001-v1",
        "workset_sha256": _apf_004_digest(selected),
        "confirmed_payload_digest": "a" * 64,
        "activation_authorization_digest": "b" * 64,
        "runtime_identity_digest": "c" * 64,
        "actor_identity": "apf-004-synthetic-actor",
        "correlation_id": "apf-004-correlation-001",
        "max_runs": 1,
    }


def _apf_004_single_workset(lane: str = "new") -> dict[str, object]:
    if lane == "new":
        item = _apf_004_item("matrix", "ASTRO-SCENARIO-BIG-THREE", "zh-TW", "new")
    elif lane == "rewrite":
        item = _apf_004_item("legacy", "ASC-AQUARIUS", "zh-TW", "rewrite")
    else:
        item = _apf_004_item("matrix", "ASTRO-SCENARIO-BIG-THREE", "ja", lane)
    return {
        "schema_version": 1,
        "campaign_version": "apf-001-v1",
        "lanes": [lane],
        "items": [item],
        "summary": {"fixture": "apf-004-single"},
    }


def _apf_004_single_kwargs(tmp_path: Path, lane: str = "new") -> dict[str, object]:
    workset = _apf_004_single_workset(lane)
    return _apf_004_kwargs(tmp_path, workset)


def test_apf_004_single_create_only_adapter_plan_only_is_deterministic_and_zero_write(
    tmp_path: Path,
) -> None:
    kwargs = _apf_004_single_kwargs(tmp_path)
    before = _tree_bytes(tmp_path)

    first = coordinator.create_single_source_run_adapter(**kwargs, plan_only=True)
    second = coordinator.create_single_source_run_adapter(**kwargs, plan_only=True)

    assert first == second
    assert first["status"] == "planned"
    assert first["entrypoint"] == "scripts.agy_gemini_coordinator:create_single_source_run_adapter"
    assert first["campaign_version"] == "apf-001-v1"
    assert first["production_mutation"] is False
    assert [item["lane"] for item in first["runs"]] == ["new"]
    assert len(first["exact_run_ids"]) == 1
    assert list(first["dependency_graph"].values()) == [[]]
    assert len(first["expected_write_set"]) == 3
    assert _tree_bytes(tmp_path) == before


def test_apf_004_single_create_only_adapter_apply_is_idempotent_and_resume_safe(
    tmp_path: Path,
) -> None:
    kwargs = _apf_004_single_kwargs(tmp_path, "rewrite")

    first = coordinator.create_single_source_run_adapter(**kwargs, plan_only=False)
    second = coordinator.create_single_source_run_adapter(**kwargs, plan_only=False)
    Path(str(first["transaction_receipt"])).unlink()
    resumed = coordinator.create_single_source_run_adapter(**kwargs, plan_only=False)

    assert first["exact_run_ids"] == second["exact_run_ids"] == resumed["exact_run_ids"]
    assert first["created"] == {"registered": 1, "pending_dependencies": 0}
    assert second["created"] == {"registered": 0, "pending_dependencies": 0}
    assert resumed["created"] == {"registered": 0, "pending_dependencies": 0}
    assert Path(str(resumed["transaction_receipt"])).is_file()
    assert len(sorted((tmp_path / "queue" / "runs").glob("*.json"))) == 1
    assert not (tmp_path / "queue" / "translation-pending-dependencies").exists()


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("i18n_lane", "single-source create-only adapter requires a source lane"),
        ("multi_item", "single-source create-only adapter requires exactly one item"),
        ("multi_exact", "single-source create-only adapter requires exactly one exact tuple"),
        ("work_id", "exact work identity differs"),
        ("caller_run_id", "caller-supplied run identity"),
        ("max_runs", "max_runs=1"),
    ],
)
def test_apf_004_single_create_only_adapter_negative_fails_before_write(
    tmp_path: Path,
    mutation: str,
    expected: str,
) -> None:
    kwargs = _apf_004_single_kwargs(tmp_path)
    if mutation == "i18n_lane":
        kwargs = _apf_004_single_kwargs(tmp_path, "i18n-new")
    elif mutation == "multi_item":
        workset = _apf_004_workset()
        kwargs = _apf_004_kwargs(tmp_path, workset)
    elif mutation == "multi_exact":
        kwargs["exact_tuples"] = [
            *list(kwargs["exact_tuples"]),
            _apf_004_exact_tuples(_apf_004_single_workset("rewrite"))[0],
        ]
    elif mutation == "work_id":
        exact_tuples = list(kwargs["exact_tuples"])
        exact_tuples[0] = {**exact_tuples[0], "work_id": "apf-work-drift"}
        kwargs["exact_tuples"] = exact_tuples
    elif mutation == "caller_run_id":
        workset = _apf_004_single_workset()
        items = list(workset["items"])
        items[0] = {**dict(items[0]), "run_id": "caller-run-id"}
        workset = {**workset, "items": items}
        kwargs = _apf_004_kwargs(tmp_path, workset)
        kwargs["workset_sha256"] = _apf_004_digest(workset)
    else:
        kwargs["max_runs"] = 2

    with pytest.raises(ValueError, match=expected):
        coordinator.create_single_source_run_adapter(**kwargs, plan_only=False)

    assert _tree_bytes(tmp_path) == {}


def test_apf_004_single_create_only_adapter_rejects_root_overlap_and_state_collision(
    tmp_path: Path,
) -> None:
    overlap = _apf_004_single_kwargs(tmp_path / "overlap")
    overlap["state_root"] = overlap["queue_root"]
    with pytest.raises(ValueError, match="roots must not overlap"):
        coordinator.create_single_source_run_adapter(**overlap, plan_only=False)
    assert _tree_bytes(tmp_path / "overlap") == {}

    kwargs = _apf_004_single_kwargs(tmp_path / "collision")
    plan = coordinator.create_single_source_run_adapter(**kwargs, plan_only=True)
    first_run_id = plan["runs"][0]["run_id"]
    run_dir = kwargs["run_root"] / first_run_id
    run_dir.mkdir(parents=True)
    (run_dir / "brief.json").write_text(
        json.dumps({"schema_version": 1, "run_id": first_run_id, "mode": "create", "articles": [{"article_id": "DRIFT"}]}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="run identity collision"):
        coordinator.create_single_source_run_adapter(**kwargs, plan_only=False)


def test_apf_004_create_run_adapter_plan_only_is_deterministic_and_zero_write(
    tmp_path: Path,
) -> None:
    kwargs = _apf_004_kwargs(tmp_path)
    before = _tree_bytes(tmp_path)

    first = coordinator.create_campaign_run_adapter(
        **kwargs,
        plan_only=True,
    )
    second = coordinator.create_campaign_run_adapter(
        **kwargs,
        plan_only=True,
    )

    assert first == second
    assert first["status"] == "planned"
    assert first["campaign_version"] == "apf-001-v1"
    assert [item["lane"] for item in first["runs"]] == [
        "new",
        "rewrite",
        "i18n-new",
        "i18n-rewrite",
    ]
    assert len({item["run_id"] for item in first["runs"]}) == 4
    assert first["runs"][2]["run_id"] == coordinator.multilingual.translation_run_id(
        first["runs"][0]["run_id"],
        "ASTRO-SCENARIO-BIG-THREE",
        "ja",
    )
    assert first["runs"][3]["run_id"] == coordinator.multilingual.translation_run_id(
        first["runs"][1]["run_id"],
        "ASC-AQUARIUS",
        "ja",
    )
    assert _tree_bytes(tmp_path) == before


def test_apf_004_create_run_adapter_uses_unfiltered_matrix_authority(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(coordinator.pipeline, "build_matrix_backlog", lambda _: [])

    result = coordinator.create_campaign_run_adapter(
        **_apf_004_kwargs(tmp_path), plan_only=False
    )

    assert result["created"] == {"registered": 2, "pending_dependencies": 2}


def test_apf_004_create_run_adapter_apply_is_idempotent_and_resume_safe(
    tmp_path: Path,
) -> None:
    kwargs = _apf_004_kwargs(tmp_path)
    first = coordinator.create_campaign_run_adapter(**kwargs, plan_only=False)
    pending_root = tmp_path / "queue" / "translation-pending-dependencies"
    first_pending = sorted(pending_root.glob("*.json"))
    first_states = sorted((tmp_path / "queue" / "runs").glob("*.json"))

    second = coordinator.create_campaign_run_adapter(**kwargs, plan_only=False)
    first_pending[0].unlink()
    resumed = coordinator.create_campaign_run_adapter(**kwargs, plan_only=False)

    assert first["exact_run_ids"] == second["exact_run_ids"] == resumed["exact_run_ids"]
    assert first["created"] == {"registered": 2, "pending_dependencies": 2}
    assert second["created"] == {"registered": 0, "pending_dependencies": 0}
    assert resumed["created"] == {"registered": 0, "pending_dependencies": 1}
    assert len(sorted((tmp_path / "queue" / "runs").glob("*.json"))) == 2
    assert len(sorted(pending_root.glob("*.json"))) == 2
    assert {json.loads(path.read_text())["run_id"] for path in first_states} == {
        first["runs"][0]["run_id"],
        first["runs"][1]["run_id"],
    }


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("missing_lane", "exactly four lanes"),
        ("duplicate_lane", "lane is duplicated"),
        ("fifth_lane", "exactly four lanes"),
        ("work_id", "work identity differs"),
        ("campaign_version", "campaign version drift"),
        ("source_pairing", "translation source pairing"),
        ("caller_run_id", "caller-supplied run identity"),
        ("runtime_digest", "runtime identity digest"),
        ("max_runs", "max_runs=1"),
    ],
)
def test_apf_004_create_run_adapter_negative_matrix_fails_before_write(
    tmp_path: Path,
    mutation: str,
    expected: str,
) -> None:
    workset = _apf_004_workset()
    exact_tuples = _apf_004_exact_tuples(workset)
    kwargs = _apf_004_kwargs(tmp_path, workset)
    if mutation == "missing_lane":
        exact_tuples = exact_tuples[:3]
    elif mutation == "duplicate_lane":
        exact_tuples[1] = {**exact_tuples[1], "lane": "new"}
    elif mutation == "fifth_lane":
        exact_tuples.append(
            {"lane": "extra", "work_id": "apf-work-extra", "article_id": "EXTRA", "locale": "ja"}
        )
    elif mutation == "work_id":
        exact_tuples[0] = {**exact_tuples[0], "work_id": "apf-work-drift"}
    elif mutation == "campaign_version":
        kwargs["campaign_version"] = "apf-001-drift"
    elif mutation == "source_pairing":
        items = list(workset["items"])
        drifted = dict(items[2])
        drifted["article_id"] = "ASTRO-SCENARIO-BIG-THREE"
        drifted["work_id"] = coordinator._campaign_work_id(
            "legacy",
            "ASTRO-SCENARIO-BIG-THREE",
            "zh-TW",
            "apf-001-v1",
        )
        items[2] = drifted
        workset = {**workset, "items": items}
        exact_tuples = _apf_004_exact_tuples(workset)
        kwargs["workset"] = workset
        kwargs["workset_sha256"] = _apf_004_digest(workset)
    elif mutation == "caller_run_id":
        exact_tuples[0] = {**exact_tuples[0], "run_id": "caller-run-id"}
    elif mutation == "runtime_digest":
        kwargs["runtime_identity_digest"] = "not-a-sha"
    else:
        kwargs["max_runs"] = 2
    kwargs["exact_tuples"] = exact_tuples

    with pytest.raises(ValueError, match=expected):
        coordinator.create_campaign_run_adapter(**kwargs, plan_only=False)

    assert _tree_bytes(tmp_path) == {}


@pytest.mark.parametrize(
    ("forbidden_key", "value"),
    [
        ("run_id", 123),
        ("status", False),
        ("verdict", None),
        ("ready", 0),
    ],
)
def test_apf_004_create_run_adapter_rejects_non_string_forbidden_workset_keys_before_write(
    tmp_path: Path,
    forbidden_key: str,
    value: object,
) -> None:
    workset = _apf_004_workset()
    items = list(workset["items"])
    items[1] = {**dict(items[1]), forbidden_key: value}
    workset = {**workset, "items": items}
    kwargs = _apf_004_kwargs(tmp_path, workset)
    kwargs["workset_sha256"] = _apf_004_digest(workset)

    with pytest.raises(ValueError, match="caller-supplied run identity or status"):
        coordinator.create_campaign_run_adapter(**kwargs, plan_only=True)

    assert _tree_bytes(tmp_path) == {}


def test_apf_004_create_run_adapter_rejects_root_overlap_and_state_collision(
    tmp_path: Path,
) -> None:
    overlap = _apf_004_kwargs(tmp_path / "overlap")
    overlap["state_root"] = overlap["queue_root"]
    with pytest.raises(ValueError, match="roots must not overlap"):
        coordinator.create_campaign_run_adapter(**overlap, plan_only=False)
    assert _tree_bytes(tmp_path / "overlap") == {}

    kwargs = _apf_004_kwargs(tmp_path / "collision")
    plan = coordinator.create_campaign_run_adapter(**kwargs, plan_only=True)
    first_run_id = plan["runs"][0]["run_id"]
    run_dir = kwargs["run_root"] / first_run_id
    run_dir.mkdir(parents=True)
    (run_dir / "brief.json").write_text(
        json.dumps({"schema_version": 1, "run_id": first_run_id, "mode": "create", "articles": [{"article_id": "DRIFT"}]}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="run identity collision"):
        coordinator.create_campaign_run_adapter(**kwargs, plan_only=False)


@pytest.mark.parametrize(
    "drift",
    ["source_sha", "translation_sha", "locale", "article_identity", "review_identity"],
)
def test_campaign_translation_drift_fails_before_queue_or_handoff_mutation(
    tmp_path: Path,
    drift: str,
) -> None:
    result, rewrite_briefs, briefs = _campaign_translation_fixture(tmp_path)
    client = _CampaignTranslationClient(briefs)
    queue_root = tmp_path / "translation-queue"
    state_root = tmp_path / "publisher-state"
    coordinator.replay_campaign_editorial_workset_through_translation(
        Path(__file__).resolve().parents[1],
        result,
        queue_root,
        state_root,
        client,
        rewrite_briefs=rewrite_briefs,
        locale="ja",
        max_repairs=0,
    )
    first_run = next(iter(sorted((queue_root / "translation-runs").iterdir())))
    first_state = next(
        path
        for path in sorted((queue_root / "runs").glob("*.json"))
        if json.loads(path.read_text())["run_id"] == first_run.name
    )
    if drift == "source_sha":
        brief = json.loads((first_run / "brief.json").read_text())
        brief["articles"][0]["source_sha256"] = "0" * 64
        (first_run / "brief.json").write_text(json.dumps(brief), encoding="utf-8")
    elif drift == "translation_sha":
        state = json.loads(first_state.read_text())
        state["result"]["candidate_sha256"] = "0" * 64
        first_state.write_text(json.dumps(state), encoding="utf-8")
    elif drift == "locale":
        brief = json.loads((first_run / "brief.json").read_text())
        brief["articles"][0]["locale"] = "en"
        (first_run / "brief.json").write_text(json.dumps(brief), encoding="utf-8")
    elif drift == "article_identity":
        result["runs"][0]["article_identity"] = {"id": "IDENTITY-DRIFT"}
    else:
        review = json.loads((first_run / "review.json").read_text())
        review["run_id"] = "review-identity-drift"
        (first_run / "review.json").write_text(json.dumps(review), encoding="utf-8")
    before = _tree_bytes(queue_root)

    with pytest.raises(ValueError):
        coordinator.replay_campaign_editorial_workset_through_translation(
            Path(__file__).resolve().parents[1],
            result,
            queue_root,
            state_root,
            client,
            rewrite_briefs=rewrite_briefs,
            locale="ja",
            max_repairs=0,
        )

    assert _tree_bytes(queue_root) == before
    assert not (state_root / "ledger.json").exists()


def test_campaign_editorial_work_item_validates_before_persisting_and_retries(tmp_path: Path) -> None:
    item = _campaign_item("matrix", "NEW-001")
    attempts = 0

    def writer(brief: dict[str, object]) -> dict[str, object]:
        nonlocal attempts
        attempts += 1
        return {"schema_version": 1} if attempts == 1 else _valid_campaign_candidate(brief)

    with pytest.raises(ValueError):
        coordinator.execute_campaign_editorial_work_item(item, tmp_path / "run", brief_factory=lambda _item: _article_brief_v2("new-run-001", "NEW-001"), writer=writer, reviewer=_clean_review)
    assert not (tmp_path / "run" / "editorial-vnext" / "legacy-candidate.json").exists()
    coordinator.execute_campaign_editorial_work_item(item, tmp_path / "run", brief_factory=lambda _item: _article_brief_v2("new-run-001", "NEW-001"), writer=writer, reviewer=_clean_review)
    assert attempts == 2


def test_campaign_editorial_work_item_fails_closed_for_blocking_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = _campaign_item("legacy", "LEGACY-001")
    brief = _article_brief_v2("rewrite-run-001", "LEGACY-001")
    candidate = {"schema_version": 1, "run_id": "rewrite-run-001", "mode": "rewrite_existing_body", "articles": [{"article_id": "LEGACY-001"}]}
    review = {"schema_version": 1, "run_id": "rewrite-run-001", "articles": [{"article_id": "LEGACY-001", "candidate_sha256": "a", "verdict": "REJECT", "findings": [{"code": "blocked", "message": "fixture"}]}]}
    monkeypatch.setattr(coordinator.pipeline, "validate_candidate", lambda _value: None)
    monkeypatch.setattr(coordinator.pipeline, "validate_review", lambda _value, _articles: None)

    with pytest.raises(ValueError, match="blocking findings"):
        coordinator.execute_campaign_editorial_work_item(item, tmp_path / "run", brief_factory=lambda _item: brief, writer=lambda _brief: candidate, reviewer=lambda _brief, _candidate: review)


def _write_brief(run_dir: Path, run_id: str = "private-run-001") -> None:
    run_dir.mkdir(parents=True)
    (run_dir / "brief.json").write_text(
        json.dumps({"schema_version": 1, "run_id": run_id, "mode": "create", "articles": []}),
        encoding="utf-8",
    )


def _expected_identity_envelope(
    mode: str,
    lane: str,
    article_ids: list[str],
) -> dict[str, object]:
    identity = {
        "schema_version": 1,
        "mode": mode,
        "lane": lane,
        "article_ids": sorted(article_ids),
    }
    digest = hashlib.sha256(
        json.dumps(
            identity,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return {**identity, "digest": digest}


def test_register_run_is_idempotent_and_keeps_private_path_local(tmp_path: Path) -> None:
    run_dir = tmp_path / "private-runs" / "run-001"
    queue_root = tmp_path / "queue"
    _write_brief(run_dir)

    first = register_run(run_dir, queue_root)
    second = register_run(run_dir, queue_root)

    assert first == second
    assert first["status"] == "active"
    assert first["run_dir"] == str(run_dir.resolve())
    assert len(list((queue_root / "runs").glob("*.json"))) == 1


def test_register_and_exact_activation_persist_immutable_identity_envelope(
    tmp_path: Path,
) -> None:
    queue_root = tmp_path / "queue"
    expected = _expected_identity_envelope(
        "create",
        "new",
        ["V2-MBTI-INTJ-WORK", "V2-MBTI-ENFP-LOVE"],
    )

    run_dir = tmp_path / "private-runs" / "registered-envelope"
    run_dir.mkdir(parents=True)
    (run_dir / "brief.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_id": run_dir.name,
                "mode": "create",
                "articles": [
                    {"target": {"id": "V2-MBTI-INTJ-WORK"}},
                    {"target": {"id": "V2-MBTI-ENFP-LOVE"}},
                ],
            }
        ),
        encoding="utf-8",
    )

    registered = register_run(run_dir, queue_root)

    exact_run_id = "exact-envelope"
    exact_run_dir = tmp_path / "private-runs" / exact_run_id
    staging_run_dir = (
        tmp_path / "private-runs" / ".exact-run-staging" / "owned-token" / exact_run_id
    )
    staging_run_dir.mkdir(parents=True)
    (staging_run_dir / "brief.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_id": exact_run_id,
                "mode": "create",
                "articles": [
                    {"target": {"id": "V2-MBTI-ENFP-LOVE"}},
                    {"target": {"id": "V2-MBTI-INTJ-WORK"}},
                ],
            }
        ),
        encoding="utf-8",
    )
    coordinator._reserve_run_identity(
        exact_run_id,
        exact_run_dir,
        queue_root,
        "exact-correlation",
        "owned-token",
    )
    activated = coordinator._activate_run_reservation(
        exact_run_id,
        staging_run_dir,
        exact_run_dir,
        queue_root,
        "exact-correlation",
        "owned-token",
    )

    assert registered["identity_envelope"] == expected
    assert activated["identity_envelope"] == expected


@pytest.mark.parametrize(
    ("run_id", "brief", "expected_lane"),
    [
        ("new-routing", {"mode": "create", "articles": []}, "new"),
        ("rewrite-routing", {"mode": "rewrite_existing_body", "articles": [{"article_id": "LEGACY-001"}]}, "rewrite"),
        (
            "i18n-new-routing",
            {"mode": "translate_existing", "lane": "i18n-new", "articles": [{"source_article_id": "NEW-001"}]},
            "i18n-new",
        ),
        (
            "i18n-rewrite-routing",
            {"mode": "translate_existing", "lane": "i18n-rewrite", "articles": [{"source_article_id": "LEGACY-001"}]},
            "i18n-rewrite",
        ),
    ],
)
def test_register_run_persists_immutable_mode_and_lane(
    tmp_path: Path,
    run_id: str,
    brief: dict[str, object],
    expected_lane: str,
) -> None:
    run_dir = tmp_path / "private-runs" / run_id
    queue_root = tmp_path / "queue"
    run_dir.mkdir(parents=True)
    (run_dir / "brief.json").write_text(
        json.dumps({"schema_version": 1, "run_id": run_id, **brief}),
        encoding="utf-8",
    )

    state = register_run(run_dir, queue_root)

    assert state["routing_schema_version"] == 1
    assert state["mode"] == brief["mode"]
    assert state["lane"] == expected_lane
    assert coordinator._lane_for_state(state, {"LEGACY-001"}) == expected_lane


def test_formal_coordinator_rejects_manifest_drift_before_lock_mutation(
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
        identity="formal-coordinator",
        runtime_digest="1" * 64,
        generation="generation-coordinator",
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
        "PANTHEON_RUNTIME_SERVICE_LABEL",
        "com.pantheon.agy-gemini-coordinator",
    )
    manifest_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(runtime_manifest.RuntimeManifestError):
        cycle_once(queue, repo_root=actor)

    assert not (queue / "coordinator.lock").exists()


def test_resume_locale_plan_validation_failure_starts_fresh_attempt(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "private-runs" / "run-locale-plan-failed"
    queue_root = tmp_path / "queue"
    _write_brief(run_dir, "run-locale-plan-failed")
    state = register_run(run_dir, queue_root)
    state.update(
        {
            "status": "failed",
            "last_job_id": "terminal-locale-plan-job",
            "error_type": "LocalePlanValidationError",
        }
    )
    coordinator._write_state(queue_root, state)

    resumed = coordinator.resume_run(run_dir, queue_root)

    assert resumed["status"] == "active"
    assert "last_job_id" not in resumed
    assert "error_type" not in resumed


def test_resume_other_failure_preserves_existing_job_lineage(tmp_path: Path) -> None:
    run_dir = tmp_path / "private-runs" / "run-provider-failed"
    queue_root = tmp_path / "queue"
    _write_brief(run_dir, "run-provider-failed")
    state = register_run(run_dir, queue_root)
    state.update(
        {
            "status": "failed",
            "last_job_id": "terminal-provider-job",
            "error_type": "V4BrokerFailure",
        }
    )
    coordinator._write_state(queue_root, state)

    resumed = coordinator.resume_run(run_dir, queue_root)

    assert resumed["status"] == "active"
    assert resumed["last_job_id"] == "terminal-provider-job"
    assert "error_type" not in resumed


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_same_gen_locale_plan_retry_fixture(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    run_id = "auto-i18n-ja-1414b75a404721e95e74"
    run_dir, queue_root = tmp_path / "private-runs" / run_id, tmp_path / "queue"
    run_dir.mkdir(parents=True)
    (run_dir / "brief.json").write_text(json.dumps({"schema_version": 1, "run_id": run_id, "mode": "translate_existing", "lane": "i18n-new", "articles": [{"source_article_id": "V2-TAROT-DEATH-MONEY", "locale": "ja", "article_id": "V2-TAROT-DEATH-MONEY:ja"}]}, ensure_ascii=False), encoding="utf-8")
    state = register_run(run_dir, queue_root)
    (run_dir / "continuation").mkdir()
    (run_dir / "continuation/state.json").write_text(json.dumps({"schema_version": 1, "run_id": run_id, "status": "active", "next_generation": 6}, ensure_ascii=False), encoding="utf-8")
    gen_dir = run_dir / "generations/06"
    gen_dir.mkdir(parents=True)
    artifacts = {
        "external_plan": gen_dir / "external-plan.json",
        "plan_operation": gen_dir / "plan-operation.json",
        "planning_result": gen_dir / "planning-result.json",
        "source_ref_map": gen_dir / "source-ref-map.json",
    }
    artifacts["external_plan"].write_text(json.dumps({"articles": [{"slot": "article-01", "coverage_mapping": [{"coverage_note": "財務現狀的檢視與重塑"}]}]}, ensure_ascii=False), encoding="utf-8")
    artifacts["planning_result"].write_text(json.dumps({"schema_version": 1, "generation": 6, "transport_status": "EXTERNAL_PLAN_AVAILABLE", "planning_contract_status": "PLANNING_CONTRACT_FAILURE", "terminal_stage": "PLANNING"}, ensure_ascii=False), encoding="utf-8")
    artifacts["source_ref_map"].write_text(json.dumps({"schema_version": 1, "generation": 6, "articles": []}, ensure_ascii=False), encoding="utf-8")
    lane_root = queue_root / "lanes/i18n-new"
    request_args = {"namespace": "same-gen-test", "role": "writer", "model": "gemini-test", "prompt": "retry prompt", "response_schema": {"type": "object"}}
    request = create_external_request(lane_root, **request_args)
    artifacts["plan_operation"].write_text(json.dumps({"status": "success", "role": "writer", "transport": "_outbox_transport", "prompt_sha256": request["prompt_sha256"], "schema_sha256": request["schema_sha256"]}, ensure_ascii=False), encoding="utf-8")
    job_id = str(request["job_id"])
    state.update({"status": "failed", "lane": "i18n-new", "last_job_id": job_id, "error_type": "LocalePlanValidationError"})
    coordinator._write_state(queue_root, state)
    for child in ("production-attempts", "archive", "inbox"):
        (lane_root / child).mkdir(parents=True)
    attempt = lane_root / "production-attempts" / f"{job_id}.attempt"
    archive = lane_root / "archive" / f"{job_id}.json"
    inbox = lane_root / "inbox" / f"{job_id}.json"
    attempt.write_text(json.dumps({"job_id": job_id, "attempt_status": "succeeded", "request_sha256": request["request_sha256"]}, ensure_ascii=False), encoding="utf-8")
    (lane_root / "outbox" / f"{job_id}.json").replace(archive)
    inbox.write_text(json.dumps({"schema_version": 1, "job_id": job_id, "request_sha256": request["request_sha256"], "model": request["model"], "completed_at": "2026-08-28T00:00:00+08:00", "result": {"stale": True}}, ensure_ascii=False), encoding="utf-8")
    return run_dir, queue_root, {
        "run_id": run_id, "job_id": job_id, "registry": coordinator._canonical_json_file_sha256(state),
        "attempt": _sha(attempt), "archive": _sha(archive), "inbox": _sha(inbox),
        "request_args": request_args,
        **{key: _sha(path) for key, path in artifacts.items()},
    }


def _write_prior_same_gen_quarantine(run_dir: Path, expected: dict[str, str]) -> None:
    quarantine = run_dir / "generations/06/planning-cache-quarantine" / expected["job_id"]
    quarantine.mkdir(parents=True)
    atomic_digests = {key: expected[key] for key in ("external_plan", "plan_operation", "planning_result", "source_ref_map")}
    for key, name in coordinator.SAME_GENERATION_PLAN_RETRY_FILES.items():
        shutil.copy2(run_dir / "generations/06" / name, quarantine / name)
    (quarantine / "retry-receipt.json").write_text(json.dumps({"action": "retry_same_generation_locale_plan", "run_id": expected["run_id"], "generation": 6, "job_id": expected["job_id"], "digests": {**atomic_digests, "registry": expected["registry"], "attempt": expected["attempt"], "archive": expected["archive"], "inbox": expected["inbox"]}, "status": "QUARANTINED"}, ensure_ascii=False), encoding="utf-8")


def _retry_kwargs(expected: dict[str, str]) -> dict[str, object]:
    return {
        "expected_run_id": expected["run_id"], "generation": 6, "expected_registry_digest": expected["registry"],
        "expected_job_id": expected["job_id"], "expected_attempt_digest": expected["attempt"],
        "expected_archive_digest": expected["archive"], "expected_inbox_digest": expected["inbox"],
        "expected_external_plan_digest": expected["external_plan"], "expected_plan_operation_digest": expected["plan_operation"],
        "expected_planning_result_digest": expected["planning_result"], "expected_source_ref_map_digest": expected["source_ref_map"],
    }


def test_same_generation_locale_plan_retry_plan_is_zero_write(tmp_path: Path) -> None:
    run_dir, queue_root, expected = _write_same_gen_locale_plan_retry_fixture(tmp_path)
    before = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}

    receipt = coordinator.retry_same_generation_locale_plan(run_dir, queue_root, **_retry_kwargs(expected))

    assert receipt["status"] == "READY_TO_EXECUTE"
    assert before == {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}


def test_same_generation_locale_plan_retry_cli_plan_only(tmp_path: Path) -> None:
    run_dir, queue_root, expected = _write_same_gen_locale_plan_retry_fixture(tmp_path)
    args = [sys.executable, "-m", "scripts.agy_gemini_coordinator", "--queue-root", str(queue_root), "retry-same-generation-locale-plan", str(run_dir), "--run-id", expected["run_id"], "--generation", "6", "--expected-job-id", expected["job_id"]]
    for key in ("registry", "attempt", "archive", "inbox", "external-plan", "plan-operation", "planning-result", "source-ref-map"):
        args += [f"--expected-{key}-digest", expected[key.replace("-", "_")]]

    completed = subprocess.run(args, cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True, check=True)

    assert json.loads(completed.stdout)["status"] == "READY_TO_EXECUTE"
    assert read_run_state(run_dir, queue_root)["status"] == "failed"


def test_same_generation_locale_plan_retry_execute_enqueues_fresh_gen06(tmp_path: Path) -> None:
    run_dir, queue_root, expected = _write_same_gen_locale_plan_retry_fixture(tmp_path)

    receipt = coordinator.retry_same_generation_locale_plan(run_dir, queue_root, **_retry_kwargs(expected), execute=True)
    lane_root = queue_root / "lanes/i18n-new"
    for child, suffix in (("archive", ".json"), ("inbox", ".json"), ("production-attempts", ".attempt")):
        assert not (lane_root / child / f"{expected['job_id']}{suffix}").exists()
    request = create_external_request(lane_root, **expected["request_args"])
    assert request["job_id"] == expected["job_id"]
    assert (lane_root / "outbox" / f"{expected['job_id']}.json").is_file()
    with pytest.raises(ExternalJobPending):
        consume_external_response(lane_root, request)
    calls = 0

    def tick(path: Path, _root: Path) -> dict[str, object]:
        nonlocal calls
        calls += 1
        assert path.resolve() == run_dir.resolve()
        assert not (run_dir / "generations/06/external-plan.json").exists()
        assert not (run_dir / "generations/07").exists()
        raise ExternalJobPending("fresh-gen06-job")

    summary = cycle_once(queue_root, tick=tick, process=lambda _root, **_kwargs: {"status": "idle"}, repo_root=Path(__file__).resolve().parents[1], lane_mode=True, exact_run_ids=[expected["run_id"]])
    state = read_run_state(run_dir, queue_root)

    assert receipt["status"] == "RETRY_READY"
    assert calls == 1
    assert summary["runner"] == {"status": "idle"}
    assert state["last_job_id"] == "fresh-gen06-job"
    assert (run_dir / "generations/06/planning-cache-quarantine" / expected["job_id"] / "external-plan.json").is_file()
    assert not (run_dir / "generations/06/candidate.json").exists()


@pytest.mark.parametrize("drift", ["candidate", "gen07", "lane_residue"])
def test_same_generation_locale_plan_retry_rechecks_generation_boundary_inside_lock(tmp_path: Path, drift: str) -> None:
    run_dir, queue_root, expected = _write_same_gen_locale_plan_retry_fixture(tmp_path)
    real_lock = coordinator._run_identity_lock

    @coordinator.contextmanager
    def drifting_lock(run_id: str, root: Path):
        with real_lock(run_id, root):
            if drift == "lane_residue":
                path = queue_root / "lanes/i18n-new/inbox" / f"{expected['job_id']}.json"
                path.write_text("{}", encoding="utf-8")
            else:
                path = run_dir / ("generations/06/candidate.json" if drift == "candidate" else "generations/07")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}", encoding="utf-8") if drift == "candidate" else path.mkdir()
            yield

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(coordinator, "_run_identity_lock", drifting_lock)
        with pytest.raises(ValueError):
            coordinator.retry_same_generation_locale_plan(run_dir, queue_root, **_retry_kwargs(expected), execute=True)
    assert read_run_state(run_dir, queue_root)["status"] == "failed"


@pytest.mark.parametrize("field,value", [("lane", "i18n-rewrite"), ("mode", "create"), ("routing_schema_version", 99)])
def test_same_generation_locale_plan_retry_rejects_active_selector_drift(tmp_path: Path, field: str, value: object) -> None:
    run_dir, queue_root, expected = _write_same_gen_locale_plan_retry_fixture(tmp_path)
    coordinator.retry_same_generation_locale_plan(run_dir, queue_root, **_retry_kwargs(expected), execute=True)
    state = read_run_state(run_dir, queue_root)
    state[field] = value
    coordinator._write_state(queue_root, state)

    with pytest.raises(ValueError):
        coordinator.retry_same_generation_locale_plan(run_dir, queue_root, **_retry_kwargs(expected), execute=True)


@pytest.mark.parametrize("drift", ["registry_digest", "registry_status", "job_status", "artifact_digest", "candidate_present"])
def test_same_generation_locale_plan_retry_rejects_drift(tmp_path: Path, drift: str) -> None:
    run_dir, queue_root, expected = _write_same_gen_locale_plan_retry_fixture(tmp_path)
    if drift == "registry_digest":
        expected["registry"] = "0" * 64
    elif drift == "registry_status":
        state = read_run_state(run_dir, queue_root)
        state["status"] = "active"
        coordinator._write_state(queue_root, state)
    elif drift == "job_status":
        attempt = queue_root / "lanes/i18n-new/production-attempts" / f"{expected['job_id']}.attempt"
        attempt.write_text(json.dumps({"job_id": expected["job_id"], "attempt_status": "failed", "request_sha256": "1" * 64}), encoding="utf-8")
        expected["attempt"] = _sha(attempt)
    elif drift == "artifact_digest":
        expected["external_plan"] = "0" * 64
    else:
        (run_dir / "generations/06/candidate.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError):
        coordinator.retry_same_generation_locale_plan(run_dir, queue_root, **_retry_kwargs(expected), execute=True)


def test_same_generation_locale_plan_retry_crash_window_replay(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir, queue_root, expected = _write_same_gen_locale_plan_retry_fixture(tmp_path)
    real_write_state = coordinator._write_state
    monkeypatch.setattr(coordinator, "_write_state", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("crash-after-quarantine")))
    with pytest.raises(RuntimeError, match="crash-after-quarantine"):
        coordinator.retry_same_generation_locale_plan(run_dir, queue_root, **_retry_kwargs(expected), execute=True)
    monkeypatch.setattr(coordinator, "_write_state", real_write_state)

    replay = coordinator.retry_same_generation_locale_plan(run_dir, queue_root, **_retry_kwargs(expected), execute=True)

    assert replay["status"] == "RETRY_READY"
    assert read_run_state(run_dir, queue_root)["status"] == "active"


def test_same_generation_locale_plan_retry_recovers_null_last_job_from_exact_residue(tmp_path: Path) -> None:
    run_dir, queue_root, expected = _write_same_gen_locale_plan_retry_fixture(tmp_path)
    _write_prior_same_gen_quarantine(run_dir, expected)
    state = read_run_state(run_dir, queue_root)
    state.pop("last_job_id")
    coordinator._write_state(queue_root, state)
    expected["registry"] = coordinator._canonical_json_file_sha256(state)
    before = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}

    plan = coordinator.retry_same_generation_locale_plan(run_dir, queue_root, **_retry_kwargs(expected))
    assert before == {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    receipt = coordinator.retry_same_generation_locale_plan(run_dir, queue_root, **_retry_kwargs(expected), execute=True)
    request = create_external_request(queue_root / "lanes/i18n-new", **expected["request_args"])

    assert plan["status"] == "READY_TO_EXECUTE"
    assert receipt["status"] == "RETRY_READY"
    assert request["job_id"] == expected["job_id"]
    with pytest.raises(ExternalJobPending):
        consume_external_response(queue_root / "lanes/i18n-new", request)
    assert not (run_dir / "generations/07").exists()


@pytest.mark.parametrize("drift", ["prompt_schema", "missing_both_hashes", "invalid_matching_hashes", "wrong_job", "ambiguous"])
def test_same_generation_locale_plan_retry_null_last_job_rejects_identity_drift(tmp_path: Path, drift: str) -> None:
    run_dir, queue_root, expected = _write_same_gen_locale_plan_retry_fixture(tmp_path)
    _write_prior_same_gen_quarantine(run_dir, expected)
    state = read_run_state(run_dir, queue_root)
    state.pop("last_job_id")
    coordinator._write_state(queue_root, state)
    expected["registry"] = coordinator._canonical_json_file_sha256(state)
    if drift == "prompt_schema":
        path = run_dir / "generations/06/plan-operation.json"
        path.write_text(json.dumps({"status": "success", "role": "writer", "prompt_sha256": "0" * 64, "schema_sha256": "1" * 64}, ensure_ascii=False), encoding="utf-8")
        expected["plan_operation"] = _sha(path)
    elif drift == "missing_both_hashes":
        plan_path = run_dir / "generations/06/plan-operation.json"
        archive_path = queue_root / "lanes/i18n-new/archive" / f"{expected['job_id']}.json"
        plan_path.write_text(json.dumps({"status": "success", "role": "writer"}, ensure_ascii=False), encoding="utf-8")
        archive = json.loads(archive_path.read_text(encoding="utf-8"))
        archive.pop("prompt_sha256")
        archive.pop("schema_sha256")
        archive_path.write_text(json.dumps(archive, ensure_ascii=False), encoding="utf-8")
        expected["plan_operation"], expected["archive"] = _sha(plan_path), _sha(archive_path)
    elif drift == "invalid_matching_hashes":
        plan_path = run_dir / "generations/06/plan-operation.json"
        archive_path = queue_root / "lanes/i18n-new/archive" / f"{expected['job_id']}.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        archive = json.loads(archive_path.read_text(encoding="utf-8"))
        plan["prompt_sha256"] = archive["prompt_sha256"] = "not-a-sha"
        plan["schema_sha256"] = archive["schema_sha256"] = "also-not-a-sha"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        archive_path.write_text(json.dumps(archive, ensure_ascii=False), encoding="utf-8")
        expected["plan_operation"], expected["archive"] = _sha(plan_path), _sha(archive_path)
    elif drift == "wrong_job":
        path = queue_root / "lanes/i18n-new/archive" / f"{expected['job_id']}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["job_id"] = "0" * 40
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        expected["archive"] = _sha(path)
    else:
        (queue_root / "lanes/i18n-new/outbox" / f"{expected['job_id']}.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError):
        coordinator.retry_same_generation_locale_plan(run_dir, queue_root, **_retry_kwargs(expected), execute=True)


def _write_terminal_authorized_registry_split(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    run_id = "auto-i18n-ja-1414b75a404721e95e74"
    run_dir = tmp_path / "private-runs" / run_id
    queue_root = tmp_path / "queue"
    _write_brief(run_dir, run_id)
    state = register_run(run_dir, queue_root)
    state.update({"status": "complete", "last_job_id": "reviewer-job", "result": {"status": "complete", "run_id": run_id}})
    coordinator._write_state(queue_root, state)
    continuation = {
        "schema_version": 1,
        "run_id": run_id,
        "status": "active",
        "next_generation": 6,
        "semantic_budget": 2,
    }
    transition = {
        "schema_version": 1,
        "contract": "continuation-authority-transition",
        "action": "authorize_next_generation_after_reviewer_reject",
        "run_id": run_id,
        "terminal_generation": 5,
        "to_next_generation": 6,
        "state_after_sha256": coordinator.multilingual._json_sha256(continuation),
        "state_after": continuation,
    }
    (run_dir / "continuation").mkdir()
    (run_dir / "continuation/state.json").write_text(json.dumps(continuation, ensure_ascii=False), encoding="utf-8")
    (run_dir / "continuation/authority-transition-05.json").write_text(json.dumps(transition, ensure_ascii=False), encoding="utf-8")
    return run_dir, queue_root, {
        "run_id": run_id,
        "registry_digest": coordinator._canonical_json_file_sha256(state),
        "transition_digest": coordinator.multilingual._json_sha256(transition),
        "state_after_digest": transition["state_after_sha256"],
    }


def test_authorized_next_generation_reactivation_plan_is_zero_write(tmp_path: Path) -> None:
    run_dir, queue_root, expected = _write_terminal_authorized_registry_split(tmp_path)
    before = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}

    receipt = coordinator.reactivate_authorized_next_generation_registry(
        run_dir,
        queue_root,
        expected_run_id=expected["run_id"],
        terminal_generation=5,
        expected_registry_digest=expected["registry_digest"],
        expected_transition_digest=expected["transition_digest"],
        expected_state_after_digest=expected["state_after_digest"],
        expected_next_generation=6,
    )

    assert receipt["status"] == "READY_TO_EXECUTE"
    assert before == {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}


def test_authorized_next_generation_reactivation_enables_exact_cycle(tmp_path: Path) -> None:
    run_dir, queue_root, expected = _write_terminal_authorized_registry_split(tmp_path)

    receipt = coordinator.reactivate_authorized_next_generation_registry(
        run_dir,
        queue_root,
        expected_run_id=expected["run_id"],
        terminal_generation=5,
        expected_registry_digest=expected["registry_digest"],
        expected_transition_digest=expected["transition_digest"],
        expected_state_after_digest=expected["state_after_digest"],
        expected_next_generation=6,
        execute=True,
    )
    calls: list[Path] = []

    def tick(path: Path, _job_root: Path) -> dict[str, object]:
        calls.append(path)
        raise ExternalJobPending("gen06-writer-job")

    summary = cycle_once(queue_root, tick=tick, process=lambda _root, **_kwargs: {"status": "idle"}, repo_root=Path(__file__).resolve().parents[1], lane_mode=True, exact_run_ids=[expected["run_id"]])
    state = read_run_state(run_dir, queue_root)

    assert receipt["status"] == "REACTIVATED"
    assert calls == [run_dir.resolve()]
    assert summary["active"] == 1
    assert state["status"] == "active"
    assert state["last_job_id"] == "gen06-writer-job"
    assert not (run_dir / "generations/06").exists()


@pytest.mark.parametrize("drift", ["registry", "transition", "state", "gen06"])
def test_authorized_next_generation_reactivation_rejects_drift(tmp_path: Path, drift: str) -> None:
    run_dir, queue_root, expected = _write_terminal_authorized_registry_split(tmp_path)
    if drift == "registry":
        state = read_run_state(run_dir, queue_root)
        state["result"] = {"status": "failed", "run_id": expected["run_id"]}
        coordinator._write_state(queue_root, state)
    elif drift == "transition":
        expected["transition_digest"] = "0" * 64
    elif drift == "state":
        (run_dir / "continuation/state.json").write_text(json.dumps({"status": "active", "next_generation": 7}), encoding="utf-8")
    else:
        (run_dir / "generations/06").mkdir(parents=True)

    with pytest.raises(ValueError):
        coordinator.reactivate_authorized_next_generation_registry(
            run_dir,
            queue_root,
            expected_run_id=expected["run_id"],
            terminal_generation=5,
            expected_registry_digest=expected["registry_digest"],
            expected_transition_digest=expected["transition_digest"],
            expected_state_after_digest=expected["state_after_digest"],
            expected_next_generation=6,
            execute=True,
        )


def test_authorized_next_generation_reactivation_active_replay_is_idempotent(tmp_path: Path) -> None:
    run_dir, queue_root, expected = _write_terminal_authorized_registry_split(tmp_path)
    coordinator.reactivate_authorized_next_generation_registry(run_dir, queue_root, expected_run_id=expected["run_id"], terminal_generation=5, expected_registry_digest=expected["registry_digest"], expected_transition_digest=expected["transition_digest"], expected_state_after_digest=expected["state_after_digest"], expected_next_generation=6, execute=True)

    replay = coordinator.reactivate_authorized_next_generation_registry(run_dir, queue_root, expected_run_id=expected["run_id"], terminal_generation=5, expected_registry_digest=expected["registry_digest"], expected_transition_digest=expected["transition_digest"], expected_state_after_digest=expected["state_after_digest"], expected_next_generation=6, execute=True)

    assert replay["status"] == "ALREADY_ACTIVE"


def test_authorized_next_generation_reactivation_revalidates_transition_inside_lock(tmp_path: Path) -> None:
    run_dir, queue_root, expected = _write_terminal_authorized_registry_split(tmp_path)
    real_lock = coordinator._run_identity_lock

    @coordinator.contextmanager
    def drifting_lock(run_id: str, root: Path):
        with real_lock(run_id, root):
            transition_path = run_dir / "continuation/authority-transition-05.json"
            transition = json.loads(transition_path.read_text())
            transition["state_after"]["next_generation"] = 7
            transition_path.write_text(json.dumps(transition, ensure_ascii=False), encoding="utf-8")
            yield

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(coordinator, "_run_identity_lock", drifting_lock)
        with pytest.raises(ValueError, match="transition identity"):
            coordinator.reactivate_authorized_next_generation_registry(run_dir, queue_root, expected_run_id=expected["run_id"], terminal_generation=5, expected_registry_digest=expected["registry_digest"], expected_transition_digest=expected["transition_digest"], expected_state_after_digest=expected["state_after_digest"], expected_next_generation=6, execute=True)
    assert read_run_state(run_dir, queue_root)["status"] == "complete"


def test_authorized_next_generation_reactivation_rejects_active_replay_with_stale_result(tmp_path: Path) -> None:
    run_dir, queue_root, expected = _write_terminal_authorized_registry_split(tmp_path)
    coordinator.reactivate_authorized_next_generation_registry(run_dir, queue_root, expected_run_id=expected["run_id"], terminal_generation=5, expected_registry_digest=expected["registry_digest"], expected_transition_digest=expected["transition_digest"], expected_state_after_digest=expected["state_after_digest"], expected_next_generation=6, execute=True)
    state = read_run_state(run_dir, queue_root)
    state["result"] = {"status": "complete", "run_id": expected["run_id"]}
    coordinator._write_state(queue_root, state)

    with pytest.raises(ValueError, match="already active"):
        coordinator.reactivate_authorized_next_generation_registry(run_dir, queue_root, expected_run_id=expected["run_id"], terminal_generation=5, expected_registry_digest=expected["registry_digest"], expected_transition_digest=expected["transition_digest"], expected_state_after_digest=expected["state_after_digest"], expected_next_generation=6, execute=True)


@pytest.mark.parametrize("field,value", [("lane", "rewrite"), ("mode", "rewrite_existing_body"), ("routing_schema_version", 99)])
def test_authorized_next_generation_reactivation_rejects_active_selector_drift(tmp_path: Path, field: str, value: object) -> None:
    run_dir, queue_root, expected = _write_terminal_authorized_registry_split(tmp_path)
    coordinator.reactivate_authorized_next_generation_registry(run_dir, queue_root, expected_run_id=expected["run_id"], terminal_generation=5, expected_registry_digest=expected["registry_digest"], expected_transition_digest=expected["transition_digest"], expected_state_after_digest=expected["state_after_digest"], expected_next_generation=6, execute=True)
    state = read_run_state(run_dir, queue_root)
    state[field] = value
    coordinator._write_state(queue_root, state)

    with pytest.raises(ValueError, match="already active"):
        coordinator.reactivate_authorized_next_generation_registry(run_dir, queue_root, expected_run_id=expected["run_id"], terminal_generation=5, expected_registry_digest=expected["registry_digest"], expected_transition_digest=expected["transition_digest"], expected_state_after_digest=expected["state_after_digest"], expected_next_generation=6, execute=True)


def test_authorized_next_generation_reactivation_cli_plan_only(tmp_path: Path) -> None:
    run_dir, queue_root, expected = _write_terminal_authorized_registry_split(tmp_path)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.agy_gemini_coordinator",
            "--queue-root",
            str(queue_root),
            "reactivate-authorized-next-generation",
            str(run_dir),
            "--run-id",
            expected["run_id"],
            "--terminal-generation",
            "5",
            "--expected-registry-digest",
            expected["registry_digest"],
            "--expected-transition-digest",
            expected["transition_digest"],
            "--expected-state-after-digest",
            expected["state_after_digest"],
            "--expected-next-generation",
            "6",
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=True,
    )

    assert json.loads(completed.stdout)["status"] == "READY_TO_EXECUTE"
    assert read_run_state(run_dir, queue_root)["status"] == "complete"


def test_register_run_rejects_more_than_five_articles(tmp_path: Path) -> None:
    run_dir = tmp_path / "private-runs" / "run-oversized"
    run_dir.mkdir(parents=True)
    (run_dir / "brief.json").write_text(
        json.dumps({"run_id": "too-many", "articles": [{"slot": index} for index in range(6)]}),
        encoding="utf-8",
    )

    try:
        register_run(run_dir, tmp_path / "queue")
    except ValueError as error:
        assert str(error) == "brief articles must contain at most 5 items"
    else:
        raise AssertionError("six-article run must be rejected")


def test_register_run_accepts_private_rewrite_brief_above_eight_kb(tmp_path: Path) -> None:
    run_dir = tmp_path / "private-runs" / "rewrite-above-eight-kb"
    run_dir.mkdir(parents=True)
    (run_dir / "brief.json").write_text(
        json.dumps(
            {
                "run_id": "rewrite-above-eight-kb",
                "mode": "rewrite_existing_body",
                    "articles": [
                        {
                            "article_id": "LEGACY-LARGE-BRIEF",
                            "current_body": "字" * 3000,
                        }
                    ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    state = register_run(run_dir, tmp_path / "queue")

    assert state["status"] == "active"


def test_cycle_processes_one_external_job_then_completes_run(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "run-001"
    queue_root = tmp_path / "queue"
    _write_brief(run_dir)
    register_run(run_dir, queue_root)
    tick_calls = 0
    process_calls = 0

    def fake_tick(_run_dir: Path, _queue_root: Path) -> dict[str, object]:
        nonlocal tick_calls
        tick_calls += 1
        if tick_calls == 1:
            raise ExternalJobPending("public-job-001")
        return {"status": "complete", "approved_by_reviewer": 2}

    def fake_process(_queue_root: Path) -> dict[str, str]:
        nonlocal process_calls
        process_calls += 1
        return {"status": "processed", "job_id": "public-job-001"}

    summary = cycle_once(queue_root, tick=fake_tick, process=fake_process)
    state = read_run_state(run_dir, queue_root)

    assert summary["runner"] == {"status": "processed", "job_id": "public-job-001"}
    assert summary["complete"] == 1
    assert tick_calls == 2
    assert process_calls == 1
    assert state["status"] == "complete"
    assert state["result"]["approved_by_reviewer"] == 2


def test_cycle_advances_oldest_active_runs_instead_of_state_filename_order(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    expected = [f"run-{index:03d}" for index in range(5)]
    for index in range(8):
        run_id = f"run-{index:03d}"
        run_dir = tmp_path / "runs" / run_id
        _write_brief(run_dir, run_id)
        register_run(run_dir, queue_root)
        state_path = coordinator._state_path(run_id, queue_root)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["updated_at"] = f"2026-07-25T10:{index:02d}:00+08:00"
        state_path.write_text(json.dumps(state), encoding="utf-8")

    advanced: list[str] = []

    def pending_tick(run_dir: Path, _queue_root: Path) -> dict[str, object]:
        advanced.append(run_dir.name)
        raise ExternalJobPending(f"job-{run_dir.name}")

    cycle_once(queue_root, tick=pending_tick, process=lambda _root: {"status": "idle"})

    assert advanced == expected


def test_cycle_exact_run_ids_never_advances_unlisted_active_run(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    for run_id in ("old-active-run", "target-ja-run"):
        run_dir = tmp_path / "runs" / run_id
        _write_brief(run_dir, run_id)
        register_run(run_dir, queue_root)

    advanced: list[str] = []

    def pending_tick(run_dir: Path, _queue_root: Path) -> dict[str, object]:
        advanced.append(run_dir.name)
        raise ExternalJobPending(f"job-{run_dir.name}")

    summary = cycle_once(
        queue_root,
        tick=pending_tick,
        process=lambda _root, **_kwargs: {"status": "idle"},
        exact_run_ids=["target-ja-run"],
    )

    assert advanced == ["target-ja-run"]
    assert summary["active"] == 1
    assert read_run_state(tmp_path / "runs" / "old-active-run", queue_root)["status"] == "active"


def test_cycle_exact_run_ids_processed_runner_keeps_unlisted_run_unchanged(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    for index, run_id in enumerate(("old-active-run", "target-ja-run")):
        run_dir = tmp_path / "runs" / run_id
        _write_brief(run_dir, run_id)
        register_run(run_dir, queue_root)
        state_path = coordinator._state_path(run_id, queue_root)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["updated_at"] = f"2026-08-05T10:0{index}:00+08:00"
        state_path.write_text(json.dumps(state), encoding="utf-8")

    unlisted_state_path = coordinator._state_path("old-active-run", queue_root)
    unlisted_state_before = unlisted_state_path.read_bytes()
    advanced: list[str] = []

    def pending_tick(run_dir: Path, _queue_root: Path) -> dict[str, object]:
        advanced.append(run_dir.name)
        raise ExternalJobPending(f"job-{run_dir.name}")

    summary = cycle_once(
        queue_root,
        tick=pending_tick,
        process=lambda _root, **_kwargs: {
            "status": "processed",
            "job_id": "job-target-ja-run",
        },
        exact_run_ids=["target-ja-run"],
    )

    assert advanced == ["target-ja-run", "target-ja-run"]
    assert unlisted_state_path.read_bytes() == unlisted_state_before
    assert summary["runner"] == {
        "status": "processed",
        "job_id": "job-target-ja-run",
    }


def test_cycle_exact_run_ids_reject_duplicates_before_advancing(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    run_dir = tmp_path / "runs" / "target-ja-run"
    _write_brief(run_dir, run_dir.name)
    register_run(run_dir, queue_root)

    with pytest.raises(ValueError, match="exact run ids must be unique"):
        cycle_once(
            queue_root,
            tick=lambda *_args: pytest.fail("duplicate selector must not advance"),
            exact_run_ids=[run_dir.name, run_dir.name],
        )


def test_cycle_exact_run_ids_continue_after_one_selected_run_is_terminal(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    for run_id in ("target-ja-run", "target-ko-run"):
        run_dir = tmp_path / "runs" / run_id
        _write_brief(run_dir, run_id)
        register_run(run_dir, queue_root)
    completed_path = coordinator._state_path("target-ja-run", queue_root)
    completed = json.loads(completed_path.read_text(encoding="utf-8"))
    completed["status"] = "complete"
    completed_path.write_text(json.dumps(completed), encoding="utf-8")
    advanced: list[str] = []

    def pending_tick(run_dir: Path, _queue_root: Path) -> dict[str, object]:
        advanced.append(run_dir.name)
        raise ExternalJobPending(f"job-{run_dir.name}")

    cycle_once(
        queue_root,
        tick=pending_tick,
        process=lambda _root, **_kwargs: {"status": "idle"},
        exact_run_ids=["target-ja-run", "target-ko-run"],
    )

    assert advanced == ["target-ko-run"]


def test_lane_mode_advances_one_run_per_content_lane(tmp_path: Path, monkeypatch) -> None:
    queue_root = tmp_path / "queue"
    briefs = {
        "new-run": {"mode": "create", "articles": []},
        "rewrite-run": {
            "mode": "rewrite_existing_body",
            "articles": [{"article_id": "LEGACY-001"}],
        },
        "i18n-new-run": {
            "mode": "translate_existing",
            "lane": "i18n-new",
            "articles": [{"source_article_id": "V2-NEW-001", "locale": "en"}],
        },
        "i18n-rewrite-run": {
            "mode": "translate_existing",
            "lane": "i18n-rewrite",
            "articles": [{"source_article_id": "LEGACY-001", "locale": "ja"}],
        },
    }
    for run_id, payload in briefs.items():
        run_dir = tmp_path / "runs" / run_id
        run_dir.mkdir(parents=True)
        (run_dir / "brief.json").write_text(
            json.dumps({"schema_version": 1, "run_id": run_id, **payload}),
            encoding="utf-8",
        )
        register_run(run_dir, queue_root)
    monkeypatch.setattr(coordinator.publisher, "legacy_article_ids", lambda _repo: {"LEGACY-001"})
    routed: dict[str, str] = {}

    def pending_tick(run_dir: Path, job_queue_root: Path) -> dict[str, object]:
        routed[run_dir.name] = str(job_queue_root.relative_to(queue_root))
        raise ExternalJobPending(f"job-{run_dir.name}")

    summary = cycle_once(
        queue_root,
        tick=pending_tick,
        process=lambda _root: {"status": "idle"},
        repo_root=tmp_path,
        lane_mode=True,
    )

    assert routed == {
        "new-run": "lanes/new",
        "rewrite-run": "lanes/rewrite",
        "i18n-new-run": "lanes/i18n-new",
        "i18n-rewrite-run": "lanes/i18n-rewrite",
    }
    assert summary["lanes"] == {
        "new": {"active": 1, "queued": 0, "processing": 0},
        "rewrite": {"active": 1, "queued": 0, "processing": 0},
        "i18n-new": {"active": 1, "queued": 0, "processing": 0},
        "i18n-rewrite": {"active": 1, "queued": 0, "processing": 0},
    }


def test_lane_mode_continues_oldest_registered_run_until_terminal(
    tmp_path: Path,
    monkeypatch,
) -> None:
    queue_root = tmp_path / "queue"
    for index, run_id in enumerate(("i18n-oldest", "i18n-next")):
        run_dir = tmp_path / "runs" / run_id
        run_dir.mkdir(parents=True)
        (run_dir / "brief.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "run_id": run_id,
                    "mode": "translate_existing",
                    "lane": "i18n-new",
                    "articles": [{"source_article_id": f"V2-NEW-{index + 1:03d}", "locale": "en"}],
                }
            ),
            encoding="utf-8",
        )
        register_run(run_dir, queue_root)
        state_path = coordinator._state_path(run_id, queue_root)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["registered_at"] = f"2026-07-25T10:0{index}:00+08:00"
        state["updated_at"] = state["registered_at"]
        state_path.write_text(json.dumps(state), encoding="utf-8")

    monkeypatch.setattr(coordinator.publisher, "legacy_article_ids", lambda _repo: set())
    advanced: list[str] = []

    def pending_tick(run_dir: Path, _queue_root: Path) -> dict[str, object]:
        advanced.append(run_dir.name)
        raise ExternalJobPending(f"job-{run_dir.name}")

    for _ in range(2):
        cycle_once(
            queue_root,
            tick=pending_tick,
            process=lambda _root: {"status": "idle"},
            repo_root=tmp_path,
            lane_mode=True,
        )

    assert advanced == ["i18n-oldest", "i18n-oldest"]


def test_new_only_cycle_advances_one_new_and_skips_non_new_lanes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    queue_root = tmp_path / "queue"
    briefs = {
        "new-run-1": {"mode": "create", "articles": []},
        "new-run-2": {"mode": "create", "articles": []},
        "rewrite-run": {
            "mode": "rewrite_existing_body",
            "articles": [{"article_id": "LEGACY-001"}],
        },
        "i18n-new-run": {
            "mode": "translate_existing",
            "lane": "i18n-new",
            "articles": [{"source_article_id": "V2-NEW-001", "locale": "en"}],
        },
        "i18n-rewrite-run": {
            "mode": "translate_existing",
            "lane": "i18n-rewrite",
            "articles": [{"source_article_id": "LEGACY-001", "locale": "ja"}],
        },
    }
    for run_id, payload in briefs.items():
        run_dir = tmp_path / "runs" / run_id
        run_dir.mkdir(parents=True)
        (run_dir / "brief.json").write_text(
            json.dumps({"schema_version": 1, "run_id": run_id, **payload}),
            encoding="utf-8",
        )
        register_run(run_dir, queue_root)
    disabled_job = queue_root / "lanes" / "rewrite" / "outbox" / "stale-rewrite.json"
    disabled_job.parent.mkdir(parents=True)
    disabled_job.write_text('{"status":"pending"}\n', encoding="utf-8")
    disabled_job_before = disabled_job.read_bytes()
    monkeypatch.setattr(coordinator.publisher, "legacy_article_ids", lambda _repo: {"LEGACY-001"})
    monkeypatch.setattr(
        coordinator,
        "seed_legacy_rewrite_runs",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("new-only must not seed rewrite")
        ),
    )
    advanced: list[str] = []
    process_calls: list[Path] = []

    def pending_tick(run_dir: Path, _job_queue_root: Path) -> dict[str, object]:
        advanced.append(run_dir.name)
        raise ExternalJobPending(f"job-{run_dir.name}")

    summary = cycle_once(
        queue_root,
        tick=pending_tick,
        process=lambda root: process_calls.append(root) or {"status": "processed"},
        repo_root=tmp_path,
        legacy_sweep=True,
        lane_mode=True,
        new_only=True,
    )

    assert advanced == ["new-run-1"]
    assert process_calls == []
    assert summary["runner"] == {"status": "idle"}
    assert summary["active"] == 2
    assert summary["runnable_active"] == 2
    assert summary["disabled_backlog"] == {
        "active": 3,
        "queued": 1,
        "processing": 0,
        "lanes": {
            "rewrite": {"active": 1, "queued": 1, "processing": 0},
            "i18n-new": {"active": 1, "queued": 0, "processing": 0},
            "i18n-rewrite": {"active": 1, "queued": 0, "processing": 0},
        },
    }
    assert disabled_job.read_bytes() == disabled_job_before
    assert summary["legacy_sweep"] == {
        "status": "disabled_by_new_only",
        "created": 0,
        "created_run_ids": [],
    }


def test_lane_mode_migrates_shared_pending_jobs_by_run_namespace(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    run_dir = tmp_path / "runs" / "new-run"
    _write_brief(run_dir, "new-run")
    state = register_run(run_dir, queue_root)
    namespace = coordinator._state_path(str(state["run_id"]), queue_root).stem
    request = create_external_request(
        queue_root,
        namespace=namespace,
        role="writer",
        model="gemini-test-writer",
        prompt="公開新文 prompt",
        response_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
        },
    )

    result = coordinator._migrate_pending_jobs(queue_root, [state], set())

    assert result == {"new": 1, "rewrite": 0, "i18n-new": 0, "i18n-rewrite": 0}
    assert not (queue_root / "outbox" / f"{request['job_id']}.json").exists()
    assert (queue_root / "lanes/new/outbox" / f"{request['job_id']}.json").exists()


def test_lane_mode_keeps_missing_brief_state_unroutable_without_blocking_migration(
    tmp_path: Path,
) -> None:
    queue_root = tmp_path / "queue"
    good_run_dir = tmp_path / "runs" / "new-run"
    _write_brief(good_run_dir, "new-run")
    good_state = register_run(good_run_dir, queue_root)
    missing_run_dir = tmp_path / "runs" / "missing-brief-run"
    missing_run_dir.mkdir(parents=True)
    missing_state = {
        "schema_version": 1,
        "run_id": "missing-brief-run",
        "run_dir": str(missing_run_dir.resolve()),
        "status": "active",
        "registered_at": "2026-08-18T10:00:00+08:00",
        "updated_at": "2026-08-18T10:00:00+08:00",
    }
    coordinator.atomic_write_json(
        coordinator._state_path("missing-brief-run", queue_root),
        missing_state,
    )
    good_request = create_external_request(
        queue_root,
        namespace=coordinator._state_path("new-run", queue_root).stem,
        role="writer",
        model="gemini-test-writer",
        prompt="公開新文 prompt",
        response_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
    )
    missing_request = create_external_request(
        queue_root,
        namespace=coordinator._state_path("missing-brief-run", queue_root).stem,
        role="writer",
        model="gemini-test-writer",
        prompt="缺 brief prompt",
        response_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
    )

    result = coordinator._migrate_pending_jobs(
        queue_root,
        [missing_state, good_state],
        set(),
    )

    assert result == {"new": 1, "rewrite": 0, "i18n-new": 0, "i18n-rewrite": 0}
    assert (queue_root / "lanes/new/outbox" / f"{good_request['job_id']}.json").exists()
    assert (queue_root / "outbox" / f"{missing_request['job_id']}.json").exists()


def test_lane_migration_write_failure_is_not_silently_unroutable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_root = tmp_path / "queue"
    run_dir = tmp_path / "runs" / "legacy-new-run"
    run_dir.mkdir(parents=True)
    (run_dir / "brief.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_id": "legacy-new-run",
                "mode": "create",
                "articles": [],
            }
        ),
        encoding="utf-8",
    )
    state = {
        "schema_version": 1,
        "run_id": "legacy-new-run",
        "run_dir": str(run_dir.resolve()),
        "status": "active",
        "registered_at": "2026-08-18T10:00:00+08:00",
        "updated_at": "2026-08-18T10:00:00+08:00",
    }
    monkeypatch.setattr(
        coordinator,
        "_write_state",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("state root is read-only")),
    )

    with pytest.raises(OSError, match="state root is read-only"):
        coordinator._lane_for_state_or_none(state, set(), queue_root)


def test_lane_mode_cycle_blocks_unroutable_missing_brief_state_before_advancing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_root = tmp_path / "queue"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    good_run_dir = tmp_path / "runs" / "new-run"
    _write_brief(good_run_dir, "new-run")
    register_run(good_run_dir, queue_root)
    missing_run_dir = tmp_path / "runs" / "missing-brief-run"
    missing_run_dir.mkdir(parents=True)
    coordinator.atomic_write_json(
        coordinator._state_path("missing-brief-run", queue_root),
        {
            "schema_version": 1,
            "run_id": "missing-brief-run",
            "run_dir": str(missing_run_dir.resolve()),
            "status": "active",
            "registered_at": "2026-08-18T10:00:00+08:00",
            "updated_at": "2026-08-18T10:00:00+08:00",
        },
    )
    monkeypatch.setattr(coordinator.publisher, "legacy_article_ids", lambda _repo: set())
    advanced: list[str] = []

    def pending_tick(run_dir: Path, _job_queue_root: Path) -> dict[str, object]:
        advanced.append(run_dir.name)
        raise ExternalJobPending(f"job-{run_dir.name}")

    summary = cycle_once(
        queue_root,
        tick=pending_tick,
        process=lambda _root: {"status": "idle"},
        repo_root=repo_root,
        lane_mode=True,
    )

    assert advanced == []
    assert summary == {
        "status": "blocked",
        "reason": "active run registry is dangling",
        "run_id": "missing-brief-run",
        "active": 2,
        "complete": 0,
        "failed": 0,
        "runner": {"status": "idle"},
        "new_matrix_sweep": None,
        "legacy_sweep": None,
    }
    assert read_run_state(good_run_dir, queue_root)["status"] == "active"
    assert json.loads(
        coordinator._state_path("missing-brief-run", queue_root).read_text(encoding="utf-8")
    )["status"] == "active"


def test_lane_for_state_uses_immutable_state_over_brief_and_rejects_bad_routing(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "runs" / "rewrite-run"
    queue_root = tmp_path / "queue"
    run_dir.mkdir(parents=True)
    (run_dir / "brief.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_id": "rewrite-run",
                "mode": "rewrite_existing_body",
                "articles": [{"article_id": "LEGACY-001"}],
            }
        ),
        encoding="utf-8",
    )
    state = {
        "schema_version": 1,
        "routing_schema_version": 1,
        "run_id": "rewrite-run",
        "run_dir": str(run_dir.resolve()),
        "status": "active",
        "mode": "create",
        "lane": "new",
        "registered_at": "2026-08-18T10:00:00+08:00",
        "updated_at": "2026-08-18T10:00:00+08:00",
    }

    assert coordinator._lane_for_state(state, {"LEGACY-001"}) == "new"

    with pytest.raises(ValueError, match="invalid active run routing"):
        coordinator._lane_for_state({**state, "lane": "rewrite"}, {"LEGACY-001"})
    with pytest.raises(ValueError, match="unknown active run routing schema"):
        coordinator._lane_for_state({**state, "routing_schema_version": 999}, {"LEGACY-001"})
    with pytest.raises(ValueError, match="invalid active run routing"):
        coordinator._lane_for_state({**state, "lane": "bogus"}, {"LEGACY-001"})


def test_cycle_marks_run_failed_without_retrying_external_job(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "run-001"
    queue_root = tmp_path / "queue"
    _write_brief(run_dir)
    register_run(run_dir, queue_root)

    def fail_tick(_run_dir: Path, _queue_root: Path) -> dict[str, object]:
        raise ValueError("invalid candidate")

    summary = cycle_once(queue_root, tick=fail_tick, process=lambda _root: {"status": "idle"})
    state = read_run_state(run_dir, queue_root)

    assert summary["failed"] == 1
    assert state["status"] == "failed"
    assert state["error_type"] == "ValueError"
    assert "invalid candidate" not in state


def test_seed_failed_translation_replacements_is_bounded_per_i18n_lane(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_root = tmp_path / "queue"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    failed_states = []
    for run_id, article_id in [
        ("i18n-new-base", "NEW-001"),
        ("i18n-new-later", "NEW-002"),
        ("i18n-rewrite-base", "LEGACY-001"),
        ("i18n-rewrite-later", "LEGACY-002"),
    ]:
        run_dir = queue_root / "translation-runs" / run_id
        run_dir.mkdir(parents=True)
        (run_dir / "brief.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "run_id": run_id,
                    "mode": "translate_existing",
                    "articles": [{"source_article_id": article_id}],
                }
            ),
            encoding="utf-8",
        )
        state = {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(run_dir.resolve()),
            "status": "failed",
            "error_type": "LocalePlanValidationError",
            "registered_at": f"2026-07-31T10:0{len(failed_states)}:00+08:00",
            "updated_at": f"2026-07-31T10:0{len(failed_states)}:00+08:00",
        }
        coordinator.atomic_write_json(
            coordinator._state_path(run_id, queue_root),
            state,
        )
        failed_states.append(state)

    calls: list[tuple[str, str]] = []

    def fake_enqueue(
        _repo_root: Path,
        selected_queue_root: Path,
        *,
        terminal_state: dict[str, object],
        recovery_reason: str,
    ) -> dict[str, str]:
        base_run_id = str(terminal_state["run_id"])
        replacement_run_id = f"{base_run_id}-replacement-01"
        calls.append((base_run_id, recovery_reason))
        replacement_run_dir = (
            selected_queue_root / "translation-runs" / replacement_run_id
        ).resolve()
        replacement_run_dir.mkdir(parents=True)
        base_brief = json.loads(
            (Path(str(terminal_state["run_dir"])) / "brief.json").read_text()
        )
        (replacement_run_dir / "brief.json").write_text(
            json.dumps({**base_brief, "run_id": replacement_run_id}),
            encoding="utf-8",
        )
        coordinator.atomic_write_json(
            coordinator._state_path(replacement_run_id, selected_queue_root),
            {
                "schema_version": 1,
                "run_id": replacement_run_id,
                "run_dir": str(replacement_run_dir),
                "status": "active",
                "replacement_of": base_run_id,
                "replacement_reason": recovery_reason,
            },
        )
        return {
            "run_id": replacement_run_id,
            "run_dir": str(replacement_run_dir),
            "state_path": str(
                coordinator._state_path(replacement_run_id, selected_queue_root)
            ),
        }

    monkeypatch.setattr(
        coordinator.multilingual,
        "enqueue_translation_replacement",
        fake_enqueue,
    )

    first = coordinator.seed_failed_translation_replacements(
        repo_root,
        queue_root,
        legacy_article_ids={"LEGACY-001", "LEGACY-002"},
    )
    second = coordinator.seed_failed_translation_replacements(
        repo_root,
        queue_root,
        legacy_article_ids={"LEGACY-001", "LEGACY-002"},
    )

    assert first == {
        "status": "seeded",
        "created": 2,
        "created_run_ids": [
            "i18n-new-base-replacement-01",
            "i18n-rewrite-base-replacement-01",
        ],
    }
    assert second == {
        "status": "idle",
        "created": 0,
        "created_run_ids": [],
    }
    assert calls == [
        ("i18n-new-base", "LOCALE_PLAN_VALIDATION"),
        ("i18n-rewrite-base", "LOCALE_PLAN_VALIDATION"),
    ]


def test_seed_failed_translation_replacements_persists_legacy_routing_before_enqueue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_root = tmp_path / "queue"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    run_id = "failed-legacy-translation"
    run_dir = queue_root / "translation-runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "brief.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_id": run_id,
                "mode": "translate_existing",
                "articles": [{"source_article_id": "LEGACY-001"}],
            }
        ),
        encoding="utf-8",
    )
    state = {
        "schema_version": 1,
        "run_id": run_id,
        "run_dir": str(run_dir.resolve()),
        "status": "failed",
        "error_type": "LocalePlanValidationError",
        "registered_at": "2026-08-18T10:00:00+08:00",
        "updated_at": "2026-08-18T10:00:00+08:00",
    }
    coordinator.atomic_write_json(coordinator._state_path(run_id, queue_root), state)
    seen_terminal_states: list[dict[str, object]] = []

    def fake_enqueue(
        _repo_root: Path,
        _queue_root: Path,
        *,
        terminal_state: dict[str, object],
        recovery_reason: str,
    ) -> dict[str, object]:
        seen_terminal_states.append(dict(terminal_state))
        assert recovery_reason == "LOCALE_PLAN_VALIDATION"
        return {"run_id": f"{terminal_state['run_id']}-replacement-01"}

    monkeypatch.setattr(
        coordinator.multilingual,
        "enqueue_translation_replacement",
        fake_enqueue,
    )

    summary = coordinator.seed_failed_translation_replacements(
        repo_root,
        queue_root,
        legacy_article_ids={"LEGACY-001"},
    )

    persisted = json.loads(
        coordinator._state_path(run_id, queue_root).read_text(encoding="utf-8")
    )
    assert summary["created_run_ids"] == [f"{run_id}-replacement-01"]
    assert seen_terminal_states[0]["routing_schema_version"] == 1
    assert seen_terminal_states[0]["lane"] == "i18n-rewrite"
    assert persisted["routing_schema_version"] == 1
    assert persisted["mode"] == "translate_existing"
    assert persisted["lane"] == "i18n-rewrite"
    assert coordinator._lane_for_state(persisted, set(), queue_root) == "i18n-rewrite"


def test_lane_cycle_reports_bounded_translation_replacement_seeding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_root = tmp_path / "queue"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    calls = 0

    monkeypatch.setattr(
        coordinator.publisher,
        "legacy_article_ids",
        lambda _repo_root: {"LEGACY-001"},
    )

    def fake_seed(
        selected_repo_root: Path,
        selected_queue_root: Path,
        *,
        legacy_article_ids: set[str],
    ) -> dict[str, object]:
        nonlocal calls
        calls += 1
        assert selected_repo_root == repo_root.resolve()
        assert selected_queue_root == queue_root.resolve()
        assert legacy_article_ids == {"LEGACY-001"}
        return {
            "status": "seeded",
            "created": 1,
            "created_run_ids": ["i18n-new-base-replacement-01"],
        }

    monkeypatch.setattr(
        coordinator,
        "seed_failed_translation_replacements",
        fake_seed,
    )

    summary = cycle_once(
        queue_root,
        repo_root=repo_root,
        lane_mode=True,
        tick=lambda *_args: {"status": "complete"},
        process=lambda _root: {"status": "idle"},
    )

    assert calls == 1
    assert summary["translation_replacements"] == {
        "status": "seeded",
        "created": 1,
        "created_run_ids": ["i18n-new-base-replacement-01"],
    }


def test_failed_translation_replacement_skip_is_persisted_without_log_loop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_root = tmp_path / "queue"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    run_id = "i18n-new-source-drift"
    run_dir = queue_root / "translation-runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "brief.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_id": run_id,
                "mode": "translate_existing",
                "articles": [{"source_article_id": "NEW-001"}],
            }
        ),
        encoding="utf-8",
    )
    coordinator.atomic_write_json(
        coordinator._state_path(run_id, queue_root),
        {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(run_dir.resolve()),
            "status": "failed",
            "error_type": "LocalePlanValidationError",
            "registered_at": "2026-07-31T10:00:00+08:00",
            "updated_at": "2026-07-31T10:00:00+08:00",
        },
    )
    calls = 0

    def fail_source_drift(*_args: object, **_kwargs: object) -> dict[str, str]:
        nonlocal calls
        calls += 1
        raise ValueError("translation replacement source drift")

    monkeypatch.setattr(
        coordinator.multilingual,
        "enqueue_translation_replacement",
        fail_source_drift,
    )

    first = coordinator.seed_failed_translation_replacements(
        repo_root,
        queue_root,
        legacy_article_ids=set(),
    )
    second = coordinator.seed_failed_translation_replacements(
        repo_root,
        queue_root,
        legacy_article_ids=set(),
    )

    assert first == {
        "status": "idle",
        "created": 0,
        "created_run_ids": [],
        "skipped": [{"run_id": run_id, "reason": "SOURCE_DRIFT"}],
    }
    assert second == {
        "status": "idle",
        "created": 0,
        "created_run_ids": [],
    }
    assert calls == 1
    decision = json.loads(
        coordinator._translation_replacement_decision_path(
            queue_root,
            run_id,
        ).read_text()
    )
    assert decision["run_id"] == run_id
    assert decision["status"] == "skipped"
    assert decision["reason"] == "SOURCE_DRIFT"


@pytest.mark.parametrize(
    ("error_type", "failure_category", "transport_attempts", "expected"),
    [
        ("LocalePlanValidationError", None, None, "LOCALE_PLAN_VALIDATION"),
        ("GeminiApiFailure", "NETWORK", 3, "NETWORK"),
        ("V4BrokerFailure", "SCHEMA_INVALID_PAYLOAD", 3, "SCHEMA_INVALID_PAYLOAD"),
        ("GeminiApiFailure", "PROVIDER_UNAVAILABLE", 3, "PROVIDER_UNAVAILABLE"),
        ("GeminiApiFailure", "NETWORK", 2, None),
        ("GeminiApiFailure", "AUTH", 3, None),
        ("GeminiApiFailure", "QUOTA", 3, None),
        ("CandidateValidationError", None, None, None),
    ],
)
def test_translation_replacement_reason_is_closed_and_requires_exhaustion(
    tmp_path: Path,
    error_type: str,
    failure_category: str | None,
    transport_attempts: int | None,
    expected: str | None,
) -> None:
    state: dict[str, object] = {
        "status": "failed",
        "run_id": "translation-base",
        "error_type": error_type,
    }
    if failure_category is not None:
        state["failure_category"] = failure_category
    if transport_attempts is not None:
        state["transport_attempts"] = transport_attempts

    assert coordinator._translation_replacement_reason(tmp_path, state) == expected


def _exact_translation_replacement_fixture(
    tmp_path: Path,
) -> tuple[Path, Path, Path, dict[str, object], dict[str, object]]:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    queue_root = tmp_path / "queue"
    run_id = "translation-terminal-en"
    run_dir = queue_root / "translation-runs" / run_id
    run_dir.mkdir(parents=True)
    source = {"article_id": "LEGACY-001", "canonical_path": "/articles/astrology/legacy-001", "title": "Source title", "description": "Source description", "answer": "Source answer", "tags": ["source"], "faq": [{"question": "Question?", "answer": "Answer."}], "bodySections": [{"heading": "Heading", "paragraphs": ["Paragraph."]}]}
    brief = {
        "schema_version": 1,
        "run_id": run_id,
        "mode": "translate_existing", "lane": "i18n-rewrite",
        "articles": [{
            "translation_id": "LEGACY-001:en",
            "locale": "en",
            "source_article_id": "LEGACY-001",
            "source_path": source["canonical_path"],
            "source_sha256": coordinator.multilingual.source_sha256(source),
            "source": source,
        }],
    }
    coordinator.atomic_write_json(run_dir / "brief.json", brief)
    state = {"schema_version": 1, "run_id": run_id, "run_dir": str(run_dir.resolve()), "status": "failed", "error_type": "LocalePlanValidationError", "routing_schema_version": 1, "mode": "translate_existing", "lane": "i18n-rewrite", "identity_envelope": coordinator._build_identity_envelope("translate_existing", "i18n-rewrite", ["LEGACY-001"]), "registered_at": "2026-08-30T10:00:00+08:00", "updated_at": "2026-08-30T10:00:00+08:00"}
    coordinator.atomic_write_json(coordinator._state_path(run_id, queue_root), state)
    for generation in ("01", "02"):
        coordinator.atomic_write_json(
            run_dir / "attempts" / generation / "review.json",
            {"articles": [{"verdict": "REJECT"}]},
        )
    coordinator.atomic_write_json(
        run_dir / "attempts" / "03" / "planning-result.json",
        {"schema_version": 1, "generation": 3, "transport_status": "EXTERNAL_PLAN_AVAILABLE", "planning_contract_status": "PLANNING_CONTRACT_FAILURE", "terminal_stage": "PLANNING", "terminal_reason": "locale plan rebuild reused prior outline topology for article-01"},
    )
    for lane in coordinator.CONTENT_LANES:
        coordinator.atomic_write_json(queue_root / "lanes" / lane / "protected.json", {"lane": lane})
    for locale in ("ko", "ja"):
        coordinator.atomic_write_json(queue_root / "protected-runs" / f"{locale}.json", {"locale": locale})
    coordinator.atomic_write_json(queue_root / "publisher" / "protected.json", {"status": "unchanged"})
    return repo_root, queue_root, run_dir, source, state


def _exact_translation_replacement_cli(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    repo_root: Path,
    queue_root: Path,
    run_dir: Path,
    state: dict[str, object],
    mode: str,
) -> tuple[int, dict[str, object]]:
    monkeypatch.setattr(coordinator, "_validate_formal_runtime", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(sys, "argv", [
        "agy_gemini_coordinator", "--queue-root", str(queue_root), "--repo-root", str(repo_root),
        "replace-failed-translation-run", "--run-id", str(state["run_id"]),
        "--expected-registry-digest", coordinator._canonical_json_file_sha256(state),
        "--expected-run-dir", str(run_dir.resolve()), mode,
    ])
    return coordinator.main(), json.loads(capsys.readouterr().out)


def _production_shaped_translation_replacement_fixture(
    tmp_path: Path,
) -> tuple[Path, Path, Path, Path, Path, dict[str, object], dict[str, object]]:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    queue_root = tmp_path / "queue"
    publisher_state_root = tmp_path / "publisher-state"
    publisher_state_root.mkdir()
    source_run_id = "auto-i18n-en-aa637e1bf05d3ad21429"
    target_run_id = f"{source_run_id}-replacement-01"
    source_run_dir = queue_root / "translation-runs" / source_run_id
    target_run_dir = queue_root / "translation-runs" / target_run_id
    source_run_dir.mkdir(parents=True)
    target_run_dir.mkdir(parents=True)
    source = {"article_id": "ASTRO-BASE-03", "canonical_path": "/articles/astrology/astro-base-03", "title": "Source title", "description": "Source description", "answer": "Source answer", "tags": ["source"], "faq": [{"question": "Question?", "answer": "Answer."}], "bodySections": [{"heading": "Heading", "paragraphs": ["Paragraph."]}]}
    brief = {
        "schema_version": 1,
        "run_id": target_run_id,
        "mode": "translate_existing",
        "articles": [{
            "translation_id": "ASTRO-BASE-03:en",
            "locale": "en",
            "source_article_id": "ASTRO-BASE-03",
            "source_path": source["canonical_path"],
            "source_sha256": coordinator.multilingual.source_sha256(source),
            "source": source,
        }],
    }
    coordinator.atomic_write_json(target_run_dir / "brief.json", brief)
    root_candidate = {"run_id": target_run_id, "status": "complete"}
    root_review = {"run_id": target_run_id, "status": "complete"}
    coordinator.atomic_write_json(target_run_dir / "candidate.json", root_candidate)
    coordinator.atomic_write_json(target_run_dir / "review.json", root_review)
    attempt_files = {
        "article-operation.json",
        "candidate.json",
        "deterministic-findings.json",
        "external-candidate.json",
        "external-plan.json",
        "external-review.json",
        "locale-plan.json",
        "plan-operation.json",
        "planning-result.json",
        "review.json",
        "reviewer-operation.json",
    }
    for generation in ("01", "02", "03"):
        for name in attempt_files:
            payload: dict[str, object] = {"generation": int(generation), "name": name}
            if generation == "03" and name == "candidate.json":
                payload = root_candidate
            elif generation == "03" and name == "review.json":
                payload = root_review
            coordinator.atomic_write_json(target_run_dir / "attempts" / generation / name, payload)
    (target_run_dir / "continuation").mkdir()
    source_state = {
        "schema_version": 1,
        "run_id": source_run_id,
        "run_dir": str(source_run_dir.resolve()),
        "status": "failed",
        "error_type": "LocalePlanValidationError",
        "routing_schema_version": coordinator.ROUTING_SCHEMA_VERSION,
        "mode": "translate_existing",
        "lane": "i18n-rewrite",
        "identity_envelope": coordinator._build_identity_envelope("translate_existing", "i18n-rewrite", ["ASTRO-BASE-03"]),
        "registered_at": "2026-08-30T10:00:00+08:00",
        "updated_at": "2026-08-30T10:00:00+08:00",
    }
    target_state = {
        "schema_version": 1,
        "run_id": target_run_id,
        "run_dir": str(target_run_dir.resolve()),
        "status": "complete",
        "registered_at": "2026-08-30T10:01:00+08:00",
        "updated_at": "2026-08-30T10:02:00+08:00",
        "replacement_of": source_run_id,
        "replacement_reason": "LOCALE_PLAN_VALIDATION",
        "routing_schema_version": coordinator.ROUTING_SCHEMA_VERSION,
        "mode": "translate_existing",
        "lane": "i18n-rewrite",
        "last_job_id": "job-aa637e1b",
        "result": {
            "approved_by_reviewer": 0,
            "candidate": str(target_run_dir / "candidate.json"),
            "review": str(target_run_dir / "review.md"),
            "run_id": target_run_id,
            "status": "complete",
        },
    }
    coordinator.atomic_write_json(coordinator._state_path(source_run_id, queue_root), source_state)
    target_state_path = coordinator._state_path(target_run_id, queue_root)
    coordinator.atomic_write_json(target_state_path, target_state)
    assert str(target_state_path.relative_to(queue_root)) == "runs/1bf0bbc61ff8d10e808f6923.json"
    return repo_root, queue_root, publisher_state_root, source_run_dir, target_run_dir, source_state, target_state


def _reconcile_translation_replacement_cli(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    repo_root: Path,
    queue_root: Path,
    publisher_state_root: Path,
    target_run_dir: Path,
    source_state: dict[str, object],
    target_state: dict[str, object],
    mode: str,
) -> tuple[int, dict[str, object]]:
    monkeypatch.setattr(coordinator, "_validate_formal_runtime", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(sys, "argv", [
        "agy_gemini_coordinator", "--queue-root", str(queue_root), "--repo-root", str(repo_root),
        "reconcile-translation-replacement-identity",
        "--source-run-id", str(source_state["run_id"]),
        "--target-run-id", str(target_state["run_id"]),
        "--target-registry-relative-path", "runs/1bf0bbc61ff8d10e808f6923.json",
        "--expected-target-registry-digest", coordinator._canonical_json_file_sha256(target_state),
        "--expected-target-run-dir", str(target_run_dir.resolve()),
        "--publisher-state-root", str(publisher_state_root),
        "--article-id", "ASTRO-BASE-03",
        "--lane", "i18n-rewrite",
        "--reason", "LOCALE_PLAN_VALIDATION",
        mode,
    ])
    return coordinator.main(), json.loads(capsys.readouterr().out)


def test_reconcile_translation_replacement_identity_plan_only_accepts_production_shape_without_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root, queue_root, publisher_state_root, _source_run_dir, target_run_dir, source_state, target_state = _production_shaped_translation_replacement_fixture(tmp_path)
    before = _file_snapshot(tmp_path)

    returncode, receipt = _reconcile_translation_replacement_cli(
        monkeypatch, capsys, repo_root, queue_root, publisher_state_root, target_run_dir, source_state, target_state, "--plan-only"
    )

    assert returncode == 0
    assert receipt["status"] == "plan_only"
    assert receipt["missing_fields"] == ["identity_envelope"]
    assert receipt["planned_mutation_count"] == 0
    assert receipt["expected_write_set"] == [
        str(coordinator._run_identity_lock_path(str(target_state["run_id"]), queue_root).relative_to(queue_root)),
        "translation-replacement-identity-reconciliations/auto-i18n-en-aa637e1bf05d3ad21429-replacement-01.json",
        "runs/1bf0bbc61ff8d10e808f6923.json",
    ]
    assert _file_snapshot(tmp_path) == before


def test_reconcile_translation_replacement_identity_accepts_matching_brief_lane(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root, queue_root, publisher_state_root, _source_run_dir, target_run_dir, source_state, target_state = _production_shaped_translation_replacement_fixture(tmp_path)
    brief_path = target_run_dir / "brief.json"
    coordinator.atomic_write_json(brief_path, {**json.loads(brief_path.read_text()), "lane": "i18n-rewrite"})
    before = _file_snapshot(tmp_path)

    returncode, receipt = _reconcile_translation_replacement_cli(
        monkeypatch, capsys, repo_root, queue_root, publisher_state_root, target_run_dir, source_state, target_state, "--plan-only"
    )

    assert returncode == 0
    assert receipt["status"] == "plan_only"
    assert _file_snapshot(tmp_path) == before


def test_reconcile_translation_replacement_identity_execute_only_adds_identity_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root, queue_root, publisher_state_root, _source_run_dir, target_run_dir, source_state, target_state = _production_shaped_translation_replacement_fixture(tmp_path)
    target_state_path = coordinator._state_path(str(target_state["run_id"]), queue_root)
    before_all = _file_snapshot(tmp_path)
    before_tree = _file_snapshot(target_run_dir)
    before_registry = json.loads(target_state_path.read_text())

    returncode, receipt = _reconcile_translation_replacement_cli(
        monkeypatch, capsys, repo_root, queue_root, publisher_state_root, target_run_dir, source_state, target_state, "--execute"
    )

    after_registry = json.loads(target_state_path.read_text())
    expected_identity = coordinator._build_identity_envelope("translate_existing", "i18n-rewrite", ["ASTRO-BASE-03"])
    receipt_path = queue_root / str(receipt["receipt"])
    lock_path = coordinator._run_identity_lock_path(str(target_state["run_id"]), queue_root)
    persisted_receipt = json.loads(receipt_path.read_text())
    assert returncode == 0
    assert receipt["status"] == "reconciled"
    assert after_registry == {**before_registry, "identity_envelope": expected_identity}
    assert {key: after_registry[key] for key in before_registry} == before_registry
    assert _file_snapshot(target_run_dir) == before_tree
    changed = {path for path, before in before_all.items() if _file_snapshot(tmp_path).get(path) != before}
    added = set(_file_snapshot(tmp_path)) - set(before_all)
    assert changed == {str(target_state_path.relative_to(tmp_path))}
    assert added == {str(lock_path.relative_to(tmp_path)), str(receipt_path.relative_to(tmp_path))}
    assert persisted_receipt["status"] == "RECONCILED"
    assert persisted_receipt["before_digest"] == coordinator._canonical_json_file_sha256(before_registry)
    assert persisted_receipt["after_digest"] == coordinator._canonical_json_file_sha256(after_registry)
    assert persisted_receipt["expected_before_digest"] == persisted_receipt["before_digest"]
    assert persisted_receipt["expected_after_digest"] == persisted_receipt["after_digest"]


def test_reconcile_translation_replacement_identity_receipt_replay_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root, queue_root, publisher_state_root, _source_run_dir, target_run_dir, source_state, target_state = _production_shaped_translation_replacement_fixture(tmp_path)
    plan = coordinator.reconcile_translation_replacement_identity(
        queue_root,
        source_run_id=str(source_state["run_id"]),
        target_run_id=str(target_state["run_id"]),
        target_registry_relative_path="runs/1bf0bbc61ff8d10e808f6923.json",
        expected_target_registry_digest=coordinator._canonical_json_file_sha256(target_state),
        expected_target_run_dir=target_run_dir,
        publisher_state_root=publisher_state_root,
        article_id="ASTRO-BASE-03",
        lane="i18n-rewrite",
        reason="LOCALE_PLAN_VALIDATION",
        execute=False,
    )
    receipt_path = queue_root / str(plan["receipt"])
    before_state = json.loads(coordinator._state_path(str(target_state["run_id"]), queue_root).read_text())
    after_state = {**before_state, "identity_envelope": plan["expected_identity_envelope"]}
    coordinator.atomic_write_json(receipt_path, {**plan, "status": "PREPARED", "before": before_state, "after": after_state})

    completed_code, completed = _reconcile_translation_replacement_cli(
        monkeypatch, capsys, repo_root, queue_root, publisher_state_root, target_run_dir, source_state, target_state, "--execute"
    )
    replay_code, replay = _reconcile_translation_replacement_cli(
        monkeypatch, capsys, repo_root, queue_root, publisher_state_root, target_run_dir, source_state, target_state, "--execute"
    )

    assert completed_code == replay_code == 0
    assert completed["status"] == "reconciled"
    assert replay["status"] == "already_reconciled"
    coordinator.atomic_write_json(receipt_path, {**plan, "status": "PREPARED", "before": before_state, "after": {**after_state, "lane": "i18n-new"}})
    fail_code, rejected = _reconcile_translation_replacement_cli(
        monkeypatch, capsys, repo_root, queue_root, publisher_state_root, target_run_dir, source_state, target_state, "--execute"
    )
    assert fail_code == 1
    assert rejected["status"] == "rejected"


def test_reconcile_translation_replacement_identity_rejects_registry_clobber_after_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root, queue_root, publisher_state_root, _source_run_dir, target_run_dir, source_state, target_state = _production_shaped_translation_replacement_fixture(tmp_path)
    target_state_path = coordinator._state_path(str(target_state["run_id"]), queue_root)
    receipt_path = queue_root / "translation-replacement-identity-reconciliations" / f"{target_state['run_id']}.json"
    original_write_exclusive = coordinator._write_json_exclusive

    def write_receipt_then_clobber(path: Path, payload: object) -> None:
        original_write_exclusive(path, payload)
        if path == receipt_path:
            coordinator.atomic_write_json(target_state_path, {**target_state, "status": "active"})

    monkeypatch.setattr(coordinator, "_write_json_exclusive", write_receipt_then_clobber)

    returncode, receipt = _reconcile_translation_replacement_cli(
        monkeypatch, capsys, repo_root, queue_root, publisher_state_root, target_run_dir, source_state, target_state, "--execute"
    )

    persisted_state = json.loads(target_state_path.read_text())
    assert returncode == 1
    assert receipt["status"] == "rejected"
    assert persisted_state["status"] == "active"
    assert "identity_envelope" not in persisted_state


@pytest.mark.parametrize(
    "failure",
    [
        "duplicate-target", "target-status", "conflicting-envelope", "wrong-lane", "wrong-digest",
        "routing-drift", "replacement-of", "result-candidate", "last-job", "attempt04",
        "replacement02", "publish-transaction", "publisher-ledger", "result-review", "run-symlink",
        "candidate-mirror-drift", "review-mirror-drift", "extra-result-target", "root-review-md",
        "already-identity-wrong-digest", "external-run-dir", "brief-wrong-lane", "brief-wrong-mode",
        "brief-wrong-article", "brief-multiple-articles", "brief-missing-articles", "registry-cli-lane-mismatch",
        "brief-translation-id-mismatch", "brief-locale-missing", "brief-source-article-mismatch",
        "brief-source-sha-mismatch", "brief-source-path-mismatch",
    ],
)
def test_reconcile_translation_replacement_identity_negative_matrix_has_zero_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: str,
) -> None:
    repo_root, queue_root, publisher_state_root, _source_run_dir, target_run_dir, source_state, target_state = _production_shaped_translation_replacement_fixture(tmp_path)
    target_state_path = coordinator._state_path(str(target_state["run_id"]), queue_root)
    if failure == "duplicate-target":
        coordinator.atomic_write_json(queue_root / "runs" / "duplicate.json", target_state)
    elif failure == "target-status":
        target_state["status"] = "active"; coordinator.atomic_write_json(target_state_path, target_state)
    elif failure == "conflicting-envelope":
        target_state["identity_envelope"] = coordinator._build_identity_envelope("translate_existing", "i18n-new", ["ASTRO-BASE-03"]); coordinator.atomic_write_json(target_state_path, target_state)
    elif failure == "wrong-lane":
        target_state["lane"] = "i18n-new"; coordinator.atomic_write_json(target_state_path, target_state)
    elif failure == "wrong-digest":
        pass
    elif failure == "routing-drift":
        target_state["routing_schema_version"] = 0; coordinator.atomic_write_json(target_state_path, target_state)
    elif failure == "replacement-of":
        target_state["replacement_of"] = "other-source"; coordinator.atomic_write_json(target_state_path, target_state)
    elif failure == "result-candidate":
        target_state["result"] = {**target_state["result"], "candidate": str(target_run_dir / "other.json")}; coordinator.atomic_write_json(target_state_path, target_state)
    elif failure == "result-review":
        target_state["result"] = {**target_state["result"], "review": str(target_run_dir / "other.md")}; coordinator.atomic_write_json(target_state_path, target_state)
    elif failure == "extra-result-target":
        target_state["result"] = {**target_state["result"], "target": "ASTRO-BASE-03"}; coordinator.atomic_write_json(target_state_path, target_state)
    elif failure == "last-job":
        target_state["last_job_id"] = ""; coordinator.atomic_write_json(target_state_path, target_state)
    elif failure == "attempt04":
        coordinator.atomic_write_json(target_run_dir / "attempts" / "04" / "planning-result.json", {"generation": 4})
    elif failure == "replacement02":
        coordinator.atomic_write_json(target_run_dir / "auto-i18n-en-aa637e1bf05d3ad21429-replacement-02.json", {"status": "forbidden"})
    elif failure == "publish-transaction":
        coordinator.atomic_write_json(target_run_dir / "publish-transaction.json", {"status": "forbidden"})
    elif failure == "publisher-ledger":
        coordinator.atomic_write_json(publisher_state_root / "ledger.json", {"run_id": target_state["run_id"]})
    elif failure == "run-symlink":
        target_run_dir.rename(tmp_path / "target-real")
        target_run_dir.symlink_to(tmp_path / "target-real", target_is_directory=True)
    elif failure == "candidate-mirror-drift":
        coordinator.atomic_write_json(target_run_dir / "candidate.json", {"run_id": target_state["run_id"], "status": "drift"})
    elif failure == "review-mirror-drift":
        coordinator.atomic_write_json(target_run_dir / "review.json", {"run_id": target_state["run_id"], "status": "drift"})
    elif failure == "root-review-md":
        (target_run_dir / "review.md").write_text("forbidden root file\n", encoding="utf-8")
    elif failure == "already-identity-wrong-digest":
        target_state["identity_envelope"] = coordinator._build_identity_envelope("translate_existing", "i18n-rewrite", ["ASTRO-BASE-03"])
        coordinator.atomic_write_json(target_state_path, target_state)
    elif failure == "external-run-dir":
        external_run_dir = tmp_path / "external-translation-runs" / str(target_state["run_id"])
        external_run_dir.parent.mkdir()
        target_run_dir.rename(external_run_dir)
        target_run_dir = external_run_dir
        target_state["run_dir"] = str(target_run_dir.resolve())
        target_state["result"] = {
            **target_state["result"],
            "candidate": str(target_run_dir / "candidate.json"),
            "review": str(target_run_dir / "review.md"),
        }
        coordinator.atomic_write_json(target_state_path, target_state)
    elif failure == "brief-wrong-lane":
        brief_path = target_run_dir / "brief.json"
        coordinator.atomic_write_json(brief_path, {**json.loads(brief_path.read_text()), "lane": "i18n-new"})
    elif failure == "brief-wrong-mode":
        brief_path = target_run_dir / "brief.json"
        coordinator.atomic_write_json(brief_path, {**json.loads(brief_path.read_text()), "mode": "create"})
    elif failure == "brief-wrong-article":
        brief_path = target_run_dir / "brief.json"
        brief = json.loads(brief_path.read_text())
        brief["articles"][0]["source_article_id"] = "ASTRO-BASE-04"
        coordinator.atomic_write_json(brief_path, brief)
    elif failure == "brief-multiple-articles":
        brief_path = target_run_dir / "brief.json"
        brief = json.loads(brief_path.read_text())
        brief["articles"].append({**brief["articles"][0], "source_article_id": "ASTRO-BASE-04"})
        coordinator.atomic_write_json(brief_path, brief)
    elif failure == "brief-missing-articles":
        brief_path = target_run_dir / "brief.json"
        coordinator.atomic_write_json(brief_path, {key: value for key, value in json.loads(brief_path.read_text()).items() if key != "articles"})
    elif failure == "brief-translation-id-mismatch":
        brief_path = target_run_dir / "brief.json"
        brief = json.loads(brief_path.read_text())
        brief["articles"][0]["translation_id"] = "ASTRO-BASE-03:ja"
        coordinator.atomic_write_json(brief_path, brief)
    elif failure == "brief-locale-missing":
        brief_path = target_run_dir / "brief.json"
        brief = json.loads(brief_path.read_text())
        brief["articles"][0]["locale"] = ""
        coordinator.atomic_write_json(brief_path, brief)
    elif failure == "brief-source-article-mismatch":
        brief_path = target_run_dir / "brief.json"
        brief = json.loads(brief_path.read_text())
        brief["articles"][0]["source"] = {**brief["articles"][0]["source"], "article_id": "ASTRO-BASE-04"}
        brief["articles"][0]["source_sha256"] = coordinator.multilingual.source_sha256(brief["articles"][0]["source"])
        coordinator.atomic_write_json(brief_path, brief)
    elif failure == "brief-source-sha-mismatch":
        brief_path = target_run_dir / "brief.json"
        brief = json.loads(brief_path.read_text())
        brief["articles"][0]["source_sha256"] = "0" * 64
        coordinator.atomic_write_json(brief_path, brief)
    elif failure == "brief-source-path-mismatch":
        brief_path = target_run_dir / "brief.json"
        brief = json.loads(brief_path.read_text())
        brief["articles"][0]["source_path"] = "/articles/other"
        coordinator.atomic_write_json(brief_path, brief)
    elif failure == "registry-cli-lane-mismatch":
        target_state["lane"] = "i18n-new"
        coordinator.atomic_write_json(target_state_path, target_state)
    before = _file_snapshot(tmp_path)
    if failure == "wrong-digest":
        target_state = {**target_state, "updated_at": "2026-08-30T10:03:00+08:00"}

    returncode, receipt = _reconcile_translation_replacement_cli(
        monkeypatch, capsys, repo_root, queue_root, publisher_state_root, target_run_dir, source_state, target_state, "--execute"
    )

    assert returncode == 1
    assert receipt["status"] == "rejected"
    after = _file_snapshot(tmp_path)
    lock_relative = str(coordinator._run_identity_lock_path(str(target_state["run_id"]), queue_root).relative_to(tmp_path))
    assert {path: value for path, value in after.items() if path != lock_relative} == before
    assert set(after) - set(before) <= {lock_relative}


@pytest.mark.parametrize("legacy", [False, True])
def test_exact_translation_replacement_cli_plan_only_is_zero_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], legacy: bool) -> None:
    repo_root, queue_root, run_dir, source, state = _exact_translation_replacement_fixture(tmp_path)
    if not legacy:
        coordinator.atomic_write_json(run_dir / "brief.json", {key: value for key, value in json.loads((run_dir / "brief.json").read_text()).items() if key != "lane"})
    monkeypatch.setattr(coordinator.multilingual, "load_source_article", lambda *_args: source)
    monkeypatch.setattr(coordinator.multilingual, "enqueue_translation_replacement", lambda *_args, **_kwargs: pytest.fail("enqueue invoked"))
    monkeypatch.setattr(coordinator, "cycle_once", lambda *_args, **_kwargs: pytest.fail("cycle invoked"))
    monkeypatch.setattr(coordinator, "process_once", lambda *_args, **_kwargs: pytest.fail("runner invoked"))
    before = _file_snapshot(tmp_path)
    returncode, receipt = _exact_translation_replacement_cli(
        monkeypatch, capsys, repo_root, queue_root, run_dir, state, "--plan-only"
    )
    replacement_id = f"{state['run_id']}-replacement-01"
    assert returncode == 0
    assert receipt["status"] == "plan_only"
    assert receipt["source_run_id"] == state["run_id"]
    assert receipt["replacement_run_id"] == replacement_id
    assert receipt["replacement_reason"] == "LOCALE_PLAN_VALIDATION"
    assert receipt["expected_write_set"] == [
        str((queue_root / "translation-runs" / replacement_id / "brief.json").resolve()),
        str(coordinator._state_path(replacement_id, queue_root).resolve()),
    ]
    assert receipt["runner_invoked"] is False
    assert receipt["provider_invoked"] is False
    assert receipt["publisher_invoked"] is False
    assert _file_snapshot(tmp_path) == before


def test_exact_translation_replacement_cli_execute_is_idempotent_and_does_not_advance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root, queue_root, run_dir, source, state = _exact_translation_replacement_fixture(tmp_path)
    monkeypatch.setattr(coordinator.multilingual, "load_source_article", lambda *_args: source)
    original_enqueue = coordinator.multilingual.enqueue_translation_replacement
    calls = 0
    def enqueue(*args: object, **kwargs: object) -> dict[str, str]:
        nonlocal calls
        calls += 1
        return original_enqueue(*args, **kwargs, source_loader=lambda *_args: source)
    monkeypatch.setattr(coordinator.multilingual, "enqueue_translation_replacement", enqueue)
    monkeypatch.setattr(coordinator, "cycle_once", lambda *_args, **_kwargs: pytest.fail("cycle invoked"))
    monkeypatch.setattr(coordinator, "process_once", lambda *_args, **_kwargs: pytest.fail("runner invoked"))
    source_before = (run_dir / "brief.json").read_bytes(), coordinator._state_path(str(state["run_id"]), queue_root).read_bytes()
    first_code, first = _exact_translation_replacement_cli(
        monkeypatch, capsys, repo_root, queue_root, run_dir, state, "--execute"
    )
    after_first = _file_snapshot(tmp_path)
    second_code, second = _exact_translation_replacement_cli(
        monkeypatch, capsys, repo_root, queue_root, run_dir, state, "--execute"
    )
    replacement_id = f"{state['run_id']}-replacement-01"
    replacement_dir = queue_root / "translation-runs" / replacement_id
    replacement_state = json.loads(coordinator._state_path(replacement_id, queue_root).read_text())
    assert first_code == second_code == 0
    assert first["status"] == "replacement_created"
    assert second["status"] == "already_exists"
    assert first["replacement_run_id"] == second["replacement_run_id"] == replacement_id
    assert (replacement_state["status"], set(json.loads((replacement_dir / "brief.json").read_text()))) == ("active", {"schema_version", "run_id", "mode", "articles"})
    assert replacement_state["routing_schema_version"] == coordinator.ROUTING_SCHEMA_VERSION
    assert replacement_state["mode"] == "translate_existing"
    assert replacement_state["lane"] == "i18n-rewrite"
    assert replacement_state["identity_envelope"] == coordinator._build_identity_envelope("translate_existing", "i18n-rewrite", ["LEGACY-001"])
    assert replacement_state["replacement_of"] == state["run_id"]
    assert replacement_state["replacement_reason"] == "LOCALE_PLAN_VALIDATION"
    assert not (replacement_dir / "attempts").exists()
    assert not list((queue_root / "lanes" / "i18n-rewrite" / "outbox").glob(f"*{replacement_id}*"))
    assert source_before == ((run_dir / "brief.json").read_bytes(), coordinator._state_path(str(state["run_id"]), queue_root).read_bytes())
    assert _file_snapshot(tmp_path) == after_first
    assert calls == 2
    assert first["source_terminal_preserved"] is True
    assert first["replacement_consumed"] is False
    assert first["runner_invoked"] is first["provider_invoked"] is first["publisher_invoked"] is False


@pytest.mark.parametrize(
    "failure",
    [
        "missing-run", "registry-digest", "run-dir", "brief-identity", "brief-lane", "brief-sixth-field",
        "source-drift", "nonfailed", "second-replacement", "replacement-collision", "routing",
        "consumed-attempt", "consumed-queue-outbox", "consumed-queue-processing", "consumed-queue-inbox", "consumed-queue-archive", "consumed-queue-failed", "consumed-complete", "consumed-failed",
        "source-symlink", "replacement-symlink", "identity-envelope", "orphan-attempt-plan", "orphan-brief-attempt-plan", "orphan-attempt-execute", "orphan-brief-attempt-execute",
    ],
)
def test_exact_translation_replacement_cli_rejects_identity_and_lineage_drift_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: str,
) -> None:
    repo_root, queue_root, run_dir, source, state = _exact_translation_replacement_fixture(tmp_path)
    selected_source = {**source, "title": "Drifted"} if failure == "source-drift" else source
    if failure == "nonfailed":
        state["status"] = "active"
        coordinator.atomic_write_json(coordinator._state_path(str(state["run_id"]), queue_root), state)
    if failure.startswith("brief-"):
        brief = json.loads((run_dir / "brief.json").read_text())
        drift = {"brief-identity": {"run_id": "other-run"}, "brief-lane": {"lane": "i18n-new"}, "brief-sixth-field": {"unexpected": True}}[failure]
        coordinator.atomic_write_json(run_dir / "brief.json", {**brief, **drift})
    if failure == "second-replacement":
        state["run_id"] = f"{state['run_id']}-replacement-01"
        run_dir = queue_root / "translation-runs" / str(state["run_id"])
        run_dir.mkdir(parents=True)
        brief = json.loads((queue_root / "translation-runs" / "translation-terminal-en" / "brief.json").read_text())
        coordinator.atomic_write_json(run_dir / "brief.json", {**brief, "run_id": state["run_id"]})
        state["run_dir"] = str(run_dir.resolve())
        coordinator.atomic_write_json(coordinator._state_path(str(state["run_id"]), queue_root), state)
    if failure == "replacement-collision":
        replacement_id = f"{state['run_id']}-replacement-01"
        coordinator.atomic_write_json(
            coordinator._state_path(replacement_id, queue_root),
            {"run_id": replacement_id, "replacement_of": "other-run"},
        )
    if failure == "routing":
        state["lane"] = "new"
        coordinator.atomic_write_json(coordinator._state_path(str(state["run_id"]), queue_root), state)
    if failure == "identity-envelope":
        state["identity_envelope"] = coordinator._build_identity_envelope("translate_existing", "i18n-new", ["LEGACY-001"]); coordinator.atomic_write_json(coordinator._state_path(str(state["run_id"]), queue_root), state)
    if failure.startswith("orphan-"):
        replacement_dir = queue_root / "translation-runs" / f"{state['run_id']}-replacement-01"
        if "brief" in failure:
            coordinator.atomic_write_json(replacement_dir / "brief.json", {**json.loads((run_dir / "brief.json").read_text()), "run_id": replacement_dir.name})
        coordinator.atomic_write_json(replacement_dir / "attempts" / "01" / "plan-operation.json", {"status": "pending"})
        monkeypatch.setattr(coordinator.multilingual, "enqueue_translation_replacement", lambda *_args, **_kwargs: pytest.fail("enqueue invoked"))
    if failure.startswith("consumed-"):
        replacement = coordinator.multilingual.enqueue_translation_replacement(
            repo_root, queue_root, terminal_state=state, recovery_reason="LOCALE_PLAN_VALIDATION",
            source_loader=lambda *_args: source,
        )
        replacement_dir = Path(replacement["run_dir"])
        replacement_state_path = Path(replacement["state_path"])
        replacement_state = json.loads(replacement_state_path.read_text())
        if failure == "consumed-attempt":
            coordinator.atomic_write_json(replacement_dir / "attempts" / "01" / "plan-operation.json", {"status": "pending"})
        elif failure.startswith("consumed-queue-"):
            namespace = hashlib.sha256(str(replacement["run_id"]).encode()).hexdigest()[:24]
            coordinator.atomic_write_json(queue_root / "lanes" / "i18n-rewrite" / failure.removeprefix("consumed-queue-") / "job.json", {"namespace": namespace})
        else:
            replacement_state["status"] = failure.removeprefix("consumed-")
            coordinator.atomic_write_json(replacement_state_path, replacement_state)
    if failure == "source-symlink":
        target = tmp_path / "source-outside"
        run_dir.rename(target)
        run_dir.symlink_to(target, target_is_directory=True)
        state["run_dir"] = str(run_dir)
        coordinator.atomic_write_json(coordinator._state_path(str(state["run_id"]), queue_root), state)
    if failure == "replacement-symlink":
        target = tmp_path / "replacement-outside"
        target.mkdir()
        (queue_root / "translation-runs" / f"{state['run_id']}-replacement-01").symlink_to(target, target_is_directory=True)
    selected_run_id = "missing-terminal-run" if failure == "missing-run" else str(state["run_id"])
    monkeypatch.setattr(coordinator.multilingual, "load_source_article", lambda *_args: selected_source)
    monkeypatch.setattr(coordinator, "_validate_formal_runtime", lambda *_args, **_kwargs: {})
    argv = [
        "agy_gemini_coordinator", "--queue-root", str(queue_root), "--repo-root", str(repo_root),
        "replace-failed-translation-run", "--run-id", selected_run_id,
        "--expected-registry-digest", "0" * 64 if failure == "registry-digest" else coordinator._canonical_json_file_sha256(state),
        "--expected-run-dir", str((tmp_path / "wrong-run").resolve()) if failure == "run-dir" else str(run_dir.resolve()),
        "--execute" if failure.endswith("execute") else "--plan-only",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    before = _file_snapshot(tmp_path)
    returncode = coordinator.main()
    receipt = json.loads(capsys.readouterr().out)
    assert returncode == 1
    assert receipt["status"] == "rejected"
    assert _file_snapshot(tmp_path) == before


def test_exact_translation_replacement_execute_revalidates_under_lock_before_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root, queue_root, run_dir, source, state = _exact_translation_replacement_fixture(tmp_path)
    monkeypatch.setattr(coordinator.multilingual, "load_source_article", lambda *_args: source)
    monkeypatch.setattr(coordinator.multilingual, "enqueue_translation_replacement", lambda *_args, **_kwargs: pytest.fail("enqueue invoked"))
    original_read = coordinator._read_run_state_by_id
    reads = 0
    def read_then_drift(run_id: str, root: Path) -> dict[str, object]:
        nonlocal reads
        current = original_read(run_id, root)
        reads += 1
        if reads == 1:
            coordinator.atomic_write_json(
                coordinator._state_path(str(state["run_id"]), queue_root),
                {**state, "status": "active"},
            )
        return current
    monkeypatch.setattr(coordinator, "_read_run_state_by_id", read_then_drift)
    returncode, receipt = _exact_translation_replacement_cli(
        monkeypatch, capsys, repo_root, queue_root, run_dir, state, "--execute"
    )
    assert returncode == 1
    assert receipt["status"] == "rejected"
    assert reads == 2
    assert not (queue_root / "translation-runs" / f"{state['run_id']}-replacement-01").exists()
    assert not coordinator._state_path(f"{state['run_id']}-replacement-01", queue_root).exists()


def test_cycle_persists_closed_external_failure_recovery_metadata(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "runs" / "run-network-exhausted"
    queue_root = tmp_path / "queue"
    _write_brief(run_dir, "run-network-exhausted")
    register_run(run_dir, queue_root)

    def fail_tick(_run_dir: Path, _queue_root: Path) -> dict[str, object]:
        raise coordinator.ExternalJobFailed(
            "public-job-network-exhausted",
            "GeminiApiFailure",
            "API_TIMEOUT",
            failure_category="NETWORK",
            transport_attempt=2,
        )

    summary = cycle_once(
        queue_root,
        tick=fail_tick,
        process=lambda _root: {"status": "idle"},
    )
    state = read_run_state(run_dir, queue_root)

    assert summary["failed"] == 1
    assert state["status"] == "failed"
    assert state["failure_category"] == "NETWORK"
    assert state["transport_attempts"] == 3


def test_cycle_preserves_closed_code_and_failed_run_does_not_block_next(
    tmp_path: Path,
) -> None:
    queue_root = tmp_path / "queue"
    first_run = tmp_path / "runs" / "run-001"
    second_run = tmp_path / "runs" / "run-002"
    _write_brief(first_run, "run-001")
    _write_brief(second_run, "run-002")
    register_run(first_run, queue_root)
    register_run(second_run, queue_root)

    def mixed_tick(run_dir: Path, _queue_root: Path) -> dict[str, object]:
        if run_dir == first_run.resolve():
            raise coordinator.ExternalJobFailed(
                "public-job-failed",
                "RuntimeError",
                "CLI_NONZERO",
            )
        return {"status": "complete", "run_id": "run-002"}

    summary = cycle_once(
        queue_root,
        tick=mixed_tick,
        process=lambda _root: {"status": "idle"},
    )
    first_state = read_run_state(first_run, queue_root)
    second_state = read_run_state(second_run, queue_root)

    assert summary["failed"] == 1
    assert summary["complete"] == 1
    assert first_state["status"] == "failed"
    assert first_state["error_code"] == "CLI_NONZERO"
    assert second_state["status"] == "complete"


def test_cycle_closes_untrusted_failure_receipt_error_type(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    run_dir = tmp_path / "runs" / "run-invalid-failure"
    _write_brief(run_dir, "run-invalid-failure")
    register_run(run_dir, queue_root)
    request = create_external_request(
        queue_root,
        namespace="opaque-coordinator-invalid-failure",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema={"type": "object"},
    )
    marker = "PRIVATE_PATH_MARKER/CREDENTIAL_MARKER"
    coordinator.atomic_write_json(
        queue_root / "failed" / f"{request['job_id']}.json",
        {
            "schema_version": 1,
            "job_id": request["job_id"],
            "request_sha256": request["request_sha256"],
            "error_type": marker,
            "completed_at": "2026-07-26T00:30:00+08:00",
        },
    )

    summary = cycle_once(
        queue_root,
        tick=lambda *_args: consume_external_response(queue_root, request),
        process=lambda _root: {"status": "idle"},
    )
    state = read_run_state(run_dir, queue_root)

    assert summary["failed"] == 1
    assert state["error_type"] == "InvalidFailureReceipt"
    assert marker not in json.dumps(state)


def test_cycle_closes_deep_failure_json_without_state_leak(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    run_dir = tmp_path / "runs" / "run-deep-failure"
    _write_brief(run_dir, "run-deep-failure")
    register_run(run_dir, queue_root)
    request = create_external_request(
        queue_root,
        namespace="opaque-coordinator-deep-failure",
        role="writer",
        model="gemini-test-writer",
        prompt="公開 prompt",
        response_schema={"type": "object"},
    )
    marker = "/Users/PRIVATE_PATH_MARKER/CREDENTIAL_MARKER"
    depth = 20_000
    payload = "[" * depth + json.dumps(marker) + "]" * depth
    failed_path = queue_root / "failed" / f"{request['job_id']}.json"
    failed_path.parent.mkdir()
    failed_path.write_text(payload, encoding="utf-8")

    summary = cycle_once(
        queue_root,
        tick=lambda *_args: consume_external_response(queue_root, request),
        process=lambda _root: {"status": "idle"},
    )
    state = read_run_state(run_dir, queue_root)

    assert summary["failed"] == 1
    assert state["error_type"] == "InvalidFailureReceipt"
    serialized = json.dumps(state)
    assert marker not in serialized
    assert "RecursionError" not in serialized


def test_cycle_isolates_runner_malformed_json_and_keeps_run_retryable(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "run-malformed-json"
    queue_root = tmp_path / "queue"
    _write_brief(run_dir, "run-malformed-json")
    register_run(run_dir, queue_root)

    def pending_tick(_run_dir: Path, _queue_root: Path) -> dict[str, object]:
        raise ExternalJobPending("public-job-malformed")

    def malformed_runner(_queue_root: Path) -> dict[str, str]:
        raise json.JSONDecodeError("unterminated response", '{"result":', 10)

    summary = cycle_once(queue_root, tick=pending_tick, process=malformed_runner)
    state = read_run_state(run_dir, queue_root)

    assert summary["status"] == "failed"
    assert summary["runner"] == {
        "status": "failed",
        "job_id": "public-job-malformed",
        "error_type": "JSONDecodeError",
    }
    assert state["status"] == "active"
    assert state["last_job_id"] == "public-job-malformed"


def test_campaign_dry_run_workset_is_stable_and_side_effect_free(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    repo_root.mkdir()
    records = [
        {"id": "LEGACY-001", "serial": "tarot-001", "path": "articles/tarot/tarot-001"},
        {"id": "LEGACY-002", "serial": "tarot-002", "path": "articles/tarot/tarot-002"},
    ]
    inventory = {record["id"]: {"id": record["id"], "record": record} for record in records}
    monkeypatch.setattr(
        coordinator.pipeline,
        "build_matrix_backlog",
        lambda _repo: [
            {"id": "NEW-001", "primaryKeyword": "新主題一"},
            {"id": "NEW-002", "primaryKeyword": "新主題二"},
        ],
    )
    monkeypatch.setattr(coordinator.publisher, "legacy_article_records", lambda _repo: records)
    monkeypatch.setattr(coordinator.pipeline, "_existing_rewrite_inventory", lambda _repo: inventory)
    monkeypatch.setattr(
        coordinator.publisher,
        "summarize_legacy_rewrite_backlog",
        lambda *_args, **_kwargs: {"unattempted": 1, "active_or_incomplete": 1, "released": 0},
    )

    new_run = tmp_path / "new-run"
    rewrite_run = tmp_path / "rewrite-run"
    translation_run = tmp_path / "translation-run"
    for run_dir, run_id, brief in (
        (new_run, "new-run", {"mode": "create", "articles": [{"target": {"id": "NEW-002"}}]}),
        (rewrite_run, "rewrite-run", {"mode": "rewrite_existing_body", "articles": [{"article_id": "LEGACY-002"}]}),
        (translation_run, "translation-run", {"mode": "translate_existing", "lane": "i18n-new", "articles": [{"source_article_id": "NEW-001", "locale": "en"}]}),
    ):
        run_dir.mkdir()
        (run_dir / "brief.json").write_text(
            json.dumps({"schema_version": 1, "run_id": run_id, **brief}),
            encoding="utf-8",
        )
        state_path = queue_root / "runs" / f"{run_id}.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        lane = str(brief.get("lane") or ("new" if brief["mode"] == "create" else "rewrite"))
        article = brief["articles"][0]
        article_id = (
            article["target"]["id"]
            if brief["mode"] == "create"
            else article.get("article_id", article.get("source_article_id"))
        )
        state_path.write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "run_dir": str(run_dir),
                    "status": "active",
                    "identity_envelope": _expected_identity_envelope(
                        str(brief["mode"]),
                        lane,
                        [str(article_id)],
                    ),
                }
            ),
            encoding="utf-8",
        )

    before = {str(path.relative_to(tmp_path)): path.read_bytes() for path in sorted(tmp_path.rglob("*")) if path.is_file()}
    first = build_campaign_dry_run_workset(repo_root, queue_root, state_root, campaign_version="apf-001-v1")
    second = build_campaign_dry_run_workset(repo_root, queue_root, state_root, campaign_version="apf-001-v1")
    next_campaign = build_campaign_dry_run_workset(repo_root, queue_root, state_root, campaign_version="apf-001-v2")
    after = {str(path.relative_to(tmp_path)): path.read_bytes() for path in sorted(tmp_path.rglob("*")) if path.is_file()}

    assert json.dumps(first, ensure_ascii=False, sort_keys=True, separators=(",", ":")) == json.dumps(second, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert after == before
    assert [item["lane"] for item in first["items"]] == [
        "new",
        "rewrite",
        "rewrite",
        "i18n-new",
        "i18n-new",
        "i18n-new",
        "i18n-rewrite",
        "i18n-rewrite",
        "i18n-rewrite",
        "i18n-rewrite",
        "i18n-rewrite",
        "i18n-rewrite",
    ]
    assert {(item["article_id"], item["locale"]) for item in first["items"]} == {
        ("NEW-001", "zh-TW"),
        ("LEGACY-001", "zh-TW"),
        ("LEGACY-002", "zh-TW"),
        ("NEW-001", "en"),
        ("NEW-001", "ja"),
        ("NEW-001", "ko"),
        ("LEGACY-001", "en"),
        ("LEGACY-001", "ja"),
        ("LEGACY-001", "ko"),
        ("LEGACY-002", "en"),
        ("LEGACY-002", "ja"),
        ("LEGACY-002", "ko"),
    }
    assert len({item["work_id"] for item in first["items"]}) == len(first["items"])
    assert all({"source_kind", "article_id", "locale", "campaign_version", "work_id", "lane", "reason"} <= set(item) for item in first["items"])
    assert {item["work_id"] for item in first["items"]}.isdisjoint({item["work_id"] for item in next_campaign["items"]})


def test_campaign_dry_run_dedupes_rewrite_and_translation_by_campaign_version(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    repo_root.mkdir()
    record = {"id": "LEGACY-001", "serial": "tarot-001", "path": "articles/tarot/tarot-001"}
    monkeypatch.setattr(coordinator.pipeline, "build_matrix_backlog", lambda _repo: [])
    monkeypatch.setattr(coordinator.publisher, "legacy_article_records", lambda _repo: [record])
    monkeypatch.setattr(coordinator.pipeline, "_existing_rewrite_inventory", lambda _repo: {"LEGACY-001": {"id": "LEGACY-001", "record": record}})
    monkeypatch.setattr(
        coordinator.publisher,
        "summarize_legacy_rewrite_backlog",
        lambda *_args, **_kwargs: {"unattempted": 1, "active_or_incomplete": 0, "released": 0},
    )

    def register_campaign_run(run_id: str, brief: dict[str, object]) -> None:
        run_dir = tmp_path / run_id
        run_dir.mkdir()
        (run_dir / "brief.json").write_text(
            json.dumps({"schema_version": 1, "run_id": run_id, **brief}),
            encoding="utf-8",
        )
        state_path = queue_root / "runs" / f"{run_id}.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        mode = str(brief["mode"])
        lane = "rewrite" if mode == "rewrite_existing_body" else "i18n-rewrite"
        article = brief["articles"][0]
        article_id = article.get("article_id", article.get("source_article_id"))
        state_path.write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "run_dir": str(run_dir),
                    "status": "completed",
                    "identity_envelope": _expected_identity_envelope(
                        mode,
                        lane,
                        [str(article_id)],
                    ),
                }
            ),
            encoding="utf-8",
        )

    register_campaign_run(
        "old-rewrite",
        {"mode": "rewrite_existing_body", "campaign_version": "rewrite-v0", "articles": [{"article_id": "LEGACY-001"}]},
    )
    register_campaign_run(
        "old-translation",
        {"mode": "translate_existing", "lane": "i18n-rewrite", "campaign_version": "rewrite-v0", "articles": [{"source_article_id": "LEGACY-001", "locale": "en"}]},
    )

    first = build_campaign_dry_run_workset(repo_root, queue_root, state_root, campaign_version=" rewrite-v1 ", locales=("en", "ja"))
    assert first["campaign_version"] == "rewrite-v1"
    assert [(item["lane"], item["locale"]) for item in first["items"]] == [("rewrite", "zh-TW"), ("i18n-rewrite", "en"), ("i18n-rewrite", "ja")]

    register_campaign_run(
        "same-rewrite",
        {"mode": "rewrite_existing_body", "campaign_version": "rewrite-v1", "articles": [{"article_id": "LEGACY-001"}]},
    )
    register_campaign_run(
        "same-translation",
        {"mode": "translate_existing", "lane": "i18n-rewrite", "campaign_version": "rewrite-v1", "articles": [{"source_article_id": "LEGACY-001", "locale": "ja"}]},
    )
    same_campaign = build_campaign_dry_run_workset(repo_root, queue_root, state_root, campaign_version="rewrite-v1", locales=("en", "ja"))
    assert same_campaign["items"] == []

    next_campaign = build_campaign_dry_run_workset(repo_root, queue_root, state_root, campaign_version="rewrite-v2", locales=("en", "ja"))
    assert [(item["lane"], item["locale"]) for item in next_campaign["items"]] == [("rewrite", "zh-TW"), ("i18n-rewrite", "en"), ("i18n-rewrite", "ja")]
    with pytest.raises(ValueError, match="campaign version"):
        build_campaign_dry_run_workset(repo_root, queue_root, state_root, campaign_version="rewrite-v1\nnext")


def test_seed_legacy_rewrite_runs_registers_oldest_unattempted_article(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    run_root = tmp_path / "private-runs"
    repo_root.mkdir()
    first_record = {
        "id": "LEGACY-001",
        "product": "tarot",
        "articleCategory": "tarot",
        "serial": "tarot-001",
        "slug": "yongshen-meaning",
        "urlSlug": "fortune-0039",
        "primaryKeyword": "塔羅舊文一",
        "title": "塔羅舊文一",
        "description": "描述一",
        "answer": "答案一",
        "faq": [{"question": "問一", "answer": "答一"}],
        "tags": ["塔羅"],
        "path": "articles/tarot/tarot-001",
    }
    second_record = {
        **first_record,
        "id": "LEGACY-002",
        "serial": "tarot-002",
        "slug": "legacy-two",
        "urlSlug": "legacy-two",
        "primaryKeyword": "塔羅舊文二",
        "title": "塔羅舊文二",
        "path": "articles/tarot/tarot-002",
    }
    current_body = [{"heading": "現況", "paragraphs": ["這是一段舊文內容，等待改得更貼近讀者生活。"]}]
    inventory = {
        "LEGACY-001": {"id": "LEGACY-001", "record": first_record, "canonicalPath": "/articles/tarot/tarot-001", "currentBody": current_body, "published": "2026-01-01", "updated": "2026-01-01"},
        "LEGACY-002": {"id": "LEGACY-002", "record": second_record, "canonicalPath": "/articles/tarot/tarot-002", "currentBody": current_body, "published": "2026-01-01", "updated": "2026-01-01"},
    }

    monkeypatch.setattr(coordinator.publisher, "legacy_article_records", lambda _repo: [first_record, second_record])
    monkeypatch.setattr(coordinator.pipeline, "_existing_rewrite_inventory", lambda _repo: inventory)

    summary = seed_legacy_rewrite_runs(
        repo_root,
        queue_root,
        state_root,
        run_root,
        max_new_runs=1,
        source_commit="a" * 40,
    )

    assert summary["status"] == "seeded"
    assert summary["created"] == 1
    assert summary["created_run_ids"] == ["legacy-auto-sweep-v1-tarot-001-legacy-001"]
    brief = json.loads((run_root / "legacy-auto-sweep-v1-tarot-001-legacy-001" / "brief.json").read_text(encoding="utf-8"))
    assert brief["mode"] == "rewrite_existing_body"
    assert brief["articles"][0]["article_id"] == "LEGACY-001"
    assert brief["articles"][0]["identity"]["serial"] == "tarot-001"
    assert brief["articles"][0]["identity"]["slug"] == "fortune-0039"
    assert brief["articles"][0]["immutable_fields"]["slug"] == "yongshen-meaning"
    assert len(list((queue_root / "runs").glob("*.json"))) == 1


def test_seed_legacy_rewrite_runs_preserves_orphan_identity_without_reseeding(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    run_root = tmp_path / "private-runs"
    repo_root.mkdir()
    record = {
        "id": "LEGACY-001",
        "product": "tarot",
        "articleCategory": "tarot",
        "serial": "tarot-001",
        "slug": "yongshen-meaning",
        "urlSlug": "fortune-0039",
        "primaryKeyword": "塔羅舊文一",
        "title": "塔羅舊文一",
        "description": "描述一",
        "answer": "答案一",
        "faq": [{"question": "問一", "answer": "答一"}],
        "tags": ["塔羅"],
        "path": "articles/tarot/tarot-001",
    }
    current_body = [{"heading": "現況", "paragraphs": ["這是一段舊文內容，等待改得更貼近讀者生活。"]}]
    inventory = {
        "LEGACY-001": {
            "id": "LEGACY-001",
            "record": record,
            "canonicalPath": "/articles/tarot/tarot-001",
            "currentBody": current_body,
            "published": "2026-01-01",
            "updated": "2026-01-01",
        }
    }
    base_run_id = "legacy-auto-sweep-v1-tarot-001-legacy-001"
    orphan_state_path = coordinator._state_path(base_run_id, queue_root)
    orphan_state_path.parent.mkdir(parents=True)
    orphan_state_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_id": base_run_id,
                "run_dir": str(tmp_path / "removed-worktree" / base_run_id),
                "status": "active",
                "identity_envelope": _expected_identity_envelope(
                    "rewrite_existing_body",
                    "rewrite",
                    ["LEGACY-001"],
                ),
            }
        ),
        encoding="utf-8",
    )
    orphan_state_before = orphan_state_path.read_bytes()
    preserved_base_run_dir = run_root / base_run_id
    preserved_base_run_dir.mkdir(parents=True)
    preserved_marker = preserved_base_run_dir / "preserve.txt"
    preserved_marker.write_text("failed historical seed", encoding="utf-8")

    monkeypatch.setattr(coordinator.publisher, "legacy_article_records", lambda _repo: [record])
    monkeypatch.setattr(coordinator.pipeline, "_existing_rewrite_inventory", lambda _repo: inventory)

    summary = seed_legacy_rewrite_runs(
        repo_root,
        queue_root,
        state_root,
        run_root,
        max_new_runs=1,
        source_commit="a" * 40,
    )

    assert summary["status"] == "idle"
    assert summary["created_run_ids"] == []
    assert orphan_state_path.read_bytes() == orphan_state_before
    assert preserved_marker.read_text(encoding="utf-8") == "failed historical seed"
    assert not (run_root / f"{base_run_id}-retry-01").exists()


def test_next_legacy_rewrite_run_id_skips_existing_retry_directory(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    run_root = tmp_path / "private-runs"
    base_run_id = "legacy-auto-sweep-v1-tarot-001-legacy-001"
    base_state_path = coordinator._state_path(base_run_id, queue_root)
    base_state_path.parent.mkdir(parents=True)
    base_state_path.write_text("{}", encoding="utf-8")
    retry_dir = run_root / f"{base_run_id}-retry-01"
    retry_dir.mkdir(parents=True)
    marker = retry_dir / "preserve.txt"
    marker.write_text("historical", encoding="utf-8")

    selected = coordinator._next_legacy_rewrite_run_id(run_root, queue_root, base_run_id)

    assert selected == f"{base_run_id}-retry-02"
    assert marker.read_text(encoding="utf-8") == "historical"


def test_seed_legacy_rewrite_runs_advances_past_exhausted_clean_approvals(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    run_root = tmp_path / "private-runs"
    repo_root.mkdir()
    current_body = [
        {
            "heading": "現況",
            "paragraphs": ["這是一段舊文內容，等待改得更貼近讀者生活。"],
        }
    ]
    records: list[dict[str, object]] = []
    inventory: dict[str, dict[str, object]] = {}
    completed: dict[str, tuple[dict[str, object], dict[str, object], dict[str, object]]] = {}
    retry_before: dict[Path, bytes] = {}
    for index in range(1, 7):
        article_id = f"LEGACY-{index:03d}"
        serial = f"tarot-{index:03d}"
        record = {
            "id": article_id,
            "product": "tarot",
            "articleCategory": "tarot",
            "serial": serial,
            "slug": f"legacy-{index:03d}",
            "urlSlug": f"legacy-{index:03d}",
            "primaryKeyword": f"塔羅舊文{index}",
            "title": f"塔羅舊文{index}",
            "description": f"描述{index}",
            "answer": f"答案{index}",
            "faq": [{"question": f"問{index}", "answer": f"答{index}"}],
            "tags": ["塔羅"],
            "path": f"articles/tarot/{serial}",
        }
        records.append(record)
        inventory[article_id] = {
            "id": article_id,
            "record": record,
            "canonicalPath": f"/articles/tarot/{serial}",
            "currentBody": current_body,
            "published": "2026-01-01",
            "updated": "2026-01-01",
        }
        if index == 6:
            continue
        run_id = f"rewrite-approved-{index}"
        run_dir = tmp_path / "completed-runs" / run_id
        run_dir.mkdir(parents=True)
        (run_dir / "brief.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "run_id": run_id,
                    "mode": "rewrite_existing_body",
                    "articles": [{"article_id": article_id}],
                }
            ),
            encoding="utf-8",
        )
        state = {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(run_dir),
            "status": "complete",
            "identity_envelope": _expected_identity_envelope(
                "rewrite_existing_body",
                "rewrite",
                [article_id],
            ),
        }
        candidate = {
            "schema_version": 1,
            "run_id": run_id,
            "mode": "rewrite_existing_body",
            "articles": [{"article_id": article_id}],
        }
        review = {
            "schema_version": 1,
            "run_id": run_id,
            "articles": [
                {
                    "article_id": article_id,
                    "verdict": "APPROVE",
                    "hard_failure": False,
                    "findings": [],
                }
            ],
        }
        completed[run_id] = (state, candidate, review)
        state_path = queue_root / "runs" / f"{run_id}.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state), encoding="utf-8")
        retry_path = coordinator.publisher._retry_path(state_root, "rewrite", run_id)
        retry_path.parent.mkdir(parents=True, exist_ok=True)
        retry_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "phase": "rewrite",
                    "run_id": run_id,
                    "attempts": coordinator.publisher.MAX_RETRY_ATTEMPTS,
                    "max_attempts": coordinator.publisher.MAX_RETRY_ATTEMPTS,
                    "next_eligible_at": "2026-07-30T12:20:00+08:00",
                    "eligibility": "exhausted",
                    "candidate_preserved": True,
                }
            ),
            encoding="utf-8",
        )
        retry_before[retry_path] = retry_path.read_bytes()

    monkeypatch.setattr(
        coordinator.publisher,
        "_load_completed_run",
        lambda path: completed[json.loads(path.read_text(encoding="utf-8"))["run_id"]],
    )
    monkeypatch.setattr(
        coordinator.publisher,
        "_load_rewrite_brief",
        lambda run_dir, _run_id: json.loads(
            (run_dir / "brief.json").read_text(encoding="utf-8")
        ),
    )
    monkeypatch.setattr(
        coordinator.publisher.pipeline,
        "rewrite_aggregate_findings",
        lambda *_args, **_kwargs: ([], []),
    )
    monkeypatch.setattr(
        coordinator.publisher,
        "legacy_article_records",
        lambda _repo: records,
    )
    monkeypatch.setattr(
        coordinator.pipeline,
        "_existing_rewrite_inventory",
        lambda _repo: inventory,
    )

    allowed_article_ids = {str(record["id"]) for record in records}
    backlog = coordinator.publisher.summarize_legacy_rewrite_backlog(
        queue_root,
        state_root,
        allowed_article_ids=allowed_article_ids,
        legacy_records=records,
    )
    ready = coordinator.publisher.collect_ready_rewrite_runs(
        queue_root,
        state_root,
        allowed_article_ids=allowed_article_ids,
    )
    result = seed_legacy_rewrite_runs(
        repo_root,
        queue_root,
        state_root,
        run_root,
        max_new_runs=1,
        source_commit="a" * 40,
    )

    assert backlog["clean_approve"] == 5
    assert ready == []
    assert result["status"] == "seeded"
    assert backlog["publish_ready"] == 0
    assert backlog["retry_exhausted"] == 5
    assert result["created_run_ids"] == [
        "legacy-auto-sweep-v1-tarot-006-legacy-006"
    ]
    assert len(list((queue_root / "runs").glob("*.json"))) == 6
    assert {
        path: path.read_bytes() for path in retry_before
    } == retry_before


@pytest.mark.parametrize("blocked_field", ["retry_deferred", "retry_invalid"])
def test_seed_legacy_rewrite_runs_surfaces_non_idle_retry_blocker(
    tmp_path: Path,
    monkeypatch,
    blocked_field: str,
) -> None:
    backlog = {
        "released": 0,
        "clean_approve": 1,
        "publish_ready": 0,
        "retry_deferred": 0,
        "retry_exhausted": 0,
        "retry_invalid": 0,
        "reject": 0,
        "active_or_incomplete": 0,
        "non_legacy": 0,
        "legacy_total": 2,
        "attempted": 1,
        "unattempted": 1,
        "clean_approve_run_ids": ["rewrite-blocked"],
        "unattempted_articles": [],
    }
    backlog[blocked_field] = 1
    monkeypatch.setattr(
        coordinator.publisher,
        "legacy_article_records",
        lambda _repo: [{"id": "LEGACY-001"}],
    )
    monkeypatch.setattr(
        coordinator.publisher,
        "summarize_legacy_rewrite_backlog",
        lambda *_args, **_kwargs: backlog,
    )

    result = seed_legacy_rewrite_runs(
        tmp_path,
        tmp_path / "queue",
        tmp_path / "state",
        tmp_path / "private-runs",
        source_commit="a" * 40,
    )

    assert result["status"] == "rewrite_retry_blocked"
    assert result["created"] == 0
    assert result["backlog"][blocked_field] == 1
    assert not (tmp_path / "private-runs").exists()


def test_seed_legacy_rewrite_runs_surfaces_exhausted_terminal_when_inventory_is_done(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        coordinator.publisher,
        "legacy_article_records",
        lambda _repo: [{"id": "LEGACY-001"}],
    )
    monkeypatch.setattr(
        coordinator.publisher,
        "summarize_legacy_rewrite_backlog",
        lambda *_args, **_kwargs: {
            "clean_approve": 1,
            "publish_ready": 0,
            "retry_exhausted": 1,
            "unattempted": 0,
        },
    )

    result = seed_legacy_rewrite_runs(
        tmp_path,
        tmp_path / "queue",
        tmp_path / "state",
        tmp_path / "private-runs",
        source_commit="a" * 40,
    )

    assert result["status"] == "rewrite_retry_exhausted"
    assert result["created"] == 0
    assert result["backlog"]["retry_exhausted"] == 1


def test_failed_external_job_replacement_cli_entrypoint_exists(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.agy_gemini_coordinator",
            "--queue-root",
            str(tmp_path / "queue"),
            "replace-failed-external-job",
            "--help",
        ],
        cwd=Path(coordinator.__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--authority-digest" in completed.stdout
    assert "--plan-only" in completed.stdout


def _failure_receipt(
    request: dict[str, object],
    *,
    error_type: object = "GeminiCliFailure",
    error_code: object = "CLI_NONZERO",
) -> dict[str, object]:
    receipt: dict[str, object] = {
        "schema_version": 1,
        "job_id": request["job_id"],
        "request_sha256": request["request_sha256"],
        "error_type": error_type,
        "completed_at": "2026-08-25T12:00:00+08:00",
    }
    if error_code is not None:
        receipt["error_code"] = error_code
    return receipt


def _failed_external_replacement_fixture(
    tmp_path: Path,
    *,
    run_id: str = "v0393-synthetic-run",
    model: str = "gemini-3.5-flash",
    article_ids: list[str] | None = None,
) -> tuple[Path, Path, dict[str, object], str]:
    run_dir = tmp_path / "runs" / run_id
    queue_root = tmp_path / "queue"
    correlation_id = "8ca37c8df03cbb06b4b65ac0912d485b"
    if article_ids is None:
        _write_brief(run_dir, run_id)
    else:
        run_dir.mkdir(parents=True)
        coordinator.atomic_write_json(
            run_dir / "brief.json",
            {
                "schema_version": 1,
                "run_id": run_id,
                "mode": "create",
                "articles": [{"target": {"id": article_id}} for article_id in article_ids],
            },
        )
    state = register_run(run_dir, queue_root, correlation_id=correlation_id)
    request = create_external_request(
        queue_root,
        namespace="v0393-fixture",
        role="writer",
        model=model,
        prompt="公開 synthetic failed replacement fixture",
        response_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
        },
    )
    outbox_path = queue_root / "outbox" / f"{request['job_id']}.json"
    archive_path = queue_root / "archive" / outbox_path.name
    archive_path.parent.mkdir(parents=True)
    os.replace(outbox_path, archive_path)
    coordinator.atomic_write_json(
        queue_root / "failed" / f"{request['job_id']}.json",
        _failure_receipt(request),
    )
    state["last_job_id"] = request["job_id"]
    coordinator._write_state(queue_root, state)
    return run_dir, queue_root, request, correlation_id


def _replacement_authority_digest(label: str = "v0393-authority") -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _replace_failed(
    run_dir: Path,
    queue_root: Path,
    request: dict[str, object],
    correlation_id: str,
    *,
    execute: bool = True,
    plan_only: bool = False,
    authority_digest: str | None = None,
    **overrides: object,
) -> dict[str, object]:
    brief_path = run_dir / "brief.json"
    expected_run_id = (
        json.loads(brief_path.read_text())["run_id"] if brief_path.exists() else run_dir.name
    )
    args: dict[str, object] = {
        "job_queue_root": queue_root,
        "lane": "new",
        "expected_run_id": expected_run_id,
        "source_job_id": request["job_id"],
        "request_sha256": request["request_sha256"],
        "namespace": request["namespace"],
        "correlation_id": correlation_id,
        "failure_category": "CLI_NONZERO",
        "error_code": "CLI_NONZERO",
        "authority_digest": authority_digest or _replacement_authority_digest(),
        "execute": execute,
        "plan_only": plan_only,
    }
    args.update(overrides)
    return coordinator.replace_failed_external_job(run_dir, queue_root, **args)


def _legacy_null_correlation_id(run_id: str) -> str:
    return f"legacy-null-correlation:{run_id}"


def _write_provider_attempt_zero_invalid_receipt(
    queue_root: Path,
    request: dict[str, object],
) -> None:
    coordinator.atomic_write_json(
        queue_root / "failed" / f"{request['job_id']}.json",
        {
            "schema_version": 1,
            "job_id": request["job_id"],
            "request_sha256": request["request_sha256"],
            "error_type": "ValueError",
            "failure_category": "INVALID_RECEIPT",
            "completed_at": "2026-08-28T17:34:28+08:00",
        },
    )


def _failed_external_replacement_invalid_receipt_fixture(
    tmp_path: Path,
    *,
    model: str = "gemini-3.5-flash-lite",
) -> tuple[Path, Path, dict[str, object], str, str]:
    run_dir, queue_root, request, correlation_id = _failed_external_replacement_fixture(
        tmp_path,
        model=model,
    )
    result = _replace_failed(run_dir, queue_root, request, correlation_id)
    replacement_job_id = str(result["replacement_job_id"])
    os.replace(
        queue_root / "outbox" / f"{replacement_job_id}.json",
        queue_root / "archive" / f"{replacement_job_id}.json",
    )
    coordinator.atomic_write_json(
        queue_root / "failed" / f"{replacement_job_id}.json",
        {
            "schema_version": 1,
            "job_id": replacement_job_id,
            "request_sha256": request["request_sha256"],
            "error_type": "ValueError",
            "failure_category": "INVALID_RECEIPT",
            "completed_at": "2026-08-25T17:34:28+08:00",
        },
    )
    state = read_run_state(run_dir, queue_root)
    state["status"] = "failed"
    state["error_type"] = "ValueError"
    coordinator._write_state(queue_root, state)
    return run_dir, queue_root, request, correlation_id, replacement_job_id


def _resume_replacement(
    run_dir: Path,
    queue_root: Path,
    request: dict[str, object],
    correlation_id: str,
    **overrides: object,
) -> dict[str, object]:
    return _replace_failed(
        run_dir,
        queue_root,
        request,
        correlation_id,
        resume_replacement=True,
        local_preflight_reason="NO_ANTIGRAVITY_LOW_MODEL_LABEL",
        **overrides,
    )


def test_failed_external_job_replacement_plan_only_is_side_effect_free(tmp_path: Path) -> None:
    run_dir, queue_root, request, correlation_id = _failed_external_replacement_fixture(tmp_path)
    before = _file_snapshot(queue_root)

    result = _replace_failed(
        run_dir,
        queue_root,
        request,
        correlation_id,
        execute=False,
        plan_only=True,
    )

    assert result["status"] == "plan_only"
    assert result["source_job_id"] == request["job_id"]
    assert result["request_sha256"] == request["request_sha256"]
    assert result["failure_category"] == "CLI_NONZERO"
    assert result["authority_digest"] == _replacement_authority_digest()
    assert _file_snapshot(queue_root) == before


def test_failed_external_job_replacement_plan_only_accepts_provider_zero_invalid_receipt_legacy_null_correlation(
    tmp_path: Path,
) -> None:
    run_dir, queue_root, request, _correlation_id = _failed_external_replacement_fixture(
        tmp_path,
    )
    run_id = json.loads((run_dir / "brief.json").read_text(encoding="utf-8"))["run_id"]
    failed_path = queue_root / "failed" / f"{request['job_id']}.json"
    failed_path.unlink()
    _write_provider_attempt_zero_invalid_receipt(queue_root, request)
    state = read_run_state(run_dir, queue_root)
    state.pop("correlation_id")
    state["last_job_id"] = request["job_id"]
    coordinator._write_state(queue_root, state)
    before = _file_snapshot(queue_root)

    result = _replace_failed(
        run_dir,
        queue_root,
        request,
        _legacy_null_correlation_id(run_id),
        failure_category="INVALID_RECEIPT",
        error_code="NO_ERROR_CODE",
        execute=False,
        plan_only=True,
    )

    assert result["status"] == "plan_only"
    assert result["failure_category"] == "INVALID_RECEIPT"
    assert result["error_code"] is None
    assert result["correlation_id"] is None
    assert result["legacy_null_correlation"] is True
    assert result["operator_correlation_authority"] == _legacy_null_correlation_id(run_id)
    assert result["source_provider_attempt"] == 0
    assert result["source_job_id"] == request["job_id"]
    assert result["namespace"] == request["namespace"]
    assert _file_snapshot(queue_root) == before


def test_failed_external_job_replacement_legacy_null_correlation_result_recovers_without_actor_run_dir(
    tmp_path: Path,
) -> None:
    run_dir, queue_root, request, _correlation_id = _failed_external_replacement_fixture(
        tmp_path,
    )
    run_id = json.loads((run_dir / "brief.json").read_text(encoding="utf-8"))["run_id"]
    (queue_root / "failed" / f"{request['job_id']}.json").unlink()
    _write_provider_attempt_zero_invalid_receipt(queue_root, request)
    state = read_run_state(run_dir, queue_root)
    state.pop("correlation_id")
    state["last_job_id"] = request["job_id"]
    coordinator._write_state(queue_root, state)

    result = _replace_failed(
        run_dir,
        queue_root,
        request,
        _legacy_null_correlation_id(run_id),
        failure_category="INVALID_RECEIPT",
        error_code="NO_ERROR_CODE",
    )
    replacement_job_id = str(result["replacement_job_id"])
    persisted = coordinator._read_run_state_by_id(run_id, queue_root)
    assert persisted.get("correlation_id") is None
    assert persisted["failed_external_job_replacement"]["correlation_id"] is None
    coordinator.atomic_write_json(
        queue_root / "inbox" / f"{replacement_job_id}.json",
        {
            "schema_version": 1,
            "job_id": replacement_job_id,
            "request_sha256": request["request_sha256"],
            "model": request["model"],
            "completed_at": "2026-08-28T17:35:00+08:00",
            "result": {"ok": True},
        },
    )
    shutil.rmtree(run_dir)

    summary = coordinator.cycle_once(queue_root, exact_run_ids=(run_id,))

    state = coordinator._read_run_state_by_id(run_id, queue_root)
    assert summary["complete"] == 1
    assert summary["failed"] == 0
    assert state["status"] == "complete"
    assert state["result"]["recovered_failed_external_job"] == {
        "source_job_id": request["job_id"],
        "replacement_job_id": replacement_job_id,
        "decision": f"failed-external-job-replacements/{request['job_id']}.json",
    }
    assert state["result"]["external_result"] == {"ok": True}


def test_failed_external_job_replacement_rejects_invalid_receipt_when_provider_attempt_exists(
    tmp_path: Path,
) -> None:
    run_dir, queue_root, request, _correlation_id = _failed_external_replacement_fixture(
        tmp_path,
    )
    run_id = json.loads((run_dir / "brief.json").read_text(encoding="utf-8"))["run_id"]
    (queue_root / "failed" / f"{request['job_id']}.json").unlink()
    _write_provider_attempt_zero_invalid_receipt(queue_root, request)
    attempt_path = queue_root / "production-attempts" / f"{request['job_id']}.attempt"
    coordinator.atomic_write_json(
        attempt_path,
        {
            "schema_version": 1,
            "job_id": request["job_id"],
            "attempt": 1,
            "recorded_at": "2026-08-28T17:34:28+08:00",
        },
    )
    state = read_run_state(run_dir, queue_root)
    state.pop("correlation_id")
    state["last_job_id"] = request["job_id"]
    coordinator._write_state(queue_root, state)
    before = _file_snapshot(queue_root)

    with pytest.raises(ValueError, match="failure identity"):
        _replace_failed(
            run_dir,
            queue_root,
            request,
            _legacy_null_correlation_id(run_id),
            failure_category="INVALID_RECEIPT",
            error_code="NO_ERROR_CODE",
            execute=False,
            plan_only=True,
        )
    assert _file_snapshot(queue_root) == before


def test_failed_external_job_replacement_plan_only_uses_durable_registry_when_run_dir_missing(
    tmp_path: Path,
) -> None:
    run_dir, queue_root, request, correlation_id = _failed_external_replacement_fixture(tmp_path)
    before = _file_snapshot(queue_root)
    shutil.rmtree(run_dir)

    result = _replace_failed(
        run_dir,
        queue_root,
        request,
        correlation_id,
        execute=False,
        plan_only=True,
    )

    assert result["status"] == "plan_only"
    assert result["run_id"] == "v0393-synthetic-run"
    assert result["source_job_id"] == request["job_id"]
    assert _file_snapshot(queue_root) == before


def test_failed_external_job_replacement_execute_is_exactly_once_and_consumable(
    tmp_path: Path,
) -> None:
    run_dir, queue_root, request, correlation_id = _failed_external_replacement_fixture(tmp_path)
    source_archive = queue_root / "archive" / f"{request['job_id']}.json"
    source_failed = queue_root / "failed" / f"{request['job_id']}.json"
    source_archive_bytes = source_archive.read_bytes()
    source_failed_bytes = source_failed.read_bytes()

    result = _replace_failed(run_dir, queue_root, request, correlation_id)
    after_first = _file_snapshot(queue_root)
    replay = _replace_failed(run_dir, queue_root, request, correlation_id)

    assert result["status"] == "replacement_created"
    assert replay["status"] == "already_replaced"
    assert _file_snapshot(queue_root) == after_first
    replacement_job_id = str(result["replacement_job_id"])
    replacement_path = queue_root / "outbox" / f"{replacement_job_id}.json"
    replacement = json.loads(replacement_path.read_text())
    assert replacement["request_sha256"] == request["request_sha256"]
    assert replacement["prompt"] == request["prompt"]
    assert replacement["response_schema"] == request["response_schema"]
    assert replacement["model"] == request["model"]
    assert replacement["role"] == request["role"]
    assert replacement["replacement"] == {
        "authority_digest": _replacement_authority_digest(),
        "lineage_attempt": 1,
        "lineage_id": result["replacement_lineage_id"],
        "lineage_kind": "failed_external_job_replacement",
        "source_job_id": request["job_id"],
    }
    assert source_archive.read_bytes() == source_archive_bytes
    assert source_failed.read_bytes() == source_failed_bytes
    state = read_run_state(run_dir, queue_root)
    decision = json.loads(
        (
            queue_root
            / "identity-replacement-receipts"
            / f"{request['job_id']}.json"
        ).read_text(encoding="utf-8")
    )
    assert state["status"] == "active"
    assert state["last_job_id"] == replacement_job_id
    assert state["failed_external_job_replacement"]["source_job_id"] == request["job_id"]
    assert state["identity_replacement_receipt"] == (
        f"identity-replacement-receipts/{request['job_id']}.json"
    )
    assert decision["identity_envelope"] == state["identity_envelope"]
    assert not (queue_root / "inbox" / f"{request['job_id']}.json").exists()

    coordinator.atomic_write_json(
        queue_root / "inbox" / f"{replacement_job_id}.json",
        {
            "schema_version": 1,
            "job_id": replacement_job_id,
            "request_sha256": request["request_sha256"],
            "model": request["model"],
            "completed_at": "2026-08-25T12:05:00+08:00",
            "result": {"ok": True},
        },
    )
    assert consume_external_response(queue_root, request) == {"ok": True}


def test_failed_external_job_replacement_result_continues_exact_run_without_actor_run_dir(
    tmp_path: Path,
) -> None:
    run_dir, queue_root, request, correlation_id = _failed_external_replacement_fixture(tmp_path)
    result = _replace_failed(run_dir, queue_root, request, correlation_id)
    replacement_job_id = str(result["replacement_job_id"])
    coordinator.atomic_write_json(
        queue_root / "inbox" / f"{replacement_job_id}.json",
        {
            "schema_version": 1,
            "job_id": replacement_job_id,
            "request_sha256": request["request_sha256"],
            "model": request["model"],
            "completed_at": "2026-08-25T12:05:00+08:00",
            "result": {"ok": True},
        },
    )
    shutil.rmtree(run_dir)

    summary = coordinator.cycle_once(
        queue_root,
        exact_run_ids=("v0393-synthetic-run",),
    )

    state = coordinator._read_run_state_by_id("v0393-synthetic-run", queue_root)
    assert summary["complete"] == 1
    assert summary["failed"] == 0
    assert state["status"] == "complete"
    assert state["result"]["recovered_failed_external_job"] == {
        "source_job_id": request["job_id"],
        "replacement_job_id": replacement_job_id,
        "decision": f"failed-external-job-replacements/{request['job_id']}.json",
    }
    assert state["result"]["external_result"] == {"ok": True}


def test_failed_external_job_replacement_dangling_run_blocks_automatic_sweeps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, queue_root, request, correlation_id = _failed_external_replacement_fixture(tmp_path)
    result = _replace_failed(run_dir, queue_root, request, correlation_id)
    replacement_job_id = str(result["replacement_job_id"])
    before = _file_snapshot(queue_root)
    shutil.rmtree(run_dir)
    sweep_calls: list[str] = []

    def observe_new_sweep(*_args, **_kwargs) -> dict[str, object]:
        sweep_calls.append("new")
        return {"status": "seeded", "created": 1, "created_run_ids": ["new-seeded-run"]}

    def observe_legacy_sweep(*_args, **_kwargs) -> dict[str, object]:
        sweep_calls.append("legacy")
        return {"status": "seeded", "created": 1, "created_run_ids": ["legacy-seeded-run"]}

    monkeypatch.setattr(coordinator, "seed_new_matrix_runs", observe_new_sweep)
    monkeypatch.setattr(coordinator, "seed_legacy_rewrite_runs", observe_legacy_sweep)

    summary = coordinator.cycle_once(
        queue_root,
        repo_root=tmp_path,
        new_matrix_sweep=True,
        legacy_sweep=True,
        legacy_state_root=tmp_path / "publisher-state",
        tick=lambda *_args: pytest.fail("dangling replacement must block before tick"),
        process=lambda _root: pytest.fail("dangling replacement must not run provider"),
    )

    state = coordinator._read_run_state_by_id("v0393-synthetic-run", queue_root)
    assert summary == {
        "status": "blocked",
        "reason": "active run registry is dangling",
        "run_id": "v0393-synthetic-run",
        "active": 1,
        "complete": 0,
        "failed": 0,
        "runner": {"status": "idle"},
        "new_matrix_sweep": None,
        "legacy_sweep": None,
    }
    assert sweep_calls == []
    assert state["status"] == "active"
    assert state["last_job_id"] == replacement_job_id
    after = _file_snapshot(queue_root)
    before.pop("coordinator.lock", None)
    after.pop("coordinator.lock", None)
    assert after == before


def test_failed_external_job_replacement_resume_plan_and_execute_same_job(
    tmp_path: Path,
) -> None:
    run_dir, queue_root, request, correlation_id, replacement_job_id = (
        _failed_external_replacement_invalid_receipt_fixture(tmp_path)
    )
    before = _file_snapshot(queue_root)

    plan = _resume_replacement(
        run_dir,
        queue_root,
        request,
        correlation_id,
        execute=False,
        plan_only=True,
    )
    after_plan = _file_snapshot(queue_root)
    execute = _resume_replacement(run_dir, queue_root, request, correlation_id)

    assert plan["status"] == "plan_only"
    assert plan["replacement_job_id"] == replacement_job_id
    assert plan["local_preflight_message"] == (
        "no Antigravity Low model label for gemini-3.5-flash-lite"
    )
    assert after_plan == before
    assert _file_snapshot(queue_root) != before
    assert execute["status"] == "replacement_requeued"
    assert execute["replacement_job_id"] == replacement_job_id
    assert (queue_root / "outbox" / f"{replacement_job_id}.json").is_file()
    assert not (queue_root / "failed" / f"{replacement_job_id}.json").exists()
    assert (
        queue_root
        / "failed-external-job-replacements"
        / f"{request['job_id']}.{replacement_job_id}.failed-preserved.json"
    ).is_file()


def test_failed_external_job_replacement_resume_rejects_attempt_marker(
    tmp_path: Path,
) -> None:
    run_dir, queue_root, request, correlation_id, replacement_job_id = (
        _failed_external_replacement_invalid_receipt_fixture(tmp_path)
    )
    coordinator.atomic_write_json(
        queue_root / "production-attempts" / f"{replacement_job_id}.attempt",
        {
            "schema_version": 1,
            "job_id": replacement_job_id,
            "request_sha256": request["request_sha256"],
            "attempt_status": "started",
        },
    )
    before = _file_snapshot(queue_root)

    with pytest.raises(ValueError, match="resume evidence mismatch"):
        _resume_replacement(run_dir, queue_root, request, correlation_id)

    assert _file_snapshot(queue_root) == before


@pytest.mark.parametrize(
    ("fixture_model", "mutate", "match"),
    [
        (
            "gemini-3.5-flash-lite",
            lambda queue_root, request, replacement_job_id: coordinator.atomic_write_json(
                queue_root / "failed" / f"{replacement_job_id}.json",
                _failure_receipt(
                    {
                        "job_id": replacement_job_id,
                        "request_sha256": request["request_sha256"],
                    },
                    error_type="GeminiApiFailure",
                    error_code="API_TRANSPORT_ERROR",
                ),
            ),
            "resume evidence mismatch",
        ),
        (
            "gemini-3.5-flash",
            lambda _queue_root, _request, _replacement_job_id: None,
            "preflight proof is invalid",
        ),
    ],
)
def test_failed_external_job_replacement_resume_rejects_wrong_failure_or_reason(
    tmp_path: Path,
    fixture_model: str,
    mutate,
    match: str,
) -> None:
    run_dir, queue_root, request, correlation_id, replacement_job_id = (
        _failed_external_replacement_invalid_receipt_fixture(tmp_path, model=fixture_model)
    )
    mutate(queue_root, request, replacement_job_id)
    before = _file_snapshot(queue_root)

    with pytest.raises(ValueError, match=match):
        _resume_replacement(run_dir, queue_root, request, correlation_id)

    assert _file_snapshot(queue_root) == before


def test_failed_external_job_replacement_resume_replay_outbox_is_idempotent(
    tmp_path: Path,
) -> None:
    run_dir, queue_root, request, correlation_id, replacement_job_id = (
        _failed_external_replacement_invalid_receipt_fixture(tmp_path)
    )
    first = _resume_replacement(run_dir, queue_root, request, correlation_id)
    after_first = _file_snapshot(queue_root)
    replay = _resume_replacement(run_dir, queue_root, request, correlation_id)

    assert first["status"] == "replacement_requeued"
    assert replay["status"] == "already_replaced"
    assert replay["replacement_job_id"] == replacement_job_id
    assert _file_snapshot(queue_root) == after_first


@pytest.mark.parametrize(
    ("case", "mutate", "overrides"),
    [
        ("namespace", lambda _run_dir, _queue_root, _request: None, {"namespace": "drift"}),
        (
            "existing-success",
            lambda _run_dir, queue_root, request: coordinator.atomic_write_json(
                queue_root / "inbox" / f"{request['job_id']}.json",
                {
                    "schema_version": 1,
                    "job_id": request["job_id"],
                    "request_sha256": request["request_sha256"],
                    "model": request["model"],
                    "completed_at": "2026-08-25T12:01:00+08:00",
                    "result": {"ok": True},
                },
            ),
            {},
        ),
        (
            "non-active",
            lambda run_dir, queue_root, _request: (
                (state := read_run_state(run_dir, queue_root)).update({"status": "failed"}),
                coordinator._write_state(queue_root, state),
            ),
            {},
        ),
        (
            "last-job-drift",
            lambda run_dir, queue_root, _request: (
                (state := read_run_state(run_dir, queue_root)).update({"last_job_id": "0" * 40}),
                coordinator._write_state(queue_root, state),
            ),
            {},
        ),
        (
            "missing-archive",
            lambda _run_dir, queue_root, request: (
                queue_root / "archive" / f"{request['job_id']}.json"
            ).unlink(),
            {},
        ),
        (
            "missing-failed",
            lambda _run_dir, queue_root, request: (
                queue_root / "failed" / f"{request['job_id']}.json"
            ).unlink(),
            {},
        ),
    ],
)
def test_failed_external_job_replacement_rejects_drift_without_mutation(
    tmp_path: Path,
    case: str,
    mutate,
    overrides: dict[str, object],
) -> None:
    run_dir, queue_root, request, correlation_id = _failed_external_replacement_fixture(
        tmp_path / case
    )
    mutate(run_dir, queue_root, request)
    before = _file_snapshot(queue_root)

    with pytest.raises(ValueError):
        _replace_failed(
            run_dir,
            queue_root,
            request,
            correlation_id,
            **overrides,
        )

    assert _file_snapshot(queue_root) == before


def test_failed_external_job_replacement_rejects_second_authority_without_mutation(
    tmp_path: Path,
) -> None:
    run_dir, queue_root, request, correlation_id = _failed_external_replacement_fixture(tmp_path)
    _replace_failed(run_dir, queue_root, request, correlation_id)
    before = _file_snapshot(queue_root)

    with pytest.raises(ValueError, match="decision identity mismatch"):
        _replace_failed(
            run_dir,
            queue_root,
            request,
            correlation_id,
            authority_digest=_replacement_authority_digest("different-authority"),
        )

    assert _file_snapshot(queue_root) == before


def test_failed_external_job_replacement_runner_claim_race_leaves_no_executable_orphan(
    tmp_path: Path,
) -> None:
    run_dir, queue_root, request, correlation_id = _failed_external_replacement_fixture(tmp_path)

    result = _replace_failed(run_dir, queue_root, request, correlation_id)
    claimed = runner._claim_next(queue_root)

    assert claimed == queue_root / "processing" / f"{result['replacement_job_id']}.json"
    state = read_run_state(run_dir, queue_root)
    assert state["last_job_id"] == result["replacement_job_id"]
    assert (
        queue_root / "failed-external-job-replacements" / f"{request['job_id']}.json"
    ).is_file()
    assert state["failed_external_job_replacement"]["decision"] == (
        f"failed-external-job-replacements/{request['job_id']}.json"
    )


def test_failed_external_job_replacement_crash_before_staging_is_zero_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, queue_root, request, correlation_id = _failed_external_replacement_fixture(tmp_path)
    before = _file_snapshot(queue_root)
    original_atomic_write = coordinator.atomic_write_json

    def fail_staging(path: Path, payload: object) -> None:
        if path.name.endswith(".request-staged.json"):
            raise OSError("synthetic staging write failure")
        original_atomic_write(path, payload)

    monkeypatch.setattr(coordinator, "atomic_write_json", fail_staging)

    with pytest.raises(OSError, match="synthetic staging write failure"):
        _replace_failed(run_dir, queue_root, request, correlation_id)

    assert _file_snapshot(queue_root) == before
    assert runner._claim_next(queue_root) is None


def test_failed_external_job_replacement_decision_crash_leaves_only_non_executable_stage_and_replays(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, queue_root, request, correlation_id = _failed_external_replacement_fixture(tmp_path)
    original_atomic_write = coordinator.atomic_write_json

    def fail_decision(path: Path, payload: object) -> None:
        if path.parent == queue_root / "failed-external-job-replacements" and path.name == f"{request['job_id']}.json":
            raise OSError("synthetic decision write failure")
        original_atomic_write(path, payload)

    monkeypatch.setattr(coordinator, "atomic_write_json", fail_decision)

    with pytest.raises(OSError, match="synthetic decision write failure"):
        _replace_failed(run_dir, queue_root, request, correlation_id)

    assert runner._claim_next(queue_root) is None
    assert not list((queue_root / "outbox").glob("*.json"))
    assert not list((queue_root / "processing").glob("*.json"))
    assert list((queue_root / "failed-external-job-replacements").glob("*.request-staged.json"))

    monkeypatch.setattr(coordinator, "atomic_write_json", original_atomic_write)
    replay = _replace_failed(run_dir, queue_root, request, correlation_id)

    assert replay["status"] == "replacement_created"
    assert [path.name for path in (queue_root / "outbox").glob("*.json")] == [
        f"{replay['replacement_job_id']}.json"
    ]


def test_failed_external_job_replacement_state_crash_replays_without_second_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, queue_root, request, correlation_id = _failed_external_replacement_fixture(tmp_path)
    original_atomic_write = coordinator.atomic_write_json
    state_path = coordinator._state_path(str(json.loads((run_dir / "brief.json").read_text())["run_id"]), queue_root)

    def fail_state(path: Path, payload: object) -> None:
        if path == state_path and isinstance(payload, dict) and payload.get("failed_external_job_replacement"):
            raise OSError("synthetic state write failure")
        original_atomic_write(path, payload)

    monkeypatch.setattr(coordinator, "atomic_write_json", fail_state)

    with pytest.raises(OSError, match="synthetic state write failure"):
        _replace_failed(run_dir, queue_root, request, correlation_id)

    assert runner._claim_next(queue_root) is None
    assert not list((queue_root / "outbox").glob("*.json"))
    assert read_run_state(run_dir, queue_root)["last_job_id"] == request["job_id"]

    monkeypatch.setattr(coordinator, "atomic_write_json", original_atomic_write)
    replay = _replace_failed(run_dir, queue_root, request, correlation_id)
    second = _replace_failed(run_dir, queue_root, request, correlation_id)

    assert replay["status"] == "replacement_created"
    assert second["status"] == "already_replaced"
    assert [path.name for path in (queue_root / "outbox").glob("*.json")] == [
        f"{replay['replacement_job_id']}.json"
    ]


def test_failed_external_job_replacement_final_publish_crash_replays_same_job(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, queue_root, request, correlation_id = _failed_external_replacement_fixture(tmp_path)
    original_replace = coordinator.os.replace
    failed = False

    def fail_final_publish(source: Path, target: Path) -> None:
        nonlocal failed
        if (
            Path(source).name.endswith(".request-staged.json")
            and Path(target).parent == queue_root / "outbox"
            and not failed
        ):
            failed = True
            raise OSError("synthetic final publish failure")
        original_replace(source, target)

    monkeypatch.setattr(coordinator.os, "replace", fail_final_publish)

    with pytest.raises(OSError, match="synthetic final publish failure"):
        _replace_failed(run_dir, queue_root, request, correlation_id)

    assert runner._claim_next(queue_root) is None
    state = read_run_state(run_dir, queue_root)
    assert state["failed_external_job_replacement"]["source_job_id"] == request["job_id"]
    assert not list((queue_root / "outbox").glob("*.json"))

    replay = _replace_failed(run_dir, queue_root, request, correlation_id)

    assert replay["status"] == "already_replaced"
    assert [path.name for path in (queue_root / "outbox").glob("*.json")] == [
        f"{replay['replacement_job_id']}.json"
    ]


def test_failed_external_job_replacement_revalidates_archive_path_after_location_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, queue_root, request, correlation_id = _failed_external_replacement_fixture(tmp_path)
    original_locations = coordinator._known_request_locations
    source_archive = queue_root / "archive" / f"{request['job_id']}.json"
    replaced = False

    def replace_archive_after_location_check(root: Path, job_id: str) -> list[tuple[str, Path]]:
        nonlocal replaced
        result = original_locations(root, job_id)
        if root == queue_root and job_id == request["job_id"] and not replaced:
            replaced = True
            preserved = tmp_path / "preserved-source.json"
            os.replace(source_archive, preserved)
            source_archive.symlink_to(preserved)
        return result

    monkeypatch.setattr(coordinator, "_known_request_locations", replace_archive_after_location_check)
    before_state = read_run_state(run_dir, queue_root)

    with pytest.raises(ValueError, match="source request artifact is missing|regular file|JSON"):
        _replace_failed(run_dir, queue_root, request, correlation_id)

    assert read_run_state(run_dir, queue_root) == before_state
    assert runner._claim_next(queue_root) is None
    assert not list((queue_root / "failed-external-job-replacements").glob("*.json"))


def test_failed_external_job_replacement_cli_plan_only_and_execute(tmp_path: Path) -> None:
    run_dir, queue_root, request, correlation_id = _failed_external_replacement_fixture(tmp_path)
    base_command = [
        sys.executable,
        "-m",
        "scripts.agy_gemini_coordinator",
        "--queue-root",
        str(queue_root),
        "replace-failed-external-job",
        str(run_dir),
        "--job-queue-root",
        str(queue_root),
        "--lane",
        "new",
        "--run-id",
        str(json.loads((run_dir / "brief.json").read_text())["run_id"]),
        "--job-id",
        str(request["job_id"]),
        "--request-sha256",
        str(request["request_sha256"]),
        "--namespace",
        str(request["namespace"]),
        "--correlation-id",
        correlation_id,
        "--failure-category",
        "CLI_NONZERO",
        "--error-code",
        "CLI_NONZERO",
        "--authority-digest",
        _replacement_authority_digest(),
    ]
    before = _file_snapshot(queue_root)

    plan = subprocess.run(
        [*base_command, "--plan-only"],
        cwd=Path(coordinator.__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert plan.returncode == 0, plan.stderr
    assert json.loads(plan.stdout)["status"] == "plan_only"
    assert _file_snapshot(queue_root) == before

    execute = subprocess.run(
        [*base_command, "--execute"],
        cwd=Path(coordinator.__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert execute.returncode == 0, execute.stderr
    assert json.loads(execute.stdout)["status"] == "replacement_created"


def test_terminalize_pending_cli_defaults_to_dry_run_without_mutation(
    tmp_path: Path,
) -> None:
    run_id = "synthetic-operator-terminalization"
    run_dir, queue_root, request = _operator_pending_fixture(
        tmp_path,
        run_id,
    )
    before = _file_snapshot(queue_root)

    completed = _operator_cli(run_dir, queue_root, request)

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "status": "dry_run",
        "action": "terminalize_pending",
        "run_id": run_id,
        "lane": "i18n-rewrite",
        "job_id": request["job_id"],
        "request_sha256": request["request_sha256"],
        "model": "gemini-3.5-flash",
        "role": "writer",
        "transport_attempt": 1,
        "reason": "UNSUPPORTED_MODEL_CANARY_ABORT",
        "from": "outbox",
        "to": "archive",
    }
    assert _file_snapshot(queue_root) == before
    assert not list((queue_root / "archive").glob("*.json"))
    assert not list((queue_root / "operator-terminalizations").glob("*.json"))


RCA_STALE_SUCCESS_FIXTURE_ROOT = (
    Path(__file__).parent / "fixtures" / "new_lane_stale_success_rca_20260829"
)
RCA_STALE_SUCCESS_RUN_ID = "auto-new-v1-20260826-001-01"
RCA_STALE_SUCCESS_JOB_ID = "6972e8062d1aad444b30ec0fdf201bf8fce36d9d"


def _stale_success_rca_fixture(
    tmp_path: Path,
) -> tuple[Path, Path, Path, dict[str, str]]:
    run_dir = tmp_path / "gsc-copy" / RCA_STALE_SUCCESS_RUN_ID
    state_root = tmp_path / "queue"
    lane_root = state_root / "lanes" / "new"
    _write_brief(run_dir, RCA_STALE_SUCCESS_RUN_ID)
    state = register_run(run_dir, state_root)
    state["last_job_id"] = RCA_STALE_SUCCESS_JOB_ID
    coordinator._write_state(state_root, state)
    writer_path = run_dir / "attempts" / "01" / "writer-operation.json"
    writer_path.parent.mkdir(parents=True)
    shutil.copyfile(RCA_STALE_SUCCESS_FIXTURE_ROOT / "writer-operation.json", writer_path)
    fixture_paths = {
        "archive": lane_root / "archive" / f"{RCA_STALE_SUCCESS_JOB_ID}.json",
        "inbox": lane_root / "inbox" / f"{RCA_STALE_SUCCESS_JOB_ID}.json",
        "attempt": lane_root
        / "production-attempts"
        / f"{RCA_STALE_SUCCESS_JOB_ID}.attempt",
    }
    for name, target in fixture_paths.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(RCA_STALE_SUCCESS_FIXTURE_ROOT / f"{name}.json", target)
    inbox = json.loads(fixture_paths["inbox"].read_text(encoding="utf-8"))
    result_sha256 = hashlib.sha256(
        json.dumps(
            inbox["result"],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    expected = {
        "run_id": RCA_STALE_SUCCESS_RUN_ID,
        "job_id": RCA_STALE_SUCCESS_JOB_ID,
        "request_sha256": "6972e8062d1aad444b30ec0fdf201bf8fce36d9d1ef47912f70bc4b47e3a8a6e",
        "prompt_sha256": "b669a9c30674d89b9198c452d42d28a723d6f7bd3e9ccabe66c59f0097d57cf0",
        "schema_sha256": "86c426c3a0c3fcaaa5a6472a865675362d814cb48db64d0ce37dfc71fdfb52bd",
        "result_sha256": result_sha256,
        "registry": coordinator._canonical_json_file_sha256(
            read_run_state(run_dir, state_root)
        ),
        "writer_operation": _sha(writer_path),
        **{name: _sha(path) for name, path in fixture_paths.items()},
    }
    assert {
        key: expected[key]
        for key in ("writer_operation", "attempt", "inbox", "archive", "result_sha256")
    } == {
        "writer_operation": "1aca602672aefd06a38e9a97d29461d1d11ee02c172627e0e85f5f2dff25f546",
        "attempt": "ae052e389aafdd43033af145f67b69d081f91f850ad599b9f63a0df5ef8fa78d",
        "inbox": "28b65e223f5f36dfc21ab60b0801c3fbf085f0e25c500b426a29dc0662ef6a2b",
        "archive": "655a01e97a712e1aaefc9f99e0d2d5222ebff2391fd22f486eedab9c8218dbd0",
        "result_sha256": "2448751f5c4bd3a5b2b3a015c4b7e15ed84eaa61477b28c2171ca4f81b3c938f",
    }
    return run_dir, state_root, lane_root, expected


def _stale_success_cli(
    run_dir: Path,
    state_root: Path,
    lane_root: Path,
    expected: dict[str, str],
    *,
    execute: bool = False,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        "-m",
        "scripts.agy_gemini_coordinator",
        "--queue-root",
        str(state_root),
        "terminalize-stale-succeeded-writer",
        str(run_dir),
        "--job-queue-root",
        str(lane_root),
        "--lane",
        "new",
        "--run-id",
        expected["run_id"],
        "--job-id",
        expected["job_id"],
        "--request-sha256",
        expected["request_sha256"],
        "--prompt-sha256",
        expected["prompt_sha256"],
        "--schema-sha256",
        expected["schema_sha256"],
        "--result-sha256",
        expected["result_sha256"],
        "--expected-registry-digest",
        expected["registry"],
        "--expected-writer-operation-digest",
        expected["writer_operation"],
        "--expected-attempt-digest",
        expected["attempt"],
        "--expected-inbox-digest",
        expected["inbox"],
        "--expected-archive-digest",
        expected["archive"],
        "--reason",
        "CURRENT_ACCEPTANCE_REQUIRES_FRESH_WRITER",
    ]
    if execute:
        command.append("--execute")
    return subprocess.run(
        command,
        cwd=Path(coordinator.__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )


def test_stale_success_rca_exact_fixture_has_plan_only_operator_seam(
    tmp_path: Path,
) -> None:
    run_dir, state_root, lane_root, expected = _stale_success_rca_fixture(tmp_path)
    before = _file_snapshot(tmp_path)

    completed = _stale_success_cli(run_dir, state_root, lane_root, expected)

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["status"] == "READY_TO_EXECUTE"
    assert _file_snapshot(tmp_path) == before


def _stale_success_kwargs(
    lane_root: Path,
    expected: dict[str, str],
    **overrides: object,
) -> dict[str, object]:
    arguments: dict[str, object] = {
        "job_queue_root": lane_root,
        "lane": "new",
        "expected_run_id": expected["run_id"],
        "expected_job_id": expected["job_id"],
        "expected_request_sha256": expected["request_sha256"],
        "expected_prompt_sha256": expected["prompt_sha256"],
        "expected_schema_sha256": expected["schema_sha256"],
        "expected_result_sha256": expected["result_sha256"],
        "expected_registry_digest": expected["registry"],
        "expected_writer_operation_digest": expected["writer_operation"],
        "expected_attempt_digest": expected["attempt"],
        "expected_inbox_digest": expected["inbox"],
        "expected_archive_digest": expected["archive"],
        "reason": "CURRENT_ACCEPTANCE_REQUIRES_FRESH_WRITER",
        "execute": True,
    }
    arguments.update(overrides)
    return arguments


def test_stale_success_execute_is_receipt_first_immutable_and_idempotent(
    tmp_path: Path,
) -> None:
    run_dir, state_root, lane_root, expected = _stale_success_rca_fixture(tmp_path)
    protected = {
        name: path.read_bytes()
        for name, path in {
            "archive": lane_root / "archive" / f"{expected['job_id']}.json",
            "inbox": lane_root / "inbox" / f"{expected['job_id']}.json",
            "attempt": lane_root
            / "production-attempts"
            / f"{expected['job_id']}.attempt",
            "writer_operation": run_dir / "attempts" / "01" / "writer-operation.json",
        }.items()
    }
    before = _file_snapshot(tmp_path)

    first = coordinator.terminalize_stale_succeeded_writer(
        run_dir,
        state_root,
        **_stale_success_kwargs(lane_root, expected),
    )
    after_first = _file_snapshot(tmp_path)
    second = coordinator.terminalize_stale_succeeded_writer(
        run_dir,
        state_root,
        **_stale_success_kwargs(lane_root, expected),
    )

    changed = {path for path in before | after_first if before.get(path) != after_first.get(path)}
    state_path = coordinator._state_path(expected["run_id"], state_root)
    receipt_path = (
        state_root / "succeeded-provider-terminalizations" / f"{expected['job_id']}.json"
    )
    state = json.loads(state_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert first["status"] == "terminalized"
    assert second["status"] == "already_terminalized"
    assert first["provider_calls"] == first["reviewer_calls"] == first["publisher_calls"] == 0
    assert state["status"] == "failed"
    assert state["error_type"] == "SucceededProviderOutcomeTerminalized"
    assert receipt["status"] == "TERMINALIZED"
    assert changed == {
        str(state_path.relative_to(tmp_path)),
        str(receipt_path.relative_to(tmp_path)),
    }
    assert _file_snapshot(tmp_path) == after_first
    assert protected == {
        "archive": (lane_root / "archive" / f"{expected['job_id']}.json").read_bytes(),
        "inbox": (lane_root / "inbox" / f"{expected['job_id']}.json").read_bytes(),
        "attempt": (
            lane_root / "production-attempts" / f"{expected['job_id']}.attempt"
        ).read_bytes(),
        "writer_operation": (
            run_dir / "attempts" / "01" / "writer-operation.json"
        ).read_bytes(),
    }


def test_stale_success_cli_execute_wires_public_operator_seam(tmp_path: Path) -> None:
    run_dir, state_root, lane_root, expected = _stale_success_rca_fixture(tmp_path)

    completed = _stale_success_cli(
        run_dir,
        state_root,
        lane_root,
        expected,
        execute=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["status"] == "terminalized"
    assert read_run_state(run_dir, state_root)["status"] == "failed"


def test_stale_success_crash_after_receipt_replays_without_state_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, state_root, lane_root, expected = _stale_success_rca_fixture(tmp_path)
    state_path = coordinator._state_path(expected["run_id"], state_root)
    receipt_path = (
        state_root / "succeeded-provider-terminalizations" / f"{expected['job_id']}.json"
    )
    original = coordinator.atomic_write_json

    def fail_state(path: Path, payload: object) -> None:
        if path == state_path and isinstance(payload, dict) and payload.get("status") == "failed":
            raise OSError("synthetic state interruption after receipt")
        original(path, payload)

    monkeypatch.setattr(coordinator, "atomic_write_json", fail_state)
    with pytest.raises(OSError, match="synthetic state interruption after receipt"):
        coordinator.terminalize_stale_succeeded_writer(
            run_dir,
            state_root,
            **_stale_success_kwargs(lane_root, expected),
        )
    assert json.loads(receipt_path.read_text(encoding="utf-8"))["status"] == "PREPARED"
    assert json.loads(state_path.read_text(encoding="utf-8"))["status"] == "active"

    monkeypatch.setattr(coordinator, "atomic_write_json", original)
    recovered = coordinator.terminalize_stale_succeeded_writer(
        run_dir,
        state_root,
        **_stale_success_kwargs(lane_root, expected),
    )

    assert recovered["status"] == "terminalized"
    assert json.loads(receipt_path.read_text(encoding="utf-8"))["status"] == "TERMINALIZED"
    assert json.loads(state_path.read_text(encoding="utf-8"))["status"] == "failed"


@pytest.mark.parametrize(
    "override",
    [
        "expected_request_sha256",
        "expected_prompt_sha256",
        "expected_schema_sha256",
        "expected_result_sha256",
        "expected_registry_digest",
        "expected_writer_operation_digest",
        "expected_attempt_digest",
        "expected_inbox_digest",
        "expected_archive_digest",
    ],
)
def test_stale_success_hash_drift_is_zero_write(
    tmp_path: Path,
    override: str,
) -> None:
    run_dir, state_root, lane_root, expected = _stale_success_rca_fixture(tmp_path)
    before = _file_snapshot(tmp_path)

    with pytest.raises(ValueError, match="mismatch"):
        coordinator.terminalize_stale_succeeded_writer(
            run_dir,
            state_root,
            **_stale_success_kwargs(lane_root, expected, **{override: "0" * 64}),
        )

    assert _file_snapshot(tmp_path) == before


@pytest.mark.parametrize("boundary", ["second_job", "candidate", "review", "wrong_lane"])
def test_stale_success_boundaries_fail_closed(
    tmp_path: Path,
    boundary: str,
) -> None:
    run_dir, state_root, lane_root, expected = _stale_success_rca_fixture(tmp_path)
    overrides: dict[str, object] = {}
    if boundary == "second_job":
        second = run_dir / "attempts" / "02" / "writer-operation.json"
        second.parent.mkdir(parents=True)
        second.write_text("{}\n", encoding="utf-8")
    elif boundary == "candidate":
        (run_dir / "attempts" / "01" / "candidate.json").write_text("{}\n", encoding="utf-8")
    elif boundary == "review":
        (run_dir / "review.json").write_text("{}\n", encoding="utf-8")
    else:
        overrides["lane"] = "rewrite"
    before = _file_snapshot(tmp_path)

    with pytest.raises(ValueError):
        coordinator.terminalize_stale_succeeded_writer(
            run_dir,
            state_root,
            **_stale_success_kwargs(lane_root, expected, **overrides),
        )

    assert _file_snapshot(tmp_path) == before


@pytest.mark.parametrize("missing", ["archive", "inbox"])
def test_stale_success_missing_protected_evidence_is_zero_write(
    tmp_path: Path,
    missing: str,
) -> None:
    run_dir, state_root, lane_root, expected = _stale_success_rca_fixture(tmp_path)
    target = lane_root / missing / f"{expected['job_id']}.json"
    target.unlink()
    before = _file_snapshot(tmp_path)

    with pytest.raises(ValueError, match="regular file"):
        coordinator.terminalize_stale_succeeded_writer(
            run_dir,
            state_root,
            **_stale_success_kwargs(lane_root, expected),
        )

    assert _file_snapshot(tmp_path) == before


@pytest.mark.parametrize("artifact", ["archive", "inbox", "attempt", "writer_operation"])
def test_stale_success_rejects_symlinked_protected_artifact(
    tmp_path: Path,
    artifact: str,
) -> None:
    run_dir, state_root, lane_root, expected = _stale_success_rca_fixture(tmp_path)
    paths = {
        "archive": lane_root / "archive" / f"{expected['job_id']}.json",
        "inbox": lane_root / "inbox" / f"{expected['job_id']}.json",
        "attempt": lane_root / "production-attempts" / f"{expected['job_id']}.attempt",
        "writer_operation": run_dir / "attempts" / "01" / "writer-operation.json",
    }
    target = paths[artifact]
    preserved = tmp_path / f"preserved-{artifact}.json"
    target.replace(preserved)
    target.symlink_to(preserved)
    before = _file_snapshot(tmp_path)

    with pytest.raises(ValueError, match="regular file"):
        coordinator.terminalize_stale_succeeded_writer(
            run_dir,
            state_root,
            **_stale_success_kwargs(lane_root, expected),
        )

    assert target.is_symlink()
    assert _file_snapshot(tmp_path) == before


def test_stale_success_terminalization_releases_fresh_new_scheduler_frontier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, state_root, lane_root, expected = _stale_success_rca_fixture(tmp_path)
    coordinator.terminalize_stale_succeeded_writer(
        run_dir,
        state_root,
        **_stale_success_kwargs(lane_root, expected),
    )
    provider_calls = 0

    def prepare(_repo: Path, _prefix: str, *, output_root: Path, **_kwargs: object) -> list[Path]:
        fresh = output_root / "fresh-new-after-stale-terminalization"
        _write_brief(fresh, "fresh-new-after-stale-terminalization")
        return [fresh / "brief.json"]

    monkeypatch.setattr(coordinator.pipeline, "prepare_matrix_runs", prepare)
    scheduler = seed_new_matrix_runs(
        tmp_path / "repo",
        state_root,
        tmp_path / "fresh-runs",
        min_active_runs=1,
        max_new_runs=1,
        max_articles_per_run=1,
    )

    assert scheduler["status"] == "seeded"
    assert scheduler["created_run_ids"] == ["fresh-new-after-stale-terminalization"]
    assert provider_calls == 0


def test_terminalize_pending_cli_supports_split_state_and_job_queue_roots(
    tmp_path: Path,
) -> None:
    run_id = "synthetic-operator-split-root"
    run_dir = tmp_path / "runs" / run_id
    state_root = tmp_path / "queue"
    job_root = state_root / "lanes" / "i18n-rewrite"
    _write_brief(run_dir, run_id)
    state = register_run(run_dir, state_root)
    request = create_external_request(
        job_root,
        namespace="operator-split-root",
        role="writer",
        model="gemini-3.5-flash",
        prompt="公開 synthetic operator split root",
        response_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
        },
        transport_attempt=1,
    )

    def pending_tick(_run_dir: Path, _queue_root: Path) -> dict[str, object]:
        raise ExternalJobPending(str(request["job_id"]))

    assert coordinator._advance(
        state_root,
        state,
        pending_tick,
        job_queue_root=job_root,
    ) == "pending"
    before_state = coordinator._state_path(run_id, state_root).read_bytes()
    before_request = (
        job_root / "outbox" / f"{request['job_id']}.json"
    ).read_bytes()

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.agy_gemini_coordinator",
            "--queue-root",
            str(state_root),
            "terminalize-pending",
            str(run_dir),
            "--job-queue-root",
            str(job_root),
            "--lane",
            "i18n-rewrite",
            "--run-id",
            run_id,
            "--job-id",
            str(request["job_id"]),
            "--request-sha256",
            str(request["request_sha256"]),
            "--model",
            str(request["model"]),
            "--role",
            str(request["role"]),
            "--transport-attempt",
            "1",
            "--reason",
            "UNSUPPORTED_MODEL_CANARY_ABORT",
        ],
        cwd=Path(coordinator.__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["lane"] == "i18n-rewrite"
    assert coordinator._state_path(run_id, state_root).read_bytes() == before_state
    assert (
        job_root / "outbox" / f"{request['job_id']}.json"
    ).read_bytes() == before_request


def test_terminalize_pending_execute_writes_state_and_evidence_to_split_roots(
    tmp_path: Path,
) -> None:
    run_id = "synthetic-operator-split-execute"
    run_dir = tmp_path / "runs" / run_id
    state_root = tmp_path / "queue"
    job_root = state_root / "lanes" / "i18n-rewrite"
    _write_brief(run_dir, run_id)
    state = register_run(run_dir, state_root)
    request = create_external_request(
        job_root,
        namespace="operator-split-execute",
        role="writer",
        model="gemini-3.5-flash",
        prompt="公開 synthetic operator split execute",
        response_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
        },
        transport_attempt=1,
    )

    def pending_tick(_run_dir: Path, _queue_root: Path) -> dict[str, object]:
        raise ExternalJobPending(str(request["job_id"]))

    assert coordinator._advance(
        state_root,
        state,
        pending_tick,
        job_queue_root=job_root,
    ) == "pending"
    result = coordinator.terminalize_pending_job(
        run_dir,
        state_root,
        job_queue_root=job_root,
        lane="i18n-rewrite",
        expected_run_id=run_id,
        job_id=str(request["job_id"]),
        request_sha256=str(request["request_sha256"]),
        model=str(request["model"]),
        role=str(request["role"]),
        transport_attempt=1,
        reason="UNSUPPORTED_MODEL_CANARY_ABORT",
        execute=True,
    )

    assert result["status"] == "terminalized"
    assert (job_root / "archive" / f"{request['job_id']}.json").is_file()
    assert (
        job_root / "operator-terminalizations" / f"{request['job_id']}.json"
    ).is_file()
    terminal_state = read_run_state(run_dir, state_root)
    assert terminal_state["status"] == "failed"
    assert terminal_state["operator_terminalization"]["lane"] == "i18n-rewrite"
    assert terminal_state["operator_terminalization"]["decision"] == (
        f"lanes/i18n-rewrite/operator-terminalizations/{request['job_id']}.json"
    )


def test_terminalize_pending_execute_preserves_request_and_marks_run_terminal(
    tmp_path: Path,
) -> None:
    run_id = "synthetic-operator-execute"
    run_dir, queue_root, request = _operator_pending_fixture(
        tmp_path,
        run_id,
    )
    outbox_path = queue_root / "outbox" / f"{request['job_id']}.json"
    request_bytes = outbox_path.read_bytes()

    result = _operator_terminalize(run_dir, queue_root, request)

    assert result["status"] == "terminalized"
    assert not outbox_path.exists()
    archive_path = queue_root / "archive" / f"{request['job_id']}.json"
    assert archive_path.read_bytes() == request_bytes
    decision = json.loads(
        (queue_root / "operator-terminalizations" / f"{request['job_id']}.json").read_text()
    )
    assert decision["status"] == "terminalized"
    assert decision["request_file_sha256"] == hashlib.sha256(request_bytes).hexdigest()
    assert decision["reason"] == "UNSUPPORTED_MODEL_CANARY_ABORT"
    terminal_state = read_run_state(run_dir, queue_root)
    assert terminal_state["status"] == "failed"
    assert terminal_state["error_type"] == "OperatorTerminalized"
    assert terminal_state["last_job_id"] == request["job_id"]
    assert terminal_state["operator_terminalization"] == {
        "decision": f"operator-terminalizations/{request['job_id']}.json",
        "job_id": request["job_id"],
        "lane": "i18n-rewrite",
        "model": "gemini-3.5-flash",
        "reason": "UNSUPPORTED_MODEL_CANARY_ABORT",
        "request_sha256": request["request_sha256"],
        "role": "writer",
        "transport_attempt": 1,
    }
    assert not (queue_root / "failed" / f"{request['job_id']}.json").exists()
    assert not (queue_root / "inbox" / f"{request['job_id']}.json").exists()


def test_terminalize_pending_cli_execute_wires_public_command(tmp_path: Path) -> None:
    run_dir, queue_root, request = _operator_pending_fixture(
        tmp_path,
        "synthetic-operator-cli-execute",
    )

    completed = _operator_cli(run_dir, queue_root, request, execute=True)

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["status"] == "terminalized"
    assert read_run_state(run_dir, queue_root)["status"] == "failed"


def _operator_pending_fixture(
    tmp_path: Path,
    run_id: str,
) -> tuple[Path, Path, dict[str, object]]:
    run_dir = tmp_path / "runs" / run_id
    queue_root = tmp_path / "queue"
    _write_brief(run_dir, run_id)
    state = register_run(run_dir, queue_root)
    request = create_external_request(
        queue_root,
        namespace="operator-fixture",
        role="writer",
        model="gemini-3.5-flash",
        prompt="公開 synthetic operator fixture",
        response_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
        },
        transport_attempt=1,
    )

    def pending_tick(_run_dir: Path, _queue_root: Path) -> dict[str, object]:
        raise ExternalJobPending(str(request["job_id"]))

    assert coordinator._advance(queue_root, state, pending_tick) == "pending"
    return run_dir, queue_root, request


def _operator_terminalize(
    run_dir: Path,
    queue_root: Path,
    request: dict[str, object],
    **overrides: object,
) -> dict[str, object]:
    arguments: dict[str, object] = {
        "job_queue_root": queue_root,
        "lane": "i18n-rewrite",
        "expected_run_id": json.loads((run_dir / "brief.json").read_text())["run_id"],
        "job_id": request["job_id"],
        "request_sha256": request["request_sha256"],
        "model": request["model"],
        "role": request["role"],
        "transport_attempt": request.get("transport_attempt", 0),
        "reason": "UNSUPPORTED_MODEL_CANARY_ABORT",
        "execute": True,
    }
    arguments.update(overrides)
    return coordinator.terminalize_pending_job(
        run_dir,
        queue_root,
        **arguments,
    )


def _operator_cli(
    run_dir: Path,
    queue_root: Path,
    request: dict[str, object],
    *,
    execute: bool = False,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        "-m",
        "scripts.agy_gemini_coordinator",
        "--queue-root",
        str(queue_root),
        "terminalize-pending",
        str(run_dir),
        "--job-queue-root",
        str(queue_root),
        "--lane",
        "i18n-rewrite",
        "--run-id",
        str(json.loads((run_dir / "brief.json").read_text())["run_id"]),
        "--job-id",
        str(request["job_id"]),
        "--request-sha256",
        str(request["request_sha256"]),
        "--model",
        str(request["model"]),
        "--role",
        str(request["role"]),
        "--transport-attempt",
        str(request.get("transport_attempt", 0)),
        "--reason",
        "UNSUPPORTED_MODEL_CANARY_ABORT",
    ]
    if execute:
        command.append("--execute")
    return subprocess.run(
        command,
        cwd=Path(coordinator.__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )


def _file_snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_terminalize_pending_execute_is_byte_idempotent(tmp_path: Path) -> None:
    run_dir, queue_root, request = _operator_pending_fixture(
        tmp_path,
        "synthetic-operator-idempotent",
    )
    first = _operator_terminalize(run_dir, queue_root, request)
    after_first = _file_snapshot(queue_root)

    second = _operator_terminalize(run_dir, queue_root, request)

    assert first["status"] == "terminalized"
    assert second["status"] == "already_terminalized"
    assert _file_snapshot(queue_root) == after_first


@pytest.mark.parametrize(
    ("override", "value"),
    [
        ("expected_run_id", "different-run"),
        ("job_id", "0" * 40),
        ("request_sha256", "0" * 64),
        ("model", "gemini-2.5-flash-lite"),
        ("role", "reviewer"),
        ("transport_attempt", 2),
        ("reason", "UNBOUNDED_OPERATOR_REASON"),
    ],
)
def test_terminalize_pending_rejects_identity_mismatch_without_mutation(
    tmp_path: Path,
    override: str,
    value: object,
) -> None:
    run_dir, queue_root, request = _operator_pending_fixture(
        tmp_path,
        f"synthetic-operator-mismatch-{override}",
    )
    before = _file_snapshot(queue_root)

    with pytest.raises(ValueError):
        _operator_terminalize(
            run_dir,
            queue_root,
            request,
            **{override: value},
        )

    assert _file_snapshot(queue_root) == before


def test_terminalize_pending_rejects_processing_job_without_operator_write(
    tmp_path: Path,
) -> None:
    run_dir, queue_root, request = _operator_pending_fixture(
        tmp_path,
        "synthetic-operator-processing",
    )
    outbox_path = queue_root / "outbox" / f"{request['job_id']}.json"
    processing_path = queue_root / "processing" / outbox_path.name
    processing_path.parent.mkdir(parents=True)
    os.replace(outbox_path, processing_path)
    before = _file_snapshot(queue_root)

    with pytest.raises(ValueError, match="already processing"):
        _operator_terminalize(run_dir, queue_root, request)

    assert _file_snapshot(queue_root) == before
    assert not list((queue_root / "operator-terminalizations").glob("*.json"))


def test_terminalize_pending_recovers_after_state_write_interruption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = "synthetic-operator-recovery"
    run_dir, queue_root, request = _operator_pending_fixture(tmp_path, run_id)
    state_path = coordinator._state_path(run_id, queue_root)
    original_atomic_write = coordinator.atomic_write_json
    interrupted = False

    def interrupt_state_write(path: Path, payload: object) -> None:
        nonlocal interrupted
        if path == state_path and isinstance(payload, dict) and payload.get("status") == "failed":
            interrupted = True
            raise OSError("synthetic state write interruption")
        original_atomic_write(path, payload)

    monkeypatch.setattr(coordinator, "atomic_write_json", interrupt_state_write)
    with pytest.raises(OSError, match="synthetic state write interruption"):
        _operator_terminalize(run_dir, queue_root, request)
    assert interrupted is True
    assert read_run_state(run_dir, queue_root)["status"] == "active"
    assert (
        queue_root / "archive" / f"{request['job_id']}.json"
    ).is_file()
    decision_path = queue_root / "operator-terminalizations" / f"{request['job_id']}.json"
    assert json.loads(decision_path.read_text())["status"] == "terminalizing"

    monkeypatch.setattr(coordinator, "atomic_write_json", original_atomic_write)
    recovered = _operator_terminalize(run_dir, queue_root, request)

    assert recovered["status"] == "terminalized"
    assert read_run_state(run_dir, queue_root)["status"] == "failed"
    assert json.loads(decision_path.read_text())["status"] == "terminalized"


def test_terminalize_pending_rejects_existing_production_attempt_evidence(
    tmp_path: Path,
) -> None:
    run_dir, queue_root, request = _operator_pending_fixture(
        tmp_path,
        "synthetic-operator-attempted",
    )
    attempt_path = queue_root / "production-attempts" / f"{request['job_id']}.attempt"
    attempt_path.parent.mkdir(parents=True)
    attempt_path.write_text("existing-attempt-evidence\n", encoding="utf-8")
    before = _file_snapshot(queue_root)

    with pytest.raises(ValueError, match="production attempt evidence"):
        _operator_terminalize(run_dir, queue_root, request)

    assert _file_snapshot(queue_root) == before


def test_terminalize_pending_rejects_symlink_request(
    tmp_path: Path,
) -> None:
    run_dir, queue_root, request = _operator_pending_fixture(
        tmp_path,
        "synthetic-operator-symlink",
    )
    outbox_path = queue_root / "outbox" / f"{request['job_id']}.json"
    preserved_path = tmp_path / "preserved-request.json"
    os.replace(outbox_path, preserved_path)
    outbox_path.symlink_to(preserved_path)
    state_before = coordinator._state_path(
        "synthetic-operator-symlink",
        queue_root,
    ).read_bytes()
    request_before = preserved_path.read_bytes()

    with pytest.raises(ValueError, match="regular request file"):
        _operator_terminalize(run_dir, queue_root, request)

    assert outbox_path.is_symlink()
    assert preserved_path.read_bytes() == request_before
    assert coordinator._state_path(
        "synthetic-operator-symlink",
        queue_root,
    ).read_bytes() == state_before
    assert not list((queue_root / "operator-terminalizations").glob("*.json"))


def test_terminalize_pending_rejects_corrupt_decision_schema_version(
    tmp_path: Path,
) -> None:
    run_dir, queue_root, request = _operator_pending_fixture(
        tmp_path,
        "synthetic-operator-decision-version",
    )
    _operator_terminalize(run_dir, queue_root, request)
    decision_path = queue_root / "operator-terminalizations" / f"{request['job_id']}.json"
    decision = json.loads(decision_path.read_text())
    decision["schema_version"] = 2
    decision_path.write_text(json.dumps(decision), encoding="utf-8")
    state_before = read_run_state(run_dir, queue_root)

    with pytest.raises(ValueError, match="decision identity mismatch"):
        _operator_terminalize(run_dir, queue_root, request)

    assert read_run_state(run_dir, queue_root) == state_before
    assert not (tmp_path / "private-runs").exists()


def test_seed_legacy_rewrite_runs_ignores_non_rewrite_active_runs_for_capacity(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    state_root = tmp_path / "state"
    run_root = tmp_path / "private-runs"
    repo_root.mkdir()
    record = {
        "id": "LEGACY-003",
        "product": "tarot",
        "articleCategory": "tarot",
        "serial": "tarot-003",
        "slug": "legacy-three",
        "urlSlug": "legacy-three",
        "primaryKeyword": "塔羅舊文三",
        "title": "塔羅舊文三",
        "description": "描述三",
        "answer": "答案三",
        "faq": [{"question": "問三", "answer": "答三"}],
        "tags": ["塔羅"],
        "path": "articles/tarot/tarot-003",
    }
    current_body = [{"heading": "現況", "paragraphs": ["這是一段舊文內容，等待改得更貼近讀者生活。"]}]
    active_briefs = {
        "create-active": {"mode": "create", "articles": []},
        "translate-active": {
            "mode": "translate_existing",
            "lane": "i18n-new",
            "articles": [{"source_article_id": "V2-NEW-001", "locale": "en"}],
        },
        "rewrite-active": {
            "mode": "rewrite_existing_body",
            "articles": [{"article_id": "LEGACY-OTHER"}],
        },
    }
    for run_id, payload in active_briefs.items():
        active_run_dir = tmp_path / "active-runs" / run_id
        active_run_dir.mkdir(parents=True)
        (active_run_dir / "brief.json").write_text(
            json.dumps({"schema_version": 1, "run_id": run_id, **payload}),
            encoding="utf-8",
        )
        register_run(active_run_dir, queue_root)

    monkeypatch.setattr(coordinator.publisher, "legacy_article_records", lambda _repo: [record])
    monkeypatch.setattr(
        coordinator.pipeline,
        "_existing_rewrite_inventory",
        lambda _repo: {
            "LEGACY-003": {
                "id": "LEGACY-003",
                "record": record,
                "canonicalPath": "/articles/tarot/tarot-003",
                "currentBody": current_body,
                "published": "2026-01-01",
                "updated": "2026-01-01",
            }
        },
    )

    summary = seed_legacy_rewrite_runs(
        repo_root,
        queue_root,
        state_root,
        run_root,
        max_new_runs=2,
        max_active_runs=2,
        source_commit="c" * 40,
    )

    assert summary["status"] == "seeded"
    assert summary["created"] == 1
    assert summary["created_run_ids"] == ["legacy-auto-sweep-v1-tarot-003-legacy-003"]


def test_cycle_legacy_sweep_does_not_require_manual_register(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    record = {
        "id": "LEGACY-010",
        "product": "mbti",
        "articleCategory": "mbti",
        "serial": "mbti-010",
        "slug": "legacy-ten",
        "urlSlug": "legacy-ten",
        "primaryKeyword": "人格舊文十",
        "title": "人格舊文十",
        "description": "描述十",
        "answer": "答案十",
        "faq": [{"question": "問十", "answer": "答十"}],
        "tags": ["人格"],
        "path": "articles/mbti/mbti-010",
    }
    current_body = [{"heading": "現況", "paragraphs": ["這是一段舊文內容，等待改得更貼近讀者生活。"]}]
    monkeypatch.setattr(coordinator.publisher, "legacy_article_records", lambda _repo: [record])
    monkeypatch.setattr(
        coordinator.pipeline,
        "_existing_rewrite_inventory",
        lambda _repo: {
            "LEGACY-010": {
                "id": "LEGACY-010",
                "record": record,
                "canonicalPath": "/articles/mbti/mbti-010",
                "currentBody": current_body,
                "published": "2026-01-01",
                "updated": "2026-01-01",
            }
        },
    )
    monkeypatch.setattr(coordinator, "_head_sha", lambda _repo: "b" * 40)

    def pending_tick(_run_dir: Path, _queue_root: Path) -> dict[str, object]:
        raise ExternalJobPending("public-job-legacy-010")

    summary = cycle_once(
        tmp_path / "queue",
        tick=pending_tick,
        process=lambda _root: {"status": "idle"},
        repo_root=repo_root,
        legacy_sweep=True,
        legacy_state_root=tmp_path / "state",
        legacy_run_root=tmp_path / "private-runs",
    )

    assert summary["legacy_sweep"]["status"] == "seeded"
    assert summary["legacy_sweep"]["created_run_ids"] == ["legacy-auto-sweep-v1-mbti-010-legacy-010"]
    assert summary["active"] == 1
    assert summary["runner"] == {"status": "idle"}


def test_seed_new_matrix_runs_registers_only_one_run_and_article_per_cycle(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    run_root = tmp_path / "private-runs"
    repo_root.mkdir()
    calls: list[dict[str, object]] = []

    def fake_prepare_matrix_runs(
        _repo_root: Path,
        run_prefix: str,
        *,
        output_root: Path,
        limit: int,
        exclude_ids: set[str],
        max_articles_per_run: int,
    ) -> list[Path]:
        calls.append(
            {
                "run_prefix": run_prefix,
                "limit": limit,
                "exclude_ids": sorted(exclude_ids),
                "max_articles_per_run": max_articles_per_run,
            }
        )
        paths: list[Path] = []
        article_ids = [
            "V2-ZODIAC-ARIES-LOVE",
            "V2-ZODIAC-ARIES-WORK",
            "V2-ZODIAC-ARIES-MONEY",
            "V2-ZODIAC-ARIES-HEALTH",
            "V2-ZODIAC-ARIES-GROWTH",
        ]
        for index, article_id in enumerate(article_ids, start=1):
            run_dir = output_root / f"{run_prefix}-{index:02d}"
            run_dir.mkdir(parents=True)
            brief = {
                "schema_version": 1,
                "run_id": f"{run_prefix}-{index:02d}",
                "mode": "create",
                "articles": [{"target": {"id": article_id}}],
            }
            path = run_dir / "brief.json"
            path.write_text(json.dumps(brief), encoding="utf-8")
            paths.append(path)
        return paths

    monkeypatch.setattr(coordinator.pipeline, "prepare_matrix_runs", fake_prepare_matrix_runs)

    summary = seed_new_matrix_runs(
        repo_root,
        queue_root,
        run_root,
        min_active_runs=1,
        max_new_runs=1,
        max_articles_per_run=5,
    )

    assert summary["status"] == "seeded"
    assert summary["created"] == 1
    assert summary["created_run_ids"][0].startswith("auto-new-v1-")
    assert calls[0]["limit"] == 1
    assert calls[0]["max_articles_per_run"] == 1
    assert calls[0]["exclude_ids"] == []
    assert len(list((queue_root / "runs").glob("*.json"))) == 1
    state_path = next((queue_root / "runs").glob("*.json"))
    state = json.loads(state_path.read_text(encoding="utf-8"))
    brief = json.loads((Path(state["run_dir"]) / "brief.json").read_text(encoding="utf-8"))
    assert len(brief["articles"]) == 1


def _prepare_exact_brief_stub(
    _repo_root: Path,
    _run_prefix: str,
    *,
    output_root: Path,
    exact_run_id: str,
    **_kwargs,
) -> list[Path]:
    run_dir = output_root / exact_run_id
    _write_brief(run_dir, exact_run_id)
    return [run_dir / "brief.json"]


def test_seed_new_matrix_runs_reserves_exact_replacement_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    run_root = tmp_path / "private-runs"
    exact_run_id = "auto-new-v1-20260812-001-02"
    repo_root.mkdir()
    monkeypatch.setattr(
        coordinator.pipeline,
        "build_matrix_backlog",
        lambda _repo: [{"id": "V2-MBTI-INTJ-WORK", "primaryKeyword": "INTJ 工作"}],
    )
    monkeypatch.setattr(
        coordinator.pipeline,
        "_matrix_targets",
        lambda _repo, _backlog: {
            "V2-MBTI-INTJ-WORK": {
                "id": "V2-MBTI-INTJ-WORK",
                "section": "mbti",
                "product": "mbti",
                "slug": "v2-mbti-intj-work",
                "serial": "mbti-0001",
                "urlSlug": "mbti-0001",
                "published": "2026-08-12",
                "updated": "2026-08-12",
                "primaryKeyword": "INTJ 工作",
            }
        },
    )
    monkeypatch.setattr(coordinator.pipeline, "compact_publication_policy", lambda: {})

    summary = seed_new_matrix_runs(
        repo_root,
        queue_root,
        run_root,
        exact_run_id=exact_run_id,
    )

    assert summary["created_run_ids"] == [exact_run_id]
    brief_path = run_root / exact_run_id / "brief.json"
    assert json.loads(brief_path.read_text(encoding="utf-8"))["run_id"] == exact_run_id
    state = json.loads(coordinator._state_path(exact_run_id, queue_root).read_text(encoding="utf-8"))
    assert state["status"] == "active"
    assert state["correlation_id"]
    assert "reservation_token" not in state
    assert not (run_root / ".exact-run-staging").exists()


@pytest.mark.parametrize("collision_source", ["run_root", "queue"])
def test_seed_new_matrix_runs_rejects_exact_identity_collision_before_prepare(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    collision_source: str,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    run_root = tmp_path / "private-runs"
    exact_run_id = "auto-new-v1-20260812-001-02"
    repo_root.mkdir()
    if collision_source == "run_root":
        (run_root / exact_run_id).mkdir(parents=True)
    else:
        state_path = coordinator._state_path(exact_run_id, queue_root)
        state_path.parent.mkdir(parents=True)
        state_path.write_text(json.dumps({"run_id": exact_run_id, "status": "complete"}), encoding="utf-8")
    prepare_calls = 0

    def fail_if_prepared(*_args, **_kwargs) -> list[Path]:
        nonlocal prepare_calls
        prepare_calls += 1
        return []

    monkeypatch.setattr(coordinator.pipeline, "prepare_matrix_runs", fail_if_prepared)

    with pytest.raises(ValueError, match="exact run identity is already in use"):
        seed_new_matrix_runs(repo_root, queue_root, run_root, exact_run_id=exact_run_id)

    assert prepare_calls == 0
    assert not (run_root / exact_run_id / "brief.json").exists()


def test_seed_new_matrix_runs_rejects_unclosed_exact_identity_before_register(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    run_root = tmp_path / "private-runs"
    repo_root.mkdir()
    monkeypatch.setattr(coordinator.pipeline, "prepare_matrix_runs", lambda *_args, **_kwargs: [])

    with pytest.raises(ValueError, match="exact run identity could not be allocated"):
        seed_new_matrix_runs(
            repo_root,
            queue_root,
            run_root,
            exact_run_id="auto-new-v1-20260812-001-02",
        )

    assert not coordinator._state_path("auto-new-v1-20260812-001-02", queue_root).exists()


def test_seed_new_matrix_runs_cleans_owned_reservation_after_prepare_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    run_root = tmp_path / "private-runs"
    exact_run_id = "auto-new-v1-20260812-001-02"
    repo_root.mkdir()

    def fail_prepare(*_args, **_kwargs) -> list[Path]:
        raise RuntimeError("prepare failed")

    monkeypatch.setattr(coordinator.pipeline, "prepare_matrix_runs", fail_prepare)

    with pytest.raises(RuntimeError, match="prepare failed"):
        seed_new_matrix_runs(
            repo_root,
            queue_root,
            run_root,
            exact_run_id=exact_run_id,
        )

    assert not coordinator._state_path(exact_run_id, queue_root).exists()
    assert not (run_root / exact_run_id / "brief.json").exists()
    assert not (queue_root / "outbox").exists()


def test_activate_run_reservation_rejects_ownership_mismatch(
    tmp_path: Path,
) -> None:
    run_id = "auto-new-v1-20260812-001-02"
    run_root = tmp_path / "private-runs"
    run_dir = run_root / run_id
    staging_run_dir = run_root / ".exact-run-staging" / "owned-token" / run_id
    queue_root = tmp_path / "queue"
    _write_brief(staging_run_dir, run_id)
    state_path = coordinator._reserve_run_identity(
        run_id,
        run_dir,
        queue_root,
        "owned-correlation",
        "owned-token",
    )
    reservation = json.loads(state_path.read_text(encoding="utf-8"))

    with pytest.raises(ValueError, match="reservation ownership mismatch"):
        coordinator._activate_run_reservation(
            run_id,
            staging_run_dir,
            run_dir,
            queue_root,
            "owned-correlation",
            "foreign-token",
        )

    assert json.loads(state_path.read_text(encoding="utf-8")) == reservation
    assert not run_dir.exists()


def test_seed_new_matrix_runs_rejects_foreign_state_inserted_after_prepare(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    run_root = tmp_path / "private-runs"
    exact_run_id = "auto-new-v1-20260812-001-02"
    run_dir = run_root / exact_run_id
    state_path = coordinator._state_path(exact_run_id, queue_root)
    repo_root.mkdir()
    foreign_state = {
        "schema_version": 1,
        "run_id": exact_run_id,
        "run_dir": str(run_dir.resolve()),
        "status": "complete",
        "correlation_id": "other",
    }
    foreign_bytes = json.dumps(foreign_state, indent=2).encode("utf-8") + b"\n"

    staging_paths: list[Path] = []

    def prepare_then_replace_reservation(*_args, **kwargs) -> list[Path]:
        staging_run_dir = Path(kwargs["output_root"]) / exact_run_id
        staging_paths.append(staging_run_dir)
        _write_brief(staging_run_dir, exact_run_id)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_bytes(foreign_bytes)
        return [staging_run_dir / "brief.json"]

    monkeypatch.setattr(
        coordinator.pipeline,
        "prepare_matrix_runs",
        prepare_then_replace_reservation,
    )

    with pytest.raises(ValueError, match="reservation ownership mismatch"):
        seed_new_matrix_runs(
            repo_root,
            queue_root,
            run_root,
            exact_run_id=exact_run_id,
        )

    assert state_path.read_bytes() == foreign_bytes
    assert not (run_root / exact_run_id / "brief.json").exists()
    assert staging_paths and all(not path.exists() for path in staging_paths)
    assert not (run_root / ".exact-run-staging").exists()
    assert not (queue_root / "outbox").exists()


def test_exact_run_cleanup_does_not_unlink_foreign_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    run_root = tmp_path / "private-runs"
    exact_run_id = "auto-new-v1-20260812-001-02"
    state_path = coordinator._state_path(exact_run_id, queue_root)
    repo_root.mkdir()
    foreign_bytes = b'{"run_id":"foreign","status":"complete"}\n'
    original_rename = coordinator.os.rename

    def interleave_cleanup(source, target) -> None:
        if str(target).endswith(".cleanup"):
            state_path.write_bytes(foreign_bytes)
        original_rename(source, target)

    monkeypatch.setattr(coordinator.os, "rename", interleave_cleanup)
    monkeypatch.setattr(
        coordinator.pipeline,
        "prepare_matrix_runs",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("prepare failed")),
    )

    with pytest.raises(RuntimeError, match="prepare failed"):
        seed_new_matrix_runs(
            repo_root,
            queue_root,
            run_root,
            exact_run_id=exact_run_id,
        )

    assert state_path.read_bytes() == foreign_bytes
    assert not (run_root / exact_run_id).exists()
    assert not (run_root / ".exact-run-staging").exists()


def test_exact_run_activation_does_not_replace_interleaved_foreign_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    run_root = tmp_path / "private-runs"
    exact_run_id = "auto-new-v1-20260812-001-02"
    state_path = coordinator._state_path(exact_run_id, queue_root)
    repo_root.mkdir()
    foreign_bytes = b'{"run_id":"foreign","status":"complete"}\n'
    original_write = coordinator._write_json_exclusive

    def interleave_activation(path: Path, payload: object) -> None:
        if isinstance(payload, dict) and payload.get("status") == "active":
            path.write_bytes(foreign_bytes)
        original_write(path, payload)

    monkeypatch.setattr(coordinator, "_write_json_exclusive", interleave_activation)
    monkeypatch.setattr(coordinator.pipeline, "prepare_matrix_runs", _prepare_exact_brief_stub)

    with pytest.raises(ValueError, match="reservation ownership mismatch"):
        seed_new_matrix_runs(
            repo_root,
            queue_root,
            run_root,
            exact_run_id=exact_run_id,
        )

    assert state_path.read_bytes() == foreign_bytes
    assert not (run_root / exact_run_id).exists()
    assert not (run_root / ".exact-run-staging").exists()


def test_exact_run_publish_failure_cleans_only_owned_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    run_root = tmp_path / "private-runs"
    exact_run_id = "auto-new-v1-20260812-001-02"
    run_dir = run_root / exact_run_id
    repo_root.mkdir()
    original_rename = coordinator.os.rename

    def fail_publish(source, target) -> None:
        if Path(target) == run_dir:
            raise OSError("publish failed")
        original_rename(source, target)

    monkeypatch.setattr(coordinator.os, "rename", fail_publish)
    monkeypatch.setattr(coordinator.pipeline, "prepare_matrix_runs", _prepare_exact_brief_stub)

    with pytest.raises(OSError, match="publish failed"):
        seed_new_matrix_runs(
            repo_root,
            queue_root,
            run_root,
            exact_run_id=exact_run_id,
        )

    assert not coordinator._state_path(exact_run_id, queue_root).exists()
    assert not run_dir.exists()
    assert not (run_root / ".exact-run-staging").exists()


def test_exact_run_foreign_directory_is_preserved_before_activation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    run_root = tmp_path / "private-runs"
    exact_run_id = "auto-new-v1-20260812-001-02"
    run_dir = run_root / exact_run_id
    sentinel = run_dir / "foreign.bin"
    repo_root.mkdir()
    original_activate = coordinator._activate_run_reservation

    def insert_foreign_directory(*args, **kwargs) -> dict[str, object]:
        run_dir.mkdir(parents=True)
        sentinel.write_bytes(b"foreign-directory-bytes")
        return original_activate(*args, **kwargs)

    monkeypatch.setattr(coordinator, "_activate_run_reservation", insert_foreign_directory)
    monkeypatch.setattr(coordinator.pipeline, "prepare_matrix_runs", _prepare_exact_brief_stub)

    with pytest.raises(ValueError, match="exact run identity is already in use"):
        seed_new_matrix_runs(
            repo_root,
            queue_root,
            run_root,
            exact_run_id=exact_run_id,
        )

    assert sentinel.read_bytes() == b"foreign-directory-bytes"
    assert not coordinator._state_path(exact_run_id, queue_root).exists()
    assert not (run_root / ".exact-run-staging").exists()


def test_exact_run_stale_transition_fails_closed_before_prepare(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    run_root = tmp_path / "private-runs"
    exact_run_id = "auto-new-v1-20260812-001-02"
    state_path = coordinator._state_path(exact_run_id, queue_root)
    stale = state_path.with_name(f".{state_path.name}.stale.transition")
    repo_root.mkdir()
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"stale-token")
    prepare_calls = 0

    def count_prepare(*_args, **_kwargs) -> list[Path]:
        nonlocal prepare_calls
        prepare_calls += 1
        return []

    monkeypatch.setattr(coordinator.pipeline, "prepare_matrix_runs", count_prepare)

    with pytest.raises(ValueError, match="stale transaction"):
        seed_new_matrix_runs(
            repo_root,
            queue_root,
            run_root,
            exact_run_id=exact_run_id,
        )

    assert prepare_calls == 0
    assert stale.read_bytes() == b"stale-token"


def test_cycle_new_matrix_sweep_does_not_require_manual_register(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    def fake_prepare_matrix_runs(
        _repo_root: Path,
        run_prefix: str,
        *,
        output_root: Path,
        limit: int,
        exclude_ids: set[str],
        max_articles_per_run: int,
    ) -> list[Path]:
        run_dir = output_root / f"{run_prefix}-01"
        run_dir.mkdir(parents=True)
        (run_dir / "brief.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "run_id": f"{run_prefix}-01",
                    "mode": "create",
                    "articles": [{"target": {"id": "V2-MBTI-INTJ-WORK"}}],
                }
            ),
            encoding="utf-8",
        )
        return [run_dir / "brief.json"]

    monkeypatch.setattr(coordinator.pipeline, "prepare_matrix_runs", fake_prepare_matrix_runs)

    def pending_tick(_run_dir: Path, _queue_root: Path) -> dict[str, object]:
        raise ExternalJobPending("public-job-new-001")

    summary = cycle_once(
        tmp_path / "queue",
        tick=pending_tick,
        process=lambda _root: {"status": "idle"},
        repo_root=repo_root,
        new_matrix_sweep=True,
        new_matrix_run_root=tmp_path / "private-runs",
        new_matrix_min_active_runs=1,
        new_matrix_max_new_runs_per_cycle=1,
    )

    assert summary["new_matrix_sweep"]["status"] == "seeded"
    assert summary["new_matrix_sweep"]["created"] == 1
    assert summary["active"] == 1
    assert summary["runner"] == {"status": "idle"}


def test_cycle_blocks_dangling_active_registry_before_automatic_sweeps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    queue_root = tmp_path / "queue"
    repo_root.mkdir()
    coordinator.atomic_write_json(
        coordinator._state_path("dangling-active-run", queue_root),
        {
            "schema_version": 1,
            "run_id": "dangling-active-run",
            "run_dir": str(queue_root / "gsc-copy" / "dangling-active-run"),
            "status": "active",
        },
    )
    sweep_calls: list[str] = []

    def observe_new_sweep(*_args, **_kwargs) -> dict[str, object]:
        sweep_calls.append("new")
        return {"status": "idle", "created": 0, "created_run_ids": []}

    def observe_legacy_sweep(*_args, **_kwargs) -> dict[str, object]:
        sweep_calls.append("legacy")
        return {"status": "idle", "created": 0, "created_run_ids": []}

    monkeypatch.setattr(coordinator, "seed_new_matrix_runs", observe_new_sweep)
    monkeypatch.setattr(coordinator, "seed_legacy_rewrite_runs", observe_legacy_sweep)

    summary = cycle_once(
        queue_root,
        repo_root=repo_root,
        new_matrix_sweep=True,
        legacy_sweep=True,
        legacy_state_root=tmp_path / "publisher-state",
        tick=lambda *_args: {"status": "complete"},
        process=lambda _root: {"status": "idle"},
    )

    assert summary == {
        "status": "blocked",
        "reason": "active run registry is dangling",
        "run_id": "dangling-active-run",
        "active": 1,
        "complete": 0,
        "failed": 0,
        "runner": {"status": "idle"},
        "new_matrix_sweep": None,
        "legacy_sweep": None,
    }
    assert sweep_calls == []
    assert not (queue_root / "gsc-copy" / "dangling-active-run").exists()


def test_terminalized_identity_envelopes_block_new_and_legacy_reseeding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_root = tmp_path / "queue"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    identities = {
        "dangling-create": _expected_identity_envelope(
            "create",
            "new",
            ["V2-MBTI-INTJ-WORK"],
        ),
        "dangling-rewrite": _expected_identity_envelope(
            "rewrite_existing_body",
            "rewrite",
            ["LEGACY-001"],
        ),
    }
    for run_id, envelope in identities.items():
        run_dir = queue_root / "gsc-copy" / run_id
        state = {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(run_dir.resolve(strict=False)),
            "status": "active",
            "correlation_id": f"{run_id}-correlation",
            "identity_envelope": envelope,
        }
        coordinator.atomic_write_json(coordinator._state_path(run_id, queue_root), state)
        coordinator.terminalize_dangling_active_run(
            queue_root,
            expected_run_id=run_id,
            expected_registry_digest=coordinator._canonical_json_file_sha256(state),
            expected_run_dir=run_dir,
            reason="UNRECOVERABLE_RUN_DIR_MISSING",
            execute=True,
        )

    excluded_new_ids: list[set[str]] = []

    def prepare_new_runs(*_args, **kwargs) -> list[Path]:
        excluded_new_ids.append(set(kwargs["exclude_ids"]))
        return []

    legacy_record = {
        "id": "LEGACY-001",
        "product": "tarot",
        "articleCategory": "tarot",
        "serial": "tarot-001",
        "slug": "legacy-one",
        "urlSlug": "legacy-one",
        "primaryKeyword": "塔羅舊文一",
        "title": "塔羅舊文一",
        "description": "描述一",
        "answer": "答案一",
        "faq": [{"question": "問一", "answer": "答一"}],
        "tags": ["塔羅"],
        "path": "articles/tarot/tarot-001",
    }
    legacy_inventory = {
        "LEGACY-001": {
            "id": "LEGACY-001",
            "record": legacy_record,
            "canonicalPath": "/articles/tarot/tarot-001",
            "currentBody": [{"heading": "現況", "paragraphs": ["舊文內容"]}],
            "published": "2026-01-01",
            "updated": "2026-01-01",
        }
    }
    legacy_backlog = {
        "clean_approve": 0,
        "publish_ready": 0,
        "retry_deferred": 0,
        "retry_invalid": 0,
        "retry_exhausted": 0,
        "unattempted": 1,
        "unattempted_articles": ["LEGACY-001"],
    }
    monkeypatch.setattr(coordinator.pipeline, "prepare_matrix_runs", prepare_new_runs)
    monkeypatch.setattr(coordinator.publisher, "legacy_article_records", lambda _repo: [legacy_record])
    monkeypatch.setattr(
        coordinator.publisher,
        "summarize_legacy_rewrite_backlog",
        lambda *_args, **_kwargs: legacy_backlog,
    )
    monkeypatch.setattr(coordinator.pipeline, "_existing_rewrite_inventory", lambda _repo: legacy_inventory)
    monkeypatch.setattr(coordinator, "_head_sha", lambda _repo: "a" * 40)
    before = _file_snapshot(queue_root)

    summary = cycle_once(
        queue_root,
        repo_root=repo_root,
        new_matrix_sweep=True,
        new_matrix_run_root=tmp_path / "new-runs",
        legacy_sweep=True,
        legacy_state_root=tmp_path / "publisher-state",
        legacy_run_root=tmp_path / "legacy-runs",
        tick=lambda *_args: pytest.fail("terminalized runs must not tick"),
        process=lambda _root: {"status": "idle"},
    )

    after = _file_snapshot(queue_root)
    before.pop("coordinator.lock", None)
    after.pop("coordinator.lock", None)
    assert excluded_new_ids == [{"V2-MBTI-INTJ-WORK"}]
    assert summary["new_matrix_sweep"]["created_run_ids"] == []
    assert summary["legacy_sweep"]["created_run_ids"] == []
    assert not list((tmp_path / "new-runs").glob("*/brief.json"))
    assert not list((tmp_path / "legacy-runs").glob("*/brief.json"))
    assert after == before


@pytest.mark.parametrize(
    ("registry_lane", "brief_lane"),
    [("i18n-new", "i18n-rewrite"), ("i18n-rewrite", "i18n-new")],
)
def test_active_translation_identity_rejects_observed_lane_drift(
    tmp_path: Path,
    registry_lane: str,
    brief_lane: str,
) -> None:
    run_id = f"translation-lane-drift-{registry_lane}"
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True)
    coordinator.atomic_write_json(
        run_dir / "brief.json",
        {
            "schema_version": 1,
            "run_id": run_id,
            "mode": "translate_existing",
            "lane": brief_lane,
            "articles": [{"source_article_id": "NEW-001", "locale": "ja"}],
        },
    )
    state = {
        "schema_version": 1,
        "run_id": run_id,
        "run_dir": str(run_dir.resolve()),
        "status": "active",
        "identity_envelope": _expected_identity_envelope(
            "translate_existing",
            registry_lane,
            ["NEW-001"],
        ),
    }

    assert coordinator._active_run_integrity_block([state]) == {
        "status": "blocked",
        "reason": "active run registry is dangling",
        "run_id": run_id,
        "active": 1,
        "complete": 0,
        "failed": 0,
        "runner": {"status": "idle"},
        "new_matrix_sweep": None,
        "legacy_sweep": None,
    }


_MISSING = object()


def _production_shaped_legacy_translation_active_run(
    tmp_path: Path,
    *,
    run_id: str = "auto-i18n-ja-1414b75a404721e95e74",
    source_article_id: str = "V2-TAROT-DEATH-MONEY",
    registry_lane: str = "i18n-new",
    state_lane: object = "i18n-new",
    brief_lane: object = _MISSING,
    state_mode: object = _MISSING,
    routing_schema_version: object = _MISSING,
) -> tuple[Path, Path, Path]:
    queue_root = tmp_path / "queue"
    repo_root = tmp_path / "repo"
    run_dir = (queue_root / "gsc-copy" / run_id).resolve()
    repo_root.mkdir(parents=True)
    run_dir.mkdir(parents=True)
    brief: dict[str, object] = {
        "schema_version": 1,
        "run_id": run_id,
        "mode": "translate_existing",
        "source_commit": "a" * 40,
        "generation": 5,
        "articles": [
            {
                "source_article_id": source_article_id,
                "locale": "ja",
                "article_id": f"{source_article_id}:ja",
            }
        ],
    }
    if brief_lane is not _MISSING:
        brief["lane"] = brief_lane
    coordinator.atomic_write_json(run_dir / "brief.json", brief)

    state: dict[str, object] = {
        "schema_version": 1,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "status": "active",
        "correlation_id": f"{run_id}-correlation",
        "active_generation": 5,
        "next_generation": 5,
        "semantic_budget": 1,
        "identity_envelope": _expected_identity_envelope(
            "translate_existing",
            registry_lane,
            [source_article_id],
        ),
    }
    if state_lane is not _MISSING:
        state["lane"] = state_lane
    if state_mode is not _MISSING:
        state["mode"] = state_mode
    if routing_schema_version is not _MISSING:
        state["routing_schema_version"] = routing_schema_version
    coordinator.atomic_write_json(coordinator._state_path(run_id, queue_root), state)
    return queue_root, repo_root, run_dir


def test_active_legacy_translation_missing_brief_lane_uses_valid_current_identity_without_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_root, repo_root, _run_dir = _production_shaped_legacy_translation_active_run(
        tmp_path,
    )
    calls = {"tick": 0, "process": 0}
    monkeypatch.setattr(coordinator.publisher, "legacy_article_ids", lambda _repo: set())

    def complete_tick(_run_dir: Path, _job_queue_root: Path) -> dict[str, object]:
        calls["tick"] += 1
        return {"status": "synthetic-complete"}

    def provider_process(*_args, **_kwargs) -> dict[str, str]:
        calls["process"] += 1
        return {"status": "processed"}

    summary = cycle_once(
        queue_root,
        tick=complete_tick,
        process=provider_process,
        repo_root=repo_root,
        lane_mode=True,
        exact_run_ids=["auto-i18n-ja-1414b75a404721e95e74"],
    )

    assert summary.get("reason") != "active run registry is dangling", {
        "summary": summary,
        "calls": calls,
    }
    assert summary == {
        "status": "ok",
        "active": 0,
        "complete": 1,
        "failed": 0,
        "runner": {"status": "idle"},
        "new_matrix_sweep": None,
        "legacy_sweep": None,
        "lanes": {
            "new": {"active": 0, "queued": 0, "processing": 0},
            "rewrite": {"active": 0, "queued": 0, "processing": 0},
            "i18n-new": {"active": 0, "queued": 0, "processing": 0},
            "i18n-rewrite": {"active": 0, "queued": 0, "processing": 0},
        },
        "migrated_jobs": None,
    }, {"summary": summary, "calls": calls}
    assert calls == {"tick": 1, "process": 0}


def test_active_legacy_translation_partial_lane_selector_uses_identity_without_migration(
    tmp_path: Path,
) -> None:
    queue_root, _repo_root, _run_dir = _production_shaped_legacy_translation_active_run(
        tmp_path,
    )
    state_path = coordinator._state_path(
        "auto-i18n-ja-1414b75a404721e95e74",
        queue_root,
    )
    state = json.loads(state_path.read_text(encoding="utf-8"))
    before_bytes = state_path.read_bytes()

    assert coordinator._lane_for_state(state, set(), queue_root=queue_root) == "i18n-new"
    assert state_path.read_bytes() == before_bytes


def test_active_guard_accepts_missing_brief_lane_with_matching_state_lane_without_state_mode(
    tmp_path: Path,
) -> None:
    queue_root, _repo_root, _run_dir = _production_shaped_legacy_translation_active_run(
        tmp_path,
    )
    state_path = coordinator._state_path(
        "auto-i18n-ja-1414b75a404721e95e74",
        queue_root,
    )
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert "mode" not in state
    assert "routing_schema_version" not in state
    coordinator.atomic_write_json(state_path, state)

    assert coordinator._active_run_integrity_block([state]) is None


@pytest.mark.parametrize(
    ("state_lane", "brief_lane"),
    [
        (_MISSING, _MISSING),
        ("new", _MISSING),
        ("i18n-rewrite", _MISSING),
        ("i18n-new", "i18n-rewrite"),
    ],
)
def test_active_legacy_translation_identity_fails_closed_for_lane_authority_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    state_lane: object,
    brief_lane: object,
) -> None:
    queue_root, repo_root, _run_dir = _production_shaped_legacy_translation_active_run(
        tmp_path,
        state_lane=state_lane,
        brief_lane=brief_lane,
    )
    calls = {"tick": 0, "process": 0}
    monkeypatch.setattr(coordinator.publisher, "legacy_article_ids", lambda _repo: set())

    summary = cycle_once(
        queue_root,
        tick=lambda *_args: calls.__setitem__("tick", calls["tick"] + 1) or {"status": "unreachable"},
        process=lambda *_args, **_kwargs: calls.__setitem__("process", calls["process"] + 1) or {"status": "unreachable"},
        repo_root=repo_root,
        lane_mode=True,
        exact_run_ids=["auto-i18n-ja-1414b75a404721e95e74"],
    )

    assert summary == {
        "status": "blocked",
        "reason": "active run registry is dangling",
        "run_id": "auto-i18n-ja-1414b75a404721e95e74",
        "active": 1,
        "complete": 0,
        "failed": 0,
        "runner": {"status": "idle"},
        "new_matrix_sweep": None,
        "legacy_sweep": None,
    }
    assert calls == {"tick": 0, "process": 0}


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown_routing_schema",
        "state_mode_without_routing_schema",
        "invalid_identity_digest",
        "non_translation_envelope",
    ],
)
def test_active_legacy_translation_partial_selector_fails_closed_for_invalid_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    queue_root, repo_root, _run_dir = _production_shaped_legacy_translation_active_run(
        tmp_path,
    )
    state_path = coordinator._state_path(
        "auto-i18n-ja-1414b75a404721e95e74",
        queue_root,
    )
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if mutation == "unknown_routing_schema":
        state["routing_schema_version"] = 999
    elif mutation == "state_mode_without_routing_schema":
        state["mode"] = "translate_existing"
    elif mutation == "invalid_identity_digest":
        state["identity_envelope"]["digest"] = "0" * 64
    elif mutation == "non_translation_envelope":
        state["lane"] = "new"
        state["identity_envelope"] = _expected_identity_envelope(
            "create",
            "new",
            ["V2-TAROT-DEATH-MONEY"],
        )
    else:
        raise AssertionError(mutation)
    coordinator.atomic_write_json(state_path, state)
    calls = {"tick": 0, "process": 0}
    monkeypatch.setattr(coordinator.publisher, "legacy_article_ids", lambda _repo: set())

    summary = cycle_once(
        queue_root,
        tick=lambda *_args: calls.__setitem__("tick", calls["tick"] + 1) or {"status": "unreachable"},
        process=lambda *_args, **_kwargs: calls.__setitem__("process", calls["process"] + 1) or {"status": "unreachable"},
        repo_root=repo_root,
        lane_mode=True,
        exact_run_ids=["auto-i18n-ja-1414b75a404721e95e74"],
    )

    assert summary == {
        "status": "blocked",
        "reason": "active run registry is dangling",
        "run_id": "auto-i18n-ja-1414b75a404721e95e74",
        "active": 1,
        "complete": 0,
        "failed": 0,
        "runner": {"status": "idle"},
        "new_matrix_sweep": None,
        "legacy_sweep": None,
    }
    assert calls == {"tick": 0, "process": 0}


def _durable_dangling_state(
    tmp_path: Path,
    run_id: str,
) -> tuple[Path, Path, Path, dict[str, object]]:
    queue_root = tmp_path / "queue"
    run_dir = queue_root / "gsc-copy" / run_id
    state = {
        "schema_version": 1,
        "run_id": run_id,
        "run_dir": str(run_dir.resolve(strict=False)),
        "status": "active",
        "correlation_id": f"{run_id}-correlation",
        "identity_envelope": _expected_identity_envelope(
            "create",
            "new",
            ["V2-MBTI-INTJ-WORK"],
        ),
    }
    state_path = coordinator._state_path(run_id, queue_root)
    coordinator.atomic_write_json(state_path, state)
    return queue_root, run_dir, state_path, state


def test_dangling_terminalization_receipt_is_verifiable_and_idempotent(
    tmp_path: Path,
) -> None:
    queue_root, run_dir, state_path, state = _durable_dangling_state(
        tmp_path,
        "dangling-idempotent",
    )
    before_digest = coordinator._canonical_json_file_sha256(state)

    first = coordinator.terminalize_dangling_active_run(
        queue_root,
        expected_run_id="dangling-idempotent",
        expected_registry_digest=before_digest,
        expected_run_dir=run_dir,
        reason="UNRECOVERABLE_RUN_DIR_MISSING",
        execute=True,
    )
    after_first = _file_snapshot(queue_root)
    second = coordinator.terminalize_dangling_active_run(
        queue_root,
        expected_run_id="dangling-idempotent",
        expected_registry_digest=before_digest,
        expected_run_dir=run_dir,
        reason="UNRECOVERABLE_RUN_DIR_MISSING",
        execute=True,
    )

    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    receipt = json.loads(
        (
            queue_root
            / "dangling-active-terminalizations"
            / "dangling-idempotent.json"
        ).read_text(encoding="utf-8")
    )
    assert first["status"] == "terminalized"
    assert second["status"] == "already_terminalized"
    assert receipt["before_digest"] == before_digest
    assert receipt["after_digest"] == coordinator._canonical_json_file_sha256(persisted)
    assert receipt["before"]["identity_envelope"] == state["identity_envelope"]
    assert receipt["after"]["identity_envelope"] == state["identity_envelope"]
    assert _file_snapshot(queue_root) == after_first


def test_dangling_terminalization_accepts_legacy_state_without_identity(
    tmp_path: Path,
) -> None:
    queue_root, run_dir, state_path, state = _durable_dangling_state(
        tmp_path,
        "dangling-legacy-no-identity",
    )
    state.pop("identity_envelope")
    coordinator.atomic_write_json(state_path, state)
    before_digest = coordinator._canonical_json_file_sha256(state)

    result = coordinator.terminalize_dangling_active_run(
        queue_root,
        expected_run_id="dangling-legacy-no-identity",
        expected_registry_digest=before_digest,
        expected_run_dir=run_dir,
        reason="UNRECOVERABLE_RUN_DIR_MISSING",
        execute=True,
    )

    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    assert result["status"] == "terminalized"
    assert persisted["status"] == "failed"
    assert "identity_envelope" not in persisted


@pytest.mark.parametrize("case", ["digest", "existing", "non-active"])
def test_dangling_terminalization_negatives_have_zero_mutation(
    tmp_path: Path,
    case: str,
) -> None:
    queue_root, run_dir, state_path, state = _durable_dangling_state(
        tmp_path,
        f"dangling-{case}",
    )
    expected_digest = coordinator._canonical_json_file_sha256(state)
    expected_error = "registry digest mismatch"
    if case == "existing":
        run_dir.mkdir(parents=True)
        expected_error = "run directory is not missing"
    elif case == "non-active":
        state["status"] = "failed"
        coordinator.atomic_write_json(state_path, state)
        expected_digest = coordinator._canonical_json_file_sha256(state)
        expected_error = "requires active run"
    before = _file_snapshot(queue_root)

    with pytest.raises(ValueError, match=expected_error):
        coordinator.terminalize_dangling_active_run(
            queue_root,
            expected_run_id=f"dangling-{case}",
            expected_registry_digest=("0" * 64 if case == "digest" else expected_digest),
            expected_run_dir=run_dir,
            reason="UNRECOVERABLE_RUN_DIR_MISSING",
            execute=True,
        )

    assert _file_snapshot(queue_root) == before


def test_dangling_terminalization_rejects_concurrent_registry_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_root, run_dir, state_path, state = _durable_dangling_state(
        tmp_path,
        "dangling-concurrent-drift",
    )
    before_digest = coordinator._canonical_json_file_sha256(state)
    original_atomic_write = coordinator.atomic_write_json

    def drift_before_receipt(path: Path, payload: object) -> None:
        if path.parent.name == "dangling-active-terminalizations":
            drifted = json.loads(state_path.read_text(encoding="utf-8"))
            drifted["last_job_id"] = "9" * 40
            original_atomic_write(state_path, drifted)
        original_atomic_write(path, payload)

    monkeypatch.setattr(coordinator, "atomic_write_json", drift_before_receipt)
    with pytest.raises(ValueError, match="registry changed during terminalization"):
        coordinator.terminalize_dangling_active_run(
            queue_root,
            expected_run_id="dangling-concurrent-drift",
            expected_registry_digest=before_digest,
            expected_run_dir=run_dir,
            reason="UNRECOVERABLE_RUN_DIR_MISSING",
            execute=True,
        )

    assert json.loads(state_path.read_text(encoding="utf-8"))["last_job_id"] == "9" * 40
    assert not list((queue_root / "dangling-active-terminalizations").glob("*.json"))


def test_legacy_identity_source_authority_fails_closed_without_backfill(
    tmp_path: Path,
) -> None:
    queue_root = tmp_path / "queue"
    run_id = "legacy-conflicting-evidence"
    source_path = queue_root / "identity-evidence" / "source-request.json"
    replacement_path = queue_root / "identity-evidence" / "replacement-receipt.json"
    coordinator.atomic_write_json(
        source_path,
        {
            "schema_version": 1,
            "run_id": run_id,
            "identity_envelope": _expected_identity_envelope(
                "create",
                "new",
                ["V2-MBTI-INTJ-WORK"],
            ),
        },
    )
    coordinator.atomic_write_json(
        replacement_path,
        {
            "schema_version": 1,
            "run_id": run_id,
            "identity_envelope": _expected_identity_envelope(
                "create",
                "new",
                ["V2-MBTI-ENFP-LOVE"],
            ),
        },
    )
    state_path = coordinator._state_path(run_id, queue_root)
    coordinator.atomic_write_json(
        state_path,
        {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(queue_root / "gsc-copy" / run_id),
            "status": "failed",
            "identity_source_request": str(source_path.relative_to(queue_root)),
            "identity_replacement_receipt": str(replacement_path.relative_to(queue_root)),
        },
    )
    before = state_path.read_bytes()

    with pytest.raises(ValueError, match="legacy run identity source request cannot authorize backfill"):
        coordinator._registered_article_ids_by_mode(queue_root, "create")

    assert state_path.read_bytes() == before


def test_legacy_identity_rejects_arbitrary_queue_local_source_request(
    tmp_path: Path,
) -> None:
    queue_root = tmp_path / "queue"
    run_id = "legacy-unique-evidence"
    envelope = _expected_identity_envelope("create", "new", ["V2-MBTI-INTJ-WORK"])
    source_path = queue_root / "identity-evidence" / "source-request.json"
    coordinator.atomic_write_json(
        source_path,
        {
            "schema_version": 1,
            "run_id": run_id,
            "identity_envelope": envelope,
        },
    )
    state_path = coordinator._state_path(run_id, queue_root)
    coordinator.atomic_write_json(
        state_path,
        {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(queue_root / "gsc-copy" / run_id),
            "status": "failed",
            "identity_source_request": str(source_path.relative_to(queue_root)),
        },
    )

    before = state_path.read_bytes()

    with pytest.raises(ValueError, match="legacy run identity source request cannot authorize backfill"):
        coordinator._registered_article_ids_by_mode(queue_root, "create")

    assert state_path.read_bytes() == before


def test_legacy_identity_backfills_from_strict_replacement_lifecycle(
    tmp_path: Path,
) -> None:
    run_dir, queue_root, request, correlation_id = _failed_external_replacement_fixture(
        tmp_path,
        article_ids=["V2-MBTI-INTJ-WORK"],
    )
    _replace_failed(run_dir, queue_root, request, correlation_id)
    state_path = coordinator._state_path("v0393-synthetic-run", queue_root)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    expected = state.pop("identity_envelope")
    coordinator.atomic_write_json(state_path, state)

    assert coordinator._registered_article_ids_by_mode(queue_root, "create") == {
        "V2-MBTI-INTJ-WORK"
    }
    assert json.loads(state_path.read_text(encoding="utf-8"))["identity_envelope"] == expected


@pytest.mark.parametrize(
    "case",
    ["canonical_path", "request_digest", "run_binding", "schema", "request_uniqueness"],
)
def test_legacy_identity_replacement_evidence_requires_closed_trace(
    tmp_path: Path,
    case: str,
) -> None:
    run_dir, queue_root, request, correlation_id = _failed_external_replacement_fixture(tmp_path)
    _replace_failed(run_dir, queue_root, request, correlation_id)
    state_path = coordinator._state_path("v0393-synthetic-run", queue_root)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state.pop("identity_envelope")
    receipt_path = queue_root / str(state["identity_replacement_receipt"])
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if case == "canonical_path":
        copied_path = queue_root / "identity-evidence" / "copied-receipt.json"
        coordinator.atomic_write_json(copied_path, receipt)
        state["identity_replacement_receipt"] = str(copied_path.relative_to(queue_root))
    elif case == "request_digest":
        receipt["request_sha256"] = "0" * 64
        coordinator.atomic_write_json(receipt_path, receipt)
    elif case == "run_binding":
        receipt["run_id"] = "other-run"
        coordinator.atomic_write_json(receipt_path, receipt)
    elif case == "schema":
        receipt["schema_version"] = 2
        coordinator.atomic_write_json(receipt_path, receipt)
    else:
        source_job_id = str(request["job_id"])
        coordinator.atomic_write_json(
            queue_root / "processing" / f"{source_job_id}.json",
            request,
        )
    coordinator.atomic_write_json(state_path, state)
    before = state_path.read_bytes()

    with pytest.raises(ValueError, match="legacy run identity"):
        coordinator._registered_article_ids_by_mode(queue_root, "create")

    assert state_path.read_bytes() == before


def test_terminal_legacy_identity_missing_evidence_does_not_block_registry(
    tmp_path: Path,
) -> None:
    queue_root = tmp_path / "queue"
    run_id = "legacy-missing-evidence"
    state_path = coordinator._state_path(run_id, queue_root)
    coordinator.atomic_write_json(
        state_path,
        {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(queue_root / "gsc-copy" / run_id),
            "status": "failed",
        },
    )
    before = state_path.read_bytes()

    assert coordinator._registered_article_ids_by_mode(queue_root, "create") == set()
    assert state_path.read_bytes() == before


def test_active_legacy_identity_missing_evidence_still_fails_closed(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    run_id = "legacy-active-missing-evidence"
    coordinator.atomic_write_json(
        coordinator._state_path(run_id, queue_root),
        {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(queue_root / "gsc-copy" / run_id),
            "status": "active",
        },
    )

    with pytest.raises(ValueError, match="legacy run identity evidence is unavailable"):
        coordinator._registered_article_ids_by_mode(queue_root, "create")


def test_legacy_identity_backfills_from_canonical_durable_brief(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    run_id = "legacy-durable-brief"
    run_dir = (tmp_path / "gsc-copy" / run_id).resolve()
    run_dir.mkdir(parents=True)
    brief = {
        "run_id": run_id,
        "mode": "create",
        "lane": "new",
        "articles": [{"target": {"id": "V2-TAROT-DEATH-WORK"}}],
    }
    coordinator.atomic_write_json(run_dir / "brief.json", brief)
    state_path = coordinator._state_path(run_id, queue_root)
    coordinator.atomic_write_json(
        state_path,
        {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(run_dir),
            "status": "failed",
        },
    )

    assert coordinator._registered_article_ids_by_mode(queue_root, "create") == {
        "V2-TAROT-DEATH-WORK"
    }
    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    assert persisted["identity_envelope"] == coordinator._identity_envelope_from_brief(brief)


def test_legacy_translation_identity_backfills_lane_from_registry(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    run_id = "legacy-translation-lane"
    run_dir = (tmp_path / "translation-runs" / run_id).resolve()
    run_dir.mkdir(parents=True)
    brief = {
        "run_id": run_id,
        "mode": "translate_existing",
        "articles": [{"source_article_id": "ASTRO-BASE-03", "locale": "ja"}],
    }
    coordinator.atomic_write_json(run_dir / "brief.json", brief)
    state_path = coordinator._state_path(run_id, queue_root)
    coordinator.atomic_write_json(
        state_path,
        {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(run_dir),
            "status": "active",
            "lane": "i18n-rewrite",
        },
    )

    assert coordinator._registered_article_ids_by_mode(
        queue_root,
        "translate_existing",
    ) == {"ASTRO-BASE-03"}
    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    assert persisted["identity_envelope"]["lane"] == "i18n-rewrite"


def test_launchd_template_runs_coordinator_and_installer_is_valid_shell(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    installer = (repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh").read_text(encoding="utf-8")
    plist = plistlib.loads(
        (repo_root / "ops/launchd/com.pantheon.agy-gemini-coordinator.plist.example").read_bytes()
    )
    lane_plist = plistlib.loads(
        (repo_root / "ops/launchd/com.pantheon.agy-gemini-lane.plist.example").read_bytes()
    )
    arguments = plist["ProgramArguments"]

    assert arguments[1:3] == ["-m", "scripts.pantheon_content_runtime_manifest"]
    assert arguments[3:5] == ["barrier-exec", "--barrier"]
    separator = arguments.index("--")
    assert arguments[separator + 2 : separator + 4] == [
        "-m",
        "scripts.agy_gemini_coordinator",
    ]
    assert "--lane-mode" in arguments
    assert "--new-matrix-sweep" in arguments
    assert "--new-matrix-run-root" in arguments
    assert "--legacy-sweep" in arguments
    assert "--legacy-state-root" in arguments
    assert "--legacy-run-root" in arguments
    assert arguments[-1] == "cycle"
    assert plist["RunAtLoad"] is True
    assert lane_plist["ProgramArguments"][1:3] == [
        "-m",
        "scripts.pantheon_content_runtime_manifest",
    ]
    lane_arguments = lane_plist["ProgramArguments"]
    lane_separator = lane_arguments.index("--")
    assert lane_arguments[lane_separator + 2 : lane_separator + 4] == [
        "-m",
        "scripts.agy_gemini_runner",
    ]
    assert "--lane" in lane_plist["ProgramArguments"]
    assert lane_plist["ProgramArguments"][-1] == "process-once"
    assert plist["EnvironmentVariables"]["AGY_GEMINI_NEW_ONLY"] == "0"
    assert lane_plist["EnvironmentVariables"]["AGY_GEMINI_NEW_ONLY"] == "0"
    assert (
        lane_plist["EnvironmentVariables"]["AGY_GEMINI_RATE_LIMIT_COOLDOWN_SECONDS"]
        == "300"
    )
    assert (
        plist["EnvironmentVariables"]["AGY_GEMINI_RATE_LIMIT_COOLDOWN_SECONDS"]
        == "300"
    )
    assert "for LANE in new rewrite i18n-new i18n-rewrite" in installer
    assert 'LANE_LABEL="com.pantheon.agy-gemini-${LANE}"' in installer
    assert 'LAUNCHD_PATH="${PANTHEON_LAUNCHD_PATH:-' in installer
    assert "Set :EnvironmentVariables:PATH ${LAUNCHD_PATH}" in installer
    assert 'PRODUCTION_POOL_FILE="${AGY_GEMINI_CREDENTIAL_POOL_FILE:-}"' in installer
    assert 'MODEL_ROUTE_CONFIG_PATH="${REPO_ROOT}/config/agy_gemini_model_routes.v1.json"' in installer
    assert "load_model_route_config" in installer
    assert 'NEW_ONLY="${AGY_GEMINI_NEW_ONLY:-0}"' in installer
    assert 'USER_HOME_DIR="${PANTHEON_USER_HOME_DIR:-}"' in installer
    assert (
        'RATE_LIMIT_COOLDOWN_SECONDS="${AGY_GEMINI_RATE_LIMIT_COOLDOWN_SECONDS:-300}"'
        in installer
    )
    assert (
        'PRODUCTION_STATE_FILE="${AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE:-'
        in installer
    )
    assert "AGY_GEMINI_CREDENTIAL_POOL_FILE" not in lane_plist["EnvironmentVariables"]
    assert "AGY_GEMINI_CREDENTIAL_POOL_FILE" not in plist["EnvironmentVariables"]
    assert "AGY_WRITER_MODEL" not in plist["EnvironmentVariables"]
    assert "AGY_REVIEWER_MODEL" not in plist["EnvironmentVariables"]
    assert "AGY_WRITER_MODEL" not in lane_plist["EnvironmentVariables"]
    assert "AGY_REVIEWER_MODEL" not in lane_plist["EnvironmentVariables"]
    assert (
        "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE"
        not in lane_plist["EnvironmentVariables"]
    )
    assert (
        "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE"
        not in plist["EnvironmentVariables"]
    )
    assert "Add :EnvironmentVariables:AGY_GEMINI_CREDENTIAL_POOL_FILE string" in installer
    assert (
        "Add :EnvironmentVariables:AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE string"
        in installer
    )
    assert "Add :EnvironmentVariables:AGY_WRITER_MODEL string" in installer
    assert "Add :EnvironmentVariables:AGY_REVIEWER_MODEL string" in installer
    assert "optional_manifest_field actor_head" in installer
    assert "optional_manifest_field python_executable" in installer
    assert 'PYTHON_BIN="${PYTHON_REALPATH}"' in installer
    assert '--expected-python-executable "${PYTHON_BIN}"' in installer
    assert 'add_hardened_runtime_identity "${TEMP_PLIST}"' in installer
    assert 'add_hardened_runtime_identity "${LANE_TEMP_PLIST}"' in installer
    assert "for LANE in new rewrite i18n-new i18n-rewrite" in installer
    preflight_end = installer.index(
        'if launchctl print "gui/${USER_ID}/com.pantheon.agy-gemini-runner"'
    )
    first_plist_write = installer.index('cp "${TEMPLATE_PLIST}" "${TEMP_PLIST}"')
    first_control_write = installer.index('launchctl bootout "gui/${USER_ID}/${LABEL}"')
    assert "PRODUCTION_STATE_FILE" in installer[:preflight_end]
    assert preflight_end < first_plist_write < first_control_write
    completed = subprocess.run(
        ["bash", "-n", "scripts/install_agy_gemini_coordinator_launchd.sh"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    smoke = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.agy_gemini_coordinator",
            "--queue-root",
            str(tmp_path / "queue"),
            "cycle",
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert smoke.returncode == 0
    assert json.loads(smoke.stdout)["runner"] == {"status": "idle"}


def test_installer_rejects_relative_production_pool_before_install_side_effects(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    fake_bin = tmp_path / "bin"
    fake_home = tmp_path / "home"
    fake_bin.mkdir()
    pool_file = tmp_path / "relative-production-pool.json"
    pool_file.write_text("{}\n", encoding="utf-8")
    pool_file.chmod(0o600)
    cli_path = tmp_path / "agy"
    cli_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    cli_path.chmod(0o700)
    dscl = fake_bin / "dscl"
    dscl.write_text(f"#!/bin/sh\nprintf '%s\\n' 'NFSHomeDirectory: {fake_home}'\n", encoding="utf-8")
    dscl.chmod(0o700)
    launchctl_log = tmp_path / "launchctl.log"
    launchctl = fake_bin / "launchctl"
    launchctl.write_text(
        f"#!/bin/sh\nprintf '%s\\n' \"$*\" >> '{launchctl_log}'\nexit 1\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)
    env = os.environ.copy()
    env.pop("AGY_WRITER_MODEL", None)
    env.pop("AGY_REVIEWER_MODEL", None)
    env.update(
        {
            "AGY_GEMINI_CREDENTIAL_POOL_FILE": pool_file.name,
            "AGY_GEMINI_CLI_PATH": str(cli_path),
            "PANTHEON_PYTHON_PATH": sys.executable,
            "PATH": f"{fake_bin}:/usr/bin:/bin",
            "TMPDIR": str(tmp_path),
        }
    )

    completed = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "absolute path" in completed.stderr
    assert not fake_home.exists()
    assert not launchctl_log.exists()


def test_installer_rejects_relative_allocator_state_before_install_side_effects(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    fake_bin = tmp_path / "bin"
    fake_home = tmp_path / "home"
    fake_bin.mkdir()
    pool_file, _manifest_sha256 = _write_installer_pool(tmp_path)
    cli_path = tmp_path / "agy"
    cli_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    cli_path.chmod(0o700)
    dscl = fake_bin / "dscl"
    dscl.write_text(
        f"#!/bin/sh\nprintf '%s\\n' 'NFSHomeDirectory: {fake_home}'\n",
        encoding="utf-8",
    )
    dscl.chmod(0o700)
    launchctl_log = tmp_path / "launchctl.log"
    launchctl = fake_bin / "launchctl"
    launchctl.write_text(
        f"#!/bin/sh\nprintf '%s\\n' \"$*\" >> '{launchctl_log}'\nexit 1\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)
    env = os.environ.copy()
    env.update(
        {
            "AGY_GEMINI_CREDENTIAL_POOL_FILE": str(pool_file),
            "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE": "relative-state.json",
            "AGY_GEMINI_CLI_PATH": str(cli_path),
            "PANTHEON_PYTHON_PATH": sys.executable,
            "PATH": f"{fake_bin}:/usr/bin:/bin",
            "TMPDIR": str(tmp_path),
        }
    )

    completed = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "state path" in completed.stderr
    assert not fake_home.exists()
    assert not launchctl_log.exists()


def _write_installer_pool(tmp_path: Path) -> tuple[Path, str]:
    slots = []
    for index, slot_id in enumerate(("account-1", "account-2", "account-3"), 1):
        credential = tmp_path / f"credential-{index}"
        credential.write_text(
            f"synthetic-installer-credential-{index}-value\n",
            encoding="utf-8",
        )
        credential.chmod(0o600)
        slots.append({"slot_id": slot_id, "credential_file": str(credential)})
    payload = {
        "schema_version": 1,
        "pool_id": "pantheon-production-v1",
        "slots": slots,
    }
    pool = tmp_path / "production-pool.json"
    pool.write_text(json.dumps(payload), encoding="utf-8")
    pool.chmod(0o600)
    _payload, manifest_sha256 = runner._read_production_pool(pool)
    return pool, manifest_sha256


def _write_installer_state(
    path: Path,
    manifest_sha256: str,
    *,
    pool_id: str = "pantheon-production-v1",
) -> Path:
    lock = path.with_name(f"{path.name}.lock")
    lock.touch(mode=0o600)
    lock_stat = lock.stat()
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "pool_id": pool_id,
                "manifest_sha256": manifest_sha256,
                "last_ordinal": 1,
                "lock_device": lock_stat.st_dev,
                "lock_inode": lock_stat.st_ino,
            }
        ),
        encoding="utf-8",
    )
    path.chmod(0o600)
    return lock


def _write_installer_runtime_manifest(
    tmp_path: Path,
    *,
    publisher_root: Path | None = None,
    python_executable: Path | None = None,
) -> tuple[Path, Path, Path, Path]:
    repo_root = Path(__file__).resolve().parents[1]
    queue_root = tmp_path / "runtime-queue"
    state_root = publisher_root or tmp_path / "runtime-publisher-state"
    log_root = tmp_path / "runtime-logs"
    for path in (queue_root, state_root, log_root):
        path.mkdir(parents=True, exist_ok=True)
    manifest = runtime_manifest.build_manifest(
        actor_root=repo_root,
        queue_root=queue_root,
        publisher_state_root=state_root,
        log_root=log_root,
        identity="synthetic-installer:501",
        python_executable=python_executable,
        uv_executable=Path("/usr/bin/true"),
    )
    manifest_path = tmp_path / "runtime-manifest.json"
    runtime_manifest.write_manifest(manifest_path, manifest)
    return manifest_path, queue_root, state_root, log_root


def _installer_test_env(
    tmp_path: Path,
    *,
    pool: Path,
    state: Path,
    fail_plutil_call: int | None = None,
    python_executable: Path | None = None,
    python_path: Path | None = None,
) -> tuple[dict[str, str], Path, Path]:
    fake_bin = tmp_path / "bin"
    fake_home = tmp_path / "home"
    fake_bin.mkdir(exist_ok=True)
    cli_path = tmp_path / "agy"
    cli_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    cli_path.chmod(0o700)
    dscl = fake_bin / "dscl"
    dscl.write_text(
        f"#!/bin/sh\nprintf '%s\\n' 'NFSHomeDirectory: {fake_home}'\n",
        encoding="utf-8",
    )
    dscl.chmod(0o700)
    mutation_log = tmp_path / "launchctl-mutations.log"
    launchctl = fake_bin / "launchctl"
    launchctl.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then exit 1; fi\n"
        f"printf '%s\\n' \"$*\" >> '{mutation_log}'\n"
        "exit 0\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)
    if fail_plutil_call is not None:
        counter = tmp_path / "plutil-count"
        plutil = fake_bin / "plutil"
        plutil.write_text(
            "#!/bin/sh\n"
            f"count=$(cat '{counter}' 2>/dev/null || printf 0)\n"
            "count=$((count + 1))\n"
            f"printf '%s' \"$count\" > '{counter}'\n"
            f"if [ \"$count\" -eq {fail_plutil_call} ]; then exit 1; fi\n"
            "exec /usr/bin/plutil \"$@\"\n",
            encoding="utf-8",
        )
        plutil.chmod(0o700)
    manifest_path, queue_root, publisher_root, _log_root = _write_installer_runtime_manifest(
        tmp_path,
        python_executable=python_executable,
    )
    manifest_digest = runtime_manifest.load_manifest(manifest_path)["manifest_digest"]
    env = os.environ.copy()
    env.pop("AGY_WRITER_MODEL", None)
    env.pop("AGY_REVIEWER_MODEL", None)
    env.update(
        {
            "AGY_GEMINI_CREDENTIAL_POOL_FILE": str(pool),
            "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE": str(state),
            "AGY_GEMINI_CLI_PATH": str(cli_path),
            "PANTHEON_PYTHON_PATH": str(python_path or sys.executable),
            "PANTHEON_RUNTIME_MANIFEST_FILE": str(manifest_path),
            "PANTHEON_EXPECTED_RUNTIME_MANIFEST_DIGEST": manifest_digest,
            "AGY_GEMINI_QUEUE_ROOT": str(queue_root),
            "PANTHEON_CONTENT_PUBLISHER_ROOT": str(publisher_root),
            "PATH": f"{fake_bin}:/usr/bin:/bin",
            "TMPDIR": str(tmp_path),
        }
    )
    return env, fake_home, mutation_log


def _write_aggregate_stage_plist(
    path: Path,
    *,
    label: str,
    manifest: dict[str, object],
    manifest_digest: str | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    environment = {
        "PANTHEON_RUNTIME_MANIFEST_DIGEST": manifest_digest
        or manifest["manifest_digest"],
        "PANTHEON_RUNTIME_IDENTITY": manifest["identity"],
        "PANTHEON_RUNTIME_SERVICE_LABEL": label,
        "PANTHEON_RUNTIME_IDENTITY_DIGEST": manifest[
            "runtime_identity_digest"
        ],
        "PANTHEON_RUNTIME_CODE_DIGEST": manifest["runtime_digest"],
        "PANTHEON_RUNTIME_CONFIG_VERSION": manifest["config_version"],
        "PANTHEON_RUNTIME_GENERATION": manifest["generation"],
        "PANTHEON_RUNTIME_ACTOR_ROOT": manifest["actor_root"],
        "PANTHEON_RUNTIME_QUEUE_ROOT": manifest["queue_root"],
        "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT": manifest[
            "publisher_state_root"
        ],
        "PANTHEON_RUNTIME_LOG_ROOT": manifest["log_root"],
    }
    for field, environment_name in (
        ("actor_head", "PANTHEON_RUNTIME_ACTOR_HEAD"),
        ("python_executable", "PANTHEON_RUNTIME_PYTHON_EXECUTABLE"),
        ("uv_executable", "PANTHEON_RUNTIME_UV_EXECUTABLE"),
    ):
        if field in manifest:
            environment[environment_name] = manifest[field]
    with path.open("wb") as stream:
        plistlib.dump(
            {
                "Label": label,
                "WorkingDirectory": manifest["actor_root"],
                "EnvironmentVariables": environment,
            },
            stream,
        )
    path.chmod(0o600)


def _write_activation_stage_plist(
    path: Path,
    *,
    label: str,
    manifest: dict[str, object],
) -> None:
    barrier = (
        Path(str(manifest["publisher_state_root"]))
        / f"four-lane-activation-{manifest['generation']}.barrier"
    )
    ready_root = path.parent / "readiness" / str(manifest["generation"])
    child_module = (
        "scripts.pantheon_content_capacity_guard"
        if label == "com.pantheon.content-capacity-guard"
        else "scripts.agy_content_publisher"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    environment = {
        "PANTHEON_RUNTIME_MANIFEST_DIGEST": manifest[
            "manifest_digest"
        ],
        "PANTHEON_RUNTIME_IDENTITY": manifest["identity"],
        "PANTHEON_RUNTIME_SERVICE_LABEL": label,
        "PANTHEON_RUNTIME_IDENTITY_DIGEST": manifest[
            "runtime_identity_digest"
        ],
        "PANTHEON_RUNTIME_CODE_DIGEST": manifest["runtime_digest"],
        "PANTHEON_RUNTIME_CONFIG_VERSION": manifest["config_version"],
        "PANTHEON_RUNTIME_GENERATION": manifest["generation"],
        "PANTHEON_RUNTIME_ACTOR_ROOT": manifest["actor_root"],
        "PANTHEON_RUNTIME_QUEUE_ROOT": manifest["queue_root"],
        "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT": manifest[
            "publisher_state_root"
        ],
        "PANTHEON_RUNTIME_LOG_ROOT": manifest["log_root"],
    }
    for field, environment_name in (
        ("actor_head", "PANTHEON_RUNTIME_ACTOR_HEAD"),
        ("python_executable", "PANTHEON_RUNTIME_PYTHON_EXECUTABLE"),
        ("uv_executable", "PANTHEON_RUNTIME_UV_EXECUTABLE"),
    ):
        if field in manifest:
            environment[environment_name] = manifest[field]
    with path.open("wb") as stream:
        plistlib.dump(
            {
                "Label": label,
                "ProgramArguments": [
                    sys.executable,
                    "-m",
                    "scripts.pantheon_content_runtime_manifest",
                    "barrier-exec",
                    "--barrier",
                    str(barrier),
                    "--expected-digest",
                    str(manifest["manifest_digest"]),
                    "--manifest",
                    str(path.parent / "runtime-manifest.json"),
                    "--service-label",
                    label,
                    "--ready-root",
                    str(ready_root),
                    "--timeout",
                    "90",
                    "--",
                    sys.executable,
                    "-m",
                    child_module,
                ],
                "WorkingDirectory": manifest["actor_root"],
                "EnvironmentVariables": environment,
            },
            stream,
        )
    path.chmod(0o600)


def _write_publisher_normal_plist(
    path: Path,
    *,
    manifest: dict[str, object],
    max_runs: str = "1",
    exact_run_id: str | None = None,
    manifest_digest: str | None = None,
) -> None:
    _write_activation_stage_plist(
        path,
        label="com.pantheon.agy-content-publisher",
        manifest=manifest,
    )
    with path.open("rb") as stream:
        payload = plistlib.load(stream)
    payload["EnvironmentVariables"]["PANTHEON_RUNTIME_MANIFEST_DIGEST"] = (
        manifest_digest or manifest["manifest_digest"]
    )
    arguments = list(payload["ProgramArguments"])
    separator = arguments.index("--")
    child = arguments[separator + 1 :]
    child.extend(
        [
            "--repo-root",
            str(manifest["actor_root"]),
            "--queue-root",
            str(manifest["queue_root"]),
            "--state-root",
            str(manifest["publisher_state_root"]),
            "--max-runs",
            max_runs,
        ]
    )
    if exact_run_id is not None:
        child.extend(["--exact-run-id", exact_run_id])
    payload["ProgramArguments"] = arguments[: separator + 1] + child
    with path.open("wb") as stream:
        plistlib.dump(payload, stream)
    path.chmod(0o600)


def _write_activation_only_live_plists(
    launch_agents: Path,
    manifest: dict[str, object],
) -> dict[str, bytes]:
    payloads: dict[str, bytes] = {}
    for label in runtime_manifest.SERVICE_LABELS:
        path = launch_agents / f"{label}.plist"
        _write_activation_stage_plist(path, label=label, manifest=manifest)
        with path.open("rb") as stream:
            payload = plistlib.load(stream)
        payload["ProgramArguments"].insert(
            payload["ProgramArguments"].index("--"),
            "--activation-only",
        )
        with path.open("wb") as stream:
            plistlib.dump(payload, stream)
        path.chmod(0o600)
        payloads[label] = path.read_bytes()
    return payloads


def _write_publisher_terminal_live(source: Path, target: Path) -> None:
    _write_publisher_normal_live(source, target, start_interval=None)


def _write_publisher_scheduled_live(
    source: Path,
    target: Path,
    *,
    start_interval: int | str = 60,
) -> None:
    _write_publisher_normal_live(source, target, start_interval=start_interval)


def _write_publisher_normal_live(
    source: Path,
    target: Path,
    *,
    start_interval: int | str | None,
    keep_alive: bool | None = None,
) -> None:
    with source.open("rb") as stream:
        payload = plistlib.load(stream)
    arguments = list(payload["ProgramArguments"])
    if "--activation-only" in arguments:
        arguments.remove("--activation-only")
    payload["ProgramArguments"] = arguments
    payload["RunAtLoad"] = True
    if start_interval is None:
        payload.pop("StartInterval", None)
    else:
        payload["StartInterval"] = start_interval
    if keep_alive is None:
        payload.pop("KeepAlive", None)
    else:
        payload["KeepAlive"] = keep_alive
    with target.open("wb") as stream:
        plistlib.dump(payload, stream)
    target.chmod(0o600)


def _prepare_publisher_only_activation_fixture(
    tmp_path: Path,
    *,
    max_runs: str = "1",
    exact_run_id: str | None = "publisher-only-run-001",
    write_barrier: bool = True,
    stage_manifest_digest: str | None = None,
) -> tuple[dict[str, str], Path, Path, dict[str, object], Path, Path, dict[str, bytes]]:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    env["PANTHEON_ACTIVATION_CORRELATION_ID"] = "publisher-only-bounded"
    manifest = runtime_manifest.load_manifest(Path(env["PANTHEON_RUNTIME_MANIFEST_FILE"]))
    launch_agents = fake_home / "Library" / "LaunchAgents"
    launch_agents.mkdir(parents=True, exist_ok=True)
    live_payloads = _write_activation_only_live_plists(launch_agents, manifest)
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    stage_dir.mkdir(parents=True, exist_ok=True)
    (stage_dir / "manifest-digest").write_text(
        str(manifest["manifest_digest"]) + "\n",
        encoding="utf-8",
    )
    (stage_dir / "generation").write_text(
        str(manifest["generation"]) + "\n",
        encoding="utf-8",
    )
    (stage_dir / "publisher-max-runs").write_text(max_runs + "\n", encoding="utf-8")
    if exact_run_id is not None:
        (stage_dir / "publisher-exact-run-id").write_text(
            exact_run_id + "\n",
            encoding="utf-8",
        )
    _write_publisher_normal_plist(
        stage_dir / "com.pantheon.agy-content-publisher.plist",
        manifest=manifest,
        max_runs=max_runs,
        exact_run_id=exact_run_id,
        manifest_digest=stage_manifest_digest,
    )
    barrier = (
        Path(str(manifest["publisher_state_root"]))
        / f"four-lane-activation-{manifest['generation']}.barrier"
    )
    if write_barrier:
        ready = tmp_path / "publisher-only-ready"
        for label in runtime_manifest.SERVICE_LABELS:
            runtime_manifest.write_readiness_ack(ready, manifest, label)
        runtime_manifest.activate_barrier(barrier, ready, manifest)
    loaded = tmp_path / "publisher-only-loaded"
    loaded.mkdir()
    for label in runtime_manifest.SERVICE_LABELS:
        (loaded / label).touch()
    launchctl = tmp_path / "bin" / "launchctl"
    launchctl.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  label=${2##*/}\n"
        f"  [ -f '{loaded}/'$label ] || exit 113\n"
        "  printf '%s\\n' \"gui/$(id -u)/$label = {\"\n"
        "  printf '%s\\n' 'state = waiting'\n"
        f"  printf '%s\\n' 'path = {launch_agents}/'$label'.plist'\n"
        "  printf '%s\\n' '}'\n"
        "  exit 0\n"
        "fi\n"
        f"printf '%s\\n' \"$*\" >> '{mutation_log}'\n"
        "if [ \"$1\" = \"bootout\" ]; then\n"
        "  label=${2##*/}\n"
        f"  rm -f '{loaded}/'$label\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = \"bootstrap\" ]; then\n"
        "  label=${3##*/}\n"
        "  label=${label%.plist}\n"
        f"  touch '{loaded}/'$label\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)
    return env, fake_home, mutation_log, manifest, barrier, loaded, live_payloads


def _write_launchctl_that_records_publisher_child(
    launchctl: Path,
    *,
    loaded: Path,
    mutation_log: Path,
    child_log: Path,
) -> None:
    launchctl.write_text(
        f"#!{sys.executable}\n"
        "import os, plistlib, sys\n"
        "from pathlib import Path\n"
        f"loaded = Path({str(loaded)!r})\n"
        f"mutation_log = Path({str(mutation_log)!r})\n"
        f"child_log = Path({str(child_log)!r})\n"
        "args = sys.argv[1:]\n"
        "if args[:1] == ['print']:\n"
        "    label = args[1].split('/')[-1]\n"
        "    if not (loaded / label).exists():\n"
        "        sys.exit(113)\n"
        "    print('state = waiting')\n"
        "    sys.exit(0)\n"
        "with mutation_log.open('a', encoding='utf-8') as stream:\n"
        "    stream.write(' '.join(args) + '\\n')\n"
        "if args[:1] == ['bootout']:\n"
        "    label = args[1].split('/')[-1]\n"
        "    try:\n"
        "        (loaded / label).unlink()\n"
        "    except FileNotFoundError:\n"
        "        pass\n"
        "    sys.exit(0)\n"
        "if args[:1] == ['bootstrap']:\n"
        "    plist_path = Path(args[2])\n"
        "    with plist_path.open('rb') as stream:\n"
        "        payload = plistlib.load(stream)\n"
        "    label = payload['Label']\n"
        "    (loaded / label).touch()\n"
        "    runs = 2 if 'StartInterval' in payload or payload.get('KeepAlive') else 1\n"
        "    child_exit = int(os.environ.get('PUBLISHER_CHILD_EXIT_CODE', '0'))\n"
        "    with child_log.open('a', encoding='utf-8') as stream:\n"
        "        for index in range(runs):\n"
        "            stream.write(f'{label} run={index + 1} exit={child_exit}\\n')\n"
        "    sys.exit(0)\n"
        "sys.exit(0)\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)


def _replace_plist_manifest_path(path: Path, manifest_path: Path) -> None:
    with path.open("rb") as stream:
        payload = plistlib.load(stream)
    arguments = payload["ProgramArguments"]
    arguments[arguments.index("--manifest") + 1] = str(manifest_path)
    with path.open("wb") as stream:
        plistlib.dump(payload, stream)
    path.chmod(0o600)


def _write_launchctl_that_executes_publisher_during_settle(
    launchctl: Path,
    *,
    loaded: Path,
    mutation_log: Path,
    lifecycle_log: Path,
    launch_agents: Path,
) -> None:
    settling = loaded.parent / "publisher-bootstrap-settling"
    last_exit = loaded.parent / "publisher-bootstrap-last-exit"
    launchctl.write_text(
        f"#!{sys.executable}\n"
        "import json, os, plistlib, subprocess, sys\n"
        "from pathlib import Path\n"
        f"loaded = Path({str(loaded)!r})\n"
        f"mutation_log = Path({str(mutation_log)!r})\n"
        f"lifecycle_log = Path({str(lifecycle_log)!r})\n"
        f"launch_agents = Path({str(launch_agents)!r})\n"
        f"settling = Path({str(settling)!r})\n"
        f"last_exit = Path({str(last_exit)!r})\n"
        "args = sys.argv[1:]\n"
        "def append(path, line):\n"
        "    with path.open('a', encoding='utf-8') as stream:\n"
        "        stream.write(line + '\\n')\n"
        "if args[:1] == ['print']:\n"
        "    label = args[1].split('/')[-1]\n"
        "    if label == 'com.pantheon.agy-content-publisher' and settling.exists():\n"
        "        settling.unlink()\n"
        "        append(lifecycle_log, f'print label={label} state=settling')\n"
        "        sys.exit(1)\n"
        "    if not (loaded / label).exists():\n"
        "        sys.exit(113)\n"
        "    print(f'gui/{os.getuid()}/{label} = {{')\n"
        "    print('state = waiting')\n"
        "    print(f'path = {launch_agents / (label + \".plist\")}')\n"
        "    if label == 'com.pantheon.agy-content-publisher' and last_exit.exists():\n"
        "        print(f'last exit code = {last_exit.read_text()}')\n"
        "    print('}')\n"
        "    append(lifecycle_log, f'print label={label} state=stable')\n"
        "    sys.exit(0)\n"
        "with mutation_log.open('a', encoding='utf-8') as stream:\n"
        "    stream.write(' '.join(args) + '\\n')\n"
        "if args[:1] == ['bootout']:\n"
        "    label = args[1].split('/')[-1]\n"
        "    (loaded / label).unlink(missing_ok=True)\n"
        "    settling.unlink(missing_ok=True)\n"
        "    sys.exit(0)\n"
        "if args[:1] == ['bootstrap']:\n"
        "    plist_path = Path(args[2])\n"
        "    with plist_path.open('rb') as stream:\n"
        "        payload = plistlib.load(stream)\n"
        "    label = payload['Label']\n"
        "    child_env = os.environ.copy()\n"
        "    child_env.update(payload.get('EnvironmentVariables', {}))\n"
        "    child = subprocess.run(payload['ProgramArguments'], "
        "cwd=payload['WorkingDirectory'], env=child_env, "
        "text=True, capture_output=True, check=False)\n"
        "    append(lifecycle_log, json.dumps({'event': 'bootstrap-child', "
        "'returncode': child.returncode}, sort_keys=True))\n"
        "    (loaded / label).touch()\n"
        "    last_exit.write_text(str(child.returncode), encoding='utf-8')\n"
        "    if child.returncode != 0:\n"
        "        settling.touch()\n"
        "    sys.exit(0)\n"
        "sys.exit(0)\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)


def _write_legacy_capacity_guard_plist(
    path: Path,
    *,
    label: str = "com.pantheon.content-capacity-guard",
) -> bytes:
    payload = plistlib.dumps(
        {
            "Label": label,
            "ProgramArguments": ["python", "-m", f"legacy-{label}"],
            "EnvironmentVariables": {
                "PANTHEON_LEGACY_CAPACITY_GUARD": "1",
            },
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    path.chmod(0o600)
    return payload


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("AGY_GEMINI_NEW_ONLY", "true"),
        ("AGY_GEMINI_RATE_LIMIT_COOLDOWN_SECONDS", "0"),
        ("AGY_GEMINI_RATE_LIMIT_COOLDOWN_SECONDS", "3601"),
    ],
)
def test_installer_rejects_invalid_admission_config_before_side_effects(
    tmp_path: Path,
    variable: str,
    value: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    state = tmp_path / "round-robin-state.json"
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=state,
    )
    env[variable] = value

    completed = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert not fake_home.exists()
    assert not mutation_log.exists()


@pytest.mark.parametrize(
    "failure_class",
    [
        "pool-corrupt",
        "state-corrupt",
        "pool-mismatch",
        "lock-nonempty",
        "state-parent-unsafe",
    ],
)
def test_installer_metadata_failure_has_zero_target_or_control_side_effects(
    tmp_path: Path,
    failure_class: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, manifest_sha256 = _write_installer_pool(tmp_path)
    state_parent = tmp_path / "state"
    state_parent.mkdir(mode=0o700)
    state = state_parent / "round-robin-state.json"
    lock = _write_installer_state(state, manifest_sha256)
    if failure_class == "pool-corrupt":
        pool.write_text("{broken\n", encoding="utf-8")
    elif failure_class == "state-corrupt":
        state.write_text("{broken\n", encoding="utf-8")
    elif failure_class == "pool-mismatch":
        _write_installer_state(state, manifest_sha256, pool_id="other-pool")
    elif failure_class == "lock-nonempty":
        lock.write_text("unexpected", encoding="utf-8")
    else:
        state.unlink()
        lock.unlink()
        state_parent.chmod(0o777)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=state,
    )

    completed = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert not fake_home.exists()
    assert not mutation_log.exists()


def test_installer_preflight_builds_all_lane_plists_without_control_plane_mutation(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    state = tmp_path / "round-robin-state.json"
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=state,
    )

    completed = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--preflight",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "四條 lane runner preflight 通過" in completed.stdout
    assert not fake_home.exists()
    assert not mutation_log.exists()


def test_four_lane_recovery_coordinator_rejects_new_only_before_mutation(
    tmp_path: Path,
) -> None:
    """REG-PANTHEON-FOUR-LANE-REJECT-NEW-ONLY-001。"""
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    env["AGY_GEMINI_NEW_ONLY"] = "1"

    completed = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"), "--preflight"],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "四軌 recovery 禁止 new-only" in completed.stderr
    assert not fake_home.exists()
    assert not mutation_log.exists()


def test_four_lane_installer_separates_stage_and_activation_with_rollback() -> None:
    """REG-PANTHEON-FOUR-LANE-INSTALL-ROLLBACK-001。"""
    repo_root = Path(__file__).resolve().parents[1]
    installer = (repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh").read_text(
        encoding="utf-8"
    )

    assert 'ACTION}" == "--install"' in installer
    assert '"--activate"' in installer
    assert "ACTIVATION_BARRIER" in installer
    assert "rollback_activation" in installer
    assert "previous_loaded" in installer
    install_section = installer.split('if [[ "${ACTION}" == "--install" ]]', 1)[1]
    assert install_section.index("exit 0") < install_section.index("launchctl bootstrap")


@pytest.mark.parametrize(
    ("edge_id", "action"),
    [
        ("TE-QUIESCED-TO-CAPACITY", "--activate-only"),
        ("TE-CAPACITY-TO-ACTIVATED", "--activate"),
        ("TE-CANARY-READY-TO-RUNNING", "--activate"),
    ],
)
def test_installer_rejects_wrong_release_edge_before_mutation(
    tmp_path: Path,
    edge_id: str,
    action: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    env["PANTHEON_RELEASE_NEXT_EDGE"] = edge_id

    completed = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            action,
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    receipt = json.loads(completed.stdout)
    assert receipt["blocked_code"] == "EDGE_EFFECTOR_MISMATCH"
    assert receipt["details"]["actual"] == {
        "edge_id": edge_id,
        "effector": "scripts/install_agy_gemini_coordinator_launchd.sh",
        "action": action,
    }
    assert not mutation_log.exists()
    assert not fake_home.exists()


def test_activation_invalidation_requires_publisher_restage(tmp_path: Path) -> None:
    env, fake_home, mutation_log, manifest, _barrier, _loaded, _live_payloads = (
        _prepare_publisher_only_activation_fixture(tmp_path)
    )
    stage_dir = fake_home / "Library/LaunchAgents/.pantheon-four-lane-stage"
    stage_dir.rename(tmp_path / "invalidated-preactivation-stage")
    env["PANTHEON_RELEASE_NEXT_EDGE"] = "TE-CANARY-READY-TO-RUNNING"

    completed = subprocess.run(
        [
            "/bin/bash",
            str(Path(__file__).resolve().parents[1] / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--activate-publisher-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert not mutation_log.exists()
    assert not stage_dir.exists()
    assert manifest["generation"] in completed.stderr or "stage" in completed.stderr.lower()


@pytest.mark.parametrize(
    ("external_correlation", "expected_correlation", "expected_phase"),
    [
        ("apf-004-private-red", "apf-004-private-red", "aggregate_preflight"),
        ("invalid correlation", None, "correlation_validation"),
    ],
)
def test_aggregate_activation_rejects_before_mutation_with_failure_receipt(
    tmp_path: Path,
    external_correlation: str,
    expected_correlation: str | None,
    expected_phase: str,
) -> None:
    """REG-PANTHEON-CROSS-ACTOR-PATH-IDENTITY-001 aggregate caller。"""
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    env["PANTHEON_ACTIVATION_CORRELATION_ID"] = external_correlation
    staged = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--install",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert staged.returncode == 0, staged.stderr
    manifest = runtime_manifest.load_manifest(Path(env["PANTHEON_RUNTIME_MANIFEST_FILE"]))
    stage_dir = fake_home / "Library/LaunchAgents/.pantheon-four-lane-stage"
    _write_aggregate_stage_plist(
        stage_dir / "com.pantheon.agy-content-publisher.plist",
        label="com.pantheon.agy-content-publisher",
        manifest=manifest,
    )
    _write_aggregate_stage_plist(
        stage_dir / "com.pantheon.content-capacity-guard.plist",
        label="com.pantheon.content-capacity-guard",
        manifest=manifest,
        manifest_digest="0" * 64,
    )

    activated = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--activate",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode != 0
    if expected_phase == "aggregate_preflight":
        assert "mismatch" in activated.stdout
    else:
        assert "correlation id 格式無效" in activated.stderr
    assert not mutation_log.exists()
    assert not (fake_home / "Library/LaunchAgents/com.pantheon.agy-gemini-coordinator.plist").exists()
    receipt_path = stage_dir / "failure-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["schema_version"] == 1
    assert receipt["status"] == "ACTIVATION_REJECTED"
    assert receipt["failed"] is True
    if expected_correlation is None:
        assert receipt["correlation_id"].startswith(
            f"activation-{manifest['generation']}-"
        )
        assert receipt["correlation_id"] != external_correlation
    else:
        assert receipt["correlation_id"] == expected_correlation
    assert receipt["stage_identity"] == {
        "manifest_digest": manifest["manifest_digest"],
        "generation": manifest["generation"],
    }
    assert receipt["exit_reason"] == {
        "phase": expected_phase,
        "exit_code": 1,
    }


@pytest.mark.parametrize(
    ("rollback_fail_at", "expected_rollback_status"),
    [(0, "ROLLBACK_COMPLETE"), (4, "ROLLBACK_FAILED")],
)
def test_four_lane_activation_failure_restores_previous_plists_and_loaded_state(
    tmp_path: Path,
    rollback_fail_at: int,
    expected_rollback_status: str,
) -> None:
    """REG-PANTHEON-FOUR-LANE-INSTALL-ROLLBACK-001 動態 rollback。"""
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    env["PANTHEON_ACTIVATION_CORRELATION_ID"] = (
        f"apf-004-rollback-{expected_rollback_status.lower()}"
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    launch_agents.mkdir(parents=True)
    labels = [
        "com.pantheon.agy-gemini-coordinator",
        "com.pantheon.agy-gemini-new",
        "com.pantheon.agy-gemini-rewrite",
        "com.pantheon.agy-gemini-i18n-new",
        "com.pantheon.agy-gemini-i18n-rewrite",
        "com.pantheon.agy-content-publisher",
        "com.pantheon.content-capacity-guard",
    ]
    manifest = runtime_manifest.load_manifest(Path(env["PANTHEON_RUNTIME_MANIFEST_FILE"]))
    barrier = (
        Path(manifest["publisher_state_root"])
        / f"four-lane-activation-{manifest['generation']}.barrier"
    )
    previous_payload = {
        "Label": "com.pantheon.agy-gemini-coordinator",
        "ProgramArguments": [
            "python",
            "-m",
            "runtime",
            "barrier-exec",
            "--barrier",
            str(barrier),
        ],
        "EnvironmentVariables": {
            "PANTHEON_RUNTIME_MANIFEST": env["PANTHEON_RUNTIME_MANIFEST_FILE"],
            "PANTHEON_RUNTIME_MANIFEST_DIGEST": manifest["manifest_digest"],
        },
    }
    previous = plistlib.dumps(previous_payload)
    for label in labels:
        (launch_agents / f"{label}.plist").write_bytes(previous)
    ready = tmp_path / "previous-ready"
    for label in runtime_manifest.SERVICE_LABELS:
        runtime_manifest.write_readiness_ack(ready, manifest, label)
    runtime_manifest.activate_barrier(barrier, ready, manifest)
    launchctl = tmp_path / "bin" / "launchctl"
    bootstrap_count = tmp_path / "bootstrap-count"
    loaded = tmp_path / "loaded"
    loaded.mkdir()
    for label in labels:
        (loaded / label).touch()
    launchctl.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$*\" >> '{mutation_log}'\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in *com.pantheon.agy-gemini-runner) exit 113;; esac\n"
        "  label=${2##*/}\n"
        f"  [ -f '{loaded}/'$label ] || exit 113\n"
        "  printf '%s\\n' 'pid = 4242'\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = \"bootout\" ]; then\n"
        "  label=${2##*/}\n"
        f"  rm -f '{loaded}/'$label\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = \"bootstrap\" ]; then\n"
        f"  count=$(cat '{bootstrap_count}' 2>/dev/null || printf 0)\n"
        "  count=$((count + 1))\n"
        f"  printf '%s' \"$count\" > '{bootstrap_count}'\n"
        f"  if [ \"$count\" -eq 3 ] || [ \"$count\" -eq {rollback_fail_at} ]; then exit 1; fi\n"
        "  label=${3##*/}\n"
        "  label=${label%.plist}\n"
        f"  touch '{loaded}/'$label\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)

    staged = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"), "--install"],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert staged.returncode == 0, staged.stderr
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    for label in labels[-2:]:
        _write_aggregate_stage_plist(
            stage_dir / f"{label}.plist",
            label=label,
            manifest=manifest,
        )
    for label in labels:
        assert (launch_agents / f"{label}.plist").read_bytes() == previous
        assert (stage_dir / f"{label}.plist").is_file()
    activated = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"), "--activate"],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode != 0
    for label in labels:
        assert (launch_agents / f"{label}.plist").read_bytes() == previous
    assert runtime_manifest.validate_barrier(barrier, manifest)["status"] == "PASS"
    failure_receipt = launch_agents / ".pantheon-four-lane-stage" / "failure-receipt.json"
    receipt = json.loads(failure_receipt.read_text(encoding="utf-8"))
    assert receipt["status"] == expected_rollback_status
    assert receipt["correlation_id"] == (
        f"apf-004-rollback-{expected_rollback_status.lower()}"
    )
    assert receipt["stage_identity"] == {
        "manifest_digest": manifest["manifest_digest"],
        "generation": manifest["generation"],
    }
    assert receipt["exit_reason"] == {
        "phase": "bootstrap_staged_services",
        "exit_code": 1,
    }
    mutations = mutation_log.read_text(encoding="utf-8")
    assert mutations.count("bootout") >= 2
    assert mutations.count("bootstrap") >= len(labels)


def test_four_lane_activation_success_commits_matching_private_stage(
    tmp_path: Path,
) -> None:
    """APF-004 normal transition 成功 fixture；全程只用 fake launchctl。"""
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    env["PANTHEON_ACTIVATION_CORRELATION_ID"] = "apf-004-private-green"
    manifest = runtime_manifest.load_manifest(Path(env["PANTHEON_RUNTIME_MANIFEST_FILE"]))
    stage_dir = fake_home / "Library/LaunchAgents/.pantheon-four-lane-stage"
    ready_root = stage_dir / "readiness" / str(manifest["generation"])
    readiness_fixture = tmp_path / "readiness-fixture"
    for label in runtime_manifest.SERVICE_LABELS:
        runtime_manifest.write_readiness_ack(readiness_fixture, manifest, label)
    barrier = (
        Path(manifest["publisher_state_root"])
        / f"four-lane-activation-{manifest['generation']}.barrier"
    )
    runtime_manifest.activate_barrier(barrier, readiness_fixture, manifest)
    launchctl = tmp_path / "bin" / "launchctl"
    loaded = tmp_path / "loaded"
    loaded.mkdir()
    launchctl.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$*\" >> '{mutation_log}'\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in *com.pantheon.agy-gemini-runner) exit 113;; esac\n"
        "  label=${2##*/}\n"
        f"  [ -f '{loaded}/'$label ] || exit 113\n"
        "  printf '%s\\n' 'service = fixture'\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = \"bootout\" ]; then\n"
        "  label=${2##*/}\n"
        f"  rm -f '{loaded}/'$label\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = \"bootstrap\" ]; then\n"
        "  label=${3##*/}\n"
        "  label=${label%.plist}\n"
        f"  touch '{loaded}/'$label\n"
        f"  mkdir -p '{ready_root}'\n"
        f"  cp '{readiness_fixture}/'* '{ready_root}/'\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)

    staged = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--install",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert staged.returncode == 0, staged.stderr
    for label in runtime_manifest.SERVICE_LABELS:
        if label not in {
            "com.pantheon.agy-content-publisher",
            "com.pantheon.content-capacity-guard",
        }:
            continue
        _write_aggregate_stage_plist(
            stage_dir / f"{label}.plist",
            label=label,
            manifest=manifest,
        )

    activated = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--activate",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode == 0, activated.stderr
    assert "aggregate activation 已完成" in activated.stdout
    assert not stage_dir.exists()
    assert runtime_manifest.validate_barrier(barrier, manifest)["status"] == "PASS"
    assert sorted(path.name for path in loaded.iterdir()) == sorted(
        runtime_manifest.SERVICE_LABELS
    )


def test_normal_activate_rejects_missing_activation_barrier_before_mutation(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    env["PANTHEON_ACTIVATION_CORRELATION_ID"] = "safe-act-normal-missing-barrier"
    manifest = runtime_manifest.load_manifest(Path(env["PANTHEON_RUNTIME_MANIFEST_FILE"]))
    stage_dir = fake_home / "Library/LaunchAgents/.pantheon-four-lane-stage"
    ready_root = stage_dir / "readiness" / str(manifest["generation"])
    readiness_fixture = tmp_path / "readiness-fixture"
    for label in runtime_manifest.SERVICE_LABELS:
        runtime_manifest.write_readiness_ack(readiness_fixture, manifest, label)
    loaded = tmp_path / "loaded"
    loaded.mkdir()
    child_io_marker = tmp_path / "publisher-child-io-marker"
    barrier = (
        Path(manifest["publisher_state_root"])
        / f"four-lane-activation-{manifest['generation']}.barrier"
    )
    launchctl = tmp_path / "bin" / "launchctl"
    launchctl.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in *com.pantheon.agy-gemini-runner) exit 113;; esac\n"
        "  label=${2##*/}\n"
        f"  [ -f '{loaded}/'$label ] || exit 113\n"
        "  printf '%s\\n' 'service = missing-barrier-fixture'\n"
        "  exit 0\n"
        "fi\n"
        f"printf '%s\\n' \"$*\" >> '{mutation_log}'\n"
        "if [ \"$1\" = \"bootstrap\" ]; then\n"
        "  label=${3##*/}\n"
        "  label=${label%.plist}\n"
        "  if [ \"$label\" = \"com.pantheon.agy-content-publisher\" ] "
        f"&& [ ! -f '{barrier}' ]; then touch '{child_io_marker}'; fi\n"
        f"  touch '{loaded}/'$label\n"
        f"  mkdir -p '{ready_root}'\n"
        f"  cp '{readiness_fixture}/'* '{ready_root}/'\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)

    staged = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--install",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert staged.returncode == 0, staged.stderr
    for label in {
        "com.pantheon.agy-content-publisher",
        "com.pantheon.content-capacity-guard",
    }:
        _write_aggregate_stage_plist(
            stage_dir / f"{label}.plist",
            label=label,
            manifest=manifest,
        )

    activated = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--activate",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode != 0
    assert not child_io_marker.exists()
    assert not mutation_log.exists()
    receipt = json.loads((stage_dir / "failure-receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "ACTIVATION_REJECTED"
    assert receipt["correlation_id"] == "safe-act-normal-missing-barrier"
    assert receipt["exit_reason"] == {
        "phase": "normal_transition_barrier_validation",
        "exit_code": 1,
    }


def test_gate2_activation_only_bootstraps_barrier_without_child_io(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    env["PANTHEON_ACTIVATION_CORRELATION_ID"] = "apf-004-gate2-activation-only"
    manifest = runtime_manifest.load_manifest(Path(env["PANTHEON_RUNTIME_MANIFEST_FILE"]))
    stage_dir = fake_home / "Library/LaunchAgents/.pantheon-four-lane-stage"
    ready_root = stage_dir / "readiness" / str(manifest["generation"])
    readiness_fixture = tmp_path / "readiness-fixture"
    for label in runtime_manifest.SERVICE_LABELS:
        runtime_manifest.write_readiness_ack(readiness_fixture, manifest, label)
    launchctl = tmp_path / "bin" / "launchctl"
    loaded = tmp_path / "loaded"
    child_io_marker = tmp_path / "child-io-marker"
    loaded.mkdir()
    launchctl.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$*\" >> '{mutation_log}'\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in *com.pantheon.agy-gemini-runner) exit 113;; esac\n"
        "  label=${2##*/}\n"
        f"  [ -f '{loaded}/'$label ] || exit 113\n"
        "  printf '%s\\n' 'service = activation-only-fixture'\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = \"bootout\" ]; then\n"
        "  label=${2##*/}\n"
        f"  rm -f '{loaded}/'$label\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = \"bootstrap\" ]; then\n"
        "  label=${3##*/}\n"
        "  label=${label%.plist}\n"
        "  /usr/libexec/PlistBuddy -c 'Print :ProgramArguments' \"$3\" "
        f"| grep -q -- '--activation-only' || touch '{child_io_marker}'\n"
        f"  touch '{loaded}/'$label\n"
        f"  mkdir -p '{ready_root}'\n"
        f"  cp '{readiness_fixture}/'* '{ready_root}/'\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)

    staged = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--install",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert staged.returncode == 0, staged.stderr
    for label in {
        "com.pantheon.agy-content-publisher",
        "com.pantheon.content-capacity-guard",
    }:
        _write_activation_stage_plist(
            stage_dir / f"{label}.plist",
            label=label,
            manifest=manifest,
        )

    activated = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--activate-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode == 0, activated.stderr
    assert not child_io_marker.exists()
    barrier = (
        Path(manifest["publisher_state_root"])
        / f"four-lane-activation-{manifest['generation']}.barrier"
    )
    assert runtime_manifest.validate_barrier(barrier, manifest)["status"] == "PASS"
    launch_agents = fake_home / "Library" / "LaunchAgents"
    for label in runtime_manifest.SERVICE_LABELS:
        with (launch_agents / f"{label}.plist").open("rb") as stream:
            arguments = plistlib.load(stream)["ProgramArguments"]
        separator = arguments.index("--")
        assert arguments[:separator].count("--activation-only") == 1
        assert "--activation-only" not in arguments[separator + 1 :]
    assert sorted(path.name for path in loaded.iterdir()) == sorted(
        runtime_manifest.SERVICE_LABELS
    )


def test_normal_activate_rejects_activation_only_staged_plist_before_mutation(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    env["PANTHEON_ACTIVATION_CORRELATION_ID"] = "apf-004-normal-rejects-ao"
    staged = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--install",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert staged.returncode == 0, staged.stderr
    manifest = runtime_manifest.load_manifest(Path(env["PANTHEON_RUNTIME_MANIFEST_FILE"]))
    stage_dir = fake_home / "Library/LaunchAgents/.pantheon-four-lane-stage"
    for label in {
        "com.pantheon.agy-content-publisher",
        "com.pantheon.content-capacity-guard",
    }:
        _write_activation_stage_plist(
            stage_dir / f"{label}.plist",
            label=label,
            manifest=manifest,
        )
    poisoned = stage_dir / "com.pantheon.agy-content-publisher.plist"
    with poisoned.open("rb") as stream:
        payload = plistlib.load(stream)
    payload["ProgramArguments"].insert(
        payload["ProgramArguments"].index("--"),
        "--activation-only",
    )
    with poisoned.open("wb") as stream:
        plistlib.dump(payload, stream)
    poisoned.chmod(0o600)

    activated = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--activate",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode != 0
    assert not mutation_log.exists()
    launch_agents = fake_home / "Library" / "LaunchAgents"
    for label in runtime_manifest.SERVICE_LABELS:
        assert not (launch_agents / f"{label}.plist").exists()
    receipt = json.loads((stage_dir / "failure-receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "ACTIVATION_REJECTED"
    assert receipt["correlation_id"] == "apf-004-normal-rejects-ao"
    assert receipt["exit_reason"] == {
        "phase": "aggregate_preflight",
        "exit_code": 1,
    }


def test_publisher_only_bounded_activation_replaces_only_publisher(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    (
        env,
        fake_home,
        mutation_log,
        manifest,
        barrier,
        loaded,
        live_payloads,
    ) = _prepare_publisher_only_activation_fixture(tmp_path)
    launch_agents = fake_home / "Library" / "LaunchAgents"
    stage_dir = launch_agents / ".pantheon-four-lane-stage"

    activated = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--activate-publisher-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode == 0, activated.stderr
    assert "Publisher-only bounded activation 已完成" in activated.stdout
    assert runtime_manifest.validate_barrier(barrier, manifest)["status"] == "PASS"
    assert not stage_dir.exists()
    mutations = mutation_log.read_text(encoding="utf-8").splitlines()
    user_id = os.getuid()
    assert mutations == [
        f"bootout gui/{user_id}/com.pantheon.agy-content-publisher",
        f"bootstrap gui/{user_id} {launch_agents / 'com.pantheon.agy-content-publisher.plist'}",
    ]
    assert sorted(path.name for path in loaded.iterdir()) == sorted(
        runtime_manifest.SERVICE_LABELS
    )
    for label in runtime_manifest.SERVICE_LABELS:
        live_path = launch_agents / f"{label}.plist"
        if label == "com.pantheon.agy-content-publisher":
            with live_path.open("rb") as stream:
                payload = plistlib.load(stream)
            assert payload["RunAtLoad"] is True
            assert "StartInterval" not in payload
            assert "KeepAlive" not in payload
            arguments = payload["ProgramArguments"]
            separator = arguments.index("--")
            assert "--activation-only" not in arguments[:separator]
            assert arguments[arguments.index("--max-runs") + 1] == "1"
            assert arguments[arguments.index("--exact-run-id") + 1] == (
                "publisher-only-run-001"
            )
            continue
        assert live_path.read_bytes() == live_payloads[label]


@pytest.mark.parametrize("child_exit", [0, 7])
def test_publisher_only_activation_is_one_shot_for_child_success_and_failure(
    tmp_path: Path,
    child_exit: int,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    (
        env,
        fake_home,
        mutation_log,
        _manifest,
        _barrier,
        loaded,
        live_payloads,
    ) = _prepare_publisher_only_activation_fixture(tmp_path)
    env["PUBLISHER_CHILD_EXIT_CODE"] = str(child_exit)
    child_log = tmp_path / "publisher-child.log"
    launch_agents = fake_home / "Library" / "LaunchAgents"
    _write_launchctl_that_records_publisher_child(
        tmp_path / "bin" / "launchctl",
        loaded=loaded,
        mutation_log=mutation_log,
        child_log=child_log,
    )

    activated = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--activate-publisher-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode == 0, activated.stderr
    assert child_log.read_text(encoding="utf-8").splitlines() == [
        f"com.pantheon.agy-content-publisher run=1 exit={child_exit}"
    ]
    with (launch_agents / "com.pantheon.agy-content-publisher.plist").open("rb") as stream:
        payload = plistlib.load(stream)
    assert payload["RunAtLoad"] is True
    assert "StartInterval" not in payload
    assert "KeepAlive" not in payload
    for label in runtime_manifest.SERVICE_LABELS:
        if label != "com.pantheon.agy-content-publisher":
            assert (launch_agents / f"{label}.plist").read_bytes() == live_payloads[label]


def test_publisher_terminal_reset_accepts_scheduled_live_publisher_absent(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    (
        env,
        fake_home,
        mutation_log,
        manifest,
        _barrier,
        loaded,
        live_payloads,
    ) = _prepare_publisher_only_activation_fixture(tmp_path)
    launch_agents = fake_home / "Library" / "LaunchAgents"
    publisher_label = "com.pantheon.agy-content-publisher"
    publisher_live = launch_agents / f"{publisher_label}.plist"
    _write_publisher_scheduled_live(
        launch_agents / ".pantheon-four-lane-stage" / f"{publisher_label}.plist",
        publisher_live,
    )
    (loaded / publisher_label).unlink()
    child_log = tmp_path / "publisher-child.log"

    reset = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--reset-publisher-activation-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert reset.returncode == 0, reset.stderr
    assert "Publisher activation-only reset 已完成" in reset.stdout
    reset_receipt_path = (
        launch_agents / ".pantheon-four-lane-stage/publisher-reset-receipt.json"
    )
    reset_receipt = json.loads(reset_receipt_path.read_text(encoding="utf-8"))
    assert reset_receipt_path.stat().st_mode & 0o777 == 0o600
    assert reset_receipt["status"] == "PASS"
    assert reset_receipt["correlation_id"] == "publisher-only-bounded"
    assert reset_receipt["target"]["generation"] == manifest["generation"]
    assert reset_receipt["old_live"]["generation_relation"] == (
        "target_same_generation"
    )
    assert reset_receipt["publisher"]["post_plist_receipt"]["label"] == (
        publisher_label
    )
    assert len(reset_receipt["other_six"]) == 6
    assert all(
        proof["pre_plist_sha256"] == proof["post_plist_sha256"]
        for proof in reset_receipt["other_six"]
    )
    assert mutation_log.read_text(encoding="utf-8").splitlines() == [
        f"bootstrap gui/{os.getuid()} {publisher_live}",
    ]
    assert sorted(path.name for path in loaded.iterdir()) == sorted(
        runtime_manifest.SERVICE_LABELS
    )
    for label in runtime_manifest.SERVICE_LABELS:
        live_path = launch_agents / f"{label}.plist"
        if label == publisher_label:
            receipt = runtime_manifest.plist_receipt(
                live_path,
                expected_activation_mode="activation-only",
            )
            assert receipt["label"] == publisher_label
            assert receipt["manifest_digest"] == manifest["manifest_digest"]
            with live_path.open("rb") as stream:
                payload = plistlib.load(stream)
            assert payload["RunAtLoad"] is True
            assert "StartInterval" not in payload
            assert "KeepAlive" not in payload
            continue
        assert live_path.read_bytes() == live_payloads[label]
    assert (launch_agents / ".pantheon-four-lane-stage").is_dir()
    assert not child_log.exists()


def test_publisher_terminal_reset_canonicalizes_ambient_tmpdir_alias(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env, fake_home, mutation_log, _manifest, _barrier, loaded, live_payloads = (
        _prepare_publisher_only_activation_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    publisher_label = "com.pantheon.agy-content-publisher"
    publisher_live = launch_agents / f"{publisher_label}.plist"
    _write_publisher_scheduled_live(
        launch_agents / ".pantheon-four-lane-stage" / f"{publisher_label}.plist",
        publisher_live,
    )
    (loaded / publisher_label).unlink()
    canonical_tmpdir = tmp_path / "canonical-tmpdir"
    canonical_tmpdir.mkdir()
    tmpdir_alias = tmp_path / "tmpdir-alias"
    tmpdir_alias.symlink_to(canonical_tmpdir, target_is_directory=True)
    env["TMPDIR"] = str(tmpdir_alias)

    reset = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--reset-publisher-activation-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert reset.returncode == 0, reset.stderr
    assert mutation_log.read_text(encoding="utf-8").splitlines() == [
        f"bootstrap gui/{os.getuid()} {publisher_live}",
    ]
    assert sorted(path.name for path in loaded.iterdir()) == sorted(
        runtime_manifest.SERVICE_LABELS
    )
    for label, payload in live_payloads.items():
        if label != publisher_label:
            assert (launch_agents / f"{label}.plist").read_bytes() == payload


def test_publisher_terminal_reset_reports_temp_receipt_failure_before_mutation(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env, fake_home, mutation_log, _manifest, _barrier, _loaded, live_payloads = (
        _prepare_publisher_only_activation_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    publisher_label = "com.pantheon.agy-content-publisher"
    publisher_live = launch_agents / f"{publisher_label}.plist"
    _write_publisher_scheduled_live(
        launch_agents / ".pantheon-four-lane-stage" / f"{publisher_label}.plist",
        publisher_live,
    )
    publisher_before = publisher_live.read_bytes()
    stale_success_receipt = (
        launch_agents / ".pantheon-four-lane-stage/publisher-reset-receipt.json"
    )
    stale_success_receipt.write_text('{"status":"PASS"}\n', encoding="utf-8")
    stale_success_receipt.chmod(0o600)
    plutil = Path(env["PATH"].split(":", 1)[0]) / "plutil"
    plutil.write_text(
        "#!/bin/sh\n"
        "case \"${2:-}\" in\n"
        "  *pantheon-publisher-reset.*)\n"
        f"    /usr/libexec/PlistBuddy -c 'Set :Label {publisher_label}.drifted' \"$2\" >/dev/null\n"
        "    ;;\n"
        "esac\n"
        "exec /usr/bin/plutil \"$@\"\n",
        encoding="utf-8",
    )
    plutil.chmod(0o700)

    reset = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--reset-publisher-activation-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert reset.returncode != 0
    assert "Publisher activation-only reset temp receipt failed" in reset.stderr
    assert '"status": "NO-GO"' in reset.stderr
    assert publisher_live.read_bytes() == publisher_before
    assert not stale_success_receipt.exists()
    assert not mutation_log.exists()
    for label, payload in live_payloads.items():
        if label != publisher_label:
            assert (launch_agents / f"{label}.plist").read_bytes() == payload


def test_publisher_terminal_reset_accepts_scheduled_loaded_without_pid(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    (
        env,
        fake_home,
        mutation_log,
        manifest,
        _barrier,
        loaded,
        live_payloads,
    ) = _prepare_publisher_only_activation_fixture(tmp_path)
    launch_agents = fake_home / "Library" / "LaunchAgents"
    publisher_label = "com.pantheon.agy-content-publisher"
    publisher_live = launch_agents / f"{publisher_label}.plist"
    _write_publisher_scheduled_live(
        launch_agents / ".pantheon-four-lane-stage" / f"{publisher_label}.plist",
        publisher_live,
    )

    reset = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--reset-publisher-activation-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert reset.returncode == 0, reset.stderr
    assert mutation_log.read_text(encoding="utf-8").splitlines() == [
        f"bootout gui/{os.getuid()}/{publisher_label}",
        f"bootstrap gui/{os.getuid()} {publisher_live}",
    ]
    assert sorted(path.name for path in loaded.iterdir()) == sorted(
        runtime_manifest.SERVICE_LABELS
    )
    receipt = runtime_manifest.plist_receipt(
        publisher_live,
        expected_activation_mode="activation-only",
    )
    assert receipt["label"] == publisher_label
    assert receipt["manifest_digest"] == manifest["manifest_digest"]
    with publisher_live.open("rb") as stream:
        payload = plistlib.load(stream)
    assert payload["RunAtLoad"] is True
    assert "StartInterval" not in payload
    assert "KeepAlive" not in payload
    for label, payload_bytes in live_payloads.items():
        if label != publisher_label:
            assert (launch_agents / f"{label}.plist").read_bytes() == payload_bytes


def test_publisher_terminal_reset_preserves_terminal_one_shot_input(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env, fake_home, mutation_log, _manifest, _barrier, loaded, _live_payloads = (
        _prepare_publisher_only_activation_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    publisher_label = "com.pantheon.agy-content-publisher"
    publisher_live = launch_agents / f"{publisher_label}.plist"
    _write_publisher_terminal_live(
        launch_agents / ".pantheon-four-lane-stage" / f"{publisher_label}.plist",
        publisher_live,
    )
    (loaded / publisher_label).unlink()

    reset = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--reset-publisher-activation-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert reset.returncode == 0, reset.stderr
    assert mutation_log.read_text(encoding="utf-8").splitlines() == [
        f"bootstrap gui/{os.getuid()} {publisher_live}",
    ]
    assert (loaded / publisher_label).exists()
    with publisher_live.open("rb") as stream:
        payload = plistlib.load(stream)
    assert payload["RunAtLoad"] is True
    assert "StartInterval" not in payload
    assert "KeepAlive" not in payload


def test_publisher_terminal_reset_settles_after_manifest_promotion(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    (
        env,
        fake_home,
        mutation_log,
        old_manifest,
        _barrier,
        loaded,
        live_payloads,
    ) = _prepare_publisher_only_activation_fixture(tmp_path)
    launch_agents = fake_home / "Library" / "LaunchAgents"
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    publisher_label = "com.pantheon.agy-content-publisher"
    publisher_live = launch_agents / f"{publisher_label}.plist"
    current_manifest_path = Path(env["PANTHEON_RUNTIME_MANIFEST_FILE"])
    _write_publisher_scheduled_live(
        stage_dir / f"{publisher_label}.plist",
        publisher_live,
    )
    _replace_plist_manifest_path(publisher_live, current_manifest_path)
    (loaded / publisher_label).unlink()

    promoted_manifest = runtime_manifest.build_manifest(
        actor_root=Path(str(old_manifest["actor_root"])),
        queue_root=Path(str(old_manifest["queue_root"])),
        publisher_state_root=Path(str(old_manifest["publisher_state_root"])),
        log_root=Path(str(old_manifest["log_root"])),
        identity="synthetic-installer-promoted:501",
        config_version=str(old_manifest["config_version"]),
        generation="g34-promoted-fixture",
        python_executable=Path(sys.executable).resolve(strict=True),
        uv_executable=Path("/usr/bin/true"),
    )
    runtime_manifest.write_manifest(current_manifest_path, promoted_manifest)
    env["PANTHEON_EXPECTED_RUNTIME_MANIFEST_DIGEST"] = str(
        promoted_manifest["manifest_digest"]
    )
    (stage_dir / "manifest-digest").write_text(
        str(promoted_manifest["manifest_digest"]) + "\n",
        encoding="utf-8",
    )
    (stage_dir / "generation").write_text(
        str(promoted_manifest["generation"]) + "\n",
        encoding="utf-8",
    )
    _write_publisher_normal_plist(
        stage_dir / f"{publisher_label}.plist",
        manifest=promoted_manifest,
        max_runs="1",
        exact_run_id="publisher-only-run-001",
    )
    _replace_plist_manifest_path(
        stage_dir / f"{publisher_label}.plist",
        current_manifest_path,
    )
    lifecycle_log = tmp_path / "publisher-reset-lifecycle.jsonl"
    _write_launchctl_that_executes_publisher_during_settle(
        tmp_path / "bin" / "launchctl",
        loaded=loaded,
        mutation_log=mutation_log,
        lifecycle_log=lifecycle_log,
        launch_agents=launch_agents,
    )

    reset = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--reset-publisher-activation-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert reset.returncode == 0, reset.stderr
    lifecycle = lifecycle_log.read_text(encoding="utf-8").splitlines()
    child = next(json.loads(line) for line in lifecycle if line.startswith("{"))
    assert child == {"event": "bootstrap-child", "returncode": 78}
    assert lifecycle.count(
        f"print label={publisher_label} state=settling"
    ) == 1
    assert lifecycle.count(f"print label={publisher_label} state=stable") == 1
    assert mutation_log.read_text(encoding="utf-8").splitlines() == [
        f"bootstrap gui/{os.getuid()} {publisher_live}",
    ]
    assert (loaded / publisher_label).exists()
    assert (stage_dir / "publisher-exact-run-id").read_text(encoding="utf-8") == (
        "publisher-only-run-001\n"
    )
    assert (stage_dir / "publisher-max-runs").read_text(encoding="utf-8") == "1\n"
    reset_receipt = json.loads(
        (stage_dir / "publisher-reset-receipt.json").read_text(encoding="utf-8")
    )
    assert reset_receipt["correlation_id"] == "publisher-only-bounded"
    assert reset_receipt["target"]["generation"] == promoted_manifest["generation"]
    assert reset_receipt["old_live"]["generation"] == old_manifest["generation"]
    assert reset_receipt["old_live"]["generation_relation"] == (
        "target_newer_than_live"
    )
    assert reset_receipt["publisher"]["post_launchctl_identity"][
        "last_exit_codes"
    ] == [78]
    assert all(
        proof["pre_plist_sha256"] == proof["post_plist_sha256"]
        for proof in reset_receipt["other_six"]
    )
    for label, payload in live_payloads.items():
        if label != publisher_label:
            assert (launch_agents / f"{label}.plist").read_bytes() == payload


def test_publisher_terminal_reset_settles_after_transient_pid(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    (
        env,
        fake_home,
        mutation_log,
        manifest,
        _barrier,
        loaded,
        live_payloads,
    ) = _prepare_publisher_only_activation_fixture(tmp_path)
    launch_agents = fake_home / "Library" / "LaunchAgents"
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    publisher_label = "com.pantheon.agy-content-publisher"
    publisher_live = launch_agents / f"{publisher_label}.plist"
    _write_publisher_scheduled_live(
        stage_dir / f"{publisher_label}.plist",
        publisher_live,
    )
    (loaded / publisher_label).unlink()
    child_log = tmp_path / "publisher-child.log"
    print_count = tmp_path / "publisher-print-count"
    launchctl = tmp_path / "bin" / "launchctl"
    original = launchctl.read_text(encoding="utf-8")
    path_line = f"  printf '%s\\n' 'path = {launch_agents}/'$label'.plist'\n"
    launchctl.write_text(
        original.replace(
            path_line,
            path_line
            + f"  if [ \"$label\" = \"{publisher_label}\" ]; then\n"
            f"    count=$(cat '{print_count}' 2>/dev/null || printf 0)\n"
            "    count=$((count + 1))\n"
            f"    printf '%s' \"$count\" > '{print_count}'\n"
            "    if [ \"$count\" -eq 1 ]; then\n"
            "      printf '%s\\n' 'pid = 4242'\n"
            "    fi\n"
            "  fi\n",
        ),
        encoding="utf-8",
    )
    launchctl.chmod(0o700)

    reset = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--reset-publisher-activation-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert reset.returncode == 0, reset.stderr
    assert "Publisher activation-only reset 已完成" in reset.stdout
    assert print_count.read_text(encoding="utf-8") == "2"
    assert mutation_log.read_text(encoding="utf-8").splitlines() == [
        f"bootstrap gui/{os.getuid()} {publisher_live}",
    ]
    assert sorted(path.name for path in loaded.iterdir()) == sorted(
        runtime_manifest.SERVICE_LABELS
    )
    receipt = runtime_manifest.plist_receipt(
        publisher_live,
        expected_activation_mode="activation-only",
    )
    assert receipt["label"] == publisher_label
    assert receipt["manifest_digest"] == manifest["manifest_digest"]
    reset_receipt = json.loads(
        (stage_dir / "publisher-reset-receipt.json").read_text(encoding="utf-8")
    )
    assert reset_receipt["status"] == "PASS"
    assert reset_receipt["correlation_id"] == "publisher-only-bounded"
    assert all(
        proof["pre_plist_sha256"] == proof["post_plist_sha256"]
        for proof in reset_receipt["other_six"]
    )
    for label, payload in live_payloads.items():
        if label != publisher_label:
            assert (launch_agents / f"{label}.plist").read_bytes() == payload
    assert not child_log.exists()


@pytest.mark.parametrize(
    ("variant", "expected_error"),
    [
        ("wrong-start-interval", "StartInterval"),
        ("keepalive", "normal one-shot or scheduled Publisher plist"),
    ],
)
def test_publisher_terminal_reset_rejects_bad_schedule_before_mutation(
    tmp_path: Path,
    variant: str,
    expected_error: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env, fake_home, mutation_log, _manifest, _barrier, _loaded, live_payloads = (
        _prepare_publisher_only_activation_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    publisher_label = "com.pantheon.agy-content-publisher"
    publisher_live = launch_agents / f"{publisher_label}.plist"
    stage_publisher = (
        launch_agents
        / ".pantheon-four-lane-stage"
        / f"{publisher_label}.plist"
    )
    if variant == "wrong-start-interval":
        _write_publisher_scheduled_live(
            stage_publisher,
            publisher_live,
            start_interval=30,
        )
    else:
        _write_publisher_normal_live(
            stage_publisher,
            publisher_live,
            start_interval=60,
            keep_alive=True,
        )
    publisher_before = publisher_live.read_bytes()

    reset = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--reset-publisher-activation-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert reset.returncode != 0
    assert expected_error in reset.stderr
    assert publisher_live.read_bytes() == publisher_before
    assert not mutation_log.exists()
    for label, payload in live_payloads.items():
        if label != publisher_label:
            assert (launch_agents / f"{label}.plist").read_bytes() == payload


def test_publisher_terminal_reset_rejects_publisher_launchctl_path_drift(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env, fake_home, mutation_log, _manifest, _barrier, _loaded, live_payloads = (
        _prepare_publisher_only_activation_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    publisher_label = "com.pantheon.agy-content-publisher"
    publisher_live = launch_agents / f"{publisher_label}.plist"
    _write_publisher_scheduled_live(
        launch_agents / ".pantheon-four-lane-stage" / f"{publisher_label}.plist",
        publisher_live,
    )
    publisher_before = publisher_live.read_bytes()
    launchctl = tmp_path / "bin" / "launchctl"
    original = launchctl.read_text(encoding="utf-8")
    launchctl.write_text(
        original.replace(
            f"  printf '%s\\n' 'path = {launch_agents}/'$label'.plist'\n",
            f"  if [ \"$label\" = \"{publisher_label}\" ]; then\n"
            "    printf '%s\\n' 'path = /tmp/drifted-publisher.plist'\n"
            "  else\n"
            f"    printf '%s\\n' 'path = {launch_agents}/'$label'.plist'\n"
            "  fi\n",
        ),
        encoding="utf-8",
    )
    launchctl.chmod(0o700)

    reset = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--reset-publisher-activation-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert reset.returncode != 0
    assert "Publisher launchctl path drift" in reset.stderr
    assert publisher_live.read_bytes() == publisher_before
    assert not mutation_log.exists()
    for label, payload in live_payloads.items():
        if label != publisher_label:
            assert (launch_agents / f"{label}.plist").read_bytes() == payload


def test_publisher_terminal_reset_rejects_live_publisher_identity_drift(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env, fake_home, mutation_log, _manifest, _barrier, _loaded, live_payloads = (
        _prepare_publisher_only_activation_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    publisher_label = "com.pantheon.agy-content-publisher"
    publisher_live = launch_agents / f"{publisher_label}.plist"
    _write_publisher_scheduled_live(
        launch_agents / ".pantheon-four-lane-stage" / f"{publisher_label}.plist",
        publisher_live,
    )
    with publisher_live.open("rb") as stream:
        payload = plistlib.load(stream)
    payload["EnvironmentVariables"]["PANTHEON_RUNTIME_GENERATION"] = "drifted"
    with publisher_live.open("wb") as stream:
        plistlib.dump(payload, stream)
    publisher_before = publisher_live.read_bytes()

    reset = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--reset-publisher-activation-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert reset.returncode != 0
    assert "live identity drift" in reset.stderr
    assert publisher_live.read_bytes() == publisher_before
    assert not mutation_log.exists()


def test_publisher_terminal_reset_rejects_live_publisher_argv_drift(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env, fake_home, mutation_log, _manifest, _barrier, _loaded, live_payloads = (
        _prepare_publisher_only_activation_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    publisher_label = "com.pantheon.agy-content-publisher"
    publisher_live = launch_agents / f"{publisher_label}.plist"
    _write_publisher_scheduled_live(
        launch_agents / ".pantheon-four-lane-stage" / f"{publisher_label}.plist",
        publisher_live,
    )
    with publisher_live.open("rb") as stream:
        payload = plistlib.load(stream)
    arguments = list(payload["ProgramArguments"])
    arguments[arguments.index("scripts.agy_content_publisher")] = "scripts.drifted"
    payload["ProgramArguments"] = arguments
    with publisher_live.open("wb") as stream:
        plistlib.dump(payload, stream)
    publisher_before = publisher_live.read_bytes()

    reset = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--reset-publisher-activation-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert reset.returncode != 0
    assert publisher_live.read_bytes() == publisher_before
    assert not mutation_log.exists()


def test_publisher_terminal_reset_rejects_live_publisher_outer_argv_drift(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env, fake_home, mutation_log, _manifest, _barrier, _loaded, _live_payloads = (
        _prepare_publisher_only_activation_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    publisher_label = "com.pantheon.agy-content-publisher"
    publisher_live = launch_agents / f"{publisher_label}.plist"
    _write_publisher_scheduled_live(
        launch_agents / ".pantheon-four-lane-stage" / f"{publisher_label}.plist",
        publisher_live,
    )
    with publisher_live.open("rb") as stream:
        payload = plistlib.load(stream)
    assert "PANTHEON_RUNTIME_PYTHON_EXECUTABLE" not in payload["EnvironmentVariables"]
    payload["ProgramArguments"][2] = "scripts.drifted_outer"
    with publisher_live.open("wb") as stream:
        plistlib.dump(payload, stream)
    publisher_before = publisher_live.read_bytes()

    reset = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--reset-publisher-activation-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert reset.returncode != 0
    assert publisher_live.read_bytes() == publisher_before
    assert not mutation_log.exists()


def test_publisher_terminal_reset_rejects_other_service_launchctl_path_drift(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env, fake_home, mutation_log, _manifest, _barrier, _loaded, live_payloads = (
        _prepare_publisher_only_activation_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    publisher_label = "com.pantheon.agy-content-publisher"
    publisher_live = launch_agents / f"{publisher_label}.plist"
    _write_publisher_scheduled_live(
        launch_agents / ".pantheon-four-lane-stage" / f"{publisher_label}.plist",
        publisher_live,
    )
    publisher_before = publisher_live.read_bytes()
    launchctl = tmp_path / "bin" / "launchctl"
    original = launchctl.read_text(encoding="utf-8")
    launchctl.write_text(
        original.replace(
            f"  printf '%s\\n' 'path = {launch_agents}/'$label'.plist'\n",
            "  if [ \"$label\" = \"com.pantheon.agy-gemini-coordinator\" ]; then\n"
            "    printf '%s\\n' 'path = /tmp/drifted.plist'\n"
            "  else\n"
            f"    printf '%s\\n' 'path = {launch_agents}/'$label'.plist'\n"
            "  fi\n",
        ),
        encoding="utf-8",
    )
    launchctl.chmod(0o700)

    reset = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--reset-publisher-activation-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert reset.returncode != 0
    assert "other-service launchctl path drift" in reset.stderr
    assert publisher_live.read_bytes() == publisher_before
    assert not mutation_log.exists()


@pytest.mark.parametrize(
    ("pid_label", "expected_error"),
    [
        (
            "com.pantheon.agy-content-publisher",
            "refuses a running Publisher",
        ),
        (
            "com.pantheon.agy-gemini-coordinator",
            "requires other services loaded without PID",
        ),
    ],
)
def test_publisher_terminal_reset_rejects_any_live_pid_before_mutation(
    tmp_path: Path,
    pid_label: str,
    expected_error: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env, fake_home, mutation_log, _manifest, _barrier, loaded, live_payloads = (
        _prepare_publisher_only_activation_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    publisher_label = "com.pantheon.agy-content-publisher"
    publisher_live = launch_agents / f"{publisher_label}.plist"
    _write_publisher_scheduled_live(
        launch_agents / ".pantheon-four-lane-stage" / f"{publisher_label}.plist",
        publisher_live,
    )
    launchctl = tmp_path / "bin" / "launchctl"
    original = launchctl.read_text(encoding="utf-8")
    launchctl.write_text(
        original.replace(
            "  printf '%s\\n' 'state = waiting'\n",
            "  printf '%s\\n' 'state = waiting'\n"
            f"  [ \"$label\" != \"{pid_label}\" ] || printf '%s\\n' 'pid = 4242'\n",
        ),
        encoding="utf-8",
    )
    launchctl.chmod(0o700)
    publisher_before = publisher_live.read_bytes()

    reset = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--reset-publisher-activation-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert reset.returncode != 0
    assert expected_error in reset.stderr
    assert publisher_live.read_bytes() == publisher_before
    assert not mutation_log.exists()
    for label, payload in live_payloads.items():
        if label != publisher_label:
            assert (launch_agents / f"{label}.plist").read_bytes() == payload


def test_publisher_terminal_reset_rolls_back_bootstrap_failure(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env, fake_home, _mutation_log, _manifest, _barrier, loaded, live_payloads = (
        _prepare_publisher_only_activation_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    publisher_label = "com.pantheon.agy-content-publisher"
    publisher_live = launch_agents / f"{publisher_label}.plist"
    _write_publisher_scheduled_live(
        launch_agents / ".pantheon-four-lane-stage" / f"{publisher_label}.plist",
        publisher_live,
    )
    (loaded / publisher_label).unlink()
    publisher_before = publisher_live.read_bytes()
    launchctl = tmp_path / "bin" / "launchctl"
    original = launchctl.read_text(encoding="utf-8")
    launchctl.write_text(
        original.replace(
            f"  touch '{loaded}/'$label\n",
            f"  [ \"$label\" != \"{publisher_label}\" ] || exit 9\n"
            f"  touch '{loaded}/'$label\n",
        ),
        encoding="utf-8",
    )
    launchctl.chmod(0o700)

    reset = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--reset-publisher-activation-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert reset.returncode != 0
    assert publisher_live.read_bytes() == publisher_before
    assert not (loaded / publisher_label).exists()
    for label, payload in live_payloads.items():
        if label != publisher_label:
            assert (launch_agents / f"{label}.plist").read_bytes() == payload
    receipt = json.loads((stage_dir / "failure-receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "ROLLBACK_COMPLETE"
    assert receipt["exit_reason"] == {
        "phase": "publisher_reset_bootstrap",
        "exit_code": 9,
    }


def test_publisher_terminal_reset_rolls_back_when_settle_remains_absent(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env, fake_home, mutation_log, _manifest, _barrier, loaded, live_payloads = (
        _prepare_publisher_only_activation_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    publisher_label = "com.pantheon.agy-content-publisher"
    publisher_live = launch_agents / f"{publisher_label}.plist"
    _write_publisher_scheduled_live(
        stage_dir / f"{publisher_label}.plist",
        publisher_live,
    )
    (loaded / publisher_label).unlink()
    publisher_before = publisher_live.read_bytes()
    launchctl = tmp_path / "bin" / "launchctl"
    original = launchctl.read_text(encoding="utf-8")
    launchctl.write_text(
        original.replace(
            f"  touch '{loaded}/'$label\n",
            f"  [ \"$label\" != \"{publisher_label}\" ] || exit 0\n"
            f"  touch '{loaded}/'$label\n",
        ),
        encoding="utf-8",
    )
    launchctl.chmod(0o700)

    reset = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--reset-publisher-activation-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert reset.returncode != 0
    assert "did not settle" in reset.stderr
    assert publisher_live.read_bytes() == publisher_before
    assert not (loaded / publisher_label).exists()
    for label, payload in live_payloads.items():
        if label != publisher_label:
            assert (launch_agents / f"{label}.plist").read_bytes() == payload
    mutations = mutation_log.read_text(encoding="utf-8").splitlines()
    assert mutations.count(f"bootstrap gui/{os.getuid()} {publisher_live}") == 1
    assert mutations.count(f"bootout gui/{os.getuid()}/{publisher_label}") == 1
    receipt = json.loads((stage_dir / "failure-receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "ROLLBACK_COMPLETE"
    assert receipt["exit_reason"] == {
        "phase": "publisher_reset_settle",
        "exit_code": 1,
    }


@pytest.mark.parametrize("drift", ["pid", "path"])
def test_publisher_terminal_reset_rolls_back_settle_identity_drift(
    tmp_path: Path,
    drift: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env, fake_home, mutation_log, _manifest, _barrier, loaded, live_payloads = (
        _prepare_publisher_only_activation_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    publisher_label = "com.pantheon.agy-content-publisher"
    publisher_live = launch_agents / f"{publisher_label}.plist"
    _write_publisher_scheduled_live(
        stage_dir / f"{publisher_label}.plist",
        publisher_live,
    )
    (loaded / publisher_label).unlink()
    publisher_before = publisher_live.read_bytes()
    launchctl = tmp_path / "bin" / "launchctl"
    original = launchctl.read_text(encoding="utf-8")
    path_line = f"  printf '%s\\n' 'path = {launch_agents}/'$label'.plist'\n"
    if drift == "pid":
        replacement = (
            path_line
            + f"  [ \"$label\" != \"{publisher_label}\" ] || printf '%s\\n' 'pid = 4242'\n"
        )
    else:
        replacement = (
            f"  if [ \"$label\" = \"{publisher_label}\" ]; then\n"
            f"    printf '%s\\n' 'path = {launch_agents}/wrong-publisher.plist'\n"
            "  else\n"
            + path_line
            + "  fi\n"
        )
    launchctl.write_text(original.replace(path_line, replacement), encoding="utf-8")
    launchctl.chmod(0o700)

    reset = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--reset-publisher-activation-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert reset.returncode != 0
    assert (
        "running Publisher" if drift == "pid" else "path drift"
    ) in reset.stderr
    assert publisher_live.read_bytes() == publisher_before
    assert not (loaded / publisher_label).exists()
    for label, payload in live_payloads.items():
        if label != publisher_label:
            assert (launch_agents / f"{label}.plist").read_bytes() == payload
    mutations = mutation_log.read_text(encoding="utf-8").splitlines()
    assert mutations.count(f"bootstrap gui/{os.getuid()} {publisher_live}") == 1
    assert mutations.count(f"bootout gui/{os.getuid()}/{publisher_label}") == 1
    receipt = json.loads((stage_dir / "failure-receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "ROLLBACK_COMPLETE"
    assert receipt["exit_reason"] == {
        "phase": "publisher_reset_settle",
        "exit_code": 1,
    }


def test_publisher_terminal_reset_rolls_back_postcheck_failure(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env, fake_home, _mutation_log, _manifest, _barrier, loaded, live_payloads = (
        _prepare_publisher_only_activation_fixture(tmp_path)
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    publisher_label = "com.pantheon.agy-content-publisher"
    publisher_live = launch_agents / f"{publisher_label}.plist"
    _write_publisher_scheduled_live(
        launch_agents / ".pantheon-four-lane-stage" / f"{publisher_label}.plist",
        publisher_live,
    )
    publisher_before = publisher_live.read_bytes()
    launchctl = tmp_path / "bin" / "launchctl"
    bootstrap_count = tmp_path / "publisher-bootstrap-count"
    original = launchctl.read_text(encoding="utf-8")
    launchctl.write_text(
        original.replace(
            f"  touch '{loaded}/'$label\n",
            f"  touch '{loaded}/'$label\n"
            f"  if [ \"$label\" = \"{publisher_label}\" ]; then\n"
            f"    count=$(cat '{bootstrap_count}' 2>/dev/null || printf 0)\n"
            "    count=$((count + 1))\n"
            f"    printf '%s' \"$count\" > '{bootstrap_count}'\n"
            "    if [ \"$count\" -eq 1 ]; then\n"
            "      /usr/libexec/PlistBuddy -c 'Delete :ProgramArguments:16' \"$3\" >/dev/null\n"
            "    fi\n"
            "  fi\n",
        ),
        encoding="utf-8",
    )
    launchctl.chmod(0o700)

    reset = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--reset-publisher-activation-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert reset.returncode != 0
    assert publisher_live.read_bytes() == publisher_before
    assert (loaded / publisher_label).exists()
    for label, payload in live_payloads.items():
        if label != publisher_label:
            assert (launch_agents / f"{label}.plist").read_bytes() == payload
    receipt = json.loads((stage_dir / "failure-receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "ROLLBACK_COMPLETE"
    assert receipt["exit_reason"] == {
        "phase": "publisher_reset_postcheck",
        "exit_code": 1,
    }


def test_publisher_only_bounded_activation_allows_no_exact_run_receipt(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env, _fake_home, mutation_log, _manifest, _barrier, _loaded, _live_payloads = (
        _prepare_publisher_only_activation_fixture(tmp_path, exact_run_id=None)
    )

    activated = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--activate-publisher-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode == 0, activated.stderr
    assert mutation_log.exists()


@pytest.mark.parametrize(
    ("variant", "expected_phase", "expected_error"),
    [
        ("missing-barrier", "publisher_only_barrier_validation", "matching activation barrier"),
        ("max-runs", "publisher_only_stage_validation", "max-runs=1"),
        ("exact-run-format", "publisher_only_stage_validation", "exact-run-id"),
        ("plist-drift", "publisher_only_stage_validation", "mismatch"),
        ("missing-exact-run-receipt", "publisher_only_stage_validation", "receipt mismatch"),
        ("stale-exact-run-receipt", "publisher_only_stage_validation", "receipt mismatch"),
        ("exact-run-receipt-mismatch", "publisher_only_stage_validation", "receipt mismatch"),
        ("empty-exact-run-receipt", "publisher_only_stage_validation", "receipt is empty"),
    ],
)
def test_publisher_only_bounded_activation_fails_closed_before_mutation(
    tmp_path: Path,
    variant: str,
    expected_phase: str,
    expected_error: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    fixture = _prepare_publisher_only_activation_fixture(
        tmp_path,
        max_runs="2" if variant == "max-runs" else "1",
        exact_run_id="invalid run id" if variant == "exact-run-format" else "publisher-only-run-001",
        write_barrier=variant != "missing-barrier",
        stage_manifest_digest="0" * 64 if variant == "plist-drift" else None,
    )
    env, fake_home, mutation_log, _manifest, _barrier, _loaded, live_payloads = fixture
    env["PANTHEON_ACTIVATION_CORRELATION_ID"] = f"publisher-only-{variant}"
    launch_agents = fake_home / "Library" / "LaunchAgents"
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    exact_run_receipt = stage_dir / "publisher-exact-run-id"
    if variant == "missing-exact-run-receipt":
        exact_run_receipt.unlink()
    elif variant == "stale-exact-run-receipt":
        _write_publisher_normal_plist(
            stage_dir / "com.pantheon.agy-content-publisher.plist",
            manifest=_manifest,
            max_runs="1",
            exact_run_id=None,
        )
    elif variant == "exact-run-receipt-mismatch":
        exact_run_receipt.write_text("publisher-only-run-002\\n", encoding="utf-8")
    elif variant == "empty-exact-run-receipt":
        exact_run_receipt.write_text("", encoding="utf-8")

    activated = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--activate-publisher-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode != 0
    assert expected_error in activated.stderr or expected_error in activated.stdout
    assert not mutation_log.exists()
    for label in runtime_manifest.SERVICE_LABELS:
        assert (launch_agents / f"{label}.plist").read_bytes() == live_payloads[label]
    receipt = json.loads(
        (
            launch_agents
            / ".pantheon-four-lane-stage"
            / "failure-receipt.json"
        ).read_text(encoding="utf-8")
    )
    assert receipt["status"] == "ACTIVATION_REJECTED"
    assert receipt["correlation_id"] == f"publisher-only-{variant}"
    assert receipt["exit_reason"] == {
        "phase": expected_phase,
        "exit_code": 1,
    }
    assert not (stage_dir / "publisher-only-backups").exists()


def test_activation_only_adopts_exact_legacy_capacity_guard(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    env["PANTHEON_ACTIVATION_CORRELATION_ID"] = "apf-004-legacy-capacity-green"
    manifest = runtime_manifest.load_manifest(Path(env["PANTHEON_RUNTIME_MANIFEST_FILE"]))
    launch_agents = fake_home / "Library" / "LaunchAgents"
    legacy_plist = launch_agents / "com.pantheon.content-capacity-guard.plist"
    _write_legacy_capacity_guard_plist(legacy_plist)
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    ready_root = stage_dir / "readiness" / str(manifest["generation"])
    readiness_fixture = tmp_path / "readiness-fixture"
    for label in runtime_manifest.SERVICE_LABELS:
        runtime_manifest.write_readiness_ack(readiness_fixture, manifest, label)
    loaded = tmp_path / "loaded"
    loaded.mkdir()
    (loaded / "com.pantheon.content-capacity-guard").touch()
    child_io_marker = tmp_path / "child-io-marker"
    launchctl = tmp_path / "bin" / "launchctl"
    launchctl.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in *com.pantheon.agy-gemini-runner) exit 113;; esac\n"
        "  label=${2##*/}\n"
        f"  [ -f '{loaded}/'$label ] || exit 113\n"
        "  printf '%s\\n' 'state = waiting'\n"
        f"  printf '%s\\n' '    path = {legacy_plist}'\n"
        "  exit 0\n"
        "fi\n"
        f"printf '%s\\n' \"$*\" >> '{mutation_log}'\n"
        "if [ \"$1\" = \"bootout\" ]; then\n"
        "  label=${2##*/}\n"
        f"  rm -f '{loaded}/'$label\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = \"bootstrap\" ]; then\n"
        "  label=${3##*/}\n"
        "  label=${label%.plist}\n"
        "  /usr/libexec/PlistBuddy -c 'Print :ProgramArguments' \"$3\" "
        f"| grep -q -- '--activation-only' || touch '{child_io_marker}'\n"
        f"  touch '{loaded}/'$label\n"
        f"  mkdir -p '{ready_root}'\n"
        f"  cp '{readiness_fixture}/'* '{ready_root}/'\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)
    staged = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--install",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert staged.returncode == 0, staged.stderr
    for label in {
        "com.pantheon.agy-content-publisher",
        "com.pantheon.content-capacity-guard",
    }:
        _write_activation_stage_plist(
            stage_dir / f"{label}.plist",
            label=label,
            manifest=manifest,
        )

    activated = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--activate-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode == 0, activated.stderr
    assert not child_io_marker.exists()
    assert not stage_dir.exists()
    mutations = mutation_log.read_text(encoding="utf-8")
    assert mutations.count("bootout") == 1
    assert mutations.count("bootstrap") == len(runtime_manifest.SERVICE_LABELS)
    barrier = (
        Path(manifest["publisher_state_root"])
        / f"four-lane-activation-{manifest['generation']}.barrier"
    )
    assert runtime_manifest.validate_barrier(barrier, manifest)["status"] == "PASS"


def test_activation_only_adopts_legacy_capacity_with_complete_inert_plist_set(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    env["PANTHEON_ACTIVATION_CORRELATION_ID"] = "apf-004-inert-six-green"
    manifest = runtime_manifest.load_manifest(Path(env["PANTHEON_RUNTIME_MANIFEST_FILE"]))
    launch_agents = fake_home / "Library" / "LaunchAgents"
    for label in runtime_manifest.SERVICE_LABELS:
        _write_legacy_capacity_guard_plist(
            launch_agents / f"{label}.plist",
            label=label,
        )
    legacy_plist = launch_agents / "com.pantheon.content-capacity-guard.plist"
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    ready_root = stage_dir / "readiness" / str(manifest["generation"])
    readiness_fixture = tmp_path / "readiness-fixture"
    for label in runtime_manifest.SERVICE_LABELS:
        runtime_manifest.write_readiness_ack(readiness_fixture, manifest, label)
    loaded = tmp_path / "loaded"
    loaded.mkdir()
    (loaded / "com.pantheon.content-capacity-guard").touch()
    child_io_marker = tmp_path / "child-io-marker"
    launchctl = tmp_path / "bin" / "launchctl"
    launchctl.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in *com.pantheon.agy-gemini-runner) exit 113;; esac\n"
        "  label=${2##*/}\n"
        f"  [ -f '{loaded}/'$label ] || exit 113\n"
        "  printf '%s\\n' 'state = waiting'\n"
        f"  printf '%s\\n' '    path = {legacy_plist}'\n"
        "  exit 0\n"
        "fi\n"
        f"printf '%s\\n' \"$*\" >> '{mutation_log}'\n"
        "if [ \"$1\" = \"bootout\" ]; then\n"
        "  label=${2##*/}\n"
        f"  rm -f '{loaded}/'$label\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = \"bootstrap\" ]; then\n"
        "  label=${3##*/}\n"
        "  label=${label%.plist}\n"
        "  /usr/libexec/PlistBuddy -c 'Print :ProgramArguments' \"$3\" "
        f"| grep -q -- '--activation-only' || touch '{child_io_marker}'\n"
        f"  touch '{loaded}/'$label\n"
        f"  mkdir -p '{ready_root}'\n"
        f"  cp '{readiness_fixture}/'* '{ready_root}/'\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)
    staged = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--install",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert staged.returncode == 0, staged.stderr
    for label in {
        "com.pantheon.agy-content-publisher",
        "com.pantheon.content-capacity-guard",
    }:
        _write_activation_stage_plist(
            stage_dir / f"{label}.plist",
            label=label,
            manifest=manifest,
        )

    activated = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--activate-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode == 0, activated.stderr
    assert not child_io_marker.exists()
    assert not stage_dir.exists()
    mutations = mutation_log.read_text(encoding="utf-8")
    assert mutations.count("bootout") == 1
    assert mutations.count("bootstrap") == len(runtime_manifest.SERVICE_LABELS)
    barrier = (
        Path(manifest["publisher_state_root"])
        / f"four-lane-activation-{manifest['generation']}.barrier"
    )
    assert runtime_manifest.validate_barrier(barrier, manifest)["status"] == "PASS"


def test_activation_only_inert_six_runs_real_barrier_exec_readiness(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    env["PANTHEON_ACTIVATION_CORRELATION_ID"] = "apf-004-real-barrier-readiness"
    manifest_path = Path(env["PANTHEON_RUNTIME_MANIFEST_FILE"])
    manifest = runtime_manifest.load_manifest(manifest_path)
    launch_agents = fake_home / "Library" / "LaunchAgents"
    for label in runtime_manifest.SERVICE_LABELS:
        _write_legacy_capacity_guard_plist(
            launch_agents / f"{label}.plist",
            label=label,
        )
    legacy_plist = launch_agents / "com.pantheon.content-capacity-guard.plist"
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    loaded = tmp_path / "loaded"
    loaded.mkdir()
    (loaded / "com.pantheon.content-capacity-guard").touch()
    child_io_marker = tmp_path / "child-io-marker"
    pid_log = tmp_path / "barrier-exec-pids.log"
    subprocess_log_dir = tmp_path / "barrier-exec-logs"
    subprocess_log_dir.mkdir()
    launchctl = tmp_path / "bin" / "launchctl"
    launchctl.write_text(
        f"#!{sys.executable}\n"
        "import os, plistlib, subprocess, sys\n"
        "from pathlib import Path\n"
        f"mutation_log = Path({str(mutation_log)!r})\n"
        f"loaded = Path({str(loaded)!r})\n"
        f"pid_log = Path({str(pid_log)!r})\n"
        f"legacy_plist = {str(legacy_plist)!r}\n"
        f"log_dir = Path({str(subprocess_log_dir)!r})\n"
        "args = sys.argv[1:]\n"
        "if args[:1] == ['print']:\n"
        "    label = args[1].split('/')[-1]\n"
        "    if label == 'com.pantheon.agy-gemini-runner':\n"
        "        sys.exit(113)\n"
        "    if not (loaded / label).exists():\n"
        "        sys.exit(113)\n"
        "    print('state = waiting')\n"
        "    if label == 'com.pantheon.content-capacity-guard':\n"
        "        print(f'    path = {legacy_plist}')\n"
        "    sys.exit(0)\n"
        "with mutation_log.open('a', encoding='utf-8') as stream:\n"
        "    stream.write(' '.join(args) + '\\n')\n"
        "if args[:1] == ['bootout']:\n"
        "    label = args[1].split('/')[-1]\n"
        "    try:\n"
        "        (loaded / label).unlink()\n"
        "    except FileNotFoundError:\n"
        "        pass\n"
        "    sys.exit(0)\n"
        "if args[:1] == ['bootstrap']:\n"
        "    plist_path = Path(args[2])\n"
        "    with plist_path.open('rb') as stream:\n"
        "        payload = plistlib.load(stream)\n"
        "    label = payload['Label']\n"
        "    (loaded / label).touch()\n"
        "    child_env = os.environ.copy()\n"
        "    child_env.update(payload.get('EnvironmentVariables', {}))\n"
        "    child_env['PANTHEON_FORMAL_RUNTIME'] = '1'\n"
        "    child_env.pop('PANTHEON_RUNTIME_ACTIVATION_TOKEN', None)\n"
        "    program_args = list(payload['ProgramArguments'])\n"
        "    if '--manifest' in program_args:\n"
        "        child_env['PANTHEON_RUNTIME_MANIFEST'] = program_args[program_args.index('--manifest') + 1]\n"
        "    stdout = (log_dir / f'{label}.out').open('wb')\n"
        "    stderr = (log_dir / f'{label}.err').open('wb')\n"
        "    process = subprocess.Popen(\n"
        "        program_args,\n"
        "        cwd=payload.get('WorkingDirectory') or None,\n"
        "        env=child_env,\n"
        "        stdout=stdout,\n"
        "        stderr=stderr,\n"
        "        close_fds=True,\n"
        "    )\n"
        "    with pid_log.open('a', encoding='utf-8') as stream:\n"
        "        stream.write(f'{label} {process.pid}\\n')\n"
        "    sys.exit(0)\n"
        "sys.exit(0)\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)
    staged = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--install",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert staged.returncode == 0, staged.stderr
    runtime_manifest.write_manifest(stage_dir / "runtime-manifest.json", manifest)
    for label in {
        "com.pantheon.agy-content-publisher",
        "com.pantheon.content-capacity-guard",
    }:
        _write_activation_stage_plist(
            stage_dir / f"{label}.plist",
            label=label,
            manifest=manifest,
        )
    for staged_plist in stage_dir.glob("*.plist"):
        with staged_plist.open("rb") as stream:
            payload = plistlib.load(stream)
        arguments = list(payload["ProgramArguments"])
        separator = arguments.index("--")
        payload["ProgramArguments"] = arguments[: separator + 1] + [
            sys.executable,
            "-c",
            f"from pathlib import Path; Path({str(child_io_marker)!r}).write_text('bad')",
        ]
        with staged_plist.open("wb") as stream:
            plistlib.dump(payload, stream)
        staged_plist.chmod(0o600)

    activated = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--activate-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode == 0, activated.stderr
    assert not child_io_marker.exists()
    assert pid_log.read_text(encoding="utf-8").count("\n") == len(
        runtime_manifest.SERVICE_LABELS
    )
    barrier = (
        Path(manifest["publisher_state_root"])
        / f"four-lane-activation-{manifest['generation']}.barrier"
    )
    assert runtime_manifest.validate_barrier(barrier, manifest)["status"] == "PASS"
    assert not stage_dir.exists()


@pytest.mark.parametrize(
    "variant",
    [
        "partial-set",
        "inert-label-loaded",
        "inert-symlink",
        "inert-owner",
        "inert-mode",
        "snapshot-hash-drift",
        "snapshot-label-loaded",
    ],
)
def test_activation_only_inert_six_adoption_blocks_invalid_state_before_mutation(
    tmp_path: Path,
    variant: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    env["PANTHEON_ACTIVATION_CORRELATION_ID"] = f"apf-004-inert-{variant}"
    manifest = runtime_manifest.load_manifest(Path(env["PANTHEON_RUNTIME_MANIFEST_FILE"]))
    launch_agents = fake_home / "Library" / "LaunchAgents"
    inert_label = "com.pantheon.agy-content-publisher"
    inert_plist = launch_agents / f"{inert_label}.plist"
    for label in runtime_manifest.SERVICE_LABELS:
        _write_legacy_capacity_guard_plist(
            launch_agents / f"{label}.plist",
            label=label,
        )
    if variant == "partial-set":
        inert_plist.unlink()
    if variant == "inert-symlink":
        symlink_target = tmp_path / "inert-business-target.plist"
        symlink_target.write_bytes(inert_plist.read_bytes())
        symlink_target.chmod(0o600)
        inert_plist.unlink()
        inert_plist.symlink_to(symlink_target)
    if variant == "inert-mode":
        inert_plist.chmod(0o644)
    if variant == "inert-owner":
        stat = tmp_path / "bin" / "stat"
        stat.write_text(
            "#!/bin/sh\n"
            f"if [ \"$2\" = '%u' ] && [ \"$3\" = '{inert_plist}' ]; then\n"
            "  printf '%s\\n' 0\n"
            "  exit 0\n"
            "fi\n"
            "exec /usr/bin/stat \"$@\"\n",
            encoding="utf-8",
        )
        stat.chmod(0o700)
    legacy_plist = launch_agents / "com.pantheon.content-capacity-guard.plist"
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    loaded = tmp_path / "loaded"
    loaded.mkdir()
    (loaded / "com.pantheon.content-capacity-guard").touch()
    if variant == "inert-label-loaded":
        (loaded / inert_label).touch()
    print_count = tmp_path / "inert-print-count"
    launchctl = tmp_path / "bin" / "launchctl"
    launchctl.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in *com.pantheon.agy-gemini-runner) exit 113;; esac\n"
        "  label=${2##*/}\n"
        f"  if [ \"$label\" = '{inert_label}' ]; then\n"
        f"    count=$(cat '{print_count}' 2>/dev/null || printf 0)\n"
        "    count=$((count + 1))\n"
        f"    printf '%s' \"$count\" > '{print_count}'\n"
        f"    if [ '{variant}' = 'snapshot-hash-drift' ] && [ \"$count\" -ge 2 ]; then\n"
        f"      printf '%s\\n' drift >> '{inert_plist}'\n"
        "    fi\n"
        f"    if [ '{variant}' = 'snapshot-label-loaded' ] && [ \"$count\" -ge 2 ]; then\n"
        f"      touch '{loaded}/{inert_label}'\n"
        "    fi\n"
        "  fi\n"
        f"  [ -f '{loaded}/'$label ] || exit 113\n"
        "  printf '%s\\n' 'state = waiting'\n"
        f"  printf '%s\\n' '    path = {legacy_plist}'\n"
        "  exit 0\n"
        "fi\n"
        f"printf '%s\\n' \"$*\" >> '{mutation_log}'\n"
        "exit 0\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)
    staged = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--install",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert staged.returncode == 0, staged.stderr
    for label in {
        "com.pantheon.agy-content-publisher",
        "com.pantheon.content-capacity-guard",
    }:
        _write_activation_stage_plist(
            stage_dir / f"{label}.plist",
            label=label,
            manifest=manifest,
        )

    activated = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--activate-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode != 0
    assert not mutation_log.exists()
    receipt = json.loads((stage_dir / "failure-receipt.json").read_text(encoding="utf-8"))
    expected_phase = (
        "legacy_capacity_adoption_pre_replace"
        if variant in {"snapshot-hash-drift", "snapshot-label-loaded"}
        else "previous_barrier_validation"
    )
    assert receipt["status"] == "ACTIVATION_REJECTED"
    assert receipt["correlation_id"] == f"apf-004-inert-{variant}"
    assert receipt["exit_reason"] == {
        "phase": expected_phase,
        "exit_code": 1,
    }


@pytest.mark.parametrize(
    ("rollback_bootstrap_fails", "expected_status"),
    [(False, "ROLLBACK_COMPLETE"), (True, "ROLLBACK_FAILED")],
)
def test_activation_only_inert_six_adoption_rollback_receipts(
    tmp_path: Path,
    rollback_bootstrap_fails: bool,
    expected_status: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    env["PANTHEON_ACTIVATION_CORRELATION_ID"] = (
        f"apf-004-inert-six-{expected_status.lower()}"
    )
    manifest = runtime_manifest.load_manifest(Path(env["PANTHEON_RUNTIME_MANIFEST_FILE"]))
    launch_agents = fake_home / "Library" / "LaunchAgents"
    legacy_payloads: dict[str, bytes] = {}
    for label in runtime_manifest.SERVICE_LABELS:
        legacy_payloads[label] = _write_legacy_capacity_guard_plist(
            launch_agents / f"{label}.plist",
            label=label,
        )
    legacy_plist = launch_agents / "com.pantheon.content-capacity-guard.plist"
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    ready_root = stage_dir / "readiness" / str(manifest["generation"])
    loaded = tmp_path / "loaded"
    loaded.mkdir()
    (loaded / "com.pantheon.content-capacity-guard").touch()
    bootstrap_count = tmp_path / "bootstrap-count"
    launchctl = tmp_path / "bin" / "launchctl"
    rollback_fail_test = "1" if rollback_bootstrap_fails else "0"
    launchctl.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in *com.pantheon.agy-gemini-runner) exit 113;; esac\n"
        "  label=${2##*/}\n"
        f"  [ -f '{loaded}/'$label ] || exit 113\n"
        "  printf '%s\\n' 'state = waiting'\n"
        f"  printf '%s\\n' '    path = {legacy_plist}'\n"
        "  exit 0\n"
        "fi\n"
        f"printf '%s\\n' \"$*\" >> '{mutation_log}'\n"
        "if [ \"$1\" = \"bootout\" ]; then\n"
        "  label=${2##*/}\n"
        f"  rm -f '{loaded}/'$label\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = \"bootstrap\" ]; then\n"
        f"  count=$(cat '{bootstrap_count}' 2>/dev/null || printf 0)\n"
        "  count=$((count + 1))\n"
        f"  printf '%s' \"$count\" > '{bootstrap_count}'\n"
        "  if [ \"$count\" -eq 1 ]; then exit 1; fi\n"
        f"  if [ '{rollback_fail_test}' = '1' ] && [ \"$count\" -eq 2 ]; then exit 1; fi\n"
        "  label=${3##*/}\n"
        "  label=${label%.plist}\n"
        f"  mkdir -p '{ready_root}'\n"
        f"  touch '{loaded}/'$label\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)
    staged = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--install",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert staged.returncode == 0, staged.stderr
    for label in {
        "com.pantheon.agy-content-publisher",
        "com.pantheon.content-capacity-guard",
    }:
        _write_activation_stage_plist(
            stage_dir / f"{label}.plist",
            label=label,
            manifest=manifest,
        )

    activated = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--activate-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode != 0
    for label, payload in legacy_payloads.items():
        assert (launch_agents / f"{label}.plist").read_bytes() == payload
    if expected_status == "ROLLBACK_COMPLETE":
        assert sorted(path.name for path in loaded.iterdir()) == [
            "com.pantheon.content-capacity-guard"
        ]
    receipt = json.loads((stage_dir / "failure-receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == expected_status
    assert receipt["correlation_id"] == (
        f"apf-004-inert-six-{expected_status.lower()}"
    )
    assert receipt["exit_reason"] == {
        "phase": "bootstrap_staged_services",
        "exit_code": 1,
    }


@pytest.mark.parametrize(
    ("rollback_bootstrap_fails", "expected_status"),
    [(False, "ROLLBACK_COMPLETE"), (True, "ROLLBACK_FAILED")],
)
def test_activation_only_inert_six_barrier_timeout_rollback_receipts(
    tmp_path: Path,
    rollback_bootstrap_fails: bool,
    expected_status: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    env["PANTHEON_ACTIVATION_CORRELATION_ID"] = (
        f"apf-004-barrier-timeout-{expected_status.lower()}"
    )
    env["PANTHEON_ACTIVATION_BARRIER_TIMEOUT_SECONDS"] = "1"
    manifest = runtime_manifest.load_manifest(Path(env["PANTHEON_RUNTIME_MANIFEST_FILE"]))
    launch_agents = fake_home / "Library" / "LaunchAgents"
    legacy_payloads: dict[str, bytes] = {}
    for label in runtime_manifest.SERVICE_LABELS:
        legacy_payloads[label] = _write_legacy_capacity_guard_plist(
            launch_agents / f"{label}.plist",
            label=label,
        )
    legacy_plist = launch_agents / "com.pantheon.content-capacity-guard.plist"
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    loaded = tmp_path / "loaded"
    loaded.mkdir()
    (loaded / "com.pantheon.content-capacity-guard").touch()
    bootstrap_count = tmp_path / "bootstrap-count"
    rollback_fail_test = "1" if rollback_bootstrap_fails else "0"
    launchctl = tmp_path / "bin" / "launchctl"
    launchctl.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in *com.pantheon.agy-gemini-runner) exit 113;; esac\n"
        "  label=${2##*/}\n"
        f"  [ -f '{loaded}/'$label ] || exit 113\n"
        "  printf '%s\\n' 'state = waiting'\n"
        f"  printf '%s\\n' '    path = {legacy_plist}'\n"
        "  exit 0\n"
        "fi\n"
        f"printf '%s\\n' \"$*\" >> '{mutation_log}'\n"
        "if [ \"$1\" = \"bootout\" ]; then\n"
        "  label=${2##*/}\n"
        f"  rm -f '{loaded}/'$label\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = \"bootstrap\" ]; then\n"
        f"  count=$(cat '{bootstrap_count}' 2>/dev/null || printf 0)\n"
        "  count=$((count + 1))\n"
        f"  printf '%s' \"$count\" > '{bootstrap_count}'\n"
        f"  if [ '{rollback_fail_test}' = '1' ] && [ \"$count\" -eq 8 ]; then exit 1; fi\n"
        "  label=${3##*/}\n"
        "  label=${label%.plist}\n"
        f"  touch '{loaded}/'$label\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)
    staged = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--install",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert staged.returncode == 0, staged.stderr
    for label in {
        "com.pantheon.agy-content-publisher",
        "com.pantheon.content-capacity-guard",
    }:
        _write_activation_stage_plist(
            stage_dir / f"{label}.plist",
            label=label,
            manifest=manifest,
        )

    activated = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--activate-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode != 0
    for label, payload in legacy_payloads.items():
        assert (launch_agents / f"{label}.plist").read_bytes() == payload
    if expected_status == "ROLLBACK_COMPLETE":
        assert sorted(path.name for path in loaded.iterdir()) == [
            "com.pantheon.content-capacity-guard"
        ]
    receipt = json.loads((stage_dir / "failure-receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == expected_status
    assert receipt["correlation_id"] == (
        f"apf-004-barrier-timeout-{expected_status.lower()}"
    )
    assert receipt["exit_reason"] == {
        "phase": "barrier_activation",
        "exit_code": 1,
    }
    if expected_status == "ROLLBACK_COMPLETE":
        assert receipt["rollback_check_ids"] == []
    else:
        assert "rollback.bootstrap" in receipt["rollback_check_ids"]


@pytest.mark.parametrize(
    "variant",
    [
        "multi-loaded-label",
        "business-plist-present",
        "legacy-plist-missing",
        "identity-path-drift",
        "prefix-forged-path",
        "duplicate-path",
        "relative-path",
        "noncanonical-path",
        "symlink-alias",
        "extra-whitespace-path",
        "running-state",
        "symlink-path",
        "snapshot-mode-invalid",
    ],
)
def test_activation_only_legacy_capacity_adoption_blocks_invalid_state_before_mutation(
    tmp_path: Path,
    variant: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    env["PANTHEON_ACTIVATION_CORRELATION_ID"] = f"apf-004-legacy-{variant}"
    manifest = runtime_manifest.load_manifest(Path(env["PANTHEON_RUNTIME_MANIFEST_FILE"]))
    launch_agents = fake_home / "Library" / "LaunchAgents"
    legacy_plist = launch_agents / "com.pantheon.content-capacity-guard.plist"
    if variant != "legacy-plist-missing":
        _write_legacy_capacity_guard_plist(legacy_plist)
    if variant == "snapshot-mode-invalid":
        legacy_plist.chmod(0o644)
    if variant == "symlink-path":
        symlink_target = tmp_path / "legacy-capacity-target.plist"
        symlink_target.write_bytes(legacy_plist.read_bytes())
        symlink_target.chmod(0o600)
        legacy_plist.unlink()
        legacy_plist.symlink_to(symlink_target)
    if variant == "business-plist-present":
        _write_legacy_capacity_guard_plist(
            launch_agents / "com.pantheon.agy-content-publisher.plist"
        )
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    loaded = tmp_path / "loaded"
    loaded.mkdir()
    (loaded / "com.pantheon.content-capacity-guard").touch()
    if variant == "multi-loaded-label":
        (loaded / "com.pantheon.agy-content-publisher").touch()
    identity_path = legacy_plist
    if variant == "identity-path-drift":
        identity_path = launch_agents / "drifted-capacity-guard.plist"
    if variant == "prefix-forged-path":
        identity_path = Path(f"{legacy_plist}.forged")
    if variant == "relative-path":
        identity_path = Path("relative-capacity-guard.plist")
    if variant == "noncanonical-path":
        identity_path = f"{legacy_plist.parent}/./{legacy_plist.name}"
    if variant == "symlink-alias":
        alias_path = launch_agents / "capacity-alias.plist"
        alias_path.symlink_to(legacy_plist)
        identity_path = alias_path
    launch_state = "running" if variant == "running-state" else "waiting"
    path_line_prefix = "path = "
    if variant == "extra-whitespace-path":
        path_line_prefix = "path =  "
    duplicate_path_line = (
        f"  printf '%s\\n' 'path = {identity_path}.duplicate'\n"
        if variant == "duplicate-path"
        else ""
    )
    launchctl = tmp_path / "bin" / "launchctl"
    launchctl.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in *com.pantheon.agy-gemini-runner) exit 113;; esac\n"
        "  label=${2##*/}\n"
        f"  [ -f '{loaded}/'$label ] || exit 113\n"
        f"  printf '%s\\n' 'state = {launch_state}'\n"
        f"  printf '%s\\n' '{path_line_prefix}{identity_path}'\n"
        f"{duplicate_path_line}"
        "  exit 0\n"
        "fi\n"
        f"printf '%s\\n' \"$*\" >> '{mutation_log}'\n"
        "exit 0\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)
    staged = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--install",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert staged.returncode == 0, staged.stderr
    for label in {
        "com.pantheon.agy-content-publisher",
        "com.pantheon.content-capacity-guard",
    }:
        _write_activation_stage_plist(
            stage_dir / f"{label}.plist",
            label=label,
            manifest=manifest,
        )

    activated = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--activate-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode != 0
    assert not mutation_log.exists()
    receipt = json.loads((stage_dir / "failure-receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "ACTIVATION_REJECTED"
    assert receipt["correlation_id"] == f"apf-004-legacy-{variant}"
    assert receipt["exit_reason"] == {
        "phase": "previous_barrier_validation",
        "exit_code": 1,
    }


@pytest.mark.parametrize(
    ("rollback_bootstrap_fails", "expected_status"),
    [(False, "ROLLBACK_COMPLETE"), (True, "ROLLBACK_FAILED")],
)
def test_activation_only_legacy_capacity_adoption_rollback_receipts(
    tmp_path: Path,
    rollback_bootstrap_fails: bool,
    expected_status: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    env["PANTHEON_ACTIVATION_CORRELATION_ID"] = (
        f"apf-004-legacy-capacity-{expected_status.lower()}"
    )
    manifest = runtime_manifest.load_manifest(Path(env["PANTHEON_RUNTIME_MANIFEST_FILE"]))
    launch_agents = fake_home / "Library" / "LaunchAgents"
    legacy_plist = launch_agents / "com.pantheon.content-capacity-guard.plist"
    legacy_payload = _write_legacy_capacity_guard_plist(legacy_plist)
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    ready_root = stage_dir / "readiness" / str(manifest["generation"])
    loaded = tmp_path / "loaded"
    loaded.mkdir()
    (loaded / "com.pantheon.content-capacity-guard").touch()
    bootstrap_count = tmp_path / "bootstrap-count"
    launchctl = tmp_path / "bin" / "launchctl"
    rollback_fail_test = "1" if rollback_bootstrap_fails else "0"
    launchctl.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in *com.pantheon.agy-gemini-runner) exit 113;; esac\n"
        "  label=${2##*/}\n"
        f"  [ -f '{loaded}/'$label ] || exit 113\n"
        "  printf '%s\\n' 'state = waiting'\n"
        f"  printf '%s\\n' 'path = {legacy_plist}'\n"
        "  exit 0\n"
        "fi\n"
        f"printf '%s\\n' \"$*\" >> '{mutation_log}'\n"
        "if [ \"$1\" = \"bootout\" ]; then\n"
        "  label=${2##*/}\n"
        f"  rm -f '{loaded}/'$label\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = \"bootstrap\" ]; then\n"
        f"  count=$(cat '{bootstrap_count}' 2>/dev/null || printf 0)\n"
        "  count=$((count + 1))\n"
        f"  printf '%s' \"$count\" > '{bootstrap_count}'\n"
        "  if [ \"$count\" -eq 1 ]; then exit 1; fi\n"
        f"  if [ '{rollback_fail_test}' = '1' ] && [ \"$count\" -eq 2 ]; then exit 1; fi\n"
        "  label=${3##*/}\n"
        "  label=${label%.plist}\n"
        f"  mkdir -p '{ready_root}'\n"
        f"  touch '{loaded}/'$label\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)
    staged = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--install",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert staged.returncode == 0, staged.stderr
    for label in {
        "com.pantheon.agy-content-publisher",
        "com.pantheon.content-capacity-guard",
    }:
        _write_activation_stage_plist(
            stage_dir / f"{label}.plist",
            label=label,
            manifest=manifest,
        )

    activated = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--activate-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode != 0
    assert legacy_plist.read_bytes() == legacy_payload
    if expected_status == "ROLLBACK_COMPLETE":
        assert sorted(path.name for path in loaded.iterdir()) == [
            "com.pantheon.content-capacity-guard"
        ]
    receipt = json.loads((stage_dir / "failure-receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == expected_status
    assert receipt["correlation_id"] == (
        f"apf-004-legacy-capacity-{expected_status.lower()}"
    )
    assert receipt["exit_reason"] == {
        "phase": "bootstrap_staged_services",
        "exit_code": 1,
    }
    mutations = mutation_log.read_text(encoding="utf-8")
    assert "bootout" in mutations
    assert "bootstrap" in mutations


def test_normal_activate_rejects_legacy_capacity_adoption_authority_before_mutation(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    env["PANTHEON_ACTIVATION_CORRELATION_ID"] = "apf-004-normal-no-legacy-adopt"
    manifest = runtime_manifest.load_manifest(Path(env["PANTHEON_RUNTIME_MANIFEST_FILE"]))
    launch_agents = fake_home / "Library" / "LaunchAgents"
    legacy_plist = launch_agents / "com.pantheon.content-capacity-guard.plist"
    _write_legacy_capacity_guard_plist(legacy_plist)
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    loaded = tmp_path / "loaded"
    loaded.mkdir()
    (loaded / "com.pantheon.content-capacity-guard").touch()
    launchctl = tmp_path / "bin" / "launchctl"
    launchctl.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in *com.pantheon.agy-gemini-runner) exit 113;; esac\n"
        "  label=${2##*/}\n"
        f"  [ -f '{loaded}/'$label ] || exit 113\n"
        "  printf '%s\\n' 'state = waiting'\n"
        f"  printf '%s\\n' 'path = {legacy_plist}'\n"
        "  exit 0\n"
        "fi\n"
        f"printf '%s\\n' \"$*\" >> '{mutation_log}'\n"
        "exit 0\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)
    staged = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--install",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert staged.returncode == 0, staged.stderr
    for label in {
        "com.pantheon.agy-content-publisher",
        "com.pantheon.content-capacity-guard",
    }:
        _write_activation_stage_plist(
            stage_dir / f"{label}.plist",
            label=label,
            manifest=manifest,
        )

    activated = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--activate",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode != 0
    assert not mutation_log.exists()
    receipt = json.loads((stage_dir / "failure-receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "ACTIVATION_REJECTED"
    assert receipt["correlation_id"] == "apf-004-normal-no-legacy-adopt"
    assert receipt["exit_reason"] == {
        "phase": "previous_barrier_validation",
        "exit_code": 1,
    }


def test_activation_rejects_legacy_loaded_without_valid_barrier_before_live_replacement(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    env["PANTHEON_ACTIVATION_CORRELATION_ID"] = "apf-004-legacy-barrier-red"
    manifest = runtime_manifest.load_manifest(Path(env["PANTHEON_RUNTIME_MANIFEST_FILE"]))
    launch_agents = fake_home / "Library" / "LaunchAgents"
    launch_agents.mkdir(parents=True)
    previous_payload = plistlib.dumps(
        {
            "Label": "com.pantheon.agy-gemini-coordinator",
            "ProgramArguments": ["python", "-m", "legacy"],
            "EnvironmentVariables": {
                "PANTHEON_RUNTIME_MANIFEST": env["PANTHEON_RUNTIME_MANIFEST_FILE"],
                "PANTHEON_RUNTIME_MANIFEST_DIGEST": manifest["manifest_digest"],
            },
        }
    )
    for label in runtime_manifest.SERVICE_LABELS:
        (launch_agents / f"{label}.plist").write_bytes(previous_payload)
    launchctl = tmp_path / "bin" / "launchctl"
    loaded = tmp_path / "loaded"
    loaded.mkdir()
    for label in runtime_manifest.SERVICE_LABELS:
        (loaded / label).touch()
    launchctl.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$*\" >> '{mutation_log}'\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in *com.pantheon.agy-gemini-runner) exit 113;; esac\n"
        "  label=${2##*/}\n"
        f"  [ -f '{loaded}/'$label ] || exit 113\n"
        "  printf '%s\\n' 'service = legacy-loaded-no-barrier'\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = \"bootout\" ]; then exit 0; fi\n"
        "if [ \"$1\" = \"bootstrap\" ]; then exit 0; fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)

    staged = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--install",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert staged.returncode == 0, staged.stderr
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    for label in {
        "com.pantheon.agy-content-publisher",
        "com.pantheon.content-capacity-guard",
    }:
        _write_activation_stage_plist(
            stage_dir / f"{label}.plist",
            label=label,
            manifest=manifest,
        )

    activated = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--activate-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode != 0
    for label in runtime_manifest.SERVICE_LABELS:
        assert (launch_agents / f"{label}.plist").read_bytes() == previous_payload
    mutations = mutation_log.read_text(encoding="utf-8")
    assert "bootout" not in mutations
    assert "bootstrap" not in mutations
    receipt = json.loads((stage_dir / "failure-receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "ACTIVATION_REJECTED"
    assert receipt["correlation_id"] == "apf-004-legacy-barrier-red"
    assert receipt["exit_reason"] == {
        "phase": "previous_barrier_validation",
        "exit_code": 1,
    }


def _prepare_promoted_manifest_legacy_barrier_fixture(
    tmp_path: Path,
    *,
    correlation_id: str,
    launch_state: str = "waiting",
    include_pid: bool = False,
) -> tuple[
    dict[str, str],
    Path,
    Path,
    dict[str, object],
    dict[str, object],
    Path,
    Path,
    Path,
    Path,
]:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    env["PANTHEON_ACTIVATION_CORRELATION_ID"] = correlation_id
    env["PANTHEON_ACTIVATION_BARRIER_TIMEOUT_SECONDS"] = "1"
    shared_manifest_path = Path(env["PANTHEON_RUNTIME_MANIFEST_FILE"])
    new_manifest = runtime_manifest.load_manifest(shared_manifest_path)
    old_manifest = runtime_manifest.build_manifest(
        actor_root=repo_root,
        queue_root=Path(str(new_manifest["queue_root"])),
        publisher_state_root=Path(str(new_manifest["publisher_state_root"])),
        log_root=Path(str(new_manifest["log_root"])),
        identity="g8-old-live",
        runtime_digest="8" * 64,
        generation="g8-old-generation",
        python_executable=Path(sys.executable).resolve(strict=True),
        uv_executable=Path("/usr/bin/true"),
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    launch_agents.mkdir(parents=True, exist_ok=True)
    old_ready = tmp_path / "old-ready"
    old_barrier = (
        Path(str(old_manifest["publisher_state_root"]))
        / f"four-lane-activation-{old_manifest['generation']}.barrier"
    )
    for label in runtime_manifest.SERVICE_LABELS:
        runtime_manifest.write_readiness_ack(old_ready, old_manifest, label)
    runtime_manifest.activate_barrier(old_barrier, old_ready, old_manifest)
    for label in runtime_manifest.SERVICE_LABELS:
        live_plist = launch_agents / f"{label}.plist"
        _write_activation_stage_plist(live_plist, label=label, manifest=old_manifest)
        with live_plist.open("rb") as stream:
            payload = plistlib.load(stream)
        payload["EnvironmentVariables"]["PANTHEON_RUNTIME_MANIFEST"] = str(
            shared_manifest_path
        )
        payload["ProgramArguments"].insert(
            payload["ProgramArguments"].index("--"),
            "--activation-only",
        )
        payload["ProgramArguments"][
            payload["ProgramArguments"].index("--manifest") + 1
        ] = str(shared_manifest_path)
        with live_plist.open("wb") as stream:
            plistlib.dump(payload, stream)
        live_plist.chmod(0o600)
    runtime_manifest.write_manifest(shared_manifest_path, new_manifest)
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    ready_root = stage_dir / "readiness" / str(new_manifest["generation"])
    readiness_fixture = tmp_path / "new-readiness-fixture"
    for label in runtime_manifest.SERVICE_LABELS:
        runtime_manifest.write_readiness_ack(readiness_fixture, new_manifest, label)
    loaded = tmp_path / "loaded"
    loaded.mkdir()
    for label in runtime_manifest.SERVICE_LABELS:
        (loaded / label).touch()
    child_io_marker = tmp_path / "child-io-marker"
    pid_line = "  printf '%s\\n' 'pid = 123'\n" if include_pid else ""
    launchctl = tmp_path / "bin" / "launchctl"
    launchctl.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in *com.pantheon.agy-gemini-runner) exit 113;; esac\n"
        "  label=${2##*/}\n"
        f"  [ -f '{loaded}/'$label ] || exit 113\n"
        f"  printf '%s\\n' 'state = {launch_state}'\n"
        f"{pid_line}"
        f"  printf '%s\\n' \"    path = {launch_agents}/$label.plist\"\n"
        "  exit 0\n"
        "fi\n"
        f"printf '%s\\n' \"$*\" >> '{mutation_log}'\n"
        "if [ \"$1\" = \"bootout\" ]; then\n"
        "  label=${2##*/}\n"
        f"  rm -f '{loaded}/'$label\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = \"bootstrap\" ]; then\n"
        "  label=${3##*/}\n"
        "  label=${label%.plist}\n"
        "  /usr/libexec/PlistBuddy -c 'Print :ProgramArguments' \"$3\" "
        f"| grep -q -- '--activation-only' || touch '{child_io_marker}'\n"
        f"  touch '{loaded}/'$label\n"
        f"  mkdir -p '{ready_root}'\n"
        f"  cp '{readiness_fixture}/'* '{ready_root}/'\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)
    staged = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--install",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert staged.returncode == 0, staged.stderr
    for label in {
        "com.pantheon.agy-content-publisher",
        "com.pantheon.content-capacity-guard",
    }:
        _write_activation_stage_plist(
            stage_dir / f"{label}.plist",
            label=label,
            manifest=new_manifest,
        )
    return (
        env,
        mutation_log,
        launch_agents,
        new_manifest,
        old_manifest,
        old_barrier,
        stage_dir,
        child_io_marker,
        repo_root,
    )


def test_activate_only_accepts_coherent_old_live_with_promoted_manifest_path(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    env["PANTHEON_ACTIVATION_CORRELATION_ID"] = "g8-legacy-shared-manifest"
    shared_manifest_path = Path(env["PANTHEON_RUNTIME_MANIFEST_FILE"])
    new_manifest = runtime_manifest.load_manifest(shared_manifest_path)
    old_manifest = runtime_manifest.build_manifest(
        actor_root=repo_root,
        queue_root=Path(str(new_manifest["queue_root"])),
        publisher_state_root=Path(str(new_manifest["publisher_state_root"])),
        log_root=Path(str(new_manifest["log_root"])),
        identity="g8-old-live",
        runtime_digest="8" * 64,
        generation="g8-old-generation",
        python_executable=Path(sys.executable).resolve(strict=True),
        uv_executable=Path("/usr/bin/true"),
    )
    launch_agents = fake_home / "Library" / "LaunchAgents"
    launch_agents.mkdir(parents=True, exist_ok=True)
    old_ready = tmp_path / "old-ready"
    old_barrier = (
        Path(str(old_manifest["publisher_state_root"]))
        / f"four-lane-activation-{old_manifest['generation']}.barrier"
    )
    for label in runtime_manifest.SERVICE_LABELS:
        runtime_manifest.write_readiness_ack(old_ready, old_manifest, label)
    runtime_manifest.activate_barrier(old_barrier, old_ready, old_manifest)
    old_payloads: dict[str, bytes] = {}
    for label in runtime_manifest.SERVICE_LABELS:
        live_plist = launch_agents / f"{label}.plist"
        _write_activation_stage_plist(live_plist, label=label, manifest=old_manifest)
        with live_plist.open("rb") as stream:
            payload = plistlib.load(stream)
        payload["EnvironmentVariables"]["PANTHEON_RUNTIME_MANIFEST"] = str(
            shared_manifest_path
        )
        payload["ProgramArguments"].insert(
            payload["ProgramArguments"].index("--"),
            "--activation-only",
        )
        payload["ProgramArguments"][
            payload["ProgramArguments"].index("--manifest") + 1
        ] = str(shared_manifest_path)
        with live_plist.open("wb") as stream:
            plistlib.dump(payload, stream)
        live_plist.chmod(0o600)
        old_payloads[label] = live_plist.read_bytes()
    runtime_manifest.write_manifest(shared_manifest_path, new_manifest)
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    ready_root = stage_dir / "readiness" / str(new_manifest["generation"])
    readiness_fixture = tmp_path / "new-readiness-fixture"
    for label in runtime_manifest.SERVICE_LABELS:
        runtime_manifest.write_readiness_ack(readiness_fixture, new_manifest, label)
    loaded = tmp_path / "loaded"
    loaded.mkdir()
    for label in runtime_manifest.SERVICE_LABELS:
        (loaded / label).touch()
    child_io_marker = tmp_path / "child-io-marker"
    launchctl = tmp_path / "bin" / "launchctl"
    launchctl.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in *com.pantheon.agy-gemini-runner) exit 113;; esac\n"
        "  label=${2##*/}\n"
        f"  [ -f '{loaded}/'$label ] || exit 113\n"
        "  printf '%s\\n' 'state = waiting'\n"
        f"  printf '%s\\n' \"    path = {launch_agents}/$label.plist\"\n"
        "  exit 0\n"
        "fi\n"
        f"printf '%s\\n' \"$*\" >> '{mutation_log}'\n"
        "if [ \"$1\" = \"bootout\" ]; then\n"
        "  label=${2##*/}\n"
        f"  rm -f '{loaded}/'$label\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"$1\" = \"bootstrap\" ]; then\n"
        "  label=${3##*/}\n"
        "  label=${label%.plist}\n"
        "  /usr/libexec/PlistBuddy -c 'Print :ProgramArguments' \"$3\" "
        f"| grep -q -- '--activation-only' || touch '{child_io_marker}'\n"
        f"  touch '{loaded}/'$label\n"
        f"  mkdir -p '{ready_root}'\n"
        f"  cp '{readiness_fixture}/'* '{ready_root}/'\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)

    staged = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--install",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert staged.returncode == 0, staged.stderr
    for label in {
        "com.pantheon.agy-content-publisher",
        "com.pantheon.content-capacity-guard",
    }:
        _write_activation_stage_plist(
            stage_dir / f"{label}.plist",
            label=label,
            manifest=new_manifest,
        )
    for label in runtime_manifest.SERVICE_LABELS:
        assert (launch_agents / f"{label}.plist").read_bytes() == old_payloads[label]

    activated = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--activate-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode == 0, activated.stderr
    assert not child_io_marker.exists()
    mutations = mutation_log.read_text(encoding="utf-8")
    assert mutations.count("bootout") == len(runtime_manifest.SERVICE_LABELS)
    assert mutations.count("bootstrap") == len(runtime_manifest.SERVICE_LABELS)
    assert not stage_dir.exists()


@pytest.mark.parametrize(
    ("variant", "action", "expected_phase"),
    [
        ("mixed-old-live", "--activate-only", "previous_barrier_validation"),
        ("running-old-live", "--activate-only", "previous_barrier_validation"),
        ("pid-old-live", "--activate-only", "previous_barrier_validation"),
        ("barrier-digest", "--activate-only", "previous_barrier_validation"),
        ("barrier-generation", "--activate-only", "previous_barrier_validation"),
        ("barrier-missing", "--activate-only", "previous_barrier_validation"),
        ("barrier-malformed", "--activate-only", "previous_barrier_validation"),
        ("new-stage-drift", "--activate-only", "aggregate_preflight"),
        ("normal-activation", "--activate", "previous_barrier_validation"),
    ],
)
def test_activate_only_promoted_manifest_legacy_barrier_blocks_invalid_transition_before_mutation(
    tmp_path: Path,
    variant: str,
    action: str,
    expected_phase: str,
) -> None:
    launch_state = "running" if variant == "running-old-live" else "waiting"
    fixture = _prepare_promoted_manifest_legacy_barrier_fixture(
        tmp_path,
        correlation_id=f"g8-legacy-shared-manifest-{variant}",
        launch_state=launch_state,
        include_pid=variant == "pid-old-live",
    )
    (
        env,
        mutation_log,
        launch_agents,
        _new_manifest,
        _old_manifest,
        old_barrier,
        stage_dir,
        child_io_marker,
        repo_root,
    ) = fixture
    if variant == "mixed-old-live":
        drifted = launch_agents / "com.pantheon.agy-gemini-new.plist"
        with drifted.open("rb") as stream:
            payload = plistlib.load(stream)
        payload["EnvironmentVariables"]["PANTHEON_RUNTIME_GENERATION"] = (
            "g8-old-generation-drift"
        )
        with drifted.open("wb") as stream:
            plistlib.dump(payload, stream)
        drifted.chmod(0o600)
    elif variant in {"barrier-digest", "barrier-generation"}:
        barrier_payload = json.loads(old_barrier.read_text(encoding="utf-8"))
        if variant == "barrier-digest":
            barrier_payload["manifest_digest"] = "0" * 64
        else:
            barrier_payload["generation"] = "g8-old-generation-drift"
        old_barrier.write_text(
            json.dumps(barrier_payload, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        old_barrier.chmod(0o600)
    elif variant == "barrier-missing":
        old_barrier.unlink()
    elif variant == "barrier-malformed":
        old_barrier.write_text("{broken\n", encoding="utf-8")
        old_barrier.chmod(0o600)
    elif variant == "new-stage-drift":
        staged_plist = stage_dir / "com.pantheon.agy-gemini-new.plist"
        with staged_plist.open("rb") as stream:
            payload = plistlib.load(stream)
        payload["EnvironmentVariables"]["PANTHEON_RUNTIME_MANIFEST_DIGEST"] = (
            "0" * 64
        )
        with staged_plist.open("wb") as stream:
            plistlib.dump(payload, stream)
        staged_plist.chmod(0o600)
    protected_before = {
        path: path.read_bytes()
        for path in sorted(launch_agents.glob("*.plist")) + [old_barrier]
        if path.exists()
    }
    missing_before = {
        path for path in sorted(launch_agents.glob("*.plist")) + [old_barrier]
        if not path.exists()
    }

    activated = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            action,
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode != 0
    assert not mutation_log.exists()
    assert not child_io_marker.exists()
    for path, payload in protected_before.items():
        assert path.read_bytes() == payload
    for path in missing_before:
        assert not path.exists()
    receipt = json.loads((stage_dir / "failure-receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "ACTIVATION_REJECTED"
    assert receipt["correlation_id"] == f"g8-legacy-shared-manifest-{variant}"
    assert receipt["exit_reason"] == {
        "phase": expected_phase,
        "exit_code": 1,
    }


@pytest.mark.parametrize(
    ("variant", "control"),
    [
        *(
            ("duplicate-same", control)
            for control in (
                "--barrier",
                "--expected-digest",
                "--manifest",
                "--service-label",
                "--activation-only",
            )
        ),
        *(
            ("duplicate-drift", control)
            for control in (
                "--barrier",
                "--expected-digest",
                "--manifest",
                "--service-label",
            )
        ),
        *(
            ("missing-value", control)
            for control in (
                "--barrier",
                "--expected-digest",
                "--manifest",
                "--service-label",
            )
        ),
        ("odd-outer-token", "--expected-digest"),
        ("multiple-separator", "--expected-digest"),
        *(
            ("child-control", control)
            for control in (
                "--barrier",
                "--expected-digest",
                "--manifest",
                "--service-label",
                "--activation-only",
            )
        ),
    ],
)
def test_activate_only_promoted_manifest_rejects_malformed_outer_authority_before_mutation(
    tmp_path: Path,
    variant: str,
    control: str,
) -> None:
    fixture = _prepare_promoted_manifest_legacy_barrier_fixture(
        tmp_path,
        correlation_id=f"g8-legacy-outer-argv-{variant}-{control.removeprefix('--')}",
    )
    (
        env,
        mutation_log,
        launch_agents,
        _new_manifest,
        _old_manifest,
        old_barrier,
        stage_dir,
        child_io_marker,
        repo_root,
    ) = fixture
    drifted = launch_agents / "com.pantheon.agy-gemini-new.plist"
    with drifted.open("rb") as stream:
        payload = plistlib.load(stream)
    arguments = payload["ProgramArguments"]
    separator = arguments.index("--")
    if variant.startswith("duplicate"):
        if control == "--activation-only":
            duplicate = [control]
        else:
            current_value = arguments[arguments.index(control) + 1]
            duplicate = [
                control,
                current_value if variant == "duplicate-same" else f"{current_value}-drift",
            ]
        arguments[separator:separator] = duplicate
    elif variant == "missing-value":
        del arguments[arguments.index(control) + 1]
    elif variant == "odd-outer-token":
        arguments.insert(separator, "unexpected-outer-token")
    elif variant == "multiple-separator":
        arguments.insert(separator, "--")
    elif variant == "child-control":
        child_value = [] if control == "--activation-only" else ["child-value"]
        arguments.extend([control, *child_value])
    else:
        raise AssertionError(f"unknown variant: {variant}")
    with drifted.open("wb") as stream:
        plistlib.dump(payload, stream)
    drifted.chmod(0o600)
    protected_before = {
        path: path.read_bytes()
        for path in sorted(launch_agents.glob("*.plist")) + [old_barrier]
    }

    activated = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--activate-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode != 0
    assert not mutation_log.exists()
    assert not child_io_marker.exists()
    for path, content in protected_before.items():
        assert path.read_bytes() == content
    receipt = json.loads(
        (stage_dir / "failure-receipt.json").read_text(encoding="utf-8")
    )
    assert receipt["status"] == "ACTIVATION_REJECTED"
    assert receipt["exit_reason"] == {
        "phase": "previous_barrier_validation",
        "exit_code": 1,
    }


def test_normal_activate_rejects_inert_six_adoption_authority_before_mutation(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    env["PANTHEON_ACTIVATION_CORRELATION_ID"] = "apf-004-normal-no-inert-adopt"
    manifest = runtime_manifest.load_manifest(Path(env["PANTHEON_RUNTIME_MANIFEST_FILE"]))
    launch_agents = fake_home / "Library" / "LaunchAgents"
    for label in runtime_manifest.SERVICE_LABELS:
        _write_legacy_capacity_guard_plist(
            launch_agents / f"{label}.plist",
            label=label,
        )
    legacy_plist = launch_agents / "com.pantheon.content-capacity-guard.plist"
    stage_dir = launch_agents / ".pantheon-four-lane-stage"
    loaded = tmp_path / "loaded"
    loaded.mkdir()
    (loaded / "com.pantheon.content-capacity-guard").touch()
    launchctl = tmp_path / "bin" / "launchctl"
    launchctl.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then\n"
        "  case \"$2\" in *com.pantheon.agy-gemini-runner) exit 113;; esac\n"
        "  label=${2##*/}\n"
        f"  [ -f '{loaded}/'$label ] || exit 113\n"
        "  printf '%s\\n' 'state = waiting'\n"
        f"  printf '%s\\n' '    path = {legacy_plist}'\n"
        "  exit 0\n"
        "fi\n"
        f"printf '%s\\n' \"$*\" >> '{mutation_log}'\n"
        "exit 0\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)
    staged = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--install",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert staged.returncode == 0, staged.stderr
    for label in {
        "com.pantheon.agy-content-publisher",
        "com.pantheon.content-capacity-guard",
    }:
        _write_activation_stage_plist(
            stage_dir / f"{label}.plist",
            label=label,
            manifest=manifest,
        )

    activated = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--activate",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode != 0
    assert not mutation_log.exists()
    receipt = json.loads((stage_dir / "failure-receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "ACTIVATION_REJECTED"
    assert receipt["correlation_id"] == "apf-004-normal-no-inert-adopt"
    assert receipt["exit_reason"] == {
        "phase": "previous_barrier_validation",
        "exit_code": 1,
    }


@pytest.mark.parametrize("fail_plutil_call", [1, 2, 3, 4, 5])
def test_installer_builds_and_lints_every_plist_before_any_mutation(
    tmp_path: Path,
    fail_plutil_call: int,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    state = tmp_path / "round-robin-state.json"
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=state,
        fail_plutil_call=fail_plutil_call,
    )

    completed = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert not fake_home.exists()
    assert not mutation_log.exists()


@pytest.mark.parametrize(
    "model_overrides",
    [
        {},
        {
            "AGY_WRITER_MODEL": "gemini-explicit-writer",
            "AGY_REVIEWER_MODEL": "gemini-explicit-reviewer",
        },
    ],
)
def test_installer_injects_one_shared_allocator_contract_into_coordinator_and_all_lanes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    model_overrides: dict[str, str],
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    fake_bin = tmp_path / "bin"
    fake_home = tmp_path / "home"
    fake_bin.mkdir()
    pool_file, _manifest_sha256 = _write_installer_pool(tmp_path)
    state_file = tmp_path / "round-robin-state.json"
    publisher_root = tmp_path / "existing-content-publisher"
    cli_path = tmp_path / "agy"
    cli_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    cli_path.chmod(0o700)
    dscl = fake_bin / "dscl"
    dscl.write_text(
        f"#!/bin/sh\nprintf '%s\\n' 'NFSHomeDirectory: {fake_home}'\n",
        encoding="utf-8",
    )
    dscl.chmod(0o700)
    launchctl = fake_bin / "launchctl"
    launchctl.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"print\" ]; then exit 1; fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    launchctl.chmod(0o700)
    manifest_path, queue_root, _state_root, _log_root = _write_installer_runtime_manifest(
        tmp_path,
        publisher_root=publisher_root,
    )
    gsc_copy_root = queue_root / "gsc-copy"
    manifest_digest = runtime_manifest.load_manifest(manifest_path)["manifest_digest"]
    env = os.environ.copy()
    env.pop("AGY_WRITER_MODEL", None)
    env.pop("AGY_REVIEWER_MODEL", None)
    env.update(
        {
            "AGY_GEMINI_CREDENTIAL_POOL_FILE": str(pool_file),
            "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE": str(state_file),
            "AGY_GEMINI_CLI_PATH": str(cli_path),
            "AGY_GEMINI_NEW_ONLY": "0",
            "AGY_GEMINI_RATE_LIMIT_COOLDOWN_SECONDS": "600",
            "PANTHEON_CONTENT_PUBLISHER_ROOT": str(publisher_root),
            "AGY_GEMINI_QUEUE_ROOT": str(queue_root),
            "PANTHEON_RUNTIME_MANIFEST_FILE": str(manifest_path),
            "PANTHEON_EXPECTED_RUNTIME_MANIFEST_DIGEST": manifest_digest,
            "PANTHEON_PYTHON_PATH": sys.executable,
            "PATH": f"{fake_bin}:/usr/bin:/bin",
            "TMPDIR": str(tmp_path),
        }
    )
    env.update(model_overrides)

    completed = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    if model_overrides:
        assert completed.returncode != 0
        assert "model route 不符合鎖定契約" in completed.stderr
        assert not fake_home.exists()
        return
    assert completed.returncode == 0, completed.stderr
    coordinator_plist = plistlib.loads(
        (
            fake_home
            / "Library"
            / "LaunchAgents"
            / ".pantheon-four-lane-stage"
            / "com.pantheon.agy-gemini-coordinator.plist"
        ).read_bytes()
    )
    coordinator_arguments = coordinator_plist["ProgramArguments"]
    coordinator_variables = coordinator_plist["EnvironmentVariables"]
    assert coordinator_arguments[coordinator_arguments.index("--new-matrix-run-root") + 1] == str(gsc_copy_root)
    assert coordinator_arguments[coordinator_arguments.index("--legacy-state-root") + 1] == str(publisher_root)
    assert coordinator_arguments[coordinator_arguments.index("--legacy-run-root") + 1] == str(gsc_copy_root)
    shared_contract = {
        "AGY_GEMINI_CREDENTIAL_POOL_FILE": str(pool_file),
        "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE": str(state_file),
        "AGY_GEMINI_DAILY_PROVIDER_ADMISSION_CAP": "102",
        "AGY_GEMINI_RATE_LIMIT_COOLDOWN_SECONDS": "600",
    }
    assert coordinator_variables["AGY_GEMINI_NEW_ONLY"] == "0"
    assert {
        key: coordinator_variables[key]
        for key in shared_contract
    } == shared_contract
    assert coordinator_variables["AGY_WRITER_MODEL"] == pipeline.DEFAULT_WRITER_MODEL
    assert coordinator_variables["AGY_REVIEWER_MODEL"] == pipeline.DEFAULT_REVIEWER_MODEL
    assert coordinator_variables["AGY_GEMINI_MODEL_ROUTE_CONFIG"] == str(
        fake_home
        / "Library/LaunchAgents/.pantheon-model-routes"
        / f"model-route-config-{pipeline.MODEL_ROUTE_CONFIG_DIGEST}.json"
    )
    assert coordinator_variables["AGY_GEMINI_MODEL_ROUTE_CONFIG_DIGEST"] == (
        pipeline.MODEL_ROUTE_CONFIG_DIGEST
    )
    assert Path(coordinator_variables["AGY_GEMINI_MODEL_ROUTE_CONFIG"]).parent != (
        fake_home / "Library/LaunchAgents/.pantheon-four-lane-stage"
    )
    for lane in ("new", "rewrite", "i18n-new", "i18n-rewrite"):
        installed = plistlib.loads(
            (
                fake_home
                / "Library"
                / "LaunchAgents"
                / ".pantheon-four-lane-stage"
                / f"com.pantheon.agy-gemini-{lane}.plist"
            ).read_bytes()
        )
        variables = installed["EnvironmentVariables"]
        arguments = installed["ProgramArguments"]
        assert arguments[arguments.index("--lane") + 1] == lane
        assert {key: variables[key] for key in shared_contract} == shared_contract
        assert variables["AGY_GEMINI_NEW_ONLY"] == "0"
        assert variables["AGY_WRITER_MODEL"] == pipeline.DEFAULT_WRITER_MODEL
        assert variables["AGY_REVIEWER_MODEL"] == pipeline.DEFAULT_REVIEWER_MODEL
        assert variables["AGY_GEMINI_MODEL_ROUTE_CONFIG"] == str(
            fake_home
            / "Library/LaunchAgents/.pantheon-model-routes"
            / f"model-route-config-{pipeline.MODEL_ROUTE_CONFIG_DIGEST}.json"
        )
        assert variables["AGY_GEMINI_MODEL_ROUTE_CONFIG_DIGEST"] == (
            pipeline.MODEL_ROUTE_CONFIG_DIGEST
        )

    for key, value in coordinator_variables.items():
        monkeypatch.setenv(key, str(value))
    monkeypatch.delenv("PANTHEON_FORMAL_RUNTIME")
    monkeypatch.setattr(coordinator.publisher, "legacy_article_ids", lambda _root: set())
    queue_root = tmp_path / "canary-off-queue"
    run_dir = tmp_path / "canary-off-run"
    _write_brief(run_dir, "canary-off-root-run")
    register_run(run_dir, queue_root)
    observed: list[tuple[Path, dict[str, str]]] = []

    def pending_tick(_run_dir: Path, _queue_root: Path) -> dict[str, object]:
        raise ExternalJobPending("canary-off-root-job")

    def observe_root_runner(root: Path) -> dict[str, str]:
        observed.append(
            (
                root,
                {key: os.environ[key] for key in shared_contract},
            )
        )
        return {"status": "idle"}

    summary = cycle_once(
        queue_root,
        tick=pending_tick,
        process=observe_root_runner,
        repo_root=tmp_path,
        lane_mode=True,
        new_only=False,
    )

    assert summary["runner"] == {"status": "idle"}
    assert observed == [(queue_root.resolve(), shared_contract)]


def test_installer_rejects_actor_local_gsc_copy_override_before_side_effects(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool_file, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool_file,
        state=tmp_path / "state.json",
    )
    env["PANTHEON_GSC_COPY_ROOT"] = str(repo_root / ".work" / "gsc-copy")

    completed = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "GSC copy run root 必須由 runtime queue 擁有" in completed.stderr
    assert not fake_home.exists()
    assert not mutation_log.exists()


def test_activation_preflight_uses_api_route_gate_without_running_agy_cli(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, _fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    agy_marker = tmp_path / "agy-was-executed"
    agy_path = Path(env["AGY_GEMINI_CLI_PATH"])
    agy_path.write_text(
        f"#!/bin/sh\nprintf '%s\n' executed > '{agy_marker}'\nexit 88\n",
        encoding="utf-8",
    )
    agy_path.chmod(0o700)

    staged = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--install",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert staged.returncode == 0, staged.stderr
    mutation_log.unlink(missing_ok=True)

    activated = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--activate-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert '"transport": "api"' in activated.stdout
    assert 'gemini-3.5-flash-lite' in activated.stdout
    assert 'gemini-3.1-flash-lite' in activated.stdout
    assert "CLI capability" not in activated.stderr
    assert not agy_marker.exists()


@pytest.mark.parametrize("drift", ["bytes", "deleted", "symlink"])
def test_installer_rejects_staged_model_route_drift_before_live_mutation(
    tmp_path: Path,
    drift: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=tmp_path / "state.json",
    )
    installed = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--install",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert installed.returncode == 0, installed.stderr
    stage = fake_home / "Library/LaunchAgents/.pantheon-four-lane-stage"
    staged_config = Path(
        (stage / "model-route-path").read_text(encoding="utf-8").strip()
    )
    assert staged_config.name == (
        f"model-route-config-{pipeline.MODEL_ROUTE_CONFIG_DIGEST}.json"
    )
    assert staged_config.read_bytes() == pipeline.MODEL_ROUTE_CONFIG_PATH.read_bytes()
    assert (stage / "model-route-digest").read_text(encoding="utf-8").strip() == (
        pipeline.MODEL_ROUTE_CONFIG_DIGEST
    )
    if drift == "bytes":
        staged_config.write_text("{}\n", encoding="utf-8")
    elif drift == "deleted":
        staged_config.unlink()
    else:
        staged_config.unlink()
        staged_config.symlink_to(pipeline.MODEL_ROUTE_CONFIG_PATH)

    activated = subprocess.run(
        [
            "/bin/bash",
            str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh"),
            "--activate-only",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert activated.returncode != 0
    assert "model route stage identity" in activated.stderr
    assert not mutation_log.exists()


def test_hardened_installer_uses_canonical_python_for_coordinator_and_lanes(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    state = tmp_path / "round-robin-state.json"
    python_target = Path(sys.executable).resolve(strict=True)
    python_link = tmp_path / "python-link"
    python_link.symlink_to(python_target)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=state,
        python_executable=python_target,
        python_path=python_link,
    )

    completed = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert not mutation_log.exists()
    stage = fake_home / "Library/LaunchAgents/.pantheon-four-lane-stage"
    staged_labels = [
        "com.pantheon.agy-gemini-coordinator",
        "com.pantheon.agy-gemini-new",
        "com.pantheon.agy-gemini-rewrite",
        "com.pantheon.agy-gemini-i18n-new",
        "com.pantheon.agy-gemini-i18n-rewrite",
    ]
    for label in staged_labels:
        payload = plistlib.loads((stage / f"{label}.plist").read_bytes())
        arguments = payload["ProgramArguments"]
        variables = payload["EnvironmentVariables"]
        assert arguments[0] == str(python_target)
        assert arguments[17] == str(python_target)
        assert variables["PANTHEON_RUNTIME_PYTHON_EXECUTABLE"] == str(python_target)


def test_hardened_installer_rejects_python_drift_before_stage_or_control_mutation(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    state = tmp_path / "round-robin-state.json"
    drift_python = tmp_path / "python-drift"
    drift_python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    drift_python.chmod(0o755)
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=state,
        python_executable=drift_python,
        python_path=Path(sys.executable),
    )

    completed = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert not fake_home.exists()
    assert not mutation_log.exists()


def test_installer_pool_opt_out_preserves_compatibility_without_pool_requirements(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pool, _manifest_sha256 = _write_installer_pool(tmp_path)
    state = tmp_path / "round-robin-state.json"
    env, fake_home, mutation_log = _installer_test_env(
        tmp_path,
        pool=pool,
        state=state,
    )
    env.pop("AGY_GEMINI_CREDENTIAL_POOL_FILE")
    env.pop("AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE")

    completed = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts/install_agy_gemini_coordinator_launchd.sh")],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert not mutation_log.exists()
    installed_paths = [
        fake_home / "Library/LaunchAgents/.pantheon-four-lane-stage/com.pantheon.agy-gemini-coordinator.plist",
        *[
            fake_home / f"Library/LaunchAgents/.pantheon-four-lane-stage/com.pantheon.agy-gemini-{lane}.plist"
            for lane in ("new", "rewrite", "i18n-new", "i18n-rewrite")
        ],
    ]
    assert len(installed_paths) == 5
    for path in installed_paths:
        variables = plistlib.loads(path.read_bytes())["EnvironmentVariables"]
        assert "AGY_GEMINI_CREDENTIAL_POOL_FILE" not in variables
        assert "AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE" not in variables
        assert variables["AGY_GEMINI_RATE_LIMIT_COOLDOWN_SECONDS"] == "300"
