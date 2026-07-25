from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from typing import Any

import pytest

from scripts import agy_gemini_v4_structured_target as target


SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
}


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self.body = target.canonical_json(payload)

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, amount: int) -> bytes:
        return self.body[:amount]


class RawResponse(FakeResponse):
    def __init__(self, body: bytes) -> None:
        self.body = body


def _provider_response(*, text: str = '{"ok":true}', finish_reason: str = "STOP") -> dict[str, Any]:
    return {
        "candidates": [
            {
                "finishReason": finish_reason,
                "content": {"role": "model", "parts": [{"text": text}]},
            }
        ],
        "modelVersion": "gemini-test-version",
        "responseId": "opaque-response-id",
    }


def test_single_request_uses_native_schema_and_returns_canonical_object() -> None:
    raw_request = target.encode_target_request("writer", "公開文章任務", SCHEMA)
    calls: list[tuple[object, float]] = []

    def opener(request: object, *, timeout: float) -> FakeResponse:
        calls.append((request, timeout))
        return FakeResponse(_provider_response(text=' { "ok" : true } '))

    result = target.execute_single_request(
        raw_request,
        model="gemini-3.5-flash",
        credential="synthetic-api-key-with-safe-length",
        timeout_seconds=120,
        opener=opener,
    )

    assert result == b'{"ok":true}'
    assert len(calls) == 1
    request, timeout = calls[0]
    payload = json.loads(request.data)
    assert timeout == 120
    assert request.full_url.endswith("/v1beta/models/gemini-3.5-flash:generateContent")
    assert request.headers["X-goog-api-key"] == "synthetic-api-key-with-safe-length"
    assert payload["generationConfig"] == {
        "temperature": 0.45,
        "responseMimeType": "application/json",
        "responseJsonSchema": SCHEMA,
        "thinkingConfig": {"thinkingLevel": "LOW"},
        "maxOutputTokens": target.MAX_OUTPUT_TOKENS,
    }
    assert payload["contents"] == [{"role": "user", "parts": [{"text": "公開文章任務"}]}]
    assert payload["systemInstruction"]["parts"][0]["text"] == target.ROLE_INSTRUCTIONS["writer"]


def test_provider_schema_projection_is_versioned_and_keeps_full_caller_schema_local() -> None:
    caller_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "title": {"type": "string", "minLength": 1, "maxLength": 120},
            "score": {"type": "number", "minimum": 0, "maximum": 1},
            "tags": {
                "type": "array",
                "minItems": 1,
                "maxItems": 3,
                "items": {"type": "string", "enum": ["a", "b"]},
            },
        },
        "required": ["title", "score", "tags"],
    }
    raw_request = target.encode_target_request(
        "writer",
        "公開文章任務",
        caller_schema,
    )
    calls: list[object] = []

    def opener(request: object, *, timeout: float) -> FakeResponse:
        calls.append(request)
        assert timeout == 120
        return FakeResponse(
            _provider_response(
                text='{"title":"x","score":1,"tags":["a"]}',
            )
        )

    target.execute_single_request(
        raw_request,
        model="gemini-3.5-flash",
        credential="synthetic-api-key-with-safe-length",
        timeout_seconds=120,
        opener=opener,
    )

    assert target.PROVIDER_SCHEMA_PROJECTION_VERSION == 1
    assert json.loads(raw_request)["response_schema"] == caller_schema
    provider_schema = json.loads(calls[0].data)["generationConfig"]["responseJsonSchema"]
    assert provider_schema == {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "title": {"type": "string"},
            "score": {"type": "number", "minimum": 0, "maximum": 1},
            "tags": {
                "type": "array",
                "minItems": 1,
                "maxItems": 3,
                "items": {"type": "string", "enum": ["a", "b"]},
            },
        },
        "required": ["title", "score", "tags"],
    }


