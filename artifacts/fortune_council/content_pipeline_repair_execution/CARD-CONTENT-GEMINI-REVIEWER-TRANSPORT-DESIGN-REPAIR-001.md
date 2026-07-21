---
card_id: CARD-CONTENT-GEMINI-REVIEWER-TRANSPORT-DESIGN-REPAIR-001
chain_id: CONTENT-GEMINI-REVIEWER-TRANSPORT-DESIGN-001
status: READY_FOR_REVIEW
repair_generation: 1
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 三個 P1 涉及 strict parser、合法 APPROVE interface 與不可觀測 provider call claim；修復後須用 Gemini CLI corpus 重驗並回原 Reviewer
ownership: 只修 Review 001 的四個固定 findings，產出新 candidate
base_candidate_sha: d15df4b1e892f3b9854f42dc067d89af7ee37cd3
review_evidence_sha: c870209
allowlist:
  - scripts/agy_gemini_transport_probe.py
  - tests/test_agy_gemini_transport_probe.py
  - docs/pantheon_gemini_reviewer_transport_strategy.md
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_transport_design_repair_001/**
forbidden_scope:
  - app/**
  - scripts/agy_seo_copy_pipeline.py
  - scripts/agy_gemini_outbox.py
  - scripts/agy_gemini_runner.py
  - 正式文章與發布檔
  - Gemini CLI 安裝、登入、設定修改
  - merge、push、deploy、publish、production
verification:
  - duplicate-key, APPROVE, blank-message and invocation-accounting red-green tests
  - exact 6 fresh Gemini CLI external-process corpus
  - strict parser/schema/rubric recomputation
  - full affected tests, py_compile, allowlist and privacy scans
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_transport_design_repair_001/
reviewer_thread_id: 019f825a-306e-7e52-956c-52f294e99c26
reviewed_candidate_sha: d15df4b1e892f3b9854f42dc067d89af7ee37cd3
provisioning_source_sha: 05adf93b4843d3b4c0149e1c24e0e59d335a7bae
provisioning_parent_sha: c870209198c5f538b23ce82714dc560193e553a2
worktree_path: <codex-worktree>/691a/Pantheon
cwd: <codex-worktree>/691a/Pantheon
worktree_exists: true
thread_id: 019f8262-09d5-7ec3-9438-b1841777990a
thread_status: RUNNING
thread_host_id: local
rollout_path: <codex-sessions>/2026/07/21/rollout-2026-07-21T09-54-50-019f8262-09d5-7ec3-9438-b1841777990a.jsonl
candidate_sha: 5018589dd014e4c3edf5c6a3d736d912957ec400
candidate_parent_sha: 05adf93b4843d3b4c0149e1c24e0e59d335a7bae
re_review_status: RUNNING
---

# CARD-CONTENT-GEMINI-REVIEWER-TRANSPORT-DESIGN-REPAIR-001｜修復 strict mapper 契約

## 固定 findings

1. P1：`json.loads` 靜默接受 duplicate keys，矛盾 verdict 可穿透。
2. P1：schema 的 `findings.minItems=1` 使合法 `APPROVE + hard_failure=false + findings=[]` 不可能通過。
3. P1：只能證明外部 CLI process 次數，無法證明 vendor 內部 provider model calls；原 claim 不可保留。
4. P2：空白或純空格 finding message 仍通過。

## 修復契約

- strict JSON parser 必須以 pairs-level 檢查拒絕任一層 duplicate key；不得採後值、不得修補 JSON。
- structural schema 允許 `findings=[]`；deterministic rubric 強制：
  - `APPROVE` ↔ `hard_failure=false` 且 `findings=[]`。
  - `REJECT` ↔ `hard_failure=true` 且至少一筆 finding。
  - finding code/message trim 後必須非空。
- 計數欄位與文件改為 `external_cli_process_invocations`；`provider_model_calls` 必須明確標記 `unobservable/unknown`，不得宣稱上限或精確值。
- process budget 精確 6：推薦 Pro Low minimal judgment＋mapper，sanitized REJECT corpus 3 fresh processes、sanitized APPROVE corpus 3 fresh processes；無 retry、無第 7 次。
- 每個 corpus 需 3/3 exit、strict parse、schema、rubric，且 verdict/hard_failure 內部一致；任一未達立即 `BLOCKED`。
- 仍不得保存 prompt、raw response、stderr、秘密或本機絕對路徑，只存 sanitized receipts。

## 驗收與交付

- 先讓四個 finding 各有失敗測試，再最小修復。
- 交付 red-green、6-run corpus、verification、root-cause／finding closure mapping。
- 建立新 candidate commit，只能 `DELIVERED_CANDIDATE` 或 `BLOCKED`。
- 新 candidate 必須送回原 Reviewer thread `019f825a-306e-7e52-956c-52f294e99c26` re-review；不得換 Reviewer 或自行宣稱 GO。
- 不修改 production pipeline，不恢復三條內容線。
