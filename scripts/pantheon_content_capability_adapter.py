#!/usr/bin/env python3
"""薄接 production runtime 的 bounded、無外部副作用 capability dry-run。"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Callable, Iterator

from scripts import agy_content_publisher as publisher
from scripts import agy_gemini_coordinator as coordinator
from scripts import agy_gemini_runner as runner
from scripts import pantheon_content_capacity_guard as capacity_guard
from scripts import pantheon_content_runtime_manifest as runtime_manifest
from scripts.agy_gemini_outbox import create_external_request


CAPABILITIES = ("create", "run", "select", "publish", "transaction", "tag", "push")
PREVIOUS = dict(zip(CAPABILITIES, (None, *CAPABILITIES[:-1])))
RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
}


class AdapterBlocked(ValueError):
    """正式 production boundary 拒絕不連續或不完整 handoff。"""


def _digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@contextmanager
def _formal_environment(
    manifest_path: Path,
    manifest: dict[str, Any],
    service_label: str,
    activation_token: Path,
) -> Iterator[None]:
    values = {
        "PANTHEON_FORMAL_RUNTIME": "1",
        "PANTHEON_RUNTIME_MANIFEST": str(manifest_path),
        "PANTHEON_RUNTIME_MANIFEST_DIGEST": manifest["manifest_digest"],
        "PANTHEON_RUNTIME_IDENTITY": manifest["identity"],
        "PANTHEON_RUNTIME_IDENTITY_DIGEST": manifest["runtime_identity_digest"],
        "PANTHEON_RUNTIME_CODE_DIGEST": manifest["runtime_digest"],
        "PANTHEON_RUNTIME_CONFIG_VERSION": manifest["config_version"],
        "PANTHEON_RUNTIME_GENERATION": manifest["generation"],
        "PANTHEON_RUNTIME_SERVICE_LABEL": service_label,
        "PANTHEON_RUNTIME_ACTOR_ROOT": manifest["actor_root"],
        "PANTHEON_RUNTIME_QUEUE_ROOT": manifest["queue_root"],
        "PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT": manifest[
            "publisher_state_root"
        ],
        "PANTHEON_RUNTIME_LOG_ROOT": manifest["log_root"],
        "PANTHEON_RUNTIME_ACTIVATION_TOKEN": str(activation_token),
    }
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update({key: str(value) for key, value in values.items()})
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _load_contract(
    source: dict[str, Any],
) -> tuple[Path, dict[str, Any], Path, Path, Path, Path, dict[str, Any]]:
    manifest_path = Path(str(source.get("runtime_manifest", "")))
    sandbox_root = Path(str(source.get("sandbox_root", "")))
    if (
        not manifest_path.is_absolute()
        or not sandbox_root.is_absolute()
        or not sandbox_root.is_dir()
        or sandbox_root.resolve(strict=True) != sandbox_root
    ):
        raise AdapterBlocked("formal runtime sandbox is invalid")
    manifest = runtime_manifest.load_manifest(
        manifest_path,
        str(source.get("runtime_manifest_digest", "")),
    )
    if manifest["runtime_identity_digest"] != source.get(
        "runtime_identity_digest"
    ):
        raise AdapterBlocked("runtime identity digest mismatch")
    activation_token = Path(str(source.get("activation_token", "")))
    if not activation_token.is_absolute():
        raise AdapterBlocked("activation token is required")
    try:
        activation_receipt = runtime_manifest.validate_barrier(
            activation_token,
            manifest,
        )
    except runtime_manifest.RuntimeManifestError as error:
        raise AdapterBlocked(str(error)) from error
    try:
        queue_root = publisher._require_sandbox_descendant(
            sandbox_root, Path(manifest["queue_root"]), "queue root"
        )
        state_root = publisher._require_sandbox_descendant(
            sandbox_root,
            Path(manifest["publisher_state_root"]),
            "publisher state root",
        )
        if queue_root.is_relative_to(state_root) or state_root.is_relative_to(
            queue_root
        ):
            raise publisher.PublishBlocked("queue and publisher state roots overlap")
    except publisher.PublishBlocked as error:
        raise AdapterBlocked(str(error)) from error
    return (
        manifest_path,
        manifest,
        sandbox_root,
        queue_root,
        state_root,
        activation_token,
        activation_receipt,
    )


def _create_step(
    source: dict[str, Any],
    manifest_path: Path,
    manifest: dict[str, Any],
    sandbox_root: Path,
    activation_token: Path,
) -> dict[str, Any]:
    queue_root = Path(manifest["queue_root"])
    run_ids: dict[str, str] = {}
    states: dict[str, dict[str, Any]] = {}
    with _formal_environment(
        manifest_path,
        manifest,
        "com.pantheon.agy-gemini-coordinator",
        activation_token,
    ):
        for lane in coordinator.CONTENT_LANES:
            run_id = "probe-" + hashlib.sha256(
                f"{source['correlation_id']}:{lane}".encode()
            ).hexdigest()[:24]
            run_dir = sandbox_root / "runs" / lane
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "brief.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "run_id": run_id,
                        "mode": "create",
                        "articles": [],
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            states[lane] = coordinator.register_run(
                run_dir,
                queue_root,
                correlation_id=str(source["correlation_id"]),
            )
            run_ids[lane] = run_id
    return {
        "run_ids": run_ids,
        "coordinator_states": states,
        "production_entrypoints": [
            "scripts.agy_gemini_coordinator:register_run"
        ],
    }


def _run_step(
    source: dict[str, Any],
    manifest_path: Path,
    manifest: dict[str, Any],
    _sandbox_root: Path,
    activation_token: Path,
) -> dict[str, Any]:
    run_ids = source.get("run_ids")
    if not isinstance(run_ids, dict) or set(run_ids) != set(coordinator.CONTENT_LANES):
        raise AdapterBlocked("four-lane run identity is incomplete")
    results: dict[str, dict[str, Any]] = {}
    for lane, run_id in run_ids.items():
        lane_root = Path(manifest["queue_root"]) / "lanes" / lane
        with _formal_environment(
            manifest_path,
            manifest,
            f"com.pantheon.agy-gemini-{lane}",
            activation_token,
        ):
            runtime_manifest.validate_runtime_tick(
                f"com.pantheon.agy-gemini-{lane}",
                queue_root=lane_root,
                state_root=Path(manifest["publisher_state_root"]),
                actor_root=Path(manifest["actor_root"]),
                log_root=Path(manifest["log_root"]),
            )
            request = create_external_request(
                lane_root,
                namespace=hashlib.sha256(str(run_id).encode()).hexdigest()[:24],
                role="writer",
                model="gemini-test-writer",
                prompt=f"bounded formal runtime {lane}",
                response_schema=RESPONSE_SCHEMA,
            )
            result = runner.process_once(
                lane_root,
                lane=lane,
                exact_run_ids=[str(run_id)],
                generate_json=lambda *_args: {"ok": True},
            )
        if result.get("status") != "processed":
            raise AdapterBlocked(f"{lane} production runner did not process")
        results[lane] = {**result, "request_sha256": request["request_sha256"]}
    return {
        "run_ids": run_ids,
        "lane_results": results,
        "production_entrypoints": [
            "scripts.agy_gemini_outbox:create_external_request",
            "scripts.agy_gemini_runner:process_once",
        ],
    }


def _publisher_step(
    capability: str,
    source: dict[str, Any],
    manifest_path: Path,
    manifest: dict[str, Any],
    sandbox_root: Path,
    queue_root: Path,
    state_root: Path,
    activation_token: Path,
    activation_receipt: dict[str, Any],
) -> dict[str, Any]:
    run_ids = source.get("run_ids")
    if not isinstance(run_ids, dict):
        raise AdapterBlocked("publisher run identity is missing")
    with _formal_environment(
        manifest_path,
        manifest,
        "com.pantheon.agy-content-publisher",
        activation_token,
    ):
        runtime_receipt = runtime_manifest.validate_runtime_tick(
            "com.pantheon.agy-content-publisher",
            queue_root=Path(manifest["queue_root"]),
            state_root=Path(manifest["publisher_state_root"]),
            actor_root=Path(manifest["actor_root"]),
            log_root=Path(manifest["log_root"]),
        )
        result = publisher.formal_capability_preflight(
            capability,
            run_ids=run_ids.values(),
            correlation_id=str(source["correlation_id"]),
            trusted_sandbox_root=sandbox_root,
            queue_root=queue_root,
            state_root=state_root,
            runtime_receipt=runtime_receipt,
        )
    entrypoints = [
        str(result["entrypoint"]),
        *(str(value) for value in result.get("called_entrypoints", [])),
    ]
    output: dict[str, Any] = {
        "run_ids": run_ids,
        "publisher_result": result,
        "runtime_receipt": runtime_receipt,
        "production_entrypoints": entrypoints,
        "production_mutation": result["production_mutation"],
        "sandbox_mutation": result["sandbox_mutation"],
    }
    if result["production_mutation"]:
        raise AdapterBlocked("production mutation detected")
    if capability == "transaction":
        def fixture_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
            if command[:2] == ["launchctl", "print"]:
                return subprocess.CompletedProcess(command, 3, "", "")
            if command[:3] == ["sysctl", "-n", "vm.swapusage"]:
                return subprocess.CompletedProcess(
                    command,
                    0,
                    "total = 0.00M used = 0.00M free = 0.00M\n",
                    "",
                )
            return subprocess.CompletedProcess(command, 1, "", "unexpected command")

        with _formal_environment(
            manifest_path,
            manifest,
            "com.pantheon.content-capacity-guard",
            activation_token,
        ):
            runtime_manifest.validate_runtime_tick(
                "com.pantheon.content-capacity-guard",
                queue_root=Path(manifest["queue_root"]),
                state_root=Path(manifest["publisher_state_root"]),
                actor_root=Path(manifest["actor_root"]),
                log_root=Path(manifest["log_root"]),
            )
            guard_result = capacity_guard.preflight(
                Path(manifest["queue_root"]),
                Path(manifest["publisher_state_root"]),
                Path(manifest["log_root"]),
                runner=fixture_runner,
            )
        if guard_result.get("status") != "PASS":
            raise AdapterBlocked("capacity guard production preflight failed")
        output["capacity_guard"] = guard_result
        output["production_entrypoints"].append(
            "scripts.pantheon_content_capacity_guard:preflight"
        )
    output["activation_receipt"] = activation_receipt
    return output


def _production_transition(
    capability: str,
    source: dict[str, Any],
) -> dict[str, Any]:
    (
        manifest_path,
        manifest,
        sandbox_root,
        queue_root,
        state_root,
        activation_token,
        activation_receipt,
    ) = _load_contract(source)
    if capability == "create":
        return _create_step(
            source,
            manifest_path,
            manifest,
            sandbox_root,
            activation_token,
        )
    if capability == "run":
        return _run_step(
            source,
            manifest_path,
            manifest,
            sandbox_root,
            activation_token,
        )
    return _publisher_step(
        capability,
        source,
        manifest_path,
        manifest,
        sandbox_root,
        queue_root,
        state_root,
        activation_token,
        activation_receipt,
    )


def invoke(
    *,
    capability: str,
    input_path: Path,
    output_path: Path,
    expected_input_digest: str,
    actual_input_digest: str,
    execution_id: str,
    correlation_id: str,
    actor_identity: str,
    transition: Callable[[str, dict[str, Any]], dict[str, Any]] = _production_transition,
) -> dict[str, Any]:
    if capability not in CAPABILITIES:
        raise AdapterBlocked("capability is not registered")
    source = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(source, dict):
        raise AdapterBlocked("adapter input must be an object")
    if actual_input_digest != expected_input_digest:
        raise AdapterBlocked("input digest mismatch")
    if source.get("output_digest") != actual_input_digest:
        raise AdapterBlocked("input artifact digest mismatch")
    for field, value in (
        ("execution_id", execution_id),
        ("correlation_id", correlation_id),
        ("actor_identity", actor_identity),
    ):
        if source.get(field) != value:
            raise AdapterBlocked(f"{field} mismatch")
    if source.get("capability") != PREVIOUS[capability]:
        raise AdapterBlocked("previous capability mismatch")
    transition_result = transition(capability, source)
    payload: dict[str, Any] = {
        **source,
        "schema_version": 2,
        "capability": capability,
        "input_digest": actual_input_digest,
        "expected_input_digest": expected_input_digest,
        "entrypoint_outcome": "PASS",
        "mode": "formal-runtime-production-dry-run",
        "production_mutation": False,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        **transition_result,
    }
    payload.pop("output_digest", None)
    payload["output_digest"] = _digest(payload)
    output_path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capability", choices=CAPABILITIES, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-input-digest", required=True)
    parser.add_argument("--actual-input-digest", required=True)
    parser.add_argument("--execution-id", required=True)
    parser.add_argument("--correlation-id", required=True)
    parser.add_argument("--actor-identity", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = invoke(
            capability=args.capability,
            input_path=args.input,
            output_path=args.output,
            expected_input_digest=args.expected_input_digest,
            actual_input_digest=args.actual_input_digest,
            execution_id=args.execution_id,
            correlation_id=args.correlation_id,
            actor_identity=args.actor_identity,
        )
    except (AdapterBlocked, OSError, json.JSONDecodeError, KeyError, ValueError) as error:
        blocked = {
            "schema_version": 2,
            "capability": args.capability,
            "execution_id": args.execution_id,
            "correlation_id": args.correlation_id,
            "actor_identity": args.actor_identity,
            "input_digest": args.actual_input_digest,
            "expected_input_digest": args.expected_input_digest,
            "entrypoint_outcome": "BLOCKED",
            "output_digest": "",
            "error": str(error),
            "mode": "formal-runtime-production-dry-run",
            "production_mutation": False,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        }
        args.output.write_text(
            json.dumps(blocked, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(blocked, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
