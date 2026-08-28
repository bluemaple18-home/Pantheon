# Pantheon Acceptance B：gen05 dangling registry runtime guard 換手卡

## Root question

如何讓已具合法 current `identity_envelope` 與 matching registry lane 的 legacy
`translate_existing` run，在 brief 缺少 `lane` 時仍可由正式 coordinator exact-run
安全續跑，而不放寬 identity、建立 gen06、重叫 planning provider或手改 production state？

## Current verdict

`BLOCKED / ACTIVE_RUN_REGISTRY_DANGLING`

這不是內容失敗、gen05 planning failure或新架構事故；是 promotion compatibility
contract 與 coordinator runtime integrity guard 的 bounded contract split。

## Mainline authority

- `main` / `origin/main`：`e72bb2b74dc08e3a842aeba0e4791eef71910755`
- 最新 blocker evidence 已 push；pre-push gate PASS。
- `v0.3.373` 仍指向 `295ae1fc246f99f78335c407e974aa33142ef912`；不得移動既有 tag。
- 本輪未建立 Repair、未修改 code/config。

## Production runtime authority

- Actor：`2ce431ec41f5187531d88b52dfa91cef0373d8b5`
- Manifest digest：`7dbedf4e8544675f6203c2d40f96afa561d961a2c7e5a445c8d1f821f0d369f9`
- Runtime generation：`g55-2ce431ec-gen05-runtime-promotion-plan-20260828`
- Stage digest：`51d0e46da1c495ecf1d717011199444e485754498887823bce1fb17abbac0e29`
- Promotion transaction：`COMMITTED`；rollback required=false。
- Promotion evidence：
  `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_runtime_promotion_apply_2ce_20260828/`

## Target run durable state

- Run：`auto-i18n-ja-1414b75a404721e95e74`
- Source：`V2-TAROT-DEATH-MONEY`；locale=`ja`；article=`V2-TAROT-DEATH-MONEY:ja`
- Continuation：`active,next_generation=5,semantic_budget=1,abandoned=[4],completed=[]`
- gen04 4→5 transition 已 durable 完成；不得重做。
- gen05 已有 `source-ref-map.json`、`external-plan.json`、`plan-operation.json`、
  `planning-result.json`；不得刪除、改寫或重叫 planning provider。
- gen06 不存在。
- Registry state：`status=active,lane=i18n-new`。
- Registry current identity envelope：`translate_existing/i18n-new/V2-TAROT-DEATH-MONEY`，digest合法。
- Canonical legacy brief：`mode=translate_existing`，但 top-level `lane=null`。

## Exact failure evidence

Official g55 `barrier-exec` 包裝 coordinator `cycle --exact-run-id`，在 provider前回：

```json
{"status":"blocked","reason":"active run registry is dangling","run_id":"auto-i18n-ja-1414b75a404721e95e74","active":5,"complete":0,"failed":0,"runner":{"status":"idle"}}
```

本輪 mutation accounting：planning provider=0、Writer=0、Reviewer=0、gen06=0、
publication transaction=0、tag=0、push=0、deploy=0、manual queue/state edit=0。
七服務未載入；lane outbox/processing 均為0。

Acceptance B blocker evidence：

- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-AUTOMATION-ACCEPTANCE-B-TRANSLATION-PUBLIC-URL-20260826-RESULT.md`
- `artifacts/fortune_council/four_lane_runtime_execution/automation_acceptance_b_translation_public_url_20260826/evidence.md`
- `artifacts/fortune_council/four_lane_runtime_execution/automation_acceptance_b_translation_public_url_20260826/machine-summary.json`

## Root cause localization

`scripts/agy_gemini_coordinator.py::_active_run_integrity_block` 先驗 current envelope，
接著仍呼叫 `_identity_envelope_from_brief(brief)`；legacy translation brief 缺 lane 時，
後者拋出 `translate run lane is required for durable identity`，外層把它折疊為
`active run registry is dangling`。

Production registry/run_dir/brief/run_id 都存在且 canonical；真正 mismatch 只有
legacy brief lane missing。Current state lane 與 validated envelope lane 都精確為
`i18n-new`。

Formation history：

- `ef934239c3 Repair durable publish identity lifecycle` 的 helper 支援
  `expected_lane` bounded fallback。
- `e720f2ab41 fix: harden durable identity authority` 移除該 fallback，active guard
  改為只相信 brief lane。
- `CARD-PANTHEON-PROMOTION-HISTORY-AUTHORITY-BOUNDARY-REPAIR-3-20260826.md`
  已讓 promotion guard 在 validated envelope＋matching state lane 下接受 legacy
  missing-lane brief，但沒有同步 coordinator runtime guard。

因此 durable invariant 已在 promotion 與 runtime 之間分裂：promotion 判定可保存，
runtime 卻判定 dangling。

## Safe next step

先做一張 scoped RCA，不直接 Repair、不再跑 production：

1. 以 production-shaped fixture 重現 current coordinator exact-run provider=0 RED；
   fixture 必須包含合法 envelope、matching state lane、legacy missing-lane brief。
2. 證明 `e720f2ab41` 是形成行為，並確認 `ef934239c3` 的 bounded
   `expected_lane` 行為可通過同一 fixture；不得只靠 diff 推定。
3. 鎖定最小 Repair frontier 只能在 coordinator active integrity seam：validated
   current envelope先成立，brief lane存在時必須精確一致；brief lane缺失時只能由
   matching valid state lane確認。state lane缺失／非法／mismatch持續 fail closed。
4. 不修改 production registry、brief、queue、continuation、publisher或promotion。
5. RCA閉合後才回同一 Repair identity做一個 bounded Repair，原 Reviewer re-review；
   Review GO後再 promotion，回同一 gen05 exact-run。

## Stop conditions

- 不得 terminalize target run；它是合法 active continuation，不是遺失 run_dir。
- 不得用 `resume`、手改 brief lane、手改 registry或重新 register繞過 guard。
- 不得重跑 planning provider、建立 gen06、publish、tag或push內容。
- 若 fixture 無法 provider=0 重現、identity authority不唯一或需擴大到新 subsystem，
  立即停止並回主線。

## Thread/runtime note

- 原 Acceptance B thread 與既有 promotion task各發生零訊息／零工具空轉，已中止；
  兩者均未觸發 production call。
- Fresh short-context execution thread `01a0463a-54db-7320-ab32-f88a500f165a`
  產生本次 official blocker與 candidate evidence；不得封存。
