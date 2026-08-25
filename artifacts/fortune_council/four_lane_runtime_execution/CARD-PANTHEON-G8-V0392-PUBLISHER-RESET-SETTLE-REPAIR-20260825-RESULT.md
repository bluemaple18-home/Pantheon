---
card_id: CARD-PANTHEON-G8-V0392-PUBLISHER-RESET-SETTLE-REPAIR-20260825
status: DELIVERED_CANDIDATE
dispatch_key: v1:b316b7ba75978dc9a857211967eea548b7c5c691f388bb7dd20556d8cb8daefd
activation_token: act-v1:7add5277484df38f6c6a9fbac054082b03bea11c9811bfdd0d3b39648f1b6090
base_sha: 1a5c3d60559f26604740050de081e2d8ace027f1
candidate_sha: see_delivery_receipt
---

# Publisher activation-only settle 修復結果

## 摘要

已新增 deterministic fake-launchctl regression，重現 Publisher bootstrap 後第一次 `launchctl print` 有同一路徑 PID、第二次同 canonical path no-PID 的 transient 狀態。

最小修復後，`publisher_reset_settle` 會先驗證 `path` 必須唯一且等於 live Publisher plist；若 path 正確但 PID 仍存在，會在既有 bounded settle window 內繼續等待。直到同一路徑 no-PID 才成功；若最後一次仍有 PID，仍以 `publisher_reset_settle` rollback。

未操作真實 `launchctl`、正式 runtime、activation、publication、push、tag、merge、Reviewer/Publisher child 或 replacement。

## 變更

- `scripts/install_agy_gemini_coordinator_launchd.sh`
  - 將 settle loop 的 post-bootstrap `path` 驗證提前到每次 successful `launchctl print`。
  - 對同 canonical path 的 transient PID 改為 bounded wait。
  - 持續 PID 到第 20 次仍保留 `Publisher activation-only reset settled with a running Publisher.` fail-closed。
- `tests/test_agy_gemini_coordinator.py`
  - 新增 `test_publisher_terminal_reset_settles_after_transient_pid`。
  - 測試確認成功路徑只發生 bootstrap、沒有 Publisher child log、產生 reset success receipt，且 other six plist byte-identical。

## 證據

- RED：`artifacts/fortune_council/four_lane_runtime_execution/g8_v0392_publisher_reset_settle_repair_20260825/red_transient_pid.log`
  - 失敗原因為目標症狀：`Publisher activation-only reset settled with a running Publisher.`
- GREEN transient：`artifacts/fortune_council/four_lane_runtime_execution/g8_v0392_publisher_reset_settle_repair_20260825/green_transient_pid.log`
  - `1 passed`
- GREEN targeted reset subset：`artifacts/fortune_council/four_lane_runtime_execution/g8_v0392_publisher_reset_settle_repair_20260825/green_targeted_reset_subset.log`
  - `13 passed`
  - 覆蓋 transient PID success、loaded/no-PID success、absent settle rollback、persistent PID rollback、path drift、live PID pre-mutation、bootstrap rollback、postcheck rollback、temp receipt failure。
- Shell syntax：`artifacts/fortune_council/four_lane_runtime_execution/g8_v0392_publisher_reset_settle_repair_20260825/bash_n.log`
  - `bash -n scripts/install_agy_gemini_coordinator_launchd.sh` 通過；log 為空。
- Diff whitespace：`artifacts/fortune_council/four_lane_runtime_execution/g8_v0392_publisher_reset_settle_repair_20260825/git_diff_check.log`
  - `git diff --check` 通過；log 為空。
- Debug scan：`artifacts/fortune_council/four_lane_runtime_execution/g8_v0392_publisher_reset_settle_repair_20260825/debug_prefix_scan.log`
  - `rg "\[DBG-"` 無命中；log 為空。
- 完整檔代表性阻塞：`artifacts/fortune_council/four_lane_runtime_execution/g8_v0392_publisher_reset_settle_repair_20260825/full_file_blocker_representative.log`
  - activation tests 在本卡無關的 Writer/Reviewer CLI capability preflight 先失敗：`writer model is unavailable: gemini-3.5-flash`。

## 完整測試檔結果

已執行：

```text
/Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py
```

結果：

```text
73 failed, 192 passed in 421.52s
```

失敗共因為 `--activate` / `--activate-only` 路徑在本卡無關的 Writer/Reviewer CLI capability preflight 先被 `gemini-3.5-flash` unavailable 擋下，導致多個既有 activation 測試尚未進入各自預期的 validation/rollback phase。`--reset-publisher-activation-only` 目標子集已通過。

## 限制與風險

- 未修復 `gemini-3.5-flash` capability availability；該問題不在本卡 allowlist 與唯一責任切片內。
- 未執行真實 launchctl、正式 activation、publication、push、tag 或 merge。
- 候選 commit 需由主線/Reviewer 重新驗收完整檔阻塞是否可接受，或另開卡處理 model route capability preflight。
