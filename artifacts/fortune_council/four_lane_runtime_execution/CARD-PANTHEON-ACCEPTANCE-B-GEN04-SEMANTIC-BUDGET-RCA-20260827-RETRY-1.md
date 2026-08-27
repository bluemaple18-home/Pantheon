---
id: CARD-PANTHEON-ACCEPTANCE-B-GEN04-SEMANTIC-BUDGET-RCA-20260827-RETRY-1
status: ready
chain_id: PANTHEON-ACCEPTANCE-B-GEN04-SEMANTIC-BUDGET-RCA-20260827
role: implementation
cycle: 1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 固定候選 SHA、核心 continuation state／semantic budget 契約的唯讀 RCA；不改 production code、不執行外部流程，無需升 Sol。
execution_mode: readonly_rca
production_mutation: forbidden
remote_mutation: forbidden
---

# Pantheon Acceptance B：gen04 semantic budget 唯讀 RCA／契約重定錨

工作名稱：Pantheon Acceptance B：gen04 semantic budget 唯讀 RCA／契約重定錨

任務目的：釐清 abandoned generation allocation 是否消耗 semantic generation budget，以及 production exact state `started_after_generation=3, semantic_budget=1, next_generation=4, completed_generations=[]` 在 gen04 被合法 terminalize／abandon 後，下一次正式 continuation 如何進入 gen05。這是 `RESUME_CONTRACT_GAP` 的唯讀根因重定錨，不是 Repair-3。

接手依據：

- 換手卡：`HANDOFF-PANTHEON-ACCEPTANCE-B-GEN04-LIFECYCLE-RCA-20260827.md`
- 原 B task/thread：`01a03c34-fd96-7021-9423-29879c9b5b47`
- 前一 bounded Repair task/thread：`01a041ff-0fa2-7bf1-bca1-69eb447581f0`
- 前一 Repair RESULT：`CARD-PANTHEON-ACCEPTANCE-B-GEN04-LIFECYCLE-REPAIR-20260827-RESULT.md`

## 固定檢查對象

只允許以 candidate git objects、bounded source inspection 與 task-owned `/private/tmp` snapshot 進行唯讀檢查：

- base：`f14118b3044dc8168b759ffa6f999c7035ab55ba`
- G1：`8910d21f342c3265100f0e8389b06a8128b7697e`
- G2：`7f4a18cd024589fdd4100da9888dc79494207164`
- 原 B task：`01a03c34-fd96-7021-9423-29879c9b5b47`
- Repair task：`01a041ff-0fa2-7bf1-bca1-69eb447581f0`

不得將工作樹未提交檔案、production state 或外部服務狀態當成 candidate authority；若需比較，必須明確標示 commit object 與 bounded snapshot 來源。

## Root question

`abandoned` 的 generation allocation 是否應消耗 semantic generation budget？對 production exact state：

```text
started_after_generation = 3
semantic_budget = 1
next_generation = 4
completed_generations = []
```

在 gen04 只有 `external-plan.json`／`plan-operation.json`、缺 `source-ref-map.json`／完整 planning outcome 的情況下，正式 lifecycle 應如何：

1. 保留 gen04 audit 並明確 terminalize／abandon；
2. 不把 allocation 誤算為 semantic attempt 或 committed generation；
3. 使下一次正式入口合法、可重入地進入 gen05；
4. 不建立第二次 fresh semantic generation，不呼叫 provider，不改 production。

## 唯讀 RCA 硬邊界

- 只讀 source、candidate git objects、既有 RESULT、既有 evidence 與 bounded `/private/tmp` snapshot。
- 只可寫本卡專屬 RESULT：`CARD-PANTHEON-ACCEPTANCE-B-GEN04-SEMANTIC-BUDGET-RCA-20260827-RETRY-1-RESULT.md`。
- 只可寫本卡專屬 evidence 目錄：`pantheon_acceptance_b_gen04_semantic_budget_rca_20260827_retry_1/`。
- 可寫 task-owned `/private/tmp/pantheon-acceptance-b-gen04-semantic-budget-rca-retry-1-*` 暫存證據。
- 不得修改 `scripts/`、`tests/`、source、registry、queue、continuation state、production data、shared metadata 或其他 artifacts。
- 不得 commit source／tests 或其他非本卡檔案；完成時只允許建立一個僅含本卡 RESULT／evidence 的 candidate commit。仍禁止 push、tag、deploy、promotion、replacement、publisher、fresh generation、gen04／gen05 實跑或任何 network／provider 呼叫。
- 不得建立 Repair、Reviewer、replacement task 或新的 implementation frontier。

## 必須回答的 RCA 契約

