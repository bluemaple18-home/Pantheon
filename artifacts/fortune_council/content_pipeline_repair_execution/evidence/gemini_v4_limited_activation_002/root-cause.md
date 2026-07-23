# Gemini V4 Limited Activation-002 Root Cause

## 已證實事實

- 真實 target process durable exactly-once：
  `COMPLETE / 1`
- terminal：
  `PROCESS_TERMINAL / SUCCESS`
- caller：
  `V4BrokerFailure`
- closed diagnostic：
  `JSON_INVALID`
- retry／fallback／second process：
  `0`

`JSON_INVALID` 只表示 target stdout 不是合法 JSON；evidence 不保存 raw stdout，
因此不推測或重建其文字內容。

## Production path 對照

### Legacy CLI

`GeminiClient.generate_json` 建立 system instruction 與 generation config。
`GeminiClient._cli_transport` 再把以下內容渲染進 effective CLI prompt：

- writer／reviewer role instruction
- `只輸出符合 schema 的 JSON`
- `單一 JSON object，不得有 Markdown code fence`
- 完整 JSON schema
- user task prompt

### V4 outbox runner

Outbox request 確實包含：

- `role`
- `prompt`
- `response_schema`

但 `scripts.agy_gemini_runner.process_once` 呼叫 V4 broker 時，target
`raw_request` 只有 `request["prompt"]`。`role` 與 `response_schema` 只用於本機
選擇與回傳驗證，沒有進入 agy 的 effective prompt。

## Root cause

V4 transport adapter 沒有保留 legacy CLI 的 structured-generation envelope。
因此真實文章 prompt 要求產文格式，卻沒有把唯一 JSON、禁止 code fence 與完整
schema 告知 CLI target；本次結果遂被安全分類為 `JSON_INVALID`。

這不是 ledger、anchor、replay 或 process exactly-once 問題。

## Repair 邊界

後續 Repair 必須先用 RED 測試鎖定：

1. effective prompt 包含 closed role instruction。
2. effective prompt 包含 JSON-only／no-code-fence 約束。
3. effective prompt 包含 canonical response schema。
4. actual effective prompt digest／byte count 綁定 CommandFrame。
5. 不保存 prompt、raw response、credential 或完整環境。
6. flag-on 維持 no legacy fallback；flag-off 維持 legacy。

Activation-002 不修改 production code，也不授權第三次真實外呼。
