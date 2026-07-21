---
card_id: CARD-CONTENT-GEMINI-REVIEWER-SINGLE-SHOT-V3-REPAIR-002-REPLACEMENT-REVIEW-001
chain_id: CONTENT-GEMINI-REVIEWER-SINGLE-SHOT-V3-001
status: CARD_DRAFTED
role: replacement_final_reviewer
thickness: strict
risk: high
reviewed_candidate_sha: f6a86a5884a55514133c9ce2ea9553c32444bca2
replaces_thread_id: 019f844f-5219-7221-a1ac-b4b72a976ba2
replacement_reason: 原Reviewer final re-review連續三次平台systemError，未產生verdict或commit；依停損改用新獨立Reviewer
allowlist:
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_single_shot_v3_repair_002_replacement_review_001/**
forbidden_scope:
  - candidate, code, tests, docs and all prior evidence modification
  - Gemini CLI, HTTP or external model invocation
  - fix, repair, merge, push, deploy, publish or content recovery
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_single_shot_v3_repair_002_replacement_review_001/
thread_id: PENDING
thread_status: CARD_DRAFTED
worktree_path: PENDING
cwd: PENDING
---

# Replacement final review｜V3 Repair 2

## 任務

對 candidate `f6a86a5884a55514133c9ce2ea9553c32444bca2` 執行一次完整、獨立、唯讀的 final re-review。這是原 Reviewer 因三次平台錯誤未完成後的替代執行，不是新 Repair、不是額外修復代數。

## 啟動 Gate

- 獨立 clean worktree，HEAD 為只含本卡的 provisioning commit，HEAD^ 精確為 reviewed candidate。
- Repair 1 re-review、Repair 2 card/evidence可讀；原 final review無verdict/commit，不吸收其未提交檔案。
- Python只用主工作區既有 `.venv`；全程離線。

## 必審

1. CLI missing/preflight的terminal、gate、receipt皆為0 process；success/nonzero/timeout皆為1；無第二launch。
2. application-level owner capability是否真能阻止非owner writer在Popen spawn前完成或破壞terminal/gate。
3. 同OS user、不預先持token的正常子程序，能否讀取token或raw-write破壞records。若能，且production契約宣稱可防，判NO_GO。
4. 舊probe的raw `Path.write_bytes` callback entry=1與真實Popen spawn=0須分開判讀；不得僅依文件自我排除就接受，也不得把callback entry誤稱external process。
5. Popen改造的command/stdin/env/cwd/timeout/nonzero/stdout/stderr與resource cleanup相容性。
6. strict outbox、anchored replay/allow_other_operations、witness、resume與third-blocker不得回歸。
7. focused/full、py_compile、stored6-operation offline replay、retry search、allowlist/privacy/diff；不得fresh外部call。

## 結論

- `GO`：兩個剩餘P1關閉且無新P1。
- `NO_GO`：列severity、path:line、可重現exploit與最小修復界面；V3已達Repair 2上限，主線須封鎖，禁止Repair 3。
- `BLOCKED`：只限客觀環境阻斷；同 blocker三次即停。

只新增本卡 evidence並提交單一 review commit；不得修碼或整合。
