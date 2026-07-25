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
