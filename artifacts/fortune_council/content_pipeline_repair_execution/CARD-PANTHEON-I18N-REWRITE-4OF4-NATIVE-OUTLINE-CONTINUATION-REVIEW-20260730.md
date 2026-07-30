---
card_id: CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-REVIEW-20260730
chain_id: pantheon-i18n-rewrite-4of4-runtime-stability-p0-20260730
parent_card_id: CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-IMPLEMENTATION-20260730
role: independent-review
cycle: 2
review_cycle: 1
repair_budget: 1
status: CARD_DRAFTED
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
project_id: local-0020d4379451d545eb08362962f1def0
repo_identity: github.com/bluemaple18-home/Pantheon
reviewed_candidate: f0b70b4bba41a952f9b8bc2c12d3a2bc5c13502e
required_direct_parent: 8bb80b888561b1a06afa9550f535f6e865724871
implementation_thread_id: 019fb1a9-ea89-7231-beea-75d2fea93430
mainline_thread_id: 019fb165-8174-7192-b19f-4ed19ed19426
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-REVIEW-20260730/
created_at: 2026-07-30 Asia/Taipei
---

# Pantheon i18n-rewrite Native Outline Continuation Independent Review

## Role and stop boundary

你是本 chain 的唯一獨立 Reviewer。只審查 candidate
`f0b70b4bba41a952f9b8bc2c12d3a2bc5c13502e`；不得修改 production code、
tests 或 Implementation evidence，不得呼叫 provider、讀寫 production `.work`、
push、deploy、publish、安裝服務或建立其他 task。

只允許新增本卡專屬 Review evidence，形成單一 evidence commit。只有 P0／P1
finding 可以 `REVIEW_NO_GO`；P2／P3 必須記錄但不得阻擋。無 finding 則
`REVIEW_GO`。

## Root question

此 candidate 是否真的讓既有 deferred i18n-rewrite run 在不覆寫舊 lineage、
不誤耗 semantic budget、也不引入 production side effect 的前提下：

1. 先建立 topic-neutral、schema-valid 的 locale-specific plan；
2. 再依 source fact package 與已驗證 plan 生成母語文章；
3. repeated finding 時強制重建真正不同的 outline topology；
4. 使用 deterministic、bounded、idempotent continuation 更新 root
   candidate／review／state？

## Reviewed candidate facts

- Candidate：`f0b70b4bba41a952f9b8bc2c12d3a2bc5c13502e`
- Direct parent：`8bb80b888561b1a06afa9550f535f6e865724871`
- Implementation reported：focused `13 passed`；required suite
  `460 passed, 1 warning`；`git diff --check` PASS。
- Changed files：
  - `scripts/agy_multilingual_pipeline.py`
  - `tests/test_agy_multilingual_pipeline.py`
  - `tests/test_agy_gemini_outbox.py`
  - Implementation evidence／handoff only
- Candidate reports no provider、production `.work`、push、deploy或publish action。

## Required review

### R-001 — Topic and prompt authority

- 確認 `LOCALE_EDITORIAL_CONTRACTS` 不再內建 Tarot topic、audience、keyword或
  fixed outline。
- 確認 plan prompt 可以看到 topic cues／source facts，但 article prompt不能把
  source H2、段落數、paragraph order當作 outline。
- 確認 locale plan schema與 hydration會拒絕缺欄、額外欄、locale／source hash
  mismatch、無效 coverage mapping與非 native/empty plan。
- 確認 prompt／receipt 不意外洩漏或重新引入來源結構 authority。

### R-002 — Two-phase idempotency and semantic budget

- Plan與article必須有不同 operation identity、receipt與 external artifact path。
- Pending、transport failure、malformed/schema-invalid payload不得建立 candidate、
  前進 generation、覆寫 root candidate/review或消耗下一次 semantic generation。
- 相同 logical continuation重跑不得重複 enqueue或漂移 request identity。
- `max_repairs` 邊界、generation計數與 terminal condition不得 off-by-one。

### R-003 — Repeated finding and topology rebuild

- repeated finding判定必須綁定相同 article／連續 generation／指定 finding code，
  不得因不同 article或非連續歷史誤觸發。
- rebuild必須禁止相同 heading order與相同 fact-to-section topology；不能僅換
  同義 heading。
- targeted repair不得把 prior完整文章當主要 rewrite authority。
- 第一個 continuation generation必須正確沿用既有 root REJECT findings與
  rejected candidate topology。

### R-004 — Deferred lineage and crash consistency

- `attempts/01..03` 必須 immutable；new generation從 deterministic下一編號開始，
  重跑不能覆寫或跳號。
- run ID、brief、source hashes、starting review identity與 continuation state
  必須 fail closed；不同 run/brief/review不得接管既有 state。
- root candidate／review／state 的 write-ahead recovery必須保持一致；檢查任一
  atomic write或 unlink中斷時，重跑能安全收斂，不會留下 candidate/review混代。
- `complete` continuation重跑不得再呼叫 client或重新 enqueue。
- 不得建立 approval、apply、publish、ledger、registry、sitemap、feed或redirect
  side effect。

### R-005 — Compatibility and scope

- 審查既有 fresh run（無 root candidate/review）是否維持相容，沒有把 continuation
  狀態錯套到一般 run。
- 檢查 production caller／outbox routing是否真的能進入 continuation，且不需手改
  artifacts；若只有未接線 helper，視影響分級。
- 確認 changed files完全落在 allowlist，沒有 hidden generated或environment file。

## Fresh verification

至少執行：

```text
.venv/bin/python -m pytest \
  tests/test_agy_multilingual_pipeline.py \
  tests/test_agy_gemini_outbox.py \
  tests/test_agy_seo_copy_pipeline.py \
  tests/test_agy_content_publisher.py \
  tests/test_agy_gemini_coordinator.py \
  tests/test_agy_gemini_v4_broker.py \
  tests/test_agy_gemini_reviewer_cutover.py -q
git diff --check f0b70b4bba41a952f9b8bc2c12d3a2bc5c13502e^ \
  f0b70b4bba41a952f9b8bc2c12d3a2bc5c13502e
```

另需做 bounded source review與必要 adversarial tests，尤其是：

- cross-article／non-consecutive repeated findings；
- pending plan/article replay；
- complete state replay；
- crash recovery各中斷點；
- continuation production entrypoint可達性。

## Finding format

每筆 finding 必須包含：

- ID：`P0C-REV-###`
- severity：P0／P1／P2／P3
- file與精確 line
- concrete failure path
- violated requirement
- minimal repair direction

## Delivery

輸出：

- `REVIEW_GO` 或 `REVIEW_NO_GO`
- reviewed candidate與direct parent
- findings（若無則明寫 none）
- fresh tests與`git diff --check`
- residual risks
- 唯一 Review evidence commit SHA

完成後停止，回主線；不得自行修復。
