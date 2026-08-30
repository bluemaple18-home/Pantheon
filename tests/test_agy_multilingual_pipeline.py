from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import threading
from collections import Counter
from pathlib import Path

import pytest

from scripts import agy_multilingual_pipeline as multilingual
from scripts.agy_gemini_outbox import ExternalJobPending, OutboxGeminiClient
from scripts.agy_seo_copy_pipeline import article_sha256, build_approval


def source_article() -> dict[str, object]:
    return {
        "article_id": "TEST-001",
        "canonical_path": "/articles/tarot/tarot-0001",
        "title": "塔羅牌是什麼？",
        "description": "塔羅牌可協助整理問題，但不能替你預測必然結果。",
        "answer": "先看問題與情境，再閱讀牌義。",
        "tags": ["塔羅", "自我探索"],
        "faq": [
            {"question": "塔羅可以預測未來嗎？", "answer": "不能保證結果，只能提供觀察角度。"},
        ],
        "bodySections": [
            {
                "heading": "先釐清問題",
                "paragraphs": [
                    "閱讀塔羅牌前，先把問題、時間與可觀察事實分開。",
                    "單張牌不能取代完整情境，也不能替任何人做重大決定。",
                ],
            }
        ],
    }


def translation_brief(locale: str = "en") -> dict[str, object]:
    source = source_article()
    return {
        "schema_version": 1,
        "run_id": f"translate-test-{locale}",
        "mode": "translate_existing",
        "articles": [
            {
                "translation_id": f"TEST-001:{locale}",
                "locale": locale,
                "source_article_id": "TEST-001",
                "source_path": source["canonical_path"],
                "source_sha256": multilingual.source_sha256(source),
                "source": source,
            }
        ],
    }


def legacy_rewrite_translation_brief(locale: str = "en") -> dict[str, object]:
    brief = translation_brief(locale)
    brief["run_id"] = f"legacy-rewrite-translation-{locale}"
    brief["lane"] = "i18n-rewrite"
    return brief


def _translation_state_path(queue_root: Path, run_id: str) -> Path:
    return queue_root / "runs" / f"{hashlib.sha256(run_id.encode('utf-8')).hexdigest()[:24]}.json"


def _write_registered_translation_state(
    queue_root: Path,
    run_dir: Path,
    brief: dict[str, object],
    *,
    lane: str = "i18n-rewrite",
) -> None:
    run_id = str(brief["run_id"])
    articles = brief["articles"]
    source_article_id = "TEST-001"
    if isinstance(articles, list) and articles and isinstance(articles[0], dict):
        source_article_id = str(articles[0].get("source_article_id") or source_article_id)
    multilingual.pipeline.write_json(
        _translation_state_path(queue_root, run_id),
        {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(run_dir.resolve()),
            "status": "active",
            "lane": lane,
            "identity_envelope": multilingual.translation_identity_envelope(
                source_article_id,
                lane,
            ),
            "registered_at": "2026-08-30T00:00:00+00:00",
            "updated_at": "2026-08-30T00:00:00+00:00",
        },
    )


def _registered_legacy_rewrite_run(
    tmp_path: Path,
    locale: str = "en",
    *,
    lane: str = "i18n-rewrite",
    brief: dict[str, object] | None = None,
) -> tuple[Path, Path, dict[str, object]]:
    queue_root = tmp_path / f"queue-{locale}"
    legacy_brief = brief or legacy_rewrite_translation_brief(locale)
    run_dir = queue_root / "translation-runs" / str(legacy_brief["run_id"])
    multilingual.pipeline.write_json(run_dir / "brief.json", legacy_brief)
    _write_registered_translation_state(
        queue_root,
        run_dir,
        legacy_brief,
        lane=lane,
    )
    return queue_root, run_dir, legacy_brief


def _outbox_client(queue_root: Path, namespace: str = "legacy-brief-test") -> OutboxGeminiClient:
    return OutboxGeminiClient(
        queue_root,
        namespace=namespace,
        writer_model="writer-test",
        reviewer_model="reviewer-test",
    )


def translation_candidate(locale: str = "en") -> dict[str, object]:
    localized = {
        "en": {
            "title": "What Are Tarot Cards?",
            "description": "Tarot cards can help you organize a question and notice patterns, but they cannot guarantee a future outcome or replace a personal decision.",
            "answer": "Start with the question and context before interpreting a card.",
            "tags": ["Tarot", "Self-reflection"],
            "faq": [
                {
                    "question": "Can tarot predict the future?",
                    "answer": "No. It offers perspectives but cannot guarantee an outcome.",
                }
            ],
            "bodySections": [
                {
                    "heading": "Clarify the question first",
                    "paragraphs": [
                        "Before reading tarot cards, separate the question, time frame, and observable facts.",
                        "A single card cannot replace the full context or make an important decision for you.",
                    ],
                }
            ],
        },
        "ja": {
            "title": "タロットカードとは？",
            "description": "タロットは質問や状況を整理するための手がかりですが、未来の結果を保証したり、本人に代わって判断したりするものではありません。",
            "answer": "カードの意味より先に、質問と状況を整理しましょう。",
            "tags": ["タロット", "自己理解"],
            "faq": [
                {
                    "question": "タロットで未来を予測できますか？",
                    "answer": "結果を保証するものではなく、考える視点を提供します。",
                }
            ],
            "bodySections": [
                {
                    "heading": "最初に質問を整理する",
                    "paragraphs": [
                        "タロットを読む前に、質問、期間、確認できる事実を分けて整理します。",
                        "一枚のカードだけで状況全体を判断したり、重要な決定を代行したりすることはできません。",
                    ],
                }
            ],
        },
        "ko": {
            "title": "타로 카드는 무엇인가요?",
            "description": "타로 카드는 질문과 상황을 정리하는 데 도움을 줄 수 있지만 미래의 결과를 보장하거나 개인의 결정을 대신할 수는 없습니다.",
            "answer": "카드 뜻보다 먼저 질문과 상황을 정리하세요.",
            "tags": ["타로", "자기 이해"],
            "faq": [
                {
                    "question": "타로로 미래를 예측할 수 있나요?",
                    "answer": "결과를 보장하지 않으며 생각할 관점을 제공할 뿐입니다.",
                }
            ],
            "bodySections": [
                {
                    "heading": "먼저 질문을 분명히 하기",
                    "paragraphs": [
                        "타로를 읽기 전에 질문과 기간, 확인할 수 있는 사실을 나누어 정리하세요.",
                        "한 장의 카드가 전체 상황을 대신하거나 중요한 결정을 내려 줄 수는 없습니다.",
                    ],
                }
            ],
        },
    }[locale]
    localized["bodySections"].append(
        {
            "heading": {
                "en": "Use the reading as a prompt, not a verdict",
                "ja": "答えではなく、考える手がかりとして使う",
                "ko": "정답이 아니라 생각을 정리하는 도구로 사용합니다",
            }[locale],
            "paragraphs": [
                {
                    "en": "Use the reading to identify a question that you can verify or act on.",
                    "ja": "リーディングの後は、確認できる問いや実行できる一歩に戻りましょう。",
                    "ko": "리딩 후에는 확인할 수 있는 질문이나 실행 가능한 다음 단계로 돌아갑니다.",
                }[locale]
            ],
        }
    )
    localized["bodySections"].extend(
        [
            {
                "heading": {
                    "en": "Read the card in context",
                    "ja": "質問と状況を合わせて読む",
                    "ko": "질문과 상황을 함께 살핍니다",
                }[locale],
                "paragraphs": [
                    {
                        "en": "The same card can point to different concerns in a relationship or career reading.",
                        "ja": "同じカードでも、恋愛と仕事では注目する点が変わります。",
                        "ko": "같은 카드라도 연애와 직업 질문에서는 살펴볼 지점이 달라집니다.",
                    }[locale]
                ],
            },
            {
                "heading": {
                    "en": "Keep the limits clear",
                    "ja": "カードで決められないこと",
                    "ko": "카드가 결정할 수 없는 것",
                }[locale],
                "paragraphs": [
                    {
                        "en": "Tarot cannot guarantee an outcome or replace professional advice.",
                        "ja": "タロットは結果を保証せず、専門家の判断にも代わりません。",
                        "ko": "타로는 결과를 보장하거나 전문가의 판단을 대신하지 않습니다.",
                    }[locale]
                ],
            },
        ]
    )
    brief = translation_brief(locale)
    source = brief["articles"][0]
    return {
        "schema_version": 1,
        "run_id": brief["run_id"],
        "mode": "translate_existing",
        "articles": [
            {
                "article_id": source["translation_id"],
                "locale": locale,
                "source_article_id": source["source_article_id"],
                "source_path": source["source_path"],
                "source_sha256": source["source_sha256"],
                **localized,
            }
        ],
    }


def write_stage_json(path: Path, payload: object) -> None:
    multilingual.pipeline.write_json(path, payload)


def approved_stage_fixture(
    tmp_path: Path, *, replacement_shape: bool = False
) -> dict[str, object]:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    run_id = "stage-ja"
    run_dir = tmp_path / "runtime" / "translation-runs" / run_id
    queue_state_path = tmp_path / "runtime" / "queue" / "runs" / "stage-ja.json"
    publisher_ledger_path = tmp_path / "runtime" / "state" / "ledger.json"
    approved_root = tmp_path / "approved"
    brief = translation_brief("ja")
    brief["run_id"] = run_id
    candidate = translation_candidate("ja")
    candidate["run_id"] = run_id
    article = candidate["articles"][0]
    approved_review = {
        "schema_version": 1,
        "run_id": run_id,
        "articles": [
            {
                "article_id": article["article_id"],
                "candidate_sha256": article_sha256(article),
                "verdict": "APPROVE",
                "findings": [],
            }
        ],
    }
    root_review = {
        "schema_version": 1,
        "run_id": run_id,
        "articles": [
            {
                "article_id": article["article_id"],
                "candidate_sha256": article_sha256(article),
                "verdict": "REJECT",
                "hard_failure": True,
                "findings": [{"code": "AI_TEMPLATE_STYLE", "message": "退件"}],
            }
        ],
    }
    continuation = {
        "schema_version": 1,
        "operation_id": "stage-test-operation",
        "run_id": run_id,
        "source_sha256": [brief["articles"][0]["source_sha256"]],
        "starting_review_sha256": "1" * 64,
        "terminal_candidate_sha256": multilingual._json_sha256(candidate),
        "terminal_review_sha256": multilingual._json_sha256(root_review),
        "started_after_generation": 3,
        "semantic_budget": 2,
        "next_generation": 7,
        "completed_generations": [5, 6],
        "abandoned_generations": [4],
        "status": "complete",
    }
    queue_state = {
        "schema_version": 1,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "status": "complete",
        "result": {"candidate": str(run_dir / "candidate.json")},
    }
    ledger = {
        "schema_version": 1,
        "published_runs": [],
        "quarantined_runs": [],
        "rewrite_released_runs": [],
        "superseded_runs": [],
        "translation_published_runs": [],
        "translation_deferred_runs": [],
    }
    formal_result = {
        "schema_version": 1,
        "exit_verdict": "APPROVE_READY_FOR_STAGING",
        "findings": [],
        "review": approved_review,
    }
    continuation_path = run_dir / "continuation" / "state.json"
    generation_candidate_path = run_dir / "generations" / "06" / "candidate.json"
    generation_review_path = run_dir / "generations" / "06" / "review.json"
    for path, payload in (
        (run_dir / "brief.json", brief),
        (run_dir / "candidate.json", candidate),
        (run_dir / "review.json", root_review),
        (continuation_path, continuation),
        (generation_candidate_path, candidate),
        (generation_review_path, root_review),
        (queue_state_path, queue_state),
        (publisher_ledger_path, ledger),
        (approved_root / "candidate.json", candidate),
        (approved_root / "review.json", approved_review),
        (approved_root / "formal-review-result.json", formal_result),
        (
            approved_root / "formal-request-identity.json",
            {
                "schema_version": 1,
                "run_id": run_id,
                "lane": "i18n-new",
                "role": "reviewer",
                "job_id": "a" * 40,
                "request_sha256": "a" * 64,
            },
        ),
    ):
        if replacement_shape and path in {
            continuation_path, generation_candidate_path, generation_review_path
        }:
            continue
        write_stage_json(path, payload)
    kwargs = {
        "repo_root": repo_root,
        "run_dir": run_dir,
        "approved_candidate_path": approved_root / "candidate.json",
        "approved_review_path": approved_root / "review.json",
        "formal_review_result_path": approved_root / "formal-review-result.json",
        "queue_state_path": queue_state_path,
        "publisher_ledger_path": publisher_ledger_path,
        "expected_run_id": run_id,
        "terminal_owner_kind": "continuation_generation",
        "terminal_generation": 6,
        "expected_approved_article_sha256": article_sha256(article),
        "expected_root_candidate_sha256": hashlib.sha256((run_dir / "candidate.json").read_bytes()).hexdigest(),
        "expected_root_review_sha256": hashlib.sha256((run_dir / "review.json").read_bytes()).hexdigest(),
        "expected_continuation_state_sha256": (
            None if replacement_shape else hashlib.sha256(
                (run_dir / "continuation" / "state.json").read_bytes()
            ).hexdigest()
        ),
        "expected_queue_state_sha256": hashlib.sha256(queue_state_path.read_bytes()).hexdigest(),
        "expected_publisher_ledger_sha256": hashlib.sha256(publisher_ledger_path.read_bytes()).hexdigest(),
        "expected_approved_candidate_sha256": hashlib.sha256((approved_root / "candidate.json").read_bytes()).hexdigest(),
        "expected_approved_review_sha256": hashlib.sha256((approved_root / "review.json").read_bytes()).hexdigest(),
        "expected_formal_review_result_sha256": hashlib.sha256((approved_root / "formal-review-result.json").read_bytes()).hexdigest(),
        "expected_source_sha256": brief["articles"][0]["source_sha256"],
    }
    return {
        "repo_root": repo_root,
        "run_dir": run_dir,
        "queue_state_path": queue_state_path,
        "publisher_ledger_path": publisher_ledger_path,
        "candidate": candidate,
        "root_review": root_review,
        "approved_review": approved_review,
        "kwargs": kwargs,
    }


def replacement_approved_stage_fixture(tmp_path: Path) -> dict[str, object]:
    fixture = approved_stage_fixture(tmp_path, replacement_shape=True)
    old_run_dir = fixture["run_dir"]
    run_id = "stage-en-replacement-01"
    run_dir = old_run_dir.parent / run_id
    old_run_dir.rename(run_dir)
    queue_state_path = fixture["queue_state_path"]

    brief = translation_brief("en")
    candidate = translation_candidate("en")
    brief["run_id"] = run_id
    candidate["run_id"] = run_id
    root_review = json.loads((run_dir / "review.json").read_text(encoding="utf-8"))
    approved_review = json.loads(
        fixture["kwargs"]["approved_review_path"].read_text(encoding="utf-8")
    )
    for payload in (brief, candidate, root_review, approved_review):
        payload["run_id"] = run_id
    root_review["articles"][0].pop("hard_failure", None)
    root_review["articles"][0]["article_id"] = candidate["articles"][0]["article_id"]
    approved_review["articles"][0]["article_id"] = candidate["articles"][0]["article_id"]
    root_review["articles"][0]["candidate_sha256"] = article_sha256(candidate["articles"][0])
    approved_review["articles"][0]["candidate_sha256"] = article_sha256(candidate["articles"][0])
    queue_state = {
        "schema_version": 1,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "status": "complete",
        "replacement_of": "stage-en",
        "replacement_reason": "approved locale replacement",
        "result": {"candidate": str(run_dir / "candidate.json")},
    }
    formal_result = {
        "schema_version": 1,
        "exit_verdict": "APPROVE_READY_FOR_STAGING",
        "findings": [],
        "review": approved_review,
    }
    approved_root = fixture["kwargs"]["approved_candidate_path"].parent
    (run_dir / "continuation").mkdir()
    for attempt in range(1, 4):
        write_stage_json(run_dir / "attempts" / f"{attempt:02d}" / "candidate.json", candidate)
        write_stage_json(run_dir / "attempts" / f"{attempt:02d}" / "review.json", root_review)
    for path, payload in (
        (run_dir / "brief.json", brief),
        (run_dir / "candidate.json", candidate),
        (run_dir / "review.json", root_review),
        (queue_state_path, queue_state),
        (approved_root / "candidate.json", candidate),
        (approved_root / "review.json", approved_review),
        (approved_root / "formal-review-result.json", formal_result),
        (
            approved_root / "formal-request-identity.json",
            {
                "schema_version": 1,
                "run_id": run_id,
                "lane": "i18n-rewrite",
                "role": "reviewer",
                "job_id": "b" * 40,
                "request_sha256": "b" * 64,
            },
        ),
    ):
        write_stage_json(path, payload)
    kwargs = {
        **fixture["kwargs"],
        "run_dir": run_dir,
        "expected_run_id": run_id,
        "terminal_owner_kind": "replacement_attempt",
        "terminal_attempt": 3,
        "replacement_of": queue_state["replacement_of"],
        "replacement_reason": queue_state["replacement_reason"],
        "expected_replacement_state_sha256": hashlib.sha256(queue_state_path.read_bytes()).hexdigest(),
        "expected_approved_article_sha256": article_sha256(candidate["articles"][0]),
        "expected_root_candidate_sha256": hashlib.sha256((run_dir / "candidate.json").read_bytes()).hexdigest(),
        "expected_root_review_sha256": hashlib.sha256((run_dir / "review.json").read_bytes()).hexdigest(),
        "expected_queue_state_sha256": hashlib.sha256(queue_state_path.read_bytes()).hexdigest(),
        "expected_approved_candidate_sha256": hashlib.sha256((approved_root / "candidate.json").read_bytes()).hexdigest(),
        "expected_approved_review_sha256": hashlib.sha256((approved_root / "review.json").read_bytes()).hexdigest(),
        "expected_formal_review_result_sha256": hashlib.sha256((approved_root / "formal-review-result.json").read_bytes()).hexdigest(),
    }
    kwargs.pop("terminal_generation")
    kwargs.pop("expected_continuation_state_sha256")
    static = fixture["repo_root"] / "app/web/static"
    static.mkdir(parents=True)
    module_path = static / "article-locale-stage-en.js"
    manifest_path = static / "article-locales.js"
    article = candidate["articles"][0]
    old_record = {
        "runId": "stage-en",
        "articleId": article["source_article_id"],
        "locale": article["locale"],
        "sourcePath": article["source_path"],
        "sourceSha256": "0" * 64,
        **{field: f"old-{field}" if field not in {"tags", "faq", "bodySections"} else []
           for field in sorted(multilingual.TRANSLATABLE_FIELDS)},
    }
    sibling = {**old_record, "runId": "stage-ja", "locale": "ja", "sourceSha256": "1" * 64}
    records = [old_record, sibling]
    prefix = "// AGY 核准多語文章；由 scripts/agy_multilingual_pipeline.py 產生。\n\n"
    export = "STAGE_EN_ARTICLE_LOCALES"
    module_path.write_text(
        prefix + f"export const {export} = {json.dumps(records, ensure_ascii=False, indent=2)};\n",
        encoding="utf-8",
    )
    manifest_path.write_text(
        f'import {{ {export} }} from "./{module_path.name}";\n'
        f"export const ARTICLE_LOCALE_REGISTRY = [...{export}];\n"
        "export function listArticleLocaleRecords() { return ARTICLE_LOCALE_REGISTRY; }\n",
        encoding="utf-8",
    )
    (fixture["repo_root"] / "package.json").write_text('{"type":"module"}\n', encoding="utf-8")
    sealed_article = json.loads((approved_root / "candidate.json").read_text(encoding="utf-8"))["articles"][0]
    replacement_record = {
        "runId": run_id,
        "articleId": sealed_article["source_article_id"],
        "locale": sealed_article["locale"],
        "sourcePath": sealed_article["source_path"],
        "sourceSha256": sealed_article["source_sha256"],
        **{field: sealed_article[field] for field in sorted(multilingual.TRANSLATABLE_FIELDS)},
    }
    after_records = [replacement_record, sibling]
    after_bytes = (
        prefix + f"export const {export} = {json.dumps(after_records, ensure_ascii=False, indent=2)};\n"
    ).encode()
    public_replacement = {
        "contract": "approved-locale-existing-record-replacement",
        "source_article_id": article["source_article_id"],
        "locale": article["locale"],
        "old_run_id": old_record["runId"],
        "old_source_sha256": old_record["sourceSha256"],
        "old_record_sha256": hashlib.sha256(multilingual.compact_json_bytes(old_record)).hexdigest(),
        "module_path": module_path.relative_to(fixture["repo_root"]).as_posix(),
        "module_export": export,
        "record_index": 0,
        "module_before_sha256": hashlib.sha256(module_path.read_bytes()).hexdigest(),
        "module_after_sha256": hashlib.sha256(after_bytes).hexdigest(),
        "manifest_path": manifest_path.relative_to(fixture["repo_root"]).as_posix(),
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "replacement_run_id": run_id,
        "replacement_source_sha256": article["source_sha256"],
        "approved_article_sha256": article_sha256(article),
        "replacement_record_sha256": hashlib.sha256(multilingual.compact_json_bytes(replacement_record)).hexdigest(),
    }
    kwargs["public_replacement"] = public_replacement
    return {**fixture, "run_dir": run_dir, "candidate": candidate, "root_review": root_review,
            "approved_review": approved_review, "kwargs": kwargs,
            "public_replacement": public_replacement, "module_path": module_path,
            "manifest_path": manifest_path, "old_record": old_record, "sibling": sibling}


def protected_stage_snapshot(fixture: dict[str, object]) -> dict[str, object]:
    run_dir = fixture["run_dir"]
    topology = {}
    for path in sorted(run_dir.rglob("*")):
        path_stat = path.lstat()
        entry = {
            "mode": path_stat.st_mode, "size": path_stat.st_size,
            "type": ("symlink" if path.is_symlink() else "directory" if path.is_dir()
                     else "file" if path.is_file() else "other"),
        }
        if path.is_symlink():
            entry["target"] = path.readlink().as_posix()
        elif path.is_file():
            entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        topology[path.relative_to(run_dir).as_posix()] = entry
    snapshot = {"run_topology": topology}
    for label, key in (("queue", "queue_state_path"), ("ledger", "publisher_ledger_path"),
                       ("module", "module_path"), ("manifest", "manifest_path")):
        if key in fixture:
            path = fixture[key]
            snapshot[label] = hashlib.sha256(path.read_bytes()).hexdigest()
    return snapshot


def test_replacement_approved_stage_uses_closed_attempt_owner(tmp_path: Path) -> None:
    fixture = replacement_approved_stage_fixture(tmp_path)

    plan = multilingual.plan_approved_edited_candidate_stage(**fixture["kwargs"])
    receipt = multilingual.apply_approved_edited_candidate_stage(
        **fixture["kwargs"], expected_plan_digest=plan["plan_digest"]
    )
    loaded = multilingual.load_approved_edited_candidate_stage(fixture["run_dir"])

    assert receipt["terminal_owner"]["kind"] == "replacement_attempt"
    assert receipt["terminal_owner"]["terminal_attempt"] == 3
    assert loaded["seal"]["terminal_owner"] == receipt["terminal_owner"]
    assert (fixture["run_dir"] / "continuation").is_dir()
    assert list((fixture["run_dir"] / "continuation").iterdir()) == []
    assert not (fixture["run_dir"] / "generations").exists()
    assert receipt["provider_calls"] == 0


def test_replacement_approved_stage_plan_accepts_empty_continuation_residue_read_only(
    tmp_path: Path,
) -> None:
    fixture = replacement_approved_stage_fixture(tmp_path)
    run_dir = fixture["run_dir"]
    before = protected_stage_snapshot(fixture)
    first = multilingual.plan_approved_edited_candidate_stage(**fixture["kwargs"])
    second = multilingual.plan_approved_edited_candidate_stage(**fixture["kwargs"])

    assert first == second
    assert first["provider_calls"] == 0
    assert protected_stage_snapshot(fixture) == before
    assert (run_dir / "continuation").is_dir()
    assert list((run_dir / "continuation").iterdir()) == []
    assert not (run_dir / "generations").exists()
    assert not (run_dir / "editorial-staging").exists()


def test_replacement_approved_stage_still_accepts_missing_continuation(tmp_path: Path) -> None:
    fixture = replacement_approved_stage_fixture(tmp_path)
    (fixture["run_dir"] / "continuation").rmdir()

    plan = multilingual.plan_approved_edited_candidate_stage(**fixture["kwargs"])

    assert plan["terminal_owner"]["kind"] == "replacement_attempt"
    assert plan["provider_calls"] == 0
    assert not (fixture["run_dir"] / "editorial-staging").exists()


@pytest.mark.parametrize(
    "damage", ["symlink", "file", "state", "hidden", "nested", "generations"]
)
def test_replacement_approved_stage_rejects_nonempty_or_unsafe_continuation_residue(
    tmp_path: Path, damage: str
) -> None:
    fixture = replacement_approved_stage_fixture(tmp_path)
    run_dir = fixture["run_dir"]
    continuation = run_dir / "continuation"
    if damage == "symlink":
        continuation.rmdir()
        outside = tmp_path / "outside-continuation"
        outside.mkdir()
        continuation.symlink_to(outside, target_is_directory=True)
    elif damage == "file":
        continuation.rmdir()
        continuation.write_text("not a directory", encoding="utf-8")
    elif damage == "state":
        write_stage_json(continuation / "state.json", {"schema_version": 1})
    elif damage == "hidden":
        (continuation / ".residue").write_text("stale", encoding="utf-8")
    elif damage == "nested":
        (continuation / "nested").mkdir()
    else:
        (run_dir / "generations").mkdir()
    before = protected_stage_snapshot(fixture)

    with pytest.raises((OSError, ValueError)):
        multilingual.plan_approved_edited_candidate_stage(**fixture["kwargs"])

    assert protected_stage_snapshot(fixture) == before
    assert not (run_dir / "editorial-staging").exists()


