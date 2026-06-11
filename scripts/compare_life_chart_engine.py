from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROVIDER = "life_chart_engine"
LICENSE_BOUNDARY = "AGPL-3.0 external CLI output only; no code import or vendoring"
REQUIRED_COLLECTIONS = (
    ("western", "planets"),
    ("western", "houses"),
    ("human_design", "gates"),
    ("ziwei", "palaces"),
)


@dataclass(frozen=True)
class GoldenSample:
    id: str
    name: str
    gender: str
    birth_date: str
    birth_time: str
    tz_offset: float
    latitude: float
    longitude: float
    target: str
    purpose: str


GOLDEN_SAMPLES = {
    "taipei_baseline": GoldenSample(
        id="taipei_baseline",
        name="Taipei Baseline",
        gender="女",
        birth_date="1990-06-15",
        birth_time="08:30",
        tz_offset=8.0,
        latitude=25.033,
        longitude=121.5654,
        target="2025-01-01",
        purpose="對齊 life-chart-engine README 範例，驗證 JSON parser 與欄位映射。",
    ),
    "midnight_boundary": GoldenSample(
        id="midnight_boundary",
        name="Midnight Boundary",
        gender="女",
        birth_date="1990-06-15",
        birth_time="23:50",
        tz_offset=8.0,
        latitude=25.033,
        longitude=121.5654,
        target="2025-01-01",
        purpose="測試時辰、宮位與 Human Design line 對邊界時間的敏感度。",
    ),
    "dst_city": GoldenSample(
        id="dst_city",
        name="DST City",
        gender="女",
        birth_date="1990-06-15",
        birth_time="08:30",
        tz_offset=-4.0,
        latitude=40.7128,
        longitude=-74.0060,
        target="2025-01-01",
        purpose="驗證 caller 必須提供出生當地當日 UTC offset，不可只靠 timezone 名稱。",
    ),
}


class LifeChartEngineError(RuntimeError):
    """外部 life-chart-engine 驗證失敗。"""


