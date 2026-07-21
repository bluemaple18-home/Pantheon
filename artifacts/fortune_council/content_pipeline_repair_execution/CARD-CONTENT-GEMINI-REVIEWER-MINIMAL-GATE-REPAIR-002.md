---
card_id: CARD-CONTENT-GEMINI-REVIEWER-MINIMAL-GATE-REPAIR-002
chain_id: CONTENT-GEMINI-REVIEWER-MINIMAL-GATE-IMPLEMENTATION-001
status: DRAFTED
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 最後一代 Repair，需同時修復 receipt 可稽核性、跨入口 process accounting 與 per-slot allowlist 三個 production P2
ownership: 僅修 full-range Review 的三個 P2，補離線 regression 與 candidate evidence
allowlist:
  - scripts/agy_seo_copy_pipeline.py
  - tests/test_agy_seo_copy_pipeline.py
  - tests/test_agy_gemini_outbox.py
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_minimal_gate_repair_002/**
forbidden_scope:
  - scripts/agy_gemini_reviewer_corpus.py
  - tests/test_agy_gemini_reviewer_corpus.py
  - docs/**
  - app/**
  - 正式文章、registry、metadata、prerender、sitemap、feed、redirects
  - Writer prompt/schema/content retry 行為
  - tolerant JSON、code-fence stripping、substring extraction、JSON/LLM repair
  - Gemini CLI／HTTP／任何外部模型呼叫
  - merge、push、deploy、publish、production
verification:
  - red-green regressions for all three P2 findings
  - production Reviewer focused and full pytest
  - py_compile, stored corpus recomputation, diff/allowlist/privacy scans
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_minimal_gate_repair_002/
base_sha: 4e2a9258a1e762935e01d495bf5f2b48cefee05d
candidate_sha: 66c070f43c61d38df4a1f7944b277ca9dc05406e
review_evidence_sha: 472fb0c736971d1cae7a6f5979b5c27249f2aa21
source_kind: commit
source_sha: 66c070f43c61d38df4a1f7944b277ca9dc05406e
source_clean: true
repair_generation: 2
main_cwd: <repo-root>
---

# CARD-CONTENT-GEMINI-REVIEWER-MINIMAL-GATE-REPAIR-002｜修復 full-range Review 三個 P2

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-REVIEWER-MINIMAL-GATE-REPAIR-002`。
派工對象｜strict Repair 2；這是本 chain 最後一代修復，只處理固定三個 P2。
任務目的｜保留 parse-failure fingerprint、準確計算所有 Reviewer processes、阻止跨 slot finding code 錯綁。
可改範圍｜production pipeline、兩個既有測試檔與本卡 evidence；corpus fixture、Writer、文章與發布檔禁止。
驗收證據｜三項 red→green、既有 84+ focused tests、full pytest、stored corpus 重算、隱私／allowlist 與單一 candidate commit。

## Finding 1｜error receipt fingerprint

- 位置：`scripts/agy_seo_copy_pipeline.py:2129` 附近。
- 觸發：transport 已取得 response bytes 並填入 `last_transport_receipt`，strict parse 隨後拋錯。
- 修復：error receipt 必須保留已存在的 `output_sha256` 與 `output_bytes`；不得保存 raw response、stderr 或 prompt。
- 測試：malformed Reviewer JSON 造成 parse error 時，receipt 有正確 fingerprint/bytes，且 failure 仍 fail closed、不重跑 Writer。

## Finding 2｜process accounting

- 位置：`scripts/agy_seo_copy_pipeline.py:2452` 及所有 Reviewer invocation seams。
- 觸發：多篇第 k 篇失敗、reviewer-only 多輪、closure 逐篇 review。
- 修復：每次實際 Reviewer invocation 都必須恰好計數一次；即使後續 parse/map 失敗也不可少算，且不得用固定 1 代表 N 篇。
- 優先由既有 immutable operation receipts 或單一 invocation seam 推導，避免各入口散落猜數。
- 測試：第 k 篇失敗、五篇成功、review-only 1–3 rounds、closure 五篇，均驗證精確計數；Writer process/retry 不變。

## Finding 3｜target-specific allowlist

- 位置：`scripts/agy_seo_copy_pipeline.py:1911` 附近。
- 觸發：slot B 的 deterministic code 被 batch-wide allowlist 提供給 slot A，模型回傳後被 mapper 綁到 A。
- 修復：每個 Reviewer request 只能取得該 target slot 合法的 codes；不得以整批 deterministic codes 擴張所有 slot。
- 本地 deterministic findings 仍由可信本地 merge 負責；不得讓模型偽造另一 slot 的 deterministic finding。
- 測試：A 回 B-only code 必須 fail closed；B 的合法 code 可通過；多篇 mapping 與 candidate SHA 必須保持正確。

## Gate 與交付

- 先為三個 findings 各建立會紅的 regression，再做最小 production 修復。
- 不呼叫 Gemini 或任何外部模型；已存 corpus 只可離線重算。
- 跑 affected focused suite、full pytest、py_compile、stored corpus 重算、changed-file allowlist、privacy/secret/raw/path/debug 與 `git diff --check`。
- 建立單一 Repair 2 candidate commit，回完整 SHA；不得 merge／push／deploy／publish。
- 完成後必須回同一 Reviewer thread `019f834d-b192-73f1-8282-c3832fbbce70` re-review；若仍 `NO_GO`，整條 chain 立即 `BLOCKED`，不得開 Repair 3。