def test_replacement_approved_stage_rejects_continuation_enumeration_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = replacement_approved_stage_fixture(tmp_path)
    run_dir = fixture["run_dir"]
    continuation = run_dir / "continuation"
    before = protected_stage_snapshot(fixture)
    original_iterdir = Path.iterdir

    def fail_continuation_iterdir(path: Path):
        if path == continuation:
            raise OSError("synthetic enumeration failure")
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", fail_continuation_iterdir)
    with pytest.raises(ValueError, match="cannot be inspected"):
        multilingual.plan_approved_edited_candidate_stage(**fixture["kwargs"])

    assert protected_stage_snapshot(fixture) == before
    assert not (run_dir / "editorial-staging").exists()


def replacement_stage_cli_command(fixture: dict[str, object], descriptor_path: Path | None) -> list[str]:
    kwargs = fixture["kwargs"]
    command = [sys.executable, "-m", "scripts.agy_multilingual_pipeline", "--repo-root", str(fixture["repo_root"]),
               "stage-approved-edited-candidate"]
    if descriptor_path is not None:
        command.extend(["--public-replacement", str(descriptor_path)])
    options = {
        "run-dir": kwargs["run_dir"], "approved-candidate": kwargs["approved_candidate_path"],
        "approved-review": kwargs["approved_review_path"], "formal-review-result": kwargs["formal_review_result_path"],
        "queue-state": kwargs["queue_state_path"], "publisher-ledger": kwargs["publisher_ledger_path"],
        **{name.replace("_", "-"): value for name, value in kwargs.items() if value is not None
           and (name.startswith("expected_") or name in {"terminal_owner_kind", "terminal_attempt", "replacement_of", "replacement_reason"})},
    }
    for name, value in options.items():
        command.extend([f"--{name}", str(value)])
    return command


def test_replacement_approved_stage_cli_loads_exact_descriptor_for_plan_and_execute(tmp_path: Path) -> None:
    fixture = replacement_approved_stage_fixture(tmp_path)
    descriptor_path = tmp_path / "public-replacement.json"
    descriptor_path.write_text(json.dumps(fixture["public_replacement"]), encoding="utf-8")
    command = replacement_stage_cli_command(fixture, descriptor_path)
    cwd = Path(multilingual.__file__).parent.parent
    plan = json.loads(subprocess.run(command, cwd=cwd, check=True, text=True, capture_output=True).stdout)
    executed = json.loads(subprocess.run(
        [*command, "--execute", "--expected-plan-digest", plan["plan_digest"]],
        cwd=cwd, check=True, text=True, capture_output=True,
    ).stdout)

    assert executed["status"] == "STAGED"
    assert executed["public_replacement"] == fixture["public_replacement"]


@pytest.mark.parametrize("mutation", ["missing", "unknown_key", "wrong_run", "wrong_source", "wrong_article"])
def test_replacement_approved_stage_cli_rejects_descriptor_drift_before_writes(tmp_path: Path, mutation: str) -> None:
    fixture = replacement_approved_stage_fixture(tmp_path)
    descriptor_path = tmp_path / "public-replacement.json"
    descriptor = dict(fixture["public_replacement"])
    if mutation == "unknown_key": descriptor["unexpected"] = True
    elif mutation == "wrong_run": descriptor["replacement_run_id"] = "other-run"
    elif mutation == "wrong_source": descriptor["replacement_source_sha256"] = "f" * 64
    elif mutation == "wrong_article": descriptor["source_article_id"] = "OTHER-001"
    if mutation != "missing": descriptor_path.write_text(json.dumps(descriptor), encoding="utf-8")
    before = {path.relative_to(fixture["run_dir"]): path.read_bytes() for path in fixture["run_dir"].rglob("*") if path.is_file()}

    result = subprocess.run(replacement_stage_cli_command(fixture, None if mutation == "missing" else descriptor_path),
                            cwd=Path(multilingual.__file__).parent.parent, text=True, capture_output=True)

    assert result.returncode != 0
    assert {path.relative_to(fixture["run_dir"]): path.read_bytes() for path in fixture["run_dir"].rglob("*") if path.is_file()} == before


def test_replacement_apply_updates_exact_existing_record_in_place(tmp_path: Path) -> None:
    fixture = replacement_approved_stage_fixture(tmp_path)
    plan = multilingual.plan_approved_edited_candidate_stage(**fixture["kwargs"])
    multilingual.apply_approved_edited_candidate_stage(
        **fixture["kwargs"], expected_plan_digest=plan["plan_digest"]
    )
    loaded = multilingual.load_approved_edited_candidate_stage(fixture["run_dir"])
    before_manifest = fixture["manifest_path"].read_bytes()
    approval = build_approval(
        loaded["candidate"]["run_id"], loaded["candidate"]["articles"],
        loaded["review"],
        {loaded["candidate"]["articles"][0]["article_id"]: "APPROVE"}, "publisher",
    )

    changed = multilingual.apply_approved_translations(
        fixture["repo_root"], fixture["candidate"]["run_id"],
        json.loads((fixture["run_dir"] / "brief.json").read_text(encoding="utf-8")),
        loaded["candidate"], loaded["review"], approval,
        public_replacement=loaded["seal"]["public_replacement"],
        source_loader=lambda _repo, _article_id: translation_brief("en")["articles"][0]["source"],
    )

    assert changed == [fixture["module_path"]]
    assert fixture["manifest_path"].read_bytes() == before_manifest
    assert hashlib.sha256(fixture["module_path"].read_bytes()).hexdigest() == fixture["public_replacement"]["module_after_sha256"]
    assert fixture["sibling"] in json.loads(
        fixture["module_path"].read_text(encoding="utf-8").split(" = ", 1)[1][:-2]
    )


def test_replacement_stage_rejects_wrong_old_record_before_writes(tmp_path: Path) -> None:
    fixture = replacement_approved_stage_fixture(tmp_path)
    fixture["kwargs"]["public_replacement"] = {
        **fixture["public_replacement"], "old_record_sha256": "f" * 64
    }
    before = fixture["module_path"].read_bytes()

    with pytest.raises((TypeError, ValueError)):
        multilingual.plan_approved_edited_candidate_stage(**fixture["kwargs"])

    assert fixture["module_path"].read_bytes() == before
    assert not (fixture["run_dir"] / "editorial-staging").exists()


@pytest.mark.parametrize("damage", ["attempt04", "mixed_generations", "root_review_drift"])
def test_replacement_approved_stage_rejects_attempt_authority_drift(
    tmp_path: Path, damage: str
) -> None:
    fixture = replacement_approved_stage_fixture(tmp_path)
    run_dir = fixture["run_dir"]
    if damage == "attempt04":
        write_stage_json(run_dir / "attempts" / "04" / "candidate.json", fixture["candidate"])
    elif damage == "mixed_generations":
        write_stage_json(run_dir / "generations" / "03" / "candidate.json", fixture["candidate"])
    else:
        changed = {**fixture["root_review"], "run_id": "drift"}
        write_stage_json(run_dir / "review.json", changed)

    before = protected_stage_snapshot(fixture)
    with pytest.raises((TypeError, ValueError)):
        multilingual.plan_approved_edited_candidate_stage(**fixture["kwargs"])
    assert protected_stage_snapshot(fixture) == before
    assert not (run_dir / "editorial-staging").exists()


def test_approved_edited_stage_plan_is_read_only(tmp_path: Path) -> None:
    fixture = approved_stage_fixture(tmp_path)
    run_dir = fixture["run_dir"]

    plan = multilingual.plan_approved_edited_candidate_stage(**fixture["kwargs"])

    assert plan["status"] == "READY_TO_EXECUTE"
    assert re.fullmatch(r"[0-9a-f]{64}", plan["plan_digest"])
    assert plan["provider_calls"] == 0
    assert not (run_dir / "editorial-staging").exists()
    assert not (run_dir / "generations" / "07").exists()


@pytest.mark.parametrize("damage", ["next_generation", "hard_failure", "replacement_fields"])
def test_approved_edited_stage_rejects_continuation_terminal_drift(
    tmp_path: Path, damage: str
) -> None:
    fixture = approved_stage_fixture(tmp_path)
    run_dir = fixture["run_dir"]
    kwargs = fixture["kwargs"]
    if damage == "next_generation":
        (run_dir / "generations" / "07").mkdir()
    elif damage == "hard_failure":
        review = json.loads((run_dir / "review.json").read_text(encoding="utf-8"))
        review["articles"][0]["hard_failure"] = False
        write_stage_json(run_dir / "review.json", review)
        write_stage_json(run_dir / "generations" / "06" / "review.json", review)
        kwargs["expected_root_review_sha256"] = hashlib.sha256((run_dir / "review.json").read_bytes()).hexdigest()
        state_path = run_dir / "continuation" / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["terminal_review_sha256"] = multilingual._json_sha256(review)
        write_stage_json(state_path, state)
        kwargs["expected_continuation_state_sha256"] = hashlib.sha256(state_path.read_bytes()).hexdigest()
    else:
        kwargs["terminal_attempt"] = 3
    before = protected_stage_snapshot(fixture)
    with pytest.raises(ValueError, match={"next_generation": "terminal continuation state differs", "hard_failure": "terminal generation audit differs", "replacement_fields": "fields are mixed"}[damage]):
        multilingual.plan_approved_edited_candidate_stage(**kwargs)
    assert protected_stage_snapshot(fixture) == before
    assert not (run_dir / "editorial-staging").exists()


def test_replacement_approved_stage_rejects_continuation_fields(tmp_path: Path) -> None:
    fixture = replacement_approved_stage_fixture(tmp_path)
    fixture["kwargs"]["terminal_generation"] = 3
    before = protected_stage_snapshot(fixture)
    with pytest.raises(ValueError, match="fields are mixed"):
        multilingual.plan_approved_edited_candidate_stage(**fixture["kwargs"])
    assert protected_stage_snapshot(fixture) == before
    assert not (fixture["run_dir"] / "editorial-staging").exists()


def test_approved_edited_stage_execute_is_idempotent_and_rollback_scoped(tmp_path: Path) -> None:
    fixture = approved_stage_fixture(tmp_path)
    kwargs = fixture["kwargs"]
    run_dir = fixture["run_dir"]
    root_candidate_before = (run_dir / "candidate.json").read_bytes()
    root_review_before = (run_dir / "review.json").read_bytes()
    continuation_before = (run_dir / "continuation" / "state.json").read_bytes()
    plan = multilingual.plan_approved_edited_candidate_stage(**kwargs)

    receipt = multilingual.apply_approved_edited_candidate_stage(
        **kwargs,
        expected_plan_digest=plan["plan_digest"],
    )
    loaded = multilingual.load_approved_edited_candidate_stage(run_dir)
    again = multilingual.apply_approved_edited_candidate_stage(
        **kwargs,
        expected_plan_digest=plan["plan_digest"],
    )

    assert receipt["status"] == "STAGED"
    assert loaded["candidate"] == fixture["candidate"]
    assert loaded["receipt_sha256"] == hashlib.sha256(
        Path(receipt["receipt_path"]).read_bytes()
    ).hexdigest()
    assert again["status"] == "ALREADY_STAGED"
    assert (run_dir / "candidate.json").read_bytes() == root_candidate_before
    assert (run_dir / "review.json").read_bytes() == root_review_before
    assert (run_dir / "continuation" / "state.json").read_bytes() == continuation_before
    assert not (run_dir / "generations" / "07").exists()

    rollback = multilingual.rollback_approved_edited_candidate_stage(
        run_dir,
        receipt["operation_id"],
    )

    assert rollback["status"] == "ROLLED_BACK"
    assert not (run_dir / "editorial-staging" / "current.json").exists()
    assert not Path(receipt["operation_dir"]).exists()
    assert (run_dir / "candidate.json").read_bytes() == root_candidate_before
    assert (run_dir / "review.json").read_bytes() == root_review_before


@pytest.mark.parametrize(
    ("label", "mutate"),
    [
        ("approved candidate", lambda fixture: write_stage_json(fixture["kwargs"]["approved_candidate_path"], {**fixture["candidate"], "run_id": "other"})),
        ("approved review", lambda fixture: write_stage_json(fixture["kwargs"]["approved_review_path"], {**fixture["approved_review"], "run_id": "other"})),
        ("formal result", lambda fixture: write_stage_json(fixture["kwargs"]["formal_review_result_path"], {"schema_version": 1, "exit_verdict": "REJECT", "findings": [], "review": fixture["approved_review"]})),
        ("root candidate", lambda fixture: write_stage_json(fixture["run_dir"] / "candidate.json", {**fixture["candidate"], "run_id": "other"})),
        ("root review", lambda fixture: write_stage_json(fixture["run_dir"] / "review.json", {**fixture["root_review"], "run_id": "other"})),
        ("continuation", lambda fixture: write_stage_json(fixture["run_dir"] / "continuation" / "state.json", {"schema_version": 1})),
        ("queue", lambda fixture: write_stage_json(fixture["queue_state_path"], {"schema_version": 1, "run_id": "other"})),
        ("ledger", lambda fixture: write_stage_json(fixture["publisher_ledger_path"], {"schema_version": 1, "translation_published_runs": [{"run_id": "stage-ja"}], "translation_deferred_runs": []})),
    ],
)
def test_approved_edited_stage_rejects_identity_drift(
    tmp_path: Path,
    label: str,
    mutate: object,
) -> None:
    fixture = approved_stage_fixture(tmp_path)
    mutate(fixture)

    with pytest.raises(ValueError):
        multilingual.plan_approved_edited_candidate_stage(**fixture["kwargs"])


def test_approved_edited_stage_rejects_plan_digest_drift_without_writes(tmp_path: Path) -> None:
    fixture = approved_stage_fixture(tmp_path)
    run_dir = fixture["run_dir"]

    with pytest.raises(ValueError, match="plan digest"):
        multilingual.apply_approved_edited_candidate_stage(
            **fixture["kwargs"],
            expected_plan_digest="f" * 64,
        )

    assert not (run_dir / "editorial-staging").exists()


def test_approved_edited_stage_rejects_conflicting_second_payload(tmp_path: Path) -> None:
    fixture = approved_stage_fixture(tmp_path)
    plan = multilingual.plan_approved_edited_candidate_stage(**fixture["kwargs"])
    multilingual.apply_approved_edited_candidate_stage(
        **fixture["kwargs"],
        expected_plan_digest=plan["plan_digest"],
    )
    changed = json.loads(json.dumps(fixture["candidate"], ensure_ascii=False))
    changed["articles"][0]["title"] += " 追記"
    write_stage_json(fixture["kwargs"]["approved_candidate_path"], changed)
    fixture["kwargs"]["expected_approved_article_sha256"] = article_sha256(changed["articles"][0])
    fixture["kwargs"]["expected_approved_candidate_sha256"] = hashlib.sha256(
        fixture["kwargs"]["approved_candidate_path"].read_bytes()
    ).hexdigest()
    changed_review = {
        **fixture["approved_review"],
        "articles": [
            {
                **fixture["approved_review"]["articles"][0],
                "candidate_sha256": article_sha256(changed["articles"][0]),
            }
        ],
    }
    write_stage_json(fixture["kwargs"]["approved_review_path"], changed_review)
    write_stage_json(
        fixture["kwargs"]["formal_review_result_path"],
        {
            "schema_version": 1,
            "exit_verdict": "APPROVE_READY_FOR_STAGING",
            "findings": [],
            "review": changed_review,
        },
    )
    fixture["kwargs"]["expected_approved_review_sha256"] = hashlib.sha256(
        fixture["kwargs"]["approved_review_path"].read_bytes()
    ).hexdigest()
    fixture["kwargs"]["expected_formal_review_result_sha256"] = hashlib.sha256(
        fixture["kwargs"]["formal_review_result_path"].read_bytes()
    ).hexdigest()

    with pytest.raises(ValueError, match="conflicts"):
        multilingual.plan_approved_edited_candidate_stage(**fixture["kwargs"])


def test_approved_edited_stage_rejects_tampered_payload(tmp_path: Path) -> None:
    fixture = approved_stage_fixture(tmp_path)
    plan = multilingual.plan_approved_edited_candidate_stage(**fixture["kwargs"])
    receipt = multilingual.apply_approved_edited_candidate_stage(
        **fixture["kwargs"],
        expected_plan_digest=plan["plan_digest"],
    )
    payload_path = Path(receipt["payload_path"])
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    payload["candidate"]["run_id"] = "tampered"
    write_stage_json(payload_path, payload)

    with pytest.raises(ValueError, match="record digest"):
        multilingual.load_approved_edited_candidate_stage(fixture["run_dir"])


@pytest.mark.parametrize("mutation", ["missing_run_id", "wrong_lane", "request_job_mismatch"])
def test_approved_edited_stage_rejects_formal_job_identity_tamper(
    tmp_path: Path,
    mutation: str,
) -> None:
    fixture = approved_stage_fixture(tmp_path)
    identity_path = fixture["kwargs"]["formal_review_result_path"].parent / "formal-request-identity.json"
    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    if mutation == "missing_run_id":
        identity.pop("run_id")
    elif mutation == "wrong_lane":
        identity["lane"] = "create"
    else:
        identity["request_sha256"] = "b" * 64
    write_stage_json(identity_path, identity)

    with pytest.raises(ValueError, match="formal review identity"):
        multilingual.plan_approved_edited_candidate_stage(**fixture["kwargs"])


