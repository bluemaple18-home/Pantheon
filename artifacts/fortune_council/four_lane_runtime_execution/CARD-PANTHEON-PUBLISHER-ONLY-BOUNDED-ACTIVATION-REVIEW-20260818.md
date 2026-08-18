---
id: CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-REVIEW-20260818
chain_id: PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-20260818
parent_card_id: CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-20260818
role: reviewer
cycle: 1
status: ready
type: review
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 固定 candidate 的 production LaunchAgent、barrier、rollback 與 runtime identity 高影響審查；規格已鎖定，使用 GPT-5.5 high，不使用 5.6。
review_base_sha: 1db9b8a1edd689e5c8cfecc407f51d6da8351cd5
candidate_sha: 482ae14d90d9b632e2cfa705e1fac00ffc3bc651
ownership:
  - .work/CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-REVIEW-20260818/**
forbidden_scope:
  - 修改 candidate、source、tests、rules、卡片或 production runtime
  - production activation、runtime promotion、LaunchAgent reload、發布、tag 或 push
  - 修 code、另開 Repair／Reviewer task、擴大到 Writer、lane、queue、文章或 Publisher selection semantics
verification:
  - 固定比較 review base 與 candidate SHA，檢查完整 diff、實作 evidence 與實際測試
  - 驗證 Publisher-only 路徑在任何 live mutation 前完成 bounded contract、aggregate activation-only、matching barrier 與 drift preflight
  - 驗證成功路徑只重啟 Publisher，其他六服務 plist bytes 與 launch identity 不變
  - 驗證 rollback 能恢復原 Publisher plist／loaded state，且不掩蓋 rollback failure
  - 獨立重跑目標測試、受影響回歸、bash -n、git diff --check
evidence_path: .work/CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-REVIEW-20260818/
---

# Publisher-only bounded activation independent review

## 工作名稱 → 正在做什麼 → 現在狀態

獨立審查 Publisher-only bounded 啟動 → 固定 SHA 驗證 correctness、regression、rollback 與 test gap → `READY / REVIEW ONLY`

## Root Question

Candidate `482ae14d90d9b632e2cfa705e1fac00ffc3bc651` 是否以最小、fail-closed 且可回退的正式入口，只把 Publisher 從 aggregate activation-only 切到 `max-runs=1` normal，而不改動或重啟其他六服務？

## Review boundary

- Base：`1db9b8a1edd689e5c8cfecc407f51d6da8351cd5`
- Candidate：`482ae14d90d9b632e2cfa705e1fac00ffc3bc651`
- 主要檔案：兩支 installer、runtime manifest、兩支測試與 implementation evidence。
- Reviewer 只判定，不修 code。只有 P0/P1 或 production safety risk 可 `REVIEW_NO_GO`；P2/P3 記 residual risk。

## 必查風險

1. `--activate-publisher-only` 是否先驗 staged receipt、Publisher plist、七服務 live activation-only、matching barrier，再進任何 backup／install／bootout／bootstrap。
2. `max-runs=1` 與 optional exact-run 是否從 stage artifact 到 plist child args 完整綁定，不能被 stale file、遺留 exact-run 或環境 drift 繞過。
3. 成功路徑是否只修改 Publisher target plist／service；其他六服務的 plist bytes、loaded identity、PID／launch state 不得被替換或重啟。
4. `bootout` 失敗、bootstrap 失敗、postcheck 失敗與 concurrent drift 時，rollback 是否恢復原 Publisher plist與原 loaded/unloaded state；rollback failure 必須可見。
5. stage cleanup、backup 路徑、failure receipt 與既有 aggregate `--activate`／`--activate-only` 是否互不破壞。
6. 新 `publisher-plist` manifest command 是否嚴格驗 label、manifest identity、normal mode、child command、唯一 `--max-runs 1`、exact-run 格式與重複參數。
7. 測試是否真的觀察 launchctl mutation／child I/O／其他六服務不變，而不是只比對字串或 mock 自證。
8. Implementation 報告的完整 Coordinator `196 passed, 5 failed` 是否確為 candidate-independent 既有 backlog；若無法證明則不得當作無關。

## Review procedure

1. 先確認 HEAD 包含 candidate、base/candidate objects 可讀、worktree clean、card 可讀。
2. 用 CodeGraph 查影響面；未初始化才限域 `rg`。
3. 讀完整 diff與 evidence，依 correctness、regression、release/runtime identity、test-gap 視角審查。
4. 獨立跑目標測試與必要負向 case；不得碰 production。
5. 輸出 finding schema：severity、category、path、line、evidence、risk、suggested_fix、validation_gap、confidence。
6. verdict 只能 `REVIEW_GO` 或 `REVIEW_NO_GO`。NO-GO 必須列穩定 finding IDs；GO 必須列 residual risks與 production canary 必驗項。

## 停損與交付

- 同一 blocker第三次停止。
- 不得因 Reviewer 發現問題直接修；交回主線建立唯一 Repair 線。
- 交付 review verdict、reviewed base/candidate SHA、finding matrix、commands/results、production mutation=`0`、evidence path與 review evidence commit SHA。
