---
card_id: CARD-CONTENT-GEMINI-V4-ROLLOUT-SHADOW-002-REVIEW-001
chain_id: CONTENT-GEMINI-V4-ROLLOUT-002-REVIEW-001
status: DELIVERED_CANDIDATE
role: independent_limited_rollout_reviewer
ownership: review_only
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
review_verdict: GO
delivery_status: READY_FOR_LIMITED_ROLLOUT
external_invocations: 0
base_sha: 6706ae3a28eb601fdf4c8b97531173138f67ef37
candidate_sha: 2e221546b9de8dba3498201f78b86831bacffe44
candidate_parent_sha: 6706ae3a28eb601fdf4c8b97531173138f67ef37
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_rollout_shadow_002_review_001/
---

# Gemini V4｜Shadow-002 Limited Rollout Independent Review

## Review question

Shadow-002 candidate `2e221546b9de8dba3498201f78b86831bacffe44` 是否提供足夠、
可獨立重算且 privacy-safe 的 exactly-once real canary證據，使主線可以考慮下一階段
「仍預設關閉、明確 opt-in、受限範圍」的 limited rollout？

## Fixed identity

- Base／candidate唯一parent：`6706ae3a28eb601fdf4c8b97531173138f67ef37`
- Candidate：`2e221546b9de8dba3498201f78b86831bacffe44`
- Integrated output-binding Repair／Review main：
  `1dd80978dc4c6facbb588aa8869bec8362e606a3`
- Reviewer不得修改 candidate、recorder、verifier、bundle或production code。

## Required review

1. 完整讀 AGENTS.md、本卡、Shadow-002卡與全部 evidence、output-binding
   Repair／Review evidence、production broker／runner與相關 tests。
2. 獨立執行 verifier，禁止import production broker／runner或呼叫外部 CLI。
3. 從 parsed closed-schema result與 `canonical-json-newline-v1` label重建59-byte
   stdout，核對 SHA-256、byte count與control。
4. 獨立重算 ledger JSONL SHA、event hash chain、final anchor、receipt／command／
   operation／item／attempt／request／model／profile／executable digest。
5. 驗證 target invocation／process為1/1，retry／fallback／resend／second call為0。
6. 驗證real bundle不含 raw stdout、prompt、credential、本機路徑、完整環境或CLI log。
7. 重跑三種 encoding acceptance、13 mutations、V4 focused、legacy publishing、
   coordinator、`py_compile`與`git diff --check`。
8. Findings-first：任何 P0–P3 finding須附 path／line／觸發條件／風險／建議；
   Reviewer不得自行修。

## Limited rollout boundary

即使 GO，也只代表可以另開 rollout activation卡，且必須：

- `AGY_GEMINI_V4_BROKER=1`仍是唯一明確 opt-in；flag off維持legacy。
- flag on失敗不得 fallback。
- 不得直接切成預設 transport。
- 不得改 daily article automation、queue、registry或文章內容。
- 先使用公開 sanitized 非文章 payload或明確授權的極小批次。
- 每次 activation必須有固定範圍、停止條件、observability與回退契約。
- Provider internal model-call provenance維持 `UNKNOWN`，不得宣稱已證明。

## Reviewer write allowlist

- `artifacts/fortune_council/content_pipeline_repair_execution/CARD-CONTENT-GEMINI-V4-ROLLOUT-SHADOW-002-REVIEW-001.md`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_rollout_shadow_002_review_001/**`

## Forbidden

- 修改 candidate、production code/tests/docs或既有 evidence
- 外部 Gemini／agy invocation
- repair、merge、push、deploy、publish、default promotion或activation
- article、registry、metadata、queue、automation、sitemap、feed與prerender
- login、credential、全域 CLI／環境／launchd設定

## Required evidence

- `review.md`
- `verification.txt`
- `changed-files.txt`
- `decision.md`

## Verdict

只能回報：

- `DELIVERED_CANDIDATE / GO / READY_FOR_LIMITED_ROLLOUT`
- `DELIVERED_CANDIDATE / NO_GO / DO_NOT_ROLLOUT`
- `BLOCKED`

GO 不代表 activation、整合、預設切換、發布或上線；主線仍須另行開卡並取得必要授權。

## Review result

- Verdict：`DELIVERED_CANDIDATE / GO / READY_FOR_LIMITED_ROLLOUT`
- Findings：未發現 P0–P3 具體問題。
- Independent verifier：`PASS`
- Encoding acceptance：`3/3 accepted`
- Mutation controls：`13/13 rejected`
- Regression：`137 unique passed`（V4 74、legacy 57、coordinator 6）
- Target invocation／process：`1/1`
- Retry／fallback／automatic resend／second external call：`0/0/0/0`
- Review external Gemini／agy invocation：`0`
- Boundary：只允許主線另開 activation 卡考慮預設關閉、明確 opt-in、極小受限範圍；
  不授權預設切換、文章發布、merge、push、deploy或任何新的外部呼叫。
- Provider internal model-call provenance：`UNKNOWN`
