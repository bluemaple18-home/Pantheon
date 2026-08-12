---
id: CARD-CONTENT-WRITER-VNEXT-RA-SLICE-004
card_id: CARD-CONTENT-WRITER-VNEXT-RA-SLICE-004
status: ready
execution_authorized: true
production_authorized: false
type: implementation
chain: PANTHEON-WRITER-VNEXT-RUNTIME-ACTIVATION
chain_id: PANTHEON-WRITER-VNEXT-RUNTIME-ACTIVATION
role: implementation
cycle: 5
strictness: strict
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 七段 E2E 會成為 production-readiness 核心 capability proof；入口、schema 與範圍已固定，屬 strict/core-bounded，使用 GPT-5.5 high，不升 Sol。
required_base_ref: main
required_base_sha: a2faaa1c0bf759273e2b8021c4db7353ef2bff92
required_checkpoint_a_review_commit: 5948220827baf422c44cb65566d9ddcdf4ce32f7
required_checkpoint_a_review_verdict: REVIEW_GO
slice_id: RA-SLICE-004
traces_to:
  - SC-e2e
  - SC-correlation
dependencies:
  - RA-CHECKPOINT-A
blocking_edges:
  - entry parity review
ownership: 新增單一純本機 synthetic non-production E2E harness，組合既有 coordinator create/run 與 publisher select/publish/transaction/tag/push 官方 preflight，產生同一 execution line 的七段完整 receipt。
allowlist:
  - artifacts/fortune_council/content_writer_vnext_execution/CARD-CONTENT-WRITER-VNEXT-RA-SLICE-004.md
  - scripts/pantheon_writer_vnext_runtime_activation_e2e.py
  - tests/test_pantheon_writer_vnext_runtime_activation_e2e.py
  - artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_004/**
forbidden_scope:
  - 修改 coordinator、Publisher、shared receipt validator、runner、probe/adapter、runtime manifest、capacity guard、deployment scripts 或其他 tests
  - 實作 RA-SLICE-005 capacity、RA-SLICE-006 readiness packaging、Checkpoint B 或 production canary
  - 建立第二套 coordinator、Publisher、schema validator、runtime、queue、transaction、git 或 readiness engine
  - 修改 plan、先前 implementation/repair/review evidence、registry、metadata、文章、sitemap、feed 或 redirects
  - 自行 Review、Repair、另開 task、merge、push、deploy、publication、canary、tag、network write、launchctl、服務啟停或正式產文
verification:
  - fixed Checkpoint A REVIEW_GO lineage
  - task-semantic CodeGraph query and bounded source confirmation
  - public-behavior RED before implementation
  - positive seven-step E2E probe in canonical trusted sandbox
  - identity and digest continuity fail-closed probes
  - positive and negative artifact separation
  - shared full receipt validator PASS/BLOCKED fixtures
  - coordinator and publisher capability receipt regressions
  - artifact JSON parse and path audit
  - allowlist audit
  - git diff --check
evidence_path: artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_004/
tdd: required
---

# RA-SLICE-004：Synthetic Non-production E2E Harness

## 工作名稱 → 正在做什麼 → 現在狀態

- 工作名稱：串接 Writer vNext 七段 Synthetic E2E
- 正在做什麼：用既有官方 preflight 在單一 trusted sandbox 產生 create→run→select→publish→transaction→tag→push 的完整 receipt 與分離證據。
- 現在狀態：`ready`；Checkpoint A 已 `REVIEW_GO` 並整合，production `NO-GO`、正式服務 `0/4`。

## Root Question

如何在不啟動 production、不使用網路或 credential、不重寫任何既有入口的前提下，讓 coordinator 與 Publisher preflight 對同一 execution line、correlation、actor 與 runtime identity 串成七段 digest-continuous receipt，並由唯一共享 validator 驗證？

## 固定來源事實

1. `scripts.pantheon_content_capability_receipt:validate_capability_receipt` 是唯一完整七段 schema authority。
2. ordinal 1/2 必須呼叫 `scripts.agy_gemini_coordinator:coordinator_create_run_receipt_preflight`。
3. ordinal 3–7 必須依固定順序逐一呼叫 `scripts.agy_content_publisher:formal_capability_preflight`；不得偽造 step。
4. Checkpoint A 已固定兩側入口 parity；本 slice 只擁有組合 harness，不得修改入口。
5. production 維持 `NO-GO`；所有輸出必須 `canary_created=false`、`production_mutation=false`。

## Public Contract

新增單一公開、可測試的 bounded harness。最小 signature 由 RED tests 固定，但必須：

- caller 明示 canonical absolute trusted sandbox root、runtime receipt、`execution_line_id`、`correlation_id`、`actor_identity` 與固定 synthetic brief。
- 所有 run、queue、publisher state、evidence roots 都是 sandbox strict descendants，且無危險重疊或 symlink escape。
- 先呼叫 coordinator preflight，取得恰好 create/run 兩段與唯一 run ID。
- 以 create/run 的相同四個 identity 呼叫 Publisher 五個 capability；每一步的 input digest 必須接續上一段 output digest。
- Publisher `receipt_context` 只由前一步 canonical output 與固定 identity 推導，不接受 caller-supplied verdict、step、digest 或 readiness。
- 組裝恰好七段後只呼叫共享 validator；validator PASS 才回傳 canonical receipt。
- 保存一份完整 positive receipt，以及每個 capability 的既有 positive/blocked artifact identifier inventory；positive 與 negative 不得混檔。
- 回傳與 artifact 明示 `mode=synthetic-non-production`、`canary_created=false`、`production_mutation=false`；不得宣稱 READY 或 production authorization。

## 必做 Positive Probe

1. 單一 canonical sandbox 內完成七段官方 preflight。
2. 七段共享同一 `execution_line_id`、correlation、actor、runtime digest。
3. ordinal 固定 1–7；每段 input digest 等於上一段 output digest。
4. 完整 receipt 通過唯一共享 validator。
5. 所有 evidence identifier 可解析到 sandbox 內實際不同檔案，且沒有本機絕對路徑。

## 必做 Fail-closed Probe

至少保存並驗證：

- 任一 identity 在 coordinator→Publisher 或 Publisher step 間 drift。
- 任一 digest continuity 斷裂、缺 step、重複 step、順序錯誤。
- caller-supplied verdict／receipt step／readiness authority。
- untrusted root、symlink escape、overlapping roots。
- Publisher 任一 capability BLOCKED 時不得產生後續 positive step或完整 PASS receipt。
- 任一 production mutation、`canary_created=true`、network／credential 路徑。

Blocked artifacts 必須與 positive artifacts 分離，記錄 stable case/reason/blocked capability；不得只用 pytest exception 文案充當證據。

## TDD 與 Evidence

先新增 `tests/test_pantheon_writer_vnext_runtime_activation_e2e.py` 並保存真實 RED，再做最小 GREEN。Evidence 至少：

- `red.txt`
- `green.txt`
- `positive-receipt.json`
- `blocked-receipt.json`
- `negative-matrix.json`
- `source-inventory.md`
- `verification-receipt.md`

至少跑：

```text
uv run pytest tests/test_pantheon_writer_vnext_runtime_activation_e2e.py
uv run pytest tests/test_agy_gemini_coordinator_capability_receipt.py tests/test_agy_content_publisher_capability_receipt.py tests/test_pantheon_content_capability_receipt.py
git diff --check
```

## Acceptance

1. 七段皆來自既有官方 preflight，沒有第二套狀態機、Publisher、schema 或 git engine。
2. 單一 execution line 與四項 identity 在 code 中逐段比對；digest continuity 由實際輸出推導。
3. Positive 與 fail-closed artifacts 真實分離、可解析且受 sandbox authority 限制。
4. 完整 receipt 通過唯一 validator；identity、digest、step 或 evidence 漂移 deterministic BLOCKED。
5. `canary_created=false`、`production_mutation=false`，無 network、credential、push、deploy、tag 或 production write。
6. 受影響 regression 全綠；changed files 完全落在 allowlist；`git diff --check` 通過；worktree clean；單一 candidate commit。
7. 交付只能是 `RA_SLICE_004_READY_FOR_REVIEW` 或 `BLOCKED`；不得宣稱 capacity、readiness、canary 或已整合。

## Stop Conditions

- 必須修改既有 coordinator、Publisher、shared validator、runtime 或 production 設定才可成立。
- 既有官方 preflight 無法以 trusted sandbox 組成完整七段。
- 需要 network、credential、push、deploy、publication、tag、canary、launchctl、服務啟停或正式產文。
- 同一 blocker 第三次失敗即停止，不做第四次。
