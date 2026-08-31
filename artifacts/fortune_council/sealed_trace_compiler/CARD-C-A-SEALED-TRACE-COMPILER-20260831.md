# Corrected C-A sealed trace compiler

狀態：`REPAIR_READY_FOR_REBUILD`

## 目的與邊界

在 disposable staging 中重用既有 editorial／translation Writer-Reviewer flow，並在 evidence publish 前以既有 R2 RAW_STDIN broker/runtime contract 驗證每個已錄取 request 的 sealed executable result。不得寫 runtime queue、V4 ledger、production state，亦不得修改 Runner、Coordinator、installer、Publisher 或 domain pipeline。

## 驗收

- 每個 actual trace entry 必須以相同 executable、相同 RAW_STDIN request、相同 schema/normalizer 完成一次成功 preflight；normalized output 與 Recording payload/digest 必須完全一致。
- preflight 後、bundle construction 前必須再驗 actor、source digest 與 lane queue safe tree snapshot；任何 drift 均不得發布 final artifact 或回傳 queue 未寫入的過期事實。
- final rename 後 parent fsync 若失敗，canonical final artifact path 必須先移入 hidden quarantine sibling 才做 cleanup；quarantine deletion 失敗只能留下非canonical failure evidence，不得留下可消費 bundle。
- clean actor integration 僅在新的 exact candidate commit 後執行；目前為 `PENDING_NEW_FINAL_FREEZE`。

## 結果範圍

- preflight 的 ledger／anchor 僅位於 disposable staging 的 `sealed-executable-preflight/`，compile receipt 明示其位置與 entry count；R2 bundle schema 不擴張。
- self-test 只證明 implementation contract；不構成 C-A review、runtime activation 或 clean actor integration acceptance。
- `da78112cebb8d7f2881933af85e516e07b995eb2` 是 rejected candidate 的 forensic evidence，非 acceptance 或可用 clean integration evidence。

## 最小性

why_not_less：R2 entry 只記錄 result digest 不會實際執行 sealed executable，故需在 compiler staging 補上一次 exact executable-result binding。

why_not_more：沿用既有 broker/Runner protocol 與 schema validation，不新增 executor、ledger、runtime 或 authority subsystem。
