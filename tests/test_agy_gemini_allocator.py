from __future__ import annotations

import json
from pathlib import Path

import scripts.agy_gemini_allocator as allocator


POOL_ID = "pantheon-production-v1"
MANIFEST_SHA256 = "a" * 64


def _allocate(state: Path, now: float) -> tuple[int, str]:
    with allocator.production_slot_admission(
        state,
        pool_id=POOL_ID,
        manifest_sha256=MANIFEST_SHA256,
        clock=lambda: now,
    ) as admission:
        assert admission.allowed is True
        return admission.commit()


def _cool(
    state: Path,
    slot_id: str,
    now: float,
    *,
    seconds: int = 60,
) -> dict[str, object]:
    return allocator.record_production_rate_limit(
        state,
        pool_id=POOL_ID,
        manifest_sha256=MANIFEST_SHA256,
        slot_id=slot_id,
        cooldown_seconds=seconds,
        clock=lambda: now,
    )


def test_allocator_skips_cooling_slot_and_rejoins_after_expiry(tmp_path: Path) -> None:
    state = tmp_path / "allocator-state.json"

    assert _allocate(state, 1_000.0) == (1, "account-1")
    receipt = _cool(state, "account-1", 1_001.0)
    assert receipt == {
        "slot_id": "account-1",
        "cooldown_started_ms": 1_001_000,
        "cooldown_until_ms": 1_061_000,
        "reason": "API_RATE_LIMITED",
    }
    assert _allocate(state, 1_002.0) == (2, "account-2")
    assert _allocate(state, 1_003.0) == (3, "account-3")
    assert _allocate(state, 1_061.0) == (4, "account-1")

    payload = json.loads(state.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 2
    assert payload["last_ordinal"] == 4
    assert payload["last_slot_id"] == "account-1"
    assert payload["cooldowns"] == []


def test_all_slots_cooling_denies_without_ordinal_or_state_write(tmp_path: Path) -> None:
    state = tmp_path / "allocator-state.json"
    for index, slot_id in enumerate(allocator.PRODUCTION_SLOT_IDS):
        ordinal, selected = _allocate(state, 2_000.0 + index)
        assert ordinal == index + 1
        assert selected == slot_id
        _cool(state, slot_id, 2_000.5 + index)

    before = state.read_bytes()
    with allocator.production_slot_admission(
        state,
        pool_id=POOL_ID,
        manifest_sha256=MANIFEST_SHA256,
        clock=lambda: 2_004.0,
    ) as admission:
        assert admission.allowed is False
        assert admission.receipt == {
            "reason": "API_RATE_LIMITED",
            "cooldowns": [
                {
                    "slot_id": "account-1",
                    "cooldown_started_ms": 2_000_500,
                    "cooldown_until_ms": 2_060_500,
                },
                {
                    "slot_id": "account-2",
                    "cooldown_started_ms": 2_001_500,
                    "cooldown_until_ms": 2_061_500,
                },
                {
                    "slot_id": "account-3",
                    "cooldown_started_ms": 2_002_500,
                    "cooldown_until_ms": 2_062_500,
                },
            ],
        }
    assert state.read_bytes() == before
