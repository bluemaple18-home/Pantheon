# Source map

## Source decision

首次 source decision 前呼叫 CodeGraph，指定目前 Pantheon worktree。CodeGraph
回報該 worktree 尚未初始化，未提供 symbol graph；為避免擴張工具或寫入額外
索引，依卡片契約降級為限域 `rg`，只讀：

- `scripts/agy_multilingual_pipeline.py`
- `tests/test_agy_multilingual_pipeline.py`
- final Review 的 `targeted_re_review_2_probes.py`

## Bounded seam

- `_ascii_is_name_acronym_or_number()`：唯一有缺陷的 ASCII exception seam。
- `_plan_matches_target_language()`：en／ja／ko 的 deterministic script authority。
- `validate_locale_plan()`：逐項呼叫 language matcher，涵蓋：
  - `native_search_intent`
  - 每一個 `native_query_phrasings`
  - `article_angle`
  - 每一個 `ordered_h2_outline`
  - 每一個 `coverage_note`
- `_hydrate_locale_plan()`：既有 direct tests 與 final Review probes 通過的入口。

不需變更 schema、provider、prompt、Reviewer、Outbox、continuation、publisher
或其他 production module。