def test_approved_edited_stage_recovers_verified_operation_before_current(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = approved_stage_fixture(tmp_path)
    plan = multilingual.plan_approved_edited_candidate_stage(**fixture["kwargs"])
    original_write = multilingual._atomic_write_json

    def crash_before_current(path: Path, payload: object) -> None:
        if path.name == "current.json":
            raise RuntimeError("synthetic crash before current")
        original_write(path, payload)

    monkeypatch.setattr(multilingual, "_atomic_write_json", crash_before_current)
    with pytest.raises(RuntimeError, match="before current"):
        multilingual.apply_approved_edited_candidate_stage(
            **fixture["kwargs"], expected_plan_digest=plan["plan_digest"]
        )
    monkeypatch.setattr(multilingual, "_atomic_write_json", original_write)

    recovered = multilingual.apply_approved_edited_candidate_stage(
        **fixture["kwargs"], expected_plan_digest=plan["plan_digest"]
    )

    assert recovered["recovered_current_pointer"] is True
    assert multilingual.load_approved_edited_candidate_stage(fixture["run_dir"])["candidate"] == fixture["candidate"]


@pytest.mark.parametrize("target", ["current", "payload"])
def test_approved_edited_stage_rejects_symlinked_authority_path(
    tmp_path: Path,
    target: str,
) -> None:
    fixture = approved_stage_fixture(tmp_path)
    plan = multilingual.plan_approved_edited_candidate_stage(**fixture["kwargs"])
    receipt = multilingual.apply_approved_edited_candidate_stage(
        **fixture["kwargs"], expected_plan_digest=plan["plan_digest"]
    )
    path = Path(receipt["current_seal_path"] if target == "current" else receipt["payload_path"])
    outside = tmp_path / f"outside-{target}.json"
    path.rename(outside)
    path.symlink_to(outside)

    with pytest.raises(ValueError, match="symlink"):
        multilingual.load_approved_edited_candidate_stage(fixture["run_dir"])


def test_approved_edited_stage_rollback_rejects_symlinked_operation_dir(tmp_path: Path) -> None:
    fixture = approved_stage_fixture(tmp_path)
    plan = multilingual.plan_approved_edited_candidate_stage(**fixture["kwargs"])
    receipt = multilingual.apply_approved_edited_candidate_stage(
        **fixture["kwargs"], expected_plan_digest=plan["plan_digest"]
    )
    operation_dir = Path(receipt["operation_dir"])
    outside = tmp_path / "outside-operation"
    operation_dir.rename(outside)
    operation_dir.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        multilingual.rollback_approved_edited_candidate_stage(
            fixture["run_dir"], receipt["operation_id"]
        )
    assert outside.is_dir()


def load_ja_boundary_fixture(name: str) -> dict[str, object]:
    path = (
        Path(__file__).parent
        / "fixtures"
        / "agy_multilingual_pipeline"
        / "ja_boundary_contract"
        / name
    )
    return json.loads(path.read_text(encoding="utf-8"))


def load_ja_plan_authority_fixture(name: str) -> dict[str, object]:
    path = (
        Path(__file__).parent
        / "fixtures"
        / "agy_multilingual_pipeline"
        / "ja_plan_authority"
        / name
    )
    return json.loads(path.read_text(encoding="utf-8"))


def without_provider_safety_boundary(payload: dict[str, object]) -> dict[str, object]:
    fresh = json.loads(json.dumps(payload, ensure_ascii=False))
    for article in fresh.get("articles", []):
        for mapping in article.get("coverage_mapping", []):
            mapping.pop("safety_boundary", None)
    return fresh


def fresh_ja_plan_authority_fixture(name: str) -> dict[str, object]:
    return without_provider_safety_boundary(load_ja_plan_authority_fixture(name))


def legacy_provider_safety_receipt(
    brief: dict[str, object],
    prior: dict[str, object] | None,
    source_ref_maps: dict[str, dict[str, str]],
    *,
    schema_sha256: str | None = None,
) -> dict[str, object]:
    digest = schema_sha256 or next(
        iter(
            multilingual._legacy_provider_safety_schema_sha256s(
                brief,
                prior,
                source_ref_maps,
            )
        )
    )
    return {
        "role": "writer",
        "model": "writer-test",
        "status": "success",
        "schema_sha256": digest,
        "prompt_sha256": "a" * 64,
    }


def write_legacy_provider_safety_receipt(
    generation_dir: Path,
    brief: dict[str, object],
    prior: dict[str, object] | None,
    source_ref_maps: dict[str, dict[str, str]],
    *,
    schema_sha256: str | None = None,
) -> None:
    multilingual.pipeline.write_json(
        generation_dir / "plan-operation.json",
        legacy_provider_safety_receipt(
            brief,
            prior,
            source_ref_maps,
            schema_sha256=schema_sha256,
        ),
    )


def ja_plan_authority_fixture_sha256(name: str) -> str:
    path = (
        Path(__file__).parent
        / "fixtures"
        / "agy_multilingual_pipeline"
        / "ja_plan_authority"
        / name
    )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_fact_coverage_stats(
    brief: dict[str, object],
    external: dict[str, object],
) -> dict[str, object]:
    facts = multilingual._source_fact_package(brief)["articles"][0]["facts"]
    expected = [str(fact["fact_id"]) for fact in facts]
    returned = [
        str(mapping["source_fact_id"])
        for mapping in external["articles"][0]["coverage_mapping"]
    ]
    counts = Counter(returned)
    stale = [fact_id for fact_id in returned if fact_id not in expected]
    missing = [fact_id for fact_id in expected if fact_id not in counts]
    duplicates = [fact_id for fact_id, count in counts.items() if count > 1]
    return {
        "current_facts": len(expected),
        "returned_coverage_items": len(returned),
        "stale_legacy_ids": len(stale),
        "missing_current_ids": len(missing),
        "duplicates": len(duplicates),
        "coverage": (
            "PASS"
            if not stale and not missing and not duplicates
            and len(returned) == len(expected)
            else "FAIL"
        ),
        "stale_ids": stale,
        "missing_ids": missing,
    }


def non_tarot_translation_brief(locale: str = "ko") -> dict[str, object]:
    source = {
        "article_id": "FORTUNE-0039",
        "canonical_path": "/articles/bazi/fortune-0039",
        "title": "八字用神是什麼？",
        "description": "用神是依命局失衡處選出的調整方向，不是固定五行，也不能只看單一字。",
        "answer": "先看整體強弱、寒燥與流通，再判斷哪個五行能改善失衡。",
        "tags": ["八字", "用神"],
        "faq": [
            {
                "question": "用神會永遠不變嗎？",
                "answer": "不能脫離完整命局與運勢條件，只用單一規則固定判斷。",
            }
        ],
        "bodySections": [
            {
                "heading": "先找出命局的失衡",
                "paragraphs": ["用神判斷先看日主強弱、寒燥與五行是否能流通。"],
            },
            {
                "heading": "再選擇能改善失衡的方向",
                "paragraphs": ["同一個五行在不同命局中可能有不同作用，不能套用固定答案。"],
            },
        ],
    }
    return {
        "schema_version": 1,
        "run_id": f"auto-i18n-{locale}-fortune-0039",
        "mode": "translate_existing",
        "articles": [
            {
                "translation_id": f"FORTUNE-0039:{locale}",
                "locale": locale,
                "source_article_id": "FORTUNE-0039",
                "source_path": source["canonical_path"],
                "source_sha256": multilingual.source_sha256(source),
                "source": source,
            }
        ],
    }


def non_tarot_external_candidate(
    outline: list[str] | None = None,
) -> dict[str, object]:
    payload = {
        "articles": [
            {
                "slot": "article-01",
                "title": "사주에서 용신은 어떻게 찾나요?",
                "description": "용신은 명식 전체의 불균형을 살핀 뒤 조정 방향을 찾는 개념이며, 한 글자나 고정된 오행만으로 정할 수 없습니다.",
                "answer": "강약과 한난조습, 오행의 흐름을 함께 살핀 뒤 불균형을 줄이는 방향을 찾습니다.",
                "tags": ["사주", "용신"],
                "faq": [
                    {
                        "question": "용신은 항상 같나요?",
                        "answer": "전체 명식과 운의 조건을 벗어나 하나의 규칙으로 고정할 수 없습니다.",
                    }
                ],
                "bodySections": [
                    {
                        "heading": "용신이 답하려는 질문",
                        "paragraphs": ["용신은 명식에서 무엇이 과하거나 부족한지 살피는 출발점입니다."],
                    },
                    {
                        "heading": "강약과 계절을 함께 보는 이유",
                        "paragraphs": ["일간의 강약과 계절의 한난조습을 따로 떼어 판단하지 않습니다."],
                    },
                    {
                        "heading": "오행의 흐름으로 조정 방향 찾기",
                        "paragraphs": ["막힌 흐름을 이어 주거나 지나친 기운을 덜어 내는 방향을 비교합니다."],
                    },
                    {
                        "heading": "고정 공식으로 단정하지 않기",
                        "paragraphs": ["같은 오행도 명식과 운의 조건에 따라 역할이 달라질 수 있습니다."],
                    },
                ],
            }
        ]
    }
    if outline is not None:
        for section, heading in zip(
            payload["articles"][0]["bodySections"],
            outline,
        ):
            section["heading"] = heading
    return payload


def external_locale_plan(
    brief: dict[str, object],
    *,
    rebuild_outline: bool = False,
    outline: list[str] | None = None,
    coverage_shift: int = 0,
) -> dict[str, object]:
    fact_package = multilingual._source_fact_package(brief)
    target = fact_package["articles"][0]
    locale = str(brief["articles"][0]["locale"])
    localized = {
        "en": {
            "intent": "Understand how to identify the useful element and its limits",
            "queries": ["how to find the useful element", "useful element criteria"],
            "angle": "Explain the decision order and its limits without a fixed formula",
            "outline": [
                "What the useful element answers",
                "Check strength and season together",
                "Compare the flow of elements",
                "Avoid a fixed conclusion",
            ],
            "coverage_note": "Explain this fact and its limits in the selected section",
        },
        "ja": {
            "intent": "命式で用神を判断する基準と限界を知りたい",
            "queries": ["用神の見つけ方", "用神を判断する基準"],
            "angle": "固定した公式にせず判断の順序と限界を説明する",
            "outline": [
                "用神で答えられる疑問",
                "強弱と季節を一緒に確認する理由",
                "五行の流れから調整方向を探す",
                "固定した結論を避ける",
            ],
            "coverage_note": "この事実と制限を該当する節で説明する",
        },
        "ko": {
            "intent": "사주에서 용신을 판단하는 기준과 한계를 알고 싶다",
            "queries": ["사주 용신 찾는 법", "용신 판단 기준"],
            "angle": "고정 공식을 제시하지 않고 판단 순서와 한계를 설명한다",
            "outline": [
                "용신이 답하려는 질문",
                "강약과 계절을 함께 보는 이유",
                "오행의 흐름으로 조정 방향 찾기",
                "고정 공식으로 단정하지 않기",
            ],
            "coverage_note": "이 사실과 제한을 해당 절에서 설명한다",
        },
    }[locale]
    headings = outline or localized["outline"]
    return {
        "articles": [
            {
                "slot": "article-01",
                "locale": locale,
                "source_sha256": brief["articles"][0]["source_sha256"],
                "native_search_intent": localized["intent"],
                "native_query_phrasings": localized["queries"],
                "article_angle": localized["angle"],
                "ordered_h2_outline": headings,
                "coverage_mapping": [
                    {
                        "source_fact_id": fact["fact_id"],
                        "planned_h2_slot": (
                            f"h2-{((index + coverage_shift) % len(headings)) + 1}"
                        ),
                        "coverage_note": localized["coverage_note"],
                    }
                    for index, fact in enumerate(target["facts"])
                ],
                "source_structure_not_copied": [
                    section["heading"]
                    for section in brief["articles"][0]["source"]["bodySections"]
                ],
                "rebuild_outline": rebuild_outline,
            }
        ]
    }


def external_locale_plan_with_source_refs(
    brief: dict[str, object],
    *,
    rebuild_outline: bool = False,
    outline: list[str] | None = None,
    coverage_shift: int = 0,
) -> dict[str, object]:
    external = external_locale_plan(
        brief,
        rebuild_outline=rebuild_outline,
        outline=outline,
        coverage_shift=coverage_shift,
    )
    refs = multilingual._request_local_source_ref_maps(
        brief,
        {"articles": [{"slot": "article-01"}]},
    )["article-01"]
    fact_to_ref = {fact_id: ref for ref, fact_id in refs.items()}
    item = external["articles"][0]
    item.pop("source_sha256")
    for mapping in item["coverage_mapping"]:
        mapping["source_ref"] = fact_to_ref[str(mapping.pop("source_fact_id"))]
    return external


@pytest.mark.parametrize("locale", ["en", "ja", "ko"])
def test_translation_contract_accepts_supported_locales(locale: str) -> None:
    brief = translation_brief(locale)
    candidate = translation_candidate(locale)

    multilingual.validate_translation_brief(brief)
    multilingual.validate_translation_candidate(brief, candidate)

    assert multilingual.translation_findings(brief, candidate["articles"]) == []


def test_translation_contract_rejects_source_hash_drift() -> None:
    brief = translation_brief()
    candidate = translation_candidate()
    candidate["articles"][0]["source_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="source hash"):
        multilingual.validate_translation_candidate(brief, candidate)


def test_translation_apply_gate_uses_translation_mode_without_bypassing_approval() -> None:
    candidate = translation_candidate()
    article = candidate["articles"][0]
    review = {
        "schema_version": 1,
        "run_id": candidate["run_id"],
        "articles": [
            {
                "article_id": article["article_id"],
                "candidate_sha256": article_sha256(article),
                "verdict": "APPROVE",
                "hard_failure": False,
                "findings": [],
            }
        ],
    }
    approval = build_approval(
        str(candidate["run_id"]),
        candidate["articles"],
        review,
        {str(article["article_id"]): "APPROVE"},
        "test",
    )

    approved = multilingual.pipeline.validate_apply_gate(
        candidate["articles"],
        review,
        approval,
        candidate_mode=str(candidate["mode"]),
    )

    assert approved == candidate["articles"]


def test_translation_gate_rejects_wrong_language() -> None:
    brief = translation_brief("ko")
    candidate = translation_candidate("ko")
    candidate["articles"][0]["title"] = "This is not Korean"

    findings = multilingual.translation_findings(brief, candidate["articles"])

    assert any(item["code"] == "target_language" for item in findings)


@pytest.mark.parametrize("tag", ["人際", "戀愛心理"])
def test_translation_gate_rejects_traditional_chinese_in_each_japanese_tag(
    tag: str,
) -> None:
    brief = translation_brief("ja")
    candidate = translation_candidate("ja")
    candidate["articles"][0]["tags"] = ["タロット", tag]

    findings = multilingual.translation_findings(brief, candidate["articles"])

    assert {
        "article_id": "TEST-001:ja",
        "code": "target_language_tags",
        "message": "日文 metadata tags 含繁中殘留或沿用來源語言",
    } in findings


def test_translation_gate_accepts_shared_source_authority_tag_in_japanese() -> None:
    brief = translation_brief("ja")
    source = brief["articles"][0]["source"]
    source["tags"].append("MBTI")
    brief["articles"][0]["source_sha256"] = multilingual.source_sha256(source)
    candidate = translation_candidate("ja")
    candidate["articles"][0]["source_sha256"] = brief["articles"][0]["source_sha256"]
    candidate["articles"][0]["tags"].append("MBTI")

    findings = multilingual.translation_findings(brief, candidate["articles"])

    assert not any(item["code"] == "target_language_tags" for item in findings)


def test_translation_gate_rejects_source_structure_mirroring() -> None:
    brief = translation_brief("en")
    candidate = translation_candidate("en")
    candidate["articles"][0]["bodySections"] = [
        {
            "heading": "Clarify the question first",
            "paragraphs": [
                "Start by separating the question, time frame, and facts.",
                "A single card cannot replace the full context or make a decision for you.",
            ],
        }
    ]

    findings = multilingual.translation_findings(brief, candidate["articles"])

    assert any(item["code"] == "structural_mirroring" for item in findings)


def test_translation_gate_rejects_too_few_localized_sections() -> None:
    brief = translation_brief("en")
    candidate = translation_candidate("en")
    candidate["articles"][0]["bodySections"] = candidate["articles"][0]["bodySections"][:3]

    findings = multilingual.translation_findings(brief, candidate["articles"])

    assert any(item["code"] == "localized_structure" for item in findings)


def test_ja_boundary_candidate_02_is_repeated_boilerplate_only() -> None:
    brief = load_ja_boundary_fixture("brief.json")
    candidate = load_ja_boundary_fixture("candidate_02.json")

    findings = multilingual.translation_findings(brief, candidate["articles"])

    assert [item["code"] for item in findings] == ["BOUNDARY_BOILERPLATE_REPEATED"]
    finding = findings[0]
    assert finding["repeated_locations"] == ["body"]
    assert "BOUNDARY_MEANING_MISSING" not in {item["code"] for item in findings}


def test_ja_boundary_candidate_03_is_missing_meaning_with_structured_trace() -> None:
    brief = load_ja_boundary_fixture("brief.json")
    candidate = load_ja_boundary_fixture("candidate_03.json")

    findings = multilingual.translation_findings(brief, candidate["articles"])

    finding = next(item for item in findings if item["code"] == "BOUNDARY_MEANING_MISSING")
    assert "meta_description" in finding["missing_fields"]
    assert set(finding["missing_categories"]) == {
        "contextual_or_general_interpretation",
        "professional_advice_non_substitution",
    }
    assert finding["present_categories"] == ["outcome_not_determined"]
    assert any(
        reason["reason"] == "omission" and reason["category"] in finding["missing_categories"]
        for reason in finding["reasons"]
    )


def test_ja_boundary_accepts_natural_future_result_not_confirmed_phrase() -> None:
    brief = load_ja_boundary_fixture("brief.json")
    candidate = load_ja_boundary_fixture("corrected_test_only_candidate.json")
    article = candidate["articles"][0]
    article["description"] = (
        "死神カードが示す金銭面の変化を、文化的な象徴解釈として整理します。"
        "未来の結果を完全に確定することはできず、投資や法律など専門的な助言に代わるものではありません。"
    )
    article["bodySections"][0]["paragraphs"][0] = (
        "死神カードは金銭面の変化を考えるための一般的な象徴解釈です。"
        "どのような予測ツールも未来の結果を完全に確定することはできないため、"
        "専門的な財務や法律の助言に代わるものではありません。"
    )

    findings = multilingual.translation_findings(brief, candidate["articles"])

    assert findings == []


def test_ja_boundary_natural_body_phrase_does_not_rescue_missing_meta_description() -> None:
    brief = load_ja_boundary_fixture("brief.json")
    candidate = load_ja_boundary_fixture("corrected_test_only_candidate.json")
    article = candidate["articles"][0]
    article["description"] = (
        "死神カードが示す金銭面の変化を、文化的な象徴解釈として整理します。"
        "投資や法律など専門的な助言に代わるものではありません。"
    )
    article["bodySections"][0]["paragraphs"][0] = (
        "死神カードは金銭面の変化を考えるための一般的な象徴解釈です。"
        "どのような予測ツールも未来の結果を完全に確定することはできないため、"
        "専門的な財務や法律の助言に代わるものではありません。"
    )

    findings = multilingual.translation_findings(brief, candidate["articles"])

    finding = next(item for item in findings if item["code"] == "BOUNDARY_MEANING_MISSING")
    assert finding["missing_fields"] == ["meta_description"]
    assert "outcome_not_determined" not in finding["present_categories"] or "meta_description" in finding["missing_fields"]


def test_ja_boundary_generic_uncertainty_does_not_count_as_outcome_not_determined() -> None:
    brief = load_ja_boundary_fixture("brief.json")
    candidate = load_ja_boundary_fixture("corrected_test_only_candidate.json")
    article = candidate["articles"][0]
    article["description"] = (
        "死神カードが示す金銭面の変化を、文化的な象徴解釈として整理します。"
        "状況には不確実性や可能性があり、投資や法律など専門的な助言に代わるものではありません。"
    )
    replacements = [
        (
            "死神カードは金銭面の変化を考えるための一般的な象徴解釈です。"
            "状況には不確実性や可能性があり、専門的な財務や法律の助言に代わるものではありません。"
        ),
        (
            "支出や収入の変化を文化的な読み物として整理します。"
            "先行きには曖昧さがあり、投資や法律に関する助言を構成するものではありません。"
        ),
        (
            "古い金銭習慣を見直す観点を一般的な理解として扱います。"
            "変化には幅があり、専門的な財務判断の代用にはなりません。"
        ),
        (
            "カードの象徴を文化的な内省として読みます。"
            "今後の展開には複数の可能性があり、専門家の助言に代わるものではありません。"
        ),
    ]
    for section, replacement in zip(article["bodySections"], replacements):
        section["paragraphs"] = [replacement]

    findings = multilingual.translation_findings(brief, candidate["articles"])

    finding = next(item for item in findings if item["code"] == "BOUNDARY_MEANING_MISSING")
    assert finding["missing_fields"] == ["meta_description", "body"]
    assert "outcome_not_determined" not in multilingual._ja_boundary_target_categories(
        multilingual._ja_field_text(article, "meta_description")
    )
    assert "outcome_not_determined" not in multilingual._ja_boundary_target_categories(
        multilingual._ja_field_text(article, "body")
    )


def test_ja_article_prompt_has_field_by_field_boundary_checklist() -> None:
    brief = load_ja_boundary_fixture("brief.json")
    plan = multilingual._hydrate_locale_plan(
        brief,
        external_locale_plan(brief),
        generation=1,
        rebuild_by_slot={"article-01": False},
    )

    prompt = multilingual._article_prompt(brief, plan, [])

    assert "JA field-by-field protected boundary checklist" in prompt
    assert "meta_description 與 body 必須各自包含" in prompt
    assert "outcome_not_determined" in prompt
    assert "未来の結果を完全に確定することはできない" in prompt
    assert "不得用 FAQ、answer、tags、另一個 required field" in prompt
    assert "不得把同一句 disclaimer 逐段重複成 boilerplate" in prompt


def test_ja_source_constraints_preserve_spans_and_merge_equivalent_duplicates() -> None:
    brief = load_ja_boundary_fixture("brief.json")
    package = multilingual._source_fact_package(brief)
    article = package["articles"][0]

    candidates = article["protected_source"]["boundary_candidate_dispositions"]
    constraints = article["protected_constraints"]

    assert candidates
    assert all(
        set(item) >= {"source_span_id", "disposition", "source_text", "source_digest", "field_path", "provenance"}
        for item in candidates
    )
    assert all(item["source_digest"] == hashlib.sha256(item["source_text"].encode("utf-8")).hexdigest() for item in candidates)
    assert all(item["provenance"] == "source" for item in candidates)
    assert all(item["disposition"] in {"PRESERVED", "MERGED_DUPLICATE", "NOT_A_BOUNDARY", "UNRESOLVED"} for item in candidates)
    assert not any(item["disposition"] == "UNRESOLVED" for item in candidates)

    general = [
        constraint
        for constraint in constraints
        if constraint["category"] == "contextual_or_general_interpretation"
        and constraint["equivalence_key"] == "內容只提供通用理解"
    ]
    assert len(general) == 1
    assert len(general[0]["source_span_ids"]) >= 8
    assert all(
        item["disposition"] == "MERGED_DUPLICATE"
        for item in candidates
        if item.get("constraint_ids") == [general[0]["constraint_id"]]
        and item["source_span_id"] != general[0]["source_span_ids"][0]
    )

    prompt = multilingual._plan_prompt(
        brief,
        generation=1,
        prior_plan=None,
        findings=[],
        rebuild_by_slot={"article-01": False},
    )
    source_package_text = prompt.split("source fact package:\n", 1)[1].split("\n", 1)[0]
    source_package = json.loads(source_package_text)
    fact_texts = [
        str(fact["text"])
        for article in source_package["articles"]
        for fact in article["facts"]
    ]
    assert "protected_constraints" in source_package_text
    assert "boundary_candidate_dispositions" in source_package_text
    assert not any(
        text.strip() == "內容只提供通用理解，不能替個人下結論"
        for text in fact_texts
    )


def test_ja_boundary_constraints_do_not_merge_different_claims_in_same_category() -> None:
    brief = translation_brief("ja")
    source = brief["articles"][0]["source"]
    source["description"] = (
        "內容只提供通用理解，不能替個人下結論。"
        "內容只提供通用理解，不能替個人下結論。"
        "不能保證結果。不能替你拿確定答案。"
    )
    brief["articles"][0]["source_sha256"] = multilingual.source_sha256(source)

    article = multilingual._source_fact_package(brief)["articles"][0]
    constraints = article["protected_constraints"]
    by_key = {
        (constraint["category"], constraint["equivalence_key"]): constraint
        for constraint in constraints
    }

    assert ("contextual_or_general_interpretation", "內容只提供通用理解") in by_key
    assert ("contextual_or_general_interpretation", "不能替個人下結論") in by_key
    assert by_key[
        ("contextual_or_general_interpretation", "內容只提供通用理解")
    ]["constraint_id"] != by_key[
        ("contextual_or_general_interpretation", "不能替個人下結論")
    ]["constraint_id"]
    assert len(by_key[("contextual_or_general_interpretation", "內容只提供通用理解")]["source_span_ids"]) == 2
    assert any(
        item["disposition"] == "MERGED_DUPLICATE"
        and item["source_text"] == "內容只提供通用理解"
        for item in article["protected_source"]["boundary_candidate_dispositions"]
    )
    assert ("outcome_not_determined", "不能保證結果") in by_key
    assert ("outcome_not_determined", "不能替你拿確定答案") in by_key
    assert by_key[
        ("outcome_not_determined", "不能保證結果")
    ]["constraint_id"] != by_key[
        ("outcome_not_determined", "不能替你拿確定答案")
    ]["constraint_id"]


def test_ja_source_span_id_uses_stable_clause_ordinal_not_classifier_hit_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = source_article()
    source["description"] = "不能保證結果。不能替個人下結論。"
    item = {
        "translation_id": "TEST-001:ja",
        "locale": "ja",
        "source_article_id": "TEST-001",
        "source_path": source["canonical_path"],
        "source_sha256": multilingual.source_sha256(source),
        "source": source,
    }

    original = multilingual._ja_protected_constraint_view(item)
    original_span_id = next(
        disposition["source_span_id"]
        for disposition in original["protected_source"]["boundary_candidate_dispositions"]
        if disposition["source_text"] == "不能替個人下結論"
    )

    monkeypatch.setattr(
        multilingual,
        "JA_BOUNDARY_SOURCE_HEURISTIC_RE",
        re.compile("不能替個人下結論"),
    )
    filtered = multilingual._ja_protected_constraint_view(item)
    filtered_span_id = next(
        disposition["source_span_id"]
        for disposition in filtered["protected_source"]["boundary_candidate_dispositions"]
        if disposition["source_text"] == "不能替個人下結論"
    )

    assert filtered_span_id == original_span_id


def test_ja_source_fact_projection_selects_clauses_without_broken_fragments() -> None:
    brief = load_ja_boundary_fixture("brief.json")

    facts = multilingual._source_fact_package(brief)["articles"][0]["facts"]
    fact_text = "\n".join(str(fact["text"]) for fact in facts)

    for fragment in ["，。", "，，", "。，。"]:
        assert fragment not in fact_text
    assert not any(
        sentence.strip().startswith(("旨在", "這點"))
        for sentence in re.split(r"[。！？!?]", fact_text)
    )
    assert "然而。" not in fact_text
    assert "塔羅死神在金錢中代表改變與結束舊模式" in fact_text
    assert "提醒我們檢視現狀" in fact_text
    assert "藉由符號的反思" in fact_text
    assert "我們在此探討的皆屬文化反思範疇，旨在豐富個人的心智層面與看待金錢的角度" in fact_text


def test_ja_plan_authority_red_fixture_reproduces_cross_version_id_drift() -> None:
    brief = load_ja_plan_authority_fixture("brief.json")
    prior = load_ja_plan_authority_fixture("attempt_03_locale_plan.json")
    external = load_ja_plan_authority_fixture("generation_04_external_plan.json")

    assert ja_plan_authority_fixture_sha256("brief.json") == (
        "93e09f8f637c396e35ccc28707c66734b08eb7f1c0c4cbdcb246df5b11ac8844"
    )
    assert ja_plan_authority_fixture_sha256("attempt_03_locale_plan.json") == (
        "c7c0eb857d3b87e3aa254aa1af07552205859a5f61e889ee42c4f56501771810"
    )
    assert ja_plan_authority_fixture_sha256("generation_04_external_plan.json") == (
        "063cceea4195133ab0382bf25586cb10b3240020b8a0546238830c460b943322"
    )
    assert source_fact_coverage_stats(brief, external) == {
        "current_facts": 22,
        "returned_coverage_items": 22,
        "stale_legacy_ids": 3,
        "missing_current_ids": 3,
        "duplicates": 0,
        "coverage": "FAIL",
        "stale_ids": [
            "fact-f969c002621b",
            "fact-9b6132bd3c5d",
            "fact-e9e00b456bd1",
        ],
        "missing_ids": [
            "fact-23f5088ba3c2",
            "fact-ed7ec3e401ba",
            "fact-f729514cc45f",
        ],
    }

    with pytest.raises(ValueError, match="article fields are strict|source ref coverage"):
        multilingual._hydrate_locale_plan(
            brief,
            external,
            generation=4,
            rebuild_by_slot={"article-01": True},
            prior_plan=prior,
        )


def test_ja_continuation_prompt_invalidates_legacy_ids_without_reusing_assignments() -> None:
    brief = load_ja_plan_authority_fixture("brief.json")
    prior = load_ja_plan_authority_fixture("attempt_03_locale_plan.json")
    prompt = multilingual._plan_prompt(
        brief,
        generation=4,
        prior_plan=prior,
        findings=[],
        rebuild_by_slot={"article-01": True},
    )
    legacy_authority = json.loads(
        prompt.split("legacy mapping authority:\n", 1)[1].split("\n", 1)[0]
    )
    source_package = json.loads(
        prompt.split("source fact package:\n", 1)[1].split("\n", 1)[0]
    )
    prior_prompt_view = json.loads(
        prompt.split("prior plan:\n", 1)[1].split("\n", 1)[0]
    )

    assert legacy_authority["article-01"]["legacy_mapping_status"] == "INVALIDATED"
    assert legacy_authority["article-01"]["legacy_id_counts"]["returned"] == 22
    assert legacy_authority["article-01"]["legacy_id_counts"]["stale"] > 0
    assert legacy_authority["article-01"]["legacy_id_counts"]["missing"] > 0
    assert legacy_authority["article-01"]["legacy_id_counts"]["duplicates"] == 0
    assert len(source_package["articles"][0]["facts"]) == 22
    assert [
        fact["source_ref"]
        for fact in source_package["articles"][0]["facts"]
    ] == [f"source_ref_{index + 1:02d}" for index in range(22)]
    assert "coverage_mapping" not in json.dumps(prior_prompt_view, ensure_ascii=False)
    assert "coverage_note" not in json.dumps(prior_prompt_view, ensure_ascii=False)
    for forbidden in [
        "fact-f969c002621b",
        "fact-9b6132bd3c5d",
        "fact-e9e00b456bd1",
        "source_fact_id",
        "constraint_id",
        "source_span_id",
        "source_sha256",
        "source_version_digest",
    ]:
        assert forbidden not in prompt


def test_ja_continuation_schema_uses_request_local_refs_not_fact_ids() -> None:
    brief = load_ja_plan_authority_fixture("brief.json")
    prior = load_ja_plan_authority_fixture("attempt_03_locale_plan.json")
    prompt = multilingual._plan_prompt(
        brief,
        generation=4,
        prior_plan=prior,
        findings=[],
        rebuild_by_slot={"article-01": True},
    )
    schema = multilingual._external_locale_plan_schema(brief, prior_plan=prior)
    item_schema = schema["properties"]["articles"]["items"]
    coverage = item_schema["properties"]["coverage_mapping"]

    assert "safety_boundary" not in prompt
    assert "source_sha256" not in item_schema["properties"]
    assert "source_sha256" not in item_schema["required"]
    assert "source_fact_id" not in coverage["items"]["properties"]
    assert "safety_boundary" not in coverage["items"]["properties"]
    assert "safety_boundary" not in coverage["items"]["required"]
    assert coverage["items"]["properties"]["source_ref"]["enum"] == [
        f"source_ref_{index + 1:02d}" for index in range(22)
    ]


def test_ja_continuation_current_ref_response_hydrates_to_current_ids() -> None:
    brief = load_ja_plan_authority_fixture("brief.json")
    prior = load_ja_plan_authority_fixture("attempt_03_locale_plan.json")
    external = fresh_ja_plan_authority_fixture("fixed_current_ref_external_plan.json")

    plan = multilingual._hydrate_locale_plan(
        brief,
        external,
        generation=4,
        rebuild_by_slot={"article-01": True},
        prior_plan=prior,
    )

    expected = [
        str(fact["fact_id"])
        for fact in multilingual._source_fact_package(brief)["articles"][0]["facts"]
    ]
    returned = [
        mapping["source_fact_id"]
        for mapping in plan["articles"][0]["coverage_mapping"]
    ]
    returned_safety = [
        mapping["safety_boundary"]
        for mapping in plan["articles"][0]["coverage_mapping"]
    ]
    assert returned == expected
    assert returned_safety == [
        fact["safety_boundary"]
        for fact in multilingual._source_fact_package(brief)["articles"][0]["facts"]
    ]
    assert "source_ref" not in json.dumps(plan, ensure_ascii=False)
    assert plan["articles"][0]["source_sha256"] == brief["articles"][0]["source_sha256"]


def test_ja_continuation_fresh_response_rejects_provider_safety() -> None:
    brief = load_ja_plan_authority_fixture("brief.json")
    prior = load_ja_plan_authority_fixture("attempt_03_locale_plan.json")
    external = load_ja_plan_authority_fixture("fixed_current_ref_external_plan.json")

    with pytest.raises(ValueError, match="coverage fields are strict"):
        multilingual._hydrate_locale_plan(
            brief,
            external,
            generation=4,
            rebuild_by_slot={"article-01": True},
            prior_plan=prior,
        )


@pytest.mark.parametrize("mutation", ["unknown", "missing", "duplicate"])
def test_ja_continuation_source_refs_fail_closed(mutation: str) -> None:
    brief = load_ja_plan_authority_fixture("brief.json")
    prior = load_ja_plan_authority_fixture("attempt_03_locale_plan.json")
    external = fresh_ja_plan_authority_fixture("fixed_current_ref_external_plan.json")
    mappings = external["articles"][0]["coverage_mapping"]
    if mutation == "unknown":
        mappings[0]["source_ref"] = "source_ref_99"
    elif mutation == "missing":
        mappings.pop()
    else:
        mappings[-1]["source_ref"] = mappings[0]["source_ref"]

    with pytest.raises(ValueError, match="source ref coverage|coverage differs"):
        multilingual._hydrate_locale_plan(
            brief,
            external,
            generation=4,
            rebuild_by_slot={"article-01": True},
            prior_plan=prior,
        )


def test_ja_same_domain_continuation_keeps_ref_topology_without_invalidation() -> None:
    brief = non_tarot_translation_brief("ja")
    prior = multilingual._hydrate_locale_plan(
        brief,
        external_locale_plan(brief),
        generation=1,
        rebuild_by_slot={"article-01": False},
    )

    prompt = multilingual._plan_prompt(
        brief,
        generation=2,
        prior_plan=prior,
        findings=[],
        rebuild_by_slot={"article-01": True},
    )
    legacy_authority = json.loads(
        prompt.split("legacy mapping authority:\n", 1)[1].split("\n", 1)[0]
    )
    constraints = json.loads(
        prompt.split("rebuild topology constraints:\n", 1)[1].split("\n", 1)[0]
    )

    assert legacy_authority["article-01"]["legacy_mapping_status"] == (
        "RETAINED_SAME_DOMAIN"
    )
    assert legacy_authority["article-01"]["legacy_id_counts"] == {
        "returned": len(multilingual._source_fact_package(brief)["articles"][0]["facts"]),
        "stale": 0,
        "missing": 0,
        "duplicates": 0,
    }
    assert constraints["articles"][0]["legacy_mapping_status"] == "RETAINED_SAME_DOMAIN"
    assert len(constraints["articles"][0]["prior_ref_to_h2_slot"]) == len(
        multilingual._source_fact_package(brief)["articles"][0]["facts"]
    )
    assert "source_fact_id" not in prompt


def test_ja_article_prompt_uses_provider_safe_refs_after_local_hydration() -> None:
    brief = load_ja_plan_authority_fixture("brief.json")
    prior = load_ja_plan_authority_fixture("attempt_03_locale_plan.json")
    external = fresh_ja_plan_authority_fixture("fixed_current_ref_external_plan.json")
    plan = multilingual._hydrate_locale_plan(
        brief,
        external,
        generation=4,
        rebuild_by_slot={"article-01": True},
        prior_plan=prior,
    )

    prompt = multilingual._article_prompt(brief, plan, [])
    article_input = json.loads(
        prompt.split("article input:\n", 1)[1].split("\n", 1)[0]
    )
    serialized = json.dumps(article_input, ensure_ascii=False)

    assert "source_ref_01" in serialized
    for forbidden in [
        "source_fact_id",
        "fact_id",
        "constraint_id",
        "source_span_id",
        "source_sha256",
        "source_version_digest",
    ]:
        assert forbidden not in serialized


def test_ja_source_ref_map_is_persisted_before_provider_plan_call(tmp_path: Path) -> None:
    brief = non_tarot_translation_brief("ja")
    prior = multilingual._hydrate_locale_plan(
        brief,
        external_locale_plan(brief),
        generation=1,
        rebuild_by_slot={"article-01": False},
    )

    class PendingPlanClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def generate_json(
            self,
            _role: str,
            _prompt: str,
            _schema: dict[str, object],
        ) -> dict[str, object]:
            raise RuntimeError("provider pending after map persistence")

    generation_dir = tmp_path / "generations" / "02"
    with pytest.raises(RuntimeError, match="provider pending"):
        multilingual._run_locale_generation(
            brief,
            PendingPlanClient(),
            generation=2,
            generation_dir=generation_dir,
            findings=[],
            history=[],
            prior_plan=prior,
        )

    persisted = json.loads(
        (generation_dir / "source-ref-map.json").read_text(encoding="utf-8")
    )
    assert persisted["generation"] == 2
    assert [
        item["source_ref"]
        for item in persisted["articles"][0]["refs"]
    ] == [
        f"source_ref_{index + 1:02d}"
        for index, _fact in enumerate(
            multilingual._source_fact_package(brief)["articles"][0]["facts"]
        )
    ]
    assert not (generation_dir / "external-plan.json").exists()
    assert not (generation_dir / "planning-result.json").exists()


def test_ja_resume_rejects_persisted_external_plan_without_source_ref_map(
    tmp_path: Path,
) -> None:
    brief = load_ja_plan_authority_fixture("brief.json")
    prior = load_ja_plan_authority_fixture("attempt_03_locale_plan.json")
    generation_dir = tmp_path / "generations" / "04"
    multilingual.pipeline.write_json(
        generation_dir / "external-plan.json",
        fresh_ja_plan_authority_fixture("fixed_current_ref_external_plan.json"),
    )

    class FailIfCalled:
        def generate_json(self, *_args: object) -> dict[str, object]:
            raise AssertionError("persisted external plan must not call provider")

    with pytest.raises(
        multilingual.LocalePlanValidationError,
        match="source ref map missing",
    ):
        multilingual._run_locale_generation(
            brief,
            FailIfCalled(),
            generation=4,
            generation_dir=generation_dir,
            findings=[],
            history=[],
            prior_plan=prior,
        )

    result = json.loads(
        (generation_dir / "planning-result.json").read_text(encoding="utf-8")
    )
    assert result["planning_contract_status"] == "PLANNING_CONTRACT_FAILURE"
    assert result["terminal_stage"] == "PLANNING"
    assert not (generation_dir / "article-operation.json").exists()
    assert not (generation_dir / "review-operation.json").exists()
    assert "article_provider_calls" not in result
    assert "reviewer_provider_calls" not in result


def test_ja_resume_rejects_stale_persisted_source_ref_map_after_extractor_change(
    tmp_path: Path,
) -> None:
    brief = load_ja_plan_authority_fixture("brief.json")
    prior = load_ja_plan_authority_fixture("attempt_03_locale_plan.json")
    generation_dir = tmp_path / "generations" / "04"
    source_ref_maps = multilingual._request_local_source_ref_maps(brief, prior)
    multilingual.pipeline.write_json(
        generation_dir / "source-ref-map.json",
        multilingual._source_ref_map_artifact(source_ref_maps, generation=4),
    )
    multilingual.pipeline.write_json(
        generation_dir / "external-plan.json",
        fresh_ja_plan_authority_fixture("fixed_current_ref_external_plan.json"),
    )
    mutated = json.loads(json.dumps(brief))
    source = mutated["articles"][0]["source"]
    source["bodySections"][0]["paragraphs"][0] += " これは検証用の追加文です。"
    mutated["articles"][0]["source_sha256"] = multilingual.source_sha256(source)

    class FailIfCalled:
        def generate_json(self, *_args: object) -> dict[str, object]:
            raise AssertionError("stale map must fail before provider or article")

    with pytest.raises(
        multilingual.LocalePlanValidationError,
        match="source ref map current fact coverage differs",
    ):
        multilingual._run_locale_generation(
            mutated,
            FailIfCalled(),
            generation=4,
            generation_dir=generation_dir,
            findings=[],
            history=[],
            prior_plan=prior,
        )

    result = json.loads(
        (generation_dir / "planning-result.json").read_text(encoding="utf-8")
    )
    assert result["planning_contract_status"] == "PLANNING_CONTRACT_FAILURE"
    assert result["terminal_stage"] == "PLANNING"
    assert not (generation_dir / "article-operation.json").exists()
    assert not (generation_dir / "review-operation.json").exists()
    assert "article_provider_calls" not in result
    assert "reviewer_provider_calls" not in result


def test_ja_planning_result_records_contract_failure_before_article(
    tmp_path: Path,
) -> None:
    brief = load_ja_plan_authority_fixture("brief.json")
    prior = load_ja_plan_authority_fixture("attempt_03_locale_plan.json")
    generation_dir = tmp_path / "generations" / "04"
    source_ref_maps = multilingual._request_local_source_ref_maps(brief, prior)
    multilingual.pipeline.write_json(
        generation_dir / "source-ref-map.json",
        multilingual._source_ref_map_artifact(source_ref_maps, generation=4),
    )
    multilingual.pipeline.write_json(
        generation_dir / "external-plan.json",
        load_ja_plan_authority_fixture("generation_04_external_plan.json"),
    )
    write_legacy_provider_safety_receipt(
        generation_dir,
        brief,
        prior,
        source_ref_maps,
    )

    class FailIfCalled:
        def generate_json(self, *_args: object) -> dict[str, object]:
            raise AssertionError("persisted external plan must fail in hydration")

    with pytest.raises(multilingual.LocalePlanValidationError):
        multilingual._run_locale_generation(
            brief,
            FailIfCalled(),
            generation=4,
            generation_dir=generation_dir,
            findings=[],
            history=[],
            prior_plan=prior,
        )

    result = json.loads(
        (generation_dir / "planning-result.json").read_text(encoding="utf-8")
    )
    assert result == {
        "schema_version": 1,
        "generation": 4,
        "transport_status": "EXTERNAL_PLAN_AVAILABLE",
        "planning_contract_status": "PLANNING_CONTRACT_FAILURE",
        "terminal_stage": "PLANNING",
        "terminal_reason": "external locale plan article fields are strict for article-01",
    }
    assert not (generation_dir / "article-operation.json").exists()
    assert not (generation_dir / "review-operation.json").exists()


def test_ja_planning_result_passes_only_after_local_hydration(tmp_path: Path) -> None:
    brief = load_ja_plan_authority_fixture("brief.json")
    prior = load_ja_plan_authority_fixture("attempt_03_locale_plan.json")
    generation_dir = tmp_path / "generations" / "04"
    source_ref_maps = multilingual._request_local_source_ref_maps(brief, prior)
    multilingual.pipeline.write_json(
        generation_dir / "source-ref-map.json",
        multilingual._source_ref_map_artifact(source_ref_maps, generation=4),
    )
    multilingual.pipeline.write_json(
        generation_dir / "external-plan.json",
        fresh_ja_plan_authority_fixture("fixed_current_ref_external_plan.json"),
    )

    class PendingArticleClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def generate_json(
            self,
            _role: str,
            _prompt: str,
            _schema: dict[str, object],
        ) -> dict[str, object]:
            raise RuntimeError("stop after planning success")

    with pytest.raises(RuntimeError, match="planning success"):
        multilingual._run_locale_generation(
            brief,
            PendingArticleClient(),
            generation=4,
            generation_dir=generation_dir,
            findings=[],
            history=[],
            prior_plan=prior,
        )

    result = json.loads(
        (generation_dir / "planning-result.json").read_text(encoding="utf-8")
    )
    assert result["planning_contract_status"] == "PASS"
    assert result["terminal_stage"] is None
    assert result["terminal_reason"] is None
    assert "article_provider_calls" not in result
    assert "reviewer_provider_calls" not in result
    assert (generation_dir / "locale-plan.json").is_file()
    assert (generation_dir / "article-operation.json").is_file()


def test_ja_legacy_provider_safety_read_requires_receipt(tmp_path: Path) -> None:
    brief = load_ja_plan_authority_fixture("brief.json")
    prior = load_ja_plan_authority_fixture("attempt_03_locale_plan.json")
    generation_dir = tmp_path / "generations" / "04"
    source_ref_maps = multilingual._request_local_source_ref_maps(brief, prior)
    multilingual.pipeline.write_json(
        generation_dir / "source-ref-map.json",
        multilingual._source_ref_map_artifact(source_ref_maps, generation=4),
    )
    multilingual.pipeline.write_json(
        generation_dir / "external-plan.json",
        load_ja_plan_authority_fixture("fixed_current_ref_external_plan.json"),
    )

    class FailIfCalled:
        def generate_json(self, *_args: object) -> dict[str, object]:
            raise AssertionError("legacy persisted plan must fail before provider")

    with pytest.raises(
        multilingual.LocalePlanValidationError,
        match="legacy external locale plan safety requires planning receipt",
    ):
        multilingual._run_locale_generation(
            brief,
            FailIfCalled(),
            generation=4,
            generation_dir=generation_dir,
            findings=[],
            history=[],
            prior_plan=prior,
        )

    result = json.loads(
        (generation_dir / "planning-result.json").read_text(encoding="utf-8")
    )
    assert result["terminal_reason"] == (
        "legacy external locale plan safety requires planning receipt"
    )
    assert not (generation_dir / "article-operation.json").exists()


def test_ja_legacy_provider_safety_read_rejects_schema_receipt_drift(
    tmp_path: Path,
) -> None:
    brief = load_ja_plan_authority_fixture("brief.json")
    prior = load_ja_plan_authority_fixture("attempt_03_locale_plan.json")
    generation_dir = tmp_path / "generations" / "04"
    source_ref_maps = multilingual._request_local_source_ref_maps(brief, prior)
    multilingual.pipeline.write_json(
        generation_dir / "source-ref-map.json",
        multilingual._source_ref_map_artifact(source_ref_maps, generation=4),
    )
    multilingual.pipeline.write_json(
        generation_dir / "external-plan.json",
        load_ja_plan_authority_fixture("fixed_current_ref_external_plan.json"),
    )
    write_legacy_provider_safety_receipt(
        generation_dir,
        brief,
        prior,
        source_ref_maps,
        schema_sha256="0" * 64,
    )

    class FailIfCalled:
        def generate_json(self, *_args: object) -> dict[str, object]:
            raise AssertionError("legacy schema drift must fail before provider")

    with pytest.raises(
        multilingual.LocalePlanValidationError,
        match="legacy external locale plan safety receipt schema drift",
    ):
        multilingual._run_locale_generation(
            brief,
            FailIfCalled(),
            generation=4,
            generation_dir=generation_dir,
            findings=[],
            history=[],
            prior_plan=prior,
        )

    assert not (generation_dir / "article-operation.json").exists()


def test_ja_legacy_provider_safety_read_ignores_only_safety_assertion(
    tmp_path: Path,
) -> None:
    brief = load_ja_plan_authority_fixture("brief.json")
    prior = load_ja_plan_authority_fixture("attempt_03_locale_plan.json")
    generation_dir = tmp_path / "generations" / "04"
    source_ref_maps = multilingual._request_local_source_ref_maps(brief, prior)
    external = load_ja_plan_authority_fixture("fixed_current_ref_external_plan.json")
    for mapping in external["articles"][0]["coverage_mapping"]:
        mapping["safety_boundary"] = True
    multilingual.pipeline.write_json(
        generation_dir / "source-ref-map.json",
        multilingual._source_ref_map_artifact(source_ref_maps, generation=4),
    )
    multilingual.pipeline.write_json(generation_dir / "external-plan.json", external)
    write_legacy_provider_safety_receipt(
        generation_dir,
        brief,
        prior,
        source_ref_maps,
    )
    legacy_bytes = {
        name: (generation_dir / name).read_bytes()
        for name in [
            "external-plan.json",
            "source-ref-map.json",
            "plan-operation.json",
        ]
    }
    calls: Counter[str] = Counter()

    class PendingArticleClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def generate_json(
            self,
            role: str,
            _prompt: str,
            schema: dict[str, object],
        ) -> dict[str, object]:
            if "native_search_intent" in json.dumps(schema):
                raise AssertionError("legacy plan read must not call provider")
            calls[role] += 1
            raise RuntimeError("stop after planning success")

    with pytest.raises(RuntimeError, match="planning success"):
        multilingual._run_locale_generation(
            brief,
            PendingArticleClient(),
            generation=4,
            generation_dir=generation_dir,
            findings=[],
            history=[],
            prior_plan=prior,
        )

    locale_plan = json.loads(
        (generation_dir / "locale-plan.json").read_text(encoding="utf-8")
    )
    expected_safety = [
        fact["safety_boundary"]
        for fact in multilingual._source_fact_package(brief)["articles"][0]["facts"]
    ]
    assert [
        mapping["safety_boundary"]
        for mapping in locale_plan["articles"][0]["coverage_mapping"]
    ] == expected_safety
    assert calls == Counter({"writer": 1})
    assert legacy_bytes == {
        name: (generation_dir / name).read_bytes()
        for name in legacy_bytes
    }


@pytest.mark.parametrize("mutation", ["unknown", "missing", "duplicate"])
def test_ja_legacy_provider_safety_read_ref_drift_fails_closed(
    tmp_path: Path,
    mutation: str,
) -> None:
    brief = load_ja_plan_authority_fixture("brief.json")
    prior = load_ja_plan_authority_fixture("attempt_03_locale_plan.json")
    generation_dir = tmp_path / "generations" / "04"
    source_ref_maps = multilingual._request_local_source_ref_maps(brief, prior)
    external = load_ja_plan_authority_fixture("fixed_current_ref_external_plan.json")
    mappings = external["articles"][0]["coverage_mapping"]
    if mutation == "unknown":
        mappings[0]["source_ref"] = "source_ref_99"
    elif mutation == "missing":
        mappings.pop()
    else:
        mappings[-1]["source_ref"] = mappings[0]["source_ref"]
    multilingual.pipeline.write_json(
        generation_dir / "source-ref-map.json",
        multilingual._source_ref_map_artifact(source_ref_maps, generation=4),
    )
    multilingual.pipeline.write_json(generation_dir / "external-plan.json", external)
    write_legacy_provider_safety_receipt(
        generation_dir,
        brief,
        prior,
        source_ref_maps,
    )

    class FailIfCalled:
        def generate_json(self, *_args: object) -> dict[str, object]:
            raise AssertionError("legacy ref drift must fail before article")

    with pytest.raises(
        multilingual.LocalePlanValidationError,
        match="source ref coverage|coverage differs",
    ):
        multilingual._run_locale_generation(
            brief,
            FailIfCalled(),
            generation=4,
            generation_dir=generation_dir,
            findings=[],
            history=[],
            prior_plan=prior,
        )

    assert not (generation_dir / "article-operation.json").exists()


def test_exact_production_gen05_legacy_safety_hydrates_read_only() -> None:
    run_dir = Path(
        "/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/queue/"
        "translation-runs/auto-i18n-ja-1414b75a404721e95e74"
    )
    if not run_dir.is_dir():
        pytest.skip("exact production gen05 fixture is not mounted")
    generation_dir = run_dir / "generations" / "05"
    legacy_paths = [
        generation_dir / "external-plan.json",
        generation_dir / "source-ref-map.json",
        generation_dir / "plan-operation.json",
    ]
    for path in [
        run_dir / "brief.json",
        run_dir / "attempts/03/locale-plan.json",
        *legacy_paths,
    ]:
        assert path.is_file()
    state_path = run_dir / "continuation/state.json"
    before_bytes = {path: path.read_bytes() for path in legacy_paths}
    before_state = state_path.read_bytes() if state_path.is_file() else None
    gen06_dir = run_dir / "generations/06"

    def gen06_file_snapshot() -> dict[str, bytes] | None:
        if not gen06_dir.exists():
            return None
        assert gen06_dir.is_dir()
        return {
            path.relative_to(gen06_dir).as_posix(): path.read_bytes()
            for path in sorted(gen06_dir.rglob("*"))
            if path.is_file()
        }

    before_gen06 = gen06_file_snapshot()

    brief = json.loads((run_dir / "brief.json").read_text(encoding="utf-8"))
    prior = json.loads(
        (run_dir / "attempts/03/locale-plan.json").read_text(encoding="utf-8")
    )
    source_ref_maps = multilingual._source_ref_maps_from_artifact(
        json.loads((generation_dir / "source-ref-map.json").read_text(encoding="utf-8")),
        generation=5,
    )
    multilingual._validate_source_ref_maps_against_current_package(brief, source_ref_maps)
    multilingual._validate_legacy_provider_safety_receipt(
        generation_dir / "plan-operation.json",
        brief,
        prior,
        source_ref_maps,
    )
    plan = multilingual._hydrate_locale_plan(
        brief,
        json.loads((generation_dir / "external-plan.json").read_text(encoding="utf-8")),
        generation=5,
        rebuild_by_slot={"article-01": True},
        prior_plan=prior,
        source_ref_maps=source_ref_maps,
        allow_provider_safety_boundary=True,
    )
    coverage = plan["articles"][0]["coverage_mapping"]

    assert len(coverage) == 22
    assert {mapping["safety_boundary"] for mapping in coverage} == {False}
    assert multilingual._outline_topology(plan["articles"][0]) != (
        multilingual._outline_topology(prior["articles"][0])
    )
    assert gen06_file_snapshot() == before_gen06
    assert before_bytes == {path: path.read_bytes() for path in legacy_paths}
    if before_state is not None:
        assert state_path.read_bytes() == before_state


def test_ja_boundary_repetition_detects_exact_normalized_paraphrase_span() -> None:
    brief = load_ja_boundary_fixture("brief.json")
    candidate = load_ja_boundary_fixture("corrected_test_only_candidate.json")
    repeated = (
        "これは一般的な象徴解釈として整理するもので、個人の結果を断定しません。"
        "専門的な財務助言に代わるものではありません。"
    )
    for section in candidate["articles"][0]["bodySections"][:3]:
        section["paragraphs"][0] = f"{section['paragraphs'][0]}{repeated}"

    findings = multilingual.translation_findings(brief, candidate["articles"])

    assert any(
        item["code"] == "BOUNDARY_BOILERPLATE_REPEATED"
        and item["repeated_locations"] == ["body"]
        for item in findings
    )


def test_ja_unknown_boundary_candidate_fails_closed() -> None:
    brief = translation_brief("ja")
    source = brief["articles"][0]["source"]
    source["description"] = "本內容不得用於醫療診斷，也不得自行停藥。"
    brief["articles"][0]["source_sha256"] = multilingual.source_sha256(source)
    candidate = translation_candidate("ja")
    candidate["articles"][0]["source_sha256"] = brief["articles"][0]["source_sha256"]

    package = multilingual._source_fact_package(brief)
    dispositions = package["articles"][0]["protected_source"]["boundary_candidate_dispositions"]

    unresolved = [item for item in dispositions if "醫療診斷" in item["source_text"] or "自行停藥" in item["source_text"]]
    assert unresolved
    assert {item["disposition"] for item in unresolved} == {"UNRESOLVED"}
    findings = multilingual.translation_findings(brief, candidate["articles"])
    assert any(item["code"] == "UNRESOLVED_BOUNDARY_CANDIDATE" for item in findings)


def test_ja_high_risk_contrast_candidate_fails_closed_before_not_a_boundary() -> None:
    brief = translation_brief("ja")
    source = brief["articles"][0]["source"]
    source["description"] = "這不是醫療診斷而是一般資訊。"
    brief["articles"][0]["source_sha256"] = multilingual.source_sha256(source)
    candidate = translation_candidate("ja")
    candidate["articles"][0]["source_sha256"] = brief["articles"][0]["source_sha256"]

    package = multilingual._source_fact_package(brief)
    dispositions = package["articles"][0]["protected_source"]["boundary_candidate_dispositions"]
    medical = [item for item in dispositions if "醫療診斷" in item["source_text"]]

    assert medical
    assert medical[0]["disposition"] == "UNRESOLVED"
    assert medical[0]["reason_code"] == "high_risk_boundary_candidate"
    findings = multilingual.translation_findings(brief, candidate["articles"])
    assert any(item["code"] == "UNRESOLVED_BOUNDARY_CANDIDATE" for item in findings)


def test_ja_ordinary_negation_gets_not_a_boundary_disposition() -> None:
    brief = translation_brief("ja")
    source = brief["articles"][0]["source"]
    source["description"] = "この読み方は怖がらせるためではなく、状況を整理するための説明です。不能只看單一象徵，而要比較前後文。"
    brief["articles"][0]["source_sha256"] = multilingual.source_sha256(source)

    package = multilingual._source_fact_package(brief)
    dispositions = package["articles"][0]["protected_source"]["boundary_candidate_dispositions"]
    ordinary = [item for item in dispositions if "不能只看單一象徵" in item["source_text"]]

    assert ordinary
    assert ordinary[0]["disposition"] == "NOT_A_BOUNDARY"
    assert ordinary[0]["reason_code"] == "ordinary_content_contrast"
    assert ordinary[0].get("constraint_ids", []) == []
    assert not any(
        "不能只看單一象徵" in source_text
        for constraint in package["articles"][0]["protected_constraints"]
        for source_text in constraint.get("source_texts", [])
    )


def test_ja_boundary_corrected_fixture_passes_required_constraints() -> None:
    brief = load_ja_boundary_fixture("brief.json")
    candidate = load_ja_boundary_fixture("corrected_test_only_candidate.json")

    findings = multilingual.translation_findings(brief, candidate["articles"])

    assert not any(
        item["code"]
        in {
            "BOUNDARY_MEANING_MISSING",
            "BOUNDARY_BOILERPLATE_REPEATED",
            "UNRESOLVED_BOUNDARY_CANDIDATE",
        }
        for item in findings
    )


@pytest.mark.parametrize("locale", ["en", "ko"])
def test_protected_source_constraints_do_not_change_non_ja_fact_behavior(locale: str) -> None:
    brief = translation_brief(locale)

    article = multilingual._source_fact_package(brief)["articles"][0]

    assert "protected_constraints" not in article
    assert any(fact["safety_boundary"] for fact in article["facts"])


@pytest.mark.parametrize("locale", ["en", "ja", "ko"])
def test_public_brief_includes_locale_specific_editorial_contract(locale: str) -> None:
    public = multilingual._public_brief(translation_brief(locale))
    target = public["articles"][0]

    assert target["editorial_contract"] == multilingual.LOCALE_EDITORIAL_CONTRACTS[locale]
    assert "不是翻譯" in public["policy"]["purpose"]
    assert "相同 H2／段落骨架" in public["policy"]["hard_reject"]


def test_writer_prompt_requires_source_claim_traceability_and_rejects_filler() -> None:
    brief = translation_brief("en")
    plan = multilingual._hydrate_locale_plan(
        brief,
        external_locale_plan(brief),
        generation=1,
        rebuild_by_slot={"article-01": False},
    )
    prompt = multilingual._article_prompt(brief, plan, [])

    assert "source claim ledger" in prompt
    assert "不得用常識補完" in prompt
    assert "禁止用比喻、口號、華麗形容詞或抽象 AI 套話" in prompt
    assert "article input.locale 指定的語言完整重寫" in prompt
    assert "title、description、answer、tags、FAQ、H2 與 paragraphs" in prompt
    assert "禁止保留來源語言文字" in prompt


def test_writer_and_public_brief_require_native_language_tags() -> None:
    brief = translation_brief("ja")
    plan = multilingual._hydrate_locale_plan(
        brief,
        external_locale_plan(brief),
        generation=1,
        rebuild_by_slot={"article-01": False},
    )

    prompt = multilingual._article_prompt(brief, plan, [])
    tags_policy = multilingual._public_brief(brief)["policy"]["tags"]

    assert "tags 必須逐項以目標語言的自然搜尋用語重寫" in prompt
    assert "不得複製或沿用來源語言 tag" in prompt
    assert "tags 必須逐項以目標語言的自然搜尋用語重寫" in tags_policy
    assert "不得複製或沿用來源語言 tag" in tags_policy


@pytest.mark.parametrize("locale", ["en", "ja", "ko"])
def test_locale_plan_and_article_prompts_are_topic_neutral(locale: str) -> None:
    brief = non_tarot_translation_brief(locale)
    external_plan = external_locale_plan(brief)
    plan = multilingual._hydrate_locale_plan(
        brief,
        external_plan,
        generation=1,
        rebuild_by_slot={"article-01": False},
    )

    serialized_contract = json.dumps(
        multilingual.LOCALE_EDITORIAL_CONTRACTS[locale],
        ensure_ascii=False,
    ).lower()
    plan_prompt = multilingual._plan_prompt(
        brief,
        generation=1,
        prior_plan=None,
        findings=[],
        rebuild_by_slot={"article-01": False},
    )
    article_prompt = multilingual._article_prompt(brief, plan, [])

    for forbidden in (
        "tarot",
        "タロット",
        "타로",
        "upright",
        "reversed",
        "正位置",
        "逆位置",
        "정방향",
        "역방향",
    ):
        assert forbidden not in serialized_contract
        assert forbidden not in plan_prompt.lower()
        assert forbidden not in article_prompt.lower()
    assert "用神" in plan_prompt
    assert "ordered_h2_outline" in article_prompt


@pytest.mark.parametrize("locale", ["en", "ja", "ko"])
def test_locale_plan_accepts_native_script_with_names_acronyms_and_numbers(
    locale: str,
) -> None:
    brief = non_tarot_translation_brief(locale)
    external = external_locale_plan(brief)
    item = external["articles"][0]
    item["native_search_intent"] += " OpenAI GPT-5 2026"
    item["native_query_phrasings"].append("OpenAI GPT-5 2026")
    item["article_angle"] += " OpenAI GPT-5 2026"
    item["ordered_h2_outline"][0] = "OpenAI GPT-5 2026"
    item["coverage_mapping"][0]["coverage_note"] = "OpenAI GPT-5 2026"
    if locale == "ja":
        item["ordered_h2_outline"][1] = "用神判断基準"

    multilingual._hydrate_locale_plan(
        brief,
        external,
        generation=1,
        rebuild_by_slot={"article-01": False},
    )


def _replace_locale_plan_semantic_item(
    item: dict[str, object],
    field: str,
    text: str,
) -> None:
    if field in {"native_search_intent", "article_angle"}:
        item[field] = text
        return
    if field == "native_query_phrasings":
        queries = item[field]
        assert isinstance(queries, list)
        queries[0] = text
        return
    if field == "ordered_h2_outline":
        outline = item[field]
        assert isinstance(outline, list)
        outline[0] = text
        return
    mappings = item["coverage_mapping"]
    assert isinstance(mappings, list) and isinstance(mappings[0], dict)
    mappings[0]["coverage_note"] = text


@pytest.mark.parametrize("locale", ["ja", "ko"])
@pytest.mark.parametrize(
    "field",
    [
        "native_search_intent",
        "native_query_phrasings",
        "article_angle",
        "ordered_h2_outline",
        "coverage_note",
    ],
)
@pytest.mark.parametrize(
    "wrong_text",
    [
        "orbit velvet lanterns quietly",
        "Orbit Velvet Lanterns Quietly",
        "ORBIT VELVET LANTERNS QUIETLY",
        "Zorple Quindle Marvex Tundra",
        "ZXCV QWER",
    ],
)
def test_locale_plan_rejects_ascii_only_sentence_matrix(
    locale: str,
    field: str,
    wrong_text: str,
) -> None:
    brief = non_tarot_translation_brief(locale)
    external = external_locale_plan(brief)
    item = external["articles"][0]
    _replace_locale_plan_semantic_item(item, field, wrong_text)

    with pytest.raises(ValueError, match="native locale language"):
        multilingual._hydrate_locale_plan(
            brief,
            external,
            generation=1,
            rebuild_by_slot={"article-01": False},
        )


@pytest.mark.parametrize("locale", ["ja", "ko"])
@pytest.mark.parametrize(
    "text",
    [
        "OpenAI",
        "API",
        "GPT-5",
        "2026",
        "OpenAI GPT-5 2026",
    ],
)
def test_locale_plan_accepts_closed_ascii_only_literal_contract(
    locale: str,
    text: str,
) -> None:
    assert multilingual._plan_matches_target_language(locale, text)


@pytest.mark.parametrize(
    "text",
    [
        "@@OpenAI@@",
        "OpenAI???",
        "OpenAI/GPT-5/2026",
        "OpenAI,GPT-5;2026",
    ],
)
def test_ascii_literal_contract_requires_full_value_consumption(text: str) -> None:
    assert not multilingual._ascii_is_name_acronym_or_number(text)


@pytest.mark.parametrize("text", ["Strategy", "SOURCE", "Zorple"])
def test_ascii_literal_contract_rejects_unlisted_standalone_words(
    text: str,
) -> None:
    assert not multilingual._ascii_is_name_acronym_or_number(text)


@pytest.mark.parametrize("locale", ["ja", "ko"])
@pytest.mark.parametrize(
    "text",
    [
        "ABCDEFG",
        "Supercalifragilisticexpialidocious",
        "MODEL-12345678901234567890",
        "OpenAI GPT-5 2026 2027",
    ],
)
def test_locale_plan_rejects_ascii_literal_outside_closed_boundaries(
    locale: str,
    text: str,
) -> None:
    assert not multilingual._plan_matches_target_language(locale, text)


@pytest.mark.parametrize(
    ("locale", "text"),
    [
        ("ja", "OpenAIを使う"),
        ("ja", "APIを確認する"),
        ("ja", "GPT-5を比較する"),
        ("ja", "2026年の傾向"),
        ("ko", "OpenAI를 사용합니다"),
        ("ko", "API를 확인합니다"),
        ("ko", "GPT-5를 비교합니다"),
        ("ko", "2026년의 경향"),
    ],
)
def test_locale_plan_accepts_native_text_with_closed_ascii_literal(
    locale: str,
    text: str,
) -> None:
    assert multilingual._plan_matches_target_language(locale, text)


@pytest.mark.parametrize(
    ("locale", "query"),
    [
        ("ja", "ENTJ ENTP 恋愛 相性"),
        ("ko", "ENTJ ENTP 연애 적합성"),
    ],
)
def test_locale_plan_accepts_source_acronyms_in_native_query(
    locale: str,
    query: str,
) -> None:
    brief = non_tarot_translation_brief(locale)
    target = brief["articles"][0]
    assert isinstance(target, dict)
    source = target["source"]
    assert isinstance(source, dict)
    source["title"] = "ENTJ 與 ENTP 的 MBTI 戀愛互動"
    target["source_sha256"] = multilingual.source_sha256(source)
    external = external_locale_plan(brief)
    item = external["articles"][0]
    assert isinstance(item, dict)
    item["native_query_phrasings"] = [query]

    multilingual._hydrate_locale_plan(
        brief,
        external,
        generation=1,
        rebuild_by_slot={"article-01": False},
    )


@pytest.mark.parametrize(
    ("locale", "query"),
    [
        ("ja", "ZXCV QWER 恋愛 相性"),
        ("ko", "ZXCV QWER 연애 적합성"),
    ],
)
def test_locale_plan_rejects_unrelated_acronyms_in_native_query(
    locale: str,
    query: str,
) -> None:
    brief = non_tarot_translation_brief(locale)
    target = brief["articles"][0]
    assert isinstance(target, dict)
    source = target["source"]
    assert isinstance(source, dict)
    source["title"] = "ENTJ 與 ENTP 的 MBTI 戀愛互動"
    target["source_sha256"] = multilingual.source_sha256(source)
    external = external_locale_plan(brief)
    item = external["articles"][0]
    assert isinstance(item, dict)
    item["native_query_phrasings"] = [query]

    with pytest.raises(ValueError, match="native locale language"):
        multilingual._hydrate_locale_plan(
            brief,
            external,
            generation=1,
            rebuild_by_slot={"article-01": False},
        )


def test_locale_plan_accepts_valid_japanese_kanji_only_heading() -> None:
    assert multilingual._plan_matches_target_language("ja", "実践方法")


@pytest.mark.parametrize("locale", ["en", "ja", "ko"])
@pytest.mark.parametrize(
    "field",
    [
        "native_search_intent",
        "native_query_phrasings",
        "article_angle",
        "ordered_h2_outline",
        "coverage_note",
    ],
)
def test_locale_plan_rejects_wrong_language_in_each_critical_item(
    locale: str,
    field: str,
) -> None:
    brief = non_tarot_translation_brief(locale)
    external = external_locale_plan(brief)
    item = external["articles"][0]
    wrong_text = (
        "用神的判斷順序與限制"
        if locale == "en"
        else "How to identify the useful element and its limits"
    )
    if field in {"native_search_intent", "article_angle"}:
        item[field] = wrong_text
    elif field == "native_query_phrasings":
        item[field][0] = wrong_text
    elif field == "ordered_h2_outline":
        item[field][0] = wrong_text
    else:
        item["coverage_mapping"][0]["coverage_note"] = wrong_text

    with pytest.raises(ValueError, match="native locale language"):
        multilingual._hydrate_locale_plan(
            brief,
            external,
            generation=1,
            rebuild_by_slot={"article-01": False},
        )


@pytest.mark.parametrize("locale", ["ja", "ko"])
def test_locale_plan_rejects_uppercase_general_english_heading(locale: str) -> None:
    brief = non_tarot_translation_brief(locale)
    external = external_locale_plan(brief)
    item = external["articles"][0]
    item["ordered_h2_outline"][0] = "HOW TO USE THE USEFUL ELEMENT"

    with pytest.raises(ValueError, match="native locale language"):
        multilingual._hydrate_locale_plan(
            brief,
            external,
            generation=1,
            rebuild_by_slot={"article-01": False},
        )


@pytest.mark.parametrize(
    ("locale", "wrong_text"),
    [
        ("en", "用神的判斷順序與限制"),
        ("ja", "How to identify the useful element and its limits"),
        ("ja", "用神的判斷順序與限制"),
        ("ko", "How to identify the useful element and its limits"),
        ("ko", "用神的判斷順序與限制"),
    ],
)
def test_locale_plan_rejects_wrong_script_semantic_fields(
    locale: str,
    wrong_text: str,
) -> None:
    brief = non_tarot_translation_brief(locale)
    external = external_locale_plan(brief)
    item = external["articles"][0]
    item["native_search_intent"] = wrong_text
    item["native_query_phrasings"] = [wrong_text]
    item["article_angle"] = wrong_text
    item["ordered_h2_outline"] = [f"{wrong_text} {index}" for index in range(1, 5)]
    for mapping in item["coverage_mapping"]:
        mapping["coverage_note"] = wrong_text

    with pytest.raises(ValueError, match="native locale language"):
        multilingual._hydrate_locale_plan(
            brief,
            external,
            generation=1,
            rebuild_by_slot={"article-01": False},
        )


def test_article_phase_rejects_missing_invalid_or_mismatched_plan() -> None:
    brief = non_tarot_translation_brief()
    external = external_locale_plan(brief)
    plan = multilingual._hydrate_locale_plan(
        brief,
        external,
        generation=1,
        rebuild_by_slot={"article-01": False},
    )

    with pytest.raises(ValueError, match="locale plan"):
        multilingual._article_prompt(brief, None, [])

    invalid = json.loads(json.dumps(plan))
    del invalid["articles"][0]["coverage_mapping"]
    with pytest.raises(ValueError, match="locale plan"):
        multilingual._article_prompt(brief, invalid, [])

    mismatched = json.loads(json.dumps(plan))
    mismatched["articles"][0]["source_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="source hash"):
        multilingual._article_prompt(brief, mismatched, [])


def test_invalid_generated_plan_fails_before_article_candidate(tmp_path: Path) -> None:
    brief = non_tarot_translation_brief()
    multilingual.pipeline.write_json(tmp_path / "brief.json", brief)
    calls = 0

    class InvalidPlanClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def generate_json(
            self,
            _role: str,
            _prompt: str,
            _schema: dict[str, object],
        ) -> dict[str, object]:
            nonlocal calls
            calls += 1
            payload = external_locale_plan(brief)
            del payload["articles"][0]["coverage_mapping"]
            return payload

    with pytest.raises(ValueError, match="locale plan") as caught:
        multilingual.run_writer_reviewer(
            tmp_path,
            InvalidPlanClient(),
            max_repairs=2,
        )

    assert isinstance(caught.value, multilingual.LocalePlanValidationError)
    assert calls == 1
    assert not (tmp_path / "attempts/01/locale-plan.json").exists()
    assert not (tmp_path / "attempts/01/article-operation.json").exists()
    assert not (tmp_path / "candidate.json").exists()
    assert not (tmp_path / "review.json").exists()


def test_valid_locale_plan_reaches_candidate_persistence(tmp_path: Path) -> None:
    brief = non_tarot_translation_brief()
    multilingual.pipeline.write_json(tmp_path / "brief.json", brief)
    calls: list[str] = []
    outline: list[str] | None = None

    class ValidPlanClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def generate_json(
            self,
            role: str,
            _prompt: str,
            schema: dict[str, object],
        ) -> dict[str, object]:
            nonlocal outline
            calls.append(role)
            if "native_search_intent" in json.dumps(schema):
                payload = external_locale_plan(brief)
                outline = payload["articles"][0]["ordered_h2_outline"]
                return payload
            if role == "writer":
                return non_tarot_external_candidate(outline)
            return {
                "articles": [
                    {
                        "slot": "article-01",
                        "verdict": "APPROVE",
                        "findings": [],
                    }
                ]
            }

    candidate, review = multilingual.run_writer_reviewer(
        tmp_path,
        ValidPlanClient(),
        max_repairs=0,
    )

    assert calls == ["writer", "writer", "reviewer"]
    assert review["articles"][0]["verdict"] == "APPROVE"
    assert json.loads((tmp_path / "candidate.json").read_text()) == candidate
    assert json.loads((tmp_path / "review.json").read_text()) == review
    assert (tmp_path / "attempts/01/locale-plan.json").is_file()
    assert (tmp_path / "attempts/01/candidate.json").is_file()


def test_candidate_outline_mismatch_enters_semantic_repair(tmp_path: Path) -> None:
    brief = non_tarot_translation_brief()
    multilingual.pipeline.write_json(tmp_path / "brief.json", brief)
    plan_count = 0
    candidate_count = 0
    last_outline: list[str] | None = None

    class OutlineRepairClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def generate_json(
            self,
            role: str,
            _prompt: str,
            schema: dict[str, object],
        ) -> dict[str, object]:
            nonlocal plan_count, candidate_count, last_outline
            if "native_search_intent" in json.dumps(schema):
                plan_count += 1
                payload = external_locale_plan(brief)
                if plan_count == 1:
                    payload["articles"][0]["ordered_h2_outline"] = [
                        "h2-1",
                        "h2-2",
                        "h2-3",
                        "h2-4",
                    ]
                last_outline = payload["articles"][0]["ordered_h2_outline"]
                return payload
            if role == "writer":
                candidate_count += 1
                if candidate_count == 1:
                    return non_tarot_external_candidate()
                return non_tarot_external_candidate(last_outline)
            return {
                "articles": [
                    {
                        "slot": "article-01",
                        "verdict": "APPROVE",
                        "findings": [],
                    }
                ]
            }

    _candidate, review = multilingual.run_writer_reviewer(
        tmp_path,
        OutlineRepairClient(),
        max_repairs=1,
    )

    first_review = json.loads(
        (tmp_path / "attempts/01/review.json").read_text()
    )
    assert first_review["articles"][0]["verdict"] == "REJECT"
    assert {
        finding["code"]
        for finding in first_review["articles"][0]["findings"]
    } == {
        "LOCALE_PLAN_HEADING_PLACEHOLDER",
        "LOCALE_PLAN_OUTLINE_MISMATCH",
    }
    assert review["articles"][0]["verdict"] == "APPROVE"
    assert plan_count == candidate_count == 2


@pytest.mark.parametrize("mutation", ["missing", "duplicate"])
def test_locale_plan_rejects_incomplete_or_duplicate_coverage(
    mutation: str,
) -> None:
    brief = non_tarot_translation_brief()
    external = external_locale_plan(brief)
    mappings = external["articles"][0]["coverage_mapping"]
    if mutation == "missing":
        mappings.pop()
    else:
        mappings[-1] = json.loads(json.dumps(mappings[0]))

    with pytest.raises(ValueError, match="coverage"):
        multilingual._hydrate_locale_plan(
            brief,
            external,
            generation=1,
            rebuild_by_slot={"article-01": False},
        )


def test_locale_plan_canonicalizes_complete_coverage_mapping_order_drift() -> None:
    brief = non_tarot_translation_brief()
    external = external_locale_plan(brief)
    external["articles"][0]["coverage_mapping"].reverse()

    plan = multilingual._hydrate_locale_plan(
        brief,
        external,
        generation=1,
        rebuild_by_slot={"article-01": False},
    )

    assert [
        mapping["source_fact_id"]
        for mapping in plan["articles"][0]["coverage_mapping"]
    ] == [
        fact["fact_id"]
        for fact in multilingual._source_fact_package(brief)["articles"][0]["facts"]
    ]


def test_locale_plan_rejects_fresh_provider_safety_assertion() -> None:
    brief = non_tarot_translation_brief()
    external = external_locale_plan(brief)
    mappings = external["articles"][0]["coverage_mapping"]
    mappings.reverse()
    mappings[0]["safety_boundary"] = True

    with pytest.raises(ValueError, match="coverage fields are strict"):
        multilingual._hydrate_locale_plan(
            brief,
            external,
            generation=1,
            rebuild_by_slot={"article-01": False},
        )


def test_locale_plan_rejects_external_article_order_drift() -> None:
    japanese = non_tarot_translation_brief("ja")
    korean = non_tarot_translation_brief("ko")
    brief = {
        **japanese,
        "run_id": "auto-i18n-multi-fortune-0039",
        "articles": [japanese["articles"][0], korean["articles"][0]],
    }
    japanese_plan = external_locale_plan(japanese)["articles"][0]
    korean_plan = external_locale_plan(korean)["articles"][0]
    korean_plan["slot"] = "article-02"
    external = {"articles": [korean_plan, japanese_plan]}

    with pytest.raises(ValueError, match="slots differ from brief order"):
        multilingual._hydrate_locale_plan(
            brief,
            external,
            generation=1,
            rebuild_by_slot={
                "article-01": False,
                "article-02": False,
            },
        )


def test_external_locale_plan_schema_locks_current_brief_coverage() -> None:
    brief = non_tarot_translation_brief()
    schema = multilingual._external_locale_plan_schema(brief)
    articles_schema = schema["properties"]["articles"]
    item_schema = articles_schema["items"]
    coverage_schema = item_schema["properties"]["coverage_mapping"]
    facts = multilingual._source_fact_package(brief)["articles"][0]["facts"]

    assert articles_schema["minItems"] == articles_schema["maxItems"] == 1
    assert item_schema["properties"]["slot"]["enum"] == ["article-01"]
    assert item_schema["properties"]["locale"]["enum"] == ["ko"]
    assert item_schema["properties"]["source_sha256"]["enum"] == [
        brief["articles"][0]["source_sha256"]
    ]
    assert coverage_schema["minItems"] == coverage_schema["maxItems"] == len(facts)
    assert coverage_schema["items"]["properties"]["source_fact_id"]["enum"] == [
        fact["fact_id"] for fact in facts
    ]
    assert "safety_boundary" not in coverage_schema["items"]["properties"]
    assert "safety_boundary" not in coverage_schema["items"]["required"]
    assert coverage_schema["items"]["properties"]["planned_h2_slot"]["enum"] == [
        "h2-1",
        "h2-2",
        "h2-3",
        "h2-4",
    ]
    assert item_schema["properties"]["ordered_h2_outline"]["minItems"] == 4
    assert item_schema["properties"]["ordered_h2_outline"]["maxItems"] == 4


def test_locale_plan_resolves_coverage_by_outline_index() -> None:
    brief = non_tarot_translation_brief()
    external = external_locale_plan(brief)

    plan = multilingual._hydrate_locale_plan(
        brief,
        external,
        generation=1,
        rebuild_by_slot={"article-01": False},
    )

    assert all(
        mapping["planned_h2"] in plan["articles"][0]["ordered_h2_outline"]
        for mapping in plan["articles"][0]["coverage_mapping"]
    )
    assert all(
        "planned_h2_slot" not in mapping
        for mapping in plan["articles"][0]["coverage_mapping"]
    )


def test_locale_plan_hydrates_source_structure_blacklist_from_brief() -> None:
    brief = non_tarot_translation_brief()
    external = external_locale_plan(brief)
    external["articles"][0]["source_structure_not_copied"] = [
        "source_h2_order",
        "source_section_count",
        "source_paragraph_counts",
    ]

    plan = multilingual._hydrate_locale_plan(
        brief,
        external,
        generation=1,
        rebuild_by_slot={"article-01": False},
    )

    assert plan["articles"][0]["source_structure_not_copied"] == [
        section["heading"]
        for section in brief["articles"][0]["source"]["bodySections"]
    ]


@pytest.mark.parametrize("heading_slot", ["h2-0", "h2-5", 1, True])
def test_locale_plan_rejects_coverage_outline_slot_outside_generated_outline(
    heading_slot: object,
) -> None:
    brief = non_tarot_translation_brief()
    external = external_locale_plan(brief)
    external["articles"][0]["coverage_mapping"][0]["planned_h2_slot"] = heading_slot

    with pytest.raises(ValueError, match="coverage heading slot"):
        multilingual._hydrate_locale_plan(
            brief,
            external,
            generation=1,
            rebuild_by_slot={"article-01": False},
        )


@pytest.mark.parametrize(
    ("finding_code", "expected_verdict"),
    [
        (None, "APPROVE"),
        ("NON_NATIVE_SEARCH_INTENT", "REJECT"),
        ("AI_TEMPLATE_STYLE", "REJECT"),
    ],
)
def test_i18n_rewrite_persists_candidate_and_preserves_native_quality_gate(
    tmp_path: Path,
    finding_code: str | None,
    expected_verdict: str,
) -> None:
    brief = non_tarot_translation_brief()
    multilingual.pipeline.write_json(tmp_path / "brief.json", brief)
    outline: list[str] | None = None

    class RewriteClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def generate_json(
            self,
            role: str,
            _prompt: str,
            schema: dict[str, object],
        ) -> dict[str, object]:
            nonlocal outline
            if "native_search_intent" in json.dumps(schema):
                payload = external_locale_plan(brief)
                outline = payload["articles"][0]["ordered_h2_outline"]
                return payload
            if role == "writer":
                return non_tarot_external_candidate(outline)
            findings = (
                []
                if finding_code is None
                else [
                    {
                        "code": finding_code,
                        "message": "母語品質契約的 deterministic fixture",
                    }
                ]
            )
            return {
                "articles": [
                    {
                        "slot": "article-01",
                        "verdict": expected_verdict,
                        "findings": findings,
                    }
                ]
            }

    candidate, review = multilingual.run_writer_reviewer(
        tmp_path,
        RewriteClient(),
        max_repairs=0,
    )

    assert json.loads((tmp_path / "candidate.json").read_text()) == candidate
    assert json.loads((tmp_path / "review.json").read_text()) == review
    assert review["articles"][0]["verdict"] == expected_verdict
    assert [item["code"] for item in review["articles"][0]["findings"]] == (
        [] if finding_code is None else [finding_code]
    )


def test_outline_rebuild_rejects_synonym_headings_with_same_fact_topology() -> None:
    brief = non_tarot_translation_brief()
    prior = multilingual._hydrate_locale_plan(
        brief,
        external_locale_plan(brief),
        generation=1,
        rebuild_by_slot={"article-01": False},
    )
    synonym_only = external_locale_plan(
        brief,
        rebuild_outline=True,
        outline=[
            "용신이 해결하는 핵심 질문",
            "강약과 절기를 같이 확인하는 까닭",
            "오행 흐름에서 조정 방향 고르기",
            "하나의 공식으로 결론 내리지 않기",
        ],
    )

    with pytest.raises(ValueError, match="reused prior outline topology"):
        multilingual._hydrate_locale_plan(
            brief,
            synonym_only,
            generation=2,
            rebuild_by_slot={"article-01": True},
            prior_plan=prior,
        )


def test_outline_rebuild_allows_same_headings_with_changed_fact_topology() -> None:
    brief = non_tarot_translation_brief()
    prior = multilingual._hydrate_locale_plan(
        brief,
        external_locale_plan(brief),
        generation=1,
        rebuild_by_slot={"article-01": False},
    )
    rebuilt = external_locale_plan(
        brief,
        rebuild_outline=True,
        coverage_shift=1,
    )

    current = multilingual._hydrate_locale_plan(
        brief,
        rebuilt,
        generation=2,
        rebuild_by_slot={"article-01": True},
        prior_plan=prior,
    )

    assert current["articles"][0]["ordered_h2_outline"] == (
        prior["articles"][0]["ordered_h2_outline"]
    )
    assert multilingual._outline_topology(current["articles"][0]) != (
        multilingual._outline_topology(prior["articles"][0])
    )


def test_rebuild_prompt_defines_fact_to_slot_topology_after_synonym_only_rejection() -> None:
    brief = non_tarot_translation_brief("ja")
    prior_external = external_locale_plan(brief)
    prior = multilingual._hydrate_locale_plan(
        brief,
        prior_external,
        generation=1,
        rebuild_by_slot={"article-01": False},
    )
    synonym_only = external_locale_plan_with_source_refs(
        brief,
        rebuild_outline=True,
        outline=[
            "用神が示す中心的な問い",
            "強弱と季節を合わせて見る理由",
            "五行の流れから調整方法を選ぶ",
            "一つの公式で断定しない",
        ],
    )

    assert (
        synonym_only["articles"][0]["ordered_h2_outline"]
        != prior_external["articles"][0]["ordered_h2_outline"]
    )
    assert [
        mapping["planned_h2_slot"]
        for mapping in synonym_only["articles"][0]["coverage_mapping"]
    ] == [
        mapping["planned_h2_slot"]
        for mapping in prior_external["articles"][0]["coverage_mapping"]
    ]
    with pytest.raises(ValueError, match="reused prior outline topology"):
        multilingual._hydrate_locale_plan(
            brief,
            synonym_only,
            generation=3,
            rebuild_by_slot={"article-01": True},
            prior_plan=prior,
        )

    prompt = multilingual._plan_prompt(
        brief,
        generation=3,
        prior_plan=prior,
        findings=[
            {
                "code": "NON_NATIVE_SEARCH_INTENT",
                "message": "見出しだけでなく構成を作り直してください",
            }
        ],
        rebuild_by_slot={"article-01": True},
    )
    contract = json.loads(
        prompt.split("rebuild contract:\n", 1)[1].split("\n", 1)[0]
    )

    assert contract == {
        "required_when": "rebuild_outline=true",
        "topology_definition": (
            "依 source_ref 順序排列的 coverage_mapping.planned_h2_slot 序列"
        ),
        "prior_comparison": (
            "將 prior plan coverage_mapping.planned_h2 對回 prior "
            "ordered_h2_outline 的 h2-1 至 h2-4"
        ),
        "minimum_change": (
            "至少一個有意義 fact 的 planned_h2_slot 必須與 prior plan 不同"
        ),
        "must_preserve": [
            "全部 source_ref",
            "local safety authority",
            "locale plan JSON schema",
        ],
        "insufficient_changes": [
            "只換 H2 標題或同義詞",
            "只改標題順序文字",
            "只改 coverage_note",
        ],
    }


def test_replacement_third_generation_gets_explicit_prior_topology_contract(
    tmp_path: Path,
) -> None:
    brief = non_tarot_translation_brief("ja")
    brief["run_id"] = f"{brief['run_id']}-replacement-01"
    multilingual.pipeline.write_json(tmp_path / "brief.json", brief)
    plan_count = 0
    review_count = 0
    last_outline: list[str] | None = None

    class ProductionShapedClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def generate_json(
            self,
            role: str,
            prompt: str,
            schema: dict[str, object],
        ) -> dict[str, object]:
            nonlocal plan_count, review_count, last_outline
            if "native_search_intent" in json.dumps(schema):
                plan_count += 1
                if plan_count < 3:
                    payload = (
                        external_locale_plan(brief)
                        if plan_count == 1
                        else external_locale_plan_with_source_refs(brief)
                    )
                else:
                    constraints = json.loads(
                        prompt.split("rebuild topology constraints:\n", 1)[1].split(
                            "\n", 1
                        )[0]
                    )
                    article_contract = constraints["articles"][0]
                    assert article_contract["slot"] == "article-01"
                    assert article_contract["rebuild_required"] is True
                    expected_prior = external_locale_plan(brief)["articles"][0][
                        "coverage_mapping"
                    ]
                    refs = multilingual._request_local_source_ref_maps(
                        brief,
                        {"articles": [{"slot": "article-01"}]},
                    )["article-01"]
                    fact_to_ref = {fact_id: ref for ref, fact_id in refs.items()}
                    assert article_contract["prior_ref_to_h2_slot"] == [
                        {
                            "source_ref": fact_to_ref[mapping["source_fact_id"]],
                            "planned_h2_slot": mapping["planned_h2_slot"],
                        }
                        for mapping in expected_prior
                    ]
                    assert article_contract[
                        "forbidden_prior_topology_signature"
                    ] == [mapping["planned_h2_slot"] for mapping in expected_prior]
                    payload = external_locale_plan_with_source_refs(
                        brief,
                        rebuild_outline=True,
                        coverage_shift=1,
                        outline=[
                            "用神を探す前に確認する条件",
                            "命式の偏りを分けて読む",
                            "調整候補を比較する手順",
                            "判断に残すべき限界",
                        ],
                    )
                last_outline = payload["articles"][0]["ordered_h2_outline"]
                return payload
            if role == "writer":
                return non_tarot_external_candidate(last_outline)
            review_count += 1
            return {
                "articles": [
                    {
                        "slot": "article-01",
                        "verdict": "REJECT" if review_count < 3 else "APPROVE",
                        "findings": (
                            [
                                {
                                    "code": "MIRRORED_STRUCTURE",
                                    "message": "見出しだけでなく構成も前世代と同じです",
                                }
                            ]
                            if review_count < 3
                            else []
                        ),
                    }
                ]
            }

    multilingual.run_writer_reviewer(
        tmp_path,
        ProductionShapedClient(),
        max_repairs=2,
    )

    second = json.loads((tmp_path / "attempts/02/locale-plan.json").read_text())
    third = json.loads((tmp_path / "attempts/03/locale-plan.json").read_text())
    assert multilingual._outline_topology(third["articles"][0]) != (
        multilingual._outline_topology(second["articles"][0])
    )


@pytest.mark.parametrize(
    ("external_rebuild", "pipeline_rebuild"),
    [(True, False), (False, True)],
)
def test_locale_plan_canonicalizes_rebuild_to_pipeline_authority(
    external_rebuild: bool,
    pipeline_rebuild: bool,
) -> None:
    brief = non_tarot_translation_brief()
    external = external_locale_plan(
        brief,
        rebuild_outline=external_rebuild,
    )

    plan = multilingual._hydrate_locale_plan(
        brief,
        external,
        generation=1,
        rebuild_by_slot={"article-01": pipeline_rebuild},
    )

    assert plan["articles"][0]["rebuild_outline"] is pipeline_rebuild


def test_locale_plan_rejects_non_boolean_external_rebuild_flag() -> None:
    brief = non_tarot_translation_brief()
    external = external_locale_plan(brief)
    external["articles"][0]["rebuild_outline"] = "false"

    with pytest.raises(ValueError, match="rebuild flag is invalid"):
        multilingual._hydrate_locale_plan(
            brief,
            external,
            generation=1,
            rebuild_by_slot={"article-01": False},
        )


@pytest.mark.parametrize(
    "finding_code",
    [
        "AI_TEMPLATE_STYLE",
        "SOURCE_SYNTAX_TRANSFER",
        "NON_NATIVE_SEARCH_INTENT",
        "MIRRORED_STRUCTURE",
    ],
)
def test_repeated_native_finding_forces_new_outline_topology(
    tmp_path: Path,
    finding_code: str,
) -> None:
    brief = non_tarot_translation_brief()
    multilingual.pipeline.write_json(tmp_path / "brief.json", brief)
    plan_count = 0
    review_count = 0
    last_outline: list[str] | None = None

    class ScriptedClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def generate_json(
            self,
            role: str,
            _prompt: str,
            schema: dict[str, object],
        ) -> dict[str, object]:
            nonlocal plan_count, review_count, last_outline
            if "native_search_intent" in json.dumps(schema):
                plan_count += 1
                if plan_count == 3:
                    payload = external_locale_plan(
                        brief,
                        rebuild_outline=True,
                        coverage_shift=1,
                        outline=[
                            "용신을 검색할 때 가장 먼저 묻는 것",
                            "명식 전체에서 불균형 확인하기",
                            "조정 후보를 비교하는 순서",
                            "단정 대신 조건을 남기는 이유",
                        ],
                    )
                else:
                    payload = external_locale_plan(brief)
                last_outline = payload["articles"][0]["ordered_h2_outline"]
                return payload
            if role == "writer":
                return non_tarot_external_candidate(last_outline)
            review_count += 1
            if review_count < 3:
                return {
                    "articles": [
                        {
                            "slot": "article-01",
                            "verdict": "REJECT",
                                "findings": [
                                    {
                                        "code": finding_code,
                                        "message": "구조가 이전 세대와 같은 템플릿입니다",
                                    }
                                ],
                        }
                    ]
                }
            return {
                "articles": [
                    {
                        "slot": "article-01",
                        "verdict": "APPROVE",
                        "findings": [],
                    }
                ]
            }

    multilingual.run_writer_reviewer(tmp_path, ScriptedClient(), max_repairs=2)

    first = json.loads((tmp_path / "attempts/01/locale-plan.json").read_text())
    third = json.loads((tmp_path / "attempts/03/locale-plan.json").read_text())
    assert first["articles"][0]["rebuild_outline"] is False
    assert third["articles"][0]["rebuild_outline"] is True
    assert (
        third["articles"][0]["ordered_h2_outline"]
        != first["articles"][0]["ordered_h2_outline"]
    )


def test_rebuild_authority_ignores_cross_article_and_non_consecutive_findings() -> None:
    brief = {
        "articles": [
            {"translation_id": "article-a"},
            {"translation_id": "article-b"},
        ]
    }
    history = [
        [{"article_id": "article-a", "code": "MIRRORED_STRUCTURE", "message": "a1"}],
        [{"article_id": "article-b", "code": "MIRRORED_STRUCTURE", "message": "b2"}],
        [{"article_id": "article-a", "code": "MIRRORED_STRUCTURE", "message": "a3"}],
    ]

    assert multilingual._rebuild_authority(brief, history) == {
        "article-01": False,
        "article-02": False,
    }


def _write_rejected_deferred_lineage(run_dir: Path) -> tuple[dict[str, object], dict[str, object]]:
    brief = non_tarot_translation_brief()
    candidate = multilingual._hydrate_candidate(brief, non_tarot_external_candidate())
    review = {
        "schema_version": 1,
        "run_id": brief["run_id"],
        "articles": [
            {
                "article_id": "FORTUNE-0039:ko",
                "candidate_sha256": article_sha256(candidate["articles"][0]),
                "verdict": "REJECT",
                "findings": [
                    {
                        "code": "AI_TEMPLATE_STYLE",
                        "message": "기존 구조를 반복합니다",
                    }
                ],
            }
        ],
    }
    multilingual.pipeline.write_json(run_dir / "brief.json", brief)
    multilingual.pipeline.write_json(run_dir / "candidate.json", candidate)
    multilingual.pipeline.write_json(run_dir / "review.json", review)
    for attempt in range(1, 4):
        attempt_dir = run_dir / "attempts" / f"{attempt:02d}"
        multilingual.pipeline.write_json(
            attempt_dir / "external-review.json",
            {
                "articles": [
                    {
                        "slot": "article-01",
                        "verdict": "REJECT",
                        "findings": [
                            {
                                "code": "AI_TEMPLATE_STYLE",
                                "message": f"generation {attempt} repeats the template",
                            }
                        ],
                    }
                ]
            },
        )
        (attempt_dir / "immutable-marker.txt").write_text(
            f"legacy-attempt-{attempt}\n",
            encoding="utf-8",
        )
    return candidate, review


def _ja_external_candidate_from_outline(outline: list[str]) -> dict[str, object]:
    return {
        "articles": [
            {
                "slot": "article-01",
                "title": "死神カードが金銭面で示す見直し",
                "description": "死神は金銭の終わりではなく、古い使い方や前提を整理し直す合図として読めます。",
                "answer": "支出、収入、リスクの前提を分け、変えるべき習慣を一つずつ確認します。",
                "tags": ["タロット", "金銭", "見直し"],
                "faq": [
                    {
                        "question": "死神は金銭運の悪化だけを意味しますか？",
                        "answer": "いいえ。終わらせる支出や考え方を見直す文脈で扱います。",
                    }
                ],
                "bodySections": [
                    {
                        "heading": heading,
                        "paragraphs": [
                            "金銭の判断を一つの象徴だけで断定せず、状況と選択肢を分けて確認します。"
                        ],
                    }
                    for heading in outline
                ],
            }
        ]
    }


def _write_ja_partial_generation_04_lineage(
    run_dir: Path,
    *,
    max_repairs: int = 2,
) -> tuple[dict[str, object], dict[str, object], dict[Path, bytes]]:
    brief = load_ja_plan_authority_fixture("brief.json")
    prior = load_ja_plan_authority_fixture("attempt_03_locale_plan.json")
    source_ref_maps = multilingual._request_local_source_ref_maps(brief, prior)
    root_plan = multilingual._hydrate_locale_plan(
        brief,
        fresh_ja_plan_authority_fixture("fixed_current_ref_external_plan.json"),
        generation=3,
        rebuild_by_slot={"article-01": False},
        prior_plan=prior,
        source_ref_maps=source_ref_maps,
    )
    candidate = multilingual._hydrate_candidate(
        brief,
        _ja_external_candidate_from_outline(
            root_plan["articles"][0]["ordered_h2_outline"],
        ),
    )
    review = {
        "schema_version": 1,
        "run_id": brief["run_id"],
        "articles": [
            {
                "article_id": candidate["articles"][0]["article_id"],
                "candidate_sha256": article_sha256(candidate["articles"][0]),
                "verdict": "REJECT",
                "hard_failure": False,
                "findings": [
                    {
                        "code": "NON_NATIVE_SEARCH_INTENT",
                        "message": "synthetic continuation trigger",
                    }
                ],
            }
        ],
    }
    multilingual.pipeline.write_json(run_dir / "brief.json", brief)
    multilingual.pipeline.write_json(run_dir / "candidate.json", candidate)
    multilingual.pipeline.write_json(run_dir / "review.json", review)
    for attempt in range(1, 4):
        attempt_dir = run_dir / "attempts" / f"{attempt:02d}"
        multilingual.pipeline.write_json(
            attempt_dir / "external-review.json",
            {
                "articles": [
                    {
                        "slot": "article-01",
                        "verdict": "REJECT",
                        "findings": [
                            {
                                "code": "NON_NATIVE_SEARCH_INTENT",
                                "message": f"attempt {attempt} still needs native intent",
                            }
                        ],
                    }
                ]
            },
        )
    multilingual.pipeline.write_json(run_dir / "attempts/03/locale-plan.json", prior)
    state = multilingual._load_or_create_continuation_state(
        run_dir,
        brief,
        review,
        max_repairs=max_repairs,
    )
    assert state["status"] == "active"
    assert state["started_after_generation"] == 3
    assert state["semantic_budget"] == max_repairs + 1
    assert state["next_generation"] == 4
    assert state["completed_generations"] == []
    assert state["abandoned_generations"] == []
    generation_dir = run_dir / "generations" / "04"
    multilingual.pipeline.write_json(
        generation_dir / "external-plan.json",
        load_ja_plan_authority_fixture("fixed_current_ref_external_plan.json"),
    )
    multilingual.pipeline.write_json(
        generation_dir / "plan-operation.json",
        {
            "role": "writer",
            "model": "writer-test",
            "status": "success",
            "prompt_sha256": "a" * 64,
        },
    )
    protected_paths = [
        run_dir / "brief.json",
        run_dir / "candidate.json",
        run_dir / "review.json",
        run_dir / "continuation" / "state.json",
        generation_dir / "external-plan.json",
        generation_dir / "plan-operation.json",
    ]
    protected_bytes = {
        path.relative_to(run_dir): path.read_bytes()
        for path in protected_paths
    }
    return candidate, review, protected_bytes


def _write_terminal_rejected_ja_generation(run_dir: Path) -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    brief = load_ja_boundary_fixture("brief.json")
    candidate = load_ja_boundary_fixture("candidate_03.json")
    review = load_ja_boundary_fixture("review_03.json")
    review["articles"][0]["candidate_sha256"] = article_sha256(candidate["articles"][0])
    review["articles"][0]["hard_failure"] = True
    review["articles"][0]["findings"] = [{"code": "BOUNDARY_MEANING_MISSING", "message": "deterministic protected boundary missing"}]
    for name, payload in {"brief.json": brief, "candidate.json": candidate, "review.json": review}.items():
        multilingual.pipeline.write_json(run_dir / name, payload)
    for attempt in range(1, 4):
        multilingual.pipeline.write_json(
            run_dir / "attempts" / f"{attempt:02d}" / "external-review.json",
            {"articles": [{"slot": "article-01", "verdict": "REJECT", "findings": [{"code": "BOUNDARY_MEANING_MISSING", "message": f"attempt {attempt} misses boundary"}]}]},
        )

    state = multilingual._load_or_create_continuation_state(run_dir, brief, review, max_repairs=0)
    prior_plan = multilingual._hydrate_locale_plan(
        brief,
        external_locale_plan(brief),
        generation=3,
        rebuild_by_slot={"article-01": False},
    )
    source_ref_maps = multilingual._request_local_source_ref_maps(brief, prior_plan)
    terminal_plan = multilingual._hydrate_locale_plan(
        brief,
        external_locale_plan_with_source_refs(brief),
        generation=5,
        rebuild_by_slot={"article-01": False},
        prior_plan=prior_plan,
        source_ref_maps=source_ref_maps,
    )
    multilingual.pipeline.write_json(run_dir / "generations/04/partial-generation-decision.json", {"schema_version": 1, "contract": "fixture-abandoned-generation"})
    gen05 = run_dir / "generations" / "05"
    multilingual.pipeline.write_json(gen05 / "source-ref-map.json", multilingual._source_ref_map_artifact(source_ref_maps, generation=5))
    multilingual.pipeline.write_json(gen05 / "locale-plan.json", terminal_plan)
    deterministic_findings = [{"article_id": review["articles"][0]["article_id"], **finding} for finding in review["articles"][0]["findings"]]
    multilingual.pipeline.write_json(gen05 / "deterministic-findings.json", deterministic_findings)
    multilingual.pipeline.write_json(gen05 / "candidate.json", candidate)
    multilingual.pipeline.write_json(gen05 / "review.json", review)

    state.update({"status": "complete", "semantic_budget": 1, "next_generation": 6, "completed_generations": [5], "abandoned_generations": [4], "terminal_candidate_sha256": multilingual._json_sha256(candidate), "terminal_review_sha256": multilingual._json_sha256(review)})
    multilingual.pipeline.write_json(run_dir / "continuation" / "state.json", state)
    return brief, candidate, review, terminal_plan


def _terminal_reject_authority_kwargs(brief: dict[str, object], candidate: dict[str, object], review: dict[str, object], plan: dict[str, object], run_dir: Path) -> dict[str, object]:
    return {
        "expected_run_id": brief["run_id"],
        "terminal_generation": 5,
        "expected_source_sha256": brief["articles"][0]["source_sha256"],
        "expected_locale_plan_sha256": multilingual._json_sha256(plan),
        "expected_source_ref_map_sha256": multilingual._json_sha256(json.loads((run_dir / "generations/05/source-ref-map.json").read_text(encoding="utf-8"))),
        "expected_terminal_candidate_sha256": multilingual._json_sha256(candidate),
        "expected_terminal_review_sha256": multilingual._json_sha256(review),
        "authority_digest": "a" * 64,
    }


class _TerminalRejectFakeClient:
    writer_model = "writer-test"
    reviewer_model = "reviewer-test"

    def generate_json(self, *_args: object) -> dict[str, object]:
        raise AssertionError("fake generation seam must not call provider")


def _write_fake_next_generation(
    run_dir: Path,
    brief: dict[str, object],
    plan: dict[str, object],
    generation: int,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    candidate = load_ja_boundary_fixture("corrected_test_only_candidate.json")
    review = {"schema_version": 1, "run_id": brief["run_id"], "articles": [{"article_id": candidate["articles"][0]["article_id"], "candidate_sha256": article_sha256(candidate["articles"][0]), "verdict": "APPROVE", "hard_failure": False, "findings": []}]}
    next_plan = json.loads(json.dumps(plan))
    next_plan["generation"] = generation
    source_ref_maps = multilingual._request_local_source_ref_maps(brief, plan)
    gen_dir = run_dir / "generations" / f"{generation:02d}"
    multilingual.pipeline.write_json(gen_dir / "source-ref-map.json", multilingual._source_ref_map_artifact(source_ref_maps, generation=generation))
    for name, payload in {"locale-plan.json": next_plan, "deterministic-findings.json": [], "candidate.json": candidate, "review.json": review}.items():
        multilingual.pipeline.write_json(gen_dir / name, payload)
    return candidate, review, next_plan


def _patch_fake_next_generation(monkeypatch: pytest.MonkeyPatch, brief: dict[str, object], plan: dict[str, object], generated: list[int]) -> None:
    def fake_run_locale_generation(
        fixture_brief: dict[str, object],
        _client: object,
        *,
        generation: int,
        generation_dir: Path,
        findings: list[dict[str, str]],
        history: list[list[dict[str, str]]],
        prior_plan: dict[str, object],
    ) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
        assert fixture_brief == brief
        assert generation_dir.name == f"{generation:02d}"
        assert findings and history
        assert prior_plan == plan
        generated.append(generation)
        return _write_fake_next_generation(generation_dir.parents[1], brief, plan, generation)

    monkeypatch.setattr(multilingual, "_run_locale_generation", fake_run_locale_generation)


def test_terminal_reviewer_reject_authority_plan_is_read_only(
    tmp_path: Path,
) -> None:
    brief, candidate, review, plan = _write_terminal_rejected_ja_generation(tmp_path)
    kwargs = _terminal_reject_authority_kwargs(brief, candidate, review, plan, tmp_path)
    protected = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}

    receipt = multilingual.authorize_next_generation_after_reviewer_reject(
        tmp_path,
        **kwargs,
    )

    assert receipt["status"] == "READY_TO_EXECUTE"
    assert receipt["execute"] is False
    assert receipt["from_status"] == "complete"
    assert receipt["to_status"] == "active"
    assert receipt["from_next_generation"] == 6
    assert receipt["to_next_generation"] == 6
    assert receipt["from_semantic_budget"] == 1
    assert receipt["to_semantic_budget"] == 2
    assert not (tmp_path / "generations/06").exists()
    assert not (tmp_path / "continuation/authority-transition-05.json").exists()
    assert protected == {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}


def test_terminal_reviewer_reject_authority_execute_creates_exactly_one_next_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    brief, candidate, review, plan = _write_terminal_rejected_ja_generation(tmp_path)
    kwargs = _terminal_reject_authority_kwargs(brief, candidate, review, plan, tmp_path)
    generated: list[int] = []
    _patch_fake_next_generation(monkeypatch, brief, plan, generated)

    receipt = multilingual.authorize_next_generation_after_reviewer_reject(
        tmp_path,
        execute=True,
        **kwargs,
    )
    crash_window_replay = multilingual.authorize_next_generation_after_reviewer_reject(
        tmp_path,
        execute=True,
        **kwargs,
    )
    candidate_after, review_after = multilingual.continue_writer_reviewer(
        tmp_path,
        _TerminalRejectFakeClient(),
        max_repairs=1,
    )
    with pytest.raises(ValueError, match="authorization already consumed/state progressed"):
        multilingual.authorize_next_generation_after_reviewer_reject(tmp_path, execute=True, **kwargs)

    state = json.loads((tmp_path / "continuation/state.json").read_text())
    transition = json.loads(
        (tmp_path / "continuation/authority-transition-05.json").read_text(
            encoding="utf-8"
        )
    )
    assert receipt["status"] == "AUTHORIZED"
    assert crash_window_replay["status"] == "ALREADY_AUTHORIZED"
    assert transition["action"] == "authorize_next_generation_after_reviewer_reject"
    assert transition["from_status"] == "complete"
    assert transition["to_status"] == "active"
    assert transition["from_semantic_budget"] == 1
    assert transition["to_semantic_budget"] == 2
    assert state["status"] == "complete"
    assert state["completed_generations"] == [5, 6]
    assert state["abandoned_generations"] == [4]
    assert state["next_generation"] == 7
    assert generated == [6]
    assert sorted(path.name for path in (tmp_path / "generations").iterdir()) == ["04", "05", "06"]
    assert review_after["articles"][0]["verdict"] == "APPROVE"


def test_terminal_reviewer_reject_authority_and_continuation_share_run_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    brief, candidate, review, plan = _write_terminal_rejected_ja_generation(tmp_path)
    kwargs = _terminal_reject_authority_kwargs(brief, candidate, review, plan, tmp_path)
    transition_written = threading.Event()
    allow_state_write = threading.Event()
    authorize_done = threading.Event()
    continue_done = threading.Event()
    failures: list[BaseException] = []
    generated: list[int] = []
    original_write_if_same_or_missing = multilingual._write_if_same_or_missing

    def pausing_write_if_same_or_missing(path: Path, payload: dict[str, object]) -> None:
        original_write_if_same_or_missing(path, payload)
        if path.name == "authority-transition-05.json":
            transition_written.set()
            if not allow_state_write.wait(timeout=2):
                raise AssertionError("test did not release authority state write")

    monkeypatch.setattr(
        multilingual,
        "_write_if_same_or_missing",
        pausing_write_if_same_or_missing,
    )
    _patch_fake_next_generation(monkeypatch, brief, plan, generated)

    def authorize_thread() -> None:
        try:
            multilingual.authorize_next_generation_after_reviewer_reject(
                tmp_path,
                execute=True,
                **kwargs,
            )
        except BaseException as error:
            failures.append(error)
        finally:
            authorize_done.set()

    def continue_thread() -> None:
        try:
            multilingual.continue_writer_reviewer(
                tmp_path,
                _TerminalRejectFakeClient(),
                max_repairs=1,
            )
        except BaseException as error:
            failures.append(error)
        finally:
            continue_done.set()

    authority = threading.Thread(target=authorize_thread)
    continuation = threading.Thread(target=continue_thread)
    authority.start()
    assert transition_written.wait(timeout=2)
    continuation.start()
    assert not continue_done.wait(timeout=0.1)
    allow_state_write.set()
    assert authorize_done.wait(timeout=2)
    assert continue_done.wait(timeout=2)
    authority.join(timeout=1)
    continuation.join(timeout=1)

    assert failures == []
    assert generated == [6]
    assert not (tmp_path / "generations/07").exists()


def test_terminal_reviewer_reject_authority_crash_resume_from_transition_only(
    tmp_path: Path,
) -> None:
    brief, candidate, review, plan = _write_terminal_rejected_ja_generation(tmp_path)
    kwargs = _terminal_reject_authority_kwargs(brief, candidate, review, plan, tmp_path)
    plan_receipt = multilingual.authorize_next_generation_after_reviewer_reject(
        tmp_path,
        **kwargs,
    )
    state_before = json.loads((tmp_path / "continuation/state.json").read_text())
    transition = {
        key: value
        for key, value in plan_receipt.items()
        if key not in {"status", "execute"}
    }
    multilingual.pipeline.write_json(
        tmp_path / "continuation/authority-transition-05.json",
        transition,
    )

    receipt = multilingual.authorize_next_generation_after_reviewer_reject(
        tmp_path,
        execute=True,
        **kwargs,
    )

    state_after = json.loads((tmp_path / "continuation/state.json").read_text())
    assert receipt["status"] == "AUTHORIZED"
    assert state_before["status"] == "complete"
    assert state_after == transition["state_after"]
    assert state_after["status"] == "active"
    assert not (tmp_path / "generations/06").exists()


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("state", "authorization already consumed/state progressed"),
        ("receipt", "transition identity differs"),
    ],
)
def test_terminal_reviewer_reject_authority_rejects_transition_residue_drift(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    brief, candidate, review, plan = _write_terminal_rejected_ja_generation(tmp_path)
    kwargs = _terminal_reject_authority_kwargs(brief, candidate, review, plan, tmp_path)
    receipt = multilingual.authorize_next_generation_after_reviewer_reject(tmp_path, execute=mutation == "state", **kwargs)
    if mutation == "state":
        drifted = json.loads((tmp_path / "continuation/state.json").read_text())
        drifted["semantic_budget"] = 3
        multilingual.pipeline.write_json(tmp_path / "continuation/state.json", drifted)
    else:
        transition = {key: value for key, value in receipt.items() if key not in {"status", "execute"}}
        transition["state_after"] = {**transition["state_after"], "semantic_budget": 3}
        multilingual.pipeline.write_json(tmp_path / "continuation/authority-transition-05.json", transition)
    with pytest.raises(ValueError, match=message):
        multilingual.authorize_next_generation_after_reviewer_reject(
            tmp_path,
            execute=True,
            **kwargs,
        )


def test_terminal_reviewer_reject_authority_cli_defaults_to_plan_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    brief, candidate, review, plan = _write_terminal_rejected_ja_generation(tmp_path)
    kwargs = _terminal_reject_authority_kwargs(brief, candidate, review, plan, tmp_path)
    option_values = {"run-dir": tmp_path, "expected-run-id": kwargs["expected_run_id"], "terminal-generation": kwargs["terminal_generation"], "expected-source-sha256": kwargs["expected_source_sha256"], "expected-locale-plan-sha256": kwargs["expected_locale_plan_sha256"], "expected-source-ref-map-sha256": kwargs["expected_source_ref_map_sha256"], "expected-terminal-candidate-sha256": kwargs["expected_terminal_candidate_sha256"], "expected-terminal-review-sha256": kwargs["expected_terminal_review_sha256"], "authority-digest": kwargs["authority_digest"]}
    argv = ["agy_multilingual_pipeline.py", "authorize-next-generation-after-reviewer-reject"]
    for name, value in option_values.items():
        argv.extend([f"--{name}", str(value)])
    monkeypatch.setattr("sys.argv", argv)

    exit_code = multilingual.main()
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["status"] == "READY_TO_EXECUTE"
    assert output["execute"] is False
    assert not (tmp_path / "continuation/authority-transition-05.json").exists()
    assert not (tmp_path / "generations/06").exists()


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("approved_review", "terminal review must be rejected"),
        ("missing_review", "terminal review artifact is missing"),
        ("candidate_hash", "terminal rejected state identity differs"),
        ("existing_next_generation", "authorization already consumed/state progressed"),
        ("file_byte_locale_hash", "terminal generation artifact identity differs"),
        ("root_drift", "identity|terminal root review differs"),
        ("authority_digest", "authority digest is invalid"),
    ],
)
def test_terminal_reviewer_reject_authority_fail_closed(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    brief, candidate, review, plan = _write_terminal_rejected_ja_generation(tmp_path)
    kwargs = _terminal_reject_authority_kwargs(brief, candidate, review, plan, tmp_path)
    if mutation == "approved_review":
        review["articles"][0]["verdict"] = "APPROVE"
        review["articles"][0]["hard_failure"] = False
        review["articles"][0]["findings"] = []
        multilingual.pipeline.write_json(tmp_path / "review.json", review)
        multilingual.pipeline.write_json(tmp_path / "generations/05/review.json", review)
        state = json.loads((tmp_path / "continuation/state.json").read_text())
        state["terminal_review_sha256"] = multilingual._json_sha256(review)
        multilingual.pipeline.write_json(tmp_path / "continuation/state.json", state)
        kwargs["expected_terminal_review_sha256"] = multilingual._json_sha256(review)
    elif mutation == "missing_review":
        (tmp_path / "generations/05/review.json").unlink()
    elif mutation == "candidate_hash":
        kwargs["expected_terminal_candidate_sha256"] = "b" * 64
    elif mutation == "existing_next_generation":
        multilingual.pipeline.write_json(
            tmp_path / "generations/06/candidate.json",
            {"unexpected": True},
        )
    elif mutation == "file_byte_locale_hash":
        plan_path = tmp_path / "generations/05/locale-plan.json"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        kwargs["expected_locale_plan_sha256"] = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    elif mutation == "root_drift":
        drifted = json.loads(json.dumps(review))
        drifted["articles"][0]["findings"][0]["message"] = "root drift"
        multilingual.pipeline.write_json(tmp_path / "review.json", drifted)
    elif mutation == "authority_digest":
        kwargs["authority_digest"] = "not-a-digest"

    with pytest.raises(ValueError, match=message):
        multilingual.authorize_next_generation_after_reviewer_reject(
            tmp_path,
            execute=True,
            **kwargs,
        )


def test_ja_partial_generation_04_missing_source_ref_map_terminalizes_once(
    tmp_path: Path,
) -> None:
    old_candidate, old_review, protected_bytes = _write_ja_partial_generation_04_lineage(
        tmp_path,
    )
    calls: Counter[str] = Counter()

    class FailIfCalled:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def generate_json(
            self,
            role: str,
            _prompt: str,
            _schema: dict[str, object],
        ) -> dict[str, object]:
            calls[role] += 1
            raise AssertionError("partial generation recovery must not call provider")

    outcomes = []
    inventories = []
    for _replay in range(1):
        with pytest.raises(
            multilingual.LocalePlanValidationError,
            match="source ref map missing",
        ):
            multilingual.continue_writer_reviewer(tmp_path, FailIfCalled(), max_repairs=2)
        outcomes.append(
            {
                "state": json.loads(
                    (tmp_path / "continuation/state.json").read_text(encoding="utf-8")
                ),
                "planning_result": json.loads(
                    (tmp_path / "generations/04/planning-result.json").read_text(
                        encoding="utf-8"
                    )
                ),
                "lifecycle": json.loads(
                    (tmp_path / "continuation/generation-lifecycle.json").read_text(
                        encoding="utf-8"
                    )
                ),
                "decision": json.loads(
                    (tmp_path / "generations/04/partial-generation-decision.json").read_text(
                        encoding="utf-8"
                    )
                ),
            }
        )
        inventories.append(
            sorted(
                str(path.relative_to(tmp_path))
                for path in (tmp_path / "generations").rglob("*")
                if path.is_file()
            )
        )

    assert calls == Counter()
    assert sorted(path.name for path in (tmp_path / "generations").iterdir()) == ["04"]
    assert not (tmp_path / "generations/05").exists()
    assert not (tmp_path / "generations/04/source-ref-map.json").exists()
    assert not (tmp_path / "generations/04/locale-plan.json").exists()
    assert not (tmp_path / "generations/04/article-operation.json").exists()
    assert not (tmp_path / "generations/04/review-operation.json").exists()
    assert not (tmp_path / "generations/04/reviewer-operation.json").exists()
    assert json.loads((tmp_path / "candidate.json").read_text()) == old_candidate
    assert json.loads((tmp_path / "review.json").read_text()) == old_review
    assert protected_bytes == {
        path: (tmp_path / path).read_bytes()
        for path in protected_bytes
    }
    assert outcomes[0]["state"]["status"] == "active"
    assert outcomes[0]["state"]["next_generation"] == 4
    assert outcomes[0]["state"]["completed_generations"] == []
    assert outcomes[0]["planning_result"]["planning_contract_status"] == (
        "PLANNING_CONTRACT_FAILURE"
    )
    assert outcomes[0]["lifecycle"]["generations"]["04"]["lifecycle_state"] == (
        "abandoned"
    )
    assert outcomes[0]["lifecycle"]["generations"]["04"]["decision"] == "terminalize"
    assert outcomes[0]["decision"]["committed"] is False
    assert outcomes[0]["decision"]["resumable"] is False


def test_ja_partial_generation_04_terminal_decision_advances_authority_once(
    tmp_path: Path,
) -> None:
    _old_candidate, _old_review, protected_bytes = _write_ja_partial_generation_04_lineage(
        tmp_path,
    )

    class FailIfCalled:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def generate_json(
            self,
            _role: str,
            _prompt: str,
            _schema: dict[str, object],
        ) -> dict[str, object]:
            raise AssertionError("terminal recovery must not call provider")

    with pytest.raises(
        multilingual.LocalePlanValidationError,
        match="source ref map missing",
    ):
        multilingual.continue_writer_reviewer(tmp_path, FailIfCalled(), max_repairs=2)

    gen04_audit_bytes = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in [
            tmp_path / "generations/04/external-plan.json",
            tmp_path / "generations/04/plan-operation.json",
            tmp_path / "generations/04/partial-generation-decision.json",
            tmp_path / "generations/04/planning-result.json",
        ]
    }
    with pytest.raises(
        multilingual.LocalePlanValidationError,
        match="retry continuation from generation 05",
    ):
        multilingual.continue_writer_reviewer(tmp_path, FailIfCalled(), max_repairs=2)
    first_state = json.loads(
        (tmp_path / "continuation/state.json").read_text(encoding="utf-8")
    )
    transition_receipt = json.loads(
        (tmp_path / "continuation/authority-transition-04.json").read_text(
            encoding="utf-8"
        )
    )
    transition_bytes = (
        tmp_path / "continuation/authority-transition-04.json"
    ).read_bytes()

    second_transition = multilingual._consume_partial_generation_terminalization(
        tmp_path,
        json.loads((tmp_path / "brief.json").read_text(encoding="utf-8")),
        json.loads((tmp_path / "continuation/state.json").read_text(encoding="utf-8")),
    )
    second_state = json.loads(
        (tmp_path / "continuation/state.json").read_text(encoding="utf-8")
    )

    assert second_transition is False
    assert first_state == second_state
    assert first_state["status"] == "active"
    assert first_state["completed_generations"] == []
    assert first_state["abandoned_generations"] == [4]
    assert first_state["next_generation"] == 5
    assert transition_receipt["from_next_generation"] == 4
    assert transition_receipt["to_next_generation"] == 5
    assert transition_receipt["abandoned_generations"] == [4]
    assert transition_receipt["action"] == "advance_after_terminalized_partial"
    assert (
        tmp_path / "continuation/authority-transition-04.json"
    ).read_bytes() == transition_bytes
    assert gen04_audit_bytes == {
        path: (tmp_path / path).read_bytes()
        for path in gen04_audit_bytes
    }
    protected_without_state = {
        path: payload
        for path, payload in protected_bytes.items()
        if path != Path("continuation/state.json")
    }
    assert protected_without_state == {
        path: (tmp_path / path).read_bytes()
        for path in protected_without_state
    }
    assert not (tmp_path / "generations/05").exists()
    assert not (tmp_path / "generations/04/source-ref-map.json").exists()
    assert not (tmp_path / "generations/04/locale-plan.json").exists()
    assert not (tmp_path / "generations/04/article-operation.json").exists()
    assert not (tmp_path / "generations/04/reviewer-operation.json").exists()


