---
card_id: CARD-CONTENT-GEMINI-REVIEWER-V4-IMPLEMENTATION-REVIEW-001
chain_id: CONTENT-GEMINI-REVIEWER-V4-IMPLEMENTATION-001
status: CARD_DRAFTED
role: independent_reviewer
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
candidate_sha: bfdf6cb841235f87fd6af23576eb8a458a78f3c9
candidate_parent_sha: ef5b81307ca895d500ce1b6c346d17a451428942
allowlist:
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_v4_implementation_review_001/**
forbidden_scope:
  - candidate code, tests and implementation evidence
  - app/**, articles, registry, metadata and publishing files
  - dependency, real Gemini invocation, HTTP or external model
  - repair, merge, push, deploy, publish or content-line recovery
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_v4_implementation_review_001/
thread_id: PENDING
thread_status: CARD_DRAFTED
worktree_path: PENDING
cwd: PENDING
---

# Gemini Reviewer V4 Implementation｜Independent Review 1

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-REVIEWER-V4-IMPLEMENTATION-REVIEW-001`。
派工對象｜全新 `gpt-5.6-sol`、`high` Reviewer；不得沿用 implementation 作者判斷。
審查範圍｜`ef5b813..bfdf6cb`；只審一個 bounded broker candidate。
唯一可寫｜本卡獨立 review evidence root。
交付｜fresh probes、findings、verification、正式 `GO / NO_GO` 與單一 evidence commit。

## 啟動 Gate

- 獨立 clean worktree；HEAD 為只含本卡的 provisioning commit，HEAD^ 必須是 candidate `bfdf6cb841235f87fd6af23576eb8a458a78f3c9`。
- 完整讀 AGENTS、implementation 卡、已獲 GO 的架構、candidate diff/evidence/tests；不得修改 candidate。
- Python 只用主專案既有 `.venv`；synthetic subprocess/fake executable only；離線、不下載、不呼叫 Gemini/HTTP/model。

## Reviewer-owned fresh probes

1. 以獨立 fake target 驗 success/nonzero/timeout、missing executable、exec failure、crash-before-fork、fork/exec window、terminal loss；逐案核對 replay status/count/complete/resend/reason及真實 target 次數。
2. 驗證 broker 唯一 launcher：同 operation replay 不啟動第二個 target；沒有 dual-spawn、隱式 retry或 flag-on legacy fallback。
3. 直接觀察 exec 後 FD table、argv/env/stdin；只能有 stdio，ledger FD/path、anchor、operation/item/attempt identity不可洩入 target。
4. 對 schema/version/binding/order/frame/hash-chain、legacy aliases、PID domain、duplicate/partial/truncated records做 fresh negative controls。
5. 對 anchor missing/mismatch/ledger-ahead/CAS conflict做 fresh controls；不得由 ledger 自證或自補 anchor。
6. 驗 runner flag-off 只呼叫 legacy一次；flag-on只呼叫 broker一次。`BLOCKED/AMBIGUOUS/INVALID`及 misbound COMPLETE 必須 failed+archive、無 inbox、無 fallback。
7. 驗 immutable result：外部取得/修改 dict 不得改變 receipt 本體或後續讀值。
8. 核對 exception、timeout、broken pipe、child exit與 file descriptor cleanup，不得留下 child/FD/temporary-state ownership漏洞。

## Review 判定

- 不以 candidate tests 或 evidence 代替 fresh probes；每個關鍵 claim 必須有 Reviewer-owned command/result。
- 核對 implementation 僅修改卡片 11 個 allowlist 路徑，且 runner 只有一個 callsite切換；`agy_seo_copy_pipeline.py` 等禁區未變。
- 重跑 focused、affected、full suite、py_compile、determinism、`git diff --check`。
- 兩個 Ziwei provider failure 必須在 candidate parent 的乾淨 tree 以相同命令重現才可列 baseline；否則是 P1。
- `GO` 需無 P0/P1、所有架構必要契約有 fresh evidence；`NO_GO` 依 P0-P3列可重現 finding與 bounded Repair 範圍。
- evidence 至少 `review.md`、`findings.json`、`fresh_probes.py`、`fresh_results.json`、`verification.txt`。
- 最後只提交純 review evidence commit；不得修、merge、push、deploy、publish、開真實 CLI canary或恢復內容線。
