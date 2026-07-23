# Pantheon Gemini V4：Antigravity CLI 相容契約

## 決策

`antigravity_cli_v1` 明確取代 V4 架構中「target argv 只能包含 executable、prompt 只能走 stdin」這一項假設。原因是本機 `agy 1.1.5` 的非互動介面要求 `--print <prompt>`；其餘單次 process、ledger、anchor、replay、FD 隔離與 fail-closed 契約不變。

## 封閉介面

production runner 固定且顯式選擇 `antigravity_cli_v1`，不以 executable basename 推論安全等級。runner 必須提供部署時配置的 trusted executable SHA-256；未知 profile、缺少或不相符的 digest 一律在 target fork 前 fail closed。`raw_stdin_v1` 只可由明確的 synthetic/test caller 使用，production runner 不讀取 profile override，因此 production 設定無法抵達 synthetic profile。

```text
agy
--model <allowlisted label>
--mode plan
--sandbox
--log-file <operation-local temporary path>
--print-timeout <bounded seconds>
--print <PUBLIC_SANITIZED UTF-8 prompt>
```

模型映射只有：

- `gemini-3.5-flash` → `Gemini 3.5 Flash (Low)`
- `gemini-3.1-pro-preview` → `Gemini 3.1 Pro (Low)`

未知模型在 ledger 建立與 target fork 前拒絕。CommandFrame v2 綁定 profile、CLI model label、payload class、prompt SHA-256、prompt byte length、executable digest 與 timeout；production receipt 另綁定 operation、item、attempt、外部 request SHA-256、request model、`antigravity_cli_v1` profile 與 trusted executable digest，runner 只接受完全相符的 receipt。

## 資料與程序邊界

- prompt 進入 argv 是 `agy --print` 的產品限制，因此此 profile 僅允許公開且已清理的 outbox prompt。
- 禁止本機絕對私密路徑、`.work/`、API key、Bearer token、Google key、private key 與 GitHub token marker；驗證失敗時 target process count 為 0。
- prompt 不寫入 command frame、ledger、anchor、control frame或證據摘要；這些位置只保存 hash、byte count 與 payload classification。
- `--log-file` 使用 broker process 內的 operation-local temporary directory，target 結束後立即清理，不作為交付證據。
- target stdin 為空；除 stdin/stdout/stderr 外不繼承 file descriptor。
- target environment 只允許 `HOME`、`LANG`、`LC_ALL`、`PATH`、`TMPDIR` 與 macOS runtime 的 `__CF_USER_TEXT_ENCODING`。不繼承 `GEMINI_API_KEY`、token 或其他 parent environment。
- `HOME` 提供既有本機 CLI 設定與登入狀態；本相容層不讀取、不複製也不記錄憑證內容。

`raw_stdin_v1` synthetic/test profile 維持 fake target 的原始 stdin 行為，但其 receipt 不含 production profile binding，production runner 必須拒絕，且不得把它當成生產 Gemini transport。

## Completion provenance 限制

本相容層可證的成功範圍僅是：已雜湊並封存的 trusted executable snapshot 完成一次 transport、exit status 為 0，且 stdout 通過 JSON schema。`agy 1.1.5` 未提供可由本 broker 獨立驗證的供應商內部 model-call provenance；因此 receipt 與 `caller_contract_satisfied` 不宣稱 Gemini 供應商內部模型呼叫確實發生，只代表上述 trusted transport completion。

## Canary 邊界

本變更只允許 fake CLI 驗證，不呼叫 Gemini。獨立 reviewer 明確 GO 後，真 canary 必須另卡執行：只送一個合成公開 JSON request、最多一個 target process、無 retry／fallback、不得讀寫文章或發布資料。任何 nonzero、timeout、JSON/schema、ledger/replay 或 binding 失敗都立即停止。
