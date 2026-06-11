from abc import ABC, abstractmethod
from typing import Any


class BaseDivination(ABC):
    """所有算命插件都必須實作的共同介面。"""

    name: str
    version: str = "0.1.0"

    @abstractmethod
    def calculate(self, user_data: dict[str, Any]) -> dict[str, Any]:
        """輸入標準 user_data，回傳可 JSON 序列化的排盤資料。"""
        raise NotImplementedError
