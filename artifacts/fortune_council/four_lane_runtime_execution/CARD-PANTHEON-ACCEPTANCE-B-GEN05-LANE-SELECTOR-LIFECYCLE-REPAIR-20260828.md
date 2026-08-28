---
schema_version: 1
title: Pantheon Acceptance B gen05 lane selector lifecycle repair
date: 2026-08-28
status: COMPLETE_REVIEW_GO
owner: bounded_repair_worker
scope: gen05 lane selector lifecycle repair only
target_run: auto-i18n-ja-1414b75a404721e95e74
target_actor: 8a50395f67d22343fec4b0a8a5f41c8f40ac360e
evidence_dir: artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_lane_selector_lifecycle_repair_20260828
---

# 目標

讓 `scripts/agy_gemini_coordinator.py:_lane_for_state` 與 8a
`_active_run_integrity_block` 共用等價的窄 legacy translation lane authority，
使 production-shaped partial state 可被 exact lane-mode selector 選中並 tick。

# Source allowlist

- `scripts/agy_gemini_coordinator.py`
- `tests/test_agy_gemini_coordinator.py`
- 本卡與
  `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_lane_selector_lifecycle_repair_20260828/`

# 禁止

- 不修改 production runtime state。
- 不 push、promotion、deploy、publish、tag。
- 不呼叫 provider。
- 不建立 gen06。
- 不改 `scripts/agy_multilingual_pipeline.py`。
- 不改 promotion、registry/state data 或其他檔案。

# 驗收

- production-shaped exact-cycle positive 先在 8a RED，實作後 GREEN。
- fail-closed negatives 覆蓋：
  - unknown non-null routing schema version
  - state mode without routing schema
  - invalid identity envelope digest
  - lane drift
  - non-translation envelope
  - brief lane drift
- Targeted tests、`tests/test_agy_gemini_coordinator.py` 全檔與 `git diff --check`
  皆 PASS。
