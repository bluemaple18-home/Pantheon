# Gemini Reviewer V4｜Migration and rollback

## Flag off

- `AGY_GEMINI_V4_BROKER` 未設定或不等於 `1`。
- `process_once` 維持原 legacy `generate_json(role, model, prompt, schema)` 單次呼叫。
- 不建立 V4 ledger 或 anchor。

## Flag on synthetic canary

- 只設定 `AGY_GEMINI_V4_BROKER=1` 作為 canary switch。
- `AGY_GEMINI_V4_EXECUTABLE` 指向本卡的 synthetic executable；本卡未執行真實 Gemini CLI。
- operation 使用既有 job ID；item 使用 opaque namespace；attempt 固定 `attempt-1`。
- ledger 與 external anchor 儲存在 queue root 的 V4 子目錄，但路徑、anchor 與 operation identity 不會傳給 target。
- 同一 operation 已存在 ledger 時只 replay，永不再次啟動 target。

## Failure handling

- `BLOCKED / AMBIGUOUS / INVALID`、nonzero、timeout、preflight reject、receipt mismatch 或 caller schema mismatch：寫 failed record並 archive request。
- 不寫 inbox、不補 event、不啟動第二個 target、不呼叫 legacy generator。

## Rollback

1. 關閉 `AGY_GEMINI_V4_BROKER`。
2. 保留既有 V4 ledger 與 anchor 為唯讀 evidence。
3. 不翻譯為 legacy receipt、不補 terminal、不 replay target。
4. 已留下 fail-closed 結果的同一 job 不得透過 legacy 路徑重送；如需處置，另開人工判讀卡。

真實 Gemini canary、移除舊 retry、其他 caller cutover 與內容線恢復均不在本卡。
