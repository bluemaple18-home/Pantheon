# CARD-PANTHEON-COORDINATOR-LANE-OWNERSHIP-REVIEW-V2-20260818

## 工作名稱

獨立審查 Coordinator lane ownership candidate

## 目的

以唯讀 Reviewer 身分審查 candidate `89966ec28b9cd042c5f0d1d5da8db34f7c1c8d46` 相對 base `d6525d6616cec69fd9b45798ee7aba86f8ec8879` 的變更，確認 missing brief fail-closed、immutable routing authority、legacy migration 與既有相容性是否成立。

## Review 邊界

- 主要 diff 只包含：
  - `scripts/agy_gemini_coordinator.py`
  - `tests/test_agy_gemini_coordinator.py`
  - `.work/CARD-PANTHEON-COORDINATOR-LANE-OWNERSHIP-RECOVERY-V2-20260818/evidence.md`
- 唯一可寫輸出：`.work/CARD-PANTHEON-COORDINATOR-LANE-OWNERSHIP-REVIEW-V2-20260818/review/`
- 不得修改 candidate、source、tests、Publisher、Node、prerender、capacity guard、runtime、launchd、queue、transaction、文章或 production。
- 不得整合、push、部署、啟動服務或建立 replacement。

## 必查問題

1. 新 state 是否只信持久化的 `routing_schema_version`、`mode`、`lane`，不再被 mutable 或 missing `brief.json` 影響。
2. legacy state migration 是否只在可確定 lane 時原子寫回，invalid／missing state 是否保留原狀且不搬錯 outbox。
3. `_lane_for_state_or_none` 的例外吞噬範圍是否過寬，會不會遮蔽應阻斷的資料損壞或 I/O 問題。
4. `register_run` 對 translation 無 lane hint 的相容策略是否會讓新 run 永久停留 legacy／unroutable。
5. cycle summary、selection、migration 與 new-only path 是否一致 fail-closed，且不會造成 starvation 或假 active count。
6. 新測試是否真正覆蓋 state persistence、legacy migration、missing brief、invalid routing、outbox preservation。
7. candidate 的完整單檔 pytest `153 passed / 41 failed` 是否可在 base 重現；不得僅依實作者口頭歸因。

## 驗證

- 讀 `git diff d6525d6616cec69fd9b45798ee7aba86f8ec8879 89966ec28b9cd042c5f0d1d5da8db34f7c1c8d46`。
- 重跑 candidate focused tests。
- 以隔離暫存 worktree 或等價安全方式，在 base 與 candidate 比對完整單檔 pytest；至少記錄 exact failing test names 與兩邊差集。
- 執行 `git show --check 89966ec28b9cd042c5f0d1d5da8db34f7c1c8d46`。
- 輸出 findings 時需含 severity、path:line、觸發條件、證據、風險、建議修法、validation gap、confidence。

## 停止條件

- 若 candidate 新增 P0/P1、測試差集無法證明、或需改禁止範圍，回 `REQUEST_CHANGES` 並停止。
- 若無阻塞 finding，回 `ACCEPT_WITH_RESIDUAL_RISK`，列出 41 failures 的 baseline 證據與剩餘風險。
- Reviewer 不得自行修 code。

## 交付格式

- verdict
- findings（依嚴重度排序）
- base／candidate test comparison
- changed-file boundary
- residual risks
- review evidence 路徑
