from app.calculators.bazi import BaziCalculator
from app.calculators.bazi_interactions import annual_relations, chart_relations, interaction_summary
from app.calculators.bazi_strength import strength_analysis
from app.calculators.ziwei_items import calculate_ziwei_items


def test_bazi_fire_day_golden_items(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.calculators.bazi._lunar_python_pillars",
        lambda *_: {"year": "己巳", "month": "庚午", "day": "丙午", "hour": "庚寅"},
    )

    result = BaziCalculator().calculate(
        {
            "birth_date": "1989-06-15",
            "birth_time": "04:00:00",
            "gender": "male",
            "timezone": "Asia/Taipei",
            "calendar": "solar",
            "target_year": 2026,
        }
    )
    items = result["calculated_items"]

    assert result["pillars"] == {"year": "己巳", "month": "庚午", "day": "丙午", "hour": "庚寅"}
    assert [item["label"] for item in items["growth_states"]] == ["長生", "臨官", "帝旺"]
    assert [item["label"] for item in items["special_forces"]] == ["祿", "羊刃"]
    assert [item["label"] for item in items["shensha"]] == ["六秀", "桃花", "月德"]


def test_bazi_water_day_golden_items(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.calculators.bazi._lunar_python_pillars",
        lambda *_: {"year": "壬申", "month": "癸卯", "day": "壬子", "hour": "庚子"},
    )

    result = BaziCalculator().calculate(
        {
            "birth_date": "1992-03-12",
            "birth_time": "23:30:00",
            "gender": "female",
            "timezone": "Asia/Taipei",
            "calendar": "solar",
            "target_year": 2026,
        }
    )
    items = result["calculated_items"]

    assert [item["label"] for item in items["growth_states"]] == ["長生", "帝旺"]
    assert [item["label"] for item in items["special_forces"]] == ["羊刃"]
    assert [item["label"] for item in items["shensha"]] == ["天乙"]


def test_ziwei_support_star_golden_filter() -> None:
    items = calculate_ziwei_items(
        [
            {"name": "命宮", "stars": ["天機", "文昌", "天喜"]},
            {"name": "官祿", "stars": ["天鉞", "左輔"]},
            {"name": "財帛", "stars": ["天魁", "祿存"]},
            {"name": "兄弟", "stars": ["文曲", "右弼"]},
        ]
    )

    assert [item["label"] for item in items["support_stars"]] == ["文昌", "祿存", "天魁", "天鉞"]
    assert {item["palace"] for item in items["support_stars"]} == {"命宮", "官祿", "財帛"}


def test_bazi_interaction_engine_golden_summary() -> None:
    pillars = {"year": "己未", "month": "庚午", "day": "丙午", "hour": "庚寅"}

    natal = chart_relations(pillars)
    annual = annual_relations("丙午", pillars)

    assert "午未合" in [item["name"] for item in natal["branch"]]
    assert "午未合" in interaction_summary(annual)


def test_bazi_strength_engine_golden_candidate() -> None:
    pillars = {"year": "己巳", "month": "庚午", "day": "丙午", "hour": "庚寅"}
    scores = {"木": 3, "火": 12, "土": 4, "金": 5, "水": 0}

    result = strength_analysis(pillars, scores, "丙")

    assert result["model"] == "pantheon_strength_v1"
    assert result["label"] == "strong_candidate"
    assert result["month_command_supports_day_master"] is True
