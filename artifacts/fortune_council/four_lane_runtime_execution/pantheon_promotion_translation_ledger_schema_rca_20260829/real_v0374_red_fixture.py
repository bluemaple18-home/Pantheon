"""以 v0.3.374 translation ledger shape 重現 promotion plan 的 schema RED。"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from scripts import pantheon_content_runtime_promotion as promotion


TEST_MODULE_PATH = REPO_ROOT / "tests/test_pantheon_content_runtime_promotion.py"
RUN_ID = "auto-i18n-ja-1414b75a404721e95e74"
ARTICLE_ID = "V2-TAROT-DEATH-MONEY"


def _load_fixture_module():
    spec = importlib.util.spec_from_file_location("promotion_fixture_helpers", TEST_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("promotion fixture helpers are unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    helpers = _load_fixture_module()
    with tempfile.TemporaryDirectory(prefix="pantheon-promotion-v0374-red-") as raw_tmp:
        tmp_path = Path(raw_tmp).resolve()
        request, _identities = helpers._runtime_fixture(tmp_path)
        run_dir = request.queue_root / "translation-runs" / RUN_ID
        run_dir.mkdir(parents=True)
        helpers._write_json(
            run_dir / "brief.json",
            helpers._preserved_brief(
                RUN_ID,
                mode="translate_existing",
                lane="i18n-new",
                article_ids=[ARTICLE_ID],
            ),
        )
        helpers._write_preserved_state(
            request,
            "translation-v0374.json",
            run_id=RUN_ID,
            run_dir=run_dir,
            status="complete",
            identity_envelope=helpers._identity_envelope(
                [ARTICLE_ID],
                mode="translate_existing",
                lane="i18n-new",
            ),
        )
        ledger_path = request.publisher_state_root / "ledger.json"
        helpers._write_json(
            ledger_path,
            {
                "schema_version": 1,
                "published_runs": [],
                "quarantined_runs": [],
                "rewrite_released_runs": [],
                "superseded_runs": [],
                "translation_published_runs": [
                    {
                        "article_id": ARTICLE_ID,
                        "commit_sha": "22d7e21b7a3da4e8afffd58a76b2746bebad8b41",
                        "locale": "ja",
                        "published_at": "2026-08-29T11:21:04+08:00",
                        "run_id": RUN_ID,
                        "staging_receipt_sha256": "9544705d7d8c92b370451bf8560aa9815699bfe3f67e9fa527c5e3d7b233d1a4",
                        "version": "0.3.374",
                    }
                ],
                "translation_deferred_runs": [],
            },
        )
        request = promotion.PromotionRequest(
            **{**request.__dict__, "preserved_run_ids": (RUN_ID,)}
        )
        before = {
            "ledger_sha256": _sha256(ledger_path),
            "queue_tree_digest": promotion.tree_digest(request.queue_root),
            "transaction_exists": request.transaction_root.exists(),
        }
        error = None
        try:
            promotion.plan_promotion(request)
        except promotion.PromotionError as caught:
            error = str(caught)
        after = {
            "ledger_sha256": _sha256(ledger_path),
            "queue_tree_digest": promotion.tree_digest(request.queue_root),
            "transaction_exists": request.transaction_root.exists(),
        }
        receipt = {
            "schema_version": 1,
            "fixture": "real-v0.3.374-shaped-translation-ledger-record",
            "mode": "plan-only",
            "expected_red": "publisher ledger identity mismatch",
            "observed_error": error,
            "red": error == "publisher ledger identity mismatch",
            "provider_calls": 0,
            "publisher_executes": 0,
            "new_transaction_count": int(after["transaction_exists"]),
            "bytes_unchanged": before == after,
            "before": before,
            "after": after,
        }
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))
        return 1 if receipt["red"] and receipt["bytes_unchanged"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
