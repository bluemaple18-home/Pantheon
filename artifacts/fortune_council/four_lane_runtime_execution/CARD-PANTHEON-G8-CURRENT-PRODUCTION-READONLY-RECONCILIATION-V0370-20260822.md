---
id: CARD-PANTHEON-G8-CURRENT-PRODUCTION-READONLY-RECONCILIATION-V0370-20260822
chain_id: PANTHEON-G8-CURRENT-PRODUCTION-READONLY-RECONCILIATION-V0370-20260822
role: production-readonly-reconciliation-auditor
status: ready
type: production_reconciliation
thickness: strict
risk: critical
model: gpt-5.5
reasoning: high
model_reason: Production 唯讀 reconciliation 屬 strict、規格固定且需跨 Rule 24／25 與狀態契約做高影響 fail-closed 判定，使用 GPT-5.5 high；不升 Sol，避免不必要額度消耗。
release_baseline: b0950d4c436cc902e17ac110b579b35b84aa53e4
release_tag: v0.3.370
production_read_authorized: true
production_mutation_authorized: false
canary_authorized: false
ownership:
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-CURRENT-PRODUCTION-READONLY-RECONCILIATION-V0370-20260822-RESULT.md
  - artifacts/fortune_council/four_lane_runtime_execution/g8_current_production_readonly_reconciliation_v0370_20260822/**
forbidden_scope:
  - 修改 repo source、tests、config、registry、metadata、既有 evidence 或 handoff
  - 修改 actor、manifest、queue、state、transaction、private stage、live plist、barrier、launchctl 或 git refs
  - promotion、reset、Capacity preflight/install、activation、restage、canary、Publisher child、deploy、tag、push、schedule 或 steady autonomy
  - 沿用 historical readiness、status 文案或單次結果冒充 current production evidence
verification:
  - HEAD、origin/main 與 peeled v0.3.370 release authority 精確核對
  - CodeGraph indexed HEAD 與 task-semantic query 可重現
  - production 保護面 before/after digest 與 launchctl snapshot 證明零 mutation
  - Rule 24、Rule 25、Cycle 29–34 與八態 state contract 形成唯一 gate matrix
  - verdict 僅可 GO、NO-GO 或 UNKNOWN；任何 contradiction fail closed
evidence_path: artifacts/fortune_council/four_lane_runtime_execution/g8_current_production_readonly_reconciliation_v0370_20260822/
result_path: artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-CURRENT-PRODUCTION-READONLY-RECONCILIATION-V0370-20260822-RESULT.md
---

# G8 v0.3.370 current production 唯讀 reconciliation

## 工作名稱 → 正在做什麼 → 現在狀態

G8 current production read-only reconciliation → 以 release `v0.3.370` 對帳當下 production phase、Cycle 29–34、Rule 24／25 與 canary authorization boundary → `READY / READ-ONLY ONLY`

## Root Question

在完全不改變 production、runtime、Git refs 與既有 evidence 的前提下，當下 production 是否唯一匹配 G8 八個合法 state 之一，且 v0.3.370、Publisher exit `78` provenance、Rule 24 與 Rule 25 evidence 都是 current、完整且彼此一致，足以回主線請求一次 bounded canary 人工授權？

## Authority Boundary

- 唯一 release baseline：`b0950d4c436cc902e17ac110b579b35b84aa53e4`；peeled `v0.3.370` 必須精確指向此 commit。
- 換手 commit：`9f48abaadc6474859f1e6f805ad36086b84e8700`；`HEAD` 與 `origin/main` 必須一致且包含 release baseline。
- 本卡只授權讀 production truth，以及在本卡唯一 evidence／RESULT 路徑寫新證據。
- Rule 24／25、reconciler、readiness generator與 evidence consumer 都沒有 production mutation authority。
- 歷史 Cycle 29–34 只提供 lineage、已知 defect、expected invariants與比較基準；其時間戳、generation、correlation、receipt 或 GO 文案不得直接填入 current 欄位。

## 必讀契約與 Evidence

1. `handoff_20260822_g8_exit78_release_v0370.md`
2. `artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-G8-RELEASE-STATE-CONTRACT-V1-20260821.md`
3. `artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-G8-TRANSITION-EDGE-MAP-V1-20260821.md`
4. `artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-G8-CYCLE-29-32-SHADOW-REPLAY-20260821.md`
5. `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-QUIESCENT-CAPACITY-STAGE-CYCLE-29-20260821-RESULT.md`
6. `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-PUBLISHER-ONLY-CANARY-CYCLE-30-20260821-RESULT.md`
7. `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-POST-FIX-PRECANARY-READINESS-CYCLE-31-20260821-RESULT.md`
8. `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-RUNTIME-PROMOTION-STAGE-CONVERGENCE-CYCLE-32-20260821-RESULT.md`
9. `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-TRANSITION-TO-CANARY-READY-CYCLE-33-20260822-RESULT.md`
10. `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-PUBLISHER-RESET-BOOTSTRAP-RCA-REPAIR-CYCLE-34-20260822-RESULT.md`
11. `artifacts/fortune_council/four_lane_runtime_execution/REPAIR-PANTHEON-G8-ACTIVATION-ONLY-EXIT-78-PROVENANCE-20260822-RESULT.md`
12. `artifacts/fortune_council/four_lane_runtime_execution/REVIEW-PANTHEON-G8-ACTIVATION-ONLY-EXIT-78-CONTRACT-CLARIFICATION-20260822-RE-REVIEW-RESULT.md`
13. `<ai-core-root>/rules/24-storage-capacity-safety.md`
14. `<ai-core-root>/rules/25-production-canary-readiness.md`

## 執行契約

### 1. Bootstrap 與 Code Context

1. 驗本卡實體存在、工作樹 tracked diff 為零；既存未追蹤檔只列名，不讀寫、不 stage、不刪除。
2. 唯讀驗 `HEAD`、`origin/main`、release ancestry、annotated tag object與 peeled tag。
3. CodeGraph `indexed-head` 必須等於當下 `HEAD`，並執行 task-semantic query：
   `G8 current production read-only reconciliation, release state matching, production preactivation mutation tripwire, Publisher reset receipt provenance, Capacity and Rule 25 readiness`。
4. Graph entry points 只作 candidate；限域以 source 確認：
   - `scripts/pantheon_g8_production_preactivation.py`
   - `scripts/pantheon_content_capacity_guard.py`
   - `scripts/pantheon_content_capability_receipt.py`
   - 兩個既有 launchd installer的 read-only／preflight seam

### 2. 鎖定 Production 保護面

在任何 collector 前後各做一次同一集合的 snapshot；至少包含：

- runtime actor HEAD／worktree status／remote identity；
- runtime manifest bytes、digest、generation、runtime identity digest；
- queue、state、transaction、Publisher lock與barrier；
- 七份 live plist、private stage完整 tree、stage controls與 receipts；
- launchctl 七 labels 的 loaded state、PID、observed plist path、last exit status；
- Git refs、release tag與 tracked working tree；
- evidence output 路徑不得位於或 alias 任一上述保護 root。

before／after 任一保護面 bytes、tree digest、refs 或 runtime identity 改變，固定 `NO-GO / MUTATION_DETECTED`。只能新增本卡 evidence 與 RESULT。

### 3. Current State Observation

建立一份 timestamped `release-observation.json`，逐 label、逐 scope記錄 state contract 的 deterministic fields，不得用 cohort 摘要蓋掉單一 label：

- `activation_mode`、plist present／digest／path、loaded、PID policy、`RunAtLoad`、`StartInterval`、`KeepAlive`；
- live／target generation relation、target stage policy、exact run ID、`max-runs=1`；
- current required receipt set、receipt digest、timestamp、correlation與generation；
- Publisher reset receipt freshness、owner-only mode、target manifest／runtime identity、old-live identity、post-reset Publisher identity，以及 other-six pre/post unchanged proof；
- exit `78` 若存在，必須同時證明 target newer、same correlation、loaded／no-PID、exact path與 workload child未執行；缺任一項為 `UNKNOWN`，衝突為 `DIVERGED`。

使用既有正式唯讀 reconciler `scripts/pantheon_g8_production_preactivation.py` 對 current production roots執行一次；其 `mutation_tripwire` 必須 `PASS`、`production_mutation=false`。不得加 `--allow-source-drift` 掩蓋 authority mismatch；若 source 不一致，保留原始 `BLOCKED` 結果。

### 4. Cycle 29–34 Currentness Matrix

逐 cycle 輸出：歷史主張、current 可驗證欄位、current artifact、timestamp、generation、correlation、是否可採信，以及失效原因。至少驗證：

- Cycle 29：Capacity two-cycle／quiescent與 stage evidence 是否仍對當下 generation有效；
- Cycle 30：Publisher exact-run terminal、retry/failure/recovery與 transaction boundary；
- Cycle 31：synthetic readiness只可證 capability seam，不可證 current runtime authority；
- Cycle 32：actor／manifest／stage convergence與 source authority；
- Cycle 33：`ST-TARGET-STAGED` rollback終態是否仍 current，failure receipt不得冒充 reset success receipt；
- Cycle 34：v0.3.370 repair是否已存在於 current production actor；code release存在不等於 runtime adoption。

### 5. Rule 24 Matrix

Rule 24 最終欄只可 `PASS` 或 `NO-GO`。必須有當下可重現證據：

- 寫入路徑盤點、`max_bytes`、`max_file_count`、正常每小時增長率、尖峰視窗、回收時間、保留／輪替與 cleanup allowlist；
- host free／total、專案 bytes／files、RSS、swap基線；
- 兩個代表性 synthetic 完整週期、每週期前後增量、1h／1d／retention峰值；
- 實際 cleanup回收與 stop-loss／停用自動重啟演練；
- current monitor頻率與自動停損條件。

可透過既有 `scripts/pantheon_content_capability_receipt.py apf-004-readiness` 在本卡 evidence output內生成全新 synthetic package；它不得讀寫 production roots，且不得把 historical package複製成 current。任一缺欄、unknown或 host reserve不足固定 `NO-GO`。

### 6. Rule 25 Matrix

Rule 25 必須逐一驗 `create → run → select → publish → transaction → tag → push`：

- 每段正式 production entrypoint、I/O continuity、同一 identity／execution line／correlation；
- 每段獨立 current `PASS` 正向 artifact與獨立 `BLOCKED` fail-closed artifact；
- official receipt必須 `canary_created=false`、`production_mutation=false`；
- official gate回 `READY`，missing-step／wrong-correlation fixture回 `BLOCKED`；
- readiness package必須對當下合法 state與generation有效。若尚未到 `ST-CANARY-READY`，即使 synthetic capability全綠，也固定是 phase-currentness `NO-GO`。

不得執行真正 create/run/publish/transaction/tag/push來證明 readiness；只允許正式入口的 synthetic／dry-run probe。

## 唯一 Gate Matrix

RESULT 必須有且只有一張總表，至少含下列 rows：

| gate | 必要判定 |
| --- | --- |
| Release authority | `HEAD=origin/main`、包含 baseline、peeled tag精確 |
| Mutation tripwire | protected before/after完全相同 |
| State uniqueness | 八態恰好匹配一態；缺證據 `UNKNOWN`、多態 `AMBIGUOUS` |
| Runtime source adoption | production actor確實包含 v0.3.370 repair |
| Publisher reset provenance | current／target-newer／same-correlation／other-six unchanged |
| Launchctl topology | 七 labels identity、exact path、loaded/PID／exit符合 matched state |
| Target stage／selector | generation、stage inventory、exact run、max-runs current |
| Cycle 29–34 | 歷史 evidence與 current truth分離，無 stale reuse |
| Rule 24 | 完整 current `PASS`；未知即 `NO-GO` |
| Rule 25 | 七段 current且 official `READY`；phase不符即 `NO-GO` |
| Canary boundary | `canary_created=false` 且無 mutation authority |

總 verdict：

- `GO`：所有 rows current、一致且 matched state精確為 `ST-CANARY-READY`；完成後立即停止，回主線索取一次 bounded canary人工授權。
- `NO-GO`：任一明確 mismatch、stale evidence、Rule 24／25缺口、source adoption缺口或 mutation tripwire失敗；不得自行修復或跨入 mutation卡。
- `UNKNOWN`：current evidence不足以判定且無明確 contradiction；列出最小缺口後停止。

不得輸出模糊 `READY` 取代上述三值，也不得把 `CONVERGED` 單獨等同 canary authorization。

## 交付格式

只新增：

1. `artifacts/fortune_council/four_lane_runtime_execution/g8_current_production_readonly_reconciliation_v0370_20260822/` 下的 current raw／normalized evidence、before／after snapshots、gate matrix與 command receipt；
2. `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-CURRENT-PRODUCTION-READONLY-RECONCILIATION-V0370-20260822-RESULT.md`。

RESULT 必須明列：root question、matched state、總 verdict、逐 gate evidence locator／digest／timestamp、mutation accounting、未驗證項、blocker、下一步與禁止延伸事項。完整命令放 evidence，不把本機絕對路徑寫成跨機命令。

## Stop-loss

- 同一 blocker第三次失敗立即停止，不做第四次。
- 任一 collector需要 production write、sudo、installer mutation、launchctl mutation或手改 receipt，立即 `NO-GO`。
- 任一 scope／identity／generation／correlation矛盾 fail closed；不得猜 phase。
- verdict `GO` 也不授權 canary；`NO-GO／UNKNOWN` 也不授權 repair、deploy或 transition。

## 正式 Task 初始 Prompt 核心契約

```text
你負責 CARD-PANTHEON-G8-CURRENT-PRODUCTION-READONLY-RECONCILIATION-V0370-20260822，role=production-readonly-reconciliation-auditor。完整讀卡、handoff、State Contract、Edge Map、Cycle 29–34 RESULT與 Rule 24／25。先驗 clean tracked tree、HEAD／origin/main／peeled v0.3.370，再確認 CodeGraph indexed HEAD並做 task-semantic query。只讀當下 actor／manifest／queue／state／transaction／live／stage／launchctl／receipts，執行既有 read-only reconciler與本卡 evidence內 synthetic readiness；before/after mutation tripwire必須證明保護面完全不變。只可新增本卡 evidence目錄與唯一 RESULT；禁止 promotion、reset、Capacity preflight/install、activation、restage、canary、Publisher child、deploy、tag、push、schedule、steady autonomy，以及修改 source/tests/config/production。產出唯一 gate matrix與 GO／NO-GO／UNKNOWN；只有所有 current gates一致且 state=ST-CANARY-READY才可 GO，且 GO 後立刻停止等人工 bounded canary授權。
```
