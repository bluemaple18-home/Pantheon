---
card_id: CARD-CONTENT-GEMINI-REVIEWER-V4-ARCHITECTURE-REPAIR-002
chain_id: CONTENT-GEMINI-REVIEWER-V4-001
status: CARD_DRAFTED
repair_generation: 2
role: architecture_repair
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
base_candidate_sha: ef6d6f3a26e6d44c3586cdb4beee37918d58c9ee
review_evidence_sha: 393f8469f07840ddbb056c9c38123ea2ef338f99
reviewer_thread_id: 019f881f-825d-79a1-b8d3-4fcdd07f0a86
allowlist:
  - docs/pantheon_gemini_reviewer_v4_architecture.md
  - scripts/agy_gemini_v4_architecture_probe.py
  - tests/test_agy_gemini_v4_architecture_probe.py
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_v4_architecture_repair_002/**
forbidden_scope:
  - Review/spike/V1-V3/Repair-1 evidence modification
  - existing production pipeline, outbox, runner, transport and operation modules
  - app/**, articles, registry, metadata and publishing files
  - framework dependency, automatic retry or Gemini invocation
  - merge, push, deploy, publish, production or content-line recovery
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_v4_architecture_repair_002/
thread_id: PENDING
thread_status: CARD_DRAFTED
worktree_path: PENDING
cwd: PENDING
---

# V4 Architecture Repair 2｜Replay terminal、schema v2 與 strict matrix

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-REVIEWER-V4-ARCHITECTURE-REPAIR-002`；Repair 2/2，最後修復輪。
派工對象｜`gpt-5.6-sol`、`high`；只修 re-review 固定 2 個 P1 與 1 個 P2。
任務目的｜修正 terminal 缺失的誠實分類、隔離舊事件別名、收緊 PID domain，讓 strict replay matrix 能被真實反例拉低。
可改範圍｜V4 架構文件、隔離 POC/tests 與 Repair 2 evidence。
驗收證據｜原 Reviewer fresh probes RED→GREEN、完整合法狀態表、negative controls 與單一 candidate commit。

## 啟動 Gate

- 獨立 clean worktree；HEAD 為只含本卡的 provisioning commit，父鏈包含 Repair 1 candidate 與 re-review evidence。
- 完整讀 re-review `re_review.md`、`findings.json`、`fresh_adversarial_probes.py` 與 `fresh_results.json`；三項 finding 必須先可重現。
- Python 只使用主工作區既有 `.venv`；synthetic subprocess 與 fake executable only；不連網、不使用真實憑證。
- 不擴張 V4 架構、不修改 production；所有變更必須直接對應下列三項 finding。

## P1-01｜已確認執行但缺 terminal 必須 BLOCKED／1

- 合法 prefix 已有 `EXEC_CONFIRMED` 與有效正整數 PID，但缺 `PROCESS_TERMINAL` 時，固定 replay 為 `BLOCKED`、process count `1`、`complete=false`、`resend=false`。
- `PROCESS_TERMINAL_MISSING` 是可解釋的 blocked reason，不得被通用 error path 誤判成 `INVALID/UNKNOWN`。
- `INVALID/UNKNOWN` 只保留給 schema、binding、order、frame、chain 或其他資料驗證失敗。
- 文件、probe 與 tests 必須共享同一張合法 status/count/completeness/resend 表。

## P1-02｜Schema v2 禁止舊別名與無效 PID

- current schema v2 event set 不接受 `PROCESS_NOT_STARTED`、`PROCESS_STARTED` 或其他舊別名。
- 若保留 legacy decoder，必須獨立 version/boundary，且不得產生 current-schema `COMPLETE`。
- `EXEC_CONFIRMED.pid` 必須是正整數；0、負數、bool、字串與缺值皆拒絕。
- fresh counterexamples 不得再得到 `COMPLETE/0` 或 `COMPLETE/1`。

## P2｜Strict replay matrix 必須涵蓋真實反例

- `strict_replay` observable/predicate 從完整合法狀態與 process-count 表推導，而非只檢查部分 fixture。
- real negative controls 至少包含：terminal loss、legacy alias、PID domain、既有 illegal order/frame/binding/chain cases。
- 任一 required control 未拒絕或分類錯誤時，strict replay cell 必須自動降級，不能維持 `DETECTED`。
- baseline、單項反轉與多項反轉結果可重現，且 POC 連跑兩次 byte-identical。

## 驗證與交付

- 先保存 Reviewer 三項 counterexample 的 RED，再完成 GREEN；不得改寫 Reviewer evidence。
- focused tests、`py_compile`、POC 兩次 byte-identical、derived matrix、allowlist、敏感資訊/原始本機路徑/`[DBG-]`、`git diff --check`。
- 不呼叫 Gemini、HTTP 或外部 model。
- evidence 至少包含 `root-cause.md`、`red-green.txt`、`verification.txt`、`decision.md`。
- 建立單一 Repair 2 architecture candidate，狀態只能 `READY_FOR_REVIEW` 或 `BLOCKED`；回原 Reviewer 做最終 re-review，不自審 GO、不進 production。
- 本輪若 Reviewer 最終仍為 NO_GO，整條 `CONTENT-GEMINI-REVIEWER-V4-001` 固定 BLOCKED，不得建立 Repair 3。