RESULT 必須明確回答以下五個邊界，不能以函式名稱或狀態文案代替證據：

1. authoritative owner：generation allocation、planning outcome、continuation state、current-generation authority 各自的 owner，以及誰有權將 gen04 設為 abandoned／讓 gen05 成為下一個合法 target。
2. budget semantics：`semantic_budget` 計算 allocation identity、planning attempt、committed semantic generation 或其他語意；abandoned allocation 是否扣額度，必須以 candidate 行為與 exact state 證明。
3. operation identity：gen04 partial plan、terminalization decision、authority transition 與 gen05 planning operation 如何關聯、去重與避免把同一 allocation 算成兩次 semantic attempt。
4. atomic transition／crash boundaries：partial artifacts 寫入順序、terminal receipt、state transition、budget accounting 與 crash replay 的原子性；指出何者 durable、何者僅為 residue。
5. promotion／replacement boundary：promotion 是否改變 lifecycle／budget authority；exact-fresh-JA publisher／replacement 是否能或不能 recovery partial gen04；不得把 promotion 或 replacement 當未證明的修復 seam。

另須辨識：

- 最後可成功 resume 的版本／行為；
- 從哪個 commit／機制形成或拒絕 partial generation；
- 被破壞的 durable invariant，並區分 allocated／committed／resumable；
- G1／G2 為何在 semantic budget=1 的 production exact state 仍可能出現空迴圈或假綠；
- 唯一 primary 只能是 `DATA_RESIDUE_ONLY`、`RESUME_CONTRACT_GAP`、`MIGRATION_BOUNDARY_BROKEN` 其中之一。

## Exact RED-capable fixture

必須使用 candidate objects 或 bounded snapshot 建立並實際執行一條 red-capable exact fixture；不得修改 source／tests 來製造訊號。Fixture 必須固定：

- `started_after_generation=3`
- `semantic_budget=1`
- `next_generation=4`
- `completed_generations=[]`
- generation 04 只有 `external-plan.json`、`plan-operation.json`
- 缺 `source-ref-map.json`、`locale-plan.json`、`planning-result.json`、`article-operation.json`、`review-operation.json`
- deterministic fail-if-called doubles，provider／article／reviewer 全部為 0
- gen05 不得建立

RED command 必須可重跑且因本次 semantic-budget／continuation 症狀失敗；import error、fixture 壞掉、環境缺件或無關 assertion 不算 RED。至少要記錄：

- command、exit status、兩次連跑結果與 symptom；
- provider／article／reviewer call counts = 0；
- new generation count = 0；
- success receipt count = 0；
- production／local runtime bytes 完全不動；temp fixture 的 source／gen04 audit bytes 與非授權 authority bytes before == after；
- canonical continuation state／transition receipt 只允許 candidate 既有、明確預期的 transition，必須逐拍保存 before／after hash，並記錄 `next_generation=4 -> 5` 與其後 empty-loop symptom；
- 兩個 fresh temp snapshot 各自完整重跑，須重現相同 transition 與 empty-loop symptom，failure／transition receipt 不得重複累加或改變裁決；
- failure receipt 是否 append-only，以及第二跑是否不重複累加／不改變裁決；
- exact artifact inventory 與 hash。

若只能證明舊 fail-closed guard，卻無法穩定捕捉 `semantic_budget=1` 下 allocation 與 semantic attempt 的差異，輸出 `RCA_INCOMPLETE` 並列精確缺口，不得提出修復。

## 輸出契約

RESULT 開頭只能是 `RCA_CLOSED` 或 `RCA_INCOMPLETE`。

`RCA_CLOSED` 必須包含：

- 唯一 primary 裁決；
- 已跑 RED command／exit／symptom 與雙跑 evidence；
- 四項 RCA 證據與 authoritative owner／budget／operation／atomic／promotion／replacement 分析；
- 最小 implementation frontier（僅限既有 continuation lifecycle／budget seam）；
- `why_not_less`、`why_not_more`、`do_not_absorb`；
- 明確禁止直接修、禁止 Repair-3、禁止 production／provider。

`RCA_INCOMPLETE` 必須逐項列出未閉合的 exact evidence gap、已嘗試的 red-capable command 與退出狀態；不得以推測填補缺口。

## Acceptance

主線只驗證：輸出只有本卡 RESULT／evidence、未修改 source／tests／production、RED command 真正因目標症狀失敗、兩個 fresh snapshot 的 call counts／generation／receipt／protected-byte 與逐拍 canonical transition hash 契約可重現，且 primary 與 implementation frontier 各唯一。完成後只回傳一個僅含本卡 RESULT／evidence 的 candidate commit，由主線裁決是否進入下一個 bounded 修復；本卡不得自行實作修復。