@pytest.mark.parametrize("snapshot_name", ["fresh-a", "fresh-b"])
def test_ja_partial_generation_04_abandoned_allocation_preserves_semantic_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    snapshot_name: str,
) -> None:
    run_dir = tmp_path / snapshot_name
    _old_candidate, _old_review, protected_bytes = _write_ja_partial_generation_04_lineage(
        run_dir,
        max_repairs=0,
    )
    provider_calls: Counter[str] = Counter()

    class FailIfCalled:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def generate_json(
            self,
            role: str,
            _prompt: str,
            _schema: dict[str, object],
        ) -> dict[str, object]:
            provider_calls[role] += 1
            raise AssertionError("semantic budget fixture must not call provider")

    with pytest.raises(
        multilingual.LocalePlanValidationError,
        match="source ref map missing",
    ):
        multilingual.continue_writer_reviewer(run_dir, FailIfCalled(), max_repairs=0)

    pre_transition_state = json.loads(
        (run_dir / "continuation/state.json").read_text(encoding="utf-8")
    )
    assert pre_transition_state["next_generation"] == 4
    assert pre_transition_state["semantic_budget"] == 1
    assert pre_transition_state["completed_generations"] == []
    assert pre_transition_state["abandoned_generations"] == []
    assert provider_calls == Counter()

    gen04_audit_bytes = {
        path.relative_to(run_dir): path.read_bytes()
        for path in [
            run_dir / "generations/04/external-plan.json",
            run_dir / "generations/04/plan-operation.json",
            run_dir / "generations/04/partial-generation-decision.json",
            run_dir / "generations/04/planning-result.json",
        ]
    }
    with pytest.raises(
        multilingual.LocalePlanValidationError,
        match="retry continuation from generation 05",
    ):
        multilingual.continue_writer_reviewer(run_dir, FailIfCalled(), max_repairs=0)

    transition_path = run_dir / "continuation/authority-transition-04.json"
    transition_hash = hashlib.sha256(transition_path.read_bytes()).hexdigest()
    state_after_transition = json.loads(
        (run_dir / "continuation/state.json").read_text(encoding="utf-8")
    )
    transition = json.loads(transition_path.read_text(encoding="utf-8"))
    assert state_after_transition["next_generation"] == 5
    assert state_after_transition["semantic_budget"] == 1
    assert state_after_transition["completed_generations"] == []
    assert state_after_transition["abandoned_generations"] == [4]
    assert transition["from_next_generation"] == 4
    assert transition["to_next_generation"] == 5
    assert transition["abandoned_generations"] == [4]
    assert provider_calls == Counter()

    second_transition = multilingual._consume_partial_generation_terminalization(
        run_dir,
        json.loads((run_dir / "brief.json").read_text(encoding="utf-8")),
        json.loads((run_dir / "continuation/state.json").read_text(encoding="utf-8")),
    )
    assert second_transition is False
    assert hashlib.sha256(transition_path.read_bytes()).hexdigest() == transition_hash

    targeted_generations: list[int] = []

    def intercept_locale_generation(
        _brief: dict[str, object],
        _client: object,
        *,
        generation: int,
        generation_dir: Path,
        findings: list[dict[str, str]],
        history: list[list[dict[str, str]]],
        prior_plan: dict[str, object],
    ) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
        assert findings
        assert history
        assert prior_plan
        targeted_generations.append(generation)
        assert generation_dir == run_dir / "generations" / "05"
        raise RuntimeError("intercepted deterministic gen05 semantic attempt")

    monkeypatch.setattr(
        multilingual,
        "_run_locale_generation",
        intercept_locale_generation,
    )
    with pytest.raises(
        RuntimeError,
        match="intercepted deterministic gen05 semantic attempt",
    ):
        multilingual.continue_writer_reviewer(run_dir, FailIfCalled(), max_repairs=0)

    assert targeted_generations == [5]
    assert provider_calls == Counter()
    assert gen04_audit_bytes == {
        path: (run_dir / path).read_bytes()
        for path in gen04_audit_bytes
    }
    protected_without_state = {
        path: payload
        for path, payload in protected_bytes.items()
        if path != Path("continuation/state.json")
    }
    assert protected_without_state == {
        path: (run_dir / path).read_bytes()
        for path in protected_without_state
    }
    assert not (run_dir / "generations/05").exists()


