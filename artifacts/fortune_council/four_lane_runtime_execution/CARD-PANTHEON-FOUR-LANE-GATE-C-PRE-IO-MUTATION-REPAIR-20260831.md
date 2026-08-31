---
id: PANTHEON-FOUR-LANE-GATE-C-PRE-IO-MUTATION-REPAIR
parent: PANTHEON-FOUR-LANE-GATE-C-CASE-LOCAL-ZERO-MUTATION-EVIDENCE
type: bounded-product-repair
status: ready-for-wrong-mode-only
scope: WRONG_MODE_PRODUCT_REPAIR_ONLY
production_activation_authorized: false
shadow_execution_authorized: false
---

# Gate C pre-I/O mutation repair

## Root question and strict scope

依 independent `REVIEW_NO_GO` 重新分類 Gate C evidence：

1. wrong-mode 在 reject 前建立 `coordinator.lock`：唯一保留的 product defect。
2. gen07 tombstone：分類為 `QUALIFIED_EXTERNAL_DRIFT_INSIDE_LOCK_APPLICATION_PERSISTENCE_ZERO`，不是 product defect；fixture 的 `generations/07` 不屬 source mutation，且必須保留 lock 內 revalidation semantics。

唯一 product repair 目標是讓 wrong-mode 在任何 lock application 前完成 immutable prevalidation；不得以 reject 後 cleanup 取代 pre-I/O contract。除 wrong-mode 外不得吸收其他 failure、architecture 或 runtime scope。

## Required history/source-owner gate

在任何 production change 前，必須以證據閉合 AGENTS regression stop-line 4：

1. last successful behavior/version。
2. introducing commit/mechanism，以 `git blame`／`git log` 定位。
3. 被破壞的 durable invariant。
4. 能穩定抓到問題的 exact RED tests。

若無法閉合 history、source owner 或 invariant，立即 `BLOCKED_EXACT_HISTORY_OR_OWNER_UNRESOLVED`，不得修改 production。

## Allowed change

只允許：

- `tests/test_agy_gemini_coordinator.py`
- `scripts/agy_gemini_coordinator.py`（僅在 source trace 證明此檔是 owner，且為 minimal bounded diff）
- repo-local result receipts

production change 必須只對 wrong-mode 增加 immutable prevalidation，置於 `_run_identity_lock` 前，並保留 `_run_identity_lock` 內 revalidation；不得新增 cleanup-after-reject workaround 或移除 lock 內 revalidation。

## Forbidden

- 其他 `scripts/**`、architecture、runtime manifest、queue/registry、publisher、activation/shadow。
- provider/network、publish、production queue/ledger/public content、launchctl。
- 新 subsystem、第二套 validator/lock owner、migration、legacy compatibility expansion。
- 任何未經 history/source-owner gate 證明的額外修正。

## TDD sequence

1. 先修 test assertions，使 wrong-mode `lock-exists` 明確 RED；snapshot 必須在 mutation 前後可比較。
2. 保存 wrong-mode exact RED node ID、exception/reason code、before/after lock evidence；gen07 僅保存既有 qualified semantics evidence，不將 fixture directory 當 source mutation。
3. 完成 history/source-owner/invariant 四項證據後，做最小 production diff：wrong-mode immutable prevalidation 先於 `_run_identity_lock`，並保留 lock 內 revalidation。
4. 重跑 wrong-mode exact test 使其 GREEN；gen07 existing qualified semantics 必須維持；任何 cleanup-only 或 assertion 放寬均不合格。

## Verification contract

必須執行並保存 raw outputs：

- exact wrong-mode RED → GREEN。
- gen07 existing qualified semantics（`QUALIFIED_EXTERNAL_DRIFT_INSIDE_LOCK_APPLICATION_PERSISTENCE_ZERO`）。
- 受影響 Gate C 13-node manifest。
- baseline impacted tests。
- `git diff --check`。
- allowlist audit：只含 test file、minimal owner script（若必要）與 receipts。
- independent review。

wrong-mode 必須證明 rejection 在 first I/O 前且 `coordinator.lock` 不存在；gen07 必須證明 qualified external drift、lock 內 revalidation 與 fixture `generations/07` 不屬 source mutation；queue/state/ledger/registry/runtime roots before==after，provider/service/production mutation=0。

## Acceptance and stop conditions

只有 wrong-mode exact test RED→GREEN、gen07 existing qualified semantics 維持、Gate C 13-node manifest 全綠、baseline impacted tests 全綠、zero mutation 與 independent review 完成，才可標記 `GATE_C_PRE_IO_MUTATION_REPAIR_PASS`。

若出現第三個 product defect、其他 source diff、history/owner unknown、任何 provider/service/production I/O、related failure 或 allowlist drift，立即 `BLOCKED_EXACT_<reason>`，停止並不得建立下一個 repair。

## Rollback

rollback 僅為 revert 本卡批准的 bounded diff（test assertions 與 minimal owner-source change）；不得 reset/checkout broad workspace，不得回復任何 production artifact，且 rollback 後須重新跑兩個 RED tests 證明 defect 可重現。

## Traces

- `TR-REPAIR-001`：wrong-mode lock pre-I/O RED→GREEN。
- `TR-REPAIR-002`：gen07 `QUALIFIED_EXTERNAL_DRIFT_INSIDE_LOCK_APPLICATION_PERSISTENCE_ZERO` 與 lock 內 revalidation（非 product repair）。
- `TR-REPAIR-003`：history/source-owner/invariant/introducing mechanism 四項 evidence。
- `TR-REPAIR-004`：minimal `scripts/agy_gemini_coordinator.py` owner diff（若 source trace 必要）。
- `TR-REPAIR-005`：Gate C 13-node manifest 與 impacted baseline raw outputs。
- `TR-REPAIR-006`：zero mutation、allowlist 與 independent review。

## Why not less / why not more / do not absorb

- `why_not_less`：只調整 wrong-mode assertions 或事後刪除 lock，仍違反 pre-I/O invariant；必須 immutable prevalidation 並保留 lock 內 revalidation。
- `why_not_more`：唯一 product repair 只修 wrong-mode；gen07 已 qualified，不擴張至其他 lane、validator、runtime architecture 或 lifecycle。
- `do_not_absorb`：不把 fixture `generations/07` 當 source mutation，不吸收未證實 failure、不修改其他 scripts、不建立新 cleanup/rollback owner、不放寬 strict validation/legacy contract。

## Verdict

唯一允許結果：`GATE_C_PRE_IO_MUTATION_REPAIR_PASS` 或 `BLOCKED_EXACT_<reason>`；本卡不授權 activation、shadow、provider 或 production publish。
