---
card_id: CARD-CONTENT-GEMINI-REVIEWER-MINIMAL-GATE-IMPLEMENTATION-001
chain_id: CONTENT-GEMINI-REVIEWER-MINIMAL-GATE-IMPLEMENTATION-001
status: DRAFTED
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 將已審核的 minimal judgment＋deterministic mapper 接進 production reviewer/outbox seam，涉及 strict parse、SHA binding、失敗狀態與外部 CLI corpus
ownership: production Reviewer minimal transport、local mapper、sanitized corpus 與 candidate 交付
allowlist:
  - scripts/agy_seo_copy_pipeline.py
  - scripts/agy_gemini_outbox.py
  - scripts/agy_gemini_runner.py
  - scripts/agy_gemini_reviewer_corpus.py
  - tests/test_agy_seo_copy_pipeline.py
  - tests/test_agy_gemini_outbox.py
  - tests/test_agy_gemini_reviewer_corpus.py
  - docs/pantheon_gemini_outbox_runner.md
  - docs/pantheon_gemini_reviewer_transport_strategy.md
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_minimal_gate_implementation_001/**
forbidden_scope:
  - app/**
  - 正式文章、registry、metadata、prerender、sitemap、feed、redirects
  - Writer prompt/schema 行為變更，除非 strict duplicate-key parser 的共用安全修正且有 regression test
  - tolerant JSON、code-fence stripping、substring extraction、JSON/LLM repair
  - Gemini CLI 安裝、登入、OAuth、token 或全域設定修改
  - merge、push、deploy、publish、production
verification:
  - red-green production reviewer/outbox tests
  - 12-process sanitized production-path corpus
  - focused and full pytest, py_compile, diff/allowlist/privacy scans
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_minimal_gate_implementation_001/
design_candidate_sha: 5018589dd014e4c3edf5c6a3d736d912957ec400
design_review_evidence_sha: c8e253f039ec1bda7c854c2eae7ff1d25d3373de
design_integrated_sha: 4e2a9258a1e762935e01d495bf5f2b48cefee05d
source_kind: commit
source_sha: 4e2a9258a1e762935e01d495bf5f2b48cefee05d
source_branch: main
source_clean: true
main_cwd: <repo-root>
---

# CARD-CONTENT-GEMINI-REVIEWER-MINIMAL-GATE-IMPLEMENTATION-001｜production minimal Reviewer gate

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-REVIEWER-MINIMAL-GATE-IMPLEMENTATION-001`。
派工對象｜strict implementation；以已 re-review GO 的 `ReviewerJudgmentV1` 為唯一規格，不重新設計。
任務目的｜把 Gemini Pro Low 的最小 judgment、安全 strict parse 與 deterministic mapper 接入既有 production reviewer/outbox seam。
可改範圍｜三個既有 pipeline/runner、獨立 corpus harness、相關 tests/docs/evidence；文章與發布檔全部禁止。
驗收證據｜production path red-green、4-case×3 fresh-process corpus、SHA/candidate/Writer invariant、完整測試與 candidate commit。

## 固定 interface

- Gemini Reviewer 唯一輸出 `ReviewerJudgmentV1`：`verdict`、`hard_failure`、`findings[{code,severity,message}]`；`additionalProperties=false`。
- strict parser 拒絕任一層 duplicate keys；不接受 Markdown、前後文字或 JSON 修補。
- deterministic rubric：
  - `APPROVE` 必須 `hard_failure=false` 且 `findings=[]`。
  - `REJECT` 必須 `hard_failure=true` 且至少一筆 HARD finding。
  - code 必須在該 request 的 allowlist；code/message trim 後非空。
- local mapper 只從可信本地資料注入 schema version、run/article identity、candidate SHA 與 summary；judgment 欄位原樣搬移，不補猜、不改 verdict。
- request/response/job receipts 必須繼續綁定 SHA；candidate SHA 不得因 reviewer parse/map 改變，Writer 不得因 reviewer failure 重跑。

## 失敗與 retry 邊界

- 本 implementation 不新增 transport retry。Reviewer parse/schema/rubric/map 任一失敗立即 fail closed，維持既有 BLOCKED/PENDING 隔離。
- 非 Reviewer 路徑不得誤用 minimal schema；Writer 行為與文章生成契約不變。
- evidence 只存 request/config/output SHA、byte length、typed gate、必要 error position；不保存 prompt、raw response、stderr、秘密、PII 或本機絕對路徑。
- 外層只計 `external_cli_process_invocations`；`provider_model_calls=unobservable/unknown`。

## Production-path corpus

- 使用新 harness 呼叫實際 production Reviewer transport/parse/map 路徑，不呼叫 Writer、不寫 `app/**`。
- 四個 sanitized public cases：短 APPROVE、長 APPROVE、單一 HARD REJECT、混合 HARD REJECT；每 case 3 個 fresh Gemini 3.1 Pro Low process，共精確 12 次。
- 每 case 需 3/3 exit、strict parse、schema、rubric、mapper、expected verdict/codes、candidate SHA invariant；無 retry、無第 13 次。
- 任一 case 未達 3/3 立即 `BLOCKED`，不得以 Pro High、Flash 或 tolerant parser 補救。

## Gate 與交付

- 先建立 red-capable tests，再改 production code。
- 跑 focused tests、full pytest、py_compile、corpus 重算、changed-file allowlist、privacy/secret/raw/path/debug 與 `git diff --check`。
- 建立單一 candidate commit，只能 `DELIVERED_CANDIDATE` 或 `BLOCKED`。
- candidate 後必須獨立 Review；即使 GO，也只可進 end-to-end 4-product canary，尚不得恢復新文、舊文修復或 GSC 線。
