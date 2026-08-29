# CARD：Pantheon Service Activation Shared Identity Contract Bounded Repair

- 卡號：`CARD-PANTHEON-SERVICE-ACTIVATION-IDENTITY-CONTRACT-REPAIR-20260829`
- 類型：唯一 bounded Repair
- 狀態：`RE_REVIEW_REQUESTED`
- base／origin：`779fb96434c15013d82833788a6795119730daad`
- evidence：`pantheon_service_activation_identity_contract_repair_20260829/`

## 目標

恢復 runtime manifest 既有 opaque identity contract，只移除 capacity 私有 suffix語義，讓 operation-specific identity 在正式 recovery-stage 路徑合法，同時維持 actor_head、digest、mode/stage/barrier drift fail closed。

## Locked RCA

- 主因：`CROSS_VERSION_ACTIVATION_SCHEMA_GAP`。
- `11e6c4c` 引入 caller opaque `target_identity` passthrough。
- `35cfdd52` 引入 capacity 私有 `:activation-only` transition check；`29f758f6` 保留並強化 stage validation。
- exact recovery-stage RED：coordinator install → publisher install → capacity install-recovery-stage，在六個 staged plist 後回 `preactivation manifest mismatch`。

## Strict Fact Gate

- 受影響 public seam：`runtime_manifest.build_manifest`／`load_manifest`回復parent行為；`capacity_guard.validate_preactivation_transition`與`_activation_only_service_labels`移除私有identity語義。
- identity schema：既有 nonempty、trimmed opaque correlation；actor authority為separate `actor_head`與兩層digest；mode authority為explicit args與plist/stage/live topology。
- 既有 authority保持：manifest digest、barrier、stage/live tuple、Rule24 receipt、normal/recovery mode與 aggregate fail-closed checks。
- 呼叫者：6個正式producer、14個load consumers；除capacity外沒有consumer從identity推導actor或mode。
- rollback：只回退本卡 allowlist diff；不觸碰任何 live state。

## DESIGN_GO Revision Plan

1. 完整撤回 shared actor-prefix parser與配套legacy identity改寫；驗證 opaque `g8-live`／`g8-staged`＋separate actor_head合法。
2. capacity只移除 suffix rejection與unreadable-plist identity fallback；驗證 operation-specific recovery GREEN且digest/barrier/stage/wrong-mode仍RED。
3. 跑 targeted、promotion、affected11與parent完全相同廣域selection；只有 failure node set與normalized digest exact identical才可交付。

## Allowlist

- `scripts/pantheon_content_runtime_manifest.py`
- `scripts/pantheon_content_capacity_guard.py`
- `tests/test_pantheon_content_runtime_manifest.py`
- `tests/test_pantheon_content_capacity_guard.py`
- 本卡與 `pantheon_service_activation_identity_contract_repair_20260829/`

Source＋test changed LOC上限 `220`。禁止 promotion/coordinator/publisher source、queue/registry/ledger、FSM/DB/migration、live manifest/stage/plists。

## TDD Acceptance

1. 保存 exact operation-specific recovery-stage RED。
2. runtime manifest維持nonempty/trimmed opaque identity與separate actor_head/digest validation。
3. capacity移除私有 suffix rejection與unreadable-plist identity fallback；mode只信explicit args與topology。
4. exact recovery-stage fixture GREEN；mode/stage/barrier drift仍RED；capacity-first bypass不得列為正式成功。
5. 跑兩個 targeted files、promotion suite、coordinator/install/aggregate suites、py_compile、diff-check、LOC與anti-expansion scan。
6. production/live/provider/reviewer/publisher mutation `0`；狀態交付 `RE_REVIEW_REQUESTED`。

## 交付

- 裁決：`RE_REVIEW_REQUESTED`
- 結果：[`RESULT.md`](pantheon_service_activation_identity_contract_repair_20260829/RESULT.md)
- evidence index：[`EVIDENCE.md`](pantheon_service_activation_identity_contract_repair_20260829/EVIDENCE.md)

## Hard Stops

- changed LOC超過220、需要第三個source、或 exact RED不是指定edge：`BLOCKED`。
- 不 commit／push／promotion／install／activate。
