---
id: CARD-PANTHEON-JA-KO-TRANSLATION-QUALITY-PASS-RATE-REPAIR-20260803
status: READY_FOR_REVIEW
type: implementation-decision
---

# Decision

## 狀態

`DELIVERED_CANDIDATE / READY_FOR_REVIEW`

本 implementation thread 已完成 diagnostic、RED→GREEN 與本機 regression；未執行 provider 外呼、production mutation、push、deploy、publish、排程或 canary。候選仍需主線獨立 Review GO 與容量 watchdog PASS。

## Root question / blocker / fork

- root question: 在不降低 fact、安全、H2、語言與 Reviewer gate 的前提下，修復日韓 locale-plan false-negative，並降低 `SOURCE_SYNTAX_TRANSFER`／`NON_NATIVE_SEARCH_INTENT` 的生成原因。
- blocker: production 四格 canary 與首批 `20×2` 觀察受本卡禁止範圍限制，且必須等待獨立 Review 與容量閘門。
- fork: 無；排程公平與 locale quota 不在本卡範圍。

## Data contract

```text
data_contract:
  source_and_grain: one row per terminal translation run; newest 20 ja, 20 ko, 10 en by updated_at
  confirmed_schema_and_status_semantics: state status is terminal complete/failed; primary stage is exactly one of plan/candidate/reviewer/publisher
  joins_and_cardinality: run_id joins state, translation run dir, parent new/rewrite ledger and Publisher ledger; one source_class and one primary stage per sample
  aggregation_invariants: total=50; ja=20; ko=20; en=10; unknown_or_generic=0
execution_boundary:
  database_pushdown: not applicable; bounded read-only filesystem snapshot
  controlled_artifacts: failure-taxonomy.json and saved-response-replay.json contain digests and classifications, not full articles or credentials
degradation:
  unavailable_data: none for the selected terminal sample
  provisional_thresholds: SC-003 30% production improvement is not evaluated here
  model_limits: prompt fix is proven by fixtures and Reviewer-code preservation, not by a live provider claim
validation:
  fixture_or_unit: 181 multilingual tests passed
  representative_real_data: 50 terminal production run metadata rows and 32 saved plan responses replayed offline
  old_vs_new_reconciliation: English plan/article prompt digests unchanged
  business_invariants: missing/duplicate fact, wrong safety, illegal H2 and wrong-language cases remain rejected
warnings_and_exclusions: Publisher canary, release evidence and 20x2 effectiveness observation intentionally not run
remaining_risk: ja/ko prompt effectiveness requires bounded post-review canary and observation
```

## Acceptance mapping

- `SC-001`: PASS — 50 筆 mutually-exclusive taxonomy，unknown／generic 為 0。
- `SC-002`: PASS for implementation scope — 1 個已證明 false-negative 保存 response 轉綠；負例與 Reviewer hard reject 維持。
- `SC-003`: PENDING PRODUCTION — 未執行 `20×2`，不得推論降幅。
- `SC-004`: PASS — multilingual、coordinator、publisher regression 與英文 byte control 全數通過。
- `SC-005`: PENDING PRODUCTION — 四格正式 release evidence 未執行。

## 下一步與等待條件

1. 主線對 candidate commit 做獨立 Review，特別檢查 proper-name authority 是否過寬，以及 ja/ko repair contract 是否只影響目標 locale。
2. Review GO 後先跑容量 watchdog；未 PASS 不得啟動 canary。
3. 另行授權後才依序執行 `ja/i18n-new`、`ko/i18n-new`、`ja/i18n-rewrite`、`ko/i18n-rewrite`，再觀察首批 `20×2`。
