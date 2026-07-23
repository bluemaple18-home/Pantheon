# Gemini V4 Structured-envelope Review Decision

- status: `DELIVERED_CANDIDATE`
- verdict: `DELIVERED_CANDIDATE / NO_GO`
- candidate:
  `a438bf2dec16fb386b5fe23bec83583140f44ed5`
- Review provisioning commit:
  `d56153329c7467515e00e8e13e9e9aa6f714e5f5`

## Findings

- `P2`:
  Outbox 允許 256 KiB raw task，但 runner 加上 role、policy 與 schema envelope 後，
  完整 effective prompt 可能超過 broker 同為 256 KiB 的上限。有效 request
  會在 ledger 前以 `ValueError` 失敗。

## 通過項目

- 212 個受影響 tests 全綠。
- Focused envelope `6 passed`。
- Focused behavioral boundaries `10 passed`。
- Activation-002 的 adapter contract gap 已以 synthetic capture localization。
- Writer／reviewer role isolation、unknown-role closed、schema determinism、
  no-tool／no-workspace、single JSON／no-code-fence 與 task exact bytes 通過。
- CommandFrame effective-prompt binding 與 receipt external-request binding 同時通過。
- Flag-off legacy bypass、flag-on fail-closed／no fallback、privacy 與 exactly-once
  邊界通過。
- Review 沒有 Gemini／agy invocation、retry、第三筆 payload、merge、push、
  deploy、publish、promotion 或 legacy removal。

## 判定

Structured envelope 的主要語意與安全邊界正確，但 combined size contract 尚未與
broker 上限對齊，會拒絕符合現有 outbox contract 的 request。此 finding 位於本次
renderer 變更的 correctness 邊界，因此不可進入後續 activation prep。

Verdict:
`DELIVERED_CANDIDATE / NO_GO`

下一步只能另立 Repair，補上 shared effective-prompt byte budget 與 boundary tests
後再做獨立 Review。本決策不授權 repair 或第三次真實外呼。
