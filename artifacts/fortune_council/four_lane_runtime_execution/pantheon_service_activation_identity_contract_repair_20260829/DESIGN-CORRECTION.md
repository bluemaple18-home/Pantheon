# Design correction：Runtime manifest identity semantics

## Decision

原 actor-prefix requirement 判定為 `OVERREACH`。較小且符合既有 authority topology 的模型成立：

- `identity`：nonempty、trimmed opaque correlation。
- actor：由 separate `actor_head` 擁有；存在時由 `load_manifest` 對 actor root驗證。
- integrity：`manifest_digest` 綁完整 payload；`runtime_identity_digest` 分別綁 `identity` 與存在時的 `actor_head`。
- mode：由 explicit command arguments與 plist/stage topology擁有。

## Evidence chain

1. accepted parent有6個正式 `build_manifest` producer call sites。caller輸入、promotion authorization、installer copy、recovery、canary與capability probe共呈現六種 producer schema；capability probe甚至沒有 `actor_head`。
2. accepted commit內5份 committed runtime manifests共7,556 bytes，存在兩種 identity shape；2份 `parent:<sha>;tree:<sha256>` 沒有 `actor_head`，3份 gate2 shape才有 separate actor_head。
3. 14個正式 `load_manifest` consumers中，除 capacity外沒有任何 consumer從 identity拆 actor或 mode。capacity parent只有兩個私有語義使用點：transition suffix rejection與 live plist不可讀時的 mode fallback。
4. parent同參數 baseline與candidate相比新增36個 G8 failures。這些 fixtures使用 opaque `g8-live`／`g8-staged` identity並以 separate actor_head持有 actor authority；shared parser在任何 consumer的原有 invariant之前拒絕。
5. production last-good／first located bad／current三筆恰好採 gate2 actor-embedded shape，但這只是同一 producer lineage的三個樣本，不能升格成跨 producer durable contract。

完整 callsite、test node、manifest bytes/hash與 lineage分類見 `identity-census.json`。

## Repair frontier correction

應撤回全部 shared parser新增內容。最小 Repair只移除 capacity 對 opaque identity suffix的私有解析／拒絕與 mode fallback，並保留現有：

- nonempty/trimmed identity check；
- manifest/runtime identity digest；
- separate actor_head/root validation；
- barrier、stage、live tuple、Rule24與recovery-mode fail-closed checks。

這不是把 `g8-live` 加白名單，也不把 parsing移到另一個 helper。共同 seam已存在於 manifest payload與digest；缺口是 capacity額外收窄 consumer contract。

## Why not less / why not more

- `why_not_less`：只白名單 `g8-live` 仍保留錯誤語義 owner，且無法涵蓋 `g8-staged`、`parent/tree`或後續合法 opaque correlation。
- `why_not_more`：actor_head、兩層 digest、barrier、stage/live tuple與 explicit mode topology已各自擁有 authority；不需新 parser、schema union、lineage mapping或第三個 source。
- `do_not_absorb`：per-service identity、identity registry/FSM/DB/ledger、manifest migration、live rewrite、validator bypass、逐installer分支。

## Reproducibility

從 `<repo-root>` 執行：

```bash
.venv/bin/python artifacts/fortune_council/four_lane_runtime_execution/pantheon_service_activation_identity_contract_repair_20260829/identity_semantic_census.py \
  --repo . \
  --history-census <main-checkout>/artifacts/fortune_council/four_lane_runtime_execution/pantheon_service_activation_manifest_identity_rca_20260829/history-and-live-census.json \
  --baseline-comparison artifacts/fortune_council/four_lane_runtime_execution/pantheon_service_activation_identity_contract_repair_20260829/baseline_identical.json
```

雙跑輸出 byte-identical；canonical output SHA-256為 `97816ab83a855ee543b9201a87e11611ca2a2b00d7b4ec13aca81bc1429ebce9`。production/live mutation為0。
