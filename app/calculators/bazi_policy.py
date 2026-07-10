from __future__ import annotations

from typing import Any


BAZI_RULESET_VERSION = "pantheon-bazi-rules-mvp-0.2"


def active_calendar_engine() -> dict[str, Any]:
    return {
        "provider": "lunar-python",
        "provider_status": "active",
        "algorithm_level": "calendar_provider_lunar_python_rules_mvp",
        "notice": "四柱由 lunar-python 產出；藏干、十神、合沖與大運仍由 Pantheon rules layer 計算。",
        "policies": {
            "month_boundary": "solar_term_by_provider",
            "day_boundary": "provider_default",
            "true_solar_time": "not_applied",
        },
    }


def fallback_calendar_engine(provider_error: str | None = None) -> dict[str, Any]:
    notice = "目前使用內建 MVP 曆法骨架；尚未啟用 lunar-python，月柱不是正式節氣換月。"
    if provider_error:
        notice = f"{notice} lunar-python adapter error: {provider_error}."
    return {
        "provider": "pantheon-internal",
        "provider_status": "fallback",
        "algorithm_level": "mvp_scaffold",
        "notice": notice,
        "policies": {
            "month_boundary": "calendar_month_mvp",
            "day_boundary": "clock_date_mvp",
            "true_solar_time": "not_applied",
        },
    }
