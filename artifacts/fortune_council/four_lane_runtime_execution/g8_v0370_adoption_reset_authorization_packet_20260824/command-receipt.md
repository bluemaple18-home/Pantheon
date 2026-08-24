# 唯讀命令收據

- CodeGraph：主工作區 `status → context → search → explore`，source decision 前完成。
- production snapshot：既有 `collect_readiness_evidence.py snapshot/compare`，只讀 actor、manifest、queue、state、transaction、stage、live plist 與 `launchctl print`。
- promotion：只呼叫 `scripts.pantheon_content_runtime_promotion.plan_promotion` 兩次；兩次皆 `BLOCKED / source SHA drift`，結果 deterministic。
- 未呼叫：`apply`、`finalize`、`rollback`、Publisher reset receipt writer、preactivation transition mutation、canary、deploy、schedule。
- Git：remote query `0`；未執行 fetch、pull、push、tag、branch/ref mutation 或 origin 變更。
- frontier stop：`G8-ARP-002 / CANONICAL_TARGET_SOURCE_CHECKOUT_UNAVAILABLE`；後續只封裝 blocker、契約與 tripwire evidence，未執行下游 gate。

## Repair：portable evidence digest

- 沿用 integrated preauth 的 `evidence_digest_tool.py` 契約，manifest 只保存 evidence-root-relative POSIX paths。
- 可攜驗證：在 evidence root 執行 `python evidence_digest_tool.py verify`；也可執行 `shasum -a 256 -c evidence-digests.sha256`。
- Repair 未重跑 remote query、production probe、promotion plan 或 snapshot，也未修改 Git refs。
