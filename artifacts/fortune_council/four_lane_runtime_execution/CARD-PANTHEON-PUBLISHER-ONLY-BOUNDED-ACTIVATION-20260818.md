---
id: CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-20260818
chain_id: PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-20260818
role: implementation
cycle: 1
status: ready
type: implementation
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: production LaunchAgent、barrier、runtime identity 與單筆發布邊界屬規格已固定的高回退成本控制面變更；使用 GPT-5.5 high，不使用 5.6。
ownership:
  - scripts/install_agy_gemini_coordinator_launchd.sh
  - scripts/install_agy_content_publisher_launchd.sh
  - scripts/pantheon_content_runtime_manifest.py
  - ops/launchd/com.pantheon.agy-content-publisher.plist.example
  - tests/test_agy_gemini_coordinator.py
  - tests/test_agy_content_publisher.py
  - tests/test_pantheon_content_runtime_manifest.py
  - .work/CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-20260818/**
forbidden_scope:
  - production activation、runtime promotion、LaunchAgent reload、發布、tag 或 push
  - 修改 Writer、Gemini 模型路由、四線 lane 邏輯、文章、registry、sitemap、queue、state 或 transaction
  - 手改 plist、barrier、queue 或 transaction；新增第二套 workflow engine；無界 retry
  - 放寬現有 aggregate activation barrier、runtime manifest identity 或 capacity/readiness gate
verification:
  - Publisher-only bounded normal activation 不得重載或 normal 啟動其他六服務
  - max-runs 必須等於 1；exact-run 若提供必須通過既有格式與 selector contract
  - barrier、generation、manifest digest、actor identity、staged/live plist 任一缺失或 drift 時，在任何 launchctl mutation 與 Publisher child I/O 前 fail closed
  - activation-only 既有七服務零 child I/O 契約不得退化
  - 受影響 pytest、bash -n、git diff --check
evidence_path: .work/CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-20260818/
---

# Publisher-only bounded activation

## 工作名稱 → 正在做什麼 → 現在狀態

建立 Publisher-only bounded 啟動入口 → 讓已完成 aggregate activation-only 的 runtime 能只啟動一筆 Publisher transaction → `READY / IMPLEMENTATION ONLY`

## Root Question

能否沿用既有 runtime manifest、matching activation barrier 與 Publisher installer，新增一個正式且 fail-closed 的 Publisher-only normal activation 入口，使其他六服務保持 activation-only，並把 Publisher 每次執行硬限制為 `max-runs=1`／可選 exact-run？

## 已知事實

- Production 已以 direct exact-run 成功發布 `auto-i18n-en-fcaa5bb4adcfef7aa55c`；release `v0.3.369`、content commit `3ded64e00bbd905549c771ae746952e767c94cdf`，完整驗證 `420 passed`。
- 七服務目前維持 aggregate `activation-only`，30 秒 snapshot 無新 queue/run/lane file。
- Publisher installer 已能 stage `PANTHEON_PUBLISH_MAX_RUNS=1` 與 `PANTHEON_PUBLISH_EXACT_RUN_ID`。
- 現有 normal activation 入口是七服務 aggregate，無法只切 Publisher；因此 scheduler 保持 deferred。
- 本卡只補正式控制面入口，不執行 production canary；candidate 必須經獨立 Review、主線整合後，才能另開 production canary 卡。

## 需求與成功準則

- `FR-PA-001`：提供唯一正式 Publisher-only bounded normal activation 入口；不得以手工 `launchctl` 或 plist 編輯替代。
- `FR-PA-002`：入口只允許 `max-runs=1`；可選 exact-run 必須沿用既有 run-id validation 與 selector contract。
- `FR-PA-003`：入口只替換／啟動 Publisher，其他六個 live service 的 plist bytes、activation mode、PID／launchctl identity 不得改變。
- `FR-PA-004`：matching barrier、manifest digest、generation、actor identity、staged receipt 或 Publisher plist identity 任一不符，必須在任何 live mutation與 child I/O 前 fail closed。
- `FR-PA-005`：保留 aggregate `--activate-only` 與既有 aggregate normal activation 行為，不建立第二套 manifest/barrier authority。
- `SC-PA-001`：測試證明成功路徑只有一個 Publisher bootstrap，且 selector 最多一筆。
- `SC-PA-002`：負向測試逐項證明缺 token／stale barrier／錯 generation／錯 digest／max-runs>1／plist drift 都是零 launchctl mutation、零 Publisher child I/O。
- `SC-PA-003`：本卡 production mutation count 必須為 `0`，只交 candidate commit 與 evidence。

## 執行切片

### `SLICE-PA-CONTRACT-RED`

- `traces_to`: `FR-PA-001`, `FR-PA-002`, `FR-PA-003`, `SC-PA-001`
- 先以 public CLI/installer contract 建 RED：目前無法在不重載其他六服務下，只 bounded-normal 啟動 Publisher。
- 測試必須觀察 installer command、plist identity、launchctl mutation log 與 child I/O；不得只測私有函式名稱。

### `SLICE-PA-FAIL-CLOSED-GREEN`

- `traces_to`: `FR-PA-001`, `FR-PA-002`, `FR-PA-003`, `FR-PA-004`, `FR-PA-005`, `SC-PA-001`, `SC-PA-002`
- 以最小變更重用現有 stage receipt、runtime manifest 與 matching barrier authority。
- 正向路徑只允許 Publisher bounded plist transition；負向路徑必須在 live mutation 前停止。
- 禁止 sleep、kill、手工 bootout 時序、複製 aggregate activation engine或隱式接受 `max-runs=3`。

### `SLICE-PA-VERIFY`

- `traces_to`: `SC-PA-001`, `SC-PA-002`, `SC-PA-003`
- 跑目標 pytest、相關回歸 pytest、`bash -n` 與 `git diff --check`。
- 保存 RED/GREEN、changed-file allowlist、production mutation count=`0`、candidate SHA 與 residual risks。
- 交付狀態只能是 `DELIVERED_CANDIDATE` 或帶 exact blocker 的 `BLOCKED`。

## Blocking edges 與 frontier

- Frontier：`SLICE-PA-CONTRACT-RED` 可立即開始。
- `SLICE-PA-FAIL-CLOSED-GREEN` 被 RED 可重現證據阻擋。
- `SLICE-PA-VERIFY` 被 GREEN 與全部 fail-closed negatives 阻擋。
- 獨立 Review 被 candidate SHA 阻擋；production canary 被 Review GO 與主線整合阻擋。

## 停損

- 同一 blocker 最多三次；第三次停止，不改名重跑。
- 若必須修改 queue、Publisher selection semantics、Writer/lane、文章或 production runtime，回 `BLOCKED / SCOPE_EXPANSION`。
- 若出現兩個以上 authority 或 activation 架構 fork，只列候選與證據，回主線裁決；不得自行升 Sol。
- 任何 production mutation、push、tag 或發布企圖立即停止並保全 evidence。

## 交付格式

- candidate commit SHA
- changed files
- RED/GREEN commands and results
- fail-closed negative matrix
- production mutations：必須為 `0`
- residual risks
- evidence path
