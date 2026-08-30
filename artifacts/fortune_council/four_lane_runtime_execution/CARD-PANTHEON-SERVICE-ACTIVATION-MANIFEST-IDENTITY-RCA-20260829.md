# CARD：Pantheon Service Activation Manifest Identity Topology RCA

- 卡號：`CARD-PANTHEON-SERVICE-ACTIVATION-MANIFEST-IDENTITY-RCA-20260829`
- 類型：唯讀 root-cause analysis
- 狀態：`RCA_RE_REVIEW_REQUESTED`
- accepted source：`779fb96434c15013d82833788a6795119730daad`
- evidence：`artifacts/fortune_council/four_lane_runtime_execution/pantheon_service_activation_manifest_identity_rca_20260829/`

## Root Question

七服務正式 install／stage／activation 控制面中，promotion manifest identity 與 activation-only identity 為何互斥；last-good／first-bad 在哪一個 commit／mechanism；哪個共同 seam 才是 bounded Repair frontier。

## Production Baseline

- promotion transaction：`COMMITTED` at `779fb96434c15013d82833788a6795119730daad`
- services：`7/7 stopped`
- publisher ledger 與 `rewrite`／`i18n-new`／`i18n-rewrite` lane：unchanged
- Rule24 after：`PASS`
- 上游 blocked receipt：`CARD-PANTHEON-NEW-LANE-CURRENT-PRODUCTION-ACCEPTANCE-20260829/resume-779f-blocked-contract-gap-receipt.json`

## Required Findings

1. 建立七服務 installers、stage writers、activators 的完整 DAG，列出各 edge 讀寫的 manifest／stage／plist authority。
2. 定位 committed promotion manifest identity 的 owner、格式與形成路徑。
3. 定位 activation-only identity 的 owner、格式、writer、validator 與引入時間。
4. 以 commit、receipt、tests 確定 last-good／first-bad。
5. 由證據裁決 durable invariant：單一 canonical activation identity、per-installer stage identity，或明確 lineage mapping。
6. 驗證 publisher、capacity、coordinator、四 lane 是否同樣順序敏感。
7. 建立 production-shaped、provider=0、RED-capable RCA harness；雙跑 deterministic；live bytes before==after。
8. 唯一主因只能是：`INSTALLER_VALIDATOR_OVERREACH`、`PROMOTION_MANIFEST_CONTRACT_GAP`、`ORCHESTRATION_ORDERING_GAP`、`CROSS_VERSION_ACTIVATION_SCHEMA_GAP`；secondary 另列。
9. 提出一次覆蓋七服務共同 seam 的最小 frontier，包含 `why_not_less`、`why_not_more`、`do_not_absorb`。

## Hard Boundaries

- 禁止 source／test／live state mutation。
- 禁止 install／activate／scheduler／provider／Reviewer／Publisher。
- 禁止 commit／push／tag／deploy。
- RCA 只可新增本卡、同名小寫 evidence 目錄與 `RESULT.md`。
- 禁止逐 installer if/else、新 registry／FSM／DB／authority ledger、手改 manifest／stage、繞 validator。
- 資料不足時裁決 `RCA_INCOMPLETE`，不得猜；不得在本卡實作 Repair。

## Acceptance

- CodeGraph-first；不足才限域 `rg`／git history。
- RED harness 實際執行兩次，同一 exact edge fail，輸出 byte 或 canonical digest 相同。
- production snapshot before／after bytes 與 hashes 相同；external call counts 全零。
- `RESULT.md` 交付唯一主裁決、secondary、last-good／first-bad、durable invariant、exact RED、bounded Repair frontier 與 anti-expansion receipt。

## Result

- 唯一主因：`CROSS_VERSION_ACTIVATION_SCHEMA_GAP`
- last-good：`6477ab815e8aecca7d1e8e1588e6e5eba0fab001`／g47／`:activation-only`
- first located bad COMMITTED manifest：`8a50395f67d22343fec4b0a8a5f41c8f40ac360e`／operation-specific identity
- exact RED：正式 coordinator → publisher → capacity 在六 staged plists後，capacity private suffix validator回 `preactivation manifest mismatch`
- production mutation／external calls：`0`
- 完整裁決：`pantheon_service_activation_manifest_identity_rca_20260829/RESULT.md`

## Reviewer Evidence Repair

- `P1-recovery-stage-replay`：closed；exact `--install-recovery-stage`仍命中同一 identity edge RED，雙跑 byte-identical，production bytes unchanged。
- `P1-parent-commit-causality`：closed with timeline correction；`11e6c4c` parent diff證明 opaque promotion producer引入，`29f758f6` parent diff證明 identity check已存在於parent。hard transition check introduction更正為 `35cfdd52`，`29f758f6`僅保留該check並hardening stage validation。
- 主裁決維持：`CROSS_VERSION_ACTIVATION_SCHEMA_GAP`。
