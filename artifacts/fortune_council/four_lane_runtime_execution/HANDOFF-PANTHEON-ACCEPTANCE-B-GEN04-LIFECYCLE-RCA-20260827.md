# Pantheon Acceptance B：generation 04 生命週期根因與續接換手卡

## 新對話啟動指令

請接手 Pantheon Automation Acceptance B 主線監工。

先完整閱讀本卡，核對本卡列出的正式 B 任務與最新 evidence；這是既有 scope 的續接，不是新任務。不得重做已完成的 JA boundary Repair、promotion、A、C 或 G8，也不得建立 replacement B task。

第一步只取得並審核原 B 任務的 `GEN04_RCA_CLOSED`／`GEN04_RCA_INCOMPLETE` receipt。若 receipt 尚未回傳，回到同一正式 B 任務要求 relay；不得自行重跑 production 或另開調查 task。

## Root question

generation 04 是否曾被合法提交成 committed／resumable generation？

若沒有，是誰讓 partial allocation 成為 continuation 的 current authority？若曾經合法，是哪個跨版本 promotion／migration 邊界讓它失效？

這次查的是「半成品為什麼有資格成為目前 generation」，不是補缺失檔案。

## 目前 production 狀態

- `main`、`origin/main`、正式 runtime actor 已收斂到 `3add4229e7cc871d6d77533e6cb702beb87293a2`。
- runtime promotion 已正式 `COMMITTED`。
- promotion transaction：`automation-b-runtime-adoption-3add-retry1-20260827`。
- promotion evidence：`/private/tmp/pantheon-b-promotion-apply-3add-retry1-20260827`。
- 136 個 queue identities 已保留。
- 七個服務仍停止。
- B 尚未執行；Writer／Reviewer／provider production attempt 均為 `0`。
- 不得重新 promotion；第一次失敗的 promotion transaction 已安全 rollback，第二個新 transaction 才是正式 committed authority。

## 目前 blocker

正式 blocker：

`GEN04_PERSISTED_EXTERNAL_PLAN_WITHOUT_SOURCE_REF_MAP`

target run：

`auto-i18n-ja-1414b75a404721e95e74`

continuation state：

- `status = active`
- `started_after_generation = 3`
- `semantic_budget = 1`
- `next_generation = 4`
- `completed_generations = []`

generation 04 目前只有：

- `external-plan.json`
- `plan-operation.json`

缺少：

- `source-ref-map.json`
- `article-operation.json`
- `reviewer-operation.json`
- `planning-result.json`

目前正式入口會進入 generation 04，不會自動跳到 generation 05。新版 pipeline 看到 persisted external plan 但缺 source ref map，會在任何 provider call 前 fail closed。

## 已確認的程式行為

- `_load_or_create_source_ref_maps` 遇到上述精確形狀會拒絕載入。
- `_run_locale_generation` 在 article／Reviewer 呼叫前停止。
- `continue_writer_reviewer` 從 `next_generation` 開始，因此目前會進 generation 04，而非 generation 05。
- 既有測試已證明這個形狀會在 provider 前 fail closed。
- 現有 outbox 入口沒有可證明 `writer attempt = 1`、`automatic repair = 0`、`reviewer = 1` 的 CLI 契約。
- 不得以正常入口硬跑；那只會撞 generation 04，不能合法建立 generation 05。

## 唯一正式 B 任務

- task/thread ID：`01a03c34-fd96-7021-9423-29879c9b5b47`
- title：`Pantheon 翻譯公開網址自動化驗收`
- 狀態：已回傳 `GEN04_RCA_INCOMPLETE`；唯一主裁決為 `RESUME_CONTRACT_GAP`，尚缺完整雙跑 RED 證據。

必須沿用此 task 監工與續接。不得建立 replacement B task。

## 最新 RCA receipt

### 唯一主裁決

`RESUME_CONTRACT_GAP`

### 已閉合證據

- `5aea3f98f0` 的寫入順序先落盤 `external-plan.json`，hydrate 後才寫 `source-ref-map.json`；中斷可形成目前 partial generation 形狀。
- `3e80299bd7` 新增正確的 fail-closed guard：同 generation 已有 external plan、卻缺 source ref map 時拒絕 resume。
- `3add4229e7` 只調整 planning receipt accounting，沒有造成 blocker。
- generation 04 只有 allocation 證據，沒有 committed generation 證據。
- promotion 只切換 actor／manifest authority，沒有修改或授權清理 queue partial generation；因此 promotion 不是 primary root cause。
- Publisher exact-fresh-JA 入口只接受 complete run，不是 partial generation recovery seam。
- 既有 RED seam：`tests/test_agy_multilingual_pipeline.py::test_ja_resume_rejects_persisted_external_plan_without_source_ref_map`，能證明 provider/article/reviewer 在此 blocker 前不被呼叫。

### 尚未閉合證據

精確 fixture 尚未實際證明：

- 同 fixture 連跑兩次結果一致；
- `new generation = 0`；
- `success receipt = 0`；
- protected source／continuation authority bytes before == after；
- deterministic failure receipt 不重複累加。

因此不得直接實作。下一步應先開唯一 bounded Repair 卡，把上述 provider=0 雙跑 fixture 做成 RED，再進最小 lifecycle 實作；不得再做額外 production 調查。

