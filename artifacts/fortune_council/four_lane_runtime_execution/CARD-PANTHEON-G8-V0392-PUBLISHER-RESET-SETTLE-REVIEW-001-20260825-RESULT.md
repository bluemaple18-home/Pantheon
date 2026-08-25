---
card_id: CARD-PANTHEON-G8-V0392-PUBLISHER-RESET-SETTLE-REVIEW-001-20260825
status: GO
dispatch_key: v1:3bc0db024d33a235454292e867944a63e2c941ea76ab2b193118d9467f859707
activation_token: act-v1:62f4515ee347780e250156226817ad01ba5572d53a5882baa7237e6c26591148
base_sha: 1a5c3d60559f26604740050de081e2d8ace027f1
candidate_sha: 8c18080be331be954224b5616d1374dbfee98b2c
verdict: GO
activation_readiness: BLOCKED_BY_MODEL_CAPABILITY
---

# Publisher transient PID settle 候選審查結果

## Verdict

Candidate correctness：GO。

候選 `8c18080be331be954224b5616d1374dbfee98b2c` 相對 base `1a5c3d60559f26604740050de081e2d8ace027f1` 未發現 P0/P1 或 production safety blocker。`publisher_reset_settle` 現在會先驗證 post-bootstrap `path` 唯一且等於 live Publisher plist；同一路徑若暫時仍有 PID，僅在既有 20 次 bounded window 內等待；若第 20 次仍有 PID，仍 fail-closed rollback。`settle absent`、`path drift`、`postcheck failure` 與 rollback phase 仍由 targeted subset 覆蓋。

Activation readiness：BLOCKED_BY_MODEL_CAPABILITY。

完整檔代表性 activation 測試仍被 `writer model is unavailable: gemini-3.5-flash` 擋在 Writer/Reviewer CLI capability preflight，尚不能宣稱可直接正式 activation 或 publication。此 blocker 與本候選 correctness 分軸，不抵銷本次 GO。

## Findings

### P2 - testing - transient PID 測試的 child_log 未接到 fake launcher

- severity: P2
- category: testing
- path: `tests/test_agy_gemini_coordinator.py:6351`
- evidence: `test_publisher_terminal_reset_settles_after_transient_pid` 建立 `child_log = tmp_path / "publisher-child.log"`，最後以 `assert not child_log.exists()` 作為「Publisher child 未執行」證據；但本測試沿用 `_prepare_publisher_only_activation_fixture` 產生的 shell fake launchctl，其 `bootstrap` 只 `touch` loaded marker，沒有任何可寫入 `child_log` 的路徑。相鄰 helper `_write_launchctl_that_records_publisher_child` 在 `tests/test_agy_gemini_coordinator.py:4820` 才真正把 bootstrap child execution 寫入 `child_log`。
- trigger: transient PID 測試通過時，若有人把 `child_log` 不存在解讀為 child execution 沒發生。
- risk: 這個 assert 只能證明未接線的檔案沒有被寫入，不能獨立證明 Publisher child 未執行；會削弱 SC-003 的測試證據。
- suggested_fix: 讓 transient PID 測試使用可記錄 child execution 的 fake launchctl，或在該 fake 裡加入明確 child execution trap/log；再以該 log 的空白或精確內容作為證據。
- validation_gap: 目前 targeted subset 證明 transient PID 後 no-PID 能成功、persistent PID/path drift/absent/postcheck 仍 rollback，但未用接線的 fake launcher 證明 transient success path 沒有執行 Publisher child。
- confidence: high

## Spec Axis

- SC-001：PASS。新增 transient PID regression 在 candidate 前為 RED，candidate 後為 GREEN；重跑結果 `13 passed`。
- SC-002：PASS。persistent PID 到 bounded window 結束仍 rollback；path drift 仍 fail-closed；settle absent 與 postcheck failure 仍 rollback。
- SC-003：PARTIAL。other six plist byte-identical、mutation log 與 receipt/provenance 覆蓋通過；但 transient 測試的 child_log 未接線，因此「child 未執行」證據需補強。此缺口未達 P1，因為產品 diff 沒放寬 bootstrap/rollback 邊界，且候選 success receipt 仍要求 post identity no-PID。

## Standards Axis

- implementation diff scope: PASS，產品 diff 僅 `scripts/install_agy_gemini_coordinator_launchd.sh` 與 `tests/test_agy_gemini_coordinator.py`。
- fail-closed behavior: PASS，path 缺失/重複/漂移、persistent PID、settle absent、postcheck failure 都沒有被改成 success。
- side effects: PASS，other six plist byte-identical assertions 仍在 subset 內通過。
- activation readiness: BLOCKED，不屬本候選修復範圍。

## Reviewer Evidence

- `artifacts/fortune_council/four_lane_runtime_execution/g8_v0392_publisher_reset_settle_review_001_20260825/targeted_subset.log`
  - `13 passed in 35.34s`
- `artifacts/fortune_council/four_lane_runtime_execution/g8_v0392_publisher_reset_settle_review_001_20260825/bash_n.log`
  - `bash -n scripts/install_agy_gemini_coordinator_launchd.sh` 通過；log 為空。
- `artifacts/fortune_council/four_lane_runtime_execution/g8_v0392_publisher_reset_settle_review_001_20260825/git_diff_check_candidate.log`
  - `git diff --check 1a5c3d60559f26604740050de081e2d8ace027f1 8c18080be331be954224b5616d1374dbfee98b2c` 通過；log 為空。
- `artifacts/fortune_council/four_lane_runtime_execution/g8_v0392_publisher_reset_settle_review_001_20260825/debug_prefix_scan.log`
  - `rg "\[DBG-" scripts tests` 無命中；log 為空。
- `artifacts/fortune_council/four_lane_runtime_execution/g8_v0392_publisher_reset_settle_review_001_20260825/full_file_blocker_representative.log`
  - `test_aggregate_activation_rejects_before_mutation_with_failure_receipt` 兩個參數化案例仍失敗，代表性錯誤為 `ValueError: writer model is unavailable: gemini-3.5-flash`。

## Environment

- cwd: `<repo-root>` in detached Codex worktree
- HEAD at review start: `f367d87e3d2a4372c0da8624fa25163d5b44ea6c`
- product diff reviewed: `1a5c3d60559f26604740050de081e2d8ace027f1..8c18080be331be954224b5616d1374dbfee98b2c`
- CodeGraph readiness: ready during review, 582 files indexed, 6925 nodes, 15331 edges

## Restrictions Observed

未修 code、未改 tests、未碰真實 `launchctl`、未操作正式 runtime、未 activation、未 Writer、未 publication、未 push、未 tag、未 merge、未另開任務。
