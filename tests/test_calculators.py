from app.calculators.bazi import BaziCalculator
from app.calculators.bazi_items import calculate_bazi_items
from app.calculators.mbti import MbtiCalculator
from app.calculators.nameology import NameologyCalculator
from app.calculators.ziwei import ZiweiCalculator
from app.calculators.ziwei_items import calculate_ziwei_items
from app.core.registry import build_default_registry


USER_DATA = {
    "name": "demo",
    "birth_date": "1990-05-15",
    "birth_time": "15:30:00",
    "gender": "female",
    "timezone": "Asia/Taipei",
    "calendar": "solar",
}


def test_bazi_returns_standard_payload() -> None:
    result = BaziCalculator().calculate(USER_DATA)
    assert result["system"] == "bazi"
    assert set(result["pillars"]) == {"year", "month", "day", "hour"}
    assert result["day_master"]["stem"]
    assert result["calendar_engine"]["provider_status"] in {"active", "fallback"}
    assert result["ruleset_version"] == "pantheon-bazi-rules-mvp-0.2"
    assert set(result["hidden_stems"]) == {"year", "month", "day", "hour"}
    assert result["ten_gods"]["year"]["hidden_stems"]
    assert {"stem", "god", "weight", "source_branch"} <= set(
        result["ten_gods"]["year"]["hidden_stems"][0]
    )
    assert result["calculated_items"]["policy"]["source"] == "pantheon_deterministic_rules"
    assert set(result["calculated_items"]) >= {"growth_states", "special_forces", "shensha"}


def test_bazi_calculates_confirmed_items_from_backend(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.calculators.bazi._lunar_python_pillars",
        lambda *_: {"year": "己巳", "month": "庚午", "day": "丙午", "hour": "庚寅"},
    )

    result = BaziCalculator().calculate({**USER_DATA, "birth_date": "1989-06-15", "birth_time": "04:00:00"})
    items = result["calculated_items"]
    shensha_labels = {item["label"] for item in items["shensha"]}
    force_labels = {item["label"] for item in items["special_forces"]}
    growth_labels = {item["label"] for item in items["growth_states"]}

    assert {"六秀", "月德", "桃花"} <= shensha_labels
    assert {"祿", "羊刃"} <= force_labels
    assert {"長生", "帝旺"} <= growth_labels
    assert next(item for item in items["shensha"] if item["label"] == "月德")["basis"] == "月令月德"


def test_bazi_items_engine_is_standalone() -> None:
    hidden_stems = {
        "year": [{"stem": "丙"}],
        "month": [{"stem": "丁"}],
        "day": [{"stem": "丁"}],
        "hour": [{"stem": "甲"}],
    }
    items = calculate_bazi_items(
        "丙",
        {"year": "己巳", "month": "庚午", "day": "丙午", "hour": "庚寅"},
        hidden_stems,
    )

    assert items["policy"]["source"] == "pantheon_deterministic_rules"
    assert {item["label"] for item in items["shensha"]} >= {"六秀", "月德", "桃花"}
    assert {item["label"] for item in items["special_forces"]} == {"祿", "羊刃"}


def test_bazi_marks_calendar_fallback_when_lunar_python_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr("app.calculators.bazi._lunar_python_pillars", lambda *_: None)

    result = BaziCalculator().calculate(USER_DATA)

    assert result["calendar_engine"]["provider"] == "pantheon-internal"
    assert result["calendar_engine"]["provider_status"] == "fallback"
    assert result["algorithm_level"] == "mvp_scaffold"
    assert "不是正式節氣換月" in result["notice"]


def test_bazi_can_use_lunar_python_provider(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.calculators.bazi._lunar_python_pillars",
        lambda *_: {"year": "庚午", "month": "辛巳", "day": "庚辰", "hour": "甲申"},
    )

    result = BaziCalculator().calculate(USER_DATA)

    assert result["pillars"] == {"year": "庚午", "month": "辛巳", "day": "庚辰", "hour": "甲申"}
    assert result["calendar_engine"]["provider"] == "lunar-python"
    assert result["calendar_engine"]["provider_status"] == "active"
    assert result["calendar_engine"]["policies"]["month_boundary"] == "solar_term_by_provider"


def test_bazi_luck_cycles_distinguish_decade_and_annual_theme() -> None:
    result = BaziCalculator().calculate({**USER_DATA, "target_year": 2026})
    luck = result["luck_cycles"]
    assert luck["current_decade"]["theme"] != luck["annual"]["theme"]
    assert "十年主軸" in luck["current_decade"]["theme"]
    assert "今年" in luck["annual"]["theme"]
    assert luck["annual"]["interaction_summary"]
    assert luck["qiyun"]["status"] == "computed"
    assert luck["qiyun"]["direction"] in {"forward", "reverse"}
    assert luck["qiyun"]["start_solar"]
    assert len(luck["annual"]["flow_months"]) == 12


def test_bazi_luck_direction_uses_gender_and_year_polarity() -> None:
    male = BaziCalculator().calculate({**USER_DATA, "gender": "male"})
    female = BaziCalculator().calculate({**USER_DATA, "gender": "female"})

    assert male["luck_cycles"]["qiyun"]["direction"] == "forward"
    assert female["luck_cycles"]["qiyun"]["direction"] == "reverse"
    assert male["luck_cycles"]["decade_cycles"][0]["pillar"] != female["luck_cycles"]["decade_cycles"][0]["pillar"]


