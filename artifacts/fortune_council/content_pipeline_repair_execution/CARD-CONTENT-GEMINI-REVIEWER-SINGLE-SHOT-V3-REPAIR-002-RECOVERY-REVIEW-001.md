---
card_id: CARD-CONTENT-GEMINI-REVIEWER-SINGLE-SHOT-V3-REPAIR-002-RECOVERY-REVIEW-001
chain_id: CONTENT-GEMINI-REVIEWER-SINGLE-SHOT-V3-001
status: CARD_DRAFTED
role: recovery_final_reviewer
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
reviewed_candidate_sha: f6a86a5884a55514133c9ce2ea9553c32444bca2
recovery_from_commit: e819013
allowlist:
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_single_shot_v3_repair_002_recovery_review_001/**
forbidden_scope:
  - candidate, code, tests, docs and all prior evidence modification
  - Gemini CLI, HTTP or external model invocation
  - fix, repair, merge, push, deploy, publish or content recovery
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_single_shot_v3_repair_002_recovery_review_001/
thread_id: PENDING
thread_status: CARD_DRAFTED
worktree_path: PENDING
cwd: PENDING
---

# Recovery final review｜V3 Repair 2

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-REVIEWER-SINGLE-SHOT-V3-REPAIR-002-RECOVERY-REVIEW-001`。
派工對象｜`gpt-5.6-sol`、`high`；獨立 final Reviewer。
任務目的｜在 Reviewer 執行環境恢復後，對固定 candidate 產生唯一正式 GO／NO_GO verdict。
可改範圍｜只可新增本卡 recovery review evidence。
驗收證據｜fresh adversarial probes、focused/full、offline replay、單一 review commit。

## 啟動 Gate

- 獨立 clean worktree；HEAD 為只含本卡的 provisioning commit，HEAD^ 精確為 `f6a86a5884a55514133c9ce2ea9553c32444bca2`。
- 完整讀取 Repair 1 re-review、Repair 2 card/evidence與 `platform-blocked.md`；不得吸收舊 Reviewer 未提交 probe。
- Python只用主工作區既有 `.venv`；全程離線。

## 必審

1. CLI missing/preflight之 terminal、gate、receipt皆為0 process；success/nonzero/timeout皆為1；failure code一致且無第二launch。
2. owner capability是否讓正常 application-level non-owner writer在真實 Popen spawn前遭拒，actual spawn count=0且舊bytes不變。
3. 同 OS user、不預先持token的正常子程序能否讀token或 raw-write records；若能且 production contract宣稱可防，判 `NO_GO`。
4. 舊 raw `Path.write_bytes` callback entry與真實 Popen spawn分帳；不得以文件自我排除取代實測。
5. Popen改造的command/stdin/env/cwd/timeout/nonzero/stdout/stderr/resource cleanup相容性。
6. strict outbox、anchored replay／`allow_other_operations`、code-specific witness、resume／third-blocker／APPROVED不得回歸。
7. 跑 focused affected、full suite、py_compile、stored 6-operation offline replay、runtime retry search、allowlist、privacy、`git diff --check`；fresh external calls必須0。

## Finding 與結論契約

- finding必須包含severity、category、path:line、evidence、risk、suggested_fix、validation_gap、confidence。
- `GO`：兩個剩餘P1關閉且無新P1；回單一 evidence commit。
- `NO_GO`：列可重現exploit與最小修復界面；V3已達Repair 2上限，主線必須封鎖，禁止Repair 3。
- `BLOCKED`：僅客觀環境阻斷；同 blocker第三次即停，無第四次。
- 只審不修，不得整合或恢復內容線。
