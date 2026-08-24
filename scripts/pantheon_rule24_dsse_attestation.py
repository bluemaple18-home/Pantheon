#!/usr/bin/env python3
"""Rule24 DSSE/OpenSSL Ed25519 離線簽驗 primitive。"""

from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence


SCHEMA_VERSION = 1
STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
PAYLOAD_TYPE = "application/vnd.in-toto+json"
PREDICATE_TYPE = "https://pantheon.local/rule24/trust-predicate/v1"
NO_SIDE_EFFECT_FLAGS = {
    "production_mutation": False,
    "canary_created": False,
}
OPENSSL_TIMEOUT_SECONDS = 5.0
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ResourceInput:
    name: str
    media_type: str
    path: Path


class Rule24AttestationError(ValueError):
    """Deterministic fail-closed reason for machine-readable NO-GO receipts."""

    def __init__(self, reason: str, message: str) -> None:
        self.reason = reason
        super().__init__(message)


def _no_go(reason: str) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "NO-GO",
        "reason": reason,
        **NO_SIDE_EFFECT_FLAGS,
    }


def _pass(mode: str, **fields: object) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "mode": mode,
        **fields,
        **NO_SIDE_EFFECT_FLAGS,
    }


def _canonical_path(path: Path | str, label: str, *, must_exist: bool = True) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise Rule24AttestationError("path_not_canonical", f"{label} must be absolute")
    try:
        resolved = candidate.resolve(strict=must_exist)
    except OSError as error:
        raise Rule24AttestationError("path_not_canonical", f"{label} must exist") from error
    if resolved != candidate:
        raise Rule24AttestationError(
            "path_not_canonical",
            f"{label} must be its canonical realpath",
        )
    if must_exist and not candidate.is_file():
        raise Rule24AttestationError("path_not_canonical", f"{label} must be a file")
    return candidate


def _canonical_directory(path: Path | str, label: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise Rule24AttestationError("path_not_canonical", f"{label} must be absolute")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise Rule24AttestationError("path_not_canonical", f"{label} must exist") from error
    if resolved != candidate:
        raise Rule24AttestationError(
            "path_not_canonical",
            f"{label} must be its canonical realpath",
        )
    if not candidate.is_dir():
        raise Rule24AttestationError("path_not_canonical", f"{label} must be a directory")
    return candidate


def _external_replay_state_dir(path: Path | str) -> Path:
    replay_state = _canonical_directory(path, "replay_state_dir")
    try:
        replay_state.relative_to(REPO_ROOT)
    except ValueError:
        return replay_state
    raise Rule24AttestationError(
        "replay_state_in_repo",
        "replay_state_dir must be outside the repository",
    )


def _identifier(value: object, label: str) -> str:
    if type(value) is not str or not value or value.strip() != value:
        raise Rule24AttestationError("contract", f"{label} must be a stable string")
    return value


def _digest_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _digest_path(path: Path) -> str:
    return _digest_bytes(path.read_bytes())


def _canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _load_json(path: Path, reason: str) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise Rule24AttestationError(reason, f"{path} is not valid JSON") from error
    if not isinstance(payload, Mapping):
        raise Rule24AttestationError(reason, f"{path} must contain a JSON object")
    return payload


def _strict_b64_decode(value: object, reason: str) -> bytes:
    if type(value) is not str:
        raise Rule24AttestationError(reason, "base64 field must be a string")
    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError) as error:
        raise Rule24AttestationError(reason, "base64 field is invalid") from error


