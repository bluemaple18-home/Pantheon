---
id: CARD-PANTHEON-G8-V0390-FRESH-PROMOTION-REPLAN-20260825-RESULT
verdict: BLOCKED
execution_mode: read_only_replan
authorization_state: not_authorized
production_mutation: false
remote_mutation: false
---

# V0390 fresh promotion replan 結果

## Verdict

`BLOCKED`。

Fresh target、source、actor、manifest、current private stage、queue、state、transaction 與 machine facts 均無 drift；V0388/V0389 accepted bytes 也都與指定 Git objects 完全相同。然而正式 `scripts.pantheon_content_runtime_promotion plan` 對 V0388 fresh capacity receipt fail closed，回傳 `NO-GO: capacity stop-loss is not PASS`，因此沒有合法的 promotion plan digest，也不得產生或猜測 exact apply argv。

## Root question 答案

目前不能形成可人工核准的 promotion apply plan。阻斷不是 target readiness：source 明確證明 target readiness/barrier 是 `_install_private_stage` 在 `STAGE_INSTALLED` 建立的 apply output，postcheck 才驗證；apply 前只應綁 current-stage digest。真正 blocker 是 formal planner 與 fresh Rule24 evidence 的 schema contract 未對齊：

- planner `_validate_capacity_receipt` 仍要求 `regression_id=REG-PANTHEON-CAPACITY-WRITE-CYCLES-001`、`mode=bounded-synthetic-dry-run`、cycle 的 `rss_available/swap_available`，以及 top-level `reclamation/stop_loss`。
- V0388 accepted receipt 是 `mode=synthetic-non-production-capacity-proof`，以 `before/peak/after_cleanup`、`projections` 與 `stop_loss_negative_result` 表達同類證據，且沒有舊 `regression_id`。
- 不得手工轉譯、改寫或包裝 V0388 bytes 冒充 planner 接受的 receipt，也不得在本卡修改 source/tests。

## Fresh facts 與 exact bytes

- remote `origin/main` 唯一 read-only query：`5872284828f9dd6f0a75adf407becaeadb50d61a`，等於 accepted target。
- baseline main：`8cc2435d53c2138632428d448a4d881d33fd9e29`；source worktree clean/target；production actor clean，HEAD=`db9fb4343df212fd3b65546b017aba159620a058`。
- current manifest digest=`d067358d4d6228483484cdd984f25963ccbe131e8250e4a131ea10a6e6d6e08e`；current stage digest=`8e96f5b3ad6cb702aa69cb7749184246d09a5460894efdf6fc4d8b59b7a76ee2`。
- queue snapshot digest=`e4e2b5e42570953ce1b29117243f972bc170ef7b68ddc2353512533fa378aca2`，140 個 preservable run identity；state digest=`aa9f4ea0c767a920fab719fd519c20896b08cd765ef7bcd2f76a7dc37c467991`。V0390 transaction root 不存在，既有 promotion receipts 全為 terminal state。
- target readiness 與 target barrier 均不存在；這是正確 pre-apply 狀態，不是 drift。
- V0388 capacity/cycle digests、V0389 envelope/verify/manifest digests 皆與 `033f9aaa0a`／`5748d2d1e1` Git object exact-byte match。V0389 仍只代表 local integrity，authorization 仍為 false。

## Machine-readable evidence

- `fresh-facts.json`：remote/local before-after facts、queue/state/transaction/process/LaunchAgent observation 與 mutation counters。
- `readiness-phase-contract.json`：readiness phase source/test lines與 capacity schema mismatch。
- `v0388-v0389-exact-digests.json`：accepted Git object exact-byte comparison。
- `exact-plan-argv.json`、`planner-blocked-receipt.json`：正式 plan argv、canonical digest與 fail-closed result。
- `authorization-payload.json`：`not_authorized` payload；plan/apply digest 明確 unavailable，不以 placeholder 或舊 V0383 digest代替。
- `rollback-packet.json`：只描述預期 durable rollback contract；因 planner blocked，packet 與 transaction 均未建立。
- `protected-tripwire.json`：僅表示本卡 read-only before/after observation；沒有以空 changed set 冒充 apply 後 production snapshot。
- `digest-manifest.json`、`verification-receipt.json`：artifact digests與驗收結果。

## 驗證與邊界

- affected tests：`129 passed in 15.97s`。
- JSON parse、generator `py_compile`、artifact digest重算、`git diff --check`：PASS。
- remote query=1；formal planner=2（兩次均 zero-write、同一 fail-closed result）；apply/postcheck=0；production mutation=0；remote mutation=0；LaunchAgent/deploy/canary/activation/push/tag=0。
- authorization status 固定 `not_authorized`。沒有 plan digest、exact apply argv digest與 formal PASS planner receipt前，不可授權 apply。

## Repair boundary

安全 repair 需在後續獨立工作中，讓 formal promotion capacity validator 直接驗證 V0388/V0389 fresh evidence contract（含 exact-byte、policy、two-cycle、reclaim/retention、stop-loss 與 DSSE domain bindings），補足 positive/negative regression tests後再 fresh replan。本卡沒有修改 source/tests，也沒有派下一卡。
