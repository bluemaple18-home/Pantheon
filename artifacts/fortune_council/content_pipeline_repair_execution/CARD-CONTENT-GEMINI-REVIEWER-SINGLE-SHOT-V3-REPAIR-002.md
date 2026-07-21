---
card_id: CARD-CONTENT-GEMINI-REVIEWER-SINGLE-SHOT-V3-REPAIR-002
chain_id: CONTENT-GEMINI-REVIEWER-SINGLE-SHOT-V3-001
status: CARD_DRAFTED
repair_generation: 2
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 最後兩個P1涉及production process accounting與跨process namespace ownership
ownership: 只修Repair 1 re-review固定兩個P1，交付本鏈最後Repair candidate並回原Reviewer
base_candidate_sha: c2061f0945945af3ae6133d655780b8df0b79d8e
review_evidence_sha: 41b5942cafa01927b3230c095679f6d238f65f90
reviewer_thread_id: 019f844f-5219-7221-a1ac-b4b72a976ba2
allowlist:
  - scripts/agy_gemini_operations.py
  - scripts/agy_seo_copy_pipeline.py
  - tests/test_agy_gemini_operations.py
  - tests/test_agy_seo_copy_pipeline.py
  - docs/pantheon_gemini_reviewer_transport_strategy.md
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_single_shot_v3_repair_002/**
forbidden_scope:
  - implementation, Review, Repair 1 and re-review evidence modification
  - outbox, runner, transport probe behavior unless proven strictly necessary and escalated before edit
  - app/**, articles, registry, metadata and publishing files
  - runtime retry, automatic retry or attempt-chain authorization
  - Gemini installation/login/configuration change
  - merge, push, deploy, publish, production or content-line recovery
verification:
  - exact Repair 1 re-review probes RED then GREEN
  - CLI_NOT_FOUND 0-process production accounting
  - launcher-time concurrent terminal insertion prevented before process start
  - focused/full tests, py_compile, allowlist, privacy and diff checks
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_single_shot_v3_repair_002/
thread_id: PENDING
thread_status: CARD_DRAFTED
worktree_path: PENDING
cwd: PENDING
---

# CARD-CONTENT-GEMINI-REVIEWER-SINGLE-SHOT-V3-REPAIR-002｜封閉最後兩個 process safety 缺口

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-REVIEWER-SINGLE-SHOT-V3-REPAIR-002`；V3 chain 最後一代 Repair 2/2。
派工對象｜`gpt-5.6-sol`、`high`；只修 re-review 固定兩個 P1。
任務目的｜正確記帳 CLI_NOT_FOUND 為零 process，並讓 launcher 執行期間的 terminal namespace 保持 exclusive ownership。
可改範圍｜operation 共用模組、pipeline wrapper、對應 tests/docs與 Repair 2 evidence。
驗收證據｜原 fresh probes RED→GREEN、production public regressions、完整 gates 與 candidate SHA。

## 啟動 Gate

- 獨立 clean worktree；HEAD 為只含本卡的 provisioning commit，父鏈精確包含 Repair 1 candidate `c2061f0945945af3ae6133d655780b8df0b79d8e` 與 re-review evidence `41b5942cafa01927b3230c095679f6d238f65f90`。
- 完整讀取 Repair 1 card/evidence 與 re-review `re_review.md`、`fresh_adversarial_probes.py`。
- 原封重現兩個剩餘 P1 為 RED；不能重現即 BLOCKED，不猜修。
- 使用主工作區既有 `.venv`；不得安裝、下載或修改 Gemini。

## P1-01｜CLI_NOT_FOUND 必須是零 process

- production wrapper 在任何 subprocess/process launcher 尚未真正啟動前遇到 executable missing、preflight missing 或等價 OS error，必須完成 operation 為 `PROCESS_NOT_STARTED`，`process_started=false`、external process count=0。
- 不得先假定 process 已開始後才包裝 `FileNotFoundError`；process-start witness 必須由 launcher 在成功跨過實際 spawn 邊界後回報。
- CLI nonzero、timeout與成功仍為一個 external process；HTTP request 真正送出後的 terminal failure仍按既有契約記帳，不得為修 CLI 而改壞其他 transport。
- receipt、terminal、gate與 production-facing error code必須一致；同 operation不得第二次 launch。

## P1-02｜launcher 期間 terminal namespace exclusive ownership

- claim owner 在 launcher 全期間必須獨占 terminal/gate 寫入權；其他 process 即使知道路徑，也不能以合法 API 插入、覆寫或預建 terminal/gate。
- 需把 process launch 安排在可證明的 atomic ownership protocol 內。若平台只能用 owner token/capability，所有 terminal/gate writer必須驗證不可猜測且由 claim 建立的 capability；路徑存在本身不構成權限。
- Reviewer 精確 race：在 launcher callback 內嘗試以第二 writer 寫 terminal，必須在 process 真正啟動前拒絕，因此 `launcher_calls=0`，既有 bytes不變，operation仍可由 owner形成唯一合法 terminal/gate或明確 fail closed。
- 不得只把 `FileExistsError` 延後、捕捉或改文案；不得讓 process 已執行 1 次後才發現競態。
- 文件需誠實界定：不防可任意改記憶體、程式碼或 owner secret 的惡意 root；但 application-level API 與正常跨 process writer不可越權。

## 已關閉範圍不得回歸

- strict outbox persisted request binding。
- caller-owned anchored replay，包括 `allow_other_operations=True` 仍要求精確 external commitment。
- code-specific witness quote predicate。
- resume、第三同 blocker無第4、APPROVED不重送。

## TDD、驗證與交付

- 原 re-review 兩個 probe先 RED；逐 P1 補 production public regression，再最小修改至 GREEN。
- 補 CLI missing/preflight/nonzero/timeout/success 0/1 accounting matrix；補跨 process owner/non-owner、launcher callback race、partial existing path、duplicate completion、old bytes unchanged。
- 不改 prompt/schema，不跑 Gemini；只離線 replay既有6-operation corpus，無第7次。
- 跑 focused affected、full suite、py_compile、caller trace、runtime-retry search、stored replay、allowlist、privacy/secret/raw/path/`[DBG-]`、`git diff --check`。
- Ziwei baseline如實分列，不改無關檔。
- evidence至少 `root-cause.md`、`red-green.txt`、`verification.txt`、`decision.md`。
- 建立單一 Repair 2 candidate commit，回完整 SHA；只能 `READY_FOR_REVIEW` 或 `BLOCKED`。
- 完成回原 Reviewer `019f844f-5219-7221-a1ac-b4b72a976ba2` 最終 re-review；不得自審 GO、merge、push、deploy、publish或恢復內容線。
- 本鏈若 Repair 2 最終仍 NO_GO，依上限封鎖 V3 chain，不得 Repair 3。
