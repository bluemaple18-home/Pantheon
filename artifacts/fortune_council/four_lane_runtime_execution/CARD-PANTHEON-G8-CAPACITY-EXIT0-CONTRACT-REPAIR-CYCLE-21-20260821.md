---
id: CARD-PANTHEON-G8-CAPACITY-EXIT0-CONTRACT-REPAIR-CYCLE-21-20260821
status: ready
chain_id: PANTHEON-G8-PUBLISHER-CANARY
role: repair
cycle: 21
thickness: strict
risk: production-control
model: gpt-5.5
reasoning: high
model_reason: bounded production safety contract repair with a reproduced false negative
---

# 修復 Capacity preactivation exit-0 契約

## Root question

Capacity preactivation transition 是否錯誤拒絕 cold-reset 後已安全停止的 activation-only 服務：`state=not running`、無 PID、plist/identity/path 正確、`last exit code=0`？

## 已重現證據

- Cycle 20 已成功重建 coordinator＋四 lanes 與 Publisher exact-run private stage。
- 正式 Capacity `--preflight` 只執行一次，回傳 `preactivation service mismatch`；capacity install 未執行。
- 七服務 `launchctl` identity：path 正確、`states=['not running']`、無 PID、`last_exit_codes=[0]`。
- `scripts/pantheon_content_capacity_guard.py` 的同檔其他 activation-only identity checks 已接受 `last_exit_codes in ([], [0])`；preactivation transition 第 807 行仍只接受 `([], [78])`。
- 無 activation、canary、transaction、tag、push、retry。

## 目標

1. 建立最小 RED，精確證明合法 `not running + no PID + exit 0` 被 preactivation transition 拒絕。
2. 最小修正，使該合法狀態通過；保留 PID、path、state、identity 與非零未知 exit code 的 fail-closed 行為。
3. 跑受影響測試與完整 `tests/test_pantheon_content_capacity_guard.py`。
4. 只交付 source/test candidate commit；不得操作 live runtime。

## 可改檔案

- `scripts/pantheon_content_capacity_guard.py`
- `tests/test_pantheon_content_capacity_guard.py`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-CAPACITY-EXIT0-CONTRACT-REPAIR-CYCLE-21-20260821-RESULT.md`
- `.work/CARD-PANTHEON-G8-CAPACITY-EXIT0-CONTRACT-REPAIR-CYCLE-21-20260821/**`

## 禁止

- 禁止修改 installer、manifest、plist template、queue、state、registry、sitemap、feed。
- 禁止 LaunchAgent、stage、activation、capacity live preflight、canary、transaction、tag、push。
- 禁止把所有 exit code 都視為安全；只允許由測試證明的 `0` 與既有 `78`／缺值。
- 禁止另開 thread、Reviewer、Repair 或擴大重構。

## 驗收

- RED：新增測試在修正前因 `preactivation service mismatch` 失敗。
- GREEN：合法 exit `0` 與既有 `78`／缺值通過；PID、錯 path、錯 state、未知 exit code仍拒絕。
- 完整 capacity test PASS。
- `git diff --check` PASS。
- candidate commit 只含 allowlist。

## 終局

- `FIXED / READY FOR MAINLINE`
- `BLOCKED / NO RUNTIME MUTATION`
