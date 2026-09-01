# C-C/T disposable acceptance cohort

狀態：`PRE_FREEZE_REPAIR_READY`

## 目標

在 isolated acceptance root 建立一次性七服務 acceptance projection 與 teardown seam；只重用既有 manifest、activation barrier/token、service labels 與 runtime entrypoints。

## 依賴 review evidence

- R2：`6897bb5d54a647b005b1422b207039f856ef232c`
- C-A：`1ea615ad4096077a2b82af86a2effb0c487c582d`
- C-B：`fa2e6cb65d5f57209fd3aebb3020246549ce2bc6`

## 邊界

- 僅 local implementation/tests；禁止 commit、push、launchctl、provider、production/public 或 Gate D-E execution。
- 不得改 shared installer、R2/C-A/C-B、pipeline、Publisher production behavior、manifest/routes、queue/registry/public artifacts。
- 不建立 scheduler、daemon、runtime、ledger、FSM、database 或 registry。

## Revised allowlist 與量測缺口

- 可新增 `scripts/pantheon_four_lane_disposable_acceptance_cohort.py`、其 focused test、`RESULT.md` 與 raw output；可最小修改 Coordinator 與其 focused tests。
- 唯一已量測 production seam 缺口：`cycle --exact-run-id` 的 `cycle_once` 在 pending job 存在時仍直接呼叫 imported `process_once`，會與 acceptance 的四 lane worker 競爭。
- 最小修補：只加 `cycle --external-workers-only`，要求 exact run IDs、拒絕 sweep、保留 `_advance`，但任何條件下均不可呼叫 runner process；flag 未開時既有 production path 不變。

## C-C/T projection contract

- renderer 僅產生 isolated acceptance root 下的七份 plist。四 lane child 只用 `sealed-replay-bundle-process-once`；Coordinator child 只用四個 exact run IDs 加 `--external-workers-only`。
- Publisher 自 process start 就是 activation-only，且 child 為 exact selector、`max-runs=1`、無 push；Capacity Guard 僅沿用既有 CLI/label。
- one-shot orchestration 只在 fake launchctl/process tests 做 readiness、token release、bounded wait 與 teardown；不持有 job/candidate/translation/publisher lifecycle。

## 實作結果

- Coordinator 只新增 `cycle --external-workers-only` 的 exact-run seam；flag 未開時不改既有 process 行為。
- renderer 與 tests 僅使用 disposable tmp root 與 injected fake launcher；未執行 launchctl、provider、public/push/deploy 或 Gate D-E。

## Pre-freeze repair

- services 透過既有 barrier-exec 擁有 readiness acknowledgement；controller 只 poll/validate，不注入 ack writer。
- acceptance-owned queue/state/log、plists、ready、barrier、lock、evidence 均須 strict isolated、owner-safe，並與明示 production roots 無 ancestor/descendant overlap。
- session PASS 僅可在 7/7 teardown、residue-free 與 filesystem/service-state fingerprint 前後相等後產生原子 one-shot evidence。

## Preflight acceptance

須先由 mainline 接受 discovered seven-service labels、manifest/barrier/runtime seam 與 exact allowlist，才可改 source。

## Repair verification

- 完整 focused C-C/T + Coordinator seam aggregate：`21 passed, 481 deselected`；既有 manifest/Runner targeted regression：`3 passed`。
- 覆蓋 stale second-run ack、partial readiness、partial launch、bootout failure、unknown residue、atomic projection failure、child argv token mutation、filesystem/service-state drift，以及 evidence 僅在 teardown/fingerprint proof 後寫入。
- 此狀態僅表示可供 pre-freeze independent review；不是 REVIEW_GO，亦非任何 runtime activation 證據。

## Session freshness contract repair

- production proof scope 固定為 `queue`、`ledger`、`publisher`、`public` 四個 exact roots；renderer 在任何 acceptance projection mutation 前拒絕缺漏、額外、unsafe 或 overlap root。
- `session_token` 已移除，shared readiness ack/barrier schema 不變。外部 immutable plan 的 fresh `acceptance-<nonce32>` generation 是唯一 pre-activation session authority；既有 `activation_token_digest` 仍是 post-readiness cohort proof。
- plan 為 owner-safe canonical file 並以 caller pinned SHA256 驗證；嚴格綁 session id/nonce、actor SHA、manifest/identity/generation、ordered seven labels、ordered four runs/bundle digests、Publisher run 與所有 disposable/production roots。render/run 均 revalidate。
- readiness、barrier、lock、evidence、plist projection 都 generation-specific；已存在的同 generation root、ack、barrier、evidence 或 receipt 均 fail closed。PASS receipt 綁 plan path/digest、四 root proof、ack/activation digests、7/7 teardown terminal 與 residue-free proof。
