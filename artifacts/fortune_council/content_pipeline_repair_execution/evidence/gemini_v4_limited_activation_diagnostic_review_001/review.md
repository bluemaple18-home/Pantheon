# Gemini V4 Limited Activation Diagnostic Independent Review

## Findings

### [P1] Failed record 的三個 diagnostic 欄位未做 closed sanitization

- path／line:
  `scripts/agy_gemini_runner.py:101`
- 觸發:
  `run_single_shot` 回傳 malformed／forged `BrokerResult`，在
  `replay_status`、`process_count` 或 `outcome` 放入任意 JSON-serializable
  內容，同時讓 runner 進入 `V4BrokerFailure`。
- 證據:
  synthetic probe 以非內容 sentinel 建立 forged result；failed record 原樣保留
  三個 sentinel。只有 `result_validation` 會經 closed set 檢查。
- 風險:
  若內部 broker boundary 被破壞或回傳物件遭偽造，prompt、raw response、
  credential 或其他任意內容可透過這三個欄位持久化，違反本卡 privacy 與 closed
  diagnostic 契約。
- 建議:
  在建立 `broker_diagnostic` 前，對四個欄位各自做 type 與 closed-value
  normalization；非法值只降級成安全 sentinel，不得直接持久化。補 regression
  覆蓋任意字串、container、bool-as-int 與不可雜湊的 `result_validation`。

### [P2] JSON `null` 沒有分類為 `NOT_OBJECT`

- path／line:
  `scripts/agy_gemini_v4_broker.py:1012`
- 觸發:
  target stdout 為合法 JSON `null`。
- 證據:
  production-path synthetic target 得到
  `caller_contract_satisfied=false`、`result=null`、
  `result_validation=NOT_EVALUATED`。
- 風險:
  `null` 是合法 JSON 但不是 object；目前結果違反
  `VALID / JSON_INVALID / NOT_OBJECT / SCHEMA_MISMATCH / NOT_EVALUATED`
  的互斥分類契約，會讓第二次 activation 的安全診斷再次失去精確原因。
- 建議:
  以 parse 是否成功和 parsed value 分開表示；任何成功解析但 top-level 非 object
  的值（包含 `null`、array、scalar）一律標成 `NOT_OBJECT`，並加入 `null` regression。

## Spec axis

- `VALID`、invalid JSON、array non-object、schema mismatch、nonzero、timeout 與
  durable/control failure 的既有測試全綠。
- JSON `null` 分類不符 spec。
- Runner 只有 `V4BrokerFailure` 且已有 diagnostic 時才新增 `broker_diagnostic`。
- Diagnostic 不是 fully closed；privacy spec 不通過。

## Standards axis

- Candidate production 修改只涉及 broker 與 runner；沒有 publisher、文章、
  registry、automation、default transport 或 legacy removal 變更。
- Failed record consumer 只讀 `error_type`，新增欄位相容。
- Flag-off legacy、flag-on fail-closed/no-fallback、existing operation no resend
  均通過 regression。
- Candidate 未修改 ledger／anchor implementation；replay、control mismatch 與
  exactly-once tests 全綠。

## Review 結論

有 `1 x P1` 與 `1 x P2`，因此不是 GO。

Verdict:
`DELIVERED_CANDIDATE / NO_GO`
