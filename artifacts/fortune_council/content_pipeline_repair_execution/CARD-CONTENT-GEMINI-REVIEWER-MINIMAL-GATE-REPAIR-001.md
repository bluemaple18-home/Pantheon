---
card_id: CARD-CONTENT-GEMINI-REVIEWER-MINIMAL-GATE-REPAIR-001
chain_id: CONTENT-GEMINI-REVIEWER-MINIMAL-GATE-IMPLEMENTATION-001
status: RUNNING
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 修正已定位的 corpus fixture 契約衝突，並以固定 production candidate 重新執行一次完整外部 gate
ownership: single-hard-reject fixture 語意隔離、corpus regression、sanitized evidence 與修復 candidate
allowlist:
  - scripts/agy_gemini_reviewer_corpus.py
  - tests/test_agy_gemini_reviewer_corpus.py
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_minimal_gate_repair_001/**
forbidden_scope:
  - scripts/agy_seo_copy_pipeline.py
  - scripts/agy_gemini_outbox.py
  - scripts/agy_gemini_runner.py
  - app/**
  - 正式文章、registry、metadata、prerender、sitemap、feed、redirects
  - Reviewer schema、parser、mapper、prompt、finding allowlist 或 expected-code 比對規則
  - Gemini CLI 安裝、登入、OAuth、token 或全域設定修改
  - merge、push、deploy、publish、production
verification:
  - red-green fixture isolation regression
  - 精確 12-process sanitized production-path corpus
  - focused and full pytest, py_compile, diff/allowlist/privacy scans
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_minimal_gate_repair_001/
blocked_candidate_sha: c5b33832d2c7ccb323e43fed09f502c6a3494a2d
source_kind: commit
source_sha: c5b33832d2c7ccb323e43fed09f502c6a3494a2d
source_clean: true
main_cwd: <repo-root>
source_ref: task/gemini-reviewer-minimal-gate-repair-001
provisioning_attempts: 1
provisioning_note: 新一輪依使用者明確指示，使用含 startingState.type=branch 的已驗證 payload 建立
client_thread_id: client-new-thread:9146e4b3-c606-4b91-8ffa-9237cd69b4de
provisioning_source_sha: c5b33832d2c7ccb323e43fed09f502c6a3494a2d
worktree_path: <codex-worktree>/1264/Pantheon
cwd: <codex-worktree>/1264/Pantheon
worktree_exists: true
thread_id: 019f833f-bbde-7763-92f6-a2610fd28218
thread_title: 修復 Gemini reviewer gate corpus
thread_status: RUNNING
thread_host_id: local
rollout_path: <codex-sessions>/2026/07/21/rollout-2026-07-21T13-57-00-019f833f-bbde-7763-92f6-a2610fd28218.jsonl
---

# CARD-CONTENT-GEMINI-REVIEWER-MINIMAL-GATE-REPAIR-001｜隔離 single-hard-reject 測資語意

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-REVIEWER-MINIMAL-GATE-REPAIR-001`。
派工對象｜strict repair；只修已證實的 corpus fixture 契約，不重寫 production Reviewer。
任務目的｜把 `single-hard-reject` 改成只表達一種明確風險，避免同一句同時合理觸發 `GUARANTEE_CLAIM` 與 `UNSAFE_INSTRUCTION`。
可改範圍｜corpus harness、對應測試與本卡 evidence；production pipeline 與文章全部禁止。
驗收證據｜fixture isolation red-green、4 case×3 fresh Gemini processes、12/12 完整 gate、完整離線驗證與單一 candidate commit。

## 固定修復邊界

- 來源固定為 `c5b33832d2c7ccb323e43fed09f502c6a3494a2d`，不得重建或改寫既有 production implementation。
- `single-hard-reject` 的 candidate 必須只含明確保證性宣稱；移除投資操作步驟、指令或其他可能合理觸發第二個 finding code 的語句。
- 固定 expected verdict 仍為 `REJECT`，固定 expected codes 仍只允許 `GUARANTEE_CLAIM`；不得改成 superset、subset 或模糊包含判斷。
- 新增 regression test，明確證明 fixture 不含投資指令語意，且 expected-code gate 仍採 exact set。
- 不得放寬 strict JSON、schema、rubric、mapper、finding allowlist、candidate SHA invariant 或 failure isolation。

## 外部執行與停損

- 先完成所有離線修改與測試，再且僅再執行一次正式 corpus。
- 正式 corpus 為四個 sanitized cases、每 case 3 個 fresh Gemini 3.1 Pro Low processes，精確 12 次；無 probe、無 retry、無第 13 次。
- 任一 case 未達 3/3 exit、strict parse、schema、rubric、mapper、expected verdict/codes、candidate SHA invariant，立即 `BLOCKED`。
- evidence 只存 SHA、byte length、typed gates、case/result 摘要；不保存 prompt、raw response、stderr、秘密、PII 或本機絕對路徑。
- 外層只聲明 `external_cli_process_invocations=12`；`provider_model_calls=unobservable/unknown`。

## Gate 與交付

- 跑 focused tests、full pytest、py_compile、stored corpus 重算、changed-file allowlist、privacy/secret/raw/path/debug 與 `git diff --check`。
- 建立單一 repair candidate commit，只能回 `DELIVERED_CANDIDATE` 或 `BLOCKED`。
- candidate 必須由另一張獨立 Review 卡固定 SHA 審查；即使 GO，也只可進 end-to-end 4-product canary，尚不得恢復三條內容線。
