---
schema_version: 1
title: Pantheon Acceptance B gen05 production release ac1 recovery
date: 2026-08-28
owner: codex-production-release-worker
status: NO_GO_REVIEWER_REJECTED
mode: PRODUCTION_RELEASE_RECOVERY
source_commit_prefix: ac1faef520
source_commit: ac1faef520c9b79f9bb70265735d07a6ca826b7d
target_run: auto-i18n-ja-1414b75a404721e95e74
source_job_id: 61a83c341d39c882d5eed8ea23b7f805a89085e3
expected_current_actor_prefix: 23e
evidence_dir: artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_production_release_ac1_recovery_20260828
---

# 目標

正式上線 `ac1faef520`，並以 bounded seam 恢復 gen05 target run 的
`provider-attempt=0 INVALID_RECEIPT` residue，推進 Writer → Reviewer →
publish → public URL acceptance。

# 授權

Owner 已明示授權本 mission 的 push / promotion / deploy / production /
publish；`origin/main` 已由主線推至 `ac1faef520`。本卡不得擴成其他
production 工作。

# 必要前置

- `HEAD` / `origin/main` 必須 exact 等於 `ac1faef520...` full SHA。
- production current actor 必須仍為 `23e...`，服務停止。
- Fresh Rule24：capacity two-cycle、增長、監控、停損 evidence 必須 PASS。
- Fresh Rule25：capability receipt 必須證明 create→run→select→publish→
  transaction→tag→push，且 `canary_created=false`、gate READY。
- Live residue 必須仍精準符合 bounded seam：
  - run `auto-i18n-ja-1414b75a404721e95e74`
  - source job `61a83c341d39c882d5eed8ea23b7f805a89085e3`
  - archived request valid
  - failed receipt `ValueError` / `INVALID_RECEIPT`
  - no `error_code`
  - no `credential_pool`
  - no production attempt marker
  - state active / last_job_id same / correlation null
  - no gen06 / no existing publish

# 執行邊界

- 可做本 mission 必要 production promotion / exact recovery / publish。
- 必須使用正式 runtime promotion 入口。
- 必須使用新正式 `operator-exact-process-once`，不得直接 kickstart stale
  plist `ProgramArguments`。
- Recovery 必須先 `replace-failed-external-job --plan-only`，再 execute。
- Exact operator 一次一 tick，每步先讀 durable state。
- 禁止手改 queue/state/registry。
- 禁止 gen06 / unrelated sweep / planning provider rerun。
- 任一新 related failure，立即停止 production mutation，不新增 Repair。

# 完成條件

- actor/source identity = `ac1faef520...`
- promotion transaction committed、rollback not required。
- replacement receipt created and bounded。
- target gen05 Writer → Reviewer → publish 完整。
- publication transaction/tag/content push receipt 存在。
- public URL HTTP 200 且日文正文可見；browser acceptance 有 console /
  pageerror / requestfailed hooks。
