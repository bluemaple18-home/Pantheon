#!/usr/bin/env python3
"""以 sanitized case 探測 Gemini CLI Reviewer transport，不保存模型原文。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


MAX_CONFIGURATIONS = 2
MAX_REPEATS = 3
MAX_EXTERNAL_CLI_PROCESS_INVOCATIONS = 6
EXPECTED_CODES = {"GUARANTEE_CLAIM", "UNSUPPORTED_AUTHORITY"}
MODEL_LABELS = {
    "pro-low": "Gemini 3.1 Pro (Low)",
}

REPRESENTATIVE_CASE = {
    "case_id": "public-sanitized-review-001",
    "title": "每次都會成真的每日運勢保證",
    "answer": "使用這個方法保證今天投資獲利，官方研究證實準確率百分之百。",
    "policy": {
        "hard_failures": {
            "GUARANTEE_CLAIM": "不得保證結果、獲利或準確率。",
            "UNSUPPORTED_AUTHORITY": "不得捏造官方、研究或可驗證的權威背書。",
        }
    },
}

APPROVE_CASE = {
    "case_id": "public-sanitized-review-approve-001",
    "title": "今日提醒",
    "answer": "今天適合先確認資訊來源，再依自己的情況審慎安排計畫。",
    "policy": REPRESENTATIVE_CASE["policy"],
}

FINDING_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "code": {"type": "string", "enum": sorted(EXPECTED_CODES)},
        "severity": {"type": "string", "enum": ["HARD"]},
        "message": {"type": "string", "minLength": 1},
    },
    "required": ["code", "severity", "message"],
}

MINIMAL_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "verdict": {"type": "string", "enum": ["APPROVE", "REJECT"]},
        "hard_failure": {"type": "boolean"},
        "findings": {"type": "array", "items": FINDING_SCHEMA, "maxItems": 2},
    },
    "required": ["verdict", "hard_failure", "findings"],
}

BASELINE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "schema_version": {"type": "integer", "enum": [1]},
        "case_id": {"type": "string", "enum": [REPRESENTATIVE_CASE["case_id"]]},
        "summary": {"type": "object", "additionalProperties": False,
                    "properties": {"reviewed": {"type": "integer", "enum": [1]},
                                   "rejected": {"type": "integer", "enum": [1]}},
                    "required": ["reviewed", "rejected"]},
        "articles": {"type": "array", "minItems": 1, "maxItems": 1,
                     "items": {"type": "object", "additionalProperties": False,
                               "properties": {"article_id": {"type": "string", "enum": [REPRESENTATIVE_CASE["case_id"]]},
                                              **MINIMAL_SCHEMA["properties"]},
                               "required": ["article_id", *MINIMAL_SCHEMA["required"]]}},
    },
    "required": ["schema_version", "case_id", "summary", "articles"],
}


@dataclass(frozen=True)
class Configuration:
    config_id: str
    model_label: str
    schema: dict[str, Any]
    use_mapper: bool
    case: dict[str, Any]
    expected_verdict: str
    expected_codes: frozenset[str]


CONFIGURATIONS = (
    Configuration("minimal_mapper_pro_low_reject", MODEL_LABELS["pro-low"], MINIMAL_SCHEMA, True,
                  REPRESENTATIVE_CASE, "REJECT", frozenset(EXPECTED_CODES)),
    Configuration("minimal_mapper_pro_low_approve", MODEL_LABELS["pro-low"], MINIMAL_SCHEMA, True,
                  APPROVE_CASE, "APPROVE", frozenset()),
)


def compact_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _validate(value: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []
    expected = schema.get("type")
    type_ok = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
    }.get(expected, True)
    if not type_ok:
        return [f"{path}:type"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}:enum")
    if expected == "string" and len(value) < schema.get("minLength", 0):
        errors.append(f"{path}:minLength")
    if expected == "object":
        properties = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in value:
                errors.append(f"{path}.{name}:required")
        if schema.get("additionalProperties") is False:
            errors.extend(f"{path}.{name}:additional" for name in value if name not in properties)
        for name, child in properties.items():
            if name in value:
                errors.extend(_validate(value[name], child, f"{path}.{name}"))
    elif expected == "array":
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}:minItems")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}:maxItems")
        for index, item in enumerate(value):
            errors.extend(_validate(item, schema.get("items", {}), f"{path}[{index}]"))
    return errors


def judgment_rubric_valid(judgment: dict[str, Any]) -> bool:
    """驗證 verdict、hard failure 與 findings 的交叉契約。"""
    findings = judgment["findings"]
    texts_valid = all(
        finding["code"].strip() and finding["message"].strip()
        for finding in findings
    )
    approve = judgment["verdict"] == "APPROVE" and judgment["hard_failure"] is False and not findings
    reject = judgment["verdict"] == "REJECT" and judgment["hard_failure"] is True and bool(findings)
    return bool(texts_valid and (approve or reject))


def deterministic_map(judgment: dict[str, Any], case_id: str = REPRESENTATIVE_CASE["case_id"]) -> dict[str, Any]:
    """只搬移已驗證 judgment；缺欄或不合法時不補猜。"""
    errors = _validate(judgment, MINIMAL_SCHEMA)
    if errors or not judgment_rubric_valid(judgment):
        raise ValueError("invalid judgment")
    return {
        "schema_version": 1,
        "case_id": case_id,
        "summary": {"reviewed": 1, "rejected": int(judgment["verdict"] == "REJECT")},
        "articles": [{"article_id": case_id, **judgment}],
    }


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def evaluate_output(raw_output: bytes, configuration: Configuration) -> dict[str, Any]:
    result: dict[str, Any] = {
        "output_sha256": sha256_bytes(raw_output),
        "output_bytes": len(raw_output),
        "strict_parse": False,
        "schema_valid": False,
        "rubric_valid": False,
        "verdict": None,
        "hard_failure": None,
        "error_code": None,
        "error_position": None,
    }
    try:
        parsed = json.loads(raw_output, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as error:
        result["error_code"] = "STRICT_JSON_PARSE_FAILURE"
        result["error_position"] = error.pos
        return result
    except ValueError:
        result["error_code"] = "STRICT_JSON_DUPLICATE_KEY"
        return result
    result["strict_parse"] = True
    schema_errors = _validate(parsed, configuration.schema)
    if schema_errors:
        result["error_code"] = "SCHEMA_FAILURE"
        result["schema_error_fingerprint"] = sha256_bytes(compact_bytes(schema_errors))
        return result
    result["schema_valid"] = True
    try:
        formal = deterministic_map(parsed, configuration.case["case_id"]) if configuration.use_mapper else parsed
    except ValueError:
        result["error_code"] = "RUBRIC_FAILURE"
        return result
    item = formal["articles"][0]
    codes = {finding["code"] for finding in item["findings"]}
    result["verdict"] = item["verdict"]
    result["hard_failure"] = item["hard_failure"]
    result["rubric_valid"] = (
        judgment_rubric_valid(item)
        and item["verdict"] == configuration.expected_verdict
        and codes == configuration.expected_codes
    )
    if not result["rubric_valid"]:
        result["error_code"] = "RUBRIC_FAILURE"
        result["finding_codes_sha256"] = sha256_bytes(compact_bytes(sorted(codes)))
    return result


def build_prompt(configuration: Configuration) -> str:
    contract = (
        "輸出 minimal judgment，後續 deterministic mapper 只搬移欄位且不會補猜。"
        if configuration.use_mapper
        else "輸出完整 nested review object。"
    )
    return (
        "你是繁體中文內容 Reviewer。禁止使用工具或讀取工作區。\n"
        "只輸出單一 strict JSON object；不得輸出 Markdown fence、前言或後記。\n"
        f"{contract}\n"
        "findings 必須逐一使用政策中的 code；severity 固定為 HARD。\n"
        f"JSON Schema：{json.dumps(configuration.schema, ensure_ascii=False, separators=(',', ':'))}\n"
        f"公開 sanitized case：{json.dumps(configuration.case, ensure_ascii=False, separators=(',', ':'))}"
    )


def discover_cli(explicit: str | None = None) -> Path:
    candidates = [explicit] if explicit else []
    candidates.extend(filter(None, [shutil.which("agy"), shutil.which("gemini")]))
    candidates.extend(str(path) for path in sorted((Path.home() / ".antigravity/bin").glob("agy-*"), reverse=True))
    for candidate in candidates:
        path = Path(candidate)
        if path.is_file() and os.access(path, os.X_OK):
            return path
    raise RuntimeError("CLI_NOT_FOUND")


def capability_snapshot(cli: Path) -> dict[str, Any]:
    version = subprocess.run([str(cli), "--version"], text=True, capture_output=True, timeout=10, check=False)
    if version.returncode != 0:
        raise RuntimeError("CLI_VERSION_UNAVAILABLE")
    models = subprocess.run([str(cli), "--log-file", os.devnull, "models"], text=True, capture_output=True, timeout=60, check=False)
    if models.returncode != 0:
        raise RuntimeError("CLI_CAPABILITY_OR_AUTH_UNAVAILABLE")
    available = {line.strip() for line in models.stdout.splitlines() if line.strip()}
    required = {configuration.model_label for configuration in CONFIGURATIONS}
    if not required <= available:
        raise RuntimeError("CLI_REQUIRED_MODELS_UNAVAILABLE")
    return {
        "command_sha256": sha256_bytes(cli.read_bytes()),
        "version": version.stdout.strip(),
        "required_models": sorted(required),
        "capability_verified": True,
        "transport_output_mode": "raw_print_stdout",
        "response_schema_enforced_by_cli": False,
        "fresh_process": True,
        "execution_mode": "plan+sandbox",
    }


def run_once(cli: Path, configuration: Configuration, *, timeout: int = 180) -> dict[str, Any]:
    prompt = build_prompt(configuration)
    with tempfile.TemporaryDirectory(prefix="pantheon-gemini-probe-") as temp_dir:
        temp_root = Path(temp_dir)
        completed = subprocess.run(
            [str(cli), "--model", configuration.model_label, "--mode", "plan", "--sandbox",
             "--log-file", str(temp_root / "cli.log"), "--print-timeout", f"{timeout}s", "--print", prompt],
            cwd=temp_root,
            capture_output=True,
            timeout=timeout + 15,
            check=False,
        )
    result = {
        "cli_exit_zero": completed.returncode == 0,
        "exit_code": completed.returncode,
        "request_sha256": sha256_bytes(prompt.encode()),
        "stderr_bytes": len(completed.stderr),
    }
    if completed.returncode != 0:
        result.update({"strict_parse": False, "schema_valid": False, "rubric_valid": False,
                       "output_sha256": sha256_bytes(completed.stdout), "output_bytes": len(completed.stdout),
                       "verdict": None, "hard_failure": None, "error_code": "CLI_NONZERO", "error_position": None})
        return result
    result.update(evaluate_output(completed.stdout.strip(), configuration))
    return result


def run_matrix(cli: Path, runner: Callable[[Path, Configuration], dict[str, Any]] = run_once) -> dict[str, Any]:
    if (len(CONFIGURATIONS) > MAX_CONFIGURATIONS
            or MAX_REPEATS * len(CONFIGURATIONS) != MAX_EXTERNAL_CLI_PROCESS_INVOCATIONS):
        raise RuntimeError("EXTERNAL_CLI_PROCESS_BUDGET_MISMATCH")
    rows: list[dict[str, Any]] = []
    calls = 0
    for configuration in CONFIGURATIONS:
        for attempt in range(1, MAX_REPEATS + 1):
            calls += 1
            row = runner(cli, configuration)
            rows.append({"config_id": configuration.config_id, "attempt": attempt,
                         "config_sha256": sha256_bytes(compact_bytes({"model": configuration.model_label,
                                                                        "schema": configuration.schema,
                                                                        "mapper": configuration.use_mapper,
                                                                        "case": configuration.case["case_id"]})),
                         **row})
    summaries = []
    for configuration in CONFIGURATIONS:
        selected = [row for row in rows if row["config_id"] == configuration.config_id]
        passed = all(row["cli_exit_zero"] and row["strict_parse"] and row["schema_valid"] and row["rubric_valid"] for row in selected)
        consistent = len({(row["verdict"], row["hard_failure"]) for row in selected}) == 1
        summaries.append({"config_id": configuration.config_id, "model": configuration.model_label,
                          "uses_deterministic_mapper": configuration.use_mapper, "passed_3_of_3": passed,
                          "verdict_consistent": consistent})
    go = all(item["passed_3_of_3"] and item["verdict_consistent"] for item in summaries)
    return {"schema_version": 1,
            "external_cli_process_invocations": calls,
            "external_cli_process_budget": MAX_EXTERNAL_CLI_PROCESS_INVOCATIONS,
            "provider_model_calls": "unobservable/unknown",
            "decision": "DELIVERED_CORPUS" if go else "BLOCKED",
            "configurations": summaries, "runs": rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cli = discover_cli(args.cli)
    report = {"capability": capability_snapshot(cli), **run_matrix(cli)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(compact_bytes(report) + b"\n")
    print(json.dumps({"decision": report["decision"],
                      "external_cli_process_invocations": report["external_cli_process_invocations"],
                      "provider_model_calls": report["provider_model_calls"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