def _openssl_run(args: Sequence[str], *, input_bytes: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    try:
        completed = subprocess.run(
            ["openssl", *args],
            input=input_bytes,
            check=False,
            capture_output=True,
            timeout=OPENSSL_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as error:
        raise Rule24AttestationError("openssl_missing", "openssl is not on PATH") from error
    except subprocess.TimeoutExpired as error:
        raise Rule24AttestationError("openssl_timeout", "openssl command timed out") from error
    except OSError as error:
        raise Rule24AttestationError("openssl_missing", "openssl cannot be executed") from error
    if completed.returncode != 0:
        raise Rule24AttestationError("openssl_nonzero", "openssl command failed")
    return completed


def _stdout_text(completed: subprocess.CompletedProcess[bytes]) -> str:
    stdout = completed.stdout
    if isinstance(stdout, bytes):
        return stdout.decode("utf-8", "replace")
    return str(stdout)


def openssl_capability_receipt() -> dict[str, object]:
    """Read-only OpenSSL Ed25519 capability receipt."""

    try:
        version = _stdout_text(_openssl_run(["version"])).strip()
        algorithms = _stdout_text(_openssl_run(["list", "-public-key-algorithms"]))
    except Rule24AttestationError as error:
        return _no_go(error.reason)
    if "ED25519" not in algorithms.upper():
        return _no_go("openssl_unsupported")
    return _pass(
        "preflight",
        openssl_version=version,
        ed25519_capability=True,
    )


def _require_openssl_ed25519() -> None:
    receipt = openssl_capability_receipt()
    if receipt["status"] != "PASS":
        raise Rule24AttestationError(str(receipt["reason"]), "OpenSSL Ed25519 unavailable")


def public_key_fingerprint(public_key_path: Path | str) -> str:
    """Return sha256 fingerprint over OpenSSL-exported DER public key bytes."""

    public_key = _canonical_path(public_key_path, "public_key_path")
    _require_openssl_ed25519()
    der = _openssl_run(
        ["pkey", "-pubin", "-in", str(public_key), "-outform", "DER"],
    ).stdout
    return _digest_bytes(der)


def _pae(payload_type: str, payload: bytes) -> bytes:
    encoded_type = payload_type.encode("utf-8")
    return (
        b"DSSEv1 "
        + str(len(encoded_type)).encode("ascii")
        + b" "
        + encoded_type
        + b" "
        + str(len(payload)).encode("ascii")
        + b" "
        + payload
    )


def _resource_descriptor(resource: ResourceInput, *, reason: str) -> dict[str, object]:
    name = _identifier(resource.name, "resource name")
    media_type = _identifier(resource.media_type, "resource media_type")
    path = _canonical_path(resource.path, "resource path")
    return {
        "name": name,
        "mediaType": media_type,
        "digest": {"sha256": _digest_path(path)},
    }


def _target_descriptor(path: Path | str, name: str, media_type: str) -> dict[str, object]:
    target_path = _canonical_path(path, "target_path")
    return {
        "name": _identifier(name, "target_name"),
        "mediaType": _identifier(media_type, "target_media_type"),
        "digest": {"sha256": _digest_path(target_path)},
    }


def _measurement_descriptors(
    measurement_inputs: Sequence[ResourceInput],
    *,
    reason: str,
) -> list[dict[str, object]]:
    if len(measurement_inputs) != 2:
        raise Rule24AttestationError("measurement_count", "exactly two measurements are required")
    descriptors = [
        _resource_descriptor(resource, reason=reason) for resource in measurement_inputs
    ]
    identities = [
        (descriptor["name"], descriptor["mediaType"], descriptor["digest"]["sha256"])
        for descriptor in descriptors
    ]
    if len(set(identities)) != 2:
        raise Rule24AttestationError("measurement_binding", "measurements must be distinct")
    return descriptors


def _challenge_digest(correlation: str, challenge: str) -> str:
    return _digest_bytes(_canonical_json_bytes({"challenge": challenge, "correlation": correlation}))


def build_statement(
    *,
    producer_id: str,
    target_path: Path | str,
    target_name: str,
    target_media_type: str,
    rule24_policy_path: Path | str,
    rule24_policy_name: str,
    measurement_inputs: Sequence[ResourceInput],
    correlation: str,
    challenge: str,
) -> tuple[dict[str, object], bytes]:
    correlation_id = _identifier(correlation, "correlation")
    challenge_value = _identifier(challenge, "challenge")
    policy = ResourceInput(
        name=_identifier(rule24_policy_name, "rule24_policy_name"),
        media_type="application/vnd.pantheon.rule24.policy+json",
        path=_canonical_path(rule24_policy_path, "rule24_policy_path"),
    )
    statement: dict[str, object] = {
        "_type": STATEMENT_TYPE,
        "subject": [_target_descriptor(target_path, target_name, target_media_type)],
        "predicateType": PREDICATE_TYPE,
        "predicate": {
            "schema_version": SCHEMA_VERSION,
            "producer_id": _identifier(producer_id, "producer_id"),
            "authorization": {
                "correlation": correlation_id,
                "challenge": challenge_value,
                "challenge_digest": _challenge_digest(correlation_id, challenge_value),
            },
            "rule24_policy": _resource_descriptor(policy, reason="policy_digest"),
            "measurements": _measurement_descriptors(
                measurement_inputs,
                reason="measurement_digest",
            ),
        },
    }
    payload = _canonical_json_bytes(statement)
    return statement, payload


def _sign_pae(private_key_path: Path | str, pae: bytes) -> bytes:
    private_key = _canonical_path(private_key_path, "private_key_path")
    with tempfile.TemporaryDirectory(prefix="rule24-dsse-") as temporary:
        root = Path(temporary)
        pae_path = root / "pae.bin"
        signature_path = root / "signature.bin"
        pae_path.write_bytes(pae)
        _openssl_run(
            [
                "pkeyutl",
                "-sign",
                "-rawin",
                "-inkey",
                str(private_key),
                "-in",
                str(pae_path),
                "-out",
                str(signature_path),
            ],
        )
        return signature_path.read_bytes()


def _verify_pae_signature(public_key_path: Path | str, pae: bytes, signature: bytes) -> bool:
    public_key = _canonical_path(public_key_path, "pinned_public_key_path")
    with tempfile.TemporaryDirectory(prefix="rule24-dsse-") as temporary:
        root = Path(temporary)
        pae_path = root / "pae.bin"
        signature_path = root / "signature.bin"
        pae_path.write_bytes(pae)
        signature_path.write_bytes(signature)
        try:
            completed = subprocess.run(
                [
                    "openssl",
                    "pkeyutl",
                    "-verify",
                    "-rawin",
                    "-pubin",
                    "-inkey",
                    str(public_key),
                    "-in",
                    str(pae_path),
                    "-sigfile",
                    str(signature_path),
                ],
                check=False,
                capture_output=True,
                timeout=OPENSSL_TIMEOUT_SECONDS,
            )
        except FileNotFoundError as error:
            raise Rule24AttestationError("openssl_missing", "openssl is not on PATH") from error
        except subprocess.TimeoutExpired as error:
            raise Rule24AttestationError("openssl_timeout", "openssl command timed out") from error
        except OSError as error:
            raise Rule24AttestationError("openssl_missing", "openssl cannot be executed") from error
        if completed.returncode == 0:
            return True
        return False


def _assert_keypair_matches(private_key_path: Path | str, public_key_path: Path | str) -> None:
    probe = _pae("application/vnd.pantheon.rule24.keypair-probe", b"rule24-keypair-probe")
    signature = _sign_pae(private_key_path, probe)
    if not _verify_pae_signature(public_key_path, probe, signature):
        raise Rule24AttestationError(
            "key_pair_mismatch",
            "private key does not match supplied public key",
        )


def produce_rule24_attestation(
    *,
    private_key_path: Path | str,
    public_key_path: Path | str,
    producer_id: str,
    target_path: Path | str,
    target_name: str,
    target_media_type: str,
    rule24_policy_path: Path | str,
    rule24_policy_name: str,
    measurement_inputs: Sequence[ResourceInput],
    correlation: str,
    challenge: str,
) -> dict[str, object]:
    """Build in-toto Statement v1, sign DSSE PAE with caller-supplied Ed25519 key."""

    try:
        _require_openssl_ed25519()
        fingerprint = public_key_fingerprint(public_key_path)
        _assert_keypair_matches(private_key_path, public_key_path)
        _statement, payload = build_statement(
            producer_id=producer_id,
            target_path=target_path,
            target_name=target_name,
            target_media_type=target_media_type,
            rule24_policy_path=rule24_policy_path,
            rule24_policy_name=rule24_policy_name,
            measurement_inputs=measurement_inputs,
            correlation=correlation,
            challenge=challenge,
        )
        signature = _sign_pae(private_key_path, _pae(PAYLOAD_TYPE, payload))
        target_digest = _digest_path(_canonical_path(target_path, "target_path"))
        policy_digest = _digest_path(_canonical_path(rule24_policy_path, "rule24_policy_path"))
        measurement_digests = [
            _digest_path(_canonical_path(resource.path, "resource path"))
            for resource in measurement_inputs
        ]
        envelope = {
            "payloadType": PAYLOAD_TYPE,
            "payload": base64.b64encode(payload).decode("ascii"),
            "signatures": [
                {
                    "keyid": fingerprint,
                    "sig": base64.b64encode(signature).decode("ascii"),
                }
            ],
        }
        return _pass(
            "produce",
            envelope=envelope,
            authenticated_statement_digest=_digest_bytes(payload),
            accepted_public_key_fingerprint=fingerprint,
            target_digest=target_digest,
            policy_digest=policy_digest,
            measurement_digests=measurement_digests,
            correlation_challenge_digest=_challenge_digest(correlation, challenge),
        )
    except Rule24AttestationError as error:
        return _no_go(error.reason)


def _validate_trust_policy(
    *,
    trust_policy_path: Path | str,
    producer_id: str,
    predicate_type: str,
    public_key_fingerprint_value: str,
) -> None:
    path = _canonical_path(trust_policy_path, "trust_policy_path")
    policy = _load_json(path, "trust_policy")
    if policy.get("schema_version") != SCHEMA_VERSION:
        raise Rule24AttestationError("trust_policy", "trust policy schema mismatch")
    if policy.get("producer_id") != producer_id:
        raise Rule24AttestationError("trust_policy", "producer is not trusted")
    if policy.get("allowed_predicate_type") != predicate_type:
        raise Rule24AttestationError("trust_policy", "predicate type is not allowed")
    if policy.get("threshold") != 1:
        raise Rule24AttestationError("trust_policy", "threshold must be 1")
    if policy.get("pinned_public_key_fingerprint") != public_key_fingerprint_value:
        raise Rule24AttestationError("trust_policy", "pinned key fingerprint mismatch")


def _validate_challenge(path: Path | str) -> Mapping[str, Any]:
    challenge_path = _canonical_path(path, "expected_challenge_path")
    payload = _load_json(challenge_path, "challenge_contract")
    required = ("schema_version", "correlation", "challenge", "expires_epoch", "consumed")
    if any(field not in payload for field in required):
        raise Rule24AttestationError("challenge_contract", "challenge fixture is incomplete")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise Rule24AttestationError("challenge_contract", "challenge schema mismatch")
    if type(payload.get("consumed")) is not bool:
        raise Rule24AttestationError("challenge_contract", "consumed must be boolean")
    expires_epoch = payload.get("expires_epoch")
    if not isinstance(expires_epoch, (int, float)) or not math.isfinite(expires_epoch):
        raise Rule24AttestationError("challenge_contract", "expires_epoch must be finite")
    if payload["consumed"] is True:
        raise Rule24AttestationError("challenge_replay", "challenge has already been consumed")
    if float(expires_epoch) <= time.time():
        raise Rule24AttestationError("challenge_stale", "challenge is stale")
    _identifier(payload.get("correlation"), "challenge correlation")
    _identifier(payload.get("challenge"), "challenge")
    return payload


def _statement_from_verified_payload(payload: bytes) -> Mapping[str, Any]:
    try:
        statement = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Rule24AttestationError("payload_json", "verified payload is not JSON") from error
    if not isinstance(statement, Mapping):
        raise Rule24AttestationError("payload_json", "verified payload must be an object")
    return statement


def _expect_digest(value: object, reason: str) -> str:
    if type(value) is not str or SHA256_PATTERN.fullmatch(value) is None:
        raise Rule24AttestationError(reason, "sha256 digest is invalid")
    return value


def _validate_resource_descriptor(
    descriptor: object,
    expected: dict[str, object],
    reason: str,
    *,
    digest_reason: str | None = None,
) -> None:
    if not isinstance(descriptor, Mapping):
        raise Rule24AttestationError(reason, "resource descriptor must be an object")
    if descriptor.get("name") != expected["name"]:
        raise Rule24AttestationError(reason, "resource name mismatch")
    if descriptor.get("mediaType") != expected["mediaType"]:
        raise Rule24AttestationError(reason, "resource media type mismatch")
    digest = descriptor.get("digest")
    if not isinstance(digest, Mapping):
        raise Rule24AttestationError(reason, "resource digest missing")
    effective_digest_reason = digest_reason or reason
    if (
        _expect_digest(digest.get("sha256"), effective_digest_reason)
        != expected["digest"]["sha256"]
    ):
        raise Rule24AttestationError(effective_digest_reason, "resource digest mismatch")


def _validate_statement_contract(
    statement: Mapping[str, Any],
    *,
    trust_policy_path: Path | str,
    pinned_public_key_fingerprint: str,
    target_path: Path | str,
    expected_target_name: str,
    expected_target_media_type: str,
    rule24_policy_path: Path | str,
    rule24_policy_name: str,
    measurement_inputs: Sequence[ResourceInput],
    expected_challenge_path: Path | str,
) -> tuple[str, str, str, list[str], str]:
    if statement.get("_type") != STATEMENT_TYPE:
        raise Rule24AttestationError("statement_type", "statement _type mismatch")
    if statement.get("predicateType") != PREDICATE_TYPE:
        raise Rule24AttestationError("predicate_type", "predicateType mismatch")
    subject = statement.get("subject")
    if not isinstance(subject, list) or len(subject) != 1:
        raise Rule24AttestationError("target_binding", "statement must bind one target")
    expected_target = _target_descriptor(
        target_path,
        expected_target_name,
        expected_target_media_type,
    )
    _validate_resource_descriptor(subject[0], expected_target, "target_binding")
    predicate = statement.get("predicate")
    if not isinstance(predicate, Mapping):
        raise Rule24AttestationError("predicate_contract", "predicate must be an object")
    if predicate.get("schema_version") != SCHEMA_VERSION:
        raise Rule24AttestationError("predicate_contract", "predicate schema mismatch")
    producer_id = _identifier(predicate.get("producer_id"), "producer_id")
    _validate_trust_policy(
        trust_policy_path=trust_policy_path,
        producer_id=producer_id,
        predicate_type=PREDICATE_TYPE,
        public_key_fingerprint_value=pinned_public_key_fingerprint,
    )
    expected_policy = _resource_descriptor(
        ResourceInput(
            name=rule24_policy_name,
            media_type="application/vnd.pantheon.rule24.policy+json",
            path=_canonical_path(rule24_policy_path, "rule24_policy_path"),
        ),
        reason="policy_digest",
    )
    _validate_resource_descriptor(predicate.get("rule24_policy"), expected_policy, "policy_digest")
    expected_measurements = _measurement_descriptors(
        measurement_inputs,
        reason="measurement_digest",
    )
    actual_measurements = predicate.get("measurements")
    if not isinstance(actual_measurements, list) or len(actual_measurements) != 2:
        raise Rule24AttestationError("measurement_count", "statement must bind two measurements")
    for actual, expected in zip(actual_measurements, expected_measurements, strict=True):
        _validate_resource_descriptor(
            actual,
            expected,
            "measurement_binding",
            digest_reason="measurement_digest",
        )
    authorization = predicate.get("authorization")
    if not isinstance(authorization, Mapping):
        raise Rule24AttestationError("challenge_contract", "authorization is missing")
    expected_challenge = _validate_challenge(expected_challenge_path)
    if (
        authorization.get("correlation") != expected_challenge["correlation"]
        or authorization.get("challenge") != expected_challenge["challenge"]
    ):
        raise Rule24AttestationError("challenge_mismatch", "challenge/correlation mismatch")
    challenge_digest = _challenge_digest(
        str(expected_challenge["correlation"]),
        str(expected_challenge["challenge"]),
    )
    if authorization.get("challenge_digest") != challenge_digest:
        raise Rule24AttestationError("challenge_mismatch", "challenge digest mismatch")
    return (
        expected_target["digest"]["sha256"],
        expected_policy["digest"]["sha256"],
        producer_id,
        [descriptor["digest"]["sha256"] for descriptor in expected_measurements],
        challenge_digest,
    )


def _claim_challenge_digest(
    replay_state_dir: Path,
    *,
    challenge_digest: str,
    authenticated_statement_digest: str,
) -> None:
    claim_path = replay_state_dir / f"{challenge_digest}.json"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "challenge_digest": challenge_digest,
        "authenticated_statement_digest": authenticated_statement_digest,
        "claimed_epoch": time.time(),
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8") + b"\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(claim_path, flags, 0o600)
    except FileExistsError as error:
        raise Rule24AttestationError("challenge_replay", "challenge digest is already claimed") from error
    except OSError as error:
        raise Rule24AttestationError("replay_state_claim", "challenge claim cannot be created") from error
    with os.fdopen(fd, "wb") as claim_file:
        claim_file.write(encoded)


def verify_rule24_attestation(
    *,
    envelope: Mapping[str, Any],
    trust_policy_path: Path | str,
    pinned_public_key_path: Path | str,
    target_path: Path | str,
    expected_target_name: str,
    expected_target_media_type: str,
    rule24_policy_path: Path | str,
    rule24_policy_name: str,
    measurement_inputs: Sequence[ResourceInput],
    expected_challenge_path: Path | str,
    replay_state_dir: Path | str,
    verified_payload_observer: Callable[[bytes], None] | None = None,
) -> dict[str, object]:
    """Verify DSSE signature first, then parse the exact authenticated payload bytes."""

    try:
        _require_openssl_ed25519()
        if not isinstance(envelope, Mapping):
            raise Rule24AttestationError("envelope_contract", "envelope must be an object")
        if envelope.get("payloadType") != PAYLOAD_TYPE:
            raise Rule24AttestationError("payload_type", "payloadType mismatch")
        payload = _strict_b64_decode(envelope.get("payload"), "payload")
        signatures = envelope.get("signatures")
        if not isinstance(signatures, list) or len(signatures) != 1:
            raise Rule24AttestationError("signature_contract", "exactly one signature is required")
        signature_entry = signatures[0]
        if not isinstance(signature_entry, Mapping):
            raise Rule24AttestationError("signature_contract", "signature must be an object")
        signature = _strict_b64_decode(signature_entry.get("sig"), "signature_contract")
        fingerprint = public_key_fingerprint(pinned_public_key_path)
        replay_state = _external_replay_state_dir(replay_state_dir)
        if not _verify_pae_signature(pinned_public_key_path, _pae(PAYLOAD_TYPE, payload), signature):
            raise Rule24AttestationError("signature_invalid", "signature verification failed")
        statement = _statement_from_verified_payload(payload)
        target_digest, policy_digest, _producer_id, measurement_digests, challenge_digest = (
            _validate_statement_contract(
                statement,
                trust_policy_path=trust_policy_path,
                pinned_public_key_fingerprint=fingerprint,
                target_path=target_path,
                expected_target_name=expected_target_name,
                expected_target_media_type=expected_target_media_type,
                rule24_policy_path=rule24_policy_path,
                rule24_policy_name=rule24_policy_name,
                measurement_inputs=measurement_inputs,
                expected_challenge_path=expected_challenge_path,
            )
        )
        authenticated_statement_digest = _digest_bytes(payload)
        if verified_payload_observer is not None:
            verified_payload_observer(payload)
        _claim_challenge_digest(
            replay_state,
            challenge_digest=challenge_digest,
            authenticated_statement_digest=authenticated_statement_digest,
        )
        return _pass(
            "verify",
            authenticated_statement_digest=authenticated_statement_digest,
            accepted_public_key_fingerprint=fingerprint,
            target_digest=target_digest,
            policy_digest=policy_digest,
            measurement_digests=measurement_digests,
            correlation_challenge_digest=challenge_digest,
        )
    except Rule24AttestationError as error:
        if error.reason == "openssl_nonzero":
            return _no_go("openssl_nonzero")
        return _no_go(error.reason)


def sign_statement_for_tests(
    *,
    statement_mutator: Callable[[dict[str, object]], object],
    private_key_path: Path | str,
    public_key_path: Path | str,
    producer_id: str,
    target_path: Path | str,
    target_name: str,
    target_media_type: str,
    rule24_policy_path: Path | str,
    rule24_policy_name: str,
    measurement_inputs: Sequence[ResourceInput],
    correlation: str,
    challenge: str,
) -> dict[str, object]:
    statement, _payload = build_statement(
        producer_id=producer_id,
        target_path=target_path,
        target_name=target_name,
        target_media_type=target_media_type,
        rule24_policy_path=rule24_policy_path,
        rule24_policy_name=rule24_policy_name,
        measurement_inputs=measurement_inputs,
        correlation=correlation,
        challenge=challenge,
    )
    statement_mutator(statement)
    payload = _canonical_json_bytes(statement)
    signature = _sign_pae(private_key_path, _pae(PAYLOAD_TYPE, payload))
    return {
        "payloadType": PAYLOAD_TYPE,
        "payload": base64.b64encode(payload).decode("ascii"),
        "signatures": [
            {
                "keyid": public_key_fingerprint(public_key_path),
                "sig": base64.b64encode(signature).decode("ascii"),
            }
        ],
    }


def _read_measurements(values: Sequence[str]) -> list[ResourceInput]:
    measurements: list[ResourceInput] = []
    for value in values:
        parts = value.split(":", 2)
        if len(parts) != 3:
            raise Rule24AttestationError(
                "measurement_contract",
                "measurement must be name:mediaType:/absolute/path",
            )
        measurements.append(ResourceInput(parts[0], parts[1], Path(parts[2])))
    return measurements


def _load_envelope(path: Path | str) -> Mapping[str, Any]:
    return _load_json(_canonical_path(path, "envelope_path"), "envelope_contract")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rule24 DSSE/OpenSSL attestation primitive")
    subparsers = parser.add_subparsers(dest="mode", required=True)
    produce = subparsers.add_parser("produce")
    produce.add_argument("--private-key", required=True)
    produce.add_argument("--public-key", required=True)
    produce.add_argument("--producer-id", required=True)
    produce.add_argument("--target-path", required=True)
    produce.add_argument("--target-name", required=True)
    produce.add_argument("--target-media-type", required=True)
    produce.add_argument("--rule24-policy-path", required=True)
    produce.add_argument("--rule24-policy-name", required=True)
    produce.add_argument("--measurement", action="append", default=[])
    produce.add_argument("--correlation", required=True)
    produce.add_argument("--challenge", required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--envelope", required=True)
    verify.add_argument("--trust-policy", required=True)
    verify.add_argument("--pinned-public-key", required=True)
    verify.add_argument("--target-path", required=True)
    verify.add_argument("--target-name", required=True)
    verify.add_argument("--target-media-type", required=True)
    verify.add_argument("--rule24-policy-path", required=True)
    verify.add_argument("--rule24-policy-name", required=True)
    verify.add_argument("--measurement", action="append", default=[])
    verify.add_argument("--expected-challenge", required=True)
    verify.add_argument("--replay-state-dir", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        measurements = _read_measurements(args.measurement)
        if args.mode == "produce":
            result = produce_rule24_attestation(
                private_key_path=Path(args.private_key),
                public_key_path=Path(args.public_key),
                producer_id=args.producer_id,
                target_path=Path(args.target_path),
                target_name=args.target_name,
                target_media_type=args.target_media_type,
                rule24_policy_path=Path(args.rule24_policy_path),
                rule24_policy_name=args.rule24_policy_name,
                measurement_inputs=measurements,
                correlation=args.correlation,
                challenge=args.challenge,
            )
        else:
            result = verify_rule24_attestation(
                envelope=_load_envelope(args.envelope),
                trust_policy_path=Path(args.trust_policy),
                pinned_public_key_path=Path(args.pinned_public_key),
                target_path=Path(args.target_path),
                expected_target_name=args.target_name,
                expected_target_media_type=args.target_media_type,
                rule24_policy_path=Path(args.rule24_policy_path),
                rule24_policy_name=args.rule24_policy_name,
                measurement_inputs=measurements,
                expected_challenge_path=Path(args.expected_challenge),
                replay_state_dir=Path(args.replay_state_dir),
            )
    except Rule24AttestationError as error:
        result = _no_go(error.reason)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
