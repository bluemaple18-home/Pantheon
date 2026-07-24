# Gemini V4 Limited Activation Diagnostic Repair-3 Decision

- status:
  `DELIVERED_CANDIDATE`
- decision:
  `READY_FOR_REVIEW`
- external invocation count:
  `0`

## Candidate result

- Existing boolean-only validator now produces bounded, value-free schema diagnostics.
- Broker result carries at most three fixed-keyword／schema-path diagnostics.
- Runner independently closes keyword, token type, schema membership, path depth, token
  length and array index before failed-record persistence.
- Unknown additional property names、instance values、raw response與 validator message
  都不保存。
- Flag-on remains fail closed with no legacy fallback。
- Exactly-once ledger／anchor、response schema、structured envelope與 publisher 都未修改。

## Verification

- Initial RED:
  `4 failed`
- Initial GREEN:
  `4 passed`
- Bounded-index RED／GREEN:
  `1 failed -> 1 passed`
- Unique affected tests:
  `233 passed`
- CodeGraph:
  `129 files / 2154 nodes / 4482 edges / up to date`
- py_compile／privacy／diff gates:
  `PASS`

## Review boundary

本候選只解決 schema mismatch 的安全定位能力。它沒有證明 Gemini 真實輸出已符合
schema，也不授權新 canary、放量、預設 promotion、legacy removal、發布或部署。

獨立 Review 必須特別檢查：

1. diagnostic collector 是否完全維持原 schema acceptance semantics；
2. forged BrokerResult 是否可能把任意 key、value、message 或無界 integer 寫入；
3. production writer／reviewer schema 的合法 path 是否會被錯誤封閉；
4. `BrokerResult` 新欄位是否破壞既有 positional constructors 或 replay 契約。

Review GO 前不得執行新真實外呼。
