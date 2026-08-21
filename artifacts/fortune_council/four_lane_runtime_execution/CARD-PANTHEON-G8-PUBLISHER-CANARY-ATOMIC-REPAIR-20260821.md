---
id: CARD-PANTHEON-G8-PUBLISHER-CANARY-ATOMIC-REPAIR-20260821
status: ready
priority: P0
task_type: repair
required_base_sha: f2484658fc508bdfea33dd615692d8012d797d16
---

# G8 Publisher canary 原子化一次修復

## 工作名稱 → 正在做什麼 → 現在狀態

G8 Publisher canary 原子化一次修復 → 一次修正 release test 環境隔離與 Publisher-only one-shot 生命週期 → READY

## Root question

如何讓正式 Publisher canary 在保留 production fail-closed identity 的前提下，只執行指定 exact run 一次；不因測試子程序繼承 production-only 環境而誤敗，也不因 LaunchAgent 排程自動重試？

## 已證實根因

1. `scripts/agy_content_publisher.py::_run_release_tests` 經 `_run_checked` 直接繼承 LaunchAgent 環境。`PANTHEON_FORMAL_RUNTIME=1` 進入 pytest；部分測試刻意清除 model-route identity 後，`GeminiClient.from_environment()` 在測試本身斷言前 fail-closed。Cycle30 的 `7 failed` 為同一環境污染根因，不是七個產品缺陷。
2. `scripts/install_agy_gemini_coordinator_launchd.sh --activate-publisher-only` bootstrap 後立即視為成功、刪除 stage 並解除 rollback trap；它不等待 child 終態。stage Publisher plist 仍含 `RunAtLoad=true`、`StartInterval=60`，首次 child 失敗後 launchd 自動啟動第二次。`--max-runs=1` 只限制單一 process 選取數，不限制 process 啟動次數。
3. 現有測試只驗 activation 會 bootstrap 且 stage 被刪除；沒有驗 child 失敗後不得重跑、one-shot 排程語意、或 release pytest 的環境邊界。

## 單一修復範圍

### A. Release-test 子程序環境隔離

- 為 `_run_checked`／`_run_release_tests` 增加明確、最小的 child env 契約。
- 僅 release pytest 子程序移除 production runtime identity／activation 變數；不得修改父 process `os.environ`。
- Publisher 正式 operation、runtime manifest 驗證、git/tag/push 與其他 subprocess 仍使用 production 正式環境。
- 不得放寬 `model_route_config_from_environment()` 的 fail-closed 條件；不得逐一修改七個失敗測試來繞過污染。

### B. Publisher-only 真正 one-shot

- Publisher-only stage plist 必須是無週期排程的 one-shot：不得含 `StartInterval`／KeepAlive retry 語意；只允許一次 RunAtLoad bootstrap。
- `--max-runs=1`、exact-run-id、ordinary push、manifest identity 仍須保留並通過既有 preflight。
- activation 成功的定義必須涵蓋 one-shot plist 已安裝且無自動第二次 child 的可驗證契約；不得以一般週期 Publisher plist 冒充 bounded canary。
- child 成功或失敗後都不得自動重跑。失敗必須保留 queue candidate 與 recovery evidence；不得 tag/push。
- 明確定義 stage／backup／舊 activation-only plist 的終態，使下一次動作可重現；不得讓失敗靠人工 `bootout` 才安全。

### C. 測試一次補齊

- release pytest 收到 sanitized env；父正式環境與非 pytest subprocess 不變。
- 正式 model-route identity 缺失仍 fail-closed。
- Publisher-only plist 無 `StartInterval`，仍含 exact-run-id 與 max-runs=1。
- 模擬 child exit 0 與非 0，兩者皆只啟動一次；失敗後無第二次 child、無 tag、無 push。
- activation 前失敗維持零 mutation；其他六服務 bytes／load state／child I/O 不變。
- stage、backup、failure receipt 終態符合明訂契約。

## 可修改檔案

- `scripts/agy_content_publisher.py`
- `scripts/install_agy_gemini_coordinator_launchd.sh`
- `tests/test_agy_content_publisher.py`
- `tests/test_agy_gemini_coordinator.py`
- 若 one-shot plist schema 驗證確有必要：`scripts/pantheon_content_runtime_manifest.py`、`tests/test_pantheon_content_runtime_manifest.py`
- 本卡 RESULT 檔

## 禁止範圍

- 不得修改四條 Gemini lane 的內容生成、review 或 routing 邏輯。
- 不得修改 queue production 資料、actor、LaunchAgents 或外部 remote。
- 不得執行正式 activation、canary、tag、push、schedule 或 launchctl mutation。
- 不得新開 Repair／Reviewer thread；本卡內完成 implementation、自我 review 與離線驗收。
- 不得用 sleep/retry 遮蔽 race；不得降低既有 fail-closed gate。

## 驗證順序

1. 先寫／更新聚合測試，證明兩根因與完整終態。
2. 實作兩處修復。
3. 跑受影響 focused tests。
4. 跑完整既有 release gate：`TEST_COMMAND` 對應測試集合。
5. 跑 `bash -n scripts/install_agy_gemini_coordinator_launchd.sh`。
6. 跑 `git diff --check`。
7. 靜態 review 確認無 production mutation、無 fail-open、無未覆蓋分支。

任何一步失敗：在同一 thread 內一次收集完整 failure list，再修；禁止測一個開一張新卡。相同 blocker 第三次才停止。

## 交付

- 只新增 `CARD-PANTHEON-G8-PUBLISHER-CANARY-ATOMIC-REPAIR-20260821-RESULT.md`。
- RESULT 必須列：兩根因、修改檔案、完整測試數、one-shot 正負向證據、未觸碰 production 的證據、commit SHA。
- commit 所有本卡變更；回報單一 commit SHA。

## 完成定義

離線完整驗收全綠，且證明：pytest 無 production env 污染、formal runtime 仍 fail-closed、Publisher-only 無排程重試、成功／失敗皆最多一個 child、其他六服務零變更。此卡完成只代表可重新建立安全 canary stage；不代表已上線。
