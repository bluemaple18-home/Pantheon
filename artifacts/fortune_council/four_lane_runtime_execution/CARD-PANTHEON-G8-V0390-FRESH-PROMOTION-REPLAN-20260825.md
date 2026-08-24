---
id: CARD-PANTHEON-G8-V0390-FRESH-PROMOTION-REPLAN-20260825
status: ready
execution_mode: read_only_replan
production_mutation: forbidden
remote_mutation: forbidden
---

# PANTHEON G8 V0390 fresh promotion replan

## Root question / blocker / fork

- Root question：main `5748d2d1e1` 已有 fresh Rule24 unsigned＋DSSE verified evidence後，是否能形成一份新的、可由人明確核准的 promotion apply plan？
- Current blocker：尚未以 fresh current facts重驗 target、source/actor/manifest/current-stage/queue/state no-drift，尚未移除「target readiness必須在apply前存在」的錯誤 gate，也沒有新的 plan/argv/authorization digests。
- Candidate fork：若 remote target、current stage或protected facts已漂移，輸出 `BLOCKED` repair evidence；不得硬做 ready plan。

## 工作名稱 → 正在做什麼 → 現在狀態

V0390 fresh promotion replan → 唯讀重抓 current facts、修正 readiness phase contract、重算 exact argv與authorization payload → ready；禁止 apply與任何 mutation。

## 依賴與證據邊界

- Baseline：main `5748d2d1e1`。
- Accepted target分析基線：`5872284828f9dd6f0a75adf407becaeadb50d61a`；必須由 fresh read-only remote/local source重新確認，不得直接沿用。
- Fresh capacity：V0388 integration `033f9aaa0a`。
- Fresh DSSE/domain/replay：V0389 integration `5748d2d1e1`。
- V0383 plan/argv/authorization、V0385 findings只能作歷史比較；禁止重用其digest或宣稱舊授權仍有效。
- V0389 ephemeral producer只證明local evidence integrity；不得宣稱production trust或authorization。

## 執行契約

1. 先查 CodeGraph；失敗才限域 `rg`。完整讀 V0384–V0389 accepted results與 promotion source/tests。
2. 所有Git remote、production path、process、LaunchAgent與machine facts只讀。允許 read-only remote query；禁止fetch/pull/push/tag與任何remote write。
3. fresh驗證：remote target identity、main source commit、actor/manifest/current private stage digest、queue/state/transaction idle/no-drift、current machine/capacity locator與V0388/V0389 exact digests。
4. Readiness phase契約必須依source順序：apply前不要求 target-generation readiness存在；`STAGE_INSTALLED` 由正式 `_install_private_stage` 產生 readiness/barrier；postcheck才讀取驗證。不得手造或預寫任何 production artifact。
5. 以正式 plan入口重算；若repo沒有足夠薄CLI，僅可用既有純函式/測試證明並輸出 `BLOCKED`，不得猜argv或改source。
6. 新 exact apply argv必須鎖 target、expected plan digest、fresh capacity receipt path/digest、correlation、machine/source/manifest/current-stage bindings與rollback packet。任何 placeholder存在即不可授權。
7. 新 authorization payload必須列 exact argv digest、plan digest、target/manifest/capacity/DSSE digests、allowlist、forbidden、terminal stops、人工核准欄位；本卡狀態固定 `not_authorized`。
8. protected tripwire/no-drift evidence必須區分本卡唯讀觀測與未執行的apply；不得用空changed set假裝production snapshot。

## 唯一可寫範圍

- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0390-FRESH-PROMOTION-REPLAN-20260825-RESULT.md`
- `artifacts/fortune_council/four_lane_runtime_execution/g8_v0390_fresh_promotion_replan_20260825/`
- task-owned `/private/tmp/pantheon-v0390-*` 暫存。

## 禁止範圍

- 禁止promotion apply/postcheck、production actor/manifest/stage/readiness/barrier/queue/state/transaction寫入、LaunchAgents、deploy/canary/activation。
- 禁止生成/使用private signing key、重簽V0389、重跑V0388、修改既有evidence。
- 禁止source/tests/workflow/shared metadata變更、remote mutation、push/tag、整條merge、派下一卡。

## 驗收與 verdict

- target/current facts fresh且所有 no-drift gates PASS；否則 `BLOCKED`。
- readiness phase finding以source lines與tests證明，且 plan不再把 apply output當preflight input。
- V0388/V0389 accepted bytes與digests重驗 PASS。
- plan、exact argv、authorization payload、rollback packet、protected tripwire全部machine-readable、無placeholder、可重算。
- canonical digest與再次重算一致；JSON parse、受影響promotion/capacity/DSSE tests、`git diff --check` PASS。
- production/remote mutation count皆 `0`；單一commit、clean、不push。
- Verdict只能 `READY_FOR_EXPLICIT_AUTHORIZATION` 或 `BLOCKED`。
- 即使 READY，本卡也不得執行apply；必須回主線顯示完整exact payload，另取得使用者明確授權。
