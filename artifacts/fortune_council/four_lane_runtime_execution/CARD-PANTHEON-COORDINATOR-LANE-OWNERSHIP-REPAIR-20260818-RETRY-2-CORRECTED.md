---
id: CARD-PANTHEON-COORDINATOR-LANE-OWNERSHIP-REPAIR-20260818-RETRY-2-CORRECTED
status: ready
type: implementation
chain_id: PANTHEON-COORDINATOR-PUBLISHER-RECOVERY-20260818
role: implementation
cycle: 1
thickness: strict
risk: core-bounded
model: gpt-5.5
reasoning: high
model_reason: 兩次 create 均未形成正式 task/worktree；RCA 與核心 state ownership 契約不變，依三次停止規則做最後一次正式建立。
owner: visible-thread-implementation
ownership: Coordinator lane-routing state contract only
mainline_acceptor: current-main-thread
supersedes: CARD-PANTHEON-COORDINATOR-LANE-OWNERSHIP-REPAIR-20260818-RETRY-2
evidence_path: .work/CARD-PANTHEON-COORDINATOR-LANE-OWNERSHIP-REPAIR-20260818-RETRY-2-CORRECTED/
---

# Coordinator lane ownership contract repair — Retry 2 corrected

## 工作名稱 → 正在做什麼 → 現在狀態

Coordinator lane ownership repair → 固化 lane/mode routing authority，避免缺 brief 拖垮整輪 Coordinator → `READY / FINAL REPLACEMENT AUTHORIZED`

## Replacement receipt

- 原卡 create 只形成內部 Guardian rollout，沒有正式 task、client thread、Pantheon worktree 或 code 變更。
- `RETRY-1` create 立即回傳平台錯誤；事後核對沒有正式 thread、client ID、Pantheon worktree 或 code 變更。
- `RETRY-2` 在 create request 形成前因 task intro 超過 50 字由本地 gate 終止；沒有呼叫平台、thread 或 worktree。本卡只修正派工 identity 與摘要長度，不增加平台重試次數。
- 使用者持續要求「繼續」，授權本次最後一個 `RETRY-2`。
- repo／chain／role／cycle、模型、風險與修復範圍全部不變。
- 建立前將 `RETRY-1` 標記 `SUPERSEDED`；不得再 activation 或重送舊卡。
- 本次若再遇相同 create blocker，即達第三次，必須停止，不得建立 `RETRY-3`。

## Root question 與 RCA

必讀：

- `artifacts/fortune_council/four_lane_runtime_execution/coordinator_publisher_causal_rca_20260818/rca.md`
- 原卡 `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-COORDINATOR-LANE-OWNERSHIP-REPAIR-20260818.md`

已證明：`_migrate_pending_jobs` 對缺 `<run_dir>/brief.json` 的 active state 呼叫 `_lane_for_state`，直接拋出 `ValueError("active run brief is unavailable")`，使整個 Coordinator cycle 退出。Node scan 只是 amplifier；capacity guard 是正確後果；Publisher recovery 不屬本卡。

## 可改範圍

- `scripts/agy_gemini_coordinator.py`
- `tests/test_agy_gemini_coordinator.py`
- `.work/CARD-PANTHEON-COORDINATOR-LANE-OWNERSHIP-REPAIR-20260818-RETRY-2-CORRECTED/`

其他檔案一律唯讀。不得修改 Publisher、SEO pipeline、prerender、capacity guard、runtime、launchd、queue data、transaction 或文章生成物。

## 必做契約

1. `register_run` 從已驗證 brief 推導並原子持久化版本化、immutable `mode` 與 canonical `lane`，保留既有 run/correlation identity 與 idempotency。
2. `_lane_for_state` 對新版本 state 只信 state；驗證 mode/lane pair，未知或衝突值 fail-closed，不得以可變 brief 靜默覆寫。
3. legacy state 缺 routing fields：
   - brief 可讀且合法時，允許一次明確、可測、原子的 state migration；
   - brief 不可讀時，不得 crash 整個 cycle、猜 lane、刪 state 或搬 outbox；產生穩定 quarantined/unroutable outcome，其他可路由 lane 仍能前進。
4. 保持四 lane oldest-first、shared pending namespace、retry/terminal 與既有 schema 相容。

## RED→GREEN

- missing brief state 不使 `_migrate_pending_jobs`／`cycle_once` crash，且其 outbox 不被移動；其他可路由 state 可繼續。
- 四 lane 新 state 均持久化正確 mode/lane 並可 migration。
- immutable state 與 brief 衝突不得被 brief 覆寫。
- unknown version/lane、invalid mode/lane pair fail-closed。
- 既有 register idempotency、private path、brief size、lane ordering tests 維持通過。

至少執行：

```text
uv run --frozen python -m pytest tests/test_agy_gemini_coordinator.py -q
git diff --check
```

不得安裝依賴；若 worktree 無 `.venv`，使用 toolchain 指定的既有 `uv`／Python。

## 禁止修法與 production 邊界

- 不得預設缺 brief 為任何 lane、吞錯後無證據略過、刪 state/outbox，或仍以 brief 作 routing authority。
- 不增加 timeout，不放寬 transaction isolation、SHA/identity/correlation 或 capacity guard。
- 不順手修 Node、Publisher recovery、prerender 或 production activation。
- 不執行 launchctl、deploy、publish、tag、push，不碰 production、queue 或 transaction。

## 停止與交付

- 同一 blocker 第三次即停；scope 需擴張立即 `BLOCKED`。
- 完成 candidate commit 即停，不自行整合、開 Reviewer 或 Repair。
- 回報 `DELIVERED_CANDIDATE`／`BLOCKED`、root cause、RED/GREEN、changed files、完整 SHA、evidence 路徑及零 production mutation 聲明。