@pytest.mark.parametrize(
    "child_schema",
    (
        {"type": "boolean", "enum": [True]},
        {"type": "string", "minimum": 0},
        {"type": "number", "format": "date-time"},
        {"type": "string", "enum": [1]},
        {"type": "integer", "enum": [True]},
        {"type": "number", "enum": [float("inf")]},
        {"type": "number", "minimum": float("nan")},
        {"type": "integer", "minimum": 0.5},
        {"type": "string", "format": "email"},
    ),
    ids=(
        "boolean-enum",
        "string-minimum",
        "number-format",
        "string-wrong-enum",
        "integer-bool-enum",
        "number-nonfinite-enum",
        "number-nonfinite-bound",
        "integer-nonintegral-bound",
        "string-unsupported-format",
    ),
)
def test_provider_schema_projection_rejects_invalid_typed_subset_before_http(
    child_schema: dict[str, object],
) -> None:
    calls = 0

    def opener(_request: object, *, timeout: float) -> FakeResponse:
        nonlocal calls
        calls += 1
        assert timeout == 30
        return FakeResponse(_provider_response(text='{"value":null}'))

    caller_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {"value": child_schema},
        "required": ["value"],
    }

    with pytest.raises(ValueError):
        raw_request = target.encode_target_request(
            "writer",
            "公開文章任務",
            caller_schema,
        )
        target.execute_single_request(
            raw_request,
            model="gemini-3.5-flash",
            credential="synthetic-api-key-with-safe-length",
            timeout_seconds=30,
            opener=opener,
        )

    assert calls == 0


def test_provider_schema_projection_accepts_closed_typed_subset() -> None:
    caller_schema = {
        "type": "object",
        "title": "typed provider schema",
        "description": "closed supported subset",
        "additionalProperties": False,
        "properties": {
            "published_at": {
                "type": "string",
                "enum": ["2026-07-25T00:00:00Z"],
                "format": "date-time",
                "minLength": 1,
                "maxLength": 64,
            },
            "ratio": {
                "type": "number",
                "enum": [0, 0.5, 1],
                "minimum": 0,
                "maximum": 1,
            },
            "count": {
                "type": "integer",
                "enum": [1, 2],
                "minimum": 1,
                "maximum": 2,
            },
            "flags": {
                "type": "array",
                "minItems": 1,
                "maxItems": 2,
                "items": {"type": "boolean"},
            },
            "nothing": {"type": "null"},
        },
        "required": ["published_at", "ratio", "count", "flags", "nothing"],
    }

    projection = target.project_provider_schema(caller_schema)

    assert projection["properties"]["published_at"] == {
        "type": "string",
        "enum": ["2026-07-25T00:00:00Z"],
        "format": "date-time",
    }
    assert projection["properties"]["ratio"] == {
        "type": "number",
        "enum": [0, 0.5, 1],
        "minimum": 0,
        "maximum": 1,
    }
    assert projection["properties"]["count"] == {
        "type": "integer",
        "enum": [1, 2],
        "minimum": 1,
        "maximum": 2,
    }
    assert projection["properties"]["flags"] == {
        "type": "array",
        "minItems": 1,
        "maxItems": 2,
        "items": {"type": "boolean"},
    }
    assert projection["properties"]["nothing"] == {"type": "null"}


@pytest.mark.parametrize("finish_reason", ("MAX_TOKENS", "SAFETY", "OTHER"))
def test_non_stop_finish_reason_fails_closed_without_returning_partial_text(
    finish_reason: str,
) -> None:
    calls = 0

    def opener(_request: object, *, timeout: float) -> FakeResponse:
        nonlocal calls
        calls += 1
        assert timeout == 30
        return FakeResponse(_provider_response(text='{"ok":', finish_reason=finish_reason))

    expected = "OUTPUT_TRUNCATED" if finish_reason == "MAX_TOKENS" else (
        "OUTPUT_BLOCKED" if finish_reason == "SAFETY" else "OUTPUT_INCOMPLETE"
    )
    with pytest.raises(target.TargetFailure, match=expected):
        target.execute_single_request(
            target.encode_target_request("reviewer", "公開審查任務", SCHEMA),
            model="gemini-3.1-pro-preview",
            credential="synthetic-api-key-with-safe-length",
            timeout_seconds=30,
            opener=opener,
        )

    assert calls == 1