def run_life_chart_engine(life_chart_bin: str, sample: GoldenSample) -> dict[str, Any]:
    """呼叫外部 CLI；不 import AGPL 程式碼。"""
    command = [
        life_chart_bin,
        "--json",
        "--name",
        sample.name,
        "--gender",
        sample.gender,
        "--date",
        sample.birth_date,
        "--time",
        sample.birth_time,
        "--tz",
        str(sample.tz_offset),
        "--lat",
        str(sample.latitude),
        "--lon",
        str(sample.longitude),
        "--target",
        sample.target,
    ]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError as exc:
        raise LifeChartEngineError(
            f"找不到 life-chart CLI：{life_chart_bin}。請先安裝外部 repo，或用 --input-json 測試既有輸出。"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise LifeChartEngineError("life-chart CLI 執行超過 60 秒。") from exc

    if result.returncode != 0:
        stderr = result.stderr.strip() or "(no stderr)"
        raise LifeChartEngineError(f"life-chart CLI 失敗：exit={result.returncode}; stderr={stderr}")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise LifeChartEngineError("life-chart CLI 沒有輸出有效 JSON。") from exc


def validate_life_chart_payload(payload: dict[str, Any]) -> None:
    if payload.get("ok") is not True:
        raise LifeChartEngineError("life-chart payload 必須包含 ok=true。")

    for section, key in REQUIRED_COLLECTIONS:
        value = payload.get(section, {}).get(key)
        if not isinstance(value, list) or not value:
            raise LifeChartEngineError(f"life-chart payload 缺少必要非空陣列：{section}.{key}")


def normalize_life_chart_payload(payload: dict[str, Any]) -> dict[str, Any]:
    validate_life_chart_payload(payload)
    western = payload.get("western", {})
    human_design = payload.get("human_design", {})
    ziwei = payload.get("ziwei", {})
    meta = payload.get("meta", {})

    ziwei_chart = _normalize_ziwei(ziwei)
    return {
        "provider": PROVIDER,
        "license_boundary": LICENSE_BOUNDARY,
        "charts": {
            "western_astrology": _normalize_western(western),
            "human_design": _normalize_human_design(human_design),
            "ziwei": ziwei_chart,
        },
        "metadata": {
            "external_engine": {
                "provider": PROVIDER,
                "engine": meta.get("engine", PROVIDER),
                "version": meta.get("version"),
                "ephemeris": meta.get("ephemeris"),
                "schema_version": payload.get("schema_version"),
                "license_boundary": LICENSE_BOUNDARY,
            },
            "input": payload.get("input", {}),
        },
    }


def _normalize_western(western: dict[str, Any]) -> dict[str, Any]:
    aspects = western.get("aspects", [])
    return {
        "system": "western_astrology",
        "provider": PROVIDER,
        "algorithm_level": "external_validator",
        "source_system": western.get("system"),
        "ascendant": western.get("ascendant"),
        "midheaven": western.get("midheaven"),
        "planets": western.get("planets", []),
        "houses": western.get("houses", []),
        "aspects": aspects,
        "notable_patterns": [
            {
                "id": f"western.aspect.{_slug(aspect.get('a'))}.{_slug(aspect.get('b'))}.{_slug(aspect.get('type'))}",
                "name": f"{aspect.get('a', '未知')}-{aspect.get('b', '未知')}{aspect.get('type', '相位')}",
                "basis": "西洋占星相位",
                "meaning": f"orb={aspect.get('orb', 'unknown')} 的相位訊號，可作為跨系統佐證。",
            }
            for aspect in aspects[:12]
        ],
    }


def _normalize_human_design(human_design: dict[str, Any]) -> dict[str, Any]:
    channels = human_design.get("channels", [])
    return {
        "system": "human_design",
        "provider": PROVIDER,
        "algorithm_level": "external_validator",
        "type": human_design.get("type"),
        "authority": human_design.get("authority"),
        "profile": human_design.get("profile"),
        "definition": human_design.get("definition"),
        "incarnation_cross": human_design.get("incarnation_cross"),
        "design_date": human_design.get("design_date"),
        "centers": {
            "defined": human_design.get("defined_centers", []),
            "open": human_design.get("open_centers", []),
        },
        "channels": channels,
        "gates": human_design.get("gates", []),
        "notable_patterns": [
            {
                "id": f"human_design.channel.{_slug(channel)}",
                "name": f"通道 {channel}",
                "basis": "Human Design defined channel",
                "meaning": "外部引擎判定的定義通道，可轉成後續格局卡。",
            }
            for channel in channels
        ],
    }


def _normalize_ziwei(ziwei: dict[str, Any]) -> dict[str, Any]:
    palaces = ziwei.get("palaces", [])
    life_palace = _find_life_palace(palaces)
    body_palace = _find_body_palace(palaces)
    return {
        "system": "ziwei",
        "provider": PROVIDER,
        "algorithm_level": "external_validator",
        "five_elements_class": ziwei.get("five_elements_class"),
        "soul_star": ziwei.get("soul"),
        "body_star": ziwei.get("body"),
        "hour_index": ziwei.get("hour_index"),
        "life_palace": life_palace.get("name") if life_palace else None,
        "body_palace": body_palace.get("name") if body_palace else None,
        "life_palace_stars": _palace_stars(life_palace),
        "body_palace_stars": _palace_stars(body_palace),
        "palaces": palaces,
        "horoscope": ziwei.get("horoscope"),
        "notable_patterns": _ziwei_patterns(ziwei, life_palace, body_palace),
    }


def _find_life_palace(palaces: list[dict[str, Any]]) -> dict[str, Any] | None:
    for palace in palaces:
        if "命" in str(palace.get("flags", "")) or palace.get("name") == "命宮":
            return palace
    return None


def _find_body_palace(palaces: list[dict[str, Any]]) -> dict[str, Any] | None:
    for palace in palaces:
        if "身" in str(palace.get("flags", "")) or palace.get("name") == "身宮":
            return palace
    return None


def _palace_stars(palace: dict[str, Any] | None) -> list[str]:
    if not palace:
        return []
    stars: list[str] = []
    for key in ("major_stars", "minor_stars", "adjective_stars"):
        value = palace.get(key, [])
        if isinstance(value, list):
            stars.extend(str(item) for item in value)
    return stars


def _ziwei_patterns(
    ziwei: dict[str, Any],
    life_palace: dict[str, Any] | None,
    body_palace: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    patterns = []
    if ziwei.get("five_elements_class"):
        patterns.append(
            {
                "id": "ziwei.external.five_elements_class",
                "name": str(ziwei["five_elements_class"]),
                "basis": "五行局",
                "meaning": "外部引擎回傳的紫微五行局，可作為 primary provider 的校驗欄位。",
            }
        )
    if life_palace:
        patterns.append(
            {
                "id": "ziwei.external.life_palace",
                "name": f"命宮在{life_palace.get('name')}",
                "basis": "命宮",
                "meaning": "外部引擎回傳的命宮資料，可與 Pantheon 紫微 primary provider 對照。",
            }
        )
    if body_palace:
        patterns.append(
            {
                "id": "ziwei.external.body_palace",
                "name": f"身宮在{body_palace.get('name')}",
                "basis": "身宮",
                "meaning": "外部引擎回傳的身宮資料，可與 Pantheon 紫微 primary provider 對照。",
            }
        )
    return patterns


def _slug(value: Any) -> str:
    text = str(value or "unknown").strip().lower()
    keep = []
    for char in text:
        if char.isalnum():
            keep.append(char)
        elif char in {"-", "_"}:
            keep.append(char)
        else:
            keep.append("_")
    return "".join(keep).strip("_") or "unknown"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise LifeChartEngineError("JSON root 必須是 object。")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run or normalize life-chart-engine JSON without importing AGPL code."
    )
    parser.add_argument("--sample", choices=sorted(GOLDEN_SAMPLES), default="taipei_baseline")
    parser.add_argument("--life-chart-bin", default="life-chart")
    parser.add_argument("--input-json", type=Path, help="讀取既有 life-chart --json 輸出，略過外部 CLI。")
    parser.add_argument("--expect-json", type=Path, help="比對已 normalize 的 snapshot JSON。")
    parser.add_argument("--raw", action="store_true", help="輸出原始 life-chart JSON，而不是 Pantheon normalized JSON。")
    args = parser.parse_args(argv)

    try:
        payload = load_json(args.input_json) if args.input_json else run_life_chart_engine(
            args.life_chart_bin,
            GOLDEN_SAMPLES[args.sample],
        )
        output = payload if args.raw else normalize_life_chart_payload(payload)

        if args.expect_json:
            expected = load_json(args.expect_json)
            if output != expected:
                raise LifeChartEngineError(f"normalized output 與 snapshot 不一致：{args.expect_json}")

        print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except LifeChartEngineError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
