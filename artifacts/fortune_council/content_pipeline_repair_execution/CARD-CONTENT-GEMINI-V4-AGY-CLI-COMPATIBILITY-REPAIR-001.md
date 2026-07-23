---
card_id: CARD-CONTENT-GEMINI-V4-AGY-CLI-COMPATIBILITY-REPAIR-001
chain_id: CONTENT-GEMINI-V4-AGY-CLI-COMPATIBILITY-001
status: CARD_DRAFTED
role: repair_engineer
generation: 1/2
ownership: fix_only_review_findings
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 三項P1涉及production routing、exec TOCTOU與post-fork process cleanup，另有可信completion邊界
base_candidate_sha: 2cfde3a69295f152c5e418f6a140e4543f53cbf9
reviewer_thread_id: 019f8cad-92ed-7993-8584-285e70214202
review_verdict: NO_GO
allowlist:
  - scripts/agy_gemini_v4_broker.py
  - scripts/agy_gemini_runner.py
  - tests/test_agy_gemini_v4_broker.py
  - tests/test_agy_gemini_outbox.py
  - docs/pantheon_gemini_v4_agy_cli_compatibility.md
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_agy_cli_compatibility_repair_001/**
forbidden_scope:
  - app/**, articles, registry, metadata and publishing files
  - dependency installation or unrelated refactor
  - true Gemini/agy model invocation, retry or fallback
  - merge, push, deploy, publish, acceptance or content-line recovery
verification:
  - 四項finding各有已執行的RED-capable regression與GREEN結果
  - <repo-venv>/bin/python -m pytest tests/test_agy_gemini_v4_broker.py tests/test_agy_gemini_outbox.py -q
  - <repo-venv>/bin/python -m py_compile scripts/agy_gemini_v4_broker.py scripts/agy_gemini_runner.py tests/test_agy_gemini_v4_broker.py tests/test_agy_gemini_outbox.py
  - git diff --check
  - allowlist, privacy, [DBG-], worktree clean
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_agy_cli_compatibility_repair_001/
worktree_path: PENDING
cwd: PENDING
main_cwd: <repo-root>
thread_id: PENDING
thread_status: CARD_DRAFTED
---

# Gemini V4 agy CLI 相容層｜Repair 1

只修原 reviewer 對 `2cfde3a` 的 3 P1＋1 P2。開始前讀完整 reviewer final；先為每項 finding 建立可自動重現的 RED，再做最小根因修復。

## 固定 findings

1. **P1｜production profile 可被 executable basename 繞過**  
   真 agy／symlink／wrapper 命名為 `agy-current` 時會落入 `raw_stdin_v1`，繞過 model 與 PUBLIC_SANITIZED gate。修復須由 production runner 顯式選擇 closed profile；synthetic profile 不得由 production 設定抵達；未知 profile／executable fail closed。

2. **P1｜digest 與實際 exec pathname 存在 TOCTOU**  
   驗證 `read_bytes()` 後、`Popen(path)` 前替換檔案，可執行不同 bytes。修復須讓實際 exec 與已雜湊 identity 是同一份不可替換 snapshot／FD 或等價機制；不得只縮小 race window。

3. **P1｜post-fork anchor CAS failure 可能留下 child**  
   `EXEC_CONFIRMED` append/CAS 失敗時，所有 post-fork exception 都必須 kill、wait、關閉 pipes、清理 temporary directory，且 replay／result fail closed、不得重送。

4. **P2｜schema-valid parser/stub stdout 被當成 model success**  
   production receipt 必須綁定顯式 production profile與受信任 executable identity／digest；synthetic/fake profile不得產生 production runner可接受的 receipt。若 agy 本身沒有更強 completion provenance，文件必須精確標明「exit 0＋schema」只能在 trusted executable identity成立後代表 transport completion，不能宣稱供應商內部模型呼叫可證。

## 實作界線

- `run_single_shot` 的 production caller 必須顯式傳入 profile／expected executable identity，不可再由 basename推論安全等級。
- synthetic test helper/API 與 production receipt必須型別或binding可區分；runner只接受 production receipt。
- executable snapshot、log與child lifecycle由單一 owner finally收斂；target仍恰好一個 process，FD policy不放寬。
- 保留 ledger/replay/no-resend、兩個 model mapping、PUBLIC_SANITIZED、closed argv/env及flag-off legacy行為。
- 不得用真 Gemini 驗證，不得用 retry掩蓋 failure。

## 交付

單一 Repair candidate commit；回報完整 SHA、parent、changed files、四組 RED/GREEN、focused/compile/diff/allowlist/clean。狀態只能 `READY_FOR_RE_REVIEW` 或 `BLOCKED`，不得自審 GO。
