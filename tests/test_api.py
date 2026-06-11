from fastapi.testclient import TestClient

from main import app


def _mbti_answers() -> list[dict[str, object]]:
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
    return answers


def test_predict_route_returns_charts_and_ai() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/predict",
        json={
            "name": "demo",
            "birth_date": "1990-05-15",
            "birth_time": "15:30:00",
            "gender": "female",
            "timezone": "Asia/Taipei",
            "calendar": "solar",
            "bazi_strength_model": "pantheon_strength_v1",
            "ziwei_school": "iztro_default",
            "nameology_luck_table": "disabled_until_audited",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert set(payload["charts"]) == {"bazi", "nameology", "ziwei"}
    assert payload["report"]["syntax_version"] == "0.2"
    assert payload["report"]["narrative_strategy"] == "evidence_chain"
    assert payload["report"]["signals"]
    assert payload["report"]["combo_cards"]
    assert payload["report"]["reading_blocks"]
    assert payload["ai"]["mode"] == "local_stub"
    assert payload["ai"]["syntax_version"] == "0.2"
    assert payload["metadata"]["engine_status"]["bazi"]["provider"] == "lunar-python"
    assert payload["metadata"]["engine_status"]["bazi"]["provider_status"] == "active"
    assert payload["metadata"]["engine_status"]["ziwei"]["provider"] == "iztro"
    assert payload["metadata"]["engine_status"]["ziwei"]["provider_status"] == "active"
    assert payload["metadata"]["engine_status"]["nameology"]["provider"] == "kangxi-strokecount"
    assert payload["metadata"]["school_policy"]["bazi"]["calendar_provider"] == "lunar-python"
    assert payload["metadata"]["school_policy"]["bazi"]["strength_model"] == "pantheon_strength_v1"
    assert payload["metadata"]["school_policy"]["bazi"]["qiyun_method"]
    assert payload["metadata"]["school_policy"]["ziwei"]["school"] == "iztro_default"
    assert payload["metadata"]["school_policy"]["nameology"]["luck_table"] == "disabled_until_audited"
    assert "metadata.school_policy" in payload["ai"]["prompt"]


def test_predict_route_returns_mbti_when_answers_are_present() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/predict",
        json={
            "name": "demo",
            "birth_date": "1990-05-15",
            "birth_time": "15:30:00",
            "gender": "female",
            "timezone": "Asia/Taipei",
            "calendar": "solar",
            "personality_answers": _mbti_answers(),
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert set(payload["charts"]) == {"bazi", "mbti", "nameology", "ziwei"}
    assert payload["charts"]["mbti"]["type"] == "INTJ-AH"
    signal_ids = {signal["id"] for signal in payload["report"]["signals"]}
    assert "mbti.dimension.ei" in signal_ids
    assert "mbti.dimension.ao" in signal_ids
    combo_ids = {card["id"] for card in payload["report"]["combo_cards"]}
    assert "combo.mbti_self_report" in combo_ids
    assert "64 分支人格只可視為個人自評偏好" in payload["ai"]["prompt"]


def test_predict_route_can_apply_true_solar_time() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/predict",
        json={
            "name": "demo",
            "birth_date": "1990-05-15",
            "birth_time": "15:30:00",
            "gender": "female",
            "timezone": "Asia/Taipei",
            "utc_offset": "+08:00",
            "longitude": 121.5654,
            "calendar": "solar",
            "use_true_solar_time": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["input"]["use_true_solar_time"] is True
    assert payload["charts"]["bazi"]["solar_time"]["applied"] is True
    assert payload["charts"]["bazi"]["solar_time"]["total_correction_minutes"] == 10.02


def test_personality_route_returns_mbti_only(monkeypatch) -> None:
    monkeypatch.setenv("PANTHEON_PERSONALITY_AI", "0")
    client = TestClient(app)
    response = client.post(
        "/api/v1/personality",
        json={"personality_answers": _mbti_answers()},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["chart"]["type"] == "INTJ-AH"
    assert payload["metadata"]["scope"] == "personality_only"
    assert payload["ai"]["mode"] == "local_fallback"
    assert payload["ai"]["summary"]
    signal_ids = {signal["id"] for signal in payload["report"]["signals"]}
    assert "mbti.dimension.ei" in signal_ids
    assert "bazi.day_master" not in signal_ids
