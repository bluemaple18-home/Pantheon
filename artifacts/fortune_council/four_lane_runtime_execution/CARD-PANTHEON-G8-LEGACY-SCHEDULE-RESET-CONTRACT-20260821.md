---
id: CARD-PANTHEON-G8-LEGACY-SCHEDULE-RESET-CONTRACT-20260821
status: ready
chain_id: pantheon-g8-publisher-canary-final-ship-20260821
role: Repair
cycle: 2
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: production reset 核心契約已固定，需 bounded 高影響修復
---

# G8 legacy Publisher schedule reset 契約修復

## 目標

修正 `--reset-publisher-activation-only` 的自相矛盾前置條件：正式 live Publisher 為正常排程 plist（`RunAtLoad=true`、`StartInterval=60`、無 `--activation-only`），reset 必須能在完整 identity、argv、service label 與 launchctl 安全條件通過時，將它原子轉成 activation-only terminal plist。

## 已知事實

- source base：`1f81d4c1886c9e029384fd8d91791fff15ea77ca`（建立 worktree 時必須核對完整 SHA）。
- production execution 已 fail-closed；reset invocation、Capacity、Rule25、activation、Publisher child 與其他六服務 business I/O 均為 `0`。
- 現行 handler 先以 `publisher-plist-receipt --activation-mode normal` 驗證 live Publisher，隨後又拒絕任何 `StartInterval`／`KeepAlive`；focused success fixture 先移除 schedule keys，因此未覆蓋真實 legacy normal state。
- live Publisher service 目前 absent；本卡不得接觸 production runtime、LaunchAgents、queue、actor、remote、tag 或 push。

## 允許修改

- `scripts/install_agy_gemini_coordinator_launchd.sh`
- `tests/test_agy_gemini_coordinator.py`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-LEGACY-SCHEDULE-RESET-CONTRACT-20260821-RESULT.md`

## 禁止範圍

- 不修改 Publisher 業務邏輯、四 lane routing、manifest schema、Capacity Guard 或 readiness gate。
- 不執行 launchctl mutation、正式 reset／activation、production canary、tag、push、deploy。
- 不另開 thread、Reviewer 或 replacement；只在既有 formal thread 內交付 candidate。
- 不用 sleep／retry 掩蓋競態；不降低 identity、argv、service-label、PID、launchctl path、rollback 或其他六服務不變檢查。

## 固定實作契約

1. reset pre-mutation 接受正常 scheduled Publisher：`RunAtLoad=true`、`StartInterval` 為正式 normal receipt 所允許的值、無 `KeepAlive`、無 `--activation-only`。
2. 仍由正式 `publisher-plist-receipt --activation-mode normal` 驗證 outer barrier argv、child module、manifest identity 與 service label；不可手寫寬鬆替代驗證。
3. 未載入或已載入但無 PID且 path 精確相符皆可；running PID、path drift、identity drift、argv drift、錯 schedule／KeepAlive 均在 mutation 前拒絕。
4. 成功只替換 Publisher plist並 bootstrap activation-only terminal state；其他六份 live plist byte-identical，Publisher child invocation 為 `0`。
5. 任一 replace／bootout／bootstrap／postcheck 失敗，恢復原 scheduled Publisher bytes與原 loaded/absent 狀態，保留 failure receipt；不得改動其他六服務。

## 必補測試

- 真實 normal scheduled live Publisher（含 `StartInterval=60`）成功 reset，輸出 activation-only、無 `StartInterval`／`KeepAlive`，child count `0`，其他六服務 byte-identical。
- scheduled live Publisher loaded-but-no-PID 的成功路徑，確認只 bootout／bootstrap Publisher。
- 錯 `StartInterval`、存在 `KeepAlive`、running PID、path drift、identity drift、outer／child argv drift全部 pre-mutation fail closed。
- rollback 至少覆蓋 bootstrap 或 postcheck failure，恢復 scheduled bytes與原 loaded state，其他六服務不變。
- 保留既有 terminal one-shot input 行為：若仍屬合法 normal receipt則明確測試；若正式 normal receipt 不允許，測試應清楚固定拒絕理由，不得模糊接受任意 schedule。

## 驗證

- 先列完整 focused test matrix，一次實作，不得測一個補一個。
- 執行 reset 相關 focused tests與受影響 Publisher-only bounded tests。
- `bash -n scripts/install_agy_gemini_coordinator_launchd.sh`
- `git diff --check`
- RESULT 列出 changed files、完整測試命令與結果、candidate full SHA、remaining risk。

## 停損

- 若正式 `publisher-plist-receipt --activation-mode normal` 的 canonical contract 本身拒絕 `StartInterval=60`，或需要修改 manifest schema／production state，立即 `BLOCKED`，不得擴大範圍。
- 同一 blocker 連續兩次失敗即停止，不做第三次。
