# 唯讀命令收據

- CodeGraph：主工作區 `status → context → search → explore`，source decision 前完成。
- production snapshot：既有 `collect_readiness_evidence.py snapshot/compare`，只讀 actor、manifest、queue、state、transaction、stage、live plist 與 `launchctl print`。
- promotion：只呼叫 `scripts.pantheon_content_runtime_promotion.plan_promotion` 兩次；兩次皆 `BLOCKED / source SHA drift`，結果 deterministic。
- 未呼叫：`apply`、`finalize`、`rollback`、Publisher reset receipt writer、preactivation transition mutation、canary、deploy、schedule。
- Git：remote query `0`；未執行 fetch、pull、push、tag、branch/ref mutation 或 origin 變更。
- frontier stop：`G8-ARP-002 / CANONICAL_TARGET_SOURCE_CHECKOUT_UNAVAILABLE`；後續只封裝 blocker、契約與 tripwire evidence，未執行下游 gate。
