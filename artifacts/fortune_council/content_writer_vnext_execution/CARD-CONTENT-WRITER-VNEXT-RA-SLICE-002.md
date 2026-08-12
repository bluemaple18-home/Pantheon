---
id: CARD-CONTENT-WRITER-VNEXT-RA-SLICE-002
card_id: CARD-CONTENT-WRITER-VNEXT-RA-SLICE-002
status: ready
execution_authorized: true
production_authorized: false
type: implementation
chain: PANTHEON-WRITER-VNEXT-RUNTIME-ACTIVATION
chain_id: PANTHEON-WRITER-VNEXT-RUNTIME-ACTIVATION
role: implementation
cycle: 3
strictness: strict
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: create/run receipt 會成為 production-readiness 核心 entry parity，但 plan、schema 與官方入口已固定，屬 strict/core-bounded，使用 GPT-5.5 high，不升 Sol。
required_base_ref: main
required_base_sha: b9719ad5d6b409d91b8f188d8bdfab28f8d9e08a
required_slice_001_review_commit: ec772e7e523a3736cd5fb8175c97258867c15bf7
required_slice_001_review_verdict: REVIEW_GO
slice_id: RA-SLICE-002
traces_to:
  - RA-GAP-002
  - SC-create
  - SC-run
  - SC-correlation
dependencies:
  - RA-SLICE-001
blocking_edges:
  - shared receipt schema