def test_deferred_lineage_continuation_is_incremental_immutable_and_replayable(
    tmp_path: Path,
) -> None:
    old_candidate, _old_review = _write_rejected_deferred_lineage(tmp_path)
    legacy_bytes = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in (tmp_path / "attempts").rglob("*")
        if path.is_file()
    }
    calls: list[str] = []
    last_outline: list[str] | None = None

    class ApprovingClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def generate_json(
            self,
            role: str,
            _prompt: str,
            schema: dict[str, object],
        ) -> dict[str, object]:
            nonlocal last_outline
            calls.append(role)
            if "native_search_intent" in json.dumps(schema):
                payload = external_locale_plan(
                    non_tarot_translation_brief(),
                    rebuild_outline=True,
                    coverage_shift=1,
                    outline=[
                        "용신 검색 질문부터 정리하기",
                        "명식의 강약과 계절 확인하기",
                        "오행의 흐름으로 후보 비교하기",
                        "조건에 따라 결론을 제한하기",
                    ],
                )
                last_outline = payload["articles"][0]["ordered_h2_outline"]
                return payload
            if role == "writer":
                return non_tarot_external_candidate(last_outline)
            return {
                "articles": [
                    {
                        "slot": "article-01",
                        "verdict": "APPROVE",
                        "findings": [],
                    }
                ]
            }

    candidate, review = multilingual.continue_writer_reviewer(
        tmp_path,
        ApprovingClient(),
        max_repairs=2,
    )

    state = json.loads((tmp_path / "continuation/state.json").read_text())
    assert state["status"] == "complete"
    assert not (tmp_path / "continuation/root-update.json").exists()
    assert state["started_after_generation"] == 3
    assert state["completed_generations"] == [4]
    assert (tmp_path / "generations/04/locale-plan.json").is_file()
    assert candidate["run_id"] == old_candidate["run_id"]
    assert review["run_id"] == old_candidate["run_id"]
    assert review["articles"][0]["verdict"] == "APPROVE"
    assert not (tmp_path / "approval.json").exists()
    assert not (tmp_path / "run-evidence.json").exists()
    assert legacy_bytes == {
        path.relative_to(tmp_path): path.read_bytes()
        for path in (tmp_path / "attempts").rglob("*")
        if path.is_file()
    }

    class FailIfCalled:
        def generate_json(self, *_args: object) -> dict[str, object]:
            raise AssertionError("completed continuation must replay root artifacts")

    replayed_candidate, replayed_review = multilingual.continue_writer_reviewer(
        tmp_path,
        FailIfCalled(),
        max_repairs=2,
    )
    assert replayed_candidate == candidate
    assert replayed_review == review
    assert calls == ["writer", "writer", "reviewer"]


