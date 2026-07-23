---
card_id: CARD-CONTENT-V4-DECOUPLING-001
chain_id: CONTENT-V4-DECOUPLING-001
status: VERIFIED
role: mainline_integrator
ownership: content_transport_policy
thickness: normal
risk: medium
allowlist:
  - docs/pantheon_content_transport_decoupling.md
  - docs/pantheon_gemini_outbox_runner.md
  - docs/pantheon_gemini_reviewer_transport_strategy.md
  - tests/test_agy_seo_copy_pipeline.py
  - artifacts/fortune_council/content_pipeline_repair_execution/CARD-CONTENT-V4-DECOUPLING-001.md
forbidden_scope:
  - scripts/agy_gemini_v4_broker.py
  - scripts/agy_gemini_runner.py
  - app/**
  - articles, registry, metadata and publishing files
verification:
  - focused transport tests pass
  - full affected test files pass
  - git diff --check
---

# 產文流程與 Gemini V4 Broker 解耦

## 目的

把受監督產文與 V4 transport 改善拆成兩條可獨立前進、獨立回退的工作線。

## 決策

- 受監督產文使用既有 `GeminiClient` CLI transport。
- V4 broker 維持 opt-in canary，不成為受監督產文的前置條件。
- V4 尚未通過真實 canary 前，禁止無人值守大量送出與自動發布。
- 產文仍須通過 deterministic gate、獨立 Reviewer 與人工 approval；解耦不降低內容 Gate。

## Commit 邊界

1. 決策與操作文件：撤除 V4 對受監督內容線的硬 Gate，明列兩條線的責任與切換條件。
2. 契約測試：鎖定 V4 flag 不得改變直接內容 pipeline 的 CLI transport。

## 非目標

- 不修改、回退或刪除 V4 broker。
- 不執行真實 Gemini canary。
- 不產文、不發布、不部署。