## RCA 必須閉合的四項證據

1. 最後可成功 resume 的版本／commit 或正式行為。
2. 從哪個 commit 或機制開始形成或拒絕此 partial generation。
3. 被破壞的 durable invariant：含 authoritative owner、跨版本 lifecycle、promotion／replacement 邊界。
4. 一條可穩定 RED、provider=0 的測試或 fixture。

## 硬裁決標準

必須區分：

- allocated generation
- committed generation
- resumable generation

`next_generation = 4` 或 generation 04 目錄存在，都不是 committed 證據。

必須找出是否存在 durable authority，能把下列項目綁成同一次完整 planning outcome：

- generation identity
- external plan
- source-ref map
- source／extractor contract version
- coverage result
- operation terminal status

只有 durable state 明確記錄 `PLANNING_INCOMPLETE` 類狀態與正式 `resume_action`，才能稱為正常中斷。僅有 partial files 不算正常中斷。

## 唯一可接受的主裁決

只能選一個 primary：

### `DATA_RESIDUE_ONLY`

必須由既有、早已存在的正式 recovery seam 對 generation 04 精確 fixture 證明：

- 不猜測舊 fact mapping；
- 不刪除 audit artifact；
- 不人工修改 continuation state；
- 不呼叫 provider；
- 明確 terminalize／abandon generation 04；
- 合法重新 planning 或建立下一 generation；
- 重複執行結果一致且不二次轉換；
- 不需修改 production code。

### `RESUME_CONTRACT_GAP`

符合任一即可傾向此裁決：

- 同一流程可先寫 external plan，卻沒有原子 commit 或失敗狀態；
- generation 是否完整只能靠檔案存在推論；
- continuation 把 partial generation 當 current generation；
- 沒有正式方式 terminalize partial generation；
- crash 後只能人工刪檔、補檔或改 state。

若成立，implementation frontier 只能在既有 generation lifecycle／resume seam。

### `MIGRATION_BOUNDARY_BROKEN`

必須先證明：

- generation 04 在舊版當時符合完整契約；
- 舊版確實視它為合法 resumable generation；
- promotion 明確承諾保留該 queue／generation；
- 新版新增必要條件，卻沒有在 promotion preflight 阻擋或轉換；
- 不相容直到新版 continuation 才被發現。

若 generation 04 在舊版當時已是無終態半成品，不得把 primary 責任推給 promotion。

可以記錄 secondary contributing factor，但只能有一個 implementation frontier，不得同時開 resume Repair 與 promotion Repair。

## Provider=0 RED fixture

精確 fixture：

- external plan exists
- source ref map missing
- continuation points to generation 04

必須證明：

- Writer/provider calls = 0
- article calls = 0
- Reviewer calls = 0
- new generation created = 0
- operation success receipt = 0
- source artifacts 與 continuation/current-generation authority bytes 不變
- 可允許 deterministic、append-only failure receipt；第二次執行不得重複累加或改變裁決
- 同一 fixture 連跑兩次，核心結果一致

RED 要固定的不是單純報錯，而是：目前系統無法合法判定 generation 04 應 resume、terminalize 或 supersede，因此必須停在 provider 前。

## Owner 已授權範圍

Owner 已明確授權：

1. main push；已完成。
2. runtime promotion；已完成。
3. 恰好一次 fresh JA generation／Reviewer／publication；尚未消耗。

這份授權不包含第二次 generation，也不授權手動 override、修改 queue/state 或刪除 generation 04。

在 RCA 與必要 Repair／Review 完成前，不得執行 B。

## 禁止事項

- 不刪除、rename 或覆寫 generation 04。
- 不手改 registry、queue 或 continuation state。
- 不補造 `source-ref-map.json`。
- 不用 coverage note 或文字相似度猜 mapping。
- 不呼叫 Writer、Reviewer 或 provider。
- 不建立 generation 05。
- 不再開 JA 內容／boundary Repair。
- 不重開 Promotion、G8、A 或 C。
- 不因現有函式名稱像 recovery 就宣稱已有正式 seam；必須用精確 fixture 證明。
- 不把目錄存在當成 committed generation 證據。
- 不向 Owner重問可由 repository、runtime evidence 或原 B task 回答的問題。

## 下一步

1. 從唯一正式 B task 取得最終 RCA receipt。
2. 主線依本卡標準審核四項證據是否閉合。
3. 只下唯一 primary 裁決。
4. 若為 `DATA_RESIDUE_ONLY`，只使用已存在且經 fixture 證明的正式 recovery seam。
5. 若為另外兩類，只允許一張 bounded Repair；不得先碰 production。
6. Repair 必須回原 Reviewer 驗證原 finding 與 regression。
7. 只有修復、review、main/origin/runtime authority 再次收斂後，才可消耗唯一一次 B fresh generation。
8. 若該次 Reviewer REJECT，立即停止；不得自動產生 generation 06 或下一輪 repair。

## 最終完成條件

Acceptance B 只有在以下全部成立時才完成：

- exactly one fresh JA semantic generation
- automatic writer repair count = 0
- exactly one Reviewer decision
- Reviewer APPROVE
- 既有正式 publication flow 成功
- 公開 JA URL HTTP 200
- 公開正文可見

中間 gate、commit、promotion 或狀態文案均不得單獨宣稱 B 完成。
