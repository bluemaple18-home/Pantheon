---
card_id: CARD-CONTENT-GEMINI-V4-PUBLISH-MAIN-INTEGRATION-REVIEW-001
chain_id: CONTENT-GEMINI-V4-PUBLISH-MAIN-INTEGRATION-REVIEW-001
status: READY
role: independent_integration_reviewer
ownership: review_only
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
publish_base_sha: 78d8d2fc91bd435adf371762b9ff49665cdc26d5
v4_reviewed_tip_sha: b2c51d4ee9da7a45a05be8c59725a28020d9bb60
integration_merge_sha: 99318a01d77804b90490ae87bc5485e0ddb85960
candidate_sha: b0d0f6dd855bb185c9958c7a9cf6bd0ad178a8cc
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_publish_main_integration_review_001/
---

# Gemini V4｜發布主線整合獨立 Review

## Review question

Candidate `b0d0f6dd855bb185c9958c7a9cf6bd0ad178a8cc` 是否正確合併鎖定的
發布主線 v0.3.7 與 V4 reviewed lineage，並保持文章／automation 零漂移、legacy
default、V4 opt-in與no-fallback契約？

## Required review

1. 完整讀 AGENTS.md、本卡、Integration卡與evidence、V4 rollout/review evidence、
   發布base的publisher／automation與關聯 tests。
2. 核對 candidate ancestry、card／merge parent、固定base與V4 tip。
3. 獨立證明相對發布base，`app/**`、publisher、SEO pipeline、launchd與所有文章
   輸出沒有V4 merge造成的變更。
4. 重跑 V4 74、legacy 57、coordinator 6、publisher 5 tests。
5. 驗 flag-off legacy、flag-on no-fallback、exactly-once output binding。
6. 跑 `py_compile`、privacy、allowlist、`[DBG-`與`git diff --check`。
7. Findings-first；任何P0–P3須附path／line／觸發／風險／建議，不得自行修。

## Reviewer write allowlist

- `artifacts/fortune_council/content_pipeline_repair_execution/CARD-CONTENT-GEMINI-V4-PUBLISH-MAIN-INTEGRATION-REVIEW-001.md`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_publish_main_integration_review_001/**`

## Forbidden

- 修改candidate、production code/tests/docs、Integration或既有V4 evidence
- 外部Gemini／agy invocation
- merge、push、deploy、publish、activation、default promotion或legacy removal
- 修改文章、registry、metadata、queue、automation、sitemap、feed與prerender

## Required evidence

- `review.md`
- `verification.txt`
- `changed-files.txt`
- `decision.md`

## Verdict

只能回報：

- `DELIVERED_CANDIDATE / GO / READY_FOR_FINAL_SYNC`
- `DELIVERED_CANDIDATE / NO_GO`
- `BLOCKED`

GO只代表固定-base整合candidate可進入publisher coordination與final sync；不授權
遠端合併、push、deploy、publish、activation或預設切換。
