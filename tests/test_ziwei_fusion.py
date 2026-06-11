from app.calculators.ziwei_fusion import build_ziwei_fusion


def test_primary_only_fields_are_primary_confidence() -> None:
    fusion = build_ziwei_fusion({"life_palace": "官祿", "provider": "pantheon_ziwei"})
    field = fusion["resolved"]["life_palace"]
    assert field["value"] == "官祿"
    assert field["confidence"] == "primary"
    assert fusion["conflicts"] == []


def test_matching_external_field_becomes_high_confidence() -> None:
    fusion = build_ziwei_fusion(
        {"life_palace": "官祿", "provider": "pantheon_ziwei"},
        [{"life_palace": "官祿", "provider": "life_chart_engine"}],
    )
    assert fusion["resolved"]["life_palace"]["confidence"] == "high"


def test_mismatched_external_field_is_conflict() -> None:
    fusion = build_ziwei_fusion(
        {"life_palace": "官祿", "provider": "pantheon_ziwei"},
        [{"life_palace": "命宮", "provider": "life_chart_engine"}],
    )
    field = fusion["resolved"]["life_palace"]
    assert field["confidence"] == "conflict"
    assert fusion["conflicts"] == [field]
