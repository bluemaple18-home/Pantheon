# CARD-PANTHEON-G8-PUBLISHER-CANARY-ATOMIC-REPAIR-20260821 RESULT

## 結論

已完成離線修復與驗證。此卡完成只代表可重新建立安全 Publisher-only canary stage；不代表已正式上線。

## Base 與任務卡

- 實作 base：`486ee252ee13ec91cdc45d42dfc71b64ead2148d`
- 任務卡 blob：`2401e0484b3c56a2b2e0cc30466b122a1e08fa1b`
- 備註：任務卡 front matter 仍寫 `required_base_sha: f2484658fc508bdfea33dd615692d8012d797d16`，本次派工輸入明確要求 `486ee252ee`，且 worktree HEAD 已核對為該 full SHA。

## 兩個根因

1. `_run_release_tests()` 原本經 `_run_checked()` 直接繼承父 process 的 formal runtime/model-route identity，導致 pytest child 在測試自己斷言前先被 production-only fail-closed 擋下。
2. Publisher-only activation 原本沿用含 `StartInterval` 的正常 Publisher plist；`--max-runs=1` 只限制單一 child process 選取數，不能防止 launchd 排程第二次 child。

## 修改檔案

- `scripts/agy_content_publisher.py`
- `scripts/install_agy_gemini_coordinator_launchd.sh`
- `tests/test_agy_content_publisher.py`
- `tests/test_agy_gemini_coordinator.py`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-PUBLISHER-CANARY-ATOMIC-REPAIR-20260821-RESULT.md`

## 修復內容

- `_run_checked()` 新增可選 `env`，但只有 `env is not None` 時才傳給 `subprocess.run()`；非 pytest subprocess 保持原呼叫形狀與父環境繼承。
- `_run_release_tests()` 建立 sanitized child env，移除 `PANTHEON_FORMAL_RUNTIME`、所有 `PANTHEON_RUNTIME_*`、model-route identity 與 writer/reviewer route override；父 `os.environ` 不變。
- Publisher-only activation 在 stage receipt、publisher plist preflight、activation-only live aggregate validation、barrier validation 都通過後，才將 staged Publisher plist 轉為 one-shot：刪除 `StartInterval` / `KeepAlive`，保留或新增 `RunAtLoad=true`。
- Publisher-only activation 仍保留 `--max-runs 1`、`--exact-run-id` receipt 驗證、ordinary push mode、manifest identity preflight、other six live plist byte equality checks、failure receipt 與 rollback path。

## 完整測試數

- Focused repair set：`14 passed`
- 受影響檔完整測試：`373 passed, 1 warning`
- `TEST_COMMAND` 對應 release tests：`420 passed, 2 warnings`
- Shell syntax：`bash -n scripts/install_agy_gemini_coordinator_launchd.sh` 通過
- Whitespace：`git diff --check` 通過

## One-shot 正負向證據

- 正向 plist 證據：`test_publisher_only_bounded_activation_replaces_only_publisher` 驗證 live Publisher plist `RunAtLoad is True`，且不含 `StartInterval` / `KeepAlive`；同時 `--max-runs 1` 與 `--exact-run-id publisher-only-run-001` 保留。
- 正向 child 證據：`test_publisher_only_activation_is_one_shot_for_child_success_and_failure` 以 fake launchctl 模擬 schedule；child exit `0` 與 `7` 兩種情境都只留下 `run=1`。
- 負向 pre-mutation 證據：`test_publisher_only_bounded_activation_fails_closed_before_mutation` 覆蓋 missing barrier、max-runs drift、exact-run 格式/receipt mismatch、plist drift、empty receipt；失敗時無 mutation log、六個非 Publisher live plist bytes 不變、failure receipt 記錄 phase/exit code，且尚未建立 `publisher-only-backups`。
- 六服務不變證據：成功 Publisher-only activation 測試逐一比對其他六個 live plist bytes 等於 activation-only fixture 原始 bytes。

## 未觸碰 production 的證據

- 未執行正式 activation、正式 canary、真 `launchctl` mutation、tag 或 push。
- 所有 activation 行為只在 pytest `tmp_path` 內透過 fake `launchctl` 腳本模擬。
- `git diff --name-only` 只包含任務允許檔案與本 RESULT。
- `scripts/install_agy_content_publisher_launchd.sh`、queue production data、actor、remote、LaunchAgents 實體路徑均未修改。

## 未做

- 未執行 production ACTIVATE。
- 未建立正式 Publisher canary stage。
- 未執行真 `launchctl bootstrap` / `bootout`。
- 未建立 tag、未 push remote。
- 未新增 Repair/Reviewer thread 或任何新卡。

## 未驗

- 未在 macOS launchd 真實 daemon/session 中觀察 child exit 後的 label terminal state。
- 未驗證 production queue candidate/recovery evidence 的真實資料內容，因本卡明確禁止 production mutation。
- 未跑正式 canary exact run；本次只完成離線 plist/env/rollback contract 驗證。

## 殘餘風險

- one-shot 無重跑結論來自 plist contract 與 fake launchctl schedule 模擬；真 launchd 行為仍需在後續正式 canary 流程中以安全 stage 驗證。
- Publisher-only activation 仍會在通過所有 preflight/barrier 後改寫 staged Publisher plist；若當下 `/usr/libexec/PlistBuddy` 或 `plutil` 異常，會 fail-closed 並留下 failure receipt，但不會替換 live plist。
- 測試執行時 `uv` 在 sandbox 內因 macOS system-configuration panic，改在 sandbox 外跑離線 pytest；未涉及 production mutation。

## Commit

- pre-amend commit SHA：`ad58c44368fc36ce6ffccdd2ae67fe66430f30dd`
- final HEAD SHA：由交付回報提供；同一 commit 內容無法自含自己的 final SHA，因為任何回填都會改變該 commit hash。
