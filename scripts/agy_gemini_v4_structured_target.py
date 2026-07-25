#!/usr/bin/env python3
"""Gemini V4 provider-native structured-output target；每次 process 只送一次 HTTP request。"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Final, Protocol


SCHEMA_VERSION: Final = 1
GEMINI_ENDPOINT: Final = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
APPROVED_MODELS: Final = frozenset({"gemini-3.5-flash", "gemini-3.1-pro-preview"})
MAX_REQUEST_BYTES: Final = 384 * 1024
MAX_PROVIDER_RESPONSE_BYTES: Final = 4 * 1024 * 1024
MAX_CREDENTIAL_BYTES: Final = 512
MAX_OUTPUT_TOKENS: Final = 32_768
PROVIDER_SCHEMA_PROJECTION_VERSION: Final = 1
API_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{20,512}$")
CALLER_SCHEMA_KEYWORDS: Final = frozenset(
    {
        "additionalProperties",
        "description",
        "enum",
        "format",
        "items",
        "maximum",
        "maxItems",
        "maxLength",
        "minimum",
        "minItems",
        "minLength",
        "properties",
        "required",
        "title",
        "type",
    }
)
PROVIDER_SCHEMA_KEYWORDS: Final = CALLER_SCHEMA_KEYWORDS - {
    "maxLength",
    "minLength",
}
MAX_SCHEMA_DEPTH: Final = 16
ROLE_INSTRUCTIONS: Final = {
    "writer": (
        "你是 Pantheon 繁體中文文章 Writer。只輸出符合 schema 的 JSON，"
        "不得加入未提供的事實或承諾。"
    ),
    "reviewer": (
        "你是獨立 Pantheon 文章 Reviewer。依規範嚴格審查，只輸出符合 schema 的 "
        "JSON；不得假設 Writer 對話內容。"
    ),
}


class ResponseLike(Protocol):
    def __enter__(self) -> "ResponseLike": ...
    def __exit__(self, *args: object) -> object: ...
    def read(self, amount: int) -> bytes: ...


OpenUrl = Callable[..., ResponseLike]


class TargetFailure(RuntimeError):
    """只帶 closed error code，禁止夾帶 provider body、prompt 或 credential。"""


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        _request: urllib.request.Request,
        _fp: object,
        _code: int,
        _message: str,
        _headers: object,
        _new_url: str,
    ) -> None:
        return None


_HTTP_OPENER = urllib.request.build_opener(_NoRedirectHandler())


def _open_without_redirect(
    request: urllib.request.Request,
    *,
    timeout: float,
) -> ResponseLike:
    return _HTTP_OPENER.open(request, timeout=timeout)


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _validate_caller_schema(schema: object, depth: int = 0) -> None:
    if depth > MAX_SCHEMA_DEPTH or not isinstance(schema, dict):
        raise ValueError("structured target schema is invalid")
    if not set(schema) <= CALLER_SCHEMA_KEYWORDS:
        raise ValueError("structured target schema keyword is unsupported")
    schema_type = schema.get("type")
    if schema_type not in {"object", "array", "string", "boolean", "integer", "number", "null"}:
        raise ValueError("structured target schema type is unsupported")
    if schema_type == "object":
        if schema.get("additionalProperties") is not False:
            raise ValueError("structured target object schema must be closed")
        properties = schema.get("properties")
        required = schema.get("required")
        if (
            not isinstance(properties, dict)
            or not isinstance(required, list)
            or not all(type(key) is str for key in properties)
            or not all(type(key) is str for key in required)
            or not set(required) <= set(properties)
        ):
            raise ValueError("structured target object schema is invalid")
        for child in properties.values():
            _validate_caller_schema(child, depth + 1)
    elif schema_type == "array":
        _validate_caller_schema(schema.get("items"), depth + 1)
    if "enum" in schema and (
        not isinstance(schema["enum"], list)
        or not schema["enum"]
    ):
        raise ValueError("structured target enum is invalid")


def project_provider_schema(response_schema: dict[str, Any]) -> dict[str, Any]:
    """投影為 Gemini responseJsonSchema 官方支援的 deterministic v1 subset。"""
    _validate_caller_schema(response_schema)

    def project(schema: dict[str, Any]) -> dict[str, Any]:
        projected: dict[str, Any] = {}
        for keyword in sorted(schema):
            if keyword not in PROVIDER_SCHEMA_KEYWORDS:
                continue
            value = schema[keyword]
            if keyword == "properties":
                projected[keyword] = {
                    name: project(child)
                    for name, child in sorted(value.items())
                }
            elif keyword == "items":
                projected[keyword] = project(value)
            else:
                projected[keyword] = value
        return projected

    return project(response_schema)


def encode_target_request(
    role: str,
    prompt: str,
    response_schema: dict[str, Any],
) -> bytes:
    if role not in ROLE_INSTRUCTIONS:
        raise ValueError("structured target role is invalid")
    if type(prompt) is not str or not prompt:
        raise ValueError("structured target prompt is invalid")
    if not isinstance(response_schema, dict) or response_schema.get("type") != "object":
        raise ValueError("structured target schema must describe an object")
    _validate_caller_schema(response_schema)
    encoded = canonical_json(
        {
            "schema_version": SCHEMA_VERSION,
            "role": role,
            "prompt": prompt,
            "response_schema": response_schema,
        }
    )
    if len(encoded) > MAX_REQUEST_BYTES:
        raise ValueError("structured target request exceeds maximum size")
    return encoded


def _decode_target_request(raw_request: bytes) -> dict[str, Any]:
    if not raw_request or len(raw_request) > MAX_REQUEST_BYTES:
        raise TargetFailure("REQUEST_INVALID")
    try:
        payload = json.loads(raw_request)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise TargetFailure("REQUEST_INVALID") from error
    required = {"schema_version", "role", "prompt", "response_schema"}
    if not isinstance(payload, dict) or set(payload) != required:
        raise TargetFailure("REQUEST_INVALID")
    try:
        expected = encode_target_request(
            payload["role"],
            payload["prompt"],
            payload["response_schema"],
        )
    except (KeyError, TypeError, ValueError) as error:
        raise TargetFailure("REQUEST_INVALID") from error
    if raw_request != expected:
        raise TargetFailure("REQUEST_INVALID")
    return payload


def _provider_payload(request: dict[str, Any]) -> dict[str, Any]:
    role = request["role"]
    return {
        "systemInstruction": {
            "parts": [{"text": ROLE_INSTRUCTIONS[role]}],
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": request["prompt"]}],
            }
        ],
        "generationConfig": {
            "temperature": 0.45 if role == "writer" else 0.1,
            "responseMimeType": "application/json",
            "responseJsonSchema": project_provider_schema(
                request["response_schema"],
            ),
            "thinkingConfig": {"thinkingLevel": "LOW"},
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
        },
    }


def _extract_structured_result(payload: object) -> bytes:
    if not isinstance(payload, dict):
        raise TargetFailure("ENVELOPE_INVALID")
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 1:
        raise TargetFailure("ENVELOPE_INVALID")
    candidate = candidates[0]
    if not isinstance(candidate, dict):
        raise TargetFailure("ENVELOPE_INVALID")
    finish_reason = candidate.get("finishReason")
    if finish_reason != "STOP":
        if finish_reason == "MAX_TOKENS":
            raise TargetFailure("OUTPUT_TRUNCATED")
        if finish_reason in {
            "BLOCKLIST",
            "MODEL_ARMOR",
            "PROHIBITED_CONTENT",
            "RECITATION",
            "SAFETY",
            "SPII",
        }:
            raise TargetFailure("OUTPUT_BLOCKED")
        raise TargetFailure("OUTPUT_INCOMPLETE")
    content = candidate.get("content")
    parts = content.get("parts") if isinstance(content, dict) else None
    if not isinstance(parts, list):
        raise TargetFailure("ENVELOPE_INVALID")
    text_parts: list[str] = []
    for part in parts:
        if not isinstance(part, dict):
            raise TargetFailure("ENVELOPE_INVALID")
        if part.get("thought") is True:
            continue
        if not set(part) <= {"text", "thought", "thoughtSignature"}:
            raise TargetFailure("ENVELOPE_INVALID")
        text = part.get("text")
        if type(text) is not str or not text:
            raise TargetFailure("ENVELOPE_INVALID")
        text_parts.append(text)
    if len(text_parts) != 1:
        raise TargetFailure("ENVELOPE_INVALID")
    try:
        result = json.loads(text_parts[0])
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise TargetFailure("ENVELOPE_INVALID") from error
    if not isinstance(result, dict):
        raise TargetFailure("ENVELOPE_INVALID")
    return canonical_json(result)


def execute_single_request(
    raw_request: bytes,
    *,
    model: str,
    credential: str,
    timeout_seconds: int,
    opener: OpenUrl = _open_without_redirect,
) -> bytes:
    if model not in APPROVED_MODELS:
        raise TargetFailure("REQUEST_INVALID")
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 3600:
        raise TargetFailure("REQUEST_INVALID")
    if type(credential) is not str or API_KEY_PATTERN.fullmatch(credential) is None:
        raise TargetFailure("CREDENTIAL_INVALID")
    request_payload = _decode_target_request(raw_request)
    url = GEMINI_ENDPOINT.format(model=urllib.parse.quote(model, safe=""))
    provider_request = urllib.request.Request(
        url,
        data=canonical_json(_provider_payload(request_payload)),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": credential,
        },
        method="POST",
    )
    try:
        with opener(provider_request, timeout=timeout_seconds) as response:
            encoded_response = response.read(MAX_PROVIDER_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as error:
        if error.code in {401, 403}:
            code = "AUTH_FAILED"
        elif error.code == 429:
            code = "RATE_LIMITED"
        elif error.code in {408, 500, 502, 503, 504}:
            code = "PROVIDER_UNAVAILABLE"
        else:
            code = "PROVIDER_REJECTED"
        raise TargetFailure(code) from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise TargetFailure("TRANSPORT_ERROR") from error
    if len(encoded_response) > MAX_PROVIDER_RESPONSE_BYTES:
        raise TargetFailure("ENVELOPE_INVALID")
    try:
        response_payload = json.loads(encoded_response)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise TargetFailure("ENVELOPE_INVALID") from error
    return _extract_structured_result(response_payload)


def _read_credential(descriptor: int) -> str:
    if type(descriptor) is not int or descriptor < 3:
        raise TargetFailure("CREDENTIAL_INVALID")
    chunks = bytearray()
    while len(chunks) <= MAX_CREDENTIAL_BYTES:
        chunk = os.read(descriptor, MAX_CREDENTIAL_BYTES + 1 - len(chunks))
        if not chunk:
            break
        chunks.extend(chunk)
    if len(chunks) > MAX_CREDENTIAL_BYTES:
        raise TargetFailure("CREDENTIAL_INVALID")
    try:
        credential = bytes(chunks).decode("utf-8").strip()
    except UnicodeDecodeError as error:
        raise TargetFailure("CREDENTIAL_INVALID") from error
    if API_KEY_PATTERN.fullmatch(credential) is None:
        raise TargetFailure("CREDENTIAL_INVALID")
    return credential


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, choices=sorted(APPROVED_MODELS))
    parser.add_argument("--credential-fd", required=True, type=int)
    parser.add_argument("--timeout-seconds", required=True, type=int)
    return parser.parse_args()


def main() -> int:
    arguments = _parse_args()
    try:
        credential = _read_credential(arguments.credential_fd)
        os.close(arguments.credential_fd)
        raw_request = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
        result = execute_single_request(
            raw_request,
            model=arguments.model,
            credential=credential,
            timeout_seconds=arguments.timeout_seconds,
        )
    except TargetFailure as error:
        sys.stderr.write(f"{error}\n")
        return 70
    except Exception:
        sys.stderr.write("INTERNAL_ERROR\n")
        return 70
    sys.stdout.buffer.write(result)
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
