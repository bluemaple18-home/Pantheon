import json
import subprocess

import pytest

from scripts.compare_life_chart_engine import (
    GOLDEN_SAMPLES,
    LifeChartEngineError,
    normalize_life_chart_payload,
    run_life_chart_engine,
    validate_life_chart_payload,
)


SAMPLE_PAYLOAD = {
    "ok": True,
    "schema_version": "1.0",
    "input": {
        "name": "小明",
        "gender": "女",
        "date": "1990-06-15",
        "time": "08:30",
        "tz_offset": 8.0,
        "lat": 25.033,
        "lon": 121.5654,
        "target": "2025-01-01",
    },
    "western": {
        "system": "Tropical / Placidus / Moshier",
        "ascendant": {"label": "獅子 08°29'"},
        "midheaven": {"label": "金牛 04°22'"},
        "planets": [{"name": "太陽", "sign": "雙子", "house": 11}],
        "houses": [{"house": 1, "label": "獅子 08°29'"}],
        "aspects": [{"a": "木星", "b": "冥王星", "type": "三分", "orb": 0.3744}],
    },
    "human_design": {
        "type": "投射者",
        "authority": "自我投射型權威",
        "profile": "1/3",
        "definition": "一分人(單一定義)",
        "incarnation_cross": "右角度交叉（12/11 | 36/6）",
        "design_date": "1990-03-16",
        "defined_centers": ["G", "喉"],
        "open_centers": ["情緒", "意志"],
        "channels": ["13-33"],
        "gates": [{"planet": "☉", "personality": {"gate": 12, "line": 1}}],
    },
    "ziwei": {
        "five_elements_class": "土五局",
        "soul": "祿存",
        "body": "火星",
        "hour_index": 4,
        "palaces": [
            {
                "name": "命宮",
                "ganzhi": "戊寅",
                "flags": "",
                "decadal_range": "5-14",
                "major_stars": ["七殺(廟)"],
                "minor_stars": [],
                "adjective_stars": ["天廚", "蜚廉"],
            },
            {
                "name": "夫妻",
                "ganzhi": "庚辰",
                "flags": "身",
                "major_stars": ["天府(廟)"],
                "minor_stars": ["左輔"],
                "adjective_stars": [],
            },
        ],
        "horoscope": {"decadal": {"status": "best-effort"}},
    },
    "meta": {"engine": "life-chart-engine", "version": "1.0", "ephemeris": "Moshier"},
}


def test_normalize_life_chart_payload_maps_external_json_to_pantheon_charts() -> None:
    normalized = normalize_life_chart_payload(SAMPLE_PAYLOAD)

    assert normalized["provider"] == "life_chart_engine"
    assert "AGPL-3.0 external CLI output only" in normalized["license_boundary"]

    charts = normalized["charts"]
    assert charts["western_astrology"]["ascendant"]["label"] == "獅子 08°29'"
    assert charts["human_design"]["centers"]["defined"] == ["G", "喉"]
    assert charts["human_design"]["notable_patterns"][0]["id"] == "human_design.channel.13-33"

    ziwei = charts["ziwei"]
    assert ziwei["provider"] == "life_chart_engine"
    assert ziwei["life_palace"] == "命宮"
    assert ziwei["body_palace"] == "夫妻"
    assert ziwei["life_palace_stars"] == ["七殺(廟)", "天廚", "蜚廉"]
    assert ziwei["body_palace_stars"] == ["天府(廟)", "左輔"]


def test_validate_life_chart_payload_rejects_missing_required_collections() -> None:
    payload = dict(SAMPLE_PAYLOAD)
    payload["western"] = {"planets": [], "houses": []}

    with pytest.raises(LifeChartEngineError, match="western.planets"):
        validate_life_chart_payload(payload)


def test_run_life_chart_engine_invokes_external_cli_without_importing_code(monkeypatch) -> None:
    calls = []

    def fake_run(command, check, capture_output, text, timeout):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(SAMPLE_PAYLOAD), stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    payload = run_life_chart_engine("life-chart", GOLDEN_SAMPLES["taipei_baseline"])

    assert payload["ok"] is True
    assert calls[0][0] == "life-chart"
    assert "--json" in calls[0]
    assert "--lat" in calls[0]
    assert "--lon" in calls[0]
