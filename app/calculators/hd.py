from typing import Any

from app.calculators.base import BaseDivination


class HumanDesignCalculator(BaseDivination):
    name = "human_design"

    def calculate(self, user_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "system": self.name,
            "version": self.version,
            "status": "reserved",
            "notice": "人類圖外掛插槽已保留，等待星曆與閘門通道資料接入。",
        }
