from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import agy_gemini_transport_probe as probe


def valid_minimal() -> dict[str, object]:
    return {
        "verdict": "REJECT",
        "hard_failure": True,
        "findings": [
            {"code": "GUARANTEE_CLAIM", "severity": "HARD", "message": "存在保證結果的說法"},
            {"code": "UNSUPPORTED_AUTHORITY", "severity": "HARD", "message": "捏造官方研究背書"},
        ],
    }


def test_strict_json_rejects_markdown_fence_without_preserving_raw() -> None:
    raw = b'```json\n{"verdict":"REJECT"}\n```'
    result = probe.evaluate_output(raw, probe.CONFIGURATIONS[1])
    assert result["strict_parse"] is False
    assert result["error_code"] == "STRICT_JSON_PARSE_FAILURE"
    assert result["output_sha256"] == probe.sha256_bytes(raw)
    assert raw.decode() not in json.dumps(result)


def test_minimal_schema_and_rubric_pass() -> None:
    raw = probe.compact_bytes(valid_minimal())
    result = probe.evaluate_output(raw, probe.CONFIGURATIONS[1])
    assert result["strict_parse"] is True
    assert result["schema_valid"] is True
    assert result["rubric_valid"] is True
    assert result["verdict"] == "REJECT"
    assert result["hard_failure"] is True


def test_mapper_never_guesses_missing_judgment() -> None:
    invalid = valid_minimal()
    invalid.pop("hard_failure")
    with pytest.raises(ValueError, match="invalid judgment"):
        probe.deterministic_map(invalid)


def test_rubric_requires_both_hard_failure_codes() -> None:
    invalid = valid_minimal()
    invalid["findings"] = invalid["findings"][:1]
    result = probe.evaluate_output(probe.compact_bytes(invalid), probe.CONFIGURATIONS[1])
    assert result["schema_valid"] is True
    assert result["rubric_valid"] is False
    assert result["error_code"] == "RUBRIC_FAILURE"


def test_matrix_is_exactly_three_by_three_and_selects_go(tmp_path: Path) -> None:
    calls: list[str] = []

    def fake_runner(_cli: Path, configuration: probe.Configuration) -> dict[str, object]:
        calls.append(configuration.config_id)
        return {"cli_exit_zero": True, "strict_parse": True, "schema_valid": True,
                "rubric_valid": configuration.config_id == "minimal_mapper_pro_low",
                "verdict": "REJECT", "hard_failure": True, "output_sha256": "0" * 64,
                "output_bytes": 100, "request_sha256": "1" * 64, "stderr_bytes": 0,
                "exit_code": 0, "error_code": None, "error_position": None}

    report = probe.run_matrix(tmp_path / "fake-cli", fake_runner)
    assert len(calls) == 9
    assert report["model_calls"] == report["call_budget"] == 9
    assert report["decision"] == "GO_GEMINI_CLI_MACHINE_GATE"
    assert [item["passed_3_of_3"] for item in report["configurations"]] == [False, True, False]


def test_schema_rejects_additional_fields() -> None:
    invalid = valid_minimal()
    invalid["explanation"] = "不允許的額外欄位"
    result = probe.evaluate_output(probe.compact_bytes(invalid), probe.CONFIGURATIONS[1])
    assert result["strict_parse"] is True
    assert result["schema_valid"] is False
    assert result["error_code"] == "SCHEMA_FAILURE"
