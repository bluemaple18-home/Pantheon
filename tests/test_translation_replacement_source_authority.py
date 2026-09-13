from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from scripts import agy_multilingual_pipeline as multilingual


def _source() -> dict[str, object]:
    return {
        "article_id": "POST-ACTOR-001",
        "canonical_path": "/articles/tarot/tarot-post-actor-001",
        "title": "固定 actor 之後才發布的來源文章",
        "description": "這是一筆已發布、已封存在 translation brief 的來源文章。",
        "answer": "replacement 應沿用原本已封存且 hash 綁定的來源快照。",
        "tags": ["塔羅", "來源快照"],
        "faq": [
            {
                "question": "可以忽略來源漂移嗎？",
                "answer": "不可以；來源可讀但 hash 不同時仍必須 fail closed。",
            }
        ],
        "bodySections": [
            {
                "heading": "來源權限",
                "paragraphs": [
                    "原 translation brief 已保存完整來源與 source_sha256。",
                    "只有固定 actor 明確找不到該文章時，才允許使用這份 sealed snapshot。",
                ],
            }
        ],
    }


def _terminal_run(tmp_path: Path) -> tuple[Path, dict[str, object], dict[str, object]]:
    queue_root = tmp_path / "queue"
    run_id = "translate-post-actor-ja"
    run_dir = queue_root / "translation-runs" / run_id
    source = _source()
    brief = {
        "schema_version": 1,
        "run_id": run_id,
        "mode": "translate_existing",
        "articles": [
            {
                "translation_id": "POST-ACTOR-001:ja",
                "locale": "ja",
                "source_article_id": "POST-ACTOR-001",
                "source_path": source["canonical_path"],
                "source_sha256": multilingual.source_sha256(source),
                "source": source,
            }
        ],
    }
    multilingual.validate_translation_brief(brief)
    multilingual.pipeline.write_json(run_dir / "brief.json", brief)
    state = {
        "schema_version": 1,
        "run_id": run_id,
        "run_dir": str(run_dir.resolve()),
        "status": "failed",
        "lane": "i18n-new",
        "identity_envelope": multilingual.translation_identity_envelope(
            "POST-ACTOR-001",
            "i18n-new",
        ),
        "registered_at": "2026-09-13T00:00:00+08:00",
        "updated_at": "2026-09-13T00:00:00+08:00",
    }
    state_path = (
        queue_root
        / "runs"
        / f"{hashlib.sha256(run_id.encode('utf-8')).hexdigest()[:24]}.json"
    )
    multilingual.pipeline.write_json(state_path, state)
    return queue_root, state, brief


def test_replacement_uses_sealed_source_only_when_fixed_actor_article_is_missing(
    tmp_path: Path,
) -> None:
    queue_root, terminal_state, brief = _terminal_run(tmp_path)

    def missing_from_fixed_actor(_repo_root: Path, _article_id: str) -> dict[str, object]:
        raise subprocess.CalledProcessError(
            1,
            ["node", "article-loader"],
            stderr="Error: article not found\n",
        )

    replacement = multilingual.enqueue_translation_replacement(
        tmp_path,
        queue_root,
        terminal_state=terminal_state,
        recovery_reason="LOCALE_PLAN_VALIDATION",
        source_loader=missing_from_fixed_actor,
    )

    replacement_brief = multilingual.read_translation_brief_payload(
        Path(replacement["run_dir"]) / "brief.json"
    )
    assert replacement_brief["articles"] == brief["articles"]
    assert replacement_brief["run_id"] == "translate-post-actor-ja-replacement-01"


def test_replacement_still_rejects_loadable_source_drift(tmp_path: Path) -> None:
    queue_root, terminal_state, _brief = _terminal_run(tmp_path)
    drifted = _source()
    drifted["title"] = "來源文章已經改版"

    with pytest.raises(ValueError, match="translation replacement source drift"):
        multilingual.enqueue_translation_replacement(
            tmp_path,
            queue_root,
            terminal_state=terminal_state,
            recovery_reason="LOCALE_PLAN_VALIDATION",
            source_loader=lambda _repo_root, _article_id: drifted,
        )


def test_replacement_does_not_hide_unrelated_source_loader_failure(tmp_path: Path) -> None:
    queue_root, terminal_state, _brief = _terminal_run(tmp_path)

    def broken_loader(_repo_root: Path, _article_id: str) -> dict[str, object]:
        raise subprocess.CalledProcessError(
            1,
            ["node", "article-loader"],
            stderr="SyntaxError: registry module failed to load\n",
        )

    with pytest.raises(subprocess.CalledProcessError):
        multilingual.enqueue_translation_replacement(
            tmp_path,
            queue_root,
            terminal_state=terminal_state,
            recovery_reason="LOCALE_PLAN_VALIDATION",
            source_loader=broken_loader,
        )
