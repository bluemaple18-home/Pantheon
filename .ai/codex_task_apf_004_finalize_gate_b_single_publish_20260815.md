---
id: APF-004-FINALIZE-GATE-B-SINGLE-PUBLISH
title: 完成 Gate A finalize 與單篇 production canary
status: authorized
chain_id: PANTHEON-WRITER-VNEXT-AUTO-PUBLISHING-FIRST
role: implementation
cycle: 1
thickness: strict
risk: critical
parent_candidate: 8695532bbac32b30ce134d5b6978a031675f3c94
---

# APF-004｜Gate A finalize → Gate B 單篇 production canary

## 使用者授權

- 使用者於 2026-08-15 明確核准繼續完成收尾流程。
- 授權包含：Gate A finalize、Gate B 四 lane readiness／capability 驗證、恰好一篇 `new` lane 真實 production canary publication。
- 授權不包含：另外三篇 publication、批次發文、常駐排程、APF-005、手動 rollback、改 production code 繞過 gate。

## 目標／邊界／驗收

- 目標：先關閉已 `POSTCHECK_PASSED` 的 Gate A transaction，再以 Existing Publisher 完成一篇可追溯的 `new` lane production canary。
- 可寫：既有 finalize transaction；單篇 publication／ledger transaction／release record／tag／atomic push；本卡 evidence root。
- 禁止：apply retry、第二次 finalize、另外三 lane publish、`max-runs > 1`、scheduler／LaunchAgent、批次、刪 queue/evidence、人工改 actor/manifest/stage。
- 驗收：finalize success；create→run→select→publish→transaction→tag→push 全鏈路；remote SHA/tag、publication receipt、release record、容量與 duplicate suppression PASS。
- 停損：任一步不一致立即停止；不得 retry production mutation，不得自動擴量。

## 固定基線

- Repository authority：`origin/main=8695532bbac32b30ce134d5b6978a031675f3c94`。
- Gate A apply evidence：`artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/gate_a_deterministic_plan_apply_after_capacity_pass_20260815/`。
- Apply state：`apply_calls=1`、`POSTCHECK_PASSED`、target actor `28b8b84b6dfa319d8151aac3bc1a6a819ae82aa1`。
- Plan digest：`46e720652f39441413afc9dac6805465227800cfcf2240e612f76088167e8b8b`。
- Fresh capacity evidence：`artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/gate_a_capacity_preflight_after_top_level_identity_repair_20260815/`。
- Final evidence root：`artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/gate_a_finalize_gate_b_single_publish_20260815/`，執行前必須不存在。

## Slice A｜Gate A finalize

1. clean detached checkout exact `origin/main`；驗證 apply evidence JSON/digests與 live transaction均一致。
2. 從 apply exact argv／transaction receipt 派生 public `finalize` argv；不得改 source SHA、plan digest、generation、correlation、transaction root、capacity receipt或 runtime paths。
3. 保存 before snapshot與 canonical finalize argv digest。
4. public finalize 恰好一次；失敗停止，不 retry、不人工 rollback。
5. 驗證 transaction closed/finalized、actor/manifest/stage仍為 target、queue/state business writes=0；保存 evidence candidate。
6. Reviewer APPROVED 後才進 Slice B。

## Slice B｜Gate B readiness 與單篇 canary

1. 重驗 production capability receipt：create→run→select→publish→transaction→tag→push 的正式入口、I/O、identity/correlation、正向與 fail-closed 負向證據齊全。
2. 重跑 capacity preflight；必須 PASS。確認 credentials active，不輸出 secret。
3. 四 lane `new`、`rewrite`、`i18n-new`、`i18n-rewrite` 只做 exact identity/readiness lock；不得替後三 lane 建立 publication mutation。
4. 唯一 production payload：`new` lane、exact selector、`--max-runs 1`。若無唯一 run，使用既有正式 create→run 入口建立一筆；禁止掃描其他 run。
5. 依序執行 select→Existing Publisher transaction→tag→atomic push；任何一步失敗停止，不 retry。
6. 核對 remote main SHA、唯一 tag、release record、publication artifact、ledger、duplicate suppression、站點可見性與容量 after。
7. `rewrite`、`i18n-new`、`i18n-rewrite` publication count 必須為 `0`；schedule/batch count 必須為 `0`。

## 角色／交付

- Executor：沿用既有正式 Executor thread；可產 candidate commit，不 push。
- Reviewer：沿用既有正式 Reviewer thread；唯讀審查，不修碼。
- 主線：只整合 Reviewer APPROVED candidate，跑 JSON/digest/sanitizer/受影響 gates，推 `origin/main`。
- 交付狀態：`FINALIZE_PASS`、`SINGLE_CANARY_PASS`、`STOPPED_NO_RETRY` 或 `BLOCKED_BEFORE_MUTATION`。

