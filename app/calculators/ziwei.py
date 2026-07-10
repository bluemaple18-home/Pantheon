from __future__ import annotations

import json
import subprocess
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

from app.calculators.base import BaseDivination
from app.calculators.ziwei_fusion import PRIMARY_PROVIDER, build_ziwei_fusion
from app.calculators.ziwei_items import calculate_ziwei_items


PALACES = ["命宮", "兄弟", "夫妻", "子女", "財帛", "疾厄", "遷移", "僕役", "官祿", "田宅", "福德", "父母"]
MAIN_STARS = ["紫微", "天機", "太陽", "武曲", "天同", "廉貞", "天府", "太陰", "貪狼", "巨門", "天相", "天梁", "七殺", "破軍"]
ROOT_DIR = Path(__file__).resolve().parents[2]
IZTRO_BRIDGE = ROOT_DIR / "services" / "ziwei" / "iztro_chart.mjs"


def _parse_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)).date()


def _parse_time(value: Any) -> time:
    if isinstance(value, time):
        return value
    return time.fromisoformat(str(value))


class ZiweiCalculator(BaseDivination):
    """紫微斗數 MVP 排盤接口，保留完整演算法替換點。"""

    name = "ziwei"

    def calculate(self, user_data: dict[str, Any]) -> dict[str, Any]:
        iztro_chart = _calculate_with_iztro(user_data)
        if iztro_chart:
            life_palace = next(
                palace for palace in iztro_chart["palaces"] if palace["name"] == iztro_chart["life_palace"]
            )
            body_palace = next(
                palace for palace in iztro_chart["palaces"] if palace["name"] == iztro_chart["body_palace"]
            )
            return {
                "system": self.name,
                "provider": iztro_chart["provider"],
                "provider_status": iztro_chart["provider_status"],
                "provider_version": iztro_chart["provider_version"],
                "version": self.version,
                "algorithm_level": iztro_chart["algorithm_level"],
                "notice": iztro_chart["notice"],
                "life_palace": iztro_chart["life_palace"],
                "body_palace": iztro_chart["body_palace"],
                "life_palace_stars": iztro_chart["life_palace_stars"],
                "body_palace_stars": iztro_chart["body_palace_stars"],
                "palaces": iztro_chart["palaces"],
                "calculated_items": calculate_ziwei_items(iztro_chart["palaces"]),
                "raw_chart": {
                    key: iztro_chart.get(key)
                    for key in [
                        "solar_date",
                        "lunar_date",
                        "chinese_date",
                        "time_index",
                        "time_range",
                        "sign",
                        "zodiac",
                        "soul",
                        "body",
                        "five_elements_class",
                        "earthly_branch_of_life_palace",
                        "earthly_branch_of_body_palace",
                    ]
                },
                "notable_patterns": _notable_patterns(life_palace, body_palace),
                "fusion": build_ziwei_fusion(
                    {
                        "provider": "iztro",
                        "life_palace": iztro_chart["life_palace"],
                        "body_palace": iztro_chart["body_palace"],
                        "life_palace_stars": iztro_chart["life_palace_stars"],
                        "body_palace_stars": iztro_chart["body_palace_stars"],
                        "palaces": iztro_chart["palaces"],
                        "hour_index": iztro_chart["raw_chart"]["time_index"]
                        if "raw_chart" in iztro_chart
                        else iztro_chart.get("time_index"),
                    }
                ),
                "reference_dataset": {
                    "name": "iztro",
                    "status": "active",
                    "version": iztro_chart["provider_version"],
                },
            }

        birth_date = _parse_date(user_data["birth_date"])
        birth_time = _parse_time(user_data["birth_time"])
        hour_branch_index = ((birth_time.hour + 1) // 2) % 12
        life_palace_index = (birth_date.month - hour_branch_index - 1) % 12
        body_palace_index = (birth_date.month + hour_branch_index - 1) % 12
        star_offset = (birth_date.year + birth_date.month + birth_date.day) % len(MAIN_STARS)

        palaces = []
        for index, palace_name in enumerate(PALACES):
            stars = [MAIN_STARS[(star_offset + index) % len(MAIN_STARS)]]
            if index % 3 == 0:
                stars.append(MAIN_STARS[(star_offset + index + 6) % len(MAIN_STARS)])
            palaces.append(
                {
                    "name": palace_name,
                    "index": index,
                    "is_life_palace": index == life_palace_index,
                    "is_body_palace": index == body_palace_index,
                    "stars": stars,
                }
            )

        life_palace = palaces[life_palace_index]
        body_palace = palaces[body_palace_index]
        return {
            "system": self.name,
            "provider": PRIMARY_PROVIDER,
            "provider_status": "fallback",
            "version": self.version,
            "algorithm_level": "mvp_scaffold",
            "notice": "目前為純 Python 可替換骨架，尚未完整移植 ziwei-doushu 排盤演算法。",
            "life_palace": PALACES[life_palace_index],
            "body_palace": PALACES[body_palace_index],
            "life_palace_stars": life_palace["stars"],
            "body_palace_stars": body_palace["stars"],
            "palaces": palaces,
            "calculated_items": calculate_ziwei_items(palaces),
            "notable_patterns": _notable_patterns(life_palace, body_palace),
            "fusion": build_ziwei_fusion(
                {
                    "provider": PRIMARY_PROVIDER,
                    "life_palace": PALACES[life_palace_index],
                    "body_palace": PALACES[body_palace_index],
                    "life_palace_stars": life_palace["stars"],
                    "body_palace_stars": body_palace["stars"],
                    "palaces": palaces,
                    "hour_index": hour_branch_index,
                }
            ),
            "reference_dataset": {
                "name": "ziwei-samples-v3",
                "expected_records": 518400,
                "status": "not_downloaded",
            },
        }


def _calculate_with_iztro(user_data: dict[str, Any]) -> dict[str, Any] | None:
    if not IZTRO_BRIDGE.exists():
        return None
    payload = {
        "birth_date": str(user_data["birth_date"]),
        "birth_time": str(user_data["birth_time"]),
        "gender": user_data.get("gender"),
    }
    try:
        completed = subprocess.run(
            ["node", str(IZTRO_BRIDGE)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            timeout=5,
            check=True,
            cwd=str(ROOT_DIR),
        )
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return None
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None


def _notable_patterns(life_palace: dict[str, Any], body_palace: dict[str, Any]) -> list[dict[str, Any]]:
    patterns = [
        {
            "id": "ziwei.pattern.life_palace_axis",
            "name": f"命宮在{life_palace['name']}",
            "basis": "命宮",
            "stars": life_palace["stars"],
            "meaning": "命宮代表人格底色、外在呈現與人生主軸。",
        },
        {
            "id": "ziwei.pattern.body_palace_axis",
            "name": f"身宮在{body_palace['name']}",
            "basis": "身宮",
            "stars": body_palace["stars"],
            "meaning": "身宮代表後天行動模式與實際投入的生活重心。",
        },
    ]
    if life_palace["stars"]:
        patterns.append(
            {
                "id": "ziwei.pattern.life_palace_main_star",
                "name": f"命宮{life_palace['stars'][0]}",
                "basis": "命宮主星",
                "stars": life_palace["stars"],
                "meaning": f"{life_palace['stars'][0]}是此盤命宮的主星訊號，會影響人格主軸的展開方式。",
            }
        )
    if body_palace["stars"]:
        patterns.append(
            {
                "id": "ziwei.pattern.body_palace_main_star",
                "name": f"身宮{body_palace['stars'][0]}",
                "basis": "身宮主星",
                "stars": body_palace["stars"],
                "meaning": f"{body_palace['stars'][0]}是此盤身宮的主星訊號，會影響後天行動方式。",
            }
        )
    return patterns
