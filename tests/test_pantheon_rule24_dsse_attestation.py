from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

from scripts import pantheon_rule24_dsse_attestation as rule24


PRODUCER_ID = "rule24-producer:test"
TARGET_NAME = "pantheon-rule24-target"
TARGET_TYPE = "application/vnd.pantheon.rule24.target"
POLICY_NAME = "rule24-policy.json"
MEASUREMENTS = (
    ("measurement-a.json", "application/vnd.pantheon.rule24.measurement"),
    ("measurement-b.json", "application/vnd.pantheon.rule24.measurement"),
)
CORRELATION = "corr-rule24-test"
CHALLENGE = "challenge-rule24-test"


def _openssl(*args: str, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        ["openssl", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout.strip()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _keypair(root: Path, name: str = "trusted") -> tuple[Path, Path, str]:
    private_key = root / f"{name}.private.pem"
    public_key = root / f"{name}.public.pem"
    _openssl("genpkey", "-algorithm", "ED25519", "-out", str(private_key))
    _openssl("pkey", "-in", str(private_key), "-pubout", "-out", str(public_key))
    fingerprint = rule24.public_key_fingerprint(public_key.resolve())
    return private_key.resolve(), public_key.resolve(), fingerprint


def _fixture(
    tmp_path: Path,
) -> dict[str, object]:
    private_key, public_key, fingerprint = _keypair(tmp_path)
    target = tmp_path / "target.txt"
    policy = tmp_path / POLICY_NAME
    measurement_a = tmp_path / "measurement-a.json"
    measurement_b = tmp_path / "measurement-b.json"
    target.write_text("target-v1\n", encoding="utf-8")
    _write_json(policy, {"policy": "rule24", "threshold": 1})
    _write_json(measurement_a, {"name": "a", "value": 1})
    _write_json(measurement_b, {"name": "b", "value": 2})
    trust_policy = tmp_path / "trust-policy.json"
    _write_json(
        trust_policy,
        {
            "schema_version": 1,
            "producer_id": PRODUCER_ID,
            "pinned_public_key_fingerprint": fingerprint,
            "allowed_predicate_type": rule24.PREDICATE_TYPE,
            "threshold": 1,
        },
    )
    challenge = tmp_path / "challenge.json"
    replay_state = tmp_path / "replay-state"
    replay_state.mkdir()
    _write_json(
        challenge,
        {
            "schema_version": 1,
            "correlation": CORRELATION,
            "challenge": CHALLENGE,
            "expires_epoch": 4_102_444_800,
            "consumed": False,
        },
    )
    measurements = [
        rule24.ResourceInput(
            name=MEASUREMENTS[0][0],
            media_type=MEASUREMENTS[0][1],
            path=measurement_a.resolve(),
        ),
        rule24.ResourceInput(
            name=MEASUREMENTS[1][0],
            media_type=MEASUREMENTS[1][1],
            path=measurement_b.resolve(),
        ),
    ]
    return {
        "private_key": private_key,
        "public_key": public_key,
        "fingerprint": fingerprint,
        "target": target.resolve(),
        "policy": policy.resolve(),
        "measurements": measurements,
        "trust_policy": trust_policy.resolve(),
        "challenge": challenge.resolve(),
        "replay_state": replay_state.resolve(),
    }


def _produce(fixture: dict[str, object]) -> dict[str, object]:
    return rule24.produce_rule24_attestation(
        private_key_path=fixture["private_key"],
        public_key_path=fixture["public_key"],
        producer_id=PRODUCER_ID,
        target_path=fixture["target"],
        target_name=TARGET_NAME,
        target_media_type=TARGET_TYPE,
        rule24_policy_path=fixture["policy"],
        rule24_policy_name=POLICY_NAME,
        measurement_inputs=fixture["measurements"],
        correlation=CORRELATION,
        challenge=CHALLENGE,
    )


def _verify(fixture: dict[str, object], envelope: dict[str, object]) -> dict[str, object]:
    return rule24.verify_rule24_attestation(
        envelope=envelope,
        trust_policy_path=fixture["trust_policy"],
        pinned_public_key_path=fixture["public_key"],
        target_path=fixture["target"],
        expected_target_name=TARGET_NAME,
        expected_target_media_type=TARGET_TYPE,
        rule24_policy_path=fixture["policy"],
        rule24_policy_name=POLICY_NAME,
        measurement_inputs=fixture["measurements"],
        expected_challenge_path=fixture["challenge"],
        replay_state_dir=fixture["replay_state"],
    )


def test_dsse_pae_spec_vector_is_unambiguous() -> None:
    assert rule24._pae("test", b"abc") == b"DSSEv1 4 test 3 abc"
    assert (
        rule24._pae(rule24.PAYLOAD_TYPE, b"{}")
        == b"DSSEv1 28 application/vnd.in-toto+json 2 {}"
    )


def test_ephemeral_trusted_key_produce_then_network_off_verify_pass(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    produced = _produce(fixture)
    verified = _verify(fixture, produced["envelope"])

    assert produced["status"] == "PASS"
    assert produced["mode"] == "produce"
    assert verified["status"] == "PASS"
    assert verified["mode"] == "verify"
    assert verified["accepted_public_key_fingerprint"] == fixture["fingerprint"]
    assert verified["production_mutation"] is False
    assert verified["canary_created"] is False
    assert verified["target_digest"] == _sha256(fixture["target"])
    assert verified["policy_digest"] == _sha256(fixture["policy"])
    assert verified["measurement_digests"] == [
        _sha256(Path(resource.path)) for resource in fixture["measurements"]
    ]
    assert "authenticated_statement_digest" in verified


def test_cli_produce_and_verify_emit_machine_readable_json(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    produce = subprocess.run(
        [
            sys.executable,
            "scripts/pantheon_rule24_dsse_attestation.py",
            "produce",
            "--private-key",
            str(fixture["private_key"]),
            "--public-key",
            str(fixture["public_key"]),
            "--producer-id",
            PRODUCER_ID,
            "--target-path",
            str(fixture["target"]),
            "--target-name",
            TARGET_NAME,
            "--target-media-type",
            TARGET_TYPE,
            "--rule24-policy-path",
            str(fixture["policy"]),
            "--rule24-policy-name",
            POLICY_NAME,
            "--measurement",
            f"{MEASUREMENTS[0][0]}:{MEASUREMENTS[0][1]}:{fixture['measurements'][0].path}",
            "--measurement",
            f"{MEASUREMENTS[1][0]}:{MEASUREMENTS[1][1]}:{fixture['measurements'][1].path}",
            "--correlation",
            CORRELATION,
            "--challenge",
            CHALLENGE,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    produced = json.loads(produce.stdout)
    envelope_path = tmp_path / "envelope.json"
    _write_json(envelope_path, produced["envelope"])

    verify = subprocess.run(
        [
            sys.executable,
            "scripts/pantheon_rule24_dsse_attestation.py",
            "verify",
            "--envelope",
            str(envelope_path.resolve()),
            "--trust-policy",
            str(fixture["trust_policy"]),
            "--pinned-public-key",
            str(fixture["public_key"]),
            "--target-path",
            str(fixture["target"]),
            "--target-name",
            TARGET_NAME,
            "--target-media-type",
            TARGET_TYPE,
            "--rule24-policy-path",
            str(fixture["policy"]),
            "--rule24-policy-name",
            POLICY_NAME,
            "--measurement",
            f"{MEASUREMENTS[0][0]}:{MEASUREMENTS[0][1]}:{fixture['measurements'][0].path}",
            "--measurement",
            f"{MEASUREMENTS[1][0]}:{MEASUREMENTS[1][1]}:{fixture['measurements'][1].path}",
            "--expected-challenge",
            str(fixture["challenge"]),
            "--replay-state-dir",
            str(fixture["replay_state"]),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    verified = json.loads(verify.stdout)

    assert produce.returncode == 0
    assert verify.returncode == 0
    assert produced["status"] == "PASS"
    assert verified["status"] == "PASS"
    assert verified["production_mutation"] is False
    assert verified["canary_created"] is False


def test_same_challenge_digest_can_only_verify_once(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    envelope = _produce(fixture)["envelope"]

    first = _verify(fixture, envelope)
    second = _verify(fixture, envelope)

    assert first["status"] == "PASS"
    assert second["status"] == "NO-GO"
    assert second["reason"] == "challenge_replay"
    claim_files = list(Path(fixture["replay_state"]).glob("*.json"))
    assert len(claim_files) == 1
    claim = json.loads(claim_files[0].read_text(encoding="utf-8"))
    assert set(claim) == {
        "schema_version",
        "challenge_digest",
        "authenticated_statement_digest",
        "claimed_epoch",
    }
    assert CHALLENGE not in json.dumps(claim)
    assert fixture["fingerprint"] not in json.dumps(claim)


def test_replay_rejection_does_not_release_payload_to_observer(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    envelope = _produce(fixture)["envelope"]
    observed: list[bytes] = []

    first = rule24.verify_rule24_attestation(
        envelope=envelope,
        trust_policy_path=fixture["trust_policy"],
        pinned_public_key_path=fixture["public_key"],
        target_path=fixture["target"],
        expected_target_name=TARGET_NAME,
        expected_target_media_type=TARGET_TYPE,
        rule24_policy_path=fixture["policy"],
        rule24_policy_name=POLICY_NAME,
        measurement_inputs=fixture["measurements"],
        expected_challenge_path=fixture["challenge"],
        replay_state_dir=fixture["replay_state"],
        verified_payload_observer=observed.append,
    )
    second = rule24.verify_rule24_attestation(
        envelope=envelope,
        trust_policy_path=fixture["trust_policy"],
        pinned_public_key_path=fixture["public_key"],
        target_path=fixture["target"],
        expected_target_name=TARGET_NAME,
        expected_target_media_type=TARGET_TYPE,
        rule24_policy_path=fixture["policy"],
        rule24_policy_name=POLICY_NAME,
        measurement_inputs=fixture["measurements"],
        expected_challenge_path=fixture["challenge"],
        replay_state_dir=fixture["replay_state"],
        verified_payload_observer=observed.append,
    )

    assert first["status"] == "PASS"
    assert second["status"] == "NO-GO"
    assert second["reason"] == "challenge_replay"
    assert observed == [base64.b64decode(envelope["payload"])]


def test_concurrent_verifiers_allow_at_most_one_replay_claim_pass(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    envelope = _produce(fixture)["envelope"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _index: _verify(fixture, envelope), range(8)))

    assert [result["status"] for result in results].count("PASS") == 1
    assert [result.get("reason") for result in results].count("challenge_replay") == 7
    assert len(list(Path(fixture["replay_state"]).glob("*.json"))) == 1


def test_pre_validation_failure_does_not_create_replay_claim(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    envelope = copy.deepcopy(_produce(fixture)["envelope"])
    envelope["payloadType"] = "application/json"

    result = _verify(fixture, envelope)

    assert result["status"] == "NO-GO"
    assert result["reason"] == "payload_type"
    assert list(Path(fixture["replay_state"]).iterdir()) == []


def test_replay_claim_write_oserror_is_deterministic_no_go_without_observer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(tmp_path)
    envelope = _produce(fixture)["envelope"]
    observed: list[bytes] = []
    real_open = rule24.os.open

    def fail_claim_open(path: object, flags: int, mode: int = 0o777, **kwargs: object) -> int:
        if Path(path).parent == fixture["replay_state"]:
            raise OSError("synthetic claim write failure")
        return real_open(path, flags, mode, **kwargs)

    monkeypatch.setattr(rule24.os, "open", fail_claim_open)
    result = rule24.verify_rule24_attestation(
        envelope=envelope,
        trust_policy_path=fixture["trust_policy"],
        pinned_public_key_path=fixture["public_key"],
        target_path=fixture["target"],
        expected_target_name=TARGET_NAME,
        expected_target_media_type=TARGET_TYPE,
        rule24_policy_path=fixture["policy"],
        rule24_policy_name=POLICY_NAME,
        measurement_inputs=fixture["measurements"],
        expected_challenge_path=fixture["challenge"],
        replay_state_dir=fixture["replay_state"],
        verified_payload_observer=observed.append,
    )

    assert result["status"] == "NO-GO"
    assert result["reason"] == "replay_state_claim"
    assert observed == []


def test_private_public_keypair_mismatch_fails_without_authenticated_pass_fields(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    _attacker_private, attacker_public, attacker_fingerprint = _keypair(tmp_path, "attacker")
    mismatch = dict(fixture)
    mismatch["public_key"] = attacker_public

    result = _produce(mismatch)

    assert result["status"] == "NO-GO"
    assert result["reason"] == "key_pair_mismatch"
    assert result["production_mutation"] is False
    assert result["canary_created"] is False
    assert "authenticated_statement_digest" not in result
    assert "accepted_public_key_fingerprint" not in result
    assert attacker_fingerprint not in json.dumps(result)


def test_same_inputs_serialize_deterministically(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    first = _produce(fixture)
    second = _produce(fixture)

    assert first["envelope"] == second["envelope"]
    assert first["authenticated_statement_digest"] == second["authenticated_statement_digest"]


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("payload", "signature_invalid"),
        ("payload_type", "payload_type"),
        ("signature", "signature_invalid"),
    ],
)
def test_dsse_envelope_tamper_fails_closed(
    tmp_path: Path,
    mutation: str,
    reason: str,
) -> None:
    fixture = _fixture(tmp_path)
    envelope = copy.deepcopy(_produce(fixture)["envelope"])
    if mutation == "payload":
        payload = bytearray(base64.b64decode(envelope["payload"]))
        payload[-2] ^= 1
        envelope["payload"] = base64.b64encode(bytes(payload)).decode("ascii")
    elif mutation == "payload_type":
        envelope["payloadType"] = "application/json"
    else:
        signature = bytearray(base64.b64decode(envelope["signatures"][0]["sig"]))
        signature[0] ^= 1
        envelope["signatures"][0]["sig"] = base64.b64encode(bytes(signature)).decode("ascii")

    result = _verify(fixture, envelope)

    assert result["status"] == "NO-GO"
    assert result["reason"] == reason
    assert result["production_mutation"] is False
    assert "authenticated_statement_digest" not in result


def test_untrusted_key_substitution_and_keyid_spoof_fail_closed(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    attacker_private, attacker_public, _attacker_fingerprint = _keypair(tmp_path, "attacker")
    attacker = dict(fixture)
    attacker["private_key"] = attacker_private
    attacker["public_key"] = attacker_public
    envelope = _produce(attacker)["envelope"]
    envelope["signatures"][0]["keyid"] = fixture["fingerprint"]

    result = _verify(fixture, envelope)

    assert result["status"] == "NO-GO"
    assert result["reason"] == "signature_invalid"


@pytest.mark.parametrize(
    ("mutator", "reason"),
    [
        (lambda statement: statement.__setitem__("predicateType", "wrong"), "predicate_type"),
        (lambda statement: statement.__setitem__("_type", "wrong"), "statement_type"),
        (lambda statement: statement["subject"][0].__setitem__("name", "wrong"), "target_binding"),
        (
            lambda statement: statement["subject"][0].__setitem__("mediaType", "wrong"),
            "target_binding",
        ),
        (
            lambda statement: statement["subject"][0]["digest"].__setitem__("sha256", "0" * 64),
            "target_binding",
        ),
    ],
)
def test_statement_contract_negative_matrix_fails_closed(
    tmp_path: Path,
    mutator: object,
    reason: str,
) -> None:
    fixture = _fixture(tmp_path)
    envelope = rule24.sign_statement_for_tests(
        statement_mutator=mutator,
        private_key_path=fixture["private_key"],
        public_key_path=fixture["public_key"],
        producer_id=PRODUCER_ID,
        target_path=fixture["target"],
        target_name=TARGET_NAME,
        target_media_type=TARGET_TYPE,
        rule24_policy_path=fixture["policy"],
        rule24_policy_name=POLICY_NAME,
        measurement_inputs=fixture["measurements"],
        correlation=CORRELATION,
        challenge=CHALLENGE,
    )

    assert _verify(fixture, envelope)["reason"] == reason


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("policy-bytes", "policy_digest"),
        ("measurement-bytes", "measurement_digest"),
        ("measurement-missing", "measurement_count"),
        ("measurement-extra", "measurement_count"),
        ("measurement-order", "measurement_binding"),
        ("measurement-duplicate", "measurement_binding"),
    ],
)
def test_policy_and_measurement_binding_negative_matrix(
    tmp_path: Path,
    mutation: str,
    reason: str,
) -> None:
    fixture = _fixture(tmp_path)
    envelope = _produce(fixture)["envelope"]
    if mutation == "policy-bytes":
        Path(fixture["policy"]).write_text('{"policy":"changed"}\n', encoding="utf-8")
    elif mutation == "measurement-bytes":
        Path(fixture["measurements"][0].path).write_text('{"name":"a","value":99}\n', encoding="utf-8")
    elif mutation == "measurement-missing":
        fixture["measurements"] = fixture["measurements"][:1]
    elif mutation == "measurement-extra":
        extra = Path(fixture["target"]).with_name("measurement-c.json")
        _write_json(extra, {"name": "c"})
        fixture["measurements"] = [
            *fixture["measurements"],
            rule24.ResourceInput("measurement-c.json", MEASUREMENTS[1][1], extra.resolve()),
        ]
    elif mutation == "measurement-order":
        fixture["measurements"] = list(reversed(fixture["measurements"]))
    else:
        fixture["measurements"] = [fixture["measurements"][0], fixture["measurements"][0]]

    result = _verify(fixture, envelope)

    assert result["status"] == "NO-GO"
    assert result["reason"] == reason


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("missing-correlation", "challenge_contract"),
        ("wrong-correlation", "challenge_mismatch"),
        ("wrong-challenge", "challenge_mismatch"),
        ("consumed", "challenge_replay"),
        ("stale", "challenge_stale"),
    ],
)
def test_challenge_and_correlation_fail_closed(
    tmp_path: Path,
    mutation: str,
    reason: str,
) -> None:
    fixture = _fixture(tmp_path)
    envelope = _produce(fixture)["envelope"]
    challenge = json.loads(Path(fixture["challenge"]).read_text(encoding="utf-8"))
    if mutation == "missing-correlation":
        challenge.pop("correlation")
    elif mutation == "wrong-correlation":
        challenge["correlation"] = "wrong"
    elif mutation == "wrong-challenge":
        challenge["challenge"] = "wrong"
    elif mutation == "consumed":
        challenge["consumed"] = True
    else:
        challenge["expires_epoch"] = 1
    _write_json(fixture["challenge"], challenge)

    result = _verify(fixture, envelope)

    assert result["status"] == "NO-GO"
    assert result["reason"] == reason


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("producer_id", "wrong", "trust_policy"),
        ("allowed_predicate_type", "wrong", "trust_policy"),
        ("pinned_public_key_fingerprint", "0" * 64, "trust_policy"),
        ("threshold", 2, "trust_policy"),
    ],
)
def test_trust_policy_mismatch_fails_closed(
    tmp_path: Path,
    field: str,
    value: object,
    reason: str,
) -> None:
    fixture = _fixture(tmp_path)
    envelope = _produce(fixture)["envelope"]
    policy = json.loads(Path(fixture["trust_policy"]).read_text(encoding="utf-8"))
    policy[field] = value
    _write_json(fixture["trust_policy"], policy)

    result = _verify(fixture, envelope)

    assert result["status"] == "NO-GO"
    assert result["reason"] == reason


def test_application_parse_uses_only_verified_payload_bytes(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    envelope = _produce(fixture)["envelope"]
    parsed_payloads: list[bytes] = []
    result = rule24.verify_rule24_attestation(
        envelope=envelope,
        trust_policy_path=fixture["trust_policy"],
        pinned_public_key_path=fixture["public_key"],
        target_path=fixture["target"],
        expected_target_name=TARGET_NAME,
        expected_target_media_type=TARGET_TYPE,
        rule24_policy_path=fixture["policy"],
        rule24_policy_name=POLICY_NAME,
        measurement_inputs=fixture["measurements"],
        expected_challenge_path=fixture["challenge"],
        replay_state_dir=fixture["replay_state"],
        verified_payload_observer=parsed_payloads.append,
    )

    assert result["status"] == "PASS"
    assert parsed_payloads == [base64.b64decode(envelope["payload"])]


@pytest.mark.parametrize(
    ("runner", "reason"),
    [
        (lambda *_args, **_kwargs: (_ for _ in ()).throw(FileNotFoundError()), "openssl_missing"),
        (
            lambda *_args, **_kwargs: subprocess.CompletedProcess(
                ["openssl"], 0, "OpenSSL 3.6.2\n", ""
            ),
            "openssl_unsupported",
        ),
        (
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                subprocess.TimeoutExpired(["openssl"], 1)
            ),
            "openssl_timeout",
        ),
        (
            lambda *_args, **_kwargs: subprocess.CompletedProcess(["openssl"], 1, "", "bad"),
            "openssl_nonzero",
        ),
    ],
)
def test_openssl_preflight_failures_are_no_go(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    runner: object,
    reason: str,
) -> None:
    fixture = _fixture(tmp_path)
    envelope = _produce(fixture)["envelope"]
    monkeypatch.setattr(rule24.subprocess, "run", runner)

    result = _verify(fixture, envelope)

    assert result["status"] == "NO-GO"
    assert result["reason"] == reason
    assert result["production_mutation"] is False
    assert result["canary_created"] is False


def test_relative_paths_fail_closed_and_repo_keeps_no_private_key_fixture(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    relative_measurement = rule24.ResourceInput(
        name=MEASUREMENTS[0][0],
        media_type=MEASUREMENTS[0][1],
        path=Path("relative.json"),
    )

    result = rule24.produce_rule24_attestation(
        private_key_path=fixture["private_key"],
        public_key_path=fixture["public_key"],
        producer_id=PRODUCER_ID,
        target_path=fixture["target"],
        target_name=TARGET_NAME,
        target_media_type=TARGET_TYPE,
        rule24_policy_path=fixture["policy"],
        rule24_policy_name=POLICY_NAME,
        measurement_inputs=[relative_measurement, fixture["measurements"][1]],
        correlation=CORRELATION,
        challenge=CHALLENGE,
    )

    assert result["status"] == "NO-GO"
    assert result["reason"] == "path_not_canonical"
    assert result["production_mutation"] is False
    assert result["canary_created"] is False
    assert not list(Path("tests").glob("**/*.pem"))
    assert not list(Path("tests").glob("**/*.key"))
