---
id: CARD-CONTENT-WRITER-VNEXT-RA-SLICE-001
card_id: CARD-CONTENT-WRITER-VNEXT-RA-SLICE-001
status: ready
execution_authorized: true
production_authorized: false
type: implementation
chain: PANTHEON-WRITER-VNEXT-RUNTIME-ACTIVATION
chain_id: PANTHEON-WRITER-VNEXT-RUNTIME-ACTIVATION
role: implementation
cycle: 2
strictness: strict
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: RA-SLICE-001 是固定規格的 production-readiness 核心 receipt schema 與 fail-closed validator；影響後續七段 capability 證據，但沒有未解架構 fork，因此使用 GPT-5.5 high，不升 Sol。
required_base_ref: main
required_base_sha: bb96dd0f703b083d0acf3570e6da3d7101192b55
required_plan_review_commit: ab682a298342aa2763d45d10d680923d39c1aeb6
required_plan_review_verdict: REVIEW_GO
slice_id: RA-SLICE-001
traces_to:
  - RA-GAP-001
  - RA-SLICE-001
dependencies: []
blocking_edges: []
ownership: 建立唯一共享的七段 capability receipt schema 與純本機 fail-closed validator，供後續 coordinator 與 Publisher slices 共用；不啟動 runtime。
allowlist:
  - artifacts/fortune_council/content_writer_vnext_execution/CARD-CONTENT-WRITER-VNEXT-RA-SLICE-001.md
  - scripts/pantheon_content_capability_receipt.py
  - tests/test_pantheon_content_capability_receipt.py
  - artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_001/**
forbidden_scope:
  - 修改 scripts/pantheon_content_capability_probe.py、scripts/pantheon_content_capability_adapter.py、coordinator、runner、Publisher、runtime manifest、capacity guard 或 deployment scripts
  - 實作 RA-SLICE-002 之 create/run receipt、RA-SLICE-003 之 Publisher normalization 或任何 E2E/canary harness
  - 修改既有 plan、planning evidence、review evidence、registry、metadata、文章、sitemap、feed 或 redirects
  - 自行 Review、Repair、另開 task、merge、push、deploy、publication、canary、tag、network write、launchctl、服務啟停或正式產文
verification:
  - fixed plan and REVIEW_GO lineage
  - task-semantic CodeGraph query and bounded source confirmation
  - public-behavior RED before implementation
  - targeted GREEN tests
  - existing capability probe regression tests
  - full receipt validator negative matrix
  - JSON sample validation
  - allowlist audit
  - git diff --check
evidence_path: artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_001/
tdd: required
---

# RA-SLICE-001：共享七段 Capability Receipt Schema

## 五行派工卡

任務 ID｜`CARD-CONTENT-WRITER-VNEXT-RA-SLICE-001`

卡片類型｜Strict implementation；派工對象：`GPT-5.5 high`

請讀｜本卡、已整合 Runtime Activation plan、固定 `REVIEW_GO` commit、現有 capability probe／adapter 與對應 tests

任務目的｜建立一個可被 coordinator、Publisher 與後續 readiness packaging 共用的七段 receipt schema／validator，任何缺漏或關聯漂移都 fail closed

證據路徑｜`artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_001/`

## 工作名稱 → 正在做什麼 → 現在狀態

- 工作名稱：建立 Writer vNext 七段 Capability Receipt Schema
- 正在做什麼：以 public-behavior TDD 定義共享 receipt contract 與 deterministic validator。
- 現在狀態：`ready`；目前 frontier 只有 `RA-SLICE-001`，production `NO-GO`、正式服務 `0/4`。

## Root Question

如何用單一、可重用、deterministic 的 schema 與 validator，證明 `create → run → select → publish → transaction → tag → push` 七段使用同一 execution line／correlation／actor identity，且每段都具備分離的正向與 fail-closed evidence，而不讓 caller 以狀態文案或自填布林自證 readiness？

## 固定事實

1. 本機 main 已整合 plan candidate `bb96dd0f703b083d0acf3570e6da3d7101192b55`。
2. 獨立 plan review commit `ab682a298342aa2763d45d10d680923d39c1aeb6` verdict 為 `REVIEW_GO`，無 P0/P1。
3. 現有 `pantheon_content_capability_probe.py` 與 adapter 已使用七段名稱並產生 bounded dry-run artifacts，但沒有獨立共享的 strict receipt validator authority。
4. 本 slice 只建立 schema authority 與測試；既有 probe／adapter 接線留給 `RA-SLICE-002`／`RA-SLICE-003`，不得偷跑。
5. Production authorization、容量實測、E2E、canary、tag、push 均不在本卡。

## Public Contract

新增 `scripts/pantheon_content_capability_receipt.py`，至少提供：

- 唯一固定 capability 順序：`create, run, select, publish, transaction, tag, push`。
- 明確的 schema version 與 stable error type。
- 一個 deterministic public validator，輸入一般 Python／JSON mapping，回傳 canonical validated receipt 或拋出 stable fail-closed error。
- 可由後續 coordinator／Publisher slices import 的 step 與 top-level contract；不得依賴外部服務、環境變數、Git remote、檔案是否真的存在或 caller 提供的 `valid=true`。

### Top-level 必填語意

- schema version、execution line ID、correlation ID、actor identity、runtime identity digest。
- mode 必須是明示 non-production／synthetic boundary。
- `canary_created=false`、`production_mutation=false`。
- 七段 steps 完整且順序唯一，不多不少。
- receipt verdict 必須由 step evidence 推導，不接受 caller 自填 readiness。

### 每一步必填語意

- capability、ordinal、正式 entrypoint identifier。
- inputs／outputs 的 deterministic digest；後一步 input 必須等於前一步 output。
- execution line、correlation、actor、runtime identity 必須與 top-level 完全一致。
- 正向 evidence artifact 與 fail-closed evidence artifact 必須是兩個不同、非空、repo-relative／artifact-relative identifiers。
- positive outcome 必須是 `PASS`；negative outcome 必須是 `BLOCKED`。
- 禁止同一 artifact 同時冒充正向與負向證據。

欄位命名由實作者在不違反上述語意的前提下最小化；一旦 RED tests 鎖定即視為本 slice 的 public API，不做不必要抽象。

## TDD 驗證矩陣

先建立 `tests/test_pantheon_content_capability_receipt.py` 並保存 RED，再最小 GREEN。至少覆蓋：

1. 完整七段合法 receipt 通過且回傳 canonical copy；輸入不得被原地修改。
2. 缺 step、多 step、重複、亂序或 ordinal 錯誤全部拒絕。
3. execution line／correlation／actor／runtime identity 任一跨 step 漂移拒絕。
4. 前後 digest 不連續、digest 格式錯誤或 output 缺失拒絕。
5. 正向／負向 artifact 缺漏、相同、絕對路徑、`..\`／`../` traversal 或 outcome 不符拒絕。
6. `canary_created=true`、`production_mutation=true`、未知 mode 或 caller 自證 verdict 拒絕。
7. unknown／extra keys、錯型別、空白 identifier、非有限 JSON value 拒絕。
8. 既有 `tests/test_pantheon_content_capability_probe.py` 受影響 suite 維持通過。

## Evidence

至少產出：

- `red.txt`
- `green.txt`
- `negative-matrix.json`
- `source-inventory.md`
- `verification-receipt.md`

Evidence 只保存命令、結果、固定 SHA 與摘要，不複製大量 runtime artifacts。

## Acceptance

1. Shared validator 是唯一新 schema authority，沒有第二套 queue、runtime、Publisher 或 readiness engine。
2. 七段完整、順序、identity/correlation 與 digest continuity 由 code 重算／比較，不接受 caller 布林自證。
3. 每段正向與 fail-closed evidence 分離且 outcome 正確；任一缺漏 deterministic 拒絕。
4. Validator 純本機、無 side effect、無 production authority，輸入不被修改。
5. RED evidence 證明測試先失敗；GREEN 與既有 capability probe tests 通過。
6. changed files 完全落在 allowlist，`git diff --check` 通過，worktree clean。
7. 建立單一 candidate commit；回報只能是 `RA_SLICE_001_READY_FOR_REVIEW` 或 `BLOCKED`。

## Stop Conditions

- 固定 plan／review lineage 不符，或現有 probe／adapter source claims 無法確認。
- schema 必須修改 coordinator／Publisher／runtime 或建立第二套 control plane 才能成立。
- 必須啟動服務、production、外部 write、push、deploy、publication、tag、canary 或正式產文。
- 同一 blocker 第 3 次失敗即 `BLOCKED`，不做第 4 次。
