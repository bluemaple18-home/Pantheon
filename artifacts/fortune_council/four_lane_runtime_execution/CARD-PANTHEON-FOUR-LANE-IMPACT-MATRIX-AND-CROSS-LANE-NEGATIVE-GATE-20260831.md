---
id: PANTHEON-FOUR-LANE-IMPACT-MATRIX-AND-CROSS-LANE-NEGATIVE-GATE
parent: PANTHEON-FOUR-LANE-CURRENT-ACTOR-OPERABILITY-ACCEPTANCE
type: sequential-acceptance-slice
status: ready-after-gate-a1
precondition: GATE_A1_PASS_AND_BASELINE_GREEN
canonical_actor_sha: 0f61545f8c6b561742b27792b8fef11ae8b1ccc5
production_activation_authorized: false
shadow_execution_authorized: false
---

# Impact matrix and cross-lane negative gate

## Root question

在 Gate A1 與 baseline 均綠後，將 requirements 重新綁定 current actor，完成四 lane impact/evidence matrix，並以既有 tests/private campaign harness 做 Phase C offline negative gate；不啟動服務、不觸碰 provider/network/production。

## Preconditions and authority

僅在 `GATE_A1_PASS + BASELINE_GREEN` 且 canonical actor SHA=`0f61545f8c6b561742b27792b8fef11ae8b1ccc5` 時開始。Gate A1、baseline、previous waived failures 均需先讀取並分類；不得把 waived 狀態直接視為 PASS。current actor 必須重新綁定，不能以 release tag 或舊 live actor 代替。

## Phase I：requirement × lane × evidence matrix

先使用 CodeGraph 定位 existing tests；若 CodeGraph 無結果，才限域搜尋既有 tests。完成定位後 freeze exact node IDs，receipt 必須逐列使用以下固定欄位：

`requirement_id,lane,evidence_layer,existing_receipt,dependency_intersection,evidence_disposition,execution_requirement,required_gate,reason_code`

Matrix 必須涵蓋：

- 四 lane routing、identity、isolation、resume、rollback、capacity。
- 七服務 single actor／generation／digest／token。
- publisher exact plan-only 與 zero production/public mutation。
- historical business outcomes carry-forward；current actor rebind。
- routing/identity revalidation；republish not required。

每個 dependency intersection 必須明示是否可在 offline Phase C 證明；證據不足或 waived failure 未分類時，結果為 exact blocked。

## Phase C：offline cross-lane negative gate

只可使用 existing tests 與 private campaign harness；禁止 service、provider、network、activation、shadow 或 production I/O。Coverage 必須包含下列每一類，且證明 rejection 發生在任何 I/O 前：

- wrong lane。
- wrong mode。
- wrong identity。
- wrong manifest。
- wrong generation。
- selector zero match。
- selector many match。
- duplicate locale。
- ledger conflict／lifecycle conflict。

每個 negative case 必須保存 exact node ID、expected error/reason code、zero-mutation fingerprint，以及與 matrix requirement 的 trace。不得新增 harness、source 或 test code。

## Existing test and evidence boundary

- 先由 CodeGraph 定位既有 tests；只讀取其 context，不修改 indexed state。
- freeze 後僅執行既有 exact node IDs；不得使用 broad selector 掩蓋缺失 coverage。
- private campaign harness 僅限 temporary/offline roots；provider calls、service launches、production mutation 必須為 0。
- historical business outcomes 僅 carry-forward evidence，不重新發布、不改 public content。
- Previously waived failures 必須分類為 resolved、not-applicable with evidence、或 blocker；不得 waiver-to-pass。

## Forbidden

- 新增或修改 harness、source、tests、scripts、runtime manifest、registry、queue、ledger。
- activation、shadow、service start/launchctl、provider/network。
- production queue/ledger/public content、republish、tag/push/deploy/canary。
- 以 release/tag、舊 receipt、live actor 或狀態文案取代 current actor evidence。

## Acceptance contract

只有同時成立才可標記 `IMPACT_MATRIX_ACCEPTED + GATE_C_PASS`：

1. Gate A1 PASS 與 baseline green precondition 有可重現 receipt。
2. Phase I matrix 完整，固定欄位與 traces 齊全，current actor rebind 完成。
3. exact frozen node IDs 涵蓋所有指定 negative 類型。
4. 所有 negative cases pre-I/O fail closed。
5. existing tests/private campaign harness 全程 offline，provider/service/production mutation = 0。
6. historical carry-forward 與 waived failures 分類完整，無 related failure。
7. production/public fingerprints unchanged。
8. independent review 完成。

## Verdict and stop conditions

唯一允許 verdict：

- `IMPACT_MATRIX_ACCEPTED + GATE_C_PASS`
- `BLOCKED_EXACT_<reason>`

若發現 authority unknown、matrix dependency 未閉合、negative 未 pre-I/O rejection、任何 related failure、provider/network/service call、production fingerprint drift 或未分類 waived failure，立即停止並標記 exact blocked reason；不得進入後續 activation/shadow slice。

## Traces

- `TR-IMPACT-001`：Gate A1 PASS／baseline green precondition 與 current actor rebind。
- `TR-IMPACT-002`：CodeGraph-first定位、fallback 限域搜尋與 frozen exact node IDs。
- `TR-IMPACT-003`：固定 matrix 欄位與 requirement×lane×evidence dependency intersection。
- `TR-NEG-001`：wrong lane/mode/identity/manifest/generation pre-I/O rejection。
- `TR-NEG-002`：selector zero/many、duplicate locale、ledger lifecycle conflict pre-I/O rejection。
- `TR-NEG-003`：offline zero provider/service/production mutation fingerprints。
- `TR-CARRY-001`：historical business outcomes carry-forward、republish not required、waived failure classification。
- `TR-REVIEW-001`：independent review required before PASS。

## Why not less / why not more / do not absorb

- `why_not_less`：只做正向 lane tests 或沿用舊 receipts，無法證明 cross-lane negative pre-I/O authority 與 current actor rebind。
- `why_not_more`：本 slice 只做 impact matrix 與 offline Gate C；不吸收 activation、shadow、provider、network 或 production acceptance。
- `do_not_absorb`：不新增 harness/source、不中和 previously waived failures、不把 broad selectors 或狀態文案當 exact evidence、不重新發布 historical outcomes。
