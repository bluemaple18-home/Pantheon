---
id: CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-PRODUCTION-CANARY-20260818
chain_id: PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-20260818
parent_card_id: CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-ACTIVATION-REVIEW-20260818
role: implementation
cycle: 1
status: ready
type: production_canary
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 已固定 exact-run、Publisher-only activation 與停損契約，但涉及 production promotion、LaunchAgent、內容 transaction、tag 與 push；使用 GPT-5.5 high，不使用 5.6。
authorized_exact_run_id: auto-i18n-en-614aa4dc3542ab2c5637
authorized_target: ASTRO-BASE-01:en
ownership:
  - .work/CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-PRODUCTION-CANARY-20260818/**
  - production runtime promotion transaction and receipts
  - Pantheon aggregate activation-only and Publisher-only bounded activation receipts
  - authorized exact-run content transaction, release commit, annotated tag and fast-forward push
forbidden_scope:
  - 修改 source、tests、rules、Writer、模型路由、lane 邏輯、queue/state/transaction 內容或手改 plist/barrier
  - 處理第二筆 run、啟動 aggregate normal scheduler、將其他六服務切到 normal
  - force push、非 fast-forward push、無界 retry、另開 Repair／Reviewer／replacement task
  - 用舊 readiness/capacity、單次狀態文案或 direct exact-run 冒充本入口 canary
verification:
  - current source capability READY 且 canary_created=false；current capacity PASS
  - source/origin/main/actor/manifest/staged/live identity exact matching
  - aggregate activation-only 後七服務 child I/O 零次且其他六服務維持 activation-only
  - Publisher-only staged plist max-runs=1 且 exact-run receipt/child args 完全等於 authorized run
  - pre-activation dry-run selector 只含 authorized run
  - transaction terminal、release commit、annotated tag、remote main 對齊，且無第二筆 publish
  - postcheck 其他六服務 plist bytes/launch identity 不變；Publisher bounded exact identity 可追溯
evidence_path: .work/CARD-PANTHEON-PUBLISHER-ONLY-BOUNDED-PRODUCTION-CANARY-20260818/
---

# Publisher-only bounded production canary

## 工作名稱 → 正在做什麼 → 現在狀態

執行 Publisher-only 單筆 production canary → 以正式 LaunchAgent 入口發布一筆鎖定翻譯 → `READY / USER AUTHORIZED`

## Root Question

能否在其他六服務保持 activation-only 的前提下，使用已 Review GO 的 Publisher-only bounded activation 正式入口，只發布 `auto-i18n-en-614aa4dc3542ab2c5637`，並完成 transaction → tag → push 且零第二筆副作用？

## 已知事實與授權

- Implementation、獨立 Review、Repair-1、targeted re-review 已完成；re-review verdict `GO`。
- 主線整合 SHA 在本卡建立前為 `ecb2dfb17c`；本卡 commit 將成為 canary exact source。
- 原 F001 已修復：stale/missing/extra/value mismatch exact-run receipt 皆在 launchctl mutation 前 fail closed。
- 使用者於 2026-08-18 明確要求「開卡派工做吧」，授權本卡一筆 production canary。
- 唯一授權 run：`auto-i18n-en-614aa4dc3542ab2c5637`，target `ASTRO-BASE-01:en`；此前唯讀 triage 為 `ALLOW_EXACT`。

## 成功準則

- `SC-PC-001`：所有 production mutation 前 current capability receipt 為 `READY`、capacity receipt 為 `PASS`，且 `canary_created=false`。
- `SC-PC-002`：promotion 與 aggregate activation-only 收斂到本卡 exact source；七服務 zero child I/O，其他六服務仍 activation-only。
- `SC-PC-003`：Publisher stage receipt、plist child args、dry-run selector 三者都只等於 authorized run，`max-runs=1`。
- `SC-PC-004`：正式 Publisher-only activation 只引發一筆 translation transaction；無 create/rewrite/其他 translation。
- `SC-PC-005`：transaction closed、release commit、annotated tag、remote main、公開 locale artifact 與 ledger 對齊。
- `SC-PC-006`：其他六服務 plist bytes 與 launch identity 前後不變；queue 不新增非 canary run；無第二筆 content mutation。

## 執行切片與 blocking edges

### `SLICE-PC-PREFLIGHT`

- `traces_to`: `SC-PC-001`, `SC-PC-003`
- 鎖定 source、origin/main、actor、manifest、LaunchAgents、queue/run、ledger、transactions、tag/content baseline。
- 重新跑 source tests、capability readiness、capacity proof與 exact-run dry-run。
- authorized run 若已 published、非 ready、selector 不是唯一一筆或任何 gate 非 PASS/READY，零 production mutation停止。

### `SLICE-PC-CONVERGE`

- `traces_to`: `SC-PC-001`, `SC-PC-002`
- 被 PREFLIGHT PASS 阻擋。
- 只允許 origin/main fast-forward 到本卡 source；以正式 promotion `plan → apply → postcheck → finalize` 收斂 actor/manifest。
- 重新 stage 七服務並執行 aggregate activation-only；驗證 matching barrier、zero child I/O、七服務 identity。

### `SLICE-PC-PUBLISHER-ONLY-CANARY`

- `traces_to`: `SC-PC-003`, `SC-PC-004`
- 被 CONVERGE PASS 阻擋。
- 用 Publisher installer 正式 stage：`PANTHEON_PUBLISH_MAX_RUNS=1`、`PANTHEON_PUBLISH_EXACT_RUN_ID=auto-i18n-en-614aa4dc3542ab2c5637`。
- 驗 stage receipt/plist/dry-run selector後，僅呼叫正式 `--activate-publisher-only`；不得直接執行 Publisher Python normal path冒充 canary。
- 等待唯一 transaction terminal；不得 retry 第二筆或改 selector。

### `SLICE-PC-POSTCHECK`

- `traces_to`: `SC-PC-004`, `SC-PC-005`, `SC-PC-006`
- 被唯一 transaction terminal 阻擋。
- 驗 release commit/tag/push/ledger/public artifact；比較 queue、transactions、tags與其他六服務前後 identity。
- 保存 production mutation receipt與 evidence commit；結果只能 `GO` 或帶 exact blocker 的 `BLOCKED/PARTIAL`。

## 正式入口

- `scripts/pantheon_content_runtime_promotion.py`
- `scripts/pantheon_content_runtime_manifest.py`
- `scripts/pantheon_content_capacity_guard.py`
- `scripts/pantheon_writer_vnext_runtime_activation_capacity.py`
- `scripts/pantheon_writer_vnext_runtime_activation_readiness.py`
- `<ai-core-root>/scripts/production_canary_readiness_gate.py`
- `scripts/install_agy_gemini_coordinator_launchd.sh`
- `scripts/install_agy_content_publisher_launchd.sh`
- `scripts/install_pantheon_content_capacity_guard_launchd.sh`
- `scripts/agy_content_publisher.py` 僅限 dry-run/verification；production publish 必須由 LaunchAgent Publisher-only 入口觸發

## 停損與回復

- readiness/capacity/source test/dry-run 任一非 PASS/READY：零 production mutation停止。
- promotion identity drift：依正式 rollback bundle 回復並停止。
- aggregate activation-only 非 zero child I/O 或 matching barrier失敗：rollback/停止，不做 Publisher-only。
- Publisher stage/receipt/plist/exact selector 任一不一致：零 Publisher mutation停止。
- Publisher-only activation 後出現第二筆 selection/transaction/content/tag/push：立即 bootout Publisher，保全現場，不重試。
- transaction outcome unknown、push outcome unknown 或 rollback failure：`PARTIAL`，保留 transaction/bundle，不手改 queue/state。
- 同一 blocker第三次立即停止。

## 交付格式

- exact source/origin/main/actor/manifest/plist identities
- capability/capacity receipts and digests
- authorized selector與 transaction evidence
- release commit、version、annotated tag、remote main、public artifact
- other-six before/after identity與第二筆 mutation count
- production mutation receipt、evidence commit SHA、worktree clean
