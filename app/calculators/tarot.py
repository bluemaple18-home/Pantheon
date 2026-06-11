from random import Random
from typing import Any

from app.calculators.base import BaseDivination


MAJOR_ARCANA = [
    "愚者",
    "魔術師",
    "女祭司",
    "皇后",
    "皇帝",
    "教皇",
    "戀人",
    "戰車",
    "力量",
    "隱者",
    "命運之輪",
    "正義",
    "吊人",
    "死神",
    "節制",
    "惡魔",
    "高塔",
    "星星",
    "月亮",
    "太陽",
    "審判",
    "世界",
]


class TarotCalculator(BaseDivination):
    name = "tarot"

    def calculate(self, user_data: dict[str, Any]) -> dict[str, Any]:
        seed = f"{user_data.get('birth_date')}:{user_data.get('birth_time')}:{user_data.get('name', '')}"
        rng = Random(seed)
        card = rng.choice(MAJOR_ARCANA)
        return {
            "system": self.name,
            "version": self.version,
            "status": "reserved_mvp",
            "spread": "single_card",
            "cards": [{"name": card, "reversed": rng.choice([False, True])}],
            "notice": "塔羅外掛插槽已保留，目前只提供可重現的單牌 MVP。",
        }