ownership: 為 coordinator create/run 官方入口新增純本機、trusted-sandbox 的 normalized receipt preflight；不處理 Publisher 或七段 E2E。
allowlist:
  - artifacts/fortune_council/content_writer_vnext_execution/CARD-CONTENT-WRITER-VNEXT-RA-SLICE-002.md
  - scripts/agy_gemini_coordinator.py
  - tests/test_agy_gemini_coordinator_capability_receipt.py
  - artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_002/**
forbidden_scope:
  - 修改 scripts/pantheon_content_capability_receipt.py、Publisher、runner、現有 probe/adapter、runtime manifest、capacity guard、deployment scripts 或其他 tests
  - 實作 RA-SLICE-003、Checkpoint A、RA-SLICE-004 E2E、capacity、readiness gate 或 production canary
  - 建立第二套 coordinator、queue、runtime、schema validator、Publisher 或 readiness engine
  - 修改 plan、RA-SLICE-001 implementation/repair/review evidence、registry、metadata、文章、sitemap、feed 或 redirects
  - 自行 Review、Repair、另開 task、merge、push、deploy、publication、canary、tag、network write、launchctl、服務啟停或正式產文
verification:
  - fixed plan and RA-SLICE-001 REVIEW_GO lineage
  - task-semantic CodeGraph query and bounded source confirmation
  - public-behavior RED before implementation
  - create/run positive and fail-closed probes
  - shared full receipt validator compatibility fixture
  - coordinator regression tests
  - existing receipt and capability probe regressions
  - artifact JSON parse and path audit
  - allowlist audit
  - git diff --check
evidence_path: artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_002/
tdd: required
---

# RA-SLICE-002：Coordinator Create/Run Non-production Receipt

## 工作名稱 → 正在做什麼 → 現在狀態

- 工作名稱：建立 Writer vNext Coordinator Create/Run Receipt
- 正在做什麼：讓 coordinator 官方 create/run 邊界在 trusted sandbox 產生可併入共享七段 schema 的兩段 receipt 與分離 evidence。
- 現在狀態：`ready`；RA-SLICE-001 已 `REVIEW_GO` 並整合，production `NO-GO`、正式服務 `0/4`。

## Root Question

如何在不啟動 production、不呼叫網路模型、不複製 coordinator 邏輯的前提下，讓 `register_run → cycle_once/process_once` 官方邊界對同一 execution line 與 correlation 產生 create/run normalized receipt fragments，且 missing brief、bad correlation 與 wrong lane 都在可信 sandbox 內 fail closed？

## 固定來源事實

1. `scripts/pantheon_content_capability_receipt.py` 是唯一共享 schema authority；固定七段順序 create、run、select、publish、transaction、tag、push。
2. `register_run` 已驗 brief、建立 run state 並保存 `correlation_id`；一般路徑可自動產生 correlation，但本 preflight 必須要求 caller 明示 correlation，不得隨機補值。
3. `cycle_once` 與 `process_once` 是 run 官方邊界，且已有 dependency injection seam；preflight 必須沿用這些入口，不得重寫狀態機。
4. 本 slice 只擁有 ordinal 1/2；ordinal 3–7 由 RA-SLICE-003 負責，完整 E2E 組裝留給 RA-SLICE-004。

## Public Contract

在 `scripts/agy_gemini_coordinator.py` 新增單一公開 bounded preflight 入口，名稱與最小 signature 由 RED tests 固定，但必須：

- 只接受 canonical absolute trusted sandbox root；run、queue、evidence roots 必須是其 strict descendants，且互不危險重疊。
- 明示接收或安全推導：`execution_line_id`、`correlation_id`、`actor_identity`、`runtime_identity_digest` 與 create input digest。
- runtime identity 必須來自格式正確、status PASS 的 local receipt；caller 不得用 `valid=true`、`ready=true` 或自填 full receipt verdict 自證。
- 建立恰好一個固定 synthetic brief/run，最多一篇文章；沿用 `register_run`。
- 以現有 injection seam 推進一次 bounded local run；不得使用 credential、network model、production broker、launchd 或正式 queue。
- 回傳 top-level non-production envelope與恰好兩個 `receipt_steps`；不得冒充完整七段 receipt 或直接宣稱 production readiness。
- 每個 step 必須完全符合共享 validator 的 step keys：capability、ordinal、entrypoint、input/output digest、四個 identity 欄位、positive/negative evidence identifiers、PASS/BLOCKED outcomes。
- create output digest 必須由 canonical registered state 推導；run input digest 必須等於 create output digest；run output digest 必須由 bounded cycle result／run evidence推導。
- 正向與 blocked evidence 必須是實際存在、不同、非空、repo/artifact-relative identifiers；artifact 內容保存 step、entrypoint、identity、digest、outcome 與 `production_mutation=false`，不保存本機絕對路徑。
- 全部寫入只落在 caller 授權的 trusted sandbox；回傳 `canary_created=false`、`production_mutation=false`。

不得新增第二份 step validator。測試必須把實際 create/run steps 與 ordinal 3–7 的最小 known-good fixture 組成完整 receipt，再交給 `validate_capability_receipt`；只有共享 authority 回 PASS 才算 schema-compatible。

## 必做 Positive Probe

1. 固定 synthetic brief 在 sandbox 內建立一個 run。
2. `register_run` 的 run ID、run dir、correlation 與 preflight identity 一致。
3. `cycle_once` 透過 local deterministic seam 只推進該 run，不使用網路或 production credential。
4. create/run steps 順序為 1/2，digest continuity 成立，兩個 positive artifact 可解析。

## 必做 Fail-closed Probe

至少保存並驗證：

- missing／invalid brief：在 run state 或 queue I/O 前拒絕。
- blank／drifted correlation：不得自動生成或跨 step 漂移。
- wrong／unknown lane：不得呼叫 injected process 或建立外部 request。
- untrusted root、symlink escape、overlapping roots：在 I/O 前拒絕。
- runtime identity 缺漏／錯 digest：在 I/O 前拒絕。
- caller-supplied verdict／extra receipt keys：拒絕。

Blocked artifacts 必須與 positive artifacts 分離，並記錄 stable reason；不得只用 pytest exception 文案冒充 artifact。

## TDD 與 Evidence

先新增 `tests/test_agy_gemini_coordinator_capability_receipt.py` 並保存真實 RED，再做最小 GREEN。Evidence 至少：

- `red.txt`
- `green.txt`
- `positive-create.json`
- `positive-run.json`
- `blocked-create.json`
- `blocked-run.json`
- `negative-matrix.json`
- `source-inventory.md`
- `verification-receipt.md`

至少跑：

```text
uv run pytest tests/test_agy_gemini_coordinator_capability_receipt.py
uv run pytest tests/test_agy_gemini_coordinator.py
uv run pytest tests/test_pantheon_content_capability_receipt.py tests/test_pantheon_content_capability_probe.py
git diff --check
```

## Acceptance

1. create/run 實際呼叫官方 coordinator 邊界，沒有第二套狀態機。
2. 同一 execution line、correlation、actor、runtime digest 與 digest continuity 由 code 比對／推導。
3. Positive 與 fail-closed artifacts 真實分離且可解析；所有拒絕在 production/network I/O 前。
4. 兩個實際 steps 與 fixture 3–7 組成的完整 receipt 通過唯一共享 validator；任一 identity/digest/evidence 漂移拒絕。
5. 原 coordinator、receipt validator 與 capability probe regression 全綠。
6. changed files 完全落在 allowlist，`git diff --check` 通過，worktree clean，建立單一 candidate commit。
7. 交付只能是 `RA_SLICE_002_READY_FOR_REVIEW` 或 `BLOCKED`；不得宣稱 Checkpoint A、E2E、production readiness 或已整合。

## Stop Conditions

- 必須修改 shared validator、Publisher、runner 或 production runtime 才能成立。
- 無法透過 existing official entry/injection seam 完成 bounded local run。
- 需要 network、credential、push、deploy、publication、tag、canary、launchctl、服務啟停或正式產文。
- 同一 blocker 第三次失敗即停止，不做第四次。
