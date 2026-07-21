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
    result = probe.evaluate_output(raw, probe.CONFIGURATIONS[0])
    assert result["strict_parse"] is False
    assert result["error_code"] == "STRICT_JSON_PARSE_FAILURE"
    assert result["output_sha256"] == probe.sha256_bytes(raw)
    assert raw.decode() not in json.dumps(result)


def test_minimal_schema_and_rubric_pass() -> None:
    raw = probe.compact_bytes(valid_minimal())
    result = probe.evaluate_output(raw, probe.CONFIGURATIONS[0])
    assert result["strict_parse"] is True
    assert result["schema_valid"] is True
    assert result["rubric_valid"] is True
    assert result["verdict"] == "REJECT"
    assert result["hard_failure"] is True


@pytest.mark.parametrize(
    "raw",
    [
        b'{"verdict":"APPROVE","verdict":"REJECT","hard_failure":true,"findings":[]}',
        b'{"verdict":"REJECT","hard_failure":true,"findings":[{"code":"GUARANTEE_CLAIM","code":"UNSUPPORTED_AUTHORITY","severity":"HARD","message":"duplicate"}]}',
    ],
)
def test_strict_json_rejects_duplicate_keys_at_any_depth(raw: bytes) -> None:
    result = probe.evaluate_output(raw, probe.CONFIGURATIONS[0])
    assert result["strict_parse"] is False
    assert result["error_code"] == "STRICT_JSON_DUPLICATE_KEY"


def test_approve_false_empty_findings_passes_schema_and_rubric() -> None:
    judgment = {"verdict": "APPROVE", "hard_failure": False, "findings": []}
    result = probe.evaluate_output(probe.compact_bytes(judgment), probe.CONFIGURATIONS[1])
    assert result["strict_parse"] is True
    assert result["schema_valid"] is True
    assert result["rubric_valid"] is True


@pytest.mark.parametrize(
    "judgment",
    [
        {"verdict": "APPROVE", "hard_failure": True, "findings": []},
        {"verdict": "APPROVE", "hard_failure": False, "findings": valid_minimal()["findings"]},
        {"verdict": "REJECT", "hard_failure": False, "findings": valid_minimal()["findings"]},
        {"verdict": "REJECT", "hard_failure": True, "findings": []},
    ],
)
def test_rubric_rejects_cross_field_contradictions(judgment: dict[str, object]) -> None:
    configuration = probe.CONFIGURATIONS[0 if judgment["verdict"] == "REJECT" else 1]
    result = probe.evaluate_output(probe.compact_bytes(judgment), configuration)
    assert result["schema_valid"] is True
    assert result["rubric_valid"] is False
    assert result["error_code"] == "RUBRIC_FAILURE"


@pytest.mark.parametrize("message", ["", "   "])
def test_finding_message_must_be_nonblank(message: str) -> None:
    judgment = valid_minimal()
    judgment["findings"][0]["message"] = message  # type: ignore[index]
    result = probe.evaluate_output(probe.compact_bytes(judgment), probe.CONFIGURATIONS[0])
    assert result["rubric_valid"] is False
    assert result["error_code"] in {"SCHEMA_FAILURE", "RUBRIC_FAILURE"}


def test_mapper_never_guesses_missing_judgment() -> None:
    invalid = valid_minimal()
    invalid.pop("hard_failure")
    with pytest.raises(ValueError, match="invalid judgment"):
        probe.deterministic_map(invalid)


def test_rubric_requires_both_hard_failure_codes() -> None:
    invalid = valid_minimal()
    invalid["findings"] = invalid["findings"][:1]
    result = probe.evaluate_output(probe.compact_bytes(invalid), probe.CONFIGURATIONS[0])
    assert result["schema_valid"] is True
    assert result["rubric_valid"] is False
    assert result["error_code"] == "RUBRIC_FAILURE"


def test_matrix_is_exactly_six_external_processes_and_selects_go(tmp_path: Path) -> None:
    calls: list[str] = []

    def fake_runner(_cli: Path, configuration: probe.Configuration) -> dict[str, object]:
        calls.append(configuration.config_id)
        approve = configuration.expected_verdict == "APPROVE"
        return {"cli_exit_zero": True, "strict_parse": True, "schema_valid": True,
                "rubric_valid": True,
                "verdict": configuration.expected_verdict, "hard_failure": not approve,
                "output_sha256": "0" * 64,
                "output_bytes": 100, "request_sha256": "1" * 64, "stderr_bytes": 0,
                "exit_code": 0, "error_code": None, "error_position": None}

    report = probe.run_matrix(tmp_path / "fake-cli", fake_runner)
    assert len(calls) == 6
    assert report["external_cli_process_invocations"] == 6
    assert report["external_cli_process_budget"] == 6
    assert report["provider_model_calls"] == "unobservable/unknown"
    assert "model_calls" not in report
    assert "call_budget" not in report
    assert report["decision"] == "DELIVERED_CORPUS"
    assert [item["passed_3_of_3"] for item in report["configurations"]] == [True, True]


def test_schema_rejects_additional_fields() -> None:
    invalid = valid_minimal()
    invalid["explanation"] = "不允許的額外欄位"
    result = probe.evaluate_output(probe.compact_bytes(invalid), probe.CONFIGURATIONS[0])
    assert result["strict_parse"] is True
    assert result["schema_valid"] is False
    assert result["error_code"] == "SCHEMA_FAILURE"
