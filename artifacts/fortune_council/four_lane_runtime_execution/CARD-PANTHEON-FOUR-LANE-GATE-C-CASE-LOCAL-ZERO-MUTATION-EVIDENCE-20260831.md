---
id: PANTHEON-FOUR-LANE-GATE-C-CASE-LOCAL-ZERO-MUTATION-EVIDENCE
parent: PANTHEON-FOUR-LANE-IMPACT-MATRIX-AND-CROSS-LANE-NEGATIVE-GATE
type: test-only-acceptance-slice
status: ready-after-impact-matrix
root_blocker: EXACT_8_GAPS_FROM_GATE_C_COVERAGE_AUDIT
production_activation_authorized: false
shadow_execution_authorized: false
---

# Gate C case-local zero-mutation evidence

## 目的與邊界

補齊 Gate C coverage audit 鎖定的八個 negative gaps，證明每個 case 在 I/O 前以 exact rejection reason fail closed，並保存 case-local immutable before/after evidence。這不是產品修正任務；任何現行 behavior 若真的 mutation，必須分類為 `BASELINE_PRODUCT_DEFECT`／`BLOCKED_GATE_C_PRODUCT_DEFECT`，不可放寬 assertion 或修改 script。

## Allowed／forbidden

只允許修改：

- `tests/test_agy_gemini_coordinator.py`
- `tests/test_agy_multilingual_pipeline.py`
- `tests/test_agy_content_publisher.py`
- 本卡與唯一 result receipts（repo-local evidence root）

禁止修改或執行：

- `scripts/**`、production/runtime source、activation/shadow。
- provider/network、public content、production queue/ledger、launchctl、service。
- 任何非 temporary/private test root。

## Eight exact gaps

每個 gap 都必須有獨立 exact node ID、expected rejection reason、case-local before/after snapshot 與 trace：

1. wrong worker。
2. wrong mode。
3. wrong manifest。
4. wrong generation。
5. selector zero match。
6. selector many match。
7. duplicate locale。
8. ledger conflict／lifecycle conflict。

## TDD and evidence contract

1. 先寫或鎖定 RED-capable assertions，確保 invalid input 預期在任何 I/O 前拒絕。
2. 每個 case 進入前保存 queue、state、ledger、registry、runtime roots 的 immutable digest/snapshot；in-memory case 保存 object identity/spy counters。
3. 執行 exact negative case，捕捉 exact exception/reason code 與 I/O spy。
4. 執行後再次 snapshot；純讀 selector/ledger case 要求 queue/state tree equality，in-memory case 要求 spy/no-write evidence。
5. 若現行 behavior 修改任何 generation state（尤其 `state=failed`）或其他 durable artifact，立即標記 `BASELINE_PRODUCT_DEFECT`／`BLOCKED_GATE_C_PRODUCT_DEFECT`，保留 RED；不得將 mutation 改寫成通過條件。
6. 正向或既有 baseline 不得藉此卡放寬 strict validation、legacy compatibility 或 authority boundary。

## Required case assertions

每一 negative case 必須明確證明：

- input identity、lane、mode、manifest、generation、selector 或 locale/ledger conflict 的 exact drift。
- rejection 發生於 first I/O 前（以 spy/call log 或 equivalent evidence 證明）。
- expected exception／reason code 精確匹配，不接受寬泛錯誤訊息。
- before 與 after snapshot 完全相等；任何不相等即 product defect/blocker。
- provider calls、service calls、production mutation 均為 0。

## Existing harness and exact execution

只使用既有 coordinator、multilingual pipeline、content publisher private test harness；不得新增第二套 harness。先以 CodeGraph 定位 existing implementation/test seam，若無結果才限域 `rg`；隨後 freeze exact Gate C node IDs。

Fresh process 必須執行：

- 八個 case-local negative groups。
- impact matrix 規定的既有 Gate C exact manifest。
- 相關正向/legacy control cases（僅用於確認 negative isolation）。

禁止 skip、xfail、waiver。保存 raw pytest outputs、collect manifest 與每 case receipt；不得以 broad selector 取代 exact node IDs。

## Pass／block contract

只有全部成立才可標記 `GATE_C_CASE_LOCAL_ZERO_MUTATION_PASS`：

- 八個 gaps 均有 RED-capable assertion 與 exact node ID。
- 所有 invalid cases 在 first I/O 前 fail closed。
- 所有 queue/state/ledger/registry/runtime snapshots before==after。
- in-memory I/O spies 全為 zero write/call；provider/service/production mutation = 0。
- 無 `BASELINE_PRODUCT_DEFECT`、`BLOCKED_GATE_C_PRODUCT_DEFECT` 或其他 related failure。
- fresh exact manifest raw output 完整，無 skip/xfail/waiver。
- independent review 完成。

任何 mutation、state failed durable write、authority unknown、missing exact reason、provider/service call 或 related failure，立即 `BLOCKED_EXACT_<reason>`；不得修 script、重試或以 assertion 放寬洗白。

## Evidence and traces

所有 result receipts 必須位於 umbrella evidence root 的 case-local 子目錄，至少包含：case ID、exact node ID、input drift、before digest、after digest、exception/reason、I/O spy、provider/service/production counters、raw output path 與 verdict。

- `TR-C-001`：wrong worker/mode pre-I/O rejection。
- `TR-C-002`：wrong manifest/generation pre-I/O rejection。
- `TR-C-003`：selector zero/many exact rejection。
- `TR-C-004`：duplicate locale exact rejection。
- `TR-C-005`：ledger conflict/lifecycle exact rejection。
- `TR-C-006`：case-local immutable before/after snapshot equality。
- `TR-C-007`：in-memory I/O spy zero-write evidence。
- `TR-C-008`：product defect classification and fail-closed stop。
- `TR-C-009`：fresh exact Gate C manifest and raw outputs。
- `TR-C-010`：independent review before PASS。

## Why not less / why not more / do not absorb

- `why_not_less`：只補 exception assertion 或只驗 queue，無法證明 first-I/O rejection 與 state/ledger/registry zero mutation。
- `why_not_more`：本 slice 僅補 case-local tests/evidence，不改 production behavior、不建立新 harness、不進 activation/shadow。
- `do_not_absorb`：不吸收現行 product mutation、不吸收 waived failure、不把 durable `state=failed` 視為 harmless、不以 broad selector 或狀態文案取代 raw evidence。

## Sequential placement

本卡是 umbrella sequential slices 中的 Gate C case-local slice；只有 `GATE_C_CASE_LOCAL_ZERO_MUTATION_PASS` 且 independent review 完成，才可交回 impact matrix owner 判定 Gate C overall verdict。不得自行宣告 umbrella GO。
