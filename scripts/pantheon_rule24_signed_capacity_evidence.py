#!/usr/bin/env python3
"""Rule24 signed capacity evidence composition。"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Callable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import pantheon_rule24_dsse_attestation as rule24
from scripts.pantheon_writer_vnext_runtime_activation_capacity import (
    CAPABILITIES,
    CAPACITY_RECEIPT_MEDIA_TYPE,
    CYCLE_MEASUREMENT_MEDIA_TYPE,
    CapacityEvaluator,
    CapacityProofBlocked,
    Cleanup,
    Sampler,
    Workload,
    run_capacity_proof,
    run_capacity_proof_evidence_bundle,
)


SCHEMA_VERSION = 1
CAPACITY_RECEIPT_NAME = "capacity-receipt.json"
CYCLE_MEASUREMENT_NAMES = ("cycle-1-measurements.json", "cycle-2-measurements.json")
NO_SIDE_EFFECT_FLAGS = {
    "production_mutation": False,
    "canary_created": False,
    "authorization_granted": False,
}
CAPACITY_RECEIPT_KEYS = {
    "schema_version",
    "status",
    "mode",
    "cycles",
    "policy",
    "projections",
    "stop_loss_negative_result",
    "canary_created",
    "production_mutation",
}
CYCLE_KEYS = {
    "cycle",
    "execution_line_id",
    "correlation_id",
    "root",
    "root_unique",
    "capability_receipt_status",
    "seven_step_capabilities",
    "canary_created",
    "production_mutation",
    "before",
    "peak",
    "after_cleanup",
    "growth_bytes_per_hour",
    "peak_transaction_temp_bytes",
    "cleanup",
}
SAMPLE_KEYS = {
    "label",
    "sampled_epoch",
    "elapsed_seconds",
    "host_total_bytes",
    "host_free_bytes",
    "project_bytes",
    "file_count",
    "process_rss_bytes",
    "swap_used_bytes",
}
CLEANUP_KEYS = {
    "root_exists_after_cleanup",
    "elapsed_seconds",
    "reclaimed_bytes",
    "reclaimed_file_count",
}
POLICY_KEYS = {
    "max_bytes",
    "max_file_count",
    "normal_growth_bytes_per_hour",
    "peak_window_seconds",
    "recovery_deadline_seconds",
    "retention_seconds",
    "sampling_interval_seconds",
    "max_rss_growth_bytes_per_sample",
    "max_swap_growth_bytes_per_sample",
}
PROJECTION_KEYS = {
    "measured_max_growth_bytes_per_hour",
    "projected_growth_bytes_per_hour",
    "hour_peak_bytes",
    "day_peak_bytes",
    "retention_peak_bytes",
    "host_reserve_bytes",
    "host_free_after_projection_bytes",
}
INTEGER_FIELDS = {
    "schema_version",
    "cycle",
    "host_total_bytes",
    "host_free_bytes",
    "project_bytes",
    "file_count",
    "process_rss_bytes",
    "swap_used_bytes",
    "growth_bytes_per_hour",
    "peak_transaction_temp_bytes",
    "reclaimed_bytes",
    "reclaimed_file_count",
    *POLICY_KEYS,
    *PROJECTION_KEYS,
}
FLOAT_FIELDS = {"sampled_epoch", "elapsed_seconds"}


@dataclass(frozen=True)
class CapacityArtifactInput:
    """Verifier-owned exact bytes for one capacity cycle measurement."""

    logical_name: str
    media_type: str
    path: Path
    raw_bytes: bytes


class SignedCapacityEvidenceError(ValueError):
    """Deterministic NO-GO reason for the composition layer."""

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


def _pass(**fields: object) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "mode": "verify-signed-capacity-evidence",
        **fields,
        **NO_SIDE_EFFECT_FLAGS,
    }


def _canonical_path(path: Path | str, label: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise SignedCapacityEvidenceError("path_not_canonical", f"{label} must be absolute")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise SignedCapacityEvidenceError("path_not_canonical", f"{label} must exist") from error
    if resolved != candidate or not candidate.is_file():
        raise SignedCapacityEvidenceError(
            "path_not_canonical",
            f"{label} must be its canonical file realpath",
        )
    return candidate


def _read_exact_path_bytes(path: Path | str, raw_bytes: bytes, label: str) -> Path:
    if type(raw_bytes) is not bytes:
        raise SignedCapacityEvidenceError(f"{label}_bytes_contract", f"{label} bytes must be bytes")
    canonical = _canonical_path(path, label)
    if canonical.read_bytes() != raw_bytes:
        raise SignedCapacityEvidenceError(
            f"{label}_bytes_mismatch",
            f"{label} bytes must match caller-owned path",
        )
    return canonical


def _read_bundle_authority_bytes(artifact: object, label: str) -> bytes:
    path = _canonical_path(getattr(artifact, "path"), label)
    raw_bytes = path.read_bytes()
    if (
        hashlib.sha256(raw_bytes).hexdigest() != getattr(artifact, "sha256")
        or len(raw_bytes) != getattr(artifact, "byte_length")
    ):
        raise SignedCapacityEvidenceError(
            "capacity_bundle_drift",
            f"{label} bytes drifted from bundle authority",
        )
    return raw_bytes


def _load_json_bytes(raw_bytes: bytes, reason: str) -> Mapping[str, Any]:
    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SignedCapacityEvidenceError(reason, "capacity artifact must be JSON") from error
    if not isinstance(payload, Mapping):
        raise SignedCapacityEvidenceError(reason, "capacity artifact must be an object")
    return payload


def _expect_keys(payload: Mapping[str, Any], allowed: set[str]) -> None:
    if set(payload) != allowed:
        raise SignedCapacityEvidenceError("capacity_unknown_field", "capacity schema key mismatch")


def _expect_number(field: str, value: object) -> None:
    if field in INTEGER_FIELDS:
        if type(value) is bool or not isinstance(value, int) or value < 0:
            raise SignedCapacityEvidenceError(
                "capacity_numeric_contract",
                f"{field} must be a non-negative integer",
            )
        return
    if field in FLOAT_FIELDS:
        if type(value) is bool or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise SignedCapacityEvidenceError(
                "capacity_numeric_contract",
                f"{field} must be finite",
            )


def _validate_sample(sample: object) -> None:
    if not isinstance(sample, Mapping):
        raise SignedCapacityEvidenceError("capacity_cycle_identity", "sample must be an object")
    _expect_keys(sample, SAMPLE_KEYS)
    for key, value in sample.items():
        _expect_number(str(key), value)
    if type(sample["label"]) is not str or not sample["label"]:
        raise SignedCapacityEvidenceError("capacity_cycle_identity", "sample label is invalid")


def _validate_cleanup(cleanup: object) -> None:
    if not isinstance(cleanup, Mapping):
        raise SignedCapacityEvidenceError("capacity_cycle_identity", "cleanup must be an object")
    _expect_keys(cleanup, CLEANUP_KEYS)
    for key, value in cleanup.items():
        _expect_number(str(key), value)
    if cleanup["root_exists_after_cleanup"] is not False:
        raise SignedCapacityEvidenceError(
            "capacity_production_boundary",
            "capacity cleanup must prove root removal",
        )


def _validate_cycle(cycle: object, expected_cycle: int) -> Mapping[str, Any]:
    if not isinstance(cycle, Mapping):
        raise SignedCapacityEvidenceError("capacity_cycle_identity", "cycle must be an object")
    _expect_keys(cycle, CYCLE_KEYS)
    if cycle["cycle"] != expected_cycle:
        raise SignedCapacityEvidenceError("capacity_cycle_identity", "cycle order drift")
    if cycle["capability_receipt_status"] != "PASS":
        raise SignedCapacityEvidenceError("capacity_status", "cycle receipt did not PASS")
    if cycle["seven_step_capabilities"] != list(CAPABILITIES):
        raise SignedCapacityEvidenceError("capacity_cycle_identity", "capability chain mismatch")
    if cycle["canary_created"] is not False or cycle["production_mutation"] is not False:
        raise SignedCapacityEvidenceError(
            "capacity_production_boundary",
            "cycle crossed production boundary",
        )
    if type(cycle["root_unique"]) is not bool or cycle["root_unique"] is not True:
        raise SignedCapacityEvidenceError("capacity_cycle_identity", "cycle root must be unique")
    for key in ("execution_line_id", "correlation_id", "root"):
        if type(cycle[key]) is not str or not cycle[key]:
            raise SignedCapacityEvidenceError("capacity_cycle_identity", f"{key} is invalid")
    for key, value in cycle.items():
        _expect_number(str(key), value)
    _validate_sample(cycle["before"])
    _validate_sample(cycle["peak"])
    _validate_sample(cycle["after_cleanup"])
    _validate_cleanup(cycle["cleanup"])
    return cycle


def _validate_policy(policy: object) -> None:
    if not isinstance(policy, Mapping):
        raise SignedCapacityEvidenceError("capacity_policy_contract", "policy must be an object")
    _expect_keys(policy, POLICY_KEYS)
    for key, value in policy.items():
        _expect_number(str(key), value)


def _validate_projections(projections: object) -> None:
    if not isinstance(projections, Mapping):
        raise SignedCapacityEvidenceError(
            "capacity_projection_contract",
            "projections must be an object",
        )
    _expect_keys(projections, PROJECTION_KEYS)
    for key, value in projections.items():
        _expect_number(str(key), value)
    if projections["host_free_after_projection_bytes"] < projections["host_reserve_bytes"]:
        raise SignedCapacityEvidenceError(
            "capacity_projection_contract",
            "capacity projection crosses host reserve",
        )


def _capacity_cycle_resources(
    capacity_cycle_artifacts: Sequence[CapacityArtifactInput],
) -> tuple[list[rule24.ResourceInput], list[Mapping[str, Any]]]:
    if len(capacity_cycle_artifacts) != 2:
        raise SignedCapacityEvidenceError("capacity_cycle_count", "exactly two capacity cycles are required")
    identities = [
        (artifact.logical_name, artifact.media_type, Path(artifact.path))
        for artifact in capacity_cycle_artifacts
    ]
    if len(set(identities)) != 2 or len({identity[2] for identity in identities}) != 2:
        raise SignedCapacityEvidenceError("capacity_cycle_duplicate", "capacity cycles must be distinct")
    resources: list[rule24.ResourceInput] = []
    parsed: list[Mapping[str, Any]] = []
    for index, artifact in enumerate(capacity_cycle_artifacts):
        expected_name = CYCLE_MEASUREMENT_NAMES[index]
        if artifact.logical_name != expected_name:
            raise SignedCapacityEvidenceError("capacity_cycle_identity", "capacity cycle order mismatch")
        if artifact.media_type != CYCLE_MEASUREMENT_MEDIA_TYPE:
            raise SignedCapacityEvidenceError("capacity_cycle_identity", "capacity cycle media type mismatch")
        path = _read_exact_path_bytes(artifact.path, artifact.raw_bytes, f"capacity_cycle_{index + 1}")
        parsed.append(_load_json_bytes(artifact.raw_bytes, "capacity_artifact_json"))
        resources.append(rule24.ResourceInput(artifact.logical_name, artifact.media_type, path))
    return resources, parsed


def _validate_capacity_domain(
    *,
    capacity_receipt_bytes: bytes,
    parsed_cycle_artifacts: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any]:
    receipt = _load_json_bytes(capacity_receipt_bytes, "capacity_artifact_json")
    _expect_keys(receipt, CAPACITY_RECEIPT_KEYS)
    if receipt["schema_version"] != SCHEMA_VERSION:
        raise SignedCapacityEvidenceError("capacity_schema_version", "capacity schema mismatch")
    if receipt["status"] != "PASS" or receipt["mode"] != "synthetic-non-production-capacity-proof":
        raise SignedCapacityEvidenceError("capacity_status", "capacity receipt did not PASS")
    if receipt["canary_created"] is not False or receipt["production_mutation"] is not False:
        raise SignedCapacityEvidenceError(
            "capacity_production_boundary",
            "capacity receipt crossed production boundary",
        )
    if receipt["stop_loss_negative_result"] != "BLOCKED":
        raise SignedCapacityEvidenceError(
            "capacity_stop_loss_contract",
            "capacity receipt must retain BLOCKED stop-loss",
        )
    cycles = receipt["cycles"]
    if not isinstance(cycles, list) or len(cycles) != 2:
        raise SignedCapacityEvidenceError("capacity_cycle_count", "receipt must contain exactly two cycles")
    validated_cycles = [_validate_cycle(cycles[0], 1), _validate_cycle(cycles[1], 2)]
    if list(parsed_cycle_artifacts) != validated_cycles:
        raise SignedCapacityEvidenceError(
            "capacity_cycle_identity",
            "capacity cycle artifact bytes drifted from receipt",
        )
    _validate_policy(receipt["policy"])
    _validate_projections(receipt["projections"])
    return receipt


def produce_signed_capacity_evidence(
    *,
    private_key_path: Path | str,
    public_key_path: Path | str,
    producer_id: str,
    target_path: Path | str,
    target_name: str,
    target_media_type: str,
    rule24_policy_path: Path | str,
    rule24_policy_name: str,
    capacity_sandbox_root: Path | str,
    evidence_root: Path | str,
    runtime_receipt: Mapping[str, Any],
    actor_identity: str,
    brief: Mapping[str, Any],
    capacity_policy: Mapping[str, Any],
    correlation: str,
    challenge: str,
    sampler: Sampler | None = None,
    workload: Workload | None = None,
    cleanup: Cleanup | None = None,
    capacity_evaluator: CapacityEvaluator = run_capacity_proof,
) -> dict[str, object]:
    try:
        bundle_kwargs: dict[str, Any] = {
            "capacity_sandbox_root": Path(capacity_sandbox_root),
            "evidence_root": Path(evidence_root),
            "runtime_receipt": runtime_receipt,
            "actor_identity": actor_identity,
            "brief": brief,
            "policy": capacity_policy,
            "capacity_evaluator": capacity_evaluator,
        }
        if sampler is not None:
            bundle_kwargs["sampler"] = sampler
        if workload is not None:
            bundle_kwargs["workload"] = workload
        if cleanup is not None:
            bundle_kwargs["cleanup"] = cleanup
        bundle = run_capacity_proof_evidence_bundle(**bundle_kwargs)
        capacity_receipt_bytes = _read_bundle_authority_bytes(
            bundle.capacity_receipt,
            "capacity_receipt",
        )
        cycle_artifacts = tuple(
            CapacityArtifactInput(
                logical_name=artifact.logical_name,
                media_type=artifact.media_type,
                path=artifact.path,
                raw_bytes=_read_bundle_authority_bytes(
                    artifact,
                    f"capacity_cycle_{index + 1}",
                ),
            )
            for index, artifact in enumerate(bundle.cycle_measurements)
        )
        measurement_inputs, parsed_cycles = _capacity_cycle_resources(cycle_artifacts)
        _validate_capacity_domain(
            capacity_receipt_bytes=capacity_receipt_bytes,
            parsed_cycle_artifacts=parsed_cycles,
        )
        result = rule24.produce_rule24_attestation(
            private_key_path=private_key_path,
            public_key_path=public_key_path,
            producer_id=producer_id,
            target_path=target_path,
            target_name=target_name,
            target_media_type=target_media_type,
            rule24_policy_path=rule24_policy_path,
            rule24_policy_name=rule24_policy_name,
            measurement_inputs=measurement_inputs,
            correlation=correlation,
            challenge=challenge,
            capacity_evidence_input=rule24.ResourceInput(
                rule24.CAPACITY_EVIDENCE_NAME,
                rule24.CAPACITY_EVIDENCE_MEDIA_TYPE,
                bundle.capacity_receipt.path,
            ),
        )
        if result["status"] != "PASS":
            return _no_go(str(result.get("reason", "dsse_produce")))
        return {
            **result,
            "capacity_artifacts": [
                {
                    "logical_name": artifact.logical_name,
                    "path": str(artifact.path),
                    "sha256": artifact.sha256,
                    "media_type": artifact.media_type,
                    "byte_length": artifact.byte_length,
                }
                for artifact in bundle.artifacts
            ],
            **NO_SIDE_EFFECT_FLAGS,
        }
    except CapacityProofBlocked as error:
        return _no_go(str(error.payload.get("case") or "capacity_blocked"))
    except (SignedCapacityEvidenceError, rule24.Rule24AttestationError) as error:
        return _no_go(error.reason)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        return _no_go(type(error).__name__)


def _original_envelope(envelope: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(envelope, Mapping):
        raise SignedCapacityEvidenceError("envelope_contract", "envelope must be an object")
    try:
        return json.loads(json.dumps(envelope, sort_keys=True, separators=(",", ":")))
    except (TypeError, ValueError) as error:
        raise SignedCapacityEvidenceError("envelope_contract", "envelope must be JSON") from error


def verify_signed_capacity_evidence(
    *,
    envelope: Mapping[str, Any],
    trust_policy_path: Path | str,
    pinned_public_key_path: Path | str,
    target_path: Path | str,
    expected_target_name: str,
    expected_target_media_type: str,
    rule24_policy_path: Path | str,
    rule24_policy_name: str,
    capacity_receipt_path: Path | str,
    capacity_receipt_bytes: bytes,
    capacity_cycle_artifacts: Sequence[CapacityArtifactInput],
    expected_challenge_path: Path | str,
    replay_state_dir: Path | str,
    verified_payload_observer: Callable[[bytes], None] | None = None,
) -> dict[str, object]:
    try:
        original_envelope = _original_envelope(envelope)
        receipt_path = _read_exact_path_bytes(
            capacity_receipt_path,
            capacity_receipt_bytes,
            "capacity_receipt",
        )
        if receipt_path.name != CAPACITY_RECEIPT_NAME:
            raise SignedCapacityEvidenceError(
                "capacity_receipt_identity",
                "capacity receipt logical name mismatch",
            )
        measurement_inputs, parsed_cycles = _capacity_cycle_resources(capacity_cycle_artifacts)
        authenticated = rule24.authenticate_rule24_attestation(
            envelope=original_envelope,
            trust_policy_path=trust_policy_path,
            pinned_public_key_path=pinned_public_key_path,
            target_path=target_path,
            expected_target_name=expected_target_name,
            expected_target_media_type=expected_target_media_type,
            rule24_policy_path=rule24_policy_path,
            rule24_policy_name=rule24_policy_name,
            measurement_inputs=measurement_inputs,
            expected_challenge_path=expected_challenge_path,
            capacity_evidence_bytes=capacity_receipt_bytes,
        )
        _validate_capacity_domain(
            capacity_receipt_bytes=capacity_receipt_bytes,
            parsed_cycle_artifacts=parsed_cycles,
        )
        committed = rule24.commit_rule24_replay_claim(
            envelope=original_envelope,
            trust_policy_path=trust_policy_path,
            pinned_public_key_path=pinned_public_key_path,
            target_path=target_path,
            expected_target_name=expected_target_name,
            expected_target_media_type=expected_target_media_type,
            rule24_policy_path=rule24_policy_path,
            rule24_policy_name=rule24_policy_name,
            measurement_inputs=measurement_inputs,
            expected_challenge_path=expected_challenge_path,
            replay_state_dir=replay_state_dir,
            capacity_evidence_bytes=capacity_receipt_bytes,
        )
        if committed["status"] != "PASS":
            return _no_go(str(committed.get("reason", "replay_claim")))
        if verified_payload_observer is not None:
            verified_payload_observer(authenticated.payload)
        return _pass(
            authenticated_statement_digest=authenticated.authenticated_statement_digest,
            target_digest=authenticated.target_digest,
            policy_digest=authenticated.policy_digest,
            measurement_digests=list(authenticated.measurement_digests),
            capacity_evidence_digest=authenticated.capacity_evidence_digest,
            correlation_challenge_digest=authenticated.correlation_challenge_digest,
        )
    except (SignedCapacityEvidenceError, rule24.Rule24AttestationError) as error:
        return _no_go(error.reason)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        return _no_go(type(error).__name__)


def _load_json_file(path: Path | str) -> Mapping[str, Any]:
    candidate = _canonical_path(path, "json_path")
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise SignedCapacityEvidenceError("json_contract", "JSON file must contain an object")
    return payload


def _read_cycle_argument(value: str) -> CapacityArtifactInput:
    parts = value.split(":", 2)
    if len(parts) != 3:
        raise SignedCapacityEvidenceError(
            "capacity_cycle_contract",
            "cycle artifact must be name:mediaType:/absolute/path",
        )
    path = _canonical_path(parts[2], "capacity_cycle_path")
    return CapacityArtifactInput(
        logical_name=parts[0],
        media_type=parts[1],
        path=path,
        raw_bytes=path.read_bytes(),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rule24 signed capacity evidence composition")
    subparsers = parser.add_subparsers(dest="mode", required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--envelope", required=True)
    verify.add_argument("--trust-policy", required=True)
    verify.add_argument("--pinned-public-key", required=True)
    verify.add_argument("--target-path", required=True)
    verify.add_argument("--target-name", required=True)
    verify.add_argument("--target-media-type", required=True)
    verify.add_argument("--rule24-policy-path", required=True)
    verify.add_argument("--rule24-policy-name", required=True)
    verify.add_argument("--capacity-receipt", required=True)
    verify.add_argument("--cycle-artifact", action="append", default=[])
    verify.add_argument("--expected-challenge", required=True)
    verify.add_argument("--replay-state-dir", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        capacity_receipt_path = _canonical_path(args.capacity_receipt, "capacity_receipt")
        result = verify_signed_capacity_evidence(
            envelope=_load_json_file(args.envelope),
            trust_policy_path=Path(args.trust_policy),
            pinned_public_key_path=Path(args.pinned_public_key),
            target_path=Path(args.target_path),
            expected_target_name=args.target_name,
            expected_target_media_type=args.target_media_type,
            rule24_policy_path=Path(args.rule24_policy_path),
            rule24_policy_name=args.rule24_policy_name,
            capacity_receipt_path=capacity_receipt_path,
            capacity_receipt_bytes=capacity_receipt_path.read_bytes(),
            capacity_cycle_artifacts=[_read_cycle_argument(value) for value in args.cycle_artifact],
            expected_challenge_path=Path(args.expected_challenge),
            replay_state_dir=Path(args.replay_state_dir),
        )
    except (SignedCapacityEvidenceError, rule24.Rule24AttestationError) as error:
        result = _no_go(error.reason)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        result = _no_go(type(error).__name__)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
