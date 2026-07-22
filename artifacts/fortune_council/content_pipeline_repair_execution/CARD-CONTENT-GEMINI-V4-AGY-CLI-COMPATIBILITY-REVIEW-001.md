---
card_id: CARD-CONTENT-GEMINI-V4-AGY-CLI-COMPATIBILITY-REVIEW-001
chain_id: CONTENT-GEMINI-V4-AGY-CLI-COMPATIBILITY-001
status: CARD_DRAFTED
role: independent_reviewer
ownership: read_only_candidate_review
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 外部 CLI argv/env、公開資料邊界、單次 process 與 replay 契約屬高風險跨模組審查
base_sha: 6d318a53edfe60a1b583b2c687e9317b41aeb1b8
candidate_sha: 2cfde3a69295f152c5e418f6a140e4543f53cbf9
allowlist: []
forbidden_scope:
  - 所有檔案修改、commit、merge、push、deploy、publish
  - 真實 Gemini／agy model invocation
  - retry、fallback、文章產出或內容線恢復
verification:
  - git diff --check 6d318a5..2cfde3a
  - <repo-venv>/bin/python -m pytest tests/test_agy_gemini_v4_broker.py tests/test_agy_gemini_outbox.py -q
  - 逐項核對 argv、env、PUBLIC_SANITIZED、model mapping、process count、ledger/replay 與 no-resend
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_agy_cli_compatibility_001/
worktree_path: PENDING
cwd: PENDING
main_cwd: <repo-root>
thread_id: PENDING
thread_status: CARD_DRAFTED
---

# Gemini V4 agy CLI 相容層｜獨立 Review

只審查 `6d318a5..2cfde3a`。必須直接讀 diff、測試與 evidence，不接受 implementation 的完成文案作為證據。

## 必查問題

1. `agy` 是否只接受兩個核准 model mapping，未知 model 是否在 ledger／fork 前拒絕。
2. `--print` prompt 是否限定為 UTF-8、非空、最多 256 KiB 且符合 outbox forbidden patterns；是否洩漏到 ledger、anchor、control 或 evidence。
3. target argv、stdin、environment、FD 與 temporary log lifecycle 是否 closed；是否仍恰好一個 target process。
4. CommandFrame v2 是否完整綁定 executable digest、profile、model label、payload class、prompt SHA／length 與 timeout。
5. nonzero、timeout、exec failure、digest race、replay no-resend 與舊 raw-stdin synthetic profile是否回歸。
6. 文件宣稱是否與程式和測試一致；是否存在可繞過 PUBLIC_SANITIZED 或錯把 CLI parser 成功當 model 成功的路徑。

## 回覆格式

- `VERDICT: GO` 或 `VERDICT: NO-GO`
- Reviewed commit（完整 SHA）
- Findings：依嚴重度列檔案、行號、重現方式與最小修正方向；無 finding 時明列 `None`
- Verification：實際執行命令與結果
- 明列：未修改檔案、未呼叫真 Gemini、未整合
