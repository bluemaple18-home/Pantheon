# Gemini Reviewer V4 implementation Repair 1｜Root cause

## Root question

Production `run_single_shot` 在 broker durable 寫入 `OPERATION_CREATED` 後，才重新讀取 executable 驗證 precheck digest。當 executable 在 parent precheck 與 broker validation 之間改變時，broker 直接拋出 `FrameError` 並退出，沒有把已接受的 broker attempt 與可判定的 pre-fork abort 寫入 ledger。

## Evidence

未修改的 replacement Reviewer probe 走 real `run_single_shot` 與 synthetic subprocess，重現：

- ledger 只有 `OPERATION_CREATED`
- target launch count 為 `0`
- result 與 fresh replay 均為 `INVALID / UNKNOWN`
- replay error 為 `ILLEGAL_EVENT_ORDER`

原始輸出保存於 `red-fresh-results.json`。

## Repair boundary

- 通過 executable 存在／可執行 preflight 後，先 durable append `BROKER_ATTEMPTED`。
- executable 重新讀取失敗或 digest mismatch 時，在 `FORK_ATTEMPTED` 前 durable append `BROKER_ABORTED(outcome=CRASH_BEFORE_FORK)`，回傳 `BLOCKED / 0`。
- 新 regression 直接走 production `run_single_shot` 並在 parent 啟動 broker 前置換 executable；沒有以手工 ledger fixture 代替 production path。
- preflight、fork／exec boundary、runner、flag、anchor、retry／fallback 與 strict replay schema／binding／ordering／frame／chain 判定均未改動。
