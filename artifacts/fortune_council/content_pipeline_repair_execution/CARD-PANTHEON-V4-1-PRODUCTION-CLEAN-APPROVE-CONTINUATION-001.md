---
card_id: CARD-PANTHEON-V4-1-PRODUCTION-CLEAN-APPROVE-CONTINUATION-001
status: CARD_DRAFTED
type: production-execution
project: Pantheon
chain_id: pantheon-v4-1-production-clean-approve-continuation-001
owner: production-execution
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 既有 production queue、三把 Gemini key 的 strict round-robin、at-most-once receipt 與唯一一次內容 Repair 正在進行中；錯誤重試或控制面漂移的回退成本高。
created_at: 2026-07-28 Asia/Taipei
source_sha: 3a73e5ac142bb5f676c4ddb13bef0122f5e6e7f8
---

# Pantheon V4.1 Production Clean-Approve Continuation

## Root question

在不重構 allocator、四條 lane 或內容 pipeline 的前提下，從目前 reviewer cutover 後的 live queue 繼續推進，讓既有 New lane Repair candidate 完成唯一一次 targeted re-review，並取得至少一篇可驗證的 clean approve；若 re-review 仍拒絕，依 Repair 上限停止並交回主線。

## Current state snapshot

這是派工前的時間點快照，不是固定數字；執行線開始後必須先重抓 live state：

- `origin/main` 已整合至 `3a73e5ac142bb5f676c4ddb13bef0122f5e6e7f8`。
- coordinator、New、Rewrite、i18n-new、i18n-rewrite 五個 launchd service 均為 loaded。
- live coordinator 的 reviewer override 為 `gemini-3.5-flash`；writer 維持既有 default。
- production allocator pool 為 `pantheon-gemini-v1`，派工前 `last_ordinal=62`。
- queue 快照：
  - New：`outbox=0 / processing=0 / inbox=18 / failed=11 / archive=29`
  - Rewrite：`outbox=1 / processing=0 / inbox=33 / failed=1 / archive=34`
  - i18n-new、i18n-rewrite：皆為空。
- 目標 New run：
  - run id：`auto-new-v1-20260728-003-05`
  - namespace／state id：`d72e63d557dcc2647590d376`
  - run status：`active`
  - 第一次 reviewer job：`e965212f1380832b98e2d0b3039d12bbc474d8e7`
  - 第一次 verdict：`REJECT`
  - findings：`body_length`、`banned_phrase`
  - 唯一一次 Repair writer job：`bf7eaada7b0b4aec8aff7bd5dc4c74acb7784ce9`
  - Repair writer receipt 已在 New inbox／archive，`error_type=null`；尚待 coordinator 消化並進入 targeted re-review。
- 另有其他 New jobs 出現 `API_RATE_LIMITED`；不得把已開始或已失敗的 job 當新 job 重打。
- 舊 reviewer job `96a803b3651d653efe23e9e4740004a8a4b38988` 已隔離，attempt marker 必須保留，永遠不得重試。

## Candidate fork

1. 首選：讓既有 scheduler 自然消化 `bf7eaada…`，產生同一 run 的 targeted reviewer request，再由既有 New lane runner處理。
2. 若 scheduler loaded 但超過兩個正常 tick 仍未推進：只允許對既有 coordinator／New service 使用一次非強制 `launchctl kickstart`；禁止 `-k`。
3. 若 targeted re-review clean approve：保存 candidate、review、run state、queue 與 allocator evidence，交回主線。
4. 若 targeted re-review 再次 REJECT：達到本 chain 的 Repair 上限，停止；不得建立第二次 Repair。
5. 若出現新的 code／contract blocker：只收證據並回報，不在本卡改 code。

## Ownership and allowlist

本卡只擁有 production 執行與證據：

- 透過既有 service 推進 `<main-cwd>/.work/gemini-runner/**`。
- 讀取並由既有 pipeline 更新 `<main-cwd>/.work/gsc-copy/auto-new-v1-20260728-003-05/**`。
- 對既有 coordinator／New service執行必要且非強制的 `launchctl kickstart`。
- 新增本卡 evidence：
  `artifacts/fortune_council/content_pipeline_repair_execution/evidence/production_clean_approve_continuation_001/`

除 evidence 外，不得新增或修改任何 tracked code、config、workflow、文章 registry、metadata、sitemap、feed、redirect 或 shared integration file。

## Forbidden scope

- 不修改 allocator、runner、coordinator、outbox、pipeline 或四條 lane 架構。
- 不修改 launchd plist，不重新安裝 service，不切換 writer／reviewer model。
- 不讀出、記錄、複製或輸出任何 API key；只允許既有 runner 使用既有 credential pool。
- 不對三把 key 做額外 probe；只觀察 natural queue allocation。
- 不重試 `96a803…`，也不重試任何已有 started attempt marker 的 job。
- 不刪除、覆寫或截短 queue、attempt marker、receipt、archive、inbox、failed、quarantine 或 allocator state。
- 不手動竄改 run `updated_at`、status、job id、verdict 或 review artifact。
- 不使用 `launchctl kickstart -k`。
- 不 commit 任何 live `.work` 狀態、key、receipt payload 或可能含敏感資料的原始 log。
- 不 push、merge、deploy、publish 或修改 `main`；只交付 evidence commit。
- 不開第二次 Repair，不降低 deterministic/reviewer gate。

