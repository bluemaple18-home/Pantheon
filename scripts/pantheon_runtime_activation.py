#!/usr/bin/env python3
"""七服務 activation token 的薄驗證層。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from scripts import pantheon_content_runtime_manifest as formal_runtime


T = TypeVar("T")


class RuntimeActivationError(ValueError):
    """activation token 不完整、過期或 identity 不一致。"""


def publish_generation_token(
    token_path: Path,
    ready_root: Path,
    manifest: dict[str, Any],
    *,
    correlation_id: str,
) -> dict[str, Any]:
    """七個服務 ack 完整一致時，原子發布單一 generation token。"""
    if not correlation_id or correlation_id.strip() != correlation_id:
        raise RuntimeActivationError("activation correlation id is invalid")
    try:
        activation = formal_runtime.activate_barrier(token_path, ready_root, manifest)
    except formal_runtime.RuntimeManifestError as error:
        raise RuntimeActivationError(str(error)) from error
    return {
        **activation,
        "activation_token": str(token_path),
        "correlation_id": correlation_id,
    }


def validate_token_payload(
    token_path: Path,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    """驗證 token 與當前 manifest generation/identity 完全一致。"""
    if not token_path.is_absolute():
        raise RuntimeActivationError("activation token path is invalid")
    try:
        return formal_runtime.validate_barrier(token_path, manifest)
    except formal_runtime.RuntimeManifestError as error:
        raise RuntimeActivationError(str(error)) from error


def validate_service_before_io(
    token_path: Path,
    manifest: dict[str, Any],
    service_label: str,
    *,
    queue_root: Path,
    state_root: Path,
    actor_root: Path,
    log_root: Path,
) -> dict[str, Any]:
    """在服務第一次 queue/state I/O 前重驗 token 與 runtime identity。"""
    token_receipt = validate_token_payload(token_path, manifest)
    try:
        runtime_receipt = formal_runtime.validate_runtime_tick(
            service_label,
            queue_root=queue_root,
            state_root=state_root,
            actor_root=actor_root,
            log_root=log_root,
        )
    except formal_runtime.RuntimeManifestError as error:
        raise RuntimeActivationError(str(error)) from error
    return {
        "status": "PASS",
        "activation": token_receipt,
        "runtime": runtime_receipt,
    }


def run_after_activation_token(
    token_path: Path,
    manifest: dict[str, Any],
    service_label: str,
    *,
    queue_root: Path,
    state_root: Path,
    actor_root: Path,
    log_root: Path,
    operation: Callable[[], T],
) -> T:
    """只有 token 與 service identity 重驗通過才執行 queue/state I/O。"""
    validate_service_before_io(
        token_path,
        manifest,
        service_label,
        queue_root=queue_root,
        state_root=state_root,
        actor_root=actor_root,
        log_root=log_root,
    )
    return operation()


def validate_rollback_loaded_identities(
    expected: dict[str, dict[str, Any]],
    actual: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    try:
        return formal_runtime.validate_rollback_identities(expected, actual)
    except formal_runtime.RuntimeManifestError as error:
        raise RuntimeActivationError(str(error)) from error
