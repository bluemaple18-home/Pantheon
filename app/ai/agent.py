from __future__ import annotations

from typing import Any

from app.ai.prompts import build_interpretation_prompt
from app.ai.report import UnifiedReport


def generate_interpretation(
    user_data: dict[str, Any],
    charts: dict[str, Any],
    report: UnifiedReport,
    school_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """先回傳可驗證的 prompt 與本地摘要，之後可替換成原生 SDK 呼叫。"""
    prompt = build_interpretation_prompt(user_data, charts, report, school_policy)
    first_block = report.reading_blocks[0] if report.reading_blocks else None
    summary = first_block.summary if first_block else "目前沒有足夠訊號組成統一解讀。"
    return {
        "mode": "local_stub",
        "summary": summary,
        "prompt": prompt,
        "syntax_version": report.syntax_version,
        "rag": {"enabled": False, "reason": "ziwei dataset not imported yet"},
    }