## External action authorization

使用者已明確授權：

- 既有三把 Gemini API key 依 strict round-robin 處理 natural production queue。
- 既有五個 production service 持續執行。
- 在本卡邊界內，必要時非強制 kickstart 既有 coordinator／New service。

此授權不包含新 key、新模型、額外 probe、手動 publish、GitHub push／merge、deploy 或其他外部控制面變更。

## Required execution

1. 驗證正式 thread 使用獨立 worktree；不得等於 `<main-cwd>`。
2. 執行：
   `bash ${AI_CORE_DIR:-$HOME/ai-core}/scripts/worktree_capability_preflight.sh --check --root <worktree-root>`
3. 重抓 live service、reviewer model、queue count、目標 run、Repair receipt 與 allocator safe projection。
4. 確認 `bf7eaada…` 只有成功 receipt，沒有重複 attempt 或 processing copy。
5. 讓既有 scheduler 推進；只有命中 Candidate fork 2 才做一次非強制 kickstart。
6. 驗證 targeted reviewer job 的：
   - role
   - model
   - new job identity
   - inbox／archive 或 failed outcome
   - 無舊 job replay
7. 若 clean approve，驗證 final candidate／review／run state 一致；若 REJECT 或 external failure，依 stop conditions 收斂。
8. 產生不含 secrets 的 evidence summary，commit 後交付完整 SHA。

## Verification and acceptance

最低驗證：

- 五個 service loaded 狀態與 exit evidence。
- coordinator plist safe projection：只證明 reviewer override，不能輸出 secrets。
- queue before／after counts。
- allocator `pool_id`、`last_ordinal` 與安全的 account slot 統計；不得輸出 credential payload。
- `d72e63d557dcc2647590d376` run state before／after。
- attempt 01 review、attempt 02 writer receipt、targeted re-review artifact 的 hash 或安全摘要。
- `96a803…` 不存在於 outbox／processing，且 attempt marker／quarantine evidence 仍存在。
- evidence worktree `git diff --check`、`git status --short`。

Acceptance 為以下二者之一：

- `GO`：目標 run 或另一個自然 New run 產生可驗證 clean approve，沒有重播舊 job、沒有第二次 Repair、allocator receipt invariant 未破壞。
- `BOUNDED_STOP`：targeted re-review 再次 REJECT，或遇到新的 external／contract blocker；完整保存證據並停止，沒有越過 Repair／重試上限。

不得以 service loaded、單次 writer success、單次 reviewer API success或 queue count 下降單獨宣稱 clean approve。

## Evidence and delivery

Evidence path：
`artifacts/fortune_council/content_pipeline_repair_execution/evidence/production_clean_approve_continuation_001/`

交付：

- root question、current blocker、candidate fork
- before／after safe snapshot
- targeted run／job lineage
- review／Repair 次數與最終 verdict
- allocator與 queue evidence
- stop condition 是否命中
- 完整 evidence commit SHA
- 狀態只能是 `DELIVERED_CANDIDATE`；主線負責 `ACCEPTED`。

## Stop conditions

- 同一 blocker 累計失敗 3 次，第 3 次立即停止，不做第 4 次。
- targeted re-review 再次 REJECT，立即 `BOUNDED_STOP`，不得第二次 Repair。
- 任一已 started job 出現重試需求時停止；不得重送。
- allocator receipt、pool manifest、attempt marker 或 queue identity 不一致時停止。
- 需要 code／config／plist／model／key／GitHub／deploy 變更時停止並回主線。
- 無法在不輸出 secrets 的前提下保存證據時停止。

## Dispatch receipt

- provisioning source SHA：待 card commit 後鎖定
- source branch/ref：`origin/main`
- source clean：待驗證
- Git metadata／index lock：待驗證
- unrelated dirty paths：待驗證
- formal thread ID：PENDING
- title：`Pantheon｜Production Clean Approve｜CARD-PANTHEON-V4-1-PRODUCTION-CLEAN-APPROVE-CONTINUATION-001`
- worktree cwd／exists／clean：PENDING
- model：`gpt-5.6-sol`
- reasoning：`high`
- Gate 1 card contract：PASS
- Gate 2 visible thread：PENDING
- Gate 3 candidate delivery：PENDING
- Gate 4 independent review：N/A（純 production 執行卡；code/config 變更禁止）
- Gate 5 mainline acceptance：PENDING
- workflow：`CARD_DRAFTED`
