---
card_id: CARD-CONTENT-GEMINI-V4-MAIN-INTEGRATION-001
chain_id: CONTENT-GEMINI-V4-MAINLINE-001
status: INTEGRATED
role: mainline_integrator
ownership: local_main_integration_only
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: main 與 accepted V4 candidate 分歧且共享 outbox 測試檔，需保留 legacy publishing 與 V4 fail-closed 契約
main_before_sha: e2bb8da6d40b42729f9a6fb1e9c20abff564dd91
candidate_sha: 8c1b935917364c820dec19304ecf6e0ac50cde5a
candidate_review_commit: 1c81e8f85229098f3c0a5a6f033eb5a126e8d015
candidate_review_verdict: GO
acceptance_commit: 41231cd4eeb1c9dc389f3a7321107955c830d22c
integration_branch: codex/gemini-v4-main-integration-001
integration_method: no_ff_merge_after_conflict_review
known_overlap:
  - tests/test_agy_gemini_outbox.py
allowlist:
  - artifacts/fortune_council/content_pipeline_repair_execution/CARD-CONTENT-GEMINI-V4-MAIN-INTEGRATION-001.md
  - accepted candidate tree 8c1b935917364c820dec19304ecf6e0ac50cde5a
  - tests/test_agy_gemini_outbox.py conflict resolution only
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_mainline_001/gate-7-main-integration.json
forbidden_scope:
  - article content, registry, metadata, sitemap, feed and prerender modification
  - scripts/agy_seo_copy_pipeline.py modification
  - app/** modification
  - package or dependency modification
  - force merge, rebase and history rewrite
  - push, deploy, publish and default transport promotion
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_mainline_001/
integration_status: INTEGRATED_LOCAL_MAIN
rollout_decision: DO_NOT_PROMOTE_DEFAULT
---

# Gemini V4｜Main Integration

## Root question

能否把 accepted V4 candidate 合併到目前本機 `main`，同時保留 `main` 已上線的 legacy 發文、bounded rewrite 與 malformed transport retry 行為，且不啟用 V4 預設路徑？

## Preconditions

- Integration branch 必須從 `main=e2bb8da6d40b42729f9a6fb1e9c20abff564dd91` 建立。
- Candidate 精確為 `8c1b935917364c820dec19304ecf6e0ac50cde5a`，Reviewer verdict 為 `GO`。
- Main／candidate divergence 為 `11/3`。
- 唯一 overlap 為 `tests/test_agy_gemini_outbox.py`。
- Candidate 不得修改文章、registry、metadata、sitemap、feed、prerender或 `scripts/agy_seo_copy_pipeline.py`。

## Conflict contract

若 `tests/test_agy_gemini_outbox.py` 發生衝突：

- 保留 `main` 的 `test_pipeline_tick_reserves_one_bounded_final_content_repair` 預期值 `2`。
- 保留 `main` 的 malformed JSON retry tests。
- 保留 candidate 的 V4 concurrent-create anchor、malformed anchor與 flag-on no-fallback tests。
- 禁止用整檔 ours／theirs 覆蓋。
- 出現第二個 conflict path 或任何 article/publishing production conflict，立即 `BLOCKED`。

## Verification

- V4 focused suite。
- `tests/test_agy_gemini_outbox.py` 全檔。
- Legacy publishing tests：`tests/test_agy_seo_copy_pipeline.py`。
- Coordinator tests：`tests/test_agy_gemini_coordinator.py`。
- `git diff --check` 與 candidate/forbidden scope audit。
- 確認 `AGY_GEMINI_V4_BROKER` 未設時仍走 legacy；flag on failure 不 fallback。

## Boundary

本卡只授權本機 `main` integration。不得 push、deploy、publish、執行文章 automation、變更文章內容或將 V4 設為預設 transport。

## Result

- Main before：`e2bb8da6d40b42729f9a6fb1e9c20abff564dd91`
- Code merge commit：`5cf113c7d1ce3d9f35708519e998dc377c468896`
- Merge parents：integration card commit `a5185d1d30ebc50e9a0fec12019331ac4db506cd` 與 accepted candidate `8c1b935917364c820dec19304ecf6e0ac50cde5a`
- Overlap resolution：Git 自動合併；語意核對保留 legacy bounded repair=`2`、malformed JSON retry tests 與全部 V4 race/fail-closed tests。
- V4 focused：`73 passed`
- Legacy SEO publishing：`57 passed`
- Coordinator：`6 passed`
- Article／registry／metadata／sitemap／feed／prerender diff：無。
- Push／deploy／publish／default promotion：未執行。
