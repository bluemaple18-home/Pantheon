# RESULT：Pantheon `new` Lane Current Production Acceptance

status: `BLOCKED_CONTRACT_GAP`
verdict: `BLOCKED`
accepted_source: `bde44589f3785aae738bb7d7b1626270ba5505d0`
promotion_plans: `2 READY_TO_APPLY; command/stdout byte-identical`
promotion_applies: `1 POSTCHECK_PASSED`
promotion_finalizes: `1 COMMITTED`
scheduler_creates: `0`
provider_calls: `0`
reviewer_calls: `0`
publisher_executes: `0`
release_commits: `0`
tags: `0`
pushes: `0`
deploys: `0`

## 單一裁決

本卡裁決為 `BLOCKED`。promotion 與已修復的 shared identity contract 均通過；新的唯一阻斷點是 recovery-stage 仍要求一個尚未存在的 `publisher-exact-run-id`，形成 service activation 與 fresh-run creation 的 ordering contract gap。

兩次 promotion plan-only 的 command 與 stdout 均 byte-identical，stdout SHA-256 同為 `870925d8d7c32c86a52278bc40631405791246ac412c0ff269a631ccbb40a05c`，plan digest 同為 `65724d0a572110912ce6618774b0799e5bce11ee7ea57e9d5be683ca270be89c`。唯一 apply 為 `POSTCHECK_PASSED`，finalize/status 為 `COMMITTED / PASS`；actor 與 manifest actor head 精確收斂到 `bde44589f3785aae738bb7d7b1626270ba5505d0`，manifest digest 為 `255c72a7234ca97d1868c278acb5a92405bef03954a1b8e5918f62a4c663a358`。

正式 DAG 依序執行 coordinator `--install`、publisher `--install`、capacity `--install-recovery-stage`。前兩步成功寫入六個同一 bde445 identity／generation／manifest tuple 的 staged plists；capacity 的唯一嘗試以 return code `1` fail closed，stdout 為 `preactivation stage mismatch`，SHA-256 `c75f14bc92e2a767294b36394ce84609d427eacac93d05a1c947035c26967369`。

exact root evidence：`manifest-digest`、`generation`、`publisher-max-runs=1` 均正確，但 `publisher-exact-run-id` 不存在。正式 capacity validator 在 `scripts/pantheon_content_capacity_guard.py:1040-1063` 對 recovery-stage 強制要求該欄位非空；fresh `new` run 依本卡契約尚未在 activation 前建立，因此沒有可合法提供的 exact run ID。猜值、手寫 stage、先建 queue job、capacity-first 或繞過 validator 都被禁止，故立即停止，未執行 aggregate activation 或 scheduler。

## Gate Receipts

| Gate | 結果 | Receipt |
|---|---|---|
| source / origin | `PASS` | clean detached HEAD 與 fetched `origin/main` 均為 `bde44589…` |
| immutable live baseline | `PASS` | actor/manifest `779fb…`、136 registry records、stale Writer 已 terminalized、7/7 stopped |
| Rule24 before | `PASS` | bounded synthetic two-cycle；production mutation false；receipt SHA-256 `3bb260fae46e4e94cc82d4c67a1c68ba7d427f4bcb2da50d73cc8cf72be456e8` |
| Rule25 | `READY` | official gate；failures empty；`canary_created=false` 的既有 package authority |
| promotion plan-only ×2 | `PASS` | command/stdout byte-identical；`READY_TO_APPLY`；schema/preservation checks 通過 |
| promotion apply/finalize/status | `PASS` | `POSTCHECK_PASSED → COMMITTED → PASS` |
| coordinator install | `PASS` | five staged plists；尚未 activation |
| publisher install | `PASS` | sixth staged plist；max-runs=1；尚未 activation |
| capacity recovery-stage | `BLOCKED` | `preactivation stage mismatch`；missing required `publisher-exact-run-id` |
| Rule24 after | `PASS` | stopped topology；production mutation false；receipt SHA-256 `b5f3b2a91e66f4ba81e675b6c3072742f36495cac086f90029f1fc870a6cb3d2` |
| seven services after stop | `PASS` | `7/7` stopped；aggregate activation `0` |

## Mutation Accounting

- production tree bytes：`2034569818 → 2034984626`，僅包含正式 bde445 promotion transaction/actor/manifest 與 private stage receipts。
- queue tree、136-record registry、publisher ledger、四條 lane tree 與七個 live plist before/after 全部 byte/hash-equivalent。
- `new`、`rewrite`、`i18n-new`、`i18n-rewrite` lane mutation皆為 `0`；second job `0`。
- scheduler create `0`；Writer provider `0`；Formal Reviewer `0`；Publisher execute `0`。
- live services始終 `7/7 stopped`；aggregate activation、release commit、tag、push、deploy、public mutation皆為 `0`。
- queue/state/plist 手改 `0`；capacity failure後 retry/bypass `0`。

## Evidence Index

- `resume_bde445_acceptance_helper.py`
- `resume-bde445-immutable-before-snapshot.json`
- `resume-bde445-rule24-capacity-raw.json`
- `resume-bde445-rule25-ready.stdout.json`
- `resume-bde445-promotion-plan-run-1.stdout.json`
- `resume-bde445-promotion-plan-run-2.stdout.json`
- `resume-bde445-promotion-apply.stdout.json`
- `resume-bde445-promotion-finalize.stdout.json`
- `resume-bde445-promotion-status.stdout.json`
- `resume-bde445-service-coordinator.*`
- `resume-bde445-service-publisher.*`
- `resume-bde445-service-capacity.*`
- `resume-bde445-blocked-contract-gap-receipt.json`
- `resume-bde445-post-blocked-snapshot.json`
- `resume-bde445-immutability-comparison.json`
- `resume-bde445-rule24-after-raw.json`

## Anti-expansion Receipt

- 沒有修改 source、test、promotion、coordinator、publisher、capacity 或任何 runtime code。
- 沒有新 Repair、registry、FSM、DB、authority ledger 或 migration。
- 沒有手改／刪除 queue、state、ledger、manifest、stage 或 live plist。
- 沒有猜測 fresh run ID、先建 queue job、重試 capacity、繞 validator 或啟動其他 lanes。
- contract gap 出現後只收集唯讀 root evidence、before/after hashes 與 Rule24 after receipt。

## Not Claimed

- 未宣稱 `GO_CURRENT_PUBLISHED` 或 `AMBER_REVIEW_REJECT`。
- 未完成七服務 aggregate activation或 bde445 live plist replacement。
- 未建立 fresh `new` run、outbox 或 candidate。
- 未取得 Reviewer verdict，未執行 Publisher/release/tag/push/deploy。
- 未宣稱公開 URL HTTP 200、rendered正文、canonical/title/H1 或 console acceptance。