def test_http_503_is_one_request_and_does_not_persist_response_body() -> None:
    calls = 0
    private_body = b"must-not-surface"

    def opener(request: object, *, timeout: float) -> FakeResponse:
        nonlocal calls
        calls += 1
        raise urllib.error.HTTPError(
            request.full_url,
            503,
            "unavailable",
            {},
            io.BytesIO(private_body),
        )

    with pytest.raises(target.TargetFailure) as failure:
        target.execute_single_request(
            target.encode_target_request("writer", "公開文章任務", SCHEMA),
            model="gemini-3.5-flash",
            credential="synthetic-api-key-with-safe-length",
            timeout_seconds=30,
            opener=opener,
        )

    assert calls == 1
    assert str(failure.value) == "PROVIDER_UNAVAILABLE"
    assert private_body.decode() not in str(failure.value)


@pytest.mark.parametrize(
    "response",
    (
        {},
        {"candidates": []},
        {"candidates": [{}, {}]},
        {"candidates": [{"finishReason": "STOP", "content": {"parts": []}}]},
        _provider_response(text="not-json"),
        _provider_response(text="[]"),
    ),
)
def test_malformed_provider_envelope_fails_closed(response: object) -> None:
    with pytest.raises(target.TargetFailure):
        target.execute_single_request(
            target.encode_target_request("writer", "公開文章任務", SCHEMA),
            model="gemini-3.5-flash",
            credential="synthetic-api-key-with-safe-length",
            timeout_seconds=30,
            opener=lambda _request, timeout: FakeResponse(response),
        )


@pytest.mark.parametrize(
    "value",
    (float("nan"), float("inf"), float("-inf")),
    ids=("nan", "infinity", "negative-infinity"),
)
def test_canonical_json_rejects_nonfinite_numbers(value: float) -> None:
    with pytest.raises(ValueError):
        target.canonical_json({"nested": {"value": value}})


@pytest.mark.parametrize("constant", ("NaN", "Infinity", "-Infinity"))
@pytest.mark.parametrize("boundary", ("provider-envelope", "provider-text"))
def test_provider_json_boundaries_reject_nonfinite_constants(
    constant: str,
    boundary: str,
) -> None:
    caller_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {"score": {"type": "number"}},
        "required": ["score"],
    }
    if boundary == "provider-envelope":
        body = (
            '{"candidates":[{"finishReason":"STOP","content":{"parts":'
            '[{"text":"{\\"score\\":0}"}]}}],"nonfinite":'
            f"{constant}"
            "}"
        ).encode()
    else:
        body = target.canonical_json(
            _provider_response(text=f'{{"score":{constant}}}')
        )

    with pytest.raises(target.TargetFailure, match="ENVELOPE_INVALID"):
        target.execute_single_request(
            target.encode_target_request(
                "writer",
                "公開文章任務",
                caller_schema,
            ),
            model="gemini-3.5-flash",
            credential="synthetic-api-key-with-safe-length",
            timeout_seconds=30,
            opener=lambda _request, timeout: RawResponse(body),
        )


def test_target_request_is_canonical_closed_and_contains_no_credential() -> None:
    encoded = target.encode_target_request("reviewer", "公開審查任務", SCHEMA)
    assert encoded == target.canonical_json(json.loads(encoded))
    assert set(json.loads(encoded)) == {"schema_version", "role", "prompt", "response_schema"}
    assert b"api-key" not in encoded


def test_unsupported_or_open_schema_is_rejected_before_http() -> None:
    for schema in (
        {"type": "object", "properties": {}, "required": []},
        {
            "type": "object",
            "additionalProperties": False,
            "properties": {},
            "required": [],
            "patternProperties": {},
        },
    ):
        with pytest.raises(ValueError):
            target.encode_target_request("writer", "公開文章任務", schema)


def test_default_http_handler_refuses_redirect_replay() -> None:
    handler = target._NoRedirectHandler()
    assert handler.redirect_request(
        urllib.request.Request("https://example.invalid"),
        None,
        307,
        "redirect",
        {},
        "https://other.invalid",
    ) is None
