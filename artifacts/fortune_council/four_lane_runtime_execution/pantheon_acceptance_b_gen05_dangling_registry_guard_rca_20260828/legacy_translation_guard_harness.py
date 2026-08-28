#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


RUN_ID = "auto-i18n-ja-1414b75a404721e95e74"
SOURCE_ARTICLE_ID = "V2-TAROT-DEATH-MONEY"


def expected_identity_envelope(mode: str, lane: str, article_ids: list[str]) -> dict[str, object]:
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


def current_sha() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "--short=10", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def main() -> int:
    sys.path.insert(0, str(Path.cwd()))
    from scripts import agy_gemini_coordinator as coordinator

    with tempfile.TemporaryDirectory(prefix="pantheon-gen05-guard-") as temp_dir:
        root = Path(temp_dir)
        queue_root = root / "queue"
        repo_root = root / "repo"
        run_dir = (queue_root / "gsc-copy" / RUN_ID).resolve()
        repo_root.mkdir(parents=True)
        run_dir.mkdir(parents=True)
        coordinator.atomic_write_json(
            run_dir / "brief.json",
            {
                "schema_version": 1,
                "run_id": RUN_ID,
                "mode": "translate_existing",
                "source_commit": "a" * 40,
                "generation": 5,
                "articles": [
                    {
                        "source_article_id": SOURCE_ARTICLE_ID,
                        "locale": "ja",
                        "article_id": f"{SOURCE_ARTICLE_ID}:ja",
                    }
                ],
            },
        )
        coordinator.atomic_write_json(
            coordinator._state_path(RUN_ID, queue_root),
            {
                "schema_version": 1,
                "run_id": RUN_ID,
                "run_dir": str(run_dir),
                "status": "active",
                "correlation_id": f"{RUN_ID}-correlation",
                "active_generation": 5,
                "next_generation": 5,
                "semantic_budget": 1,
                "routing_schema_version": 1,
                "mode": "translate_existing",
                "lane": "i18n-new",
                "identity_envelope": expected_identity_envelope(
                    "translate_existing",
                    "i18n-new",
                    [SOURCE_ARTICLE_ID],
                ),
            },
        )
        calls = {"tick": 0, "process": 0}
        coordinator.publisher.legacy_article_ids = lambda _repo: set()

        def complete_tick(_run_dir: Path, _job_queue_root: Path) -> dict[str, object]:
            calls["tick"] += 1
            return {"status": "synthetic-complete"}

        def provider_process(*_args: object, **_kwargs: object) -> dict[str, str]:
            calls["process"] += 1
            return {"status": "processed"}

        summary = coordinator.cycle_once(
            queue_root,
            tick=complete_tick,
            process=provider_process,
            repo_root=repo_root,
            lane_mode=True,
            exact_run_ids=[RUN_ID],
        )
    result = {"commit": current_sha(), "summary": summary, "calls": calls}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if summary.get("reason") == "active run registry is dangling":
        return 2
    if calls != {"tick": 1, "process": 0}:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
