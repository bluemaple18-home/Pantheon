# CARD：Pantheon `new` Lane Current Production Acceptance

- 卡號：`CARD-PANTHEON-NEW-LANE-CURRENT-PRODUCTION-ACCEPTANCE-20260829`
- 類型：bounded production acceptance
- 狀態：`BLOCKED_CONTRACT_GAP`
- 工作線：`new`
- execution line：單一、序列執行

## 目標

以 production 正式入口，對 accepted runtime source `bde44589f3785aae738bb7d7b1626270ba5505d0` 的 `new` lane 唯一 fresh exact run 完成 Writer → deterministic validators → formal Reviewer → Publisher → release transaction → annotated tag → atomic push → deploy → public browser acceptance。

若不存在唯一且合法的 eligible run，裁決 `MISSING_ELIGIBLE_CANDIDATE`，production 保持不變。

## 邊界

- 只允許一個 `new` lane exact run。
- 允許該 run 必要的 production state mutation、provider Writer 一次、formal Reviewer 一次、Publisher execute 一次、release commit／annotated tag／atomic push／deploy 一次。
- 若 runtime source 需要 promotion，只允許先驗 manifest digest，再依正式入口 `plan → apply → finalize` 將 remote main 的正式可 promotion source 提升為 actor。
- 不修改 source code，不開 Repair／RCA，不碰 `rewrite`、`i18n-new`、`i18n-rewrite`。
- 不重用歷史 active／failed residue 或已被 ledger 消耗的 candidate。

## 前置條件

- immutable snapshot 已保存。
- Rule24 host-telemetry normalized `PASS`。
- Rule25 official gate `READY`。
- deployment preflight `PASS`。
- fresh read-only 核對 `origin/main`、release tag、runtime actor、manifest 與 digest。
- selector 唯讀結果恰為一個 current eligible `new` run／article。

## 驗收流程

1. 以正式 selector 鎖定唯一 exact identity，不從多候選猜選。
2. 只用正式 entrypoints 完成 Writer、deterministic validators、formal Reviewer。
3. Reviewer 非 `APPROVE` 時立即 terminalize 並停止，不做內容 Repair。
4. Publisher 先以 exact identity dry-run；必須 exactly one。
5. Publisher execute 最多一次，使用 frozen first-free release namespace。
6. release tests 通過後，建立 commit、annotated tag、atomic push 並 deploy。
7. canonical public URL HTTP `200`；Playwright 在 `page.goto()` 前掛 console、pageerror、requestfailed listeners，驗證 rendered title、H1、unique body sentinel 可見，console warning/error 為 `0`；raw shell 與 rendered DOM 分欄保存。
8. production ledger、run、public URL 各自且彼此 identity 唯一。

## Stop Conditions

- actor／source／manifest／digest／correlation identity drift。
- Rule24、Rule25 或 deployment preflight 非綠。
- selector 為零或多個候選；零候選裁決 `MISSING_ELIGIBLE_CANDIDATE`。
- 需要第二次 provider call、第二個 candidate、第二次 Publisher execute。
- Reviewer 非 `APPROVE`。
- Gen／queue 異常或重用歷史 residue。
- publish attempt 失敗。
- public canonical／rendered body 驗收失敗。

## 證據與交付

- Evidence directory：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-NEW-LANE-CURRENT-PRODUCTION-ACCEPTANCE-20260829/`
- Final receipt：上述目錄的 `RESULT.md`
- 結果必須明列操作次數、final identities、release commit/tag、公開 URL、raw transport 與 rendered DOM、ledger/run/public unique accounting，以及未聲稱事項。
