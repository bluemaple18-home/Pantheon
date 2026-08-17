---
id: CARD-PANTHEON-COORDINATOR-LANE-OWNERSHIP-REPAIR-20260818
status: ready
type: implementation
chain_id: PANTHEON-COORDINATOR-PUBLISHER-RECOVERY-20260818
role: implementation
cycle: 1
thickness: strict
risk: core-bounded
model: gpt-5.5
reasoning: high
model_reason: RCA 已鎖定 Coordinator state ownership 契約；跨 register、migration 與四 lane fail-closed 行為，規格固定但屬 core-bounded 修復。
owner: visible-thread-implementation
ownership: Coordinator lane-routing state contract only
mainline_acceptor: current-main-thread
evidence_path: .work/CARD-PANTHEON-COORDINATOR-LANE-OWNERSHIP-REPAIR-20260818/
---

# Coordinator lane ownership contract repair

## 工作名稱 → 正在做什麼 → 現在狀態

Coordinator lane ownership repair → 將 lane/mode routing authority 固化到版本化 state，避免缺 brief 令整個 cycle crash → `READY / LOCAL ONLY`

## Root question

如何在不猜 lane、不略過所有 active state、不放寬 fail-closed 的前提下，使 Publisher-owned active transaction 缺 `brief.json` 時不再令 Coordinator 整個 cycle 退出？

## Authority

- 必讀 `artifacts/fortune_council/four_lane_runtime_execution/coordinator_publisher_causal_rca_20260818/rca.md`。
- 已確認 RED：`_migrate_pending_jobs` 收到缺 brief 的 active state時，於 `_lane_for_state` 拋 `ValueError("active run brief is unavailable")`。
- Node scan 與 historical recovery exit 128 不屬本卡；capacity guard 是正確 stop-loss。

## 可改範圍

- `scripts/agy_gemini_coordinator.py`
- `tests/test_agy_gemini_coordinator.py`
- `.work/CARD-PANTHEON-COORDINATOR-LANE-OWNERSHIP-REPAIR-20260818/`

其他檔案一律唯讀。不得修改 Publisher、SEO pipeline、prerender、capacity guard、runtime manifest、launchd、queue data、transaction 或文章生成物。

## 必做契約

1. 在 `register_run` 建立 state 時，從已驗證 brief 推導並原子持久化版本化 routing fields：immutable `mode` 與 canonical `lane`。必須保留既有 run/correlation identity 與 idempotency。
2. `_lane_for_state` 對具新版本 routing fields 的 state 只信 state；驗證 mode/lane pair，未知或衝突值 fail-closed，不能重讀可變 brief 覆寫。
3. legacy state 缺 routing fields：
   - brief 可讀且合法時，允許一次明確、可測、原子的 state migration；
   - brief 不可讀時，不得 crash 整個 cycle、猜 lane、刪 state 或搬動 outbox；回傳穩定的 quarantined/unroutable outcome，讓其他可路由 lane 可繼續。
4. 保持四 lane oldest-first、shared pending job namespace、retry/terminal 與 existing state schema 相容。
5. 不增加 timeout，不改 capacity guard，不碰 production。

## RED→GREEN 測試

先新增或調整最小測試並實跑 RED，再做最小修復：

- missing brief 的 active state 不使 `_migrate_pending_jobs`／`cycle_once` crash，且其 outbox 不被搬移或刪除；其他可路由 state 仍可前進。
- `new`、`rewrite`、`i18n-new`、`i18n-rewrite` 的新 state 均持久化正確 mode/lane 並可 migration。
- state routing fields 與 brief 衝突時，以 immutable state 為 authority或明確拒絕，不得靜默覆寫。
- unknown version、unknown lane、invalid mode/lane pair fail-closed。
- `register_run` idempotency、private path、brief size 與既有四 lane ordering regression 保持通過。

## 驗證

至少執行：

```text
uv run --frozen python -m pytest tests/test_agy_gemini_coordinator.py -q
git diff --check
```

若專案 frozen 環境不可用，使用既有專案 Python/uv 路徑；不得安裝依賴。需記錄 RED、GREEN、完整測試數與 command。

## 禁止修法

- 預設缺 brief 為 rewrite 或任一 lane。
- catch `ValueError` 後無證據吞掉、刪 state、清 outbox，或略過全部 active states。
- 把 routing authority 留在可變 run-dir brief。
- 放寬 transaction isolation、SHA/identity/correlation 或 capacity guard。
- 順手修 Node 效能、Publisher recovery、prerender timeout 或 production activation。

## 停止條件

- 同一 blocker 第三次出現即停，不做第四次。
- 需要擴到 allowlist 外、改 state public schema 的不相容語意，或需要 production evidence 才能繼續時立即 `BLOCKED`。
- 完成候選 commit 後停止；不得 push、deploy、啟動服務、開 Reviewer／Repair 或自行整合。

## 交付

1. `DELIVERED_CANDIDATE` 或 `BLOCKED`。
2. root cause 與最小修法。
3. RED/GREEN commands 與結果。
4. changed files 與完整 candidate SHA。
5. evidence 路徑。
6. 明確聲明未啟動服務、未碰 production、未 push。
