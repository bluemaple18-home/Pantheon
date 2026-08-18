---
id: CARD-PANTHEON-G8-FOUR-LANE-PRODUCTION-CANARY-20260818
chain_id: PANTHEON-FOUR-LANE-PRODUCTION-RECOVERY-20260818
parent_card_id: CARD-PANTHEON-G7-PREACTIVATION-OLD-LIVE-TO-NEW-STAGE-TRANSITION-REPAIR-20260818
supersedes:
  - CARD-PANTHEON-PRODUCTION-RUNTIME-CONVERGENCE-REWRITE-CANARY-20260818
role: implementation
cycle: 8
status: ready
type: production_canary
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 契約與正式入口已固定，但 production promotion、LaunchAgent、單筆內容 transaction、tag 與 push 均屬高回退成本操作；使用 GPT-5.5 high，不使用 5.6。
ownership:
  - .work/CARD-PANTHEON-G8-FOUR-LANE-PRODUCTION-CANARY-20260818/**
  - production readiness and capacity receipts
  - production runtime promotion transaction and rollback bundle
  - seven-service activation-only staging and activation receipts
  - one authorized four-lane publish transaction, annotated tag and fast-forward push
forbidden_scope:
  - 修改 source、tests、rules、Writer、模型路由、lane 邏輯、queue/state/transaction 內容或手改 plist/barrier
  - 第二筆 canary、第二個 selector、無界 retry、force push 或非 fast-forward push
  - 以舊 readiness/capacity/evidence、狀態文案或 direct Python normal path冒充正式 production canary
  - 同 blocker 第四次 production retry；任何新 blocker 必須先停止並交回主線
verification:
  - current source tests與git diff check通過
  - current seven-step capability receipt READY且canary_created=false
  - current storage/capacity gate PASS，包含兩週期、回收與停損證據
  - source/origin/main/actor/manifest/staged/live identity exact match
  - preactivation old-live aggregate loaded/no-PID且new staged seven coherent
  - aggregate activation-only zero child I/O，其他服務不得先做內容 mutation
  - canonical selector恰好一筆，Publisher transaction terminal，commit/tag/remote/public artifact可追溯
  - 第二筆 publish、第二個transaction、跨lane ownership與未完成transaction皆為零
evidence_path: .work/CARD-PANTHEON-G8-FOUR-LANE-PRODUCTION-CANARY-20260818/
---

# G8 four-lane production canary

## 工作名稱 → 正在做什麼 → 現在狀態

G8 四線正式發文驗收 → 用已 Review GO 的 transition contract 跑一筆完整 production canary → `READY / USER AUTHORIZED`

## Root Question

能否只用既有正式入口，讓舊 live 七服務 aggregate 安全轉換到本卡 exact source 的新 staged aggregate，完成一筆四線 publish，並以同一 correlation 證明 `create → run → select → publish → transaction → tag → push`？

## 使用者授權

- 使用者於 2026-08-18 明確要求「開卡派工做吧」，授權本卡 push、production runtime convergence、LaunchAgent staging/activation、單筆四線 canary、transaction、annotated tag 與 fast-forward push。
- 授權不包含 source 現場修補、手動 queue/transaction/plist/barrier 編輯、第二筆 canary、force push 或繞過 readiness/capacity gate。

## 已鎖定事實

- G6 source：`b8a34451e7a2b10a9e7ce1f11f366250cc67d87b`；promotion 已 COMMITTED。
- G6 blocker：preactivation 將 old live identity 錯當成 post-activation new target identity，後續另發現 preflight PASS 可繞過 PID transition validation。
- G7 final Reviewer GO candidate：`f3ab708ef03ba77d3496b0d67488ceed3bc2b026`。
- G7 已整合到 main：`94226be7a8cac95788a5cf22eb5f08f8e771384a`；50 capacity tests與75 runtime/promotion tests通過。
- G6 未 activation、未 publish；transaction/tag/public artifact與第二筆 publish皆為零。
- 本卡 source commit 將是新的 exact production authority；不得把 G6 receipt 搬來補 current PASS。

## 需求與成功準則

- `FR-G8-01`：所有 production mutation 前，current capability receipt 必須覆蓋七步正式入口、I/O、identity/correlation、PASS與BLOCKED evidence，gate 回 `READY` 且 `canary_created=false`。
- `FR-G8-02`：storage/capacity 必須以 current source完成兩週期、峰值、回收與停損驗證；任一未知為 `NO-GO`。
- `FR-G8-03`：preactivation 必須同時證明 old live seven 為 coherent inert loaded/no-PID aggregate，new staged seven為 coherent current target aggregate；任何 PID、混合 identity、marker/digest/barrier drift皆在 stage destination write 前拒絕。
- `FR-G8-04`：只有 post-activation 才要求 live seven等於new target；activation-only 必須 zero child I/O。
- `FR-G8-05`：canonical selector只能鎖一筆 authorized run；正式 Publisher/四線入口只能造成一筆 transaction、commit、annotated tag與fast-forward push。
- `SC-G8-01`：source、origin/main、actor、manifest、stage、live identity exact match。
- `SC-G8-02`：四線唯一 run terminal complete；lane ownership正確、無重複領取、無未完成 transaction。
- `SC-G8-03`：release commit、annotated tag、remote main、ledger、sitemap/public artifact一致；第二筆 mutation為零。

## 執行切片與 blocking edges

### `SLICE-G8-PREFLIGHT`

- `traces_to`: `FR-G8-01`, `FR-G8-02`, `SC-G8-01`
- 鎖定本卡 source SHA、origin/main、production actor、manifest、live/staged plists、queue、transaction、tag、sitemap/public artifact基線。
- 跑 source tests、`git diff --check`、current non-production capability receipt與production readiness gate。
- 跑 current storage/capacity兩週期、回收、停損與host baseline。
- 任一非 `READY/PASS`：零 production mutation停止。

### `SLICE-G8-CONVERGE-AND-STAGE`

- `traces_to`: `FR-G8-03`, `SC-G8-01`
- 被 `SLICE-G8-PREFLIGHT` 阻擋。
- origin/main只允許fast-forward至本卡source。
- 用正式 promotion `plan → apply → postcheck → finalize`，保留rollback bundle。
- 用正式 installers產生new staged seven；capacity installer必須先驗 old live seven與new candidate seven，再寫第七張stage plist。
- PID、identity、generation、digest、barrier、Publisher marker或destination drift任一不符，rollback/停止。

### `SLICE-G8-ACTIVATION-ONLY`

- `traces_to`: `FR-G8-04`, `SC-G8-01`
- 被 `SLICE-G8-CONVERGE-AND-STAGE` 阻擋。
- 只用正式 aggregate activation-only 入口切換七服務。
- 驗 live seven等於new target、matching barrier、loaded且zero child I/O；失敗正式rollback並停止。

### `SLICE-G8-ONE-PUBLISH`

- `traces_to`: `FR-G8-05`, `SC-G8-02`
- 被 `SLICE-G8-ACTIVATION-ONLY` 阻擋。
- 從canonical queue選定一筆合法run，保存exact run ID與shared correlation；先dry-run證明selector唯一。
- 只允許正式bounded production入口執行一次；不得直接呼叫Python normal path、不得改selector、不得retry第二筆。
- transaction outcome unknown、第二筆selection或跨lane ownership：立即停止Publisher並保全現場。

### `SLICE-G8-POSTCHECK`

- `traces_to`: `SC-G8-02`, `SC-G8-03`
- 被唯一transaction terminal阻擋。
- 驗transaction closed、queue complete、release commit、annotated tag、remote main、ledger、sitemap/public artifact與public內容。
- 比較前後queue/transactions/tags/other services；第二筆mutation必須為零。
- 保存production mutation receipt與evidence commit；結果只能 `GO` 或帶exact blocker的 `BLOCKED/PARTIAL`。

## 正式入口

- `scripts/pantheon_content_runtime_promotion.py`
- `scripts/pantheon_content_runtime_manifest.py`
- `scripts/pantheon_content_capacity_guard.py`
- `scripts/pantheon_writer_vnext_runtime_activation_capacity.py`
- `scripts/pantheon_writer_vnext_runtime_activation_readiness.py`
- `<ai-core-root>/scripts/production_canary_readiness_gate.py`
- `scripts/install_pantheon_content_capacity_guard_launchd.sh`
- 現有六服務與Publisher正式installer
- `scripts/agy_content_publisher.py`只限dry-run/verification；production publish必須由正式bounded LaunchAgent入口觸發

## 停損

- readiness、capacity、source tests、selector任一非PASS/READY：零production mutation停止。
- promotion/stage/activation identity drift：只用正式rollback bundle回復並停止。
- 第二筆selection/transaction/content/tag/push：立即停止肇因Publisher，保全現場，不重試。
- transaction、push或rollback outcome unknown：`PARTIAL`，不得手改state。
- 同一production blocker先前已達三次；G8出現任何同類 blocker即停止，不做G9或現場補丁。

## 交付格式

- exact source/origin/main/actor/manifest/staged/live identities
- capability/capacity receipts、digests、兩週期與停損證據
- exact selector、correlation與transaction evidence
- release commit、version、annotated tag、remote main、ledger、sitemap/public artifact
- before/after mutation count與第二筆mutation=0
- production mutation receipt、evidence commit SHA、worktree clean
