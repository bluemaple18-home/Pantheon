# Failure taxonomy

## Closed transport codes

| Code | 觸發接縫 | 持久化內容 |
| --- | --- | --- |
| `CLI_NOT_FOUND` | command 無法解析或 fork 時 executable 不存在 | code 與 exception class |
| `CLI_TIMEOUT` | subprocess timeout | code 與 exception class |
| `CLI_NONZERO` | CLI return code 非 0 | code 與 exception class |
| `CLI_ENVELOPE_ERROR` | legacy Gemini CLI JSON envelope 含 error | code 與 exception class |

## 保持獨立的 failure

- CLI stdout 不是合法 JSON：保留 `JSONDecodeError`。
- Response 缺必要 envelope 欄位：保留 validation error。
- Candidate/schema 不合格：保留 pipeline validation/schema 分類。
- V4 shadow：維持既有 closed broker diagnostic 與 fail-closed 行為。

## Privacy contract

允許新增的 diagnostic 欄位只有固定 `error_code`；值必須命中上述 enum。以下資料不得寫入 failed receipt 或 operation receipt：

- prompt / response
- raw stdout / stderr
- arbitrary exception text
- credential / token / API key
- home/private/temp path

Runner 仍保存既有 request digest、job id、時間與 exception class；沒有保存 CLI detail、exit output 或 envelope error payload。
