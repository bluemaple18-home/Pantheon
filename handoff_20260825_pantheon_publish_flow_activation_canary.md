# Pantheon 發文流程 activation／canary 換手

## Root question

用現成 runtime 完成一篇文章的端到端發佈；唯一完成條件是文章成功 publish，且公開網址可正常開啟。

## Blocker

目前無技術 blocker。尚未執行 activation、試發與公開網址驗收。

## Candidate fork

無。不要再拆卡、開新任務鏈或補局部證據卡。

## Goal

直接完成：啟動現成 runtime → 投一篇測試稿 → publish → 驗證公開網址。

## Constraints & Preferences

- 節省模式；不要重述長規則。
- 不開新卡；本 handoff 就是唯一接手入口。
- 不用局部 `PASS` 冒充完成。
- 不改寫 git 歷史，不 push、不 tag。
- 不碰既有未追蹤檔。
- 不重做 runtime promotion。
- 若同一 blocker 累計三次，停止並回報單一根因。

## Completed Actions

- main 已整合 V0390 阻擋證據：`0bc8e4140e`。
- 正式 capacity guard exercise：`PASS`，兩個 bounded write cycles、reclamation、stop-loss 均符合 promotion validator。
- 受影響測試：28 passed。
- promotion target：`5872284828f9dd6f0a75adf407becaeadb50d61a`。
- formal plan：`READY_TO_APPLY`。
- apply 內建 postcheck：`POSTCHECK_PASSED`。
- finalize：`COMMITTED`。
- plan digest：`1586b147cd680606859739fa68728c7eb40820d4cb4053ba298ebda2f681bb1b`。
- target manifest digest：`389cd799384af4628b9fc371d620b5e87bed52125f27d6612119158af568bfca`。

## Active State

- branch：`main`。
- runtime actor HEAD：`5872284828f9dd6f0a75adf407becaeadb50d61a`，clean，origin 正確。
- promotion transaction：`COMMITTED`，rollback bundle 已依 finalize 契約移除，audit receipt 保留。
- generation：`g36-5872284828-zero-write-20260824`。
- activation barrier 與 readiness 已存在。
- main 尚未 push；既有未追蹤檔保持原狀。

## In Progress / Remaining Work

1. 第一拍只讀確認本 handoff、runtime transaction 狀態與正式啟動入口。
2. 使用既有正式入口啟動 runtime；不要建立替代腳本或第二套流程。
3. 投入一篇可辨識的測試稿並完成 publish。
4. 取得公開網址，以 HTTP／browser 驗證正文可見。
5. 只以文章網址與驗證結果回報完成。

## Waiting conditions

- 不等待另一張卡。
- 不等待重做 promotion。
- 若 activation 屬外部 runtime mutation，沿用使用者在本問題鏈中「繼續做」的明確授權；不得再重複詢問同一授權。

## Blocked & Errors

- 舊 V0390 planner blocker 已解決：先前誤用 Rule24 evidence receipt；正確 producer 是既有 `scripts/pantheon_content_capacity_guard.py exercise`。
- 此 blocker 不得再衍生 V0391 或新修補卡。

## Key Decisions & Resolved Questions

- 發文流程不是精密整合專案；後續只保留單一直線。
- promotion 完成不等於發文完成。
- `PASS` 僅能描述對應檢查；端到端完成只由公開文章網址證明。

## Limits

- 不 push、不 tag、不部署其他版本。
- 不修改共享 registry／metadata，除非既有 publish 正式入口本身負責該原子交易。
- 不清理、不加入、不提交既有未追蹤檔。
