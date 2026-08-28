---
schema_version: 1
title: Pantheon Acceptance B gen06 terminal reject next-generation seam repair
date: 2026-08-28
status: RE_REVIEW_REQUESTED
mode: REPAIR_ONLY
source_commit: 99507c67e27d9e6f3af4e33c3ab0727682ed82bd
target_run: auto-i18n-ja-1414b75a404721e95e74
target_generation: 6
evidence_dir: artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_terminal_reject_next_generation_seam_repair_20260828
source_allowlist:
  - scripts/agy_multilingual_pipeline.py
  - tests/test_agy_multilingual_pipeline.py
forbidden:
  - production mutation
  - provider call
  - live gen06 creation
  - push
  - deploy
  - publish
  - commit
  - new registry/FSM/database/runtime
---

# 目標

補上唯一 bounded Repair：讓正式 continuation 有一個可規劃、可明確 execute、
可重播且綁定完整 authority 的 terminal Reviewer REJECT → next generation
授權 seam。

# 邊界

- 只修改 `scripts/agy_multilingual_pipeline.py`、直接測試與本卡 evidence。
- 不修改 runtime state、queue、registry、production artifact 或 content。
- 不呼叫 provider；測試僅使用 fake provider / monkeypatch。
- 不處理 Rule24 swap telemetry source/policy；上線時仍須用正式 host telemetry。

# 驗收

1. 新 formal function/CLI 預設 plan-only，只有 explicit execute 才寫入。
2. 只接受：
   - continuation `status=complete`
   - terminal generation Reviewer 全部 `REJECT`
   - deterministic hard failure
   - `next_generation = terminal_generation + 1`
   - target next generation dir absent
   - source / locale plan / source-ref map / terminal candidate / terminal review hashes 全綁定
   - authority digest valid
3. execute 寫一次性 authority-transition receipt，並只把 lifecycle 轉成 existing
   `continue_writer_reviewer` 能建立恰一個 next generation 的最小 state。
4. idempotent replay 不產生 gen07；ACCEPT、缺 review、hash drift、已有 next gen、
   ambiguous root 全 fail closed。
5. RED→GREEN 測試、受影響 suite、py_compile、`git diff --check` 全部留證。
