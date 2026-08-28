---
schema_version: 1
title: Pantheon Acceptance B gen05 production entrypoint INVALID_RECEIPT repair
date: 2026-08-28
owner: codex-repair-worker
status: RE_REVIEW_REQUESTED
mode: BOUNDED_REPAIR
target_run: auto-i18n-ja-1414b75a404721e95e74
source_job_id: 61a83c341d39c882d5eed8ea23b7f805a89085e3
target_commit_base: 23eab63ea31031094aa084faee0e5ff65d326533
evidence_dir: artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_production_entrypoint_invalid_receipt_repair_20260828
---

# 目標

修復 gen05 production entrypoint `INVALID_RECEIPT` 根因，不觸碰 production。

# Allowlist

- `scripts/agy_gemini_runner.py`
- `scripts/agy_gemini_coordinator.py`
- `tests/test_agy_gemini_runner.py`
- `tests/test_agy_gemini_coordinator.py`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-ACCEPTANCE-B-GEN05-PRODUCTION-ENTRYPOINT-INVALID-RECEIPT-REPAIR-20260828.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_production_entrypoint_invalid_receipt_repair_20260828/`

# 禁止

- 不 production mutation。
- 不 push、promotion、deploy、publish、tag。
- 不呼叫 provider。
- 不手改 production queue/state/registry。
- 不建立 gen06。
- 不新增 registry/FSM/database。
- 不 commit。

# 驗收

- production service label 缺 credential transport / allocator / model-route
  必要 env 時，runner 必須在 claim 前 fail-closed，queue/state/archive/failed/
  attempt marker 全不變。
- 提供薄的正式 exact one-shot operator entrypoint，使用當前
  manifest/barrier 與 plist `EnvironmentVariables`，禁止使用 stale
  `ProgramArguments`，禁止輸出 secret。
- 沿用既有 failed-external replacement seam，極窄支援 provider-attempt=0
  的 `INVALID_RECEIPT` residue、legacy null correlation 與 no-error-code
  failed receipt；不得放寬一般 invalid receipt。
- RED-capable tests 先 RED 後 GREEN。
- 受影響測試與 `git diff --check` PASS。
