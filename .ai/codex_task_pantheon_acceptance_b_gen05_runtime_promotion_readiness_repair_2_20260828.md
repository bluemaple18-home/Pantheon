---
id: REPAIR-PANTHEON-ACCEPTANCE-B-GEN05-RUNTIME-PROMOTION-READINESS-20260828-2
title: 修復第五代執行環境升版就緒證據 Repair-2
status: ready
chain_id: PANTHEON-ACCEPTANCE-B-GEN05-RUNTIME-PROMOTION
role: repair
cycle: 1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
supersedes: .ai/codex_task_pantheon_acceptance_b_gen05_runtime_promotion_readiness_repair_1_20260828.md
parent_candidate: 2b9343bc5011f82e5a9d2a81cf1d03a61d80c97d
review_commit: 125b1e87c2e32ec683b5636523dbcffc642ccafc
owner_authorization: Owner 明確同意把同一 bounded Repair 擴到正式 planner 的最小 code seam
---

# Pantheon Acceptance B：gen05 runtime promotion readiness Repair-2

## 目標

修正 `scripts/pantheon_content_runtime_promotion.py` 的 plan authority，使相同 source commit、manifest/stage 與 capacity receipt bytes 從不同乾淨 worktree 重跑時產生相同 authoritative plan digest。本機絕對 checkout／receipt path 只作 runtime locator，不得成為跨 worktree authority。

不得削弱 source SHA、manifest、stage、capacity bytes/digest 或 apply-time revalidation。

## 可改檔案

- `.ai/codex_task_pantheon_acceptance_b_gen05_runtime_promotion_readiness_repair_2_20260828.md`
- `scripts/pantheon_content_runtime_promotion.py`
- `tests/test_pantheon_content_runtime_promotion.py`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_runtime_promotion_readiness_20260827/**`
- `artifacts/fortune_council/four_lane_runtime_execution/RESULT-PANTHEON-ACCEPTANCE-B-GEN05-RUNTIME-PROMOTION-READINESS-20260827.md`
- `artifacts/fortune_council/four_lane_runtime_execution/RESULT-PANTHEON-ACCEPTANCE-B-GEN05-RUNTIME-PROMOTION-READINESS-REPAIR-2-20260828.md`

## 禁止範圍

- 不得修改其他 code、config 或 tests。
- 不得執行 promotion apply/finalize、production/provider/gen05/publish/transaction/tag/push/deploy/service mutation。
- 不得另建 planner、registry 或 FSM。
- 不得只改 artifact digest 硬湊。

## 實作前驗證

- 執行 task-semantic CodeGraph query，確認 plan→digest→apply/postcheck 的 callers 與欄位；若 CodeGraph 未初始化，記錄失敗並退到限域搜尋。
- 以原候選 exact argv 的路徑依賴建立 RED，證明舊 evidence 不能在此獨立 worktree 重現。

## 必要驗收

1. 相同 source/capacity authoritative bytes 位於兩個不同絕對 checkout/path 時，plan digest 及 authoritative plan payload 一致。
2. source SHA、manifest/stage authority 或 capacity bytes 改變時 digest 仍改變；missing/noncanonical runtime locator 仍 fail closed。
3. apply/postcheck 不得因 locator 未納入 authority而接受錯誤 checkout；必須以 stable identities／bytes 重新驗證。
4. 修復後重建 `P1-001`、`P1-002`、`P1-003` readiness evidence；`evidence-index` 必須 `missing=0`、`digest_mismatch=0`、無 `.git/` path。
5. 受影響 tests、原 Reviewer 列出的 4 個測試檔、JSON/schema/checksum、`git diff --check` 全綠；`production_mutation=0`。

## 交付

- 先提交本 revised card。
- 再做 RED→GREEN，建立 Repair-2 candidate commit；不 amend、不 push。
- 回傳 full SHA、parent、changed files、finding-to-regression mapping、tests 與 residual risk。
