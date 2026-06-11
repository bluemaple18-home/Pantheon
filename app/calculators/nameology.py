from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.calculators.base import BaseDivination


ROOT_DIR = Path(__file__).resolve().parents[2]
KANGXI_CSV = ROOT_DIR / "data" / "nameology" / "kangxi-strokecount.csv"


class NameologyCalculator(BaseDivination):
    """姓名學 MVP：只把可授權的康熙筆畫資料與自建五格公式分開輸出。"""

    name = "nameology"

    def calculate(self, user_data: dict[str, Any]) -> dict[str, Any]:
        raw_name = str(user_data.get("name") or "").strip()
        normalized_name = "".join(char for char in raw_name if not char.isspace())
        strokes_table = _load_kangxi_strokes()
        characters = [
            {
                "char": char,
                "strokes": strokes_table.get(char),
                "status": "matched" if char in strokes_table else "missing",
            }
            for char in normalized_name
        ]
        matched = [item for item in characters if item["strokes"] is not None]
        provider_status = "active" if KANGXI_CSV.exists() else "missing_data"
        grid = _five_grid([int(item["strokes"]) for item in characters if item["strokes"] is not None])
        return {
            "system": self.name,
            "version": self.version,
            "provider": "kangxi-strokecount",
            "provider_status": provider_status,
            "ruleset_version": "pantheon-nameology-rules-mvp-0.1",
            "algorithm_level": "kangxi_strokes_five_grid_mvp",
            "notice": "康熙筆畫使用 MIT CSV；五格與三才只輸出本系統 MVP 數字與元素，不輸出未審吉凶斷語。",
            "name": normalized_name,
            "characters": characters,
            "matched_count": len(matched),
            "missing_chars": [item["char"] for item in characters if item["strokes"] is None],
            "five_grid": grid,
            "three_talents": _three_talents(grid),
            "source": {
                "name": "breezyreeds/kangxi-strokecount",
                "license": "MIT",
                "path": "data/nameology/kangxi-strokecount.csv",
            },
        }


@lru_cache(maxsize=1)
def _load_kangxi_strokes() -> dict[str, int]:
    if not KANGXI_CSV.exists():
        return {}
    lines = KANGXI_CSV.read_text(encoding="utf-8-sig").splitlines()
    header_index = next((index for index, line in enumerate(lines) if line.startswith("CodePoint,")), None)
    if header_index is None:
        return {}
    reader = csv.DictReader(lines[header_index:])
    return {
        row["Character"]: int(row["Strokes"])
        for row in reader
        if row.get("Character") and row.get("Strokes", "").isdigit()
    }


def _five_grid(strokes: list[int]) -> dict[str, Any]:
    if len(strokes) < 2:
        return {"status": "insufficient_name_length"}
    surname = strokes[0]
    given = strokes[1:]
    total = sum(strokes)
    first_given = given[0]
    grid = {
        "heaven": surname + 1,
        "person": surname + first_given,
        "earth": sum(given) if len(given) > 1 else first_given + 1,
        "outer": (total - surname) + 1 if len(given) == 1 else total - (surname + first_given) + 1,
        "total": total,
    }
    return {
        "status": "mvp_single_surname_formula",
        "values": grid,
        "elements": {key: _stroke_element(value) for key, value in grid.items()},
        "formula_note": "目前採單姓公式；複姓、公司名、藝名與異體字需進入後續規則版本。",
    }


def _three_talents(grid: dict[str, Any]) -> dict[str, Any]:
    values = grid.get("values")
    if not values:
        return {"status": "unavailable"}
    return {
        "status": "mvp_stroke_tail_element",
        "sequence": [
            values["heaven"],
            values["person"],
            values["earth"],
        ],
        "elements": [
            _stroke_element(values["heaven"]),
            _stroke_element(values["person"]),
            _stroke_element(values["earth"]),
        ],
        "notice": "三才只標示天人格元素序列，不輸出吉凶表。",
    }


def _stroke_element(value: int) -> str:
    tail = value % 10
    if tail in {1, 2}:
        return "木"
    if tail in {3, 4}:
        return "火"
    if tail in {5, 6}:
        return "土"
    if tail in {7, 8}:
        return "金"
    return "水"