def test_first_continuation_generation_uses_root_review_as_final_authority(
    tmp_path: Path,
) -> None:
    _candidate, review = _write_rejected_deferred_lineage(tmp_path)
    review["articles"][0]["findings"] = [
        {
            "code": "NON_NATIVE_SEARCH_INTENT",
            "message": "ROOT-REVIEW-AUTHORITY-MARKER",
        }
    ]
    multilingual.pipeline.write_json(tmp_path / "review.json", review)
    prompts: list[str] = []

    class CaptureClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def generate_json(
            self,
            _role: str,
            prompt: str,
            _schema: dict[str, object],
        ) -> dict[str, object]:
            prompts.append(prompt)
            raise RuntimeError("capture only")

    with pytest.raises(RuntimeError, match="capture only"):
        multilingual.continue_writer_reviewer(tmp_path, CaptureClient(), max_repairs=2)

    assert prompts
    assert "ROOT-REVIEW-AUTHORITY-MARKER" in prompts[0]


def test_continuation_state_rejects_attempt_generation_gap(tmp_path: Path) -> None:
    _candidate, review = _write_rejected_deferred_lineage(tmp_path)
    (tmp_path / "attempts/02").rename(tmp_path / "attempts/04")

    with pytest.raises(ValueError, match="generation|contiguous|lineage"):
        multilingual._load_or_create_continuation_state(
            tmp_path,
            non_tarot_translation_brief(),
            review,
            max_repairs=2,
        )


