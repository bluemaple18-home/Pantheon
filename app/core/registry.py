from __future__ import annotations

from collections.abc import Iterable

from app.calculators.base import BaseDivination
from app.calculators.bazi import BaziCalculator
from app.calculators.hd import HumanDesignCalculator
from app.calculators.mbti import MbtiCalculator
from app.calculators.nameology import NameologyCalculator
from app.calculators.tarot import TarotCalculator
from app.calculators.ziwei import ZiweiCalculator


class CalculatorRegistry:
    """集中管理算力插件，避免 API 層知道每個流派的細節。"""

    def __init__(self) -> None:
        self._calculators: dict[str, BaseDivination] = {}

    def register(self, calculator: BaseDivination) -> None:
        self._calculators[calculator.name] = calculator

    def get(self, name: str) -> BaseDivination:
        return self._calculators[name]

    def names(self) -> list[str]:
        return sorted(self._calculators)

    def calculate_many(self, names: Iterable[str], user_data: dict) -> dict:
        return {name: self.get(name).calculate(user_data) for name in names}


def build_default_registry() -> CalculatorRegistry:
    registry = CalculatorRegistry()
    registry.register(BaziCalculator())
    registry.register(ZiweiCalculator())
    registry.register(NameologyCalculator())
    registry.register(MbtiCalculator())
    registry.register(HumanDesignCalculator())
    registry.register(TarotCalculator())
    return registry


registry = build_default_registry()
