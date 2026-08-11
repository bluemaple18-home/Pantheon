---
id: CARD-CONTENT-WRITER-VNEXT-RUNTIME-ACTIVATION-PLAN-001
card_id: CARD-CONTENT-WRITER-VNEXT-RUNTIME-ACTIVATION-PLAN-001
status: ready
execution_authorized: true
production_authorized: false
type: planning
chain: PANTHEON-WRITER-VNEXT-RUNTIME-ACTIVATION
chain_id: PANTHEON-WRITER-VNEXT-RUNTIME-ACTIVATION
role: implementation
cycle: 1
strictness: strict
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: Writer vNext 已整合且 recommended fork 已固定；本卡只收斂正式七段入口、非 production E2E、fail-closed 與容量 gate 的 bounded activation 計畫，不含未解架構裁決，因此使用 GPT-5.5 high，不升 Sol。
required_base_ref: main
required_base_sha: c758f34362b1503a41c8ff48885ede896ce26335
ownership: 唯讀核對 Writer vNext 整合狀態，盤點正式 runtime 七段 capability，產出非 production Runtime Activation 的可執行切片計畫與證據；不得啟動 runtime。
allowlist:
  - .ai/handoff_20260811_pantheon_writer_vnext_integrated_runtime_activation.md
  - artifacts/fortune_council/content_writer_vnext_execution/CARD-CONTENT-WRITER-VNEXT-RUNTIME-ACTIVATION-PLAN-001.md
  - artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/writer_vnext_runtime_activation_plan_001/**
  - docs/pantheon_writer_vnext_runtime_activation_plan.md
forbidden_scope:
  - 修改 scripts/**、tests/**、app/**、prototypes/**、production 設定、registry、metadata、文章、sitemap、feed 或 redirects
  - push、deploy、publication、canary、tag、network write、launchctl、排程、服務啟停或正式產文
  - 建立真正 canary、正式 transaction 或 Git remote mutation來證明 readiness
  - 用 mock、臨時 shell 片段、單篇手動成功、HTTP 200、tag 存在或 push exit 0 冒充 capability receipt
  - 重用舊 four-lane Repair-3，或另開 Review／Repair／replacement task
  - 修改、stash、reset、清理或帶入使用者目前 dirty checkout 的變更
verification:
  - first-beat read-only state receipt
  - main and integration lineage verification
  - task-semantic CodeGraph query with bounded source confirmation
  - official-entry capability matrix for create-run-select-publish-transaction-tag-push
  - positive and fail-closed evidence gap matrix
  - storage capacity plan and stop-loss matrix
  - vertical slice plan with blocking edges and checkpoints
  - allowlist audit
  - git diff --check
evidence_path: artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/writer_vnext_runtime_activation_plan_001/
tdd: not-applicable
tdd_reason: 本卡只交付規劃與既有 capability 的唯讀證據，不修改 executable behavior；後續 implementation slice 必須各自定義 public-behavior RED/GREEN。
---

# Writer vNext Runtime Activation：非 production 能力盤點與切片計畫

## 五行派工卡

任務 ID｜`CARD-CONTENT-WRITER-VNEXT-RUNTIME-ACTIVATION-PLAN-001`

卡片類型｜規劃卡；派工對象：`GPT-5.5 high`

請讀｜本卡、`.ai/handoff_20260811_pantheon_writer_vnext_integrated_runtime_activation.md`、`AGENTS.md`、`~/ai-core/compiled_lite.md`、`rules/24-storage-capacity-safety.md`、`rules/25-production-canary-readiness.md`

任務目的｜唯讀核對後，收斂可驗證且 fail-closed 的非 production Runtime Activation 垂直切片；不啟動任何正式 runtime。

證據路徑｜`artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/writer_vnext_runtime_activation_plan_001/`

## 工作名稱 → 正在做什麼 → 現在狀態

- 工作名稱：規劃 Writer vNext Runtime Activation
- 正在做什麼：核對整合主線與七段正式入口，規劃非 production E2E、容量與 readiness 證據鏈。
- 現在狀態：`ready`；正式服務 `0/4`，production `NO-GO`，未授權 push／deploy／publication／canary／tag／服務啟停／正式產文。

## Root Question

`main` 上的 Writer vNext 是否已具備從正式入口完成 `create → run → select → publish → transaction → tag → push` 的可追溯、同 correlation、fail-closed 全鏈路；若尚未具備，應如何以最少垂直切片先完成非 production E2E 與容量安全證明？

## 固定事實與來源

1. 本機 `main` 固定為 `c758f34362b1503a41c8ff48885ede896ce26335`，Writer vNext 已整合；不得重開舊 contract／integration Repair。
2. integration reviewer evidence commit 為 `1e52a551958931d34fc1faf74fc4e2b29dc7187f`，既有 verdict 為 `REVIEW_GO`。
3. 使用者目前 checkout 原本即 dirty，且不屬本卡；不得序列化、修改、stash、reset 或清理。
4. 正式服務仍 `0/4`，production authorization 為 `NO-GO`；單篇手動救援不得與正式 lane activation 混稱。
5. recommended fork 已選定為「非 production Runtime Activation／E2E evidence」；臨時限量產文保留為 `pending` fork，不在本卡執行。

## 第一拍：只做唯讀核對

在任何寫入本卡 allowlist 前，先回報並存證：

1. 目前 branch、HEAD、`main` SHA、worktree cwd/path、clean state與 index lock。
2. 本卡與 handoff 在目前 HEAD 的 Git blob 均可讀。
3. integration receipt、lineage receipt 與 reviewer report／findings Git object 可讀。
4. 正式服務數量仍為 `0/4`，未新增 server；production authorization 仍為 `NO-GO`。
5. CodeGraph readiness 只算 provisioning；須另做本任務語意 query，再限域讀原始碼確認正式入口。

完成第一拍前，禁止修改任何檔案、跑測試、啟動服務、產文或另開 task。第一拍後只可寫 allowlist 的計畫與證據檔。

## 必須盤點的 capability

逐一建立 `create`、`run`、`select`、`publish`、`transaction`、`tag`、`push` 矩陣。每段都必須列出：

- production 會使用的正式 command／script／API／tool identifier；不存在即標記 `MISSING_ENTRY`。
- 具體 input／output artifact 與上一步 output 到下一步 input 的機器可驗證關係。
- actor／resource identity、execution line ID 與全鏈共用 correlation ID。
- 可由相同正式邊界執行的非 production 正向 probe 設計。
- 缺輸入、錯 identity、錯 correlation、無 selector 與 mutation refusal 的 fail-closed 負向 probe 設計。
- 現有證據、缺口、最小修補 slice、blocking edge 與停止條件。

`transaction`、`tag`、`push` 必須分開；不得把 publication 或 Git 成功訊號合併推定。

## 必交付

### Plan document

`docs/pantheon_writer_vnext_runtime_activation_plan.md` 至少包含：

1. 正式入口與 authority owner matrix。
2. 七段 capability I/O／identity／correlation matrix。
3. positive／fail-closed evidence gap matrix。
4. 非 production E2E flow 與 synthetic／sandbox 邊界。
5. storage write-path inventory、容量預算欄位、兩週期代表性試跑、回收與 stop-loss 設計。
6. 垂直 implementation slices；每張一個核心變更，標示 blocking edges、frontier 與每 2–3 slices checkpoint。
7. 後續 strict independent Review 的固定 base／candidate／evidence 契約。
8. production canary 的另行 authorization gate；在 capability `READY`、容量 `PASS` 與獨立 Review 前維持 `NO-GO`。
9. rejected alternatives：手動單篇成功、臨時 shell、先建 canary 再補 receipt、並行拆 selector／canary／入口修補。

### Evidence

唯一 evidence 目錄至少產出：

- `first-beat-state.json`
- `source-inventory.md`
- `capability-matrix.json`
- `evidence-gap-matrix.json`
- `storage-capacity-plan.json`
- `slice-plan.json`
- `verification-receipt.md`

## Acceptance

1. 第一拍只讀證據完整，main／dirty checkout／0/4／production `NO-GO` 的邊界分開記錄。
2. 七段 capability 各有正式入口結論；缺入口或證據時明確 `BLOCKED`，不得用推論補齊。
3. I/O、identity 與 correlation 能沿同一 execution line 串接；正向與負向 evidence 不共用 artifact。
4. 非 production E2E 不建立真正 canary、不碰 production、remote Git 或外部 write。
5. 容量計畫涵蓋全部寫入路徑、上限、兩週期實測、峰值、回收與停損；缺任何欄位維持 `NO-GO`。
6. 切片垂直、dependency-aware、每張一個可驗證責任；不建立第二套 queue／Publisher／deployment control plane。
7. changed files 完全落在 allowlist，`git diff --check` 通過，worktree clean。
8. 唯一 verdict 為 `RUNTIME_ACTIVATION_PLAN_READY_FOR_REVIEW` 或 `BLOCKED`；不得宣稱 runtime 已啟用、production ready 或 Writer vNext 正式服務完成。

## Stop Conditions

- `main`、integration lineage、本卡 blob、handoff blob 或 clean worktree 與固定事實不符。
- 任何必要 capability 只能靠臨時 shell、mock 或真正 production mutation 才能證明。
- 需要修改 executable source、push、deploy、publication、tag、canary、network write、launchctl、服務啟停或正式產文。
- 發現未解 architecture／authority fork；回主線決定是否以 Sol 另開 critical 卡，不得自行升級。
- 同一 blocker 第 3 次失敗即 `BLOCKED`，不做第 4 次。
