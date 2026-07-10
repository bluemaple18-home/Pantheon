from __future__ import annotations

from typing import Any


SUPPORT_STAR_PRIORITY = ["文昌", "文曲", "祿存", "天魁", "天鉞", "左輔", "右弼", "天貴", "天喜", "紅鸞", "天馬", "華蓋"]
SUPPORT_FOCUS_PALACES = {"命宮", "官祿", "財帛"}


def calculate_ziwei_items(palaces: list[dict[str, Any]]) -> dict[str, Any]:
    support_items: list[dict[str, Any]] = []
    for palace in palaces:
        palace_name = palace.get("name")
        if palace_name not in SUPPORT_FOCUS_PALACES:
            continue
        for star in palace.get("stars", []):
            hit = next((name for name in SUPPORT_STAR_PRIORITY if name in str(star)), "")
            if hit:
                support_items.append(
                    {
                        "label": hit,
                        "palace": palace_name,
                        "star": star,
                        "note": f"{palace_name} 宮見 {star}",
                        "priority": SUPPORT_STAR_PRIORITY.index(hit),
                        "basis": "命宮、官祿、財帛重點輔星",
                    }
                )
    unique_items = {
        f"{item['label']}-{item['palace']}-{item['star']}": item
        for item in support_items
    }
    return {
        "support_stars": [
            {key: value for key, value in item.items() if key != "priority"}
            for item in sorted(unique_items.values(), key=lambda row: row["priority"])[:4]
        ],
        "policy": {
            "source": "pantheon_ziwei_focus_filter",
            "focus_palaces": sorted(SUPPORT_FOCUS_PALACES),
            "display_rule": "只輸出命宮、官祿、財帛命中的重點輔星，最多四筆。",
        },
    }
