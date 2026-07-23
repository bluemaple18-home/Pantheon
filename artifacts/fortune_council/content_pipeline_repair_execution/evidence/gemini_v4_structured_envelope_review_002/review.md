# Gemini V4 Structured-envelope Size Repair-2 Re-review

## Findings

未發現阻塞問題。沒有 P0、P1、P2 或 P3 finding。

## Prior P2 closure

- 先前 `262144`-byte raw task 渲染成 `262509`-byte effective prompt，舊 broker
  ceiling 會拒絕。
- Repair-2 的 broker ceiling 為 `393216` bytes；相同 `262509`-byte probe
  現在通過。
- 最大合法 `262144`-byte task 加 `65536`-byte schema，以較長的 reviewer role
  渲染為 `327955` bytes，仍低於 ceiling。

## Boundary verification

- `393216`-byte exact-ceiling prompt 在目前 production-like allowlisted environment
  實際成功 spawn synthetic target，process count 為 1。
- `393217` bytes、empty prompt 與 8 組 privacy pattern 均在 ledger 建立與 target
  fork 前拒絕。
- Current Darwin production host `ARG_MAX=1048576`；exact-ceiling argv 實際成功，
  不只通過常數比較。
- Outbox raw task/schema limits仍是 `262144 / 65536`，沒有縮減。

## Spec axis

- `256 KiB task + 64 KiB schema + 64 KiB closed envelope = 384 KiB`
  ceiling 精確成立。
- Structured-envelope role/schema/task/digest contract無回歸。
- CommandFrame effective-prompt digest／byte count 與 receipt external-request SHA
  雙 binding 維持。
- Flag-off legacy bypass與 flag-on no-fallback維持。

## Standards axis

- Candidate production diff只調整 broker named constants。
- Runner、outbox、SEO pipeline、process spawn、ledger、anchor、replay與 flag logic
  byte-identical。
- Privacy pattern set與 outbox parity維持；沒有新增 prompt、raw output、
  credential或完整環境持久化。
- 213 個 affected tests、focused與 static gates全綠。

## Remaining risk

`ARG_MAX` 是 host-specific contract；若未來 target 移轉到不同 OS／runtime，必須
重新驗證 ceiling與實際 argv spawn。這不影響目前固定 Darwin production target
的 verdict。

真實 agy 是否遵守 structured envelope仍需另行授權的 canary驗證；本 Review不授權
第三次真實外呼。

## Review 結論

Verdict:
`DELIVERED_CANDIDATE / GO`

GO 只代表可交回主線考慮後續 activation prep，不是 activation、整合、上線、
promotion、legacy removal或第三次真實外呼授權。
