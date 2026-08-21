---
id: CARD-PANTHEON-G8-LIVE-PUBLISHER-IDENTITY-RECONCILIATION-20260821
chain_id: PANTHEON-G8-PRODUCTION-PREACTIVATION-RECONCILIATION-20260820
parent_card_id: CARD-PANTHEON-G8-PUBLISHER-ONLY-PRODUCTION-CANARY-CYCLE-18-20260821
role: repair
cycle: 2
status: ready
type: production_reconciliation
thickness: strict
risk: critical
model: gpt-5.5
reasoning: high
ownership:
  - .work/CARD-PANTHEON-G8-LIVE-PUBLISHER-IDENTITY-RECONCILIATION-20260821/**
forbidden_scope:
  - source、tests、queue、publisher state、transaction、content、registry、tag、push mutation
  - normal activation、Publisher child execution、canary、retry、replacement thread
  - 手動 copy/edit plist 或繞過正式 installer、capacity、aggregate、barrier gate
evidence_path: .work/CARD-PANTHEON-G8-LIVE-PUBLISHER-IDENTITY-RECONCILIATION-20260821/
---

# G8 live Publisher identity reconciliation

## 工作名稱 → 正在做什麼 → 現在狀態

收斂 live Publisher 舊 identity → 以正式 aggregate `--activate-only` seam 更新七個 inert LaunchAgent → `READY TO DISPATCH TO EXISTING REPAIR THREAD`

## Root Question

能否在零 child I/O、零發文、零 queue/state/transaction 變更下，讓 live 七服務收斂到 Cycle 17 staged authority，解除 Cycle 18 的 `LIVE_PUBLISHER_IDENTITY_MISMATCH`？

## 鎖定 authority

- source／origin/main／actor：`c05929f2a7dac86e94aaeaa5ab6c5455892f5f77`
- manifest digest：`e3c393bb18a55eba1c8c6cb9e92abfb63b4241936dc78772bfaa5ec952177d32`
- runtime identity digest：`db8c1691bb5433b23a4803743782d686d8779ef4fec5d5b7d1cb9e038092999e`
- generation：`g17-c05929f2a7-20260821T827804Z`
- exact run：`auto-i18n-en-614aa4dc3542ab2c5637`
- Cycle 18 evidence commit：`aa888c548b`

## 已確認 blocker

Cycle 18 正式 preflight 在任何 activation 前 fail-closed。live Publisher 仍是 `b74646c4... / g8-b746... / f78faa...`；staged Publisher 是上述 Cycle 17 authority。正式 staged Publisher 是 normal bounded plist；禁止直接覆蓋 live，否則 `RunAtLoad` 可能執行 exact run。唯一允許的 mutation seam 是既有 aggregate installer `--activate-only`，由它對 live 七服務注入 `--activation-only`、完成 aggregate/barrier 驗證並保持 child I/O 為零。

## 執行契約

1. 只在原 Repair thread `01a01e5e-025e-7721-8cc9-0c72d66dbc86` 執行；不得建立第二個 Repair thread。
2. 先驗 source/actor clean、manifest、staged 七 plist/readiness、exact run 唯一性、live 七服務現況及 Cycle 18 零 mutation evidence。
3. 以 `TMPDIR=/private/tmp` 執行正式 capacity/preactivation preflight；任一非 `PASS/READY` 即 `BLOCKED / NO MUTATION`。
4. 保存 live 七 plist、barrier、queue/state/transaction、actor refs、公開 artifacts 的 before snapshot。
5. 正式 `--activate-only` 只允許一次。必須從 `<runtime-root>/actor` 使用既有 `scripts/install_agy_gemini_coordinator_launchd.sh --activate-only`；禁止手動 plist mutation、normal activation或 retry。
6. 驗 live 七服務皆為 current activation-only identity、aggregate PASS、barrier綁定 current manifest、loaded/no-PID；Publisher child invocation 必須為 0。
7. 驗 queue仍為 140、exact run未被消耗，state/transaction/content/registry/tag/push/ref delta皆為 0。
8. 寫 machine-readable before/after、command、aggregate/barrier、exact-counts、final receipt；不得 commit source或production artifacts。

## 停損

- preflight非 PASS、staged drift、legacy barrier不 coherent、任何 child PID/I/O、任何 protected delta：立即 `BLOCKED`，不得 retry。
- 若正式 seam 需要 source repair：只回 `BLOCKED / SOURCE_REPAIR_REQUIRED`，不可在本卡改 code。

## 完成定義

只可回其中一種：

- `RECONCILED / NO CANARY`：七服務 current activation-only、loaded/no-PID，所有 protected delta為 0。
- `BLOCKED / NO CANARY`：保留 failure/rollback evidence，production child invocation為 0。

