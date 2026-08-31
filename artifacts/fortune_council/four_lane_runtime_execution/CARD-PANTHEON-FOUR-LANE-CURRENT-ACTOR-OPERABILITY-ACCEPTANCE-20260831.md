---
id: PANTHEON-FOUR-LANE-CURRENT-ACTOR-OPERABILITY-ACCEPTANCE
type: acceptance
status: GATE_C_PASS_NEXT_D_E_DISCOVERY
target_verdict: GO_FOUR_LANE_RUNTIME_CURRENT
production_verdict: not in scope
current_remote_release: main
current_actor_sha: 0f61545f8c6b561742b27792b8fef11ae8b1ccc5
release: v0.3.375
acceptance_harness_sha: WORKTREE_UNCOMMITTED
slice_2a_status: BASELINE_GREEN
slice_2a_review: RE_REVIEW_GO
gate_a1_status: GATE_A1_PASS
next_frontier: CONDITIONAL_D_E_DISCOVERY
gate_c_status: GATE_C_PASS
activation_shadow_executed: false
evidence_root: artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_current_actor_operability_acceptance_20260831/
---

# Four-Lane Current Actor Operability Acceptance

## 授權邊界

- Gate A：read-only authority snapshot，已授權。
- Gate C：offline negative tests，已授權。
- 後續 isolated acceptance roots 的七服務 cohort、sealed/deterministic shadow E2E 與 teardown，已授權。
- production queue／ledger／public content、tag／push／deploy、live provider production calls：`false`。
- 本卡不得建立 production canary；Rule25 若被讀取，只能使用 synthetic evidence 且 `canary_created=false`。

## 穩定需求與驗收 ID

| requirement_id | 要求 |
| --- | --- |
| FR-ROUTE | 四 lane routing、identity、isolation、resume、rollback、capacity 契約完整。 |
| FR-ACTOR | 七服務 single actor／generation／digest／token 契約一致。 |
| FR-PUBLISH | Publisher exact plan-only，且不產生 production/public mutation。 |
| FR-ZERO | production/public mutation = 0。 |
| FR-HISTORY | historical releases `v0.3.371`、`v0.3.372`、`v0.3.374`、`v0.3.375` 依 requirement carry-forward。 |
| FR-TEARDOWN | teardown 後 zero residue。 |

## Evidence matrix（固定欄位）

所有 receipt 必須位於 evidence root，且每列固定包含：

`requirement_id,lane,evidence_layer,existing_receipt,dependency_intersection,evidence_disposition,execution_requirement,required_gate,reason_code`

## Sequential frontier

依序執行，任何前 gate fail 即停止：

1. Gate A：authority snapshot。
2. Impact／evidence disposition。
3. Gate C：offline negatives。
4. Capacity／readiness preflight。
5. Gate D/E：同一 isolated cohort 的 activation、shadow、teardown。
6. Gate F：public carry-forward。
7. Gate G：closeout。

### Gate A：authority snapshot

必須分開記錄 `runtime_actor_sha` 與 `acceptance_harness_sha`。唯讀檢查 current live actor、origin／clean 狀態、manifest／runtime identity、generation、roots、registry、ledger、token、barrier、installed services 與 loaded services；不得假定 release 等於 live actor。

### Impact／evidence disposition

逐項將 stable requirements 對應 evidence matrix，標記既有 receipt、dependency intersection、required gate 與 reason code。不得以狀態文案取代 runtime evidence。

### Gate C：offline negatives

wrong lane／mode／identity／manifest／generation、selector zero-many、duplicate locale、ledger lifecycle 等 negative cases 必須在 I/O 前 fail closed，並證明 zero mutation。

### Gate D/E：isolated cohort activation、shadow、teardown

Acceptance roots 是唯一隔離的 queue／state／log／evidence 位置。必須驗證：

- 空 queue 七服務 `7/7 ACK`。
- 唯一 token。
- sealed provider／outbox replay。
- 四 lane 各一 run。
- terminal state。
- 每個 selector 恰好一筆。
- public mutation = 0。
- stop／quiesce 後完成 teardown。

runtime verdict 不得綁架即時模型內容品質；sealed/deterministic evidence 才是本卡 shadow runtime acceptance authority。

### Capacity／readiness preflight

Rule24 capacity／stop-loss 在 activation 前必須 `PASS`；任何 unknown 皆為 `NO-GO`。Rule25 僅 production canary scope，本卡不得建立 canary；任何 readiness 呼叫只能是 synthetic 且明示 `canary_created=false`。

### Gate F：public carry-forward

必須完成 browser-rendered public carry-forward evidence，但不得重新發布或改動 public content。

### Gate G：closeout

必須證明 services、production queue／ledger、public content diff = 0，且無 token／lock residue。teardown drift 立即阻斷 closeout。

## Verdict contract

唯一允許 verdict：

- `GO_FOUR_LANE_RUNTIME_CURRENT`
- `NO_GO_FOUR_LANE_RUNTIME_CURRENT`
- `BLOCKED_<exact_reason>`

production verdict 不在本卡 scope。

## Evidence and path contract

所有 receipts 必須寫入：

`artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_current_actor_operability_acceptance_20260831/`

跨機引用一律使用 repo-relative／`<repo-root>` 路徑，不使用本機絕對路徑。

## Stop conditions

發現任何 production root mutation、provider call、scripts／source defect、authority unknown、capacity unknown 或 teardown drift，立即停止並以 `BLOCKED_<exact_reason>` 記錄；不得繼續後續 gate、建立 canary、deploy 或 production write。
