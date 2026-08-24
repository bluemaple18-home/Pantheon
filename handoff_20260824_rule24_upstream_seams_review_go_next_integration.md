# Pantheon Rule24 upstream seams 換手

## Goal

把已獨立驗收為 `REVIEW_GO` 的 Rule24 capacity evaluator seam 與 DSSE commit-time re-authentication seam，安全整合回 `main`。整合驗證通過後，才進入 signed evidence composition。

## Root Question

如何只整合兩條已驗收 upstream seam，不把舊 signed evidence composition 歷史或禁止 commit 一併帶回主線？

## Blocker

目前無技術 blocker。尚未鎖定最小整合 commit 集合；兩條保留分支的 ancestry 都含舊 composition／dispatch／review 歷史，因此禁止整條 merge。

## Candidate Fork

- 首選：在新 integration branch 依賴檢查後，逐筆 cherry-pick 最小 source commits，再選擇性帶入最終 review evidence。
- fallback：若 source commits 對舊 composition parent 有 patch dependency，從已驗收 tip 擷取限域 patch，重建等價 integration commit，並重跑完整受影響測試。
- 尚未判定；第一拍只讀盤點後再寫 integration 卡。

## Constraints & Preferences

- 節省模式；只開一張最小 integration 卡，不平行展開。
- 不得整條 merge `codex/g8-v0373-evaluator-seam-repair-001` 或 `codex/g8-v0374-dsse-seam-review`。
- 不得整合 `0af881df` 或 `6de8e487`。
- 不得順帶整合舊 signed evidence composition commits；已知 ancestry 含 `5ca75022ba`、`d90137815d`、`d1e1be51aa`。
- composition 尚未開始；upstream integration 驗證通過前不得開 composition implementation。
- 不得 push，除非使用者另行明確授權。
- 保留主工作區既有未追蹤檔；不要 add、移動、刪除或改寫。
- 文件、自然語言、註解與 docstring 使用繁中；程式碼維持原語言。

## Completed Actions

### V0373 capacity evaluator seam

- accepted branch：`codex/g8-v0373-evaluator-seam-repair-001`
- accepted tip：`c1b38ec30ccd4916ca6f64bd9376d488489d1b00`
- source candidate：`4185b1c961`（Expose Rule24 capacity evidence bundle）
- repair：`a7ca0c2d65`（capacity evidence bundle immutability）
- final verdict：`REVIEW_GO`
- final review result：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0373-RULE24-EVALUATOR-ARTIFACT-BUNDLE-SEAM-REVIEW-001-GENERATION-2-20260824-RESULT.md`
- final review evidence：`artifacts/fortune_council/four_lane_runtime_execution/g8_v0373_rule24_evaluator_artifact_bundle_seam_review_001_generation_2_20260824/verification-receipt.json`
- final verification：13 tests PASS；兩個 P1 已關閉。

### V0374 DSSE seam

- accepted branch：`codex/g8-v0374-dsse-seam-review`
- accepted tip：`464592cbcd523321d6100f4935f73beb47cff79b`
- source candidate：`377d0da63f`
- Repair-1：`947f781d8e`
- Repair-2：`1621d49785cada2fd0a3e3ef4b78cf9209020cce`
- final review commit：`464592cbcd523321d6100f4935f73beb47cff79b`
- final verdict：`REVIEW_GO`
- final review result：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0374-RULE24-DSSE-COMMIT-REAUTH-FINAL-REVIEW-003-20260824-RESULT.md`
- final review evidence：`artifacts/fortune_council/four_lane_runtime_execution/g8_v0374_rule24_dsse_commit_reauth_final_review_003_20260824/probe_evidence.json`
- final verification：63 affected tests PASS；31 focused tests PASS；`git diff --check` PASS。
- accepted API principle：任何會消耗 replay state 或釋放 observer payload的操作，都必須從 original DSSE envelope 與 verifier-owned trust context 重新 authentication，不得信任先前 Python object。

### Branch preservation

- `codex/g8-v0373-evaluator-seam-repair-001` 已固定在 `c1b38ec30c...`。
- `codex/g8-v0374-dsse-seam-repair-002` 已固定在 `1621d49785...`。
- `codex/g8-v0374-dsse-seam-review` 已固定在 `464592cbcd...`，避免 detached review evidence 遺失。
- 全部尚未 push。

## Active State

- repo：`<repo-root>`
- main 在建立本換手 artifact 前：`4762df7cfd4fdfda6fd19e7f8dc730dbc4a5a893`
- 主工作區沒有 tracked modification；有使用者既有未追蹤 artifacts 與舊 handoff，未碰。
- Reviewer worktree（local-only，不可跨機照抄）仍 detached 在 `464592cbcd...`。
- Repair-2 worktree（local-only，不可跨機照抄）仍 detached 在 `1621d49785...`。
- 無 server、無 deploy、無 push 在等待。

## In Progress / Remaining Work

1. 第一拍只讀盤點 `main`、兩個 accepted tips 與各 source commit 的 patch dependency。
2. 建立一張 upstream integration 實體卡，明列唯一 commit allowlist、禁止 ancestry、可改檔案與驗證。
3. 建立獨立 integration branch；禁止 merge whole branch。
4. 整合 V0373 最小 source changes，跑 evaluator 受影響 tests。
5. 整合 V0374 最小 source changes，跑 DSSE 受影響 tests。
6. 跑兩者共同 integration tests、完整相關 test files 與 `git diff --check`。
7. 確認 diff 不含舊 composition、`0af881df`、`6de8e487` 或無關 artifacts。
8. 獨立 review integration candidate；只有 `REVIEW_GO` 才能進 signed evidence composition 卡。

## Waiting Conditions

- integration candidate 必須 clean、受影響 tests 全綠、`git diff --check` PASS。
- integration review 必須 `REVIEW_GO`。
- 上述兩條同時成立前，不得開 composition implementation。

## Blocked & Errors

- 無現行 blocker。
- 歷史 NO-GO：V0374 Repair-1 仍讓 caller 重建 module-private authority；Repair-2 改為 commit-time re-authentication 後已由 final Reviewer 關閉。
- CodeGraph 在 Reviewer worktree 曾短暫顯示舊 signature；最終判定以 candidate source、bounded adversarial probe 與測試證據為準。

## Key Decisions & Resolved Questions

- 三個 upstream P1 均成立，必須修 seam；不是重寫 crypto。
- 最小安全鏈固定為：authenticate → domain validate → GO → commit re-authenticate original envelope → derive replay identity → atomic claim → observer release。
- prior `AuthenticatedRule24Attestation` 可作 pure-auth value，但不能再授權 replay consumption 或 observer release。
- 兩條 upstream seam 已完成且獨立 `REVIEW_GO`；下一步是整合，不是繼續 Repair。
- composition 必須建立在已整合、已驗收的 upstream main 上。

## Limits

- 不自動 push。
- 不自動 deploy／canary／production。
- 不清理使用者未追蹤檔。
- 不開 Repair-3。
- 不直接沿用舊 composition implementation。

## 新對話第一句

`讀 handoff_20260824_rule24_upstream_seams_review_go_next_integration.md，第一拍只讀盤點 main 與 V0373/V0374 accepted commits，然後開最小 upstream integration 卡；禁止整條 merge 分支、禁止帶入舊 signed composition commits，也不要整合 0af881df 或 6de8e487。`
