import json
from pathlib import Path
from typing import Any

import pytest

from app.calculators.bazi import BaziCalculator


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "bazi_golden_cases.json"


def _load_cases() -> list[dict[str, Any]]:
    return json.loads(FIXTURE_PATH.read_text())


@pytest.mark.parametrize("case", _load_cases(), ids=lambda case: case["id"])
def test_bazi_golden_case_stable_fields(case: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    if case.get("mock_pillars"):
        monkeypatch.setattr("app.calculators.bazi._lunar_python_pillars", lambda *_: case["mock_pillars"])
    elif case.get("force_calendar_fallback"):
        monkeypatch.setattr("app.calculators.bazi._lunar_python_pillars", lambda *_: None)

    result = BaziCalculator().calculate(case["input"])

    assert _stable_bazi_projection(result) == case["expected"]


def _stable_bazi_projection(result: dict[str, Any]) -> dict[str, Any]:
    items = result["calculated_items"]
    luck = result["luck_cycles"]
    return {
        "pillars": result["pillars"],
        "day_master": {
            "stem": result["day_master"]["stem"],
            "element": result["day_master"]["element"],
        },
        "ten_gods": {
            "visible_labels": _visible_ten_gods(result["ten_gods"]),
            "hidden_labels": _hidden_ten_gods(result["ten_gods"]),
        },
        "calculated_items": {
            "growth_labels": [item["label"] for item in items["growth_states"]],
            "special_force_labels": [item["label"] for item in items["special_forces"]],
            "shensha_labels": [item["label"] for item in items["shensha"]],
        },
        "luck_cycles": {
            "annual": {
                "year": luck["annual"]["year"],
                "pillar": luck["annual"]["pillar"],
                "ten_god": luck["annual"]["ten_god"],
            },
            "qiyun_status": luck["qiyun"]["status"],
        },
        "policy": {
            "ruleset_version": result["ruleset_version"],
            "calendar_provider": result["calendar_engine"]["provider"],
            "strength_model": result["strength_analysis"]["model"],
            "items_source": items["policy"]["source"],
        },
    }


def _visible_ten_gods(ten_gods: dict[str, dict[str, Any]]) -> list[str]:
    return _unique([item["god"] for item in ten_gods.values()])


def _hidden_ten_gods(ten_gods: dict[str, dict[str, Any]]) -> list[str]:
    return _unique(
        hidden["god"]
        for item in ten_gods.values()
        for hidden in item.get("hidden_stems", [])
    )


def _unique(values) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
