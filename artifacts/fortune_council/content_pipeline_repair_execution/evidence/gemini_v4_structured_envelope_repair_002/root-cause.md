# Gemini V4 Structured Envelope Repair-2 Root Cause

## Review finding

Outbox 的 public contract 分別接受：

- sanitized task：
  `262144 bytes`
- response schema：
  `65536 bytes`

Structured-envelope candidate 將兩者與 closed role/instruction 合成 effective
prompt，但 broker 的 `MAX_AGY_PROMPT_BYTES` 仍等於 raw task 上限
`262144 bytes`。

## Adversarial reproduction

獨立 Review 使用合法最大 task 重現：

- raw task：
  `262144 bytes`
- rendered effective prompt：
  `262509 bytes`
- result：
  `failed / ValueError`
- ledger：
  `absent`

Repair-2 RED 使用最大 task 加最大 schema，rendered effective prompt 為
`327942 bytes`，同樣超過舊 ceiling。

## Root cause

Structured-generation envelope 改變了 broker 所接收 payload 的語意與最大尺寸，
但 prompt ceiling 沒有同步從 raw-task contract 升級成 effective-prompt contract。

## 最小修正

Broker size contract 改為：

- task budget：
  `256 KiB`
- schema budget：
  `64 KiB`
- closed envelope overhead：
  `64 KiB`
- effective-prompt ceiling：
  `384 KiB`

目前 production target 的 `ARG_MAX` 是 `1 MiB`。384 KiB 位於此上限內；超過
384 KiB 仍在 ledger 與 target fork 前 fail closed。

本修正只調整 named constant 與契約測試，沒有修改 process spawn、ledger、
anchor、replay 或 output validation。

本 Repair 沒有 Gemini／agy invocation，也沒有第三筆真實 payload。
