from __future__ import annotations

from scripts.generate_content_matrix_v2 import build_rows


def test_money_scenario_uses_family_aware_public_copy() -> None:
    rows = [row for row in build_rows() if row["id"].endswith("-MONEY")]

    assert rows
    assert all(row["scenario"] == "金錢" for row in rows)
    assert all("在金錢中" not in row["primaryKeyword"] for row in rows)
    assert all("在金錢中" not in row["title"] for row in rows)
    assert all("在金錢中" not in row["intent"] for row in rows)

    by_id = {row["id"]: row for row in rows}
    assert by_id["V2-TAROT-DEATH-MONEY"] == {
        **by_id["V2-TAROT-DEATH-MONEY"],
        "primaryKeyword": "塔羅死神財運",
        "title": "塔羅死神財運怎麼看？從牌義、取捨與風險選擇理解限制",
        "intent": "問財運時抽到死神，想理解這張牌對取捨、收入變動與風險選擇提供什麼提醒，以及不能據此斷定什麼",
    }
    assert by_id["V2-ZODIAC-ARIES-MONEY"]["primaryKeyword"] == "牡羊座財運"
    assert by_id["V2-MBTI-INTJ-MONEY"]["primaryKeyword"] == "INTJ理財方式"
    assert by_id["V2-ZIWEI-ZIWEI-MONEY"]["primaryKeyword"] == "紫微星財運"
    assert by_id["V2-BAZI-ZHENGCAI-MONEY"]["primaryKeyword"] == "八字正財與財運"


def test_public_copy_keeps_matrix_cardinality_and_uniqueness() -> None:
    rows = build_rows()

    assert len(rows) == 1720
    assert len({row["id"] for row in rows}) == len(rows)
    assert len({row["primaryKeyword"] for row in rows}) == len(rows)
    assert len({row["title"] for row in rows}) == len(rows)
    assert all(20 <= len(row["title"]) <= 45 for row in rows)
