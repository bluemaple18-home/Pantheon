# C-B exact terminal-source translation materializer

狀態：`CB_IMPLEMENTATION_READY_FOR_FREEZE`

## 範圍

只在 Coordinator 加入一個由單一 source run 與單一 pending receipt 選擇的 CLI entry。它在 source terminal completion、candidate/review、identity envelope、adapter pending digest 與 four-run transaction 全數相符時，呼叫既有 `multilingual.enqueue_article_translations`。

## Authority transition

pending receipt 是 registration 前唯一的 downstream authority。enqueue 已建立既有 translation brief/state 後，原 receipt 只會原子 terminalize 成 `materialized` 並綁定既有 registration；不會先刪除 pending receipt。若 enqueue 後、terminalize 前中斷，原 pending receipt 保留，下一次 exact replay 會以既有 enqueue idempotency 完成 terminalization。

## 不吸收

- 不新增 sweep、daemon、FSM、ledger、registry、Runner 或 translation pipeline。
- Controller 不自行寫 translation `brief.json` 或 state；僅呼叫現有 enqueue/registration path。
- 不做 provider、Publisher、launchctl、public 或 production mutation。

## Why not less / why not more

每 receipt 的既有 run-identity lock 與 receipt digest re-read 是防止同一 authority 重複 terminalize 的最小 CAS boundary；沒有建立跨 receipt transaction，因既有 multilingual enqueue 已是 translation registration owner。