def test_pending_continuation_does_not_advance_or_overwrite_roots(tmp_path: Path) -> None:
    old_candidate, old_review = _write_rejected_deferred_lineage(tmp_path)
    prompts: list[str] = []

    class ExternalJobPending(RuntimeError):
        pass

    class PendingClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def _outbox_transport(self) -> None:
            raise AssertionError

        transport = _outbox_transport

        def generate_json(
            self,
            _role: str,
            prompt: str,
            _schema: dict[str, object],
        ) -> dict[str, object]:
            prompts.append(prompt)
            raise ExternalJobPending("synthetic pending plan")

    client = PendingClient()
    for _replay in range(2):
        with pytest.raises(ExternalJobPending, match="synthetic pending plan"):
            multilingual.continue_writer_reviewer(tmp_path, client, max_repairs=2)

    state = json.loads((tmp_path / "continuation/state.json").read_text())
    assert state["status"] == "active"
    assert state["next_generation"] == 4
    assert state["completed_generations"] == []
    assert sorted(path.name for path in (tmp_path / "generations").iterdir()) == ["04"]
    assert json.loads((tmp_path / "candidate.json").read_text()) == old_candidate
    assert json.loads((tmp_path / "review.json").read_text()) == old_review
    assert prompts[0] == prompts[1]
    for forbidden in ("approval.json", "apply.json", "publish.json", "run-evidence.json"):
        assert not (tmp_path / forbidden).exists()


def test_pending_continuation_article_reuses_plan_and_request_identity(
    tmp_path: Path,
) -> None:
    old_candidate, old_review = _write_rejected_deferred_lineage(tmp_path)
    brief = non_tarot_translation_brief()
    calls: list[tuple[str, str]] = []

    class ExternalJobPending(RuntimeError):
        pass

    class PendingArticleClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def _outbox_transport(self) -> None:
            raise AssertionError("transport marker only")

        transport = _outbox_transport

        def generate_json(
            self,
            role: str,
            prompt: str,
            schema: dict[str, object],
        ) -> dict[str, object]:
            calls.append((role, prompt))
            if "native_search_intent" in json.dumps(schema):
                return external_locale_plan(
                    brief,
                    rebuild_outline=True,
                    coverage_shift=1,
                    outline=[
                        "용신 검색 질문부터 정리하기",
                        "명식의 강약과 계절 확인하기",
                        "오행의 흐름으로 후보 비교하기",
                        "조건에 따라 결론을 제한하기",
                    ],
                )
            raise ExternalJobPending("synthetic pending article")

    client = PendingArticleClient()
    for _replay in range(2):
        with pytest.raises(ExternalJobPending, match="pending article"):
            multilingual.continue_writer_reviewer(tmp_path, client, max_repairs=2)

    article_prompts = [prompt for role, prompt in calls if role == "writer"][1:]
    assert len(calls) == 3
    assert article_prompts[0] == article_prompts[1]
    assert json.loads((tmp_path / "candidate.json").read_text()) == old_candidate
    assert json.loads((tmp_path / "review.json").read_text()) == old_review


