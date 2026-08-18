---
id: CARD-PANTHEON-PUBLISHER-SAFE-ACTIVATION-RESTORE-20260818
chain_id: PANTHEON-PUBLISHER-SAFE-ACTIVATION-RESTORE-20260818
role: implementation
cycle: 1
status: ready
type: implementation
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: production LaunchAgent、RunAtLoad、barrier 與 fail-closed activation 屬固定契約的高回退成本變更；規格已鎖定，不需使用 5.6。
ownership:
  - scripts/install_agy_gemini_coordinator_launchd.sh
  - scripts/pantheon_content_runtime_manifest.py
  - scripts/agy_content_publisher.py
  - ops/launchd/com.pantheon.agy-content-publisher.plist.example
  - tests/test_agy_gemini_coordinator.py
  - tests/test_pantheon_content_runtime_manifest.py
  - tests/test_agy_content_publisher.py
  - .work/CARD-PANTHEON-PUBLISHER-SAFE-ACTIVATION-RESTORE-20260818/**
forbidden_scope:
  - 修改 Writer、Gemini 模型路由、四線 lane 邏輯、文章、registry、sitemap、queue 或既有 transaction
  - normal production activation、runtime promotion、LaunchAgent reload、發布、tag 或 push
  - 新增第二套 activation engine、無界 retry、手動 queue／transaction 修復
verification:
  - activation-only bootstrap 不得啟動 Publisher child I/O
  - normal activation 在 barrier 驗證前不得執行 Publisher publish path
  - transition 缺 token、generation、manifest 或 readiness 證據時 fail closed
  - 受影響 pytest、shell syntax、git diff --check
evidence_path: .work/CARD-PANTHEON-PUBLISHER-SAFE-ACTIVATION-RESTORE-20260818/
---

# Publisher safe activation restore

## 工作名稱 → 正在做什麼 → 現在狀態

Publisher 安全啟動修復 → 阻止 normal activation 在 barrier 前因 `RunAtLoad` 直接發布 → `READY / IMPLEMENTATION ONLY`

## Root Question

能否沿用既有 aggregate installer 與 activation barrier，讓 Publisher 先安全載入並完成驗證，再才具備正常排程資格，且任何缺證據狀態都不執行 child publish？

## 已確認事實

- 第四線 rewrite 已成功發布；content commit `45942c29710fc58916addb8862f92c90444b29e8`、tag `v0.3.368`、公開 URL HTTP 200。
- 舊 active translate 已由正式 exact coordinator cycle 收斂為 terminal `failed`；無 `state/transaction-*`。
- Publisher LaunchAgent 目前 absent。
- `scripts/install_agy_gemini_coordinator_launchd.sh --activate-only` 已存在，會對七個 staged plist 注入 `--activation-only`，完成 aggregate/barrier 而不執行 child I/O。
- 前次事故入口是直接使用 normal `--activate`；Publisher plist 同時有 `RunAtLoad=true` 與 `StartInterval=60`，會在 aggregate barrier 完成前啟動 normal publish path。
- 目前問題不是四線、Writer 或 prerender 演算法；是 activation-only 到 normal scheduler 的安全 transition 契約缺口。

## 需求與成功準則

- `FR-001`：Publisher normal child 在 aggregate barrier 與 matching runtime generation 驗證完成前不得執行。
- `FR-002`：activation-only 仍須可載入七服務、寫 ready receipt、通過 aggregate validation，且 child I/O 為零。
- `FR-003`：normal transition 必須綁定 manifest digest、generation、correlation／token；缺失或 stale 一律 fail closed。
- `SC-001`：測試可重現舊行為的危險窗口，修復後證明 barrier 前 Publisher publish invocation count 為 0。
- `SC-002`：修復不得改 queue、文章、Publisher selection、Writer 或 lane state machine。
- `SC-003`：本卡只交候選 commit；禁止 production activation。主線 Review GO 後另行決定 runtime convergence 與啟動授權。

## 執行切片

### `SLICE-SAFE-ACT-RED`

- `traces_to`: `FR-001`, `SC-001`
- 建立最小 red-capable harness：normal aggregate bootstrap 中，Publisher `RunAtLoad` 可在 barrier 驗證前觸發 child publish。
- 必須驗 public/observable contract；不得只 assertion 私有函式名稱。
- 驗證：目標測試在修正前因「barrier 前 child I/O」失敗。

### `SLICE-SAFE-ACT-GREEN`

- `traces_to`: `FR-001`, `FR-002`, `FR-003`, `SC-001`, `SC-002`
- 優先重用現有 `--activate-only`、barrier、manifest authority；實作最小 two-stage／one-shot fail-closed transition。
- 禁止用 sleep、kill、手動 bootout 時序猜測或大 prompt 代替契約。
- 若不用改 source 即可由既有正式入口滿足全部準則，交付 operations proof，不做無意義 code churn。

### `SLICE-SAFE-ACT-VERIFY`

- `traces_to`: `SC-001`, `SC-002`, `SC-003`
- 跑受影響 pytest、`bash -n`、`git diff --check`。
- 保存 RED/GREEN、變更 allowlist、production mutation count=`0`、candidate SHA。
- 交付 `DELIVERED_CANDIDATE`；不得自稱已上 production 或完整 GO。

## Checkpoint 與停止條件

- Checkpoint A：RED 能精確抓到 barrier 前 Publisher child I/O，才可改 code。
- Checkpoint B：GREEN 同時證明 activation-only 無 I/O、normal transition fail closed，才可 commit。
- 同一 blocker 三次停止。
- 若唯一方案需要修改 queue、文章、Writer、lane、production runtime 或直接 normal activation，回 `BLOCKED / SCOPE_EXPANSION`。
- 若出現架構 fork，只列最多兩個候選與證據；不得自行升到 Sol 或擴卡。

## 交付格式

- candidate commit SHA
- changed files
- RED/GREEN commands and results
- production mutations: 必須為 `0`
- residual risks
- evidence path
