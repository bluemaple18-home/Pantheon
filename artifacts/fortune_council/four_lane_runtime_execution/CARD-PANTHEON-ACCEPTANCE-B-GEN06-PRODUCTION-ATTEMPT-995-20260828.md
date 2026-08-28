---
schema_version: 1
title: Pantheon Acceptance B gen06 production attempt 995
date: 2026-08-28
owner: codex-production-release-worker
status: NO_GO_NO_FORMAL_GEN06_SEAM
mode: PRODUCTION_ATTEMPT
source_commit_prefix: 99507c67e2
source_commit: 99507c67e27d9e6f3af4e33c3ab0727682ed82bd
expected_previous_actor: ac1faef520c9b79f9bb70265735d07a6ca826b7d
target_run: auto-i18n-ja-1414b75a404721e95e74
target_article: V2-TAROT-DEATH-MONEY:ja
target_generation: 6
evidence_dir: artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_production_attempt_995_20260828
---

# 目標

執行一次受控 gen06 production attempt，目標最終 LIVE。

# 授權

Owner 既有上線授權持續；`main` / `origin/main` 已 push
`99507c67e27d9e6f3af4e33c3ab0727682ed82bd`。本卡授權僅限本 mission 的
必要 production promotion、exact gen06 continuation、publish 與 acceptance。

# 必要前置

- `HEAD` / `origin/main` 必須 exact 等於 `99507c67e27d9e6f3af4e33c3ab0727682ed82bd`。
- production actor 必須為 `ac1faef520c9b79f9bb70265735d07a6ca826b7d` 且
  promotion transaction committed。
- services 必須 stopped。
- target run 必須為 gen05 complete/rejected、`next_generation=6`、gen06 absent、
  no publish。
- Fresh Rule24 必須 PASS。
- Fresh Rule25 必須 READY。

# 執行邊界

- 只能用正式 runtime promotion 入口將 actor 升至 995。
- promotion 後必須 post-apply capacity PASS 才 finalize。
- 服務保持 stopped。
- 只能沿既有 continuation / authority transition 正式 seam 建立恰一個 gen06。
- gen06 必須沿用已驗證 gen05 locale plan/source refs 與新 prompt；不得重跑
  planning，除非正式 seam contract 本身要求且 evidence 已證明。
- formal exact operator 一次一 tick 推 Writer → Reviewer。
- Reviewer ACCEPT 且 deterministic findings empty 才可 publish。

# 禁止

- 手改 state / candidate / queue / registry。
- 第二次 gen06 或重試。
- unrelated sweep。
- stale plist `ProgramArguments`。
- 新 Repair。

# 完成條件

- actor/source identity = 995。
- gen06 Writer → Reviewer 成功，Reviewer ACCEPT，deterministic findings empty。
- publication transaction/tag/content push receipts 存在。
- public URL HTTP 200，日文正文可見。
- browser acceptance 在 `goto` 前掛 console / pageerror / requestfailed hooks。
