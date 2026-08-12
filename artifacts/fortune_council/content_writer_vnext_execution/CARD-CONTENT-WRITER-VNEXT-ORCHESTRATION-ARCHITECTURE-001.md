---
id: CARD-CONTENT-WRITER-VNEXT-ORCHESTRATION-ARCHITECTURE-001
card_id: CARD-CONTENT-WRITER-VNEXT-ORCHESTRATION-ARCHITECTURE-001
status: ready
type: architecture
execution_authorized: true
production_authorized: false
chain_id: PANTHEON-WRITER-VNEXT-ORCHESTRATION
role: implementation
cycle: 1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: Writer vNext contract 與 runtime authority 已固定驗收，但 orchestration ownership、跨 tick 恢復與 Publisher handoff 屬核心跨模組契約；問題已收斂為四個 bounded 決策，使用 GPT-5.5 high，不升級為未解 fork 的 Sol。
ownership: Writer vNext orchestration architecture、artifact/state ownership 與既有 Publisher handoff 契約
traces_to:
  - US-002
  - US-003
  - US-004
  - FR-001
  - FR-002
  - FR-005
  - FR-006
  - FR-008
  - FR-009
  - FR-010
  - FR-011
  - FR-012
  - FR-013
  - FR-014
  - FR-017
source_inputs:
  writer_contract_review_commit: 038cf4d2979bf2a1a8ceaf4d44964c3fde5816c6
  writer_contract_candidate_commit: 671fdba9bf1b5655cc9182bbf375cadae3efb0b5
  runtime_authority_review_commit: 38774ddf1bccc77a0b40917322bb100d238469d7
  runtime_authority_candidate_commit: e6d93fba050eac7c22e1a34bf52d8ac4c707a1b3
