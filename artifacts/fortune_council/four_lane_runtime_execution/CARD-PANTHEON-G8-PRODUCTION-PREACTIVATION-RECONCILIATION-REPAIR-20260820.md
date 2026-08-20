---
id: CARD-PANTHEON-G8-PRODUCTION-PREACTIVATION-RECONCILIATION-REPAIR-20260820
chain_id: PANTHEON-G8-PRODUCTION-PREACTIVATION-RECONCILIATION-20260820
parent_card_id: CARD-PANTHEON-G8-PRODUCTION-CANARY-PREACTIVATION-20260820
role: repair
cycle: 1
status: ready
type: source_repair
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: Production 邊界的 authority、runtime transition 與 selector receipt 必須 fail-closed 且零 mutation；規格固定但需新增正式唯讀 seam 與負向測試，使用 GPT-5.5 high。
ownership:
  - scripts/pantheon_g8_production_preactivation.py
  - tests/test_pantheon_g8_production_preactivation.py
  - artifacts/fortune_council/four_lane_runtime_execution/g8_production_preactivation_reconciliation_20260820/**
  - .work/CARD-PANTHEON-G8-PRODUCTION-PREACTIVATION-RECONCILIATION-REPAIR-20260820/**
forbidden_scope:
  - 修改 Publisher、promotion、capacity、runtime activation既有邏輯或其他 source/tests
  - production、queue/state/transaction/registry/manifest/plist/barrier mutation
  - fetch/pull/push/tag、installer、launchctl mutation、promotion apply/finalize、發文或建立 canary
  - 將 remote mismatch或old-live→new-stage一律改判PASS
verification:
  - 正向 authority lineage、old-live→new-stage transition、current exact selector皆PASS
  - diverged remote、非allowlist source drift、mixed live、staged drift、selector零筆/多筆/錯run皆BLOCKED
  - 執行前後 queue/state/transaction/lock/git refs與production artifacts digest不變
  - affected pytest、full new test file、git diff --check通過
  - candidate僅限ownership且worktree clean
evidence_path: artifacts/fortune_council/four_lane_runtime_execution/g8_production_preactivation_reconciliation_20260820/
---

# G8 production preactivation reconciliation repair

## 工作名稱 → 正在做什麼 → 現在狀態

修復 G8 preactivation 判定 seam → 建立零 mutation 的 authority／transition／selector current receipt → `READY TO DISPATCH`

## Root Question

如何讓 preactivation 正確區分「可由既有 production 流程收斂的 planned transition」與真正 drift，並在不開 lock、不碰 production state下，產生綁定 current authority與 exact run的一筆 selector receipt？

## 已確認 blocker

- local source `fe2221bd...`，remote/actor `b8a34451...`；需驗 ancestry與 allowlisted lineage，不能只比較 SHA相等。
- live `b74646c4...`、staged/manifest/actor `b8a34451...`；既有 G8 contract允許 coherent old-live→new-stage transition，不能只比較 live/staged相等。
- staged exact run為 `auto-i18n-en-614aa4dc3542ab2c5637`；既有 dry-run receipt是其他舊 run/base。
- `publish_ready_runs(..., dry_run=True)`會建立 state root與 `publisher.lock`；不可作本卡零 mutation selector seam。
- `collect_ready_runs(...)`可作純讀 selector核心；正式 CLI仍需包裝 immutable snapshot與before/after digest。

## 實作契約

建立 `scripts/pantheon_g8_production_preactivation.py`：

1. 只接受明確 repo/actor/queue/state/live/staged/manifest、required source、origin main與 exact run輸入。
2. Authority：只有 origin為required source祖先、差異全在卡片明示 allowlist且actor/manifest關係可由正式 promotion收斂，才回 `PLANNED_FAST_FORWARD`；diverged或runtime source drift一律 `BLOCKED`。
3. Runtime：只有 live seven完整 coherent old identity、staged seven完整 coherent new identity、new identity等於 actor/manifest authority且符合既有 preactivation transition contract，才回 `OLD_LIVE_TO_NEW_STAGE_READY`；混合／unknown／部分 identity一律 `BLOCKED`。
4. Selector：直接使用既有純讀 collector驗 exact run恰好一筆、complete、candidate/review/run identity一致；不得呼叫 publisher CLI、不得 mkdir/open lock、不得寫 queue/state。
5. 執行前後計算 queue/state/transaction、publisher lock、git refs、live/staged/manifest digest；任何變化即 `BLOCKED / MUTATION_DETECTED`。
6. 輸出 machine-readable receipt只寫 caller指定 evidence path；status只可 `READY_FOR_PRODUCTION_AUTHORIZATION`或`BLOCKED`。

## 測試

- 正向：planned fast-forward + coherent old-live→new-stage + exact single ready run。
- 負向：remote diverged、非allowlist code drift、actor/manifest mismatch、live混合、stage缺服務、selector 0／2筆、錯 exact run、run identity drift。
- mutation tripwire：任何 queue/state/transaction/lock/ref/runtime digest變化必須使測試失敗。
- 驗 formal CLI output schema、exit code與 deterministic digest。

## 停損

- 無法重用既有 collector／transition contract而必須改 Publisher或production workflow：`BLOCKED / SCOPE_EXPANSION`。
- 不得為通過測試放寬 identity、allowlist、selector唯一性或mutation tripwire。
- 完成後只交 candidate；不整合、不啟動production。

## 正式 task 初始 prompt核心契約

```text
你負責 CARD-PANTHEON-G8-PRODUCTION-PREACTIVATION-RECONCILIATION-REPAIR-20260820，role=repair、cycle=1。先 CodeGraph，失敗才限域 rg。只新增卡片指定 preactivation script、tests與evidence。建立正式零 mutation seam：authority ancestry+allowlist、coherent old-live→new-stage transition、使用 collect_ready_runs 的 current exact selector receipt、全路徑 mutation tripwire。禁止修改既有 Publisher/promotion/runtime/capacity邏輯，禁止任何 production、lock、queue/state、git refs、LaunchAgent或remote mutation。跑正向與全部負向、git diff --check；只提交ownership candidate並回報SHA。若需擴 scope立即BLOCKED。
```
