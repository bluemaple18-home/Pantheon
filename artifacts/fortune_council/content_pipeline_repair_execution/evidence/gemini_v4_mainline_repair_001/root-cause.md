# Root cause

## Fixed identity

- base：`ea7308bf14533c22bc83809bd72faeddcdeed6d0`
- candidate：`6c4931c1da63257cd70bd0abe5776dc1758e4557`
- Review commit：`16a5a9c9dc4af8099650fb3b6106772b2093dcba`
- Review verdict：`NO_GO`
- Repair generation：`1/2`

## P1 `P1_CANARY_BINDING_EVIDENCE`

根因不是 production canary 摘要內部矛盾，而是 evidence contract 只保存自述 summary。舊
`real-canary.json` 沒有 closed receipt、command/control、canonical ledger frames、inbox/result
schema，也沒有能獨立重算 ledger SHA與 final anchor的材料。Fresh Reviewer不能證明
operation/item/attempt/request/model/profile/executable/result屬於同一次 durable execution。

排序假說與證偽結果：

1. 舊摘要可能已含足夠欄位，只缺 verifier。新 standalone verifier 對舊摘要回
   `REJECTED: bundle fields are not closed`，此假說被否證。
2. production replay helper可能足以作獨立驗證。該 helper與被審 production code共用 schema／
   replay logic，且舊摘要沒有 canonical frames可供輸入，因此不能形成 fresh independent seam。
3. evidence-owned recorder可在同一次 public `run_single_shot` 回傳中保存 closed receipt、
   command、control、canonical ledger與schema result，同時不保存 prompt。Synthetic rehearsal與
   12-case mutation matrix支持此假說。

最小修復界面是 evidence-owned recorder/verifier，不修改 runner或既有 implementation／Review
evidence。Verifier只使用 Python標準函式庫，自行檢查 closed schema、canonical JSONL、event
schema/order/count、hash chain、ledger SHA、final anchor、receipt/command/control/inbox/result/
executable binding與 no-fallback。

## P2 `P2_RACE_ANCHOR_ERROR_CONTRACT`

根因是 `run_single_shot` 只有初始 `anchor_store.load()` 捕捉 `AnchorError`；輸掉
`O_EXCL` concurrent-create race後的第二次 load沒有同樣的 public error mapping。Malformed、
wrong-binding或 unreadable external anchor因此逸出例外，而不是回 typed fail-closed result。

排序假說與證偽結果：

1. `replay_ledger` 可能會把 race anchor錯誤轉成 `INVALID/UNKNOWN`。Deterministic RED證明例外
   在進入 replay前就由第二次 `load()` 逸出，此假說被否證。
2. 最小修正只需在 `FileExistsError` branch捕捉 `AnchorError`，沿用初始 load的
   `EXTERNAL_ANCHOR_INVALID` mapping。GREEN證明 result為 `INVALID/UNKNOWN`、caller false、
   result none、resend false且 spawn 0。

沒有加入 retry、fallback、第二個 spawn helper或 debug instrumentation。