allowlist:
  - docs/pantheon_writer_vnext_orchestration_architecture.md
  - artifacts/fortune_council/content_writer_vnext_execution/evidence/writer_vnext_orchestration_architecture_001/**
forbidden_scope:
  - 修改 scripts/**、tests/**、app/**、package／lockfile 或既有 card/evidence
  - 實作 Agent、prompt、Gemini role、queue、retry loop、Publisher 或 runtime mutation
  - 固定 Research→Outline→Blind Reader→Fact Checker 順序
  - 文章、metadata、registry、FAQ、Schema、sitemap、feed、redirects
  - merge、push、deploy、publication、canary、network、launchctl 或服務啟動
verification:
  - 固定 source commits 與 changed-file inventory
  - CodeGraph semantic query 加原始碼確認
  - architecture invariant matrix
  - traceability preflight
  - git diff --check
evidence_path: artifacts/fortune_council/content_writer_vnext_execution/evidence/writer_vnext_orchestration_architecture_001/
tdd: not-applicable
tdd_reason: 本卡只交付架構契約與可驗證決策，不修改 executable behavior；後續 implementation 卡必須使用 public-behavior RED/GREEN。
---

# Writer vNext Orchestration Architecture

## 五行派工卡

任務 ID｜`CARD-CONTENT-WRITER-VNEXT-ORCHESTRATION-ARCHITECTURE-001`

卡片類型｜架構卡；派工對象：`gpt-5.5 high`

請讀｜本卡、固定 Writer contract commits、固定 Runtime Authority commits，以及下列現行 transport／coordinator／Publisher 原始碼。

任務目的｜把 Writer vNext contract 安全映射到既有 Writer／Reviewer transport 與 Publisher handoff，定義跨 tick 可恢復、不可重送的 forward-only orchestration 契約。

證據路徑｜`artifacts/fortune_council/content_writer_vnext_execution/evidence/writer_vnext_orchestration_architecture_001/`

## Root Question

如何在不建立第二套 queue、approval、publication 或 deployment control plane 的前提下，把 `ArticleBriefV2`、每次 run 明示的可選 editorial stages、候選稿與 review 串入既有 Gemini transport／coordinator／Publisher，且能跨 tick 恢復、不重送已完成 artifact、保留舊 run 相容與 fail-closed rollback identity？

## 固定事實

1. Writer contract 已在 `671fdba9bf1b5655cc9182bbf375cadae3efb0b5` 修復並由 `038cf4d2979bf2a1a8ceaf4d44964c3fde5816c6` 獨立 `REVIEW_GO`。
2. Runtime Authority candidate `e6d93fba050eac7c22e1a34bf52d8ac4c707a1b3` 已由 `38774ddf1bccc77a0b40917322bb100d238469d7` 獨立 `REVIEW_GO`。
3. 兩條候選尚未整合；本卡只讀 Git objects 並設計 composition seam，不得 cherry-pick、merge 或修改 executable source。
4. Publisher 是唯一 publication owner；lifecycle controller 是 lane／lock owner；Gemini outbox／runner 是唯一外部模型 transport。
5. editorial stages 可選且順序由 manifest 宣告；不得形成新的固定多 Agent 模板。
6. production 仍 `NO-GO`；正式服務 `0/4`、Publisher stopped。

## 必讀原始碼與固定 Git objects

先用 CodeGraph 做 task-semantic query，再由原始碼確認：

- `scripts/agy_editorial_contracts.py`
- `scripts/agy_seo_copy_pipeline.py`
- `scripts/agy_gemini_outbox.py`
- `scripts/agy_gemini_runner.py`
- `scripts/agy_gemini_coordinator.py`
- `scripts/agy_content_publisher.py`
- 對應 public tests

Runtime Authority 不在本 source tree 的部分，用 `git show e6d93fba050eac7c22e1a34bf52d8ac4c707a1b3:<path>` 唯讀確認；不得把 machine-specific worktree path 寫入共享文件。

## 必須回答的四個架構問題

### A. Transport mapping

- `ArticleBriefV2`、`EditorialManifestV1` 與 selected stages 如何映射到既有 request envelope。
- 是否能只使用現有 `writer`／`reviewer` role；若必須擴充 role，列出必要性、版本遷移與舊 runner 相容，不得直接實作。
- 每一步的 input artifact、output artifact、schema version、identity、request/response SHA 與 deterministic gate。

### B. Forward-only recovery

- 定義 run-level state projection 與 immutable artifact ledger；source of truth 必須是可重建 artifacts，不是自由狀態文案。
- coordinator 每個 tick 如何從 ledger 推導唯一 next action。
- 已存在且 SHA／schema／identity 全部相符的 stage 不得重送；collision、tamper、missing dependency、未知 stage 或 ambiguous next action 必須 fail loud。
- retry 必須有上限並沿用既有 transport authority；本卡不得新增 loop、daemon 或第二套 queue。

### C. Publisher handoff

- vNext manifest 與 stage artifacts 必須旁掛，不能改寫 legacy candidate identity。
- 定義最小 compatibility adapter：何時產生既有 candidate／review、哪些 blocking findings 會禁止 handoff、Publisher 如何重新驗證 identity。
- manifest 不得取得 approval、apply、Git mutation、push 或 publication authority。
- FAQ、文章形狀、metadata 與 Schema policy 留給後續卡，不在本卡解決。

### D. Compatibility and rollback

- 舊 run 沒有 vNext artifacts 時如何繼續由舊流程完成。
- 新 run 啟用 vNext 的 versioned opt-in boundary；不得用 shadow A/B。
- candidate、review、manifest、runtime activation receipt 的 rollback identity 與 fail-closed 條件。
- composition 前置：Writer contract 與 Runtime Authority 兩條 reviewed commits 如何由後續 integration 卡形成單一可驗證 lineage；本卡只定義 gate，不執行整合。

## 必交付

### Architecture document

`docs/pantheon_writer_vnext_orchestration_architecture.md` 至少包含：

1. owner／authority matrix。
2. artifact I/O 與 schema/version matrix。
3. forward-only state transition table。
4. tick reconstruction 與 dedupe pseudocode。
5. failure taxonomy、stable finding codes 與 fail-closed behavior。
6. legacy/vNext compatibility matrix。
7. Publisher handoff boundary。
8. reviewed-commit composition gate。
9. implementation slices、blocking edges、frontier 與每 2–3 slices checkpoint。
10. 明確的 rejected alternatives，包含第二套 queue、mega-agent、固定 stages 與 manifest publication authority。

### Evidence

在 evidence path 產出：

- `source-inventory.md`：固定 commits、CodeGraph query、實際 source seams。
- `traceability-matrix.json`：本卡 decisions 對 US／FR 與後續 slice IDs。
- `architecture-invariants.json`：可由後續測試直接實作的 invariants。
- `verification-receipt.md`：allowlist、禁區、trace preflight、diff-check 與唯一 verdict。

## Stable decision IDs

- `WVO-ARCH-001`：transport mapping。
- `WVO-ARCH-002`：artifact ledger 與 next-action reconstruction。
- `WVO-ARCH-003`：dedupe／collision／tamper fail-closed。
- `WVO-ARCH-004`：Publisher compatibility adapter。
- `WVO-ARCH-005`：legacy opt-in 與 rollback identity。
- `WVO-ARCH-006`：reviewed-commit composition gate。

後續 implementation slices 使用 `WVO-SLICE-*`，每個 slice 必須有 `traces_to`、blocking edges、public verification 與 evidence path；不得用排序變動回收 ID。

## Acceptance

1. 四個架構問題都有單一、可實作且可測試的答案；沒有把決策推回模糊 TODO。
2. owner matrix 只有既有 lifecycle、transport、orchestration、validator、Publisher 與 deployment owner，不新增重複 authority。
3. next action 可只由 versioned artifacts／SHA／manifest 重建；不依賴記憶體或自由文案。
4. completed stage 不重送；任何 identity/schema/SHA ambiguity fail closed。
5. Publisher handoff 保持 legacy candidate/review identity，manifest 只旁掛。
6. legacy run 與 vNext opt-in run 的相容、停止與 rollback identity 明確。
7. implementation slices 為垂直、dependency-aware、每張一個核心變更，並標示唯一 frontier。
8. traceability 無 dangling／duplicate／未解 blocking decision；N/A 有理由。
9. changed files 完全落在 allowlist，`git diff --check` 通過。
10. verdict 只能是 `ARCHITECTURE_READY_FOR_REVIEW` 或 `BLOCKED`；不得宣稱已實作、已整合、已部署或 production ready。

## Verification

```bash
git rev-parse HEAD
git status --short
git diff --check
python3 <repo-root>/../ai-core/skills/task-slice-planning/scripts/validate_traceability.py --help
```

若 traceability script 的實際位置或介面不同，先限域定位並在 receipt 記錄替代命令；不得跳過 dangling／duplicate／verification 檢查。

## Stop Conditions

- 固定 Git object 不可讀或 lineage 不符。
- 無法在既有 transport／Publisher authority 內完成，必須建立第二套控制面。
- 需要 merge、push、deploy、production、外部 write 或使用者未授權的高成本變更。
- 同一 blocker 第 3 次失敗即 `BLOCKED`，不做第 4 次。
