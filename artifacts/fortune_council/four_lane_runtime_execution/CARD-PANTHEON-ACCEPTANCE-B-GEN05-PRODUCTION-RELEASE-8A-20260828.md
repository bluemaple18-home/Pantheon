---
schema_version: 1
title: Pantheon Acceptance B gen05 production release 8a
date: 2026-08-28
owner: codex-production-release-worker
status: NO_GO_SECOND_RELATED_RUNTIME_LIFECYCLE_FAILURE
target_commit: 8a50395f67
target_run: auto-i18n-ja-1414b75a404721e95e74
evidence_dir: artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_production_release_8a_20260828
---

# 目標

將本地已 review GO 的 `8a50395f67` 透過正式入口推到 production actor，並只推進
`auto-i18n-ja-1414b75a404721e95e74` 的 gen05 exact-run，直到 Writer → Reviewer →
publish → public URL HTTP 200 且日文正文可見。

# 範圍

- 允許：本次必要的 `git push origin main`、runtime promotion、exact-run、publication
  transaction、tag、content push、browser acceptance。
- 寫入：只新增本卡與
  `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_production_release_8a_20260828/`
  內證據；publication workflow 正式內容輸出依正式入口執行。

# 禁止

- 不 force push、不移動既有 tag、不開新 Repair。
- 不手改 registry、brief、queue、state、continuation。
- 不重跑 planning provider、不建立 gen06、不使用 `resume`。
- 不清理 unrelated untracked files。

# Gate

- Rule24 fresh capacity guard 必須 PASS。
- Rule25 production canary readiness 必須 READY，且 `canary_created=false`。
- current production authority 必須精確為 actor `2ce431ec41f5187531d88b52dfa91cef0373d8b5`、
  manifest digest `7dbedf4e8544675f6203c2d40f96afa561d961a2c7e5a445c8d1f821f0d369f9`、
  stage digest `51d0e46da1c495ecf1d717011199444e485754498887823bce1fb17abbac0e29`。
- 任一 gate 缺證或不 current 即 `NO-GO`，不得 push、promotion 或 canary。

# 驗收

- pushed/promoted/executed/published/accepted 分段回報。
- 每個 mutation 後保存 capacity、state、queue、service、rollback evidence。
- 最終公開 URL 必須 HTTP 200，且 browser 驗收在 `page.goto()` 前掛
  console/pageerror/requestfailed listener，驗 canonical、hreflang 與日文正文。
