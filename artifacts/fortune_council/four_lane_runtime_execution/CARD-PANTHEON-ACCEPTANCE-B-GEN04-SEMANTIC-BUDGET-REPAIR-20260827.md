---
id: CARD-PANTHEON-ACCEPTANCE-B-GEN04-SEMANTIC-BUDGET-REPAIR-20260827
status: ready
chain_id: PANTHEON-ACCEPTANCE-B-GEN04-SEMANTIC-BUDGET-REPAIR-20260827
role: repair
cycle: 1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: lifecycle/state 與 semantic budget contract 已由前一輪 RCA 固定，影響 continuation generation authority 與唯一 B generation；目前沒有未解架構 fork，採 strict bounded code repair。
execution_mode: bounded_code_repair
production_mutation: forbidden
remote_mutation: forbidden
---

# Pantheon Acceptance B：gen04 semantic budget bounded Repair

工作名稱：Pantheon Acceptance B：gen04 semantic budget bounded Repair

任務目的：在前一 candidate G2 的既有 continuation lifecycle／semantic budget seam，修復由新 RCA candidate 證明的獨立 budget-accounting `RESUME_CONTRACT_GAP`：gen04 partial allocation 被 terminalize／consume 後，`next_generation` 從 4 推進到 5，卻因 abandoned allocation 錯誤消耗 `semantic_budget=1` 而使正式入口得到 `final_generation=4`、進入 `range(5,5)` 空迴圈並拋出 `continuation semantic budget produced no result`。必須讓 abandoned allocation 不消耗 semantic budget，讓下一個正式 continuation entry 精確 targeting gen05 一次，並保留 gen04 audit；不得猜 mapping 或在同一 terminalization action 建立 gen05。

本卡供原 Repair task `01a041ff-0fa2-7bf1-bca1-69eb447581f0` 續作；禁止新建第二個 Repair thread。這不是把舊 finding 改名或重置 cycle；新 RCA candidate `d54e3e64014aaa0411a30608182268fab439412e` 已證明這是獨立 semantic-budget root question。舊 `PANTHEON-ACCEPTANCE-B-GEN04-LIFECYCLE-20260827` chain 保持 stopped；本新 chain 只允許一代 bounded Repair，完成後回原 B Reviewer task。固定 authority：上一 candidate G2 `7f4a18cd024589fdd4100da9888dc79494207164`；RCA RESULT `CARD-PANTHEON-ACCEPTANCE-B-GEN04-SEMANTIC-BUDGET-RCA-20260827-RETRY-1-RESULT.md`；regression id `REG-GEN04-SEMANTIC-BUDGET-1-EMPTY-LOOP`。唯一 primary：`RESUME_CONTRACT_GAP`。

## 執行順序與硬門檻

1. 以 candidate G2 為 implementation source，先用兩個獨立 fresh temporary snapshots 建立 exact fixture，實際連跑 RED；RED 必須在任何 implementation change 前成立。
2. RED 必須重現：terminalize／consume 後 `next_generation=4→5`，接著正式入口得到 `final_generation=4`、進入 `range(5,5)` 空迴圈並拋出 `continuation semantic budget produced no result`；若只得到 import、fixture、環境或無關 assertion failure，不能進入實作。
3. RED 證據完整後，才可在既有 continuation lifecycle／semantic budget seam 做最小修復；不得重做 publisher、promotion、replacement 或 provider flow。
4. 實作後以同一 exact fixture 雙跑 GREEN／regression，並驗證 crash/replay/idempotency、failure/transition receipt 去重與正常 complete generation 不退化。
5. 只交付一個 candidate commit；完成後回原 B Reviewer task `01a03c34-fd96-7021-9423-29879c9b5b47` re-review 原 finding 與 `REG-GEN04-SEMANTIC-BUDGET-1-EMPTY-LOOP`。不得自行整合、執行 B、promotion、publish 或 production acceptance。

## 可改範圍與唯一輸出

只允許修改：

