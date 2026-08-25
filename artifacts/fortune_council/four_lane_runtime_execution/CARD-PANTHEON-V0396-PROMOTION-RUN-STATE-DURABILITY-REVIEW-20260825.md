---
id: CARD-PANTHEON-V0396-PROMOTION-RUN-STATE-DURABILITY-REVIEW-20260825
status: ready
chain_id: PANTHEON-PROMOTION-RUN-STATE-DURABILITY-20260825
role: review
cycle: 1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 固定 candidate SHA 的 production promotion 與 durable state 核心契約審查，採 strict/core-bounded Reviewer。
candidate_sha: 178f4504c9e4add4ecb5f35cfff9f92bd115383b
base_sha: 345d9c3184856718254615b58b92655743a8d64a
---

# Pantheon promotion 後發文狀態持久化審查

工作名稱：Pantheon promotion 後發文狀態持久化審查

任務目的：獨立審查 candidate `178f4504c9e4add4ecb5f35cfff9f92bd115383b` 是否真正關閉 promotion 刪除 active run、dangling registry 與 auto-seed identity drift；只判定，不修改產品 source。

## 審查範圍

- Base：`345d9c3184856718254615b58b92655743a8d64a`
- Candidate：`178f4504c9e4add4ecb5f35cfff9f92bd115383b`
- `scripts/pantheon_content_runtime_promotion.py`
- `scripts/agy_gemini_coordinator.py`
- `scripts/install_agy_gemini_coordinator_launchd.sh`
- 對應 tests、V0395 RESULT 與 evidence

## 必查問題

- registry→`run_dir`→`brief.json`→tree digest 是否形成 canonical、durable、promotion 前後一致的閉包。
- `failed_external_job_replacement` active state 跳過 `_active_run_integrity_block()` 是否允許 dangling registry 繼續 new/legacy sweep，重現 auto-seed 新 identity；若會，列 P1。
- installer 將 run root 固定為 `${QUEUE_ROOT}/gsc-copy` 是否打破既有 actor recovery、activation-only、legacy override 或 rollback 契約。
- promotion 的 empty/preserved/completed run、symlink、TOCTOU、digest drift 與 zero-mutation 負向路徑是否足夠。
- 測試是否真的打到「發文中途 promotion 後同 identity 接續」，而非只測 snapshot 結構。

## Verdict 契約

- 只有 P0/P1 可 `REVIEW_NO_GO`；P2/P3 記 residual risk，不移動球門。
- Finding 必須含 severity、path:line、觸發條件、證據、風險、最小修法、validation gap。
- 若 `NO_GO`，回原 V0395 implementation thread targeted repair；不得另開 implementation/Repair thread。
- 若 `GO`，明確列出已重跑驗證與 production 尚未執行的剩餘風險。

## 可寫範圍

- 本卡 `RESULT`
- `g8_v0396_promotion_run_state_durability_review_20260825/review.md`

## 禁止範圍

- 禁止修改產品 source、tests、production、launchctl、模型、真實 queue/state、publish/tag/push。
- 禁止新增 finding 範圍、架構重構、第二個 Reviewer 或第二張 Repair。

## RESULT

狀態：REVIEW_GO（cycle 2 targeted re-review）

- Verdict：`REVIEW_GO`
- Previous candidate：`178f4504c9e4add4ecb5f35cfff9f92bd115383b`
- Targeted repair candidate：`8b3eb337fbe2a20a8f08c6772250392ba617f503`
- Resolved finding：Cycle 1 P1，`failed_external_job_replacement` 的 active-run integrity 豁免已限縮到 `exact_run_ids` 明確指定同一 run；`exact_run_ids` 與 automatic sweeps 互斥，因此 dangling failed replacement registry 在 `new_matrix_sweep` / `legacy_sweep` path 會 fail closed，不會 seed 新 identity。
- Evidence：`artifacts/fortune_council/four_lane_runtime_execution/g8_v0396_promotion_run_state_durability_review_20260825/review.md`
- Verification：CodeGraph ready；已做 `178f4504...8b3eb337` targeted diff/stat/name-only、targeted `git diff --check`、candidate object check。採用 implementation evidence：focused 3 passed、affected coordinator+promotion 323 passed、`git diff --check` PASS、worktree clean。
- Residual risk：未執行 production promotion 或新 canary；本輪只複審上一輪 P1。