def test_later_generation_plan_pending_reuses_prompt_and_operation_identity(
    tmp_path: Path,
) -> None:
    old_candidate, old_review = _write_rejected_deferred_lineage(tmp_path)
    brief = non_tarot_translation_brief()
    plan_calls = 0
    last_outline: list[str] | None = None
    pending_prompts: list[str] = []

    class ExternalJobPending(RuntimeError):
        pass

    class LaterPlanPendingClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def _outbox_transport(self) -> None:
            raise AssertionError("transport marker only")

        transport = _outbox_transport

        def generate_json(
            self,
            role: str,
            prompt: str,
            schema: dict[str, object],
        ) -> dict[str, object]:
            nonlocal plan_calls, last_outline
            if "native_search_intent" in json.dumps(schema):
                plan_calls += 1
                if plan_calls == 1:
                    payload = external_locale_plan(
                        brief,
                        rebuild_outline=True,
                        coverage_shift=1,
                        outline=[
                            "용신 검색 질문부터 정리하기",
                            "명식의 강약과 계절 확인하기",
                            "오행의 흐름으로 후보 비교하기",
                            "조건에 따라 결론을 제한하기",
                        ],
                    )
                    last_outline = payload["articles"][0]["ordered_h2_outline"]
                    return payload
                pending_prompts.append(prompt)
                raise ExternalJobPending("synthetic later plan pending")
            if role == "writer":
                return non_tarot_external_candidate(last_outline)
            return {
                "articles": [
                    {
                        "slot": "article-01",
                        "verdict": "REJECT",
                        "findings": [
                            {
                                "code": "AI_TEMPLATE_STYLE",
                                "message": "still repeats the template",
                            }
                        ],
                    }
                ]
            }

    client = LaterPlanPendingClient()
    for _replay in range(2):
        with pytest.raises(ExternalJobPending, match="later plan pending"):
            multilingual.continue_writer_reviewer(tmp_path, client, max_repairs=2)

    prompt_hashes = [
        hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        for prompt in pending_prompts
    ]
    assert len(pending_prompts) == 2
    assert pending_prompts[0] == pending_prompts[1], prompt_hashes
    receipt = json.loads(
        (tmp_path / "generations/05/plan-operation.json").read_text()
    )
    assert receipt["prompt_sha256"] == prompt_hashes[0]
    assert len(list((tmp_path / "generations/05").glob("plan-operation*.json"))) == 1
    assert not (tmp_path / "generations/05/external-plan.json").exists()
    assert json.loads((tmp_path / "candidate.json").read_text()) == old_candidate
    assert json.loads((tmp_path / "review.json").read_text()) == old_review
    state = json.loads((tmp_path / "continuation/state.json").read_text())
    assert state["completed_generations"] == [4]
    assert state["next_generation"] == 5


def test_root_update_transaction_recovers_candidate_review_and_state_together(
    tmp_path: Path,
) -> None:
    _old_candidate, old_review = _write_rejected_deferred_lineage(tmp_path)
    brief = non_tarot_translation_brief()
    new_candidate = multilingual._hydrate_candidate(
        brief,
        non_tarot_external_candidate(),
    )
    new_review = {
        "schema_version": 1,
        "run_id": brief["run_id"],
        "articles": [
            {
                "article_id": "FORTUNE-0039:ko",
                "candidate_sha256": article_sha256(new_candidate["articles"][0]),
                "verdict": "APPROVE",
                "findings": [],
            }
        ],
    }
    state = multilingual._load_or_create_continuation_state(
        tmp_path,
        brief,
        old_review,
        max_repairs=2,
    )
    state["status"] = "complete"
    state["terminal_candidate_sha256"] = multilingual._json_sha256(new_candidate)
    state["terminal_review_sha256"] = multilingual._json_sha256(new_review)
    multilingual.pipeline.write_json(
        tmp_path / "continuation/root-update.json",
        {
            "schema_version": 1,
            "candidate": new_candidate,
            "review": new_review,
            "state": state,
        },
    )
    multilingual.pipeline.write_json(
        tmp_path / "candidate.json",
        {"interrupted": True},
    )

    multilingual._recover_root_result(tmp_path)

    assert json.loads((tmp_path / "candidate.json").read_text()) == new_candidate
    assert json.loads((tmp_path / "review.json").read_text()) == new_review
    assert json.loads((tmp_path / "continuation/state.json").read_text()) == state
    assert not (tmp_path / "continuation/root-update.json").exists()


def test_complete_continuation_replay_rejects_terminal_root_drift(
    tmp_path: Path,
) -> None:
    candidate, review = _write_rejected_deferred_lineage(tmp_path)
    brief = non_tarot_translation_brief()
    state = multilingual._load_or_create_continuation_state(
        tmp_path,
        brief,
        review,
        max_repairs=2,
    )
    state["status"] = "complete"
    multilingual._write_root_result(tmp_path, candidate, review, state=state)

    drifted_candidate = json.loads(json.dumps(candidate))
    drifted_candidate["articles"][0]["title"] += " drift"
    drifted_review = json.loads(json.dumps(review))
    drifted_review["articles"][0]["candidate_sha256"] = article_sha256(
        drifted_candidate["articles"][0]
    )
    multilingual.pipeline.write_json(tmp_path / "candidate.json", drifted_candidate)
    multilingual.pipeline.write_json(tmp_path / "review.json", drifted_review)

    class FailIfCalled:
        def generate_json(self, *_args: object) -> dict[str, object]:
            raise AssertionError("complete replay must not call provider")

    with pytest.raises(ValueError, match="identity"):
        multilingual.continue_writer_reviewer(tmp_path, FailIfCalled(), max_repairs=2)


def test_korean_typography_normalizes_fullwidth_western_punctuation() -> None:
    value = {
        "title": "타로란 무엇인가요？",
        "faq": [{"question": "미래를 알 수 있나요？", "answer": "아니요！"}],
    }

    normalized = multilingual._normalize_korean_typography(value)

    assert normalized == {
        "title": "타로란 무엇인가요?",
        "faq": [{"question": "미래를 알 수 있나요?", "answer": "아니요!"}],
    }


def test_external_operation_resumes_from_saved_output_without_regeneration(tmp_path: Path) -> None:
    output = tmp_path / "external-candidate.json"
    output.write_text('{"articles":[]}', encoding="utf-8")

    class FailIfCalled:
        def generate_json(self, *_args: object) -> dict[str, object]:
            raise AssertionError("saved operation must not run again")

    payload = multilingual._load_or_generate_external(
        FailIfCalled(),
        "writer",
        "prompt",
        {"type": "object"},
        tmp_path / "writer-operation.json",
        output,
    )

    assert payload == {"articles": []}


def test_translation_brief_validator_keeps_canonical_four_field_contract() -> None:
    multilingual.validate_translation_brief(translation_brief("ja"))

    with pytest.raises(ValueError, match="translation brief fields are strict"):
        multilingual.validate_translation_brief(legacy_rewrite_translation_brief("ja"))


@pytest.mark.parametrize("locale", ["en", "ja", "ko"])
def test_registered_legacy_rewrite_brief_normalizes_before_first_writer_outbox(
    tmp_path: Path,
    locale: str,
) -> None:
    _queue_root, run_dir, _brief = _registered_legacy_rewrite_run(
        tmp_path,
        locale,
    )
    outbox_root = tmp_path / f"outbox-{locale}"
    client = _outbox_client(outbox_root, namespace=f"legacy-{locale}")

    for _replay in range(2):
        with pytest.raises(ExternalJobPending):
            multilingual.run_writer_reviewer(run_dir, client, max_repairs=0)

    outbox_jobs = list((outbox_root / "outbox").glob("*.json"))
    assert len(outbox_jobs) == 1
    receipt = json.loads(
        (run_dir / "attempts" / "01" / "plan-operation.json").read_text()
    )
    assert receipt["status"] == "pending"
    assert receipt["error_type"] == "ExternalJobPending"
    assert not (run_dir / "candidate.json").exists()
    assert not (run_dir / "review.json").exists()


def test_canonical_translation_brief_still_reaches_first_writer_outbox(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "canonical-run"
    multilingual.pipeline.write_json(run_dir / "brief.json", translation_brief("ja"))
    outbox_root = tmp_path / "outbox"

    with pytest.raises(ExternalJobPending):
        multilingual.run_writer_reviewer(
            run_dir,
            _outbox_client(outbox_root, namespace="canonical-ja"),
            max_repairs=0,
        )

    assert len(list((outbox_root / "outbox").glob("*.json"))) == 1


@pytest.mark.parametrize("extra_key", ["unexpected", "source_commit"])
def test_registered_legacy_rewrite_brief_rejects_unknown_extra_without_outbox(
    tmp_path: Path,
    extra_key: str,
) -> None:
    brief = legacy_rewrite_translation_brief("ja")
    brief[extra_key] = "legacy value"
    _queue_root, run_dir, _brief = _registered_legacy_rewrite_run(
        tmp_path,
        "ja",
        brief=brief,
    )
    outbox_root = tmp_path / "outbox"

    with pytest.raises(ValueError, match="translation brief fields are strict"):
        multilingual.run_writer_reviewer(
            run_dir,
            _outbox_client(outbox_root),
            max_repairs=0,
        )

    assert not (outbox_root / "outbox").exists()


@pytest.mark.parametrize("brief_lane", ["new", "rewrite", "i18n-new", "not-a-lane"])
def test_registered_legacy_rewrite_brief_rejects_lane_mismatch_without_outbox(
    tmp_path: Path,
    brief_lane: str,
) -> None:
    brief = legacy_rewrite_translation_brief("ja")
    brief["lane"] = brief_lane
    _queue_root, run_dir, _brief = _registered_legacy_rewrite_run(
        tmp_path,
        "ja",
        brief=brief,
    )
    outbox_root = tmp_path / "outbox"

    with pytest.raises(ValueError, match="legacy translation brief lane"):
        multilingual.run_writer_reviewer(
            run_dir,
            _outbox_client(outbox_root),
            max_repairs=0,
        )

    assert not (outbox_root / "outbox").exists()


def test_registered_legacy_rewrite_brief_rejects_state_lane_mismatch_without_outbox(
    tmp_path: Path,
) -> None:
    _queue_root, run_dir, _brief = _registered_legacy_rewrite_run(
        tmp_path,
        "ja",
        lane="i18n-new",
    )
    outbox_root = tmp_path / "outbox"

    with pytest.raises(ValueError, match="legacy translation brief lane"):
        multilingual.run_writer_reviewer(
            run_dir,
            _outbox_client(outbox_root),
            max_repairs=0,
        )

    assert not (outbox_root / "outbox").exists()


def test_registered_legacy_rewrite_brief_rejects_non_string_lane_without_outbox(
    tmp_path: Path,
) -> None:
    brief = legacy_rewrite_translation_brief("ja")
    brief["lane"] = 7
    _queue_root, run_dir, _brief = _registered_legacy_rewrite_run(
        tmp_path,
        "ja",
        brief=brief,
    )
    outbox_root = tmp_path / "outbox"

    with pytest.raises(ValueError, match="legacy translation brief lane"):
        multilingual.run_writer_reviewer(
            run_dir,
            _outbox_client(outbox_root),
            max_repairs=0,
        )

    assert not (outbox_root / "outbox").exists()


@pytest.mark.parametrize(
    "mutate,match",
    [
        (lambda brief: brief.pop("mode"), "translation brief fields are strict"),
        (lambda brief: brief.__setitem__("schema_version", "1"), "translation brief identity is invalid"),
        (lambda brief: brief.__setitem__("articles", []), "legacy translation brief identity is invalid"),
    ],
)
def test_registered_legacy_rewrite_brief_preserves_strict_canonical_validation(
    tmp_path: Path,
    mutate: object,
    match: str,
) -> None:
    brief = legacy_rewrite_translation_brief("ja")
    mutate(brief)
    _queue_root, run_dir, _brief = _registered_legacy_rewrite_run(
        tmp_path,
        "ja",
        brief=brief,
    )
    outbox_root = tmp_path / "outbox"

    with pytest.raises(ValueError, match=match):
        multilingual.run_writer_reviewer(
            run_dir,
            _outbox_client(outbox_root),
            max_repairs=0,
        )

    assert not (outbox_root / "outbox").exists()


def test_transport_failure_does_not_advance_translation_semantic_attempt(
    tmp_path: Path,
) -> None:
    brief = translation_brief("en")
    multilingual.pipeline.write_json(tmp_path / "brief.json", brief)

    class FailedTransportClient:
        writer_model = "writer-test"
        reviewer_model = "reviewer-test"

        def generate_json(
            self,
            _role: str,
            _prompt: str,
            _schema: dict[str, object],
        ) -> dict[str, object]:
            failure = RuntimeError("closed synthetic transport failure")
            failure.failure_category = "NETWORK"  # type: ignore[attr-defined]
            failure.transport_attempts = 3  # type: ignore[attr-defined]
            failure.request_sha256 = "a" * 64  # type: ignore[attr-defined]
            raise failure

    with pytest.raises(RuntimeError, match="closed synthetic transport failure"):
        multilingual.run_writer_reviewer(
            tmp_path,
            FailedTransportClient(),
            max_repairs=2,
        )

    receipt = json.loads(
        (tmp_path / "attempts/01/plan-operation.json").read_text()
    )
    assert receipt["failure_category"] == "NETWORK"
    assert receipt["transport_attempts"] == 3
    assert receipt["request_sha256"] == "a" * 64
    assert not (tmp_path / "attempts/02").exists()
    for forbidden in ("candidate.json", "review.json", "approval.json", "run-evidence.json"):
        assert not (tmp_path / forbidden).exists()


def test_edited_candidate_uses_deterministic_gate_and_independent_reviewer(tmp_path: Path) -> None:
    brief = translation_brief("en")
    candidate = translation_candidate("en")
    multilingual.pipeline.write_json(tmp_path / "brief.json", brief)
    multilingual.pipeline.write_json(tmp_path / "candidate.json", candidate)

    class ReviewerClient:
        reviewer_model = "reviewer-test"

        def generate_json(self, role: str, _prompt: str, _schema: dict[str, object]) -> dict[str, object]:
            assert role == "reviewer"
            return {"articles": [{"slot": "article-01", "verdict": "APPROVE", "findings": []}]}

    review = multilingual.review_edited_candidate(tmp_path, ReviewerClient())

    assert review["articles"][0]["verdict"] == "APPROVE"
    assert (tmp_path / "editorial-review" / "deterministic-findings.json").read_text() == "[]\n"
    assert (tmp_path / "review.json").is_file()


def test_apply_approved_translation_writes_run_module_and_manifest(tmp_path: Path) -> None:
    static = tmp_path / "app" / "web" / "static"
    static.mkdir(parents=True)
    manifest = static / "article-locales.js"
    manifest.write_text(
        "export const ARTICLE_LOCALE_REGISTRY = [\n];\n",
        encoding="utf-8",
    )
    brief = translation_brief("en")
    candidate = translation_candidate("en")
    article = candidate["articles"][0]
    review = {
        "schema_version": 1,
        "run_id": candidate["run_id"],
        "articles": [
            {
                "article_id": article["article_id"],
                "candidate_sha256": article_sha256(article),
                "verdict": "APPROVE",
                "hard_failure": False,
                "findings": [],
            }
        ],
    }
    approval = build_approval(
        str(candidate["run_id"]),
        candidate["articles"],
        review,
        {str(article["article_id"]): "APPROVE"},
        "test",
    )

    changed = multilingual.apply_approved_translations(
        tmp_path,
        str(candidate["run_id"]),
        brief,
        candidate,
        review,
        approval,
        source_loader=lambda _repo, _article_id: source_article(),
    )

    module = static / "article-locale-translate-test-en.js"
    assert module in changed
    assert module.exists()
    module_text = module.read_text(encoding="utf-8")
    assert '"locale": "en"' in module_text
    assert '"articleId": "TEST-001"' in module_text
    manifest_text = manifest.read_text(encoding="utf-8")
    assert 'from "./article-locale-translate-test-en.js?v=translate-test-en"' in manifest_text
    assert "...TRANSLATE_TEST_EN_ARTICLE_LOCALES" in manifest_text


def test_apply_translation_fails_closed_when_source_changed(tmp_path: Path) -> None:
    static = tmp_path / "app" / "web" / "static"
    static.mkdir(parents=True)
    (static / "article-locales.js").write_text("export const ARTICLE_LOCALE_REGISTRY = [\n];\n", encoding="utf-8")
    brief = translation_brief()
    candidate = translation_candidate()
    article = candidate["articles"][0]
    review = {
        "schema_version": 1,
        "run_id": candidate["run_id"],
        "articles": [
            {
                "article_id": article["article_id"],
                "candidate_sha256": article_sha256(article),
                "verdict": "APPROVE",
                "hard_failure": False,
                "findings": [],
            }
        ],
    }
    approval = build_approval(
        str(candidate["run_id"]),
        candidate["articles"],
        review,
        {str(article["article_id"]): "APPROVE"},
        "test",
    )
    changed_source = source_article()
    changed_source["title"] = "原文後來改過"

    with pytest.raises(ValueError, match="source drift"):
        multilingual.apply_approved_translations(
            tmp_path,
            str(candidate["run_id"]),
            brief,
            candidate,
            review,
            approval,
            source_loader=lambda _repo, _article_id: changed_source,
        )


def test_enqueue_article_translations_creates_three_independent_idempotent_runs(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"

    first = multilingual.enqueue_article_translations(
        tmp_path,
        queue_root,
        source_run_id="source-run-001",
        article_id="TEST-001",
        lane="i18n-new",
        source_loader=lambda _repo, _article_id: source_article(),
    )
    second = multilingual.enqueue_article_translations(
        tmp_path,
        queue_root,
        source_run_id="source-run-001",
        article_id="TEST-001",
        lane="i18n-new",
        source_loader=lambda _repo, _article_id: source_article(),
    )

    assert first == second
    assert {item["locale"] for item in first} == {"en", "ja", "ko"}
    assert len(list((queue_root / "runs").glob("*.json"))) == 3
    for item in first:
        brief = json.loads((Path(item["run_dir"]) / "brief.json").read_text(encoding="utf-8"))
        assert brief["mode"] == "translate_existing"
        assert len(brief["articles"]) == 1
        assert brief["articles"][0]["locale"] == item["locale"]


def test_enqueue_article_translations_can_register_only_one_specified_ja_run(
    tmp_path: Path,
) -> None:
    queue_root = tmp_path / "queue"

    records = multilingual.enqueue_article_translations(
        tmp_path,
        queue_root,
        source_run_id="source-run-001",
        article_id="TEST-001",
        locales=["ja"],
        lane="i18n-new",
        source_loader=lambda _repo, _article_id: source_article(),
    )

    assert len(records) == 1
    assert records[0]["locale"] == "ja"
    assert len(list((queue_root / "runs").glob("*.json"))) == 1
    state = json.loads(next((queue_root / "runs").glob("*.json")).read_text())
    assert state["run_id"] == records[0]["run_id"]
    assert state["status"] == "active"
    brief = json.loads((Path(records[0]["run_dir"]) / "brief.json").read_text())
    assert [article["locale"] for article in brief["articles"]] == ["ja"]


def test_enqueue_article_translations_requires_lane_before_active_state_write(
    tmp_path: Path,
) -> None:
    queue_root = tmp_path / "queue"

    with pytest.raises(TypeError, match="lane"):
        multilingual.enqueue_article_translations(
            tmp_path,
            queue_root,
            source_run_id="source-run-001",
            article_id="TEST-001",
            locales=["ja"],
            source_loader=lambda _repo, _article_id: source_article(),
        )

    assert not queue_root.exists()


def test_enqueue_article_translations_writes_active_identity_envelope(
    tmp_path: Path,
) -> None:
    queue_root = tmp_path / "queue"

    records = multilingual.enqueue_article_translations(
        tmp_path,
        queue_root,
        source_run_id="source-run-001",
        article_id="TEST-001",
        locales=["ja"],
        lane="i18n-new",
        source_loader=lambda _repo, _article_id: source_article(),
    )

    state_path = next((queue_root / "runs").glob("*.json"))
    state = json.loads(state_path.read_text())
    state_bytes = state_path.read_bytes()
    second = multilingual.enqueue_article_translations(
        tmp_path,
        queue_root,
        source_run_id="source-run-001",
        article_id="TEST-001",
        locales=["ja"],
        lane="i18n-new",
        source_loader=lambda _repo, _article_id: source_article(),
    )
    envelope = state["identity_envelope"]
    expected_identity = {
        "schema_version": 1,
        "mode": "translate_existing",
        "lane": "i18n-new",
        "article_ids": ["TEST-001"],
    }
    expected_digest = hashlib.sha256(
        json.dumps(
            expected_identity,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    assert records[0]["locale"] == "ja"
    assert state["run_id"] == records[0]["run_id"]
    assert state["status"] == "active"
    assert state["lane"] == "i18n-new"
    assert envelope == {**expected_identity, "digest": expected_digest}
    assert second == records
    assert state_path.read_bytes() == state_bytes


def test_legacy_rewrite_source_is_seeded_once_and_terminal_locale_stays_ineligible(
    tmp_path: Path,
) -> None:
    queue_root = tmp_path / "queue"
    first = multilingual.enqueue_article_translations(
        tmp_path,
        queue_root,
        source_run_id="legacy-rewrite-fortune-0039",
        article_id="TEST-001",
        lane="i18n-rewrite",
        source_loader=lambda _repo, _article_id: source_article(),
    )
    korean_run_id = next(
        item["run_id"]
        for item in first
        if item["locale"] == "ko"
    )
    state_path = next(
        path
        for path in (queue_root / "runs").glob("*.json")
        if json.loads(path.read_text())["run_id"] == korean_run_id
    )
    state = json.loads(state_path.read_text())
    state["status"] = "complete"
    multilingual.pipeline.write_json(state_path, state)
    terminal_bytes = state_path.read_bytes()

    second = multilingual.enqueue_article_translations(
        tmp_path,
        queue_root,
        source_run_id="legacy-rewrite-fortune-0039",
        article_id="TEST-001",
        lane="i18n-rewrite",
        source_loader=lambda _repo, _article_id: source_article(),
    )

    assert first == second
    assert len(list((queue_root / "runs").glob("*.json"))) == 3
    assert state_path.read_bytes() == terminal_bytes
    assert json.loads(state_path.read_text())["status"] == "complete"


def test_enqueue_translation_replacement_is_bounded_and_preserves_source_identity(
    tmp_path: Path,
) -> None:
    queue_root = tmp_path / "queue"
    records = multilingual.enqueue_article_translations(
        tmp_path,
        queue_root,
        source_run_id="source-run-001",
        article_id="TEST-001",
        lane="i18n-new",
        source_loader=lambda _repo, _article_id: source_article(),
    )
    base = next(record for record in records if record["locale"] == "en")
    state_path = next(
        path
        for path in (queue_root / "runs").glob("*.json")
        if json.loads(path.read_text())["run_id"] == base["run_id"]
    )
    state = json.loads(state_path.read_text())
    state["status"] = "failed"
    state["error_type"] = "LocalePlanValidationError"
    multilingual.pipeline.write_json(state_path, state)
    base_state_bytes = state_path.read_bytes()
    base_brief_path = Path(base["run_dir"]) / "brief.json"
    base_brief = json.loads(base_brief_path.read_text())
    base_brief_bytes = base_brief_path.read_bytes()

    first = multilingual.enqueue_translation_replacement(
        tmp_path,
        queue_root,
        terminal_state=state,
        recovery_reason="LOCALE_PLAN_VALIDATION",
        source_loader=lambda _repo, _article_id: source_article(),
    )
    second = multilingual.enqueue_translation_replacement(
        tmp_path,
        queue_root,
        terminal_state=state,
        recovery_reason="LOCALE_PLAN_VALIDATION",
        source_loader=lambda _repo, _article_id: source_article(),
    )

    assert first == second
    assert first["run_id"] == f"{base['run_id']}-replacement-01"
    replacement_state = json.loads(Path(first["state_path"]).read_text())
    replacement_brief = json.loads(
        (Path(first["run_dir"]) / "brief.json").read_text()
    )
    assert replacement_state["status"] == "active"
    assert replacement_state["replacement_of"] == base["run_id"]
    assert replacement_state["replacement_reason"] == "LOCALE_PLAN_VALIDATION"
    assert replacement_brief == {
        **base_brief,
        "run_id": first["run_id"],
    }
    assert state_path.read_bytes() == base_state_bytes
    assert base_brief_path.read_bytes() == base_brief_bytes
    assert len(list((queue_root / "translation-runs").glob("*-replacement-01"))) == 1

    replacement_state["status"] = "failed"
    with pytest.raises(ValueError, match="lineage is exhausted"):
        multilingual.enqueue_translation_replacement(
            tmp_path,
            queue_root,
            terminal_state=replacement_state,
            recovery_reason="LOCALE_PLAN_VALIDATION",
            source_loader=lambda _repo, _article_id: source_article(),
        )
    assert not list(
        (queue_root / "translation-runs").glob("*-replacement-01-replacement-01")
    )


def test_enqueue_translation_replacement_rejects_source_drift_without_mutation(
    tmp_path: Path,
) -> None:
    queue_root = tmp_path / "queue"
    records = multilingual.enqueue_article_translations(
        tmp_path,
        queue_root,
        source_run_id="source-run-001",
        article_id="TEST-001",
        lane="i18n-new",
        source_loader=lambda _repo, _article_id: source_article(),
    )
    base = next(record for record in records if record["locale"] == "ja")
    state_path = next(
        path
        for path in (queue_root / "runs").glob("*.json")
        if json.loads(path.read_text())["run_id"] == base["run_id"]
    )
    state = json.loads(state_path.read_text())
    state["status"] = "failed"
    state["error_type"] = "LocalePlanValidationError"
    multilingual.pipeline.write_json(state_path, state)
    state_bytes = state_path.read_bytes()
    brief_path = Path(base["run_dir"]) / "brief.json"
    brief_bytes = brief_path.read_bytes()
    changed_source = source_article()
    changed_source["title"] = "來源已更新"

    with pytest.raises(ValueError, match="source drift"):
        multilingual.enqueue_translation_replacement(
            tmp_path,
            queue_root,
            terminal_state=state,
            recovery_reason="LOCALE_PLAN_VALIDATION",
            source_loader=lambda _repo, _article_id: changed_source,
        )

    assert state_path.read_bytes() == state_bytes
    assert brief_path.read_bytes() == brief_bytes
    assert not list((queue_root / "translation-runs").glob("*-replacement-01"))


def test_enqueue_article_translations_does_not_overwrite_registered_source(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    multilingual.enqueue_article_translations(
        tmp_path,
        queue_root,
        source_run_id="source-run-001",
        article_id="TEST-001",
        lane="i18n-new",
        source_loader=lambda _repo, _article_id: source_article(),
    )
    changed = source_article()
    changed["title"] = "來源文章已更新"

    with pytest.raises(ValueError, match="source drift"):
        multilingual.enqueue_article_translations(
            tmp_path,
            queue_root,
            source_run_id="source-run-001",
            article_id="TEST-001",
            lane="i18n-new",
            source_loader=lambda _repo, _article_id: changed,
        )
