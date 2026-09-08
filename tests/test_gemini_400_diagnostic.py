"""400診斷只以mock HTTP走既有單次transport與failed receipt。"""
import io
import http.client
import json
import urllib.error

import pytest

from scripts import agy_seo_copy_pipeline as p
from scripts import agy_gemini_runner as runner
from scripts import agy_gemini_outbox as outbox


def body(message='The requested schema has too many states for serving.'):
    return {'error': {'status': 'INVALID_ARGUMENT', 'message': message, 'details': [
        {'@type': 'type.googleapis.com/google.rpc.BadRequest', 'fieldViolations': [
            {'field': 'generation_config.response_json_schema', 'description': 'Array length limit is too large.', 'raw': 'DO_NOT_SAVE'},
        ]}, {'@type': 'untrusted', 'secret': 'DO_NOT_SAVE'},
    ], 'raw': 'DO_NOT_SAVE'}}


def client(monkeypatch, encoded, code=400):
    calls = []
    def fail(req, **kwargs):
        calls.append(req)
        raise urllib.error.HTTPError(req.full_url, code, 'PRIVATE_REASON', {}, io.BytesIO(encoded))
    monkeypatch.setattr(p, '_single_request_urlopen', fail)
    value = p.GeminiClient(api_key='secret-credential-value', writer_model='gemini-3.5-flash')
    value.transport = value._single_request_http_transport
    return value, calls


def test_transport_failure_roundtrips_through_existing_runner_receipt(tmp_path, monkeypatch):
    for name in ['PANTHEON_FORMAL_RUNTIME', 'AGY_GEMINI_CREDENTIAL_POOL_FILE', 'AGY_GEMINI_V4_BROKER']:
        monkeypatch.delenv(name, raising=False)
    value, calls = client(monkeypatch, json.dumps(body()).encode())
    request = outbox.create_external_request(tmp_path, namespace='diagnostic', role='writer', model='gemini-3.5-flash', prompt='PRIVATE_SOURCE_CONTENT_123', response_schema={'type': 'object'})
    result = runner.process_once(tmp_path, generate_json=lambda role, model, prompt, schema: value.generate_json(role, prompt, schema))
    assert result['status'] == 'failed' and len(calls) == 1
    receipt = outbox.validate_external_failure_receipt(tmp_path, request)
    diagnostic = receipt['provider_diagnostic']
    assert diagnostic['status'] == 'INVALID_ARGUMENT'
    assert diagnostic['message'] == body()['error']['message']
    assert diagnostic['fieldViolations'] == [{'field': 'generation_config.response_json_schema', 'description': 'Array length limit is too large.'}]
    encoded = json.dumps(receipt)
    for secret in ['DO_NOT_SAVE', 'PRIVATE_REASON', 'PRIVATE_SOURCE_CONTENT_123', 'secret-credential-value']:
        assert secret not in encoded
    assert receipt['error_code'] == 'API_HTTP_ERROR'
    assert receipt['http_status'] == 400
    assert not (tmp_path / 'outbox' / (request['job_id'] + '.json')).exists()


@pytest.mark.parametrize('message', ['secret-credential-value', 'GEMINI_API_KEY=SECRET', 'PRIVATE_SOURCE_CONTENT_123', 'https://secret.invalid/path', 'x' * 769])
def test_sensitive_or_oversized_message_is_omitted(monkeypatch, message):
    value, calls = client(monkeypatch, json.dumps(body(message)).encode())
    with pytest.raises(p.GeminiApiFailure) as caught:
        value.generate_json('writer', 'PRIVATE_SOURCE_CONTENT_123', {'type': 'object'})
    assert caught.value.provider_diagnostic['status'] == 'INVALID_ARGUMENT'
    assert 'message' not in caught.value.provider_diagnostic
    assert len(calls) == 1
    assert 'PRIVATE_REASON' not in str(caught.value)


@pytest.mark.parametrize('encoded', [b'not json', b'[]', b'\xff', b' ' * (p.MAX_GEMINI_ERROR_BODY_BYTES + 1)])
def test_malformed_or_oversized_body_keeps_original_http_failure(monkeypatch, encoded):
    value, calls = client(monkeypatch, encoded)
    with pytest.raises(p.GeminiApiFailure) as caught:
        value.generate_json('writer', 'source', {'type': 'object'})
    assert caught.value.provider_diagnostic is None
    assert caught.value.http_status == 400 and len(calls) == 1


def test_failure_receipt_rejects_unbounded_or_unknown_diagnostic():
    assert p.closed_gemini_provider_diagnostic({'raw_body': 'x'}) is None
    assert p.closed_gemini_provider_diagnostic({'message': 'x' * 769}) is None
    assert p.closed_gemini_provider_diagnostic({'status': 'ANY_FREE_TEXT'}) is None
    assert p.closed_gemini_provider_diagnostic({'fieldViolations': [{'field': 'x'}] * 5}) is None


@pytest.mark.parametrize('prompt,schema,message', [
    ('甲乙丙', {'type': 'object'}, 'Invalid input: 甲乙丙'),
    ('source', {'type': 'string', 'enum': ['PRIVATE_ENUM_VALUE']}, 'Invalid value: PRIVATE_ENUM_VALUE'),
    ('source', {'type': 'string', 'description': 'PRIVATE_SCHEMA_DESCRIPTION'}, 'Invalid: PRIVATE_SCHEMA_DESCRIPTION'),
    ('source', {'type': 'object'}, 'Cannot read /var/folders/ab/q9/session.json'),
    ('source', {'type': 'object'}, 'Cannot read /tmp/q9/session.json'),
])
def test_review_sensitive_echo_cannot_enter_receipt(tmp_path, monkeypatch, prompt, schema, message):
    for name in ['PANTHEON_FORMAL_RUNTIME', 'AGY_GEMINI_CREDENTIAL_POOL_FILE', 'AGY_GEMINI_V4_BROKER']:
        monkeypatch.delenv(name, raising=False)
    value, calls = client(monkeypatch, json.dumps(body(message)).encode())
    request = outbox.create_external_request(tmp_path, namespace='diagnostic', role='writer', model='gemini-3.5-flash', prompt=prompt, response_schema=schema)
    runner.process_once(tmp_path, generate_json=lambda role, model, text, response_schema: value.generate_json(role, text, response_schema))
    receipt = outbox.validate_external_failure_receipt(tmp_path, request)
    assert len(calls) == 1 and 'message' not in receipt['provider_diagnostic']
    assert message not in json.dumps(receipt, ensure_ascii=False)


def test_incomplete_diagnostic_stream_keeps_original_400(monkeypatch):
    class IncompleteBody:
        def read(self, amount):
            assert amount == p.MAX_GEMINI_ERROR_BODY_BYTES + 1
            raise http.client.IncompleteRead(b'private', 100)
        def close(self):
            pass
    calls = []
    def fail(request, **kwargs):
        calls.append(request)
        raise urllib.error.HTTPError(request.full_url, 400, 'private', {}, IncompleteBody())
    monkeypatch.setattr(p, '_single_request_urlopen', fail)
    with pytest.raises(p.GeminiApiFailure) as caught:
        p.GeminiClient(api_key='secret')._single_request_http_transport('gemini-test', {})
    assert len(calls) == 1 and caught.value.http_status == 400
    assert caught.value.error_code == 'API_HTTP_ERROR'
    assert caught.value.provider_diagnostic is None
