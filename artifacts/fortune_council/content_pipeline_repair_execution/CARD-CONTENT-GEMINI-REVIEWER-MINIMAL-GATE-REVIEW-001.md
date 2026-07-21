---
card_id: CARD-CONTENT-GEMINI-REVIEWER-MINIMAL-GATE-REVIEW-001
chain_id: CONTENT-GEMINI-REVIEWER-MINIMAL-GATE-IMPLEMENTATION-001
status: DRAFTED
thickness: standard
risk: high
model: gpt-5.5
reasoning: high
model_reason: 固定 SHA 的四檔獨立 review；需驗證 fixture 語意、exact-set gate、corpus 證據與隱私，但不需再次呼叫外部模型
ownership: 只審查 Repair 1 candidate，輸出 findings 與 GO/NO_GO，不修改 candidate
allowlist:
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_minimal_gate_review_001/**
forbidden_scope:
  - scripts/**
  - tests/**
  - docs/**
  - app/**
  - 正式文章與所有發布檔
  - Gemini CLI／HTTP／任何外部模型呼叫
  - 修復、merge、push、deploy、publish、production
verification:
  - fixed-SHA diff/spec/standards review
  - fixture semantics and exact-set regression audit
  - stored 12-row corpus recomputation and privacy scan
  - focused tests, py_compile, git diff check
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_minimal_gate_review_001/
base_sha: c5b33832d2c7ccb323e43fed09f502c6a3494a2d
candidate_sha: 66c070f43c61d38df4a1f7944b277ca9dc05406e
reviewed_commit_required: 66c070f43c61d38df4a1f7944b277ca9dc05406e
source_kind: commit
source_sha: 66c070f43c61d38df4a1f7944b277ca9dc05406e
source_clean: true
main_cwd: <repo-root>
---

# CARD-CONTENT-GEMINI-REVIEWER-MINIMAL-GATE-REVIEW-001｜Repair 1 固定 SHA 獨立 Review

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-REVIEWER-MINIMAL-GATE-REVIEW-001`。
派工對象｜獨立 Reviewer；不得沿用 implementation／repair thread，也不得修改 candidate。
任務目的｜對 `c5b33832..66c070f` 做 spec axis 與 standards axis 審查，確認 fixture 修復沒有放寬 production 契約。
可改範圍｜只可新增本 Review 的 sanitized evidence；任何程式、測試、文章與發布檔皆禁止修改。
驗收證據｜固定 reviewed SHA、逐 finding path:line、離線重算／測試、privacy/allowlist，以及明確 `GO` 或 `NO_GO`。

## 必查項

- Candidate parent 必須精確為 `c5b33832d2c7ccb323e43fed09f502c6a3494a2d`；reviewed commit 必須精確為 `66c070f43c61d38df4a1f7944b277ca9dc05406e`。
- Changed files 必須只有 corpus script、對應 test、repair `corpus.json` 與 `decision.md`。
- `single-hard-reject` 必須只有保證性宣稱，不含步驟、操作、投資指令或可合理觸發其他 code 的語意。
- Expected verdict 仍為 `REJECT`，expected codes 仍採 exact set `GUARANTEE_CLAIM`；測試必須證明額外 code 會失敗。
- Production pipeline、Reviewer parser/schema/mapper/prompt/finding allowlist 必須零修改。
- Stored corpus 必須可離線重算為 12 rows、四 case 各 3/3、typed gates 全 true、candidate SHA invariant；不得把 `provider_model_calls` 說成可觀測。
- Evidence 不得含 prompt、raw response、stderr、秘密、PII 或本機絕對路徑。
- Full pytest 的兩個 Ziwei failure 必須與 candidate diff 無關且不得被誤寫為全綠。

## Review 輸出

- Findings 依 P0→P3 排序，每筆必須包含 path:line、觸發條件、風險與建議修法。
- 分開回報 Spec axis、Standards axis、Testing gaps、Residual risks。
- 任一 P0/P1/P2、SHA／scope／evidence 不一致或關鍵驗證無法重現，verdict 為 `NO_GO`。
- 無阻塞 findings 才可 `GO`；只代表可交主線考慮進 end-to-end 4-product canary，不代表可整合或恢復三條內容線。
- 不呼叫 Gemini，不修改 candidate，不 merge／push／deploy／publish。