- `scripts/agy_multilingual_pipeline.py`：既有 continuation lifecycle／semantic budget seam，限 G2 已有實作及其必要的同檔 helper／contract wiring。
- `tests/test_agy_multilingual_pipeline.py`：exact fixture 的雙跑 RED/GREEN、terminalization transition、idempotency、provider=0 與正常 complete-generation regression。
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-ACCEPTANCE-B-GEN04-SEMANTIC-BUDGET-REPAIR-20260827-RESULT.md`。
- `artifacts/fortune_council/four_lane_runtime_execution/gen04_semantic_budget_repair_20260827/` 專屬 evidence 目錄。
- task-owned `/private/tmp/pantheon-acceptance-b-gen04-semantic-budget-repair-*` 暫存證據。

candidate commit 只可含上述兩個 source/test 檔與本卡 RESULT/evidence；不得帶入其他修改。

## Exact RED fixture（僅 temporary fixture，不是 production 實跑）

使用兩個互相獨立、可重建的 fresh temporary snapshots；不得讀寫或模擬 production state。每個 fixture 固定：

```text
started_after_generation = 3
semantic_budget = 1
next_generation = 4
completed_generations = []
abandoned_generations = []
```

gen04 partial artifacts 僅在 temporary fixture 內建立：有 `external-plan.json`、`plan-operation.json`，缺 `source-ref-map.json`、`locale-plan.json`、`planning-result.json`、`article-operation.json`、`review-operation.json`。使用 deterministic intercept／fail-if-called doubles；不呼叫 network、provider、Writer、article 或 Reviewer。

改碼前雙跑必須逐次證明：

- terminalization／transition phase provider/article/reviewer calls = 0；
- terminalization／transition phase new generation = 0；
- success receipt = 0；
- source、gen04 original audit、queue、current-generation 與 non-authority bytes before == after；
- canonical `continuation/state.json` 與 authority-transition receipt 必須逐拍 hash，且只允許既定 `next_generation=4→5` transition；第二次 replay 不得再改變它；
- terminalize／consume 的明確 transition 為 `next_generation=4→5`，但現行 G2 的下一正式入口得到 `final_generation=4`、進入 `range(5,5)` 空迴圈並拋出 `continuation semantic budget produced no result`；
- failure／transition receipt 在 replay 或第二跑不重複累加、不改變裁決；
- 兩個 fresh snapshots 的 call counts、generation counts、receipt counts、transition hashes 與 empty-loop symptom 一致。

RED 必須固定捕捉「abandoned allocation 與 semantic attempt 被混算」的目標症狀，不得只以錯誤文案宣稱 RED。禁止 production、gen04、gen05 實跑；gen04/gen05 僅可作為 isolated temporary fixture 的資料形狀與 deterministic target assertion。

## 最小實作契約

實作必須以 G2 為基準，在既有 seam 內建立以下 durable semantics：

1. `allocated` 只表示 generation identity／partial directory／plan residue 已配置；abandoned allocation 不消耗 `semantic_budget`。
2. `terminalize`／`abandon` 是明確、可觀測、idempotent 的 lifecycle action：保留 gen04 原始 external plan、plan operation 與 audit receipt，將其標為 abandoned/terminal，不在同一 action 建立 gen05，不猜或補 `source-ref-map`。
3. terminalization 可合法推進 continuation `next_generation=4→5`，但不把該 transition 計為 semantic planning attempt；受保護 source、queue/current-generation authority 與既有 continuation ownership 不得被手改或非授權重寫。
4. 下一個正式 continuation entry 必須在 terminal state 後 targeting gen05 exactly once；不得 target gen04、跳到 gen06、同 action 建 gen05，或因 replay 重複建立／重複 transition。
5. 只有 provider-facing semantic planning attempt 或 committed semantic generation 才可消耗 budget；partial allocation、terminalization、abandon、replay、failure receipt 與 transition receipt 不得消耗 budget。
6. crash/replay 及相同 operation identity 重跑產生相同 terminal decision；failure/transition receipt append-only 且第二次不重複累加，audit artifact 保留。
7. 正常 complete generation 的 planning、budget accounting、provider/article/reviewer side effects 與既有 cross-version fail-closed guard 不退化。

不得新增第二套 registry、FSM、database、canonical writer、常駐 recovery service 或 promotion/replacement seam；不得猜 mapping。若需新增最小字段／receipt，必須在 RESULT 明確說明 authoritative owner 與 why_not_less、why_not_more、do_not_absorb。

## 驗證與證據契約

至少記錄：

- 改碼前兩個 fresh snapshots 的 RED command、exit status、完整 symptom 與逐拍 transition hash；
- 實作後相同 snapshots 的雙跑 GREEN，terminalization/transition phase provider/article/reviewer=0、new generation=0、success receipt=0；source/gen04 original audit/queue/current-generation/non-authority bytes stable，canonical `continuation/state.json` 與 authority-transition receipt 僅出現既定 `4→5` transition 且第二次 replay 不再改變；
- 下一正式 continuation entry 的 deterministic intercept／fail-if-called evidence：target generation=5 exactly once，且在 provider 前可觀測；不得 network/provider；
- crash/replay/idempotency 與 failure/transition receipt 去重；
- 正常 complete generation regression；
- 受影響測試、必要 full-file tests、`git diff --check`；
- exact artifact inventory、before/after hashes、call counts、generation／receipt counts、candidate diff 與 commit SHA。

RESULT 必須標記 `DELIVERED_CANDIDATE`，包含 G2/RCA authority、唯一 primary、RED→implementation→GREEN 證據、`REG-GEN04-SEMANTIC-BUDGET-1-EMPTY-LOOP` 結果、why_not_less、why_not_more、do_not_absorb、未執行 production/network/provider/push/tag/deploy/promotion/replacement 動作，以及回原 B Reviewer re-review 指令。不得標記 `ACCEPTED`、`INTEGRATED`、`PRODUCTION_GO` 或宣稱 Acceptance B 完成。

## 禁止事項與停損

- 禁止 production、gen04/gen05 真實執行、network、provider、Writer、Reviewer、publisher、promotion、replacement、push、tag、deploy 或任何 remote mutation。
- 禁止修改 queue、registry、current-generation authority、production data/state、shared metadata、publication artifacts 或本卡 allowlist 外檔案。
- 禁止建立第二個 Repair/Reviewer/replacement task，禁止自行整合或執行 B。
- 若必須修改 queue/current-generation/publisher、無法以 exact fixture 閉合、無法保持 provider=0、transition target 不唯一、bytes 被非授權改寫、或同一 blocker 第三次失敗，停止並輸出 `BLOCKED`，保留 evidence，不擴大 scope。
