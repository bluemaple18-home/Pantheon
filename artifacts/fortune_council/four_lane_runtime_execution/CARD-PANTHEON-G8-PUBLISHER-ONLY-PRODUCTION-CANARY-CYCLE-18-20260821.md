---
id: CARD-PANTHEON-G8-PUBLISHER-ONLY-PRODUCTION-CANARY-CYCLE-18-20260821
chain_id: PANTHEON-G8-PRODUCTION-READINESS-20260820
parent_card_id: CARD-PANTHEON-G8-REPAIRED-SOURCE-PROMOTION-STAGING-CYCLE-17-20260821
role: implementation
cycle: 18
status: ready
type: production_canary
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 規格與 exact run 已固定，但包含 production LaunchAgent、單筆內容 transaction、tag 與 push；採 strict/core-bounded 跑道。
authorized_exact_run_id: auto-i18n-en-614aa4dc3542ab2c5637
authorized_target: ASTRO-BASE-01:en
traces_to:
  - SC-G8-C18-001
  - SC-G8-C18-002
  - SC-G8-C18-003
  - SC-G8-C18-004
ownership:
  - .work/CARD-PANTHEON-G8-PUBLISHER-ONLY-PRODUCTION-CANARY-CYCLE-18-20260821/**
  - bounded Publisher-only activation receipt
  - authorized exact-run transaction, release commit, annotated tag and fast-forward push
forbidden_scope:
  - 修改 source、tests、rules、queue/state/transaction 內容或手改 plist/barrier
  - normal aggregate activation、其他六服務 child I/O、第二筆 run
  - promotion、restaging、force push、非 fast-forward push、無界 retry
  - 新建 Repair／Reviewer／replacement task；有 blocker 回主線
evidence_path: .work/CARD-PANTHEON-G8-PUBLISHER-ONLY-PRODUCTION-CANARY-CYCLE-18-20260821/
---

# G8 Publisher-only 單筆 production canary（Cycle 18）

## 工作名稱 → 正在做什麼 → 現在狀態

`G8 Publisher-only production canary` → 從 Cycle 17 已驗收的七服務 staging 執行唯一一筆正式 Publisher canary → `READY / USER AUTHORIZED`

## Root Question

能否保持其他六服務 activation-only、零 child I/O，只透過正式 Publisher-only 入口發布 `auto-i18n-en-614aa4dc3542ab2c5637`，完成唯一 transaction → release commit → annotated tag → fast-forward push，且沒有第二筆副作用？

## 鎖定 authority

- Cycle 17 evidence commit：`ad49eccf1d`。
- Cycle 17 終態：`STAGED / NO CANARY`。
- source／origin/main／actor：`c05929f2a7dac86e94aaeaa5ab6c5455892f5f77`。
- runtime manifest digest：`e3c393bb18a55eba1c8c6cb9e92abfb63b4241936dc78772bfaa5ec952177d32`。
- runtime identity digest：`db8c1691bb5433b23a4803743782d686d8779ef4fec5d5b7d1cb9e038092999e`。
- generation：`g17-c05929f2a7-20260821T827804Z`。
- stage digest：`d63db21a621fbf5eed8c352ea8d6f0769a1bdb78edbddd3b61d982a40ae61bd0`。
- canonical Python：`/Users/mattkuo/.local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3.12`。
- authorized run：`auto-i18n-en-614aa4dc3542ab2c5637`；`PANTHEON_PUBLISH_MAX_RUNS=1`。
- Cycle 17 queue snapshot：140 runs，digest `58d51ecd0facb43b896c11bdbb8f13002829aedc91d1d38737e8160244357ac0`。
- Cycle 17 final receipt：`.work/CARD-PANTHEON-G8-REPAIRED-SOURCE-PROMOTION-STAGING-CYCLE-17-20260821/final-receipt.json`。
- 使用者已明確要求持續開卡、派工、監工；本授權只包含本卡唯一 bounded canary。

## 成功準則

- `SC-G8-C18-001`：任何 Publisher mutation 前，remote／actor／manifest／stage／barrier／canonical Python 與 Cycle 17 receipt 全部精確匹配；live 七服務維持 loaded/no-PID。
- `SC-G8-C18-002`：Publisher plist、stage receipt、dry-run selector 三者只含 authorized run，`max-runs=1`；其他六服務 bytes、identity、PID 前後不變。
- `SC-G8-C18-003`：正式 `--activate-publisher-only` 只產生一筆 transaction；terminal 後 release commit、annotated tag、remote main、ledger、公開 locale artifact 完全對齊。
- `SC-G8-C18-004`：第二筆 selection／transaction／content mutation／tag／push 均為 0；完成後 Publisher 回到 fail-closed 非執行狀態，evidence 可重現。

## 固定 forward-only 切片

### `SLICE-G8-C18-PREFLIGHT`

- blocking edge：無；目前 frontier。
- 只讀驗 Cycle 17 evidence hashes、current remote／actor／manifest／stage／barrier／live／queue／ledger／tags／content baseline。
- 使用正式 readiness／capacity／Publisher dry-run seam；不得重跑 capacity exercise、不得 promotion 或 restage。
- selector 非唯一、authorized run 已發布、任一 identity drift 或 gate 非 PASS：`BLOCKED / NO CANARY`，零 mutation停止。

### `SLICE-G8-C18-ACTIVATE-PUBLISHER`

- blocking edge：PREFLIGHT 必須全 PASS。
- 先鎖 exact command artifact 與單次 authorization。
- 唯一允許 mutation：target actor 的正式 Publisher installer `--activate-publisher-only`；不得 direct Python normal path。
- activation 後監看唯一 transaction；不 retry、不換 selector、不啟動其他六服務。

### `SLICE-G8-C18-POSTCHECK`

- blocking edge：唯一 transaction 必須 terminal，outcome 明確。
- 驗 release commit／annotated tag／remote main／ledger／public artifact；比較其他六服務、queue、transactions、tags 前後差異。
- 保存 exact counts、production mutation receipt、evidence manifest；不 commit，由主線保存。

## 停止條件

- 任一 preflight 非 PASS、identity 或 selector drift：立即停止，零 Publisher mutation。
- activation 後第二筆副作用：立即 bootout Publisher、保全現場、停止；不得重試。
- transaction、push 或 rollback outcome unknown：`PARTIAL`，不得手改 queue/state 或重送。
- 同一 blocker第三次失敗即停；本卡只允許一次正式 activation invocation。
- 終態只可：`GO`、`BLOCKED / NO CANARY`、`PARTIAL / STOPPED`。

## 交付

- exact source／remote／actor／manifest／stage／barrier／Python identities。
- formal preflight、selector、authorization、transaction、release commit、tag、remote、ledger、public artifact receipts。
- other-six before/after、queue/transaction/tag delta、所有 invocation counts。
- `jq -e`、evidence hashes、`git diff --check`。