def test_bazi_computes_true_solar_time_and_strength_candidate() -> None:
    result = BaziCalculator().calculate(
        {**USER_DATA, "longitude": 121.5654, "utc_offset": "+08:00"}
    )

    assert result["solar_time"]["status"] == "computed"
    assert result["solar_time"]["applied"] is False
    assert result["solar_time"]["total_correction_minutes"] != 0
    assert result["strength_analysis"]["status"] == "candidate_not_final_useful_god"
    assert result["strength_analysis"]["label"] in {
        "strong_candidate",
        "weak_candidate",
        "balanced_candidate",
    }


def test_bazi_can_apply_true_solar_time_policy() -> None:
    result = BaziCalculator().calculate(
        {
            **USER_DATA,
            "longitude": 121.5654,
            "utc_offset": "+08:00",
            "use_true_solar_time": True,
        }
    )

    assert result["solar_time"]["status"] == "computed"
    assert result["solar_time"]["applied"] is True
    assert result["solar_time"]["true_solar_time"].endswith("15:40:00")
    assert result["calendar_engine"]["provider"] == "lunar-python"


def test_ziwei_returns_palace_payload() -> None:
    result = ZiweiCalculator().calculate(USER_DATA)
    assert result["system"] == "ziwei"
    assert result["provider"] == "iztro"
    assert result["provider_status"] == "active"
    assert len(result["palaces"]) == 12
    assert result["life_palace"]
    assert result["reference_dataset"]["status"] == "active"
    assert result["calculated_items"]["policy"]["source"] == "pantheon_ziwei_focus_filter"
    assert "support_stars" in result["calculated_items"]


def test_ziwei_items_engine_filters_focus_palaces() -> None:
    items = calculate_ziwei_items(
        [
            {"name": "命宮", "stars": ["天機", "文昌"]},
            {"name": "官祿", "stars": ["左輔", "天鉞"]},
            {"name": "兄弟", "stars": ["天魁"]},
        ]
    )

    labels = [item["label"] for item in items["support_stars"]]
    assert labels == ["文昌", "天鉞", "左輔"]
    assert "兄弟" not in {item["palace"] for item in items["support_stars"]}


def test_ziwei_falls_back_when_iztro_bridge_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr("app.calculators.ziwei._calculate_with_iztro", lambda *_: None)

    result = ZiweiCalculator().calculate(USER_DATA)

    assert result["provider"] == "pantheon_ziwei"
    assert result["provider_status"] == "fallback"
    assert result["algorithm_level"] == "mvp_scaffold"


def test_registry_calculates_many() -> None:
    registry = build_default_registry()
    result = registry.calculate_many(["bazi", "nameology", "ziwei"], USER_DATA)
    assert sorted(result) == ["bazi", "nameology", "ziwei"]


def test_nameology_uses_kangxi_stroke_data() -> None:
    result = NameologyCalculator().calculate({**USER_DATA, "name": "王小明"})

    assert result["system"] == "nameology"
    assert result["provider"] == "kangxi-strokecount"
    assert result["provider_status"] == "active"
    assert result["matched_count"] == 3
    assert result["five_grid"]["status"] == "mvp_single_surname_formula"
    assert result["three_talents"]["elements"]


def test_mbti_scores_self_report_answers() -> None:
    answers = []
    for dimension, direction in [
        ("EI", "I"),
        ("SN", "N"),
        ("TF", "T"),
        ("JP", "J"),
        ("AO", "A"),
        ("HC", "H"),
    ]:
        for index in range(8):
            answers.append(
                {
                    "question_id": f"mbti.{dimension.lower()}.{index + 1:02d}",
                    "dimension": dimension,
                    "direction": direction,
                    "value": 5,
                }
            )

    result = MbtiCalculator().calculate({**USER_DATA, "personality_answers": answers})

    assert result["status"] == "scored"
    assert result["core_type"] == "INTJ"
    assert result["branch_code"] == "AH"
    assert result["type"] == "INTJ-AH"
    assert result["dimensions"]["EI"]["preferred"] == "I"
    assert result["dimensions"]["SN"]["confidence"] == "primary"
    assert result["answer_count"] == 48


def test_mbti_marks_low_margin_and_insufficient_data() -> None:
    low_margin_answers = [
        {"question_id": f"mbti.ei.{index}", "dimension": "EI", "direction": "E", "value": 3}
        for index in range(4)
    ]
    insufficient_answers = [
        {"question_id": "mbti.sn.1", "dimension": "SN", "direction": "S", "value": 5}
    ]

    low_margin = MbtiCalculator().calculate(
        {**USER_DATA, "personality_answers": low_margin_answers * 4}
    )
    insufficient = MbtiCalculator().calculate(
        {**USER_DATA, "personality_answers": insufficient_answers}
    )

    assert low_margin["dimensions"]["EI"]["confidence"] == "low_margin"
    assert insufficient["status"] == "insufficient_data"
    assert insufficient["type"] is None


def test_mbti_can_score_core_without_branch_dimensions() -> None:
    answers = []
    for dimension, direction in [("EI", "I"), ("SN", "N"), ("TF", "T"), ("JP", "J")]:
        for index in range(8):
            answers.append(
                {
                    "question_id": f"mbti.{dimension.lower()}.{index + 1:02d}",
                    "dimension": dimension,
                    "direction": direction,
                    "value": 5,
                }
            )

    result = MbtiCalculator().calculate({**USER_DATA, "personality_answers": answers})

    assert result["status"] == "scored_core"
    assert result["core_type"] == "INTJ"
    assert result["branch_code"] is None
    assert result["type"] == "INTJ"
