---
schema_version: 1
title: Pantheon Acceptance B gen05 dangling registry guard bounded Repair
date: 2026-08-28
owner: codex-repair-worker
status: complete
rca: pantheon_acceptance_b_gen05_dangling_registry_guard_rca_20260828/result.md
verdict: GO / BOUNDED_REPAIR_DELIVERED_PRODUCTION_NOT_ACCEPTED
---

# Repair Scope

## Target

讓已具合法 current `identity_envelope` 且 state `lane` 與 envelope lane 精確一致的 legacy
`translate_existing` active run，在 brief 缺少 top-level `lane` 時不再被
`_active_run_integrity_block` 誤判為 dangling。

## Allowed files

- `scripts/agy_gemini_coordinator.py`
- `tests/test_agy_gemini_coordinator.py`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-ACCEPTANCE-B-GEN05-DANGLING-REGISTRY-GUARD-REPAIR-20260828.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_dangling_registry_guard_repair_20260828/`

## Forbidden

- 不修改 registration、全域 identity helper、publisher、promotion、registry、brief、queue、continuation 或 production state。
- 不 resume、不重跑 planning provider、不建立 gen06、不 publish、不 tag、不 push、不 commit、不 merge、不 deploy。

## Frontier

只在 `_active_run_integrity_block` 的 validated current envelope seam 修補：

- brief lane 存在時，仍使用 `_identity_envelope_from_brief(brief)` 與 current envelope 精確比對。
- legacy `translate_existing` brief lane 缺失時，必須先驗 state lane 存在、合法，且與 valid envelope lane 完全一致。
- fallback 只可用 brief mode、state/envelope lane、brief article ids 重建 observed envelope，並與 current envelope 精確比對。
- state lane 缺失、非法、mismatch、article ids/mode/digest mismatch 持續 fail closed。

## Verification

- 保存 current RED。
- minimal fix 後跑 matching GREEN。
- 跑 4 個 fail-closed negative cases。
- 跑既有 observed lane drift test。
- 跑受影響 coordinator test file。
- 跑 `git diff --check`。
- 確認無 `[DBG-]`。
