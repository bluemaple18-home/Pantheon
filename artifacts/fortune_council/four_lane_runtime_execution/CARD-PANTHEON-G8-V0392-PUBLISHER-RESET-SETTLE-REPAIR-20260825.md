---
id: CARD-PANTHEON-G8-V0392-PUBLISHER-RESET-SETTLE-REPAIR-20260825
status: ready
chain_id: PANTHEON-G8-PUBLISHER-RESET-SETTLE-REPAIR-20260825
role: implementation
cycle: 1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 規格已固定，但修改 production activation 的 fail-closed settle 狀態契約；使用 strict/core-bounded 跑道，不需 Sol 開架構岔。
traces_to:
  - SC-001
  - SC-002
  - SC-003
supersedes: []
---

# Pantheon Publisher activation-only settle 修復

工作名稱：Pantheon Publisher activation-only settle 修復

任務目的：修正正式 `--reset-publisher-activation-only` 把 activation-only Publisher 的短暫啟動 PID 立即誤判為永久 running，導致 `publisher_reset_settle` fail-closed rollback；保留真正持續 running、path drift 與 child execution 的拒絕能力。

## 已知重現與根因邊界

- V0391 正式執行在 `publisher_reset_settle` 回傳：`Publisher activation-only reset settled with a running Publisher.`
- failure receipt 為 `ROLLBACK_COMPLETE`；沒有 `publisher-reset-receipt.json`，live Publisher 已回復 absent，沒有第三次 Writer、第二 run、Publisher child、push 或 tag。
- 現行 loop 在任一 `launchctl print` 首次看見 PID 時立即 `false`；activation-only wrapper 可能在 barrier/bootstrap 後短暫存在 PID，尚未給它在 bounded settle window 內退出的機會。
- 本卡必須先用 deterministic fake-launchctl test 證明「短暫 PID 後 no-PID」目前為 RED；不得以直接重跑 production activation 當診斷手段。

## 唯一責任切片

`SLICE-V0392-01`，`traces_to: [SC-001, SC-002, SC-003]`：以一個 RED → minimal fix → GREEN 閉環，讓 settle loop 容許 bounded transient PID，直到同一 canonical path 的 loaded/no-PID 狀態才成功；若直到期限仍有 PID，仍須 rollback 並留下 `publisher_reset_settle` failure receipt。

frontier：`SLICE-V0392-01` 可立即開始；沒有其他 slice。Reviewer 尚未派工，候選 commit 交回主線後才建立唯一 Reviewer thread。

## 可改範圍

- `scripts/install_agy_gemini_coordinator_launchd.sh`
- `tests/test_agy_gemini_coordinator.py`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0392-PUBLISHER-RESET-SETTLE-REPAIR-20260825-RESULT.md`
- `artifacts/fortune_council/four_lane_runtime_execution/g8_v0392_publisher_reset_settle_repair_20260825/`

## 禁止範圍

- 禁止修改其他 source、runtime manifest、model route、queue/run、Publisher payload、registry、共享規則與既有 evidence。
- 禁止操作 `~/Library/LaunchAgents`、`launchctl` 真實服務或正式 runtime；測試只能使用既有 fake HOME/fake launchctl fixture。
- 禁止第三次 Writer、第二 run/replacement、Reviewer/Publisher child、activation、publication、push、tag、merge、archive 或清理既有未追蹤檔。
- 禁止延長成通用 launchd 重構、改寫 rollback/provenance 契約，或放寬 path drift／持續 PID 的 fail-closed gate。

## 成功準則

- `SC-001`：新增 observable regression test，fake Publisher 在前若干次 `launchctl print` 有 PID、之後同一路徑 no-PID；修復前穩定 RED，修復後 reset 成功且產生既有 success receipt。
- `SC-002`：既有或補強測試證明 Publisher 在完整 bounded settle window 持續有 PID 時仍 rollback，failure phase 為 `publisher_reset_settle`；path drift 仍立即 fail-closed。
- `SC-003`：成功路徑沒有執行 Publisher child；只允許既有 bootstrap/print/bootout 測試記錄，其他六服務 plist byte-identical，既有 reset/provenance 契約不變。

## 驗證

1. 先跑新增 transient-PID 單測並保存 RED 證據；RED 必須是目標症狀，不得是 fixture/import 錯誤。
2. 實作最小修復後跑新增測試、持續 PID、path drift、settle absent、postcheck/rollback 相關測試。
3. 跑完整 `tests/test_agy_gemini_coordinator.py`。
4. 跑 `bash -n scripts/install_agy_gemini_coordinator_launchd.sh` 與 `git diff --check`。
5. 檢查 diff 僅在 allowlist；不得碰主工作區既有未追蹤檔。

## 停損與交付

- 若 RED 無法用 fake launchctl 重現、修復需要改第三個 source/test 檔、或發現 activation-only 子程序實際執行 Publisher child，立即 `BLOCKED` 回主線，不擴 scope。
- 同一 blocker 最多兩次有證據的修復嘗試；不得無限調 timeout、sleep 或重跑。
- 交付一個原子 candidate commit、完整 SHA、RED/GREEN 證據與 RESULT；狀態只能是 `DELIVERED_CANDIDATE` 或 `BLOCKED`，不得宣稱已整合、已 activation 或已發文。
