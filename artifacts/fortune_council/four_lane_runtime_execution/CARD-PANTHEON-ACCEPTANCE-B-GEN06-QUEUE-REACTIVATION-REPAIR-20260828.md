---
status: RE_REVIEW_REQUESTED
owner: codex
task: pantheon_acceptance_b_gen06_queue_reactivation_repair_20260828
created_at: 2026-08-28T18:30:00+08:00
scope: bounded_repair
---

# Pantheon Acceptance B gen06 queue reactivation Repair

## 目標

實作唯一 bounded Repair：在 terminal Reviewer REJECT 的 next-generation authority 已正式授權後，提供 hash-bound 的 queue registry reactivation seam，讓 coordinator exact cycle 能選中同一 run。

## 邊界

- Source allowlist：`scripts/agy_gemini_coordinator.py`、`tests/test_agy_gemini_coordinator.py`。
- Artifact allowlist：本卡與本輪 result。
- 禁止 production、provider、publish、push、commit、手改 registry/state。
- 禁止新 registry、FSM、database、generic rerun。

## 驗收

- plan-only 預設 zero-write。
- execute 只把 exact queue registry 從 complete/result complete 切回 active，並清除既有 resume 契約允許的 result/error。
- 綁定 exact run-dir/run-id、registry digest、authority transition digest、state_after digest、run-local active next_generation。
- 已 active exact replay 可安全辨識；其他 drift fail closed。
- 不建立 generation。
- RED/GREEN、targeted/affected、py_compile、`git diff --check`。
