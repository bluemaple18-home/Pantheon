# Corrected C-A sealed trace compiler result

結果：`CA_CORRECTED_REPAIR_READY_FOR_REBUILD`

- 每個 RecordingSealedClient 實際錄取的 request，在 evidence publish 前均以既有 `runner._render_v4_effective_prompt`、`RAW_STDIN_PROFILE`、`run_single_shot`、`FileAnchorStore` 與 `normalize_new_output_contract` 執行一次。結果必須是單一 schema-valid JSON object，normalized result、canonical digest 與封存 payload 全數 exact match。
- 每次 preflight 由 request/result/ordinal 派生唯一 operation/item/attempt；同一 executable 的多筆 request 不會 replay collision。ledger/anchor 只寫 disposable staging 的 `sealed-executable-preflight/`，receipt 將其列為 evidence；runtime queue 與 V4 production ledger 均未寫入。
- executable 的 owner、regular/non-symlink、canonical path、non-group/world-writable、execute bit 與 digest 於 pipeline 前驗證；digest drift 於 broker preflight fail closed。
- `exit 0` 空輸出、invalid/multiple JSON、schema mismatch、nonzero、timeout、payload mismatch 與 digest drift 都在 final artifact publish 前 reject。editorial writer→reviewer、translation chain 及 deterministic writer-only trace 都走實際 production `run_writer_reviewer`。
- artifact publisher 保持 owner-only claim + temp directory atomic publish；fsync failure 的 directory/parent descriptors 在 finally 關閉，claim/temp cleanup 有回歸測試。R2 bundle schema 沒有擴張。
- preflight 前取得 lane queue 的 owner-safe canonical tree snapshot（relative path、entry type、owner/mode、regular-file byte count/digest）；preflight 後、publish 前重新驗 actor/HEAD/base、source digest 與 queue snapshot。source、queue 或 actor drift 均 reject，final artifact 不會出現。
- final rename 後的 parent fsync failure 會先將 canonical final artifact atomically move 至 owner-only hidden quarantine sibling，再 best-effort deletion/fsync parent cleanup 並保留原始 failure；quarantine deletion 失敗只留下非canonical forensic debris，canonical bundle path 一律不存在。

驗證詳見 `raw-test-output.txt`：focused C-A `33 passed`；C-A + affected Runner/broker `142 passed`。

真實 clean actor integration：`PENDING_NEW_FINAL_FREEZE`。必須先有新的 exact candidate commit，再以 clean actor worktree 執行；`da78112cebb8d7f2881933af85e516e07b995eb2` 僅為 rejected candidate forensic evidence。本結果不宣稱 C-A review/acceptance、runtime activation 或 provider execution。
