---
card_id: CARD-CONTENT-GEMINI-V4-PUBLISH-MAIN-INTEGRATION-001
chain_id: CONTENT-GEMINI-V4-PUBLISH-MAIN-INTEGRATION-001
status: ACTIVE
role: integration_owner
ownership: publish_main_v4_integration_only
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
publish_base_sha: 78d8d2fc91bd435adf371762b9ff49665cdc26d5
publish_base_tag: v0.3.7
v4_reviewed_tip_sha: b2c51d4ee9da7a45a05be8c59725a28020d9bb60
v4_rollout_candidate_sha: 2e221546b9de8dba3498201f78b86831bacffe44
v4_rollout_review_verdict: GO_READY_FOR_LIMITED_ROLLOUT
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_publish_main_integration_001/
---

# Gemini V4｜發布主線整合

## Root question

能否將鎖定的發布主線 `v0.3.7` 與已獨立 Review GO 的 V4 lineage 合成一個本機
candidate，同時保持既有文章、automation與發布輸出相對發布 base零漂移，並證明
legacy default與V4 opt-in契約都未回歸？

## Fixed identity

- 發布 base：`78d8d2fc91bd435adf371762b9ff49665cdc26d5`
- V4 reviewed tip：`b2c51d4ee9da7a45a05be8c59725a28020d9bb60`
- Candidate 必須同時包含兩者為 ancestor。
- `origin/main`可能繼續新增文章 commits；本卡不追逐移動ref。最終同步另設 Gate。

## Integration contract

1. 以發布 base為first-parent lineage；本卡 provisioning commit只能是發布 base的
   單一child，隨後以該card commit為merge first parent、固定V4 reviewed tip為
   second parent。
2. 發布 base既有 article、registry、metadata、sitemap、feed、prerender與automation
   必須 byte-for-byte 保持不變；本卡不得人工改寫。
3. V4 production code、tests、docs與evidence必須精確承接 reviewed lineage，不得
   未驗證重作或挑選 patch。
4. `AGY_GEMINI_V4_BROKER=1`仍是唯一 opt-in。
5. Flag off維持 legacy；flag on失敗不得 fallback。
6. 不切預設transport，不執行content queue，不跑文章generation，不發布。

## Direct-write allowlist

- `artifacts/fortune_council/content_pipeline_repair_execution/CARD-CONTENT-GEMINI-V4-PUBLISH-MAIN-INTEGRATION-001.md`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_publish_main_integration_001/**`
- 合併衝突時僅可修改：
  - `scripts/agy_gemini_v4_broker.py`
  - `scripts/agy_gemini_runner.py`
  - `tests/test_agy_gemini_outbox.py`
  - `docs/pantheon_gemini_reviewer_v4_architecture.md`
  - `docs/pantheon_gemini_v4_agy_cli_compatibility.md`
  - V4 cards/evidence metadata

## Forbidden

- 人工修改 article內容、registry、metadata、sitemap、feed、prerender或automation
- `scripts/agy_seo_copy_pipeline.py`
- login、credential、全域CLI/env/launchd設定
- 外部 Gemini／agy invocation
- push、deploy、publish、tag或預設transport切換
- 刪除legacy transport

## Verification

1. 保存兩個 parent identity、merge-base、changed paths與conflict結果。
2. 證明 candidate同時包含 publish base與V4 reviewed tip。
3. 相對 publish base，文章／automation相關 paths只允許 publish base既有內容；
   V4 merge不得新增變更。
4. V4 focused：74 tests。
5. Legacy publishing：57 tests。
6. Coordinator：6 tests。
7. 自動發布 actor／publisher受影響 tests。
8. Flag-off legacy／flag-on no-fallback targeted tests。
9. `py_compile`、privacy、allowlist、`[DBG-`與`git diff --check`。

## Required evidence

- `preflight.md`
- `merge-report.md`
- `verification.txt`
- `changed-files.txt`
- `decision.md`

## Delivery

只能回報：

- `DELIVERED_CANDIDATE / READY_FOR_INTEGRATION_REVIEW`
- `BLOCKED`

本卡不得自行Review、push、deploy、publish、activation或預設切換。
