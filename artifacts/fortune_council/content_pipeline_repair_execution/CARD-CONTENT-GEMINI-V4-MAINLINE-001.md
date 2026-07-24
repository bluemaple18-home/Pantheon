---
card_id: CARD-CONTENT-GEMINI-V4-MAINLINE-001
chain_id: CONTENT-GEMINI-V4-MAINLINE-001
status: BLOCKED
review_status: REVIEW_GO
gate_5_mainline_acceptance: ACCEPTED
accepted_candidate_sha: 8c1b935917364c820dec19304ecf6e0ac50cde5a
accepted_review_commit: 1c81e8f85229098f3c0a5a6f033eb5a126e8d015
integration_status: INTEGRATED_LOCAL_MAIN
integrated_code_commit_sha: 5cf113c7d1ce3d9f35708519e998dc377c468896
role: v4_implementation_owner
ownership: v4_broker_only
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: exactly-once、durable ledger replay、外部 CLI process 與 fail-closed 跨模組契約具有高回退成本
source_of_truth: current_source_branch_production_code
allowlist:
  - artifacts/fortune_council/content_pipeline_repair_execution/CARD-CONTENT-GEMINI-V4-MAINLINE-001.md
  - docs/pantheon_gemini_reviewer_v4_architecture.md
  - docs/pantheon_gemini_v4_agy_cli_compatibility.md
  - scripts/agy_gemini_v4_broker.py
  - scripts/agy_gemini_runner.py
  - scripts/agy_gemini_v4_architecture_probe.py
  - tests/test_agy_gemini_outbox.py
  - tests/test_agy_gemini_v4_architecture_probe.py
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_mainline_001/**
forbidden_scope:
  - scripts/agy_seo_copy_pipeline.py
  - app/**
  - CHANGELOG.md
  - pyproject.toml
  - package.json
  - daily article automation, content queue and article registry
  - article content, sitemap, feed and prerender
  - merge, push, deploy and publish
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_mainline_001/
thread_status: VERIFIED
worktree_status: VERIFIED
decision: BLOCKED
rollout_decision: DO_NOT_PROMOTE_DEFAULT
delivery_statuses:
  - DELIVERED_CANDIDATE
  - BLOCKED
decision_statuses:
  - READY_FOR_REVIEW
  - BLOCKED
---

# Gemini V4 Broker 獨立技術主線

## Root question

能否以目前 source branch 的 production code 為唯一基準，收斂舊 V4 evidence、確認真實 `agy 1.1.5` CLI 相容性，並形成可重現、可獨立 review 的 exactly-once canary 候選與放量／不放量決策？

產文線固定 legacy CLI。V4 未通過不得阻擋文章發布，也不得成為預設 transport。

## 不可變契約

- `AGY_GEMINI_V4_BROKER=1` 是唯一 opt-in switch。
- flag off 必須走 legacy；flag on 後禁止 legacy fallback。
- 真實 `agy 1.1.5` 非互動介面使用 `--print <prompt>`；不得假設 prompt 只能走 stdin。
- production entrypoint 維持 `scripts.agy_gemini_v4_broker:run_single_shot`。
- exactly-once 只能由 durable ledger／anchor／replay 證據判定，不能以成功文案代替。
- 不得修改登入、憑證或全域 CLI 設定。
- evidence 不得保存 prompt、credential、完整環境或可識別本機私密路徑。
- 同一 blocker 第三次失敗立即停止，不做第四次。

## 執行順序

1. 盤點 current production truth，建立 `root-cause.md`，區分舊 evidence 的可採信部分、過期假設與唯一剩餘 blocker。
2. 先重現 focused tests；先補 RED 測試，再做最小 production 修正，禁止重寫 broker。
3. 跑 flag-off legacy 回歸與 flag-on synthetic matrix，至少涵蓋 success、nonzero exit、timeout、malformed output、pre-fork abort、partial ledger、replay、digest mismatch、concurrent duplicate。
4. synthetic 全過後，才允許一次真實 `agy` canary；外部呼叫不得發布內容，不得 retry 或 fallback。
5. 產出 `root-cause.md`、`red-green.txt`、`synthetic-matrix.json`、遮蔽後的 `real-canary.json`、`verification.txt`、`decision.md`、`changed-files.txt`。
6. 跑 focused tests、完整受影響測試與 `git diff --check`。
7. 建立一個乾淨 candidate commit，回報完整 SHA、changed files、測試數、canary 結果與尚存風險。

## 外部工具 Gate

- Tool/service：既有本機 Antigravity `agy 1.1.5` CLI。
- Operation level：一次合成公開 request 的外部 generation；不安裝、不登入、不修改 credential/config。
- Schema：只接受 closed JSON schema；prompt 使用公開、已清理、非文章內容的固定 canary payload。
- Confirmation：本卡初始授權已明確允許 synthetic 全綠後的一次真實 canary。
- Stop rule：任何 nonzero、timeout、malformed output、ledger/replay/binding 失敗立即停止；不得第二次外部呼叫。
- Evidence：只保存 hash、byte count、event types、replay status、process count、outcome 與遮蔽後 schema 結果。

## Gate 與交付

- Gate 1：正式 thread、獨立 worktree、實體卡、allowlist／forbidden scope 與 evidence root 均可讀。
- Gate 2：focused RED 可重現，最小 production 修正後 GREEN。
- Gate 3：flag-off regression 與完整 synthetic matrix 全綠。
- Gate 4：單次真實 canary 有 durable `COMPLETE/1`、唯一 target process、strict schema 與 receipt binding 證據。
- Gate 5：受影響測試、privacy/allowlist 檢查、`git diff --check`、candidate commit 全部可重現。

交付狀態只能是 `DELIVERED_CANDIDATE` 或 `BLOCKED`；decision 只能是 `READY_FOR_REVIEW` 或 `BLOCKED`。本線不得自行宣稱完成、GO、已整合或已上線。

## Main integration

- Accepted candidate：`8c1b935917364c820dec19304ecf6e0ac50cde5a`
- Canonical Review：`GO`，commit `1c81e8f85229098f3c0a5a6f033eb5a126e8d015`
- Local main code merge：`5cf113c7d1ce3d9f35708519e998dc377c468896`
- Integration status：`INTEGRATED_LOCAL_MAIN`
- Default behavior：flag off，仍走 legacy transport。
- Rollout：`DO_NOT_PROMOTE_DEFAULT`

此 integration 不代表已 push、deploy、publish或啟用 V4。文章 automation、content queue、registry、文章內容、sitemap、feed與prerender均未由本 chain 修改。

## JSON_INVALID continuation

- source evidence:
  `CARD-CONTENT-GEMINI-V4-LIMITED-ACTIVATION-004`
- durable result:
  `COMPLETE / 1 / PROCESS_TERMINAL SUCCESS / JSON_INVALID`
- current blocker:
  真實長文章 stdout 未通過嚴格 JSON parse，且既有 privacy boundary 不保存 raw
  response，因此目前無法區分 empty、invalid UTF-8、Markdown fence／前後包裝、
  截斷或一般 syntax error。
- scope:
  只新增 bounded、value-free、closed JSON format diagnostic 與 runner 二次 sanitizer；
  不猜測或自動修復輸出，不放寬 caller schema，不修改 ledger／anchor／replay。
- feedback loop:
  先在既有 `tests/test_agy_gemini_outbox.py` 補 RED，證明所有分類不保留 raw
  bytes、片段、offset、parser message 或未知字串；再做最小 production 修正。
- external call:
  本 continuation 不授權 Gemini／agy canary。任何新外呼仍須重新揭露 final payload
  並取得明確確認。
- rollout:
  `DO_NOT_PROMOTE_DEFAULT`
