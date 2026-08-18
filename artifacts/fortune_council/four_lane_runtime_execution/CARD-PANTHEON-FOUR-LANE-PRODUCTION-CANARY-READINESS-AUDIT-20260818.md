# CARD-PANTHEON-FOUR-LANE-PRODUCTION-CANARY-READINESS-AUDIT-20260818

## 工作名稱

四線 Production Canary Readiness 唯讀驗收

## Root Question

目前 main `1fffc42a5039ed460982c963536cc9cca529856c` 與既有 production 狀態，是否已有足夠證據允許後續另行申請四線 canary？

## 任務性質

- 唯讀診斷與 evidence validation。
- 不建立 canary，不部署，不重啟，不 reload，不寫 production queue／transaction／registry／article。
- 只允許在 `.work/CARD-PANTHEON-FOUR-LANE-PRODUCTION-CANARY-READINESS-AUDIT-20260818/` 寫報告與驗證輸出。

## 必讀

- `handoff_20260817_pantheon_writer_vnext_four_lane_recovery.md`
- `artifacts/fortune_council/four_lane_runtime_execution/coordinator_publisher_causal_rca_20260818/rca.md`
- `artifacts/fortune_council/four_lane_runtime_execution/publisher_recovery_rewrite_acceptance_20260817/readiness-package/production-canary-capability-receipt.json`
- `artifacts/fortune_council/four_lane_runtime_execution/publisher_recovery_rewrite_acceptance_20260817/readiness-package/capacity-proof-normalized.json`
- `<ai-core-root>/rules/24-storage-capacity-safety.md`
- `<ai-core-root>/rules/25-production-canary-readiness.md`

## Capability Gate

逐步驗證 `create → run → select → publish → transaction → tag → push`：

- production 正式入口存在且仍是 current authority。
- I/O 可串接。
- identity／execution_line_id／correlation_id 全鏈一致。
- 每步各有獨立 PASS 正向 artifact。
- 每步各有獨立 BLOCKED fail-closed artifact。
- `transaction`、`tag`、`push` 分開證明。
- `canary_created=false`。
- 使用正式 readiness gate 驗 receipt；不得手改 verdict。

## Freshness／Drift Gate

- 比對 receipt 的 source SHA、script digest、runtime identity、manifest authority 與 main `1fffc42a5039ed460982c963536cc9cca529856c`。
- 比對 production／launchd／runtime 的現況只能唯讀。
- Coordinator 修補 commits `b711184af27a8624410704f3c086b9150fd2a517`、`db74e966b4ac67d6a4b2acd14b8e8729a339b467` 若未被既有 receipt 覆蓋，必須判定 stale／BLOCKED；不得推論等價。

## Capacity Gate

- 驗證既有寫入盤點、容量預算、兩週期試跑、峰值推估、回收、停損、host reserve、RSS／swap 證據。
- 驗證 capacity proof 與 current runtime／main 是否同一版本與身份。
- 缺 current evidence 一律 `NO-GO`。
- 本卡不得自行執行會寫資料的代表性試跑、清理、停損或 production 操作。

## Dispatch Resource Receipt

- sampled_at: `2026-08-18T01:10:43Z`
- status: `PASS`
- reason: `CAPACITY_WITHIN_BUDGET`
- snapshot_digest: `bb1a1993713dbf6e376c2e3c84fd848f6e89fdb55d57fee7ee042f55d57b31e5`
- precreate_receipt_digest: `8ca96291e4e23f1416df5c1df4756fb6ab96c9ee0b24a0ce439976b24f390c3d`
- projection: `159371264` bytes, sample_count `9`, error `48234496` bytes
- post-create projection: `17` worktrees／`3731103744` bytes／`2` active threads

## 驗收輸出

- capability verdict：`READY` 或 `BLOCKED`
- capacity verdict：`PASS` 或 `NO-GO`
- overall：只有兩者皆通過才是 `READY_FOR_SEPARATE_PRODUCTION_APPROVAL`；否則 `NO-GO`
- 列 exact blocker、stale artifact、缺證據、可重現 command、下一張單一修補卡範圍。
- 不得以此卡授權 production。

## 停止條件

- 任一 artifact 缺失、digest／identity／correlation 不一致、版本 stale、gate 非 READY／PASS：立即收斂為 `NO-GO`。
- 不得為了取得 PASS 建立 canary 或改 production。
