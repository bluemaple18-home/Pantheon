# CARD-SEO-GEO-FIX-005｜AI Visibility Monitor 設計

## 任務目的

設計 P3 AI visibility monitor，用固定 prompt 追蹤 ChatGPT / Gemini / Perplexity 對 Pantheon 與 Click108 的提及、引用與語氣差異。

## 請讀

- `artifacts/fortune_council/seo_geo_repo_intake/source_manifest.md`
- `docs/competitor_seo_tool.md`
- `output/competitor_seo/news.click108.com.tw/comparison.md`

## 任務範圍

- 先做 plan-only / dry-run，不接商業 API key。
- 定義 prompt set：塔羅、MBTI、命盤、人生方向、人際關係。
- 定義輸出 schema：model、prompt、mentioned_brands、ranking_position、cited_urls、tone、missing_entities。
- 定義人工驗收方式與後續自動化邊界。
- 不宣稱已測 Google AI Overview，除非有可重現瀏覽器證據。

## 接受標準

- 產出 `ai_visibility_prompt_set.md`。
- 產出 `ai_visibility_result_schema.md`。
- 產出 `ai_visibility_runbook.md`。
- 明確標出哪些需要 API key、哪些可人工抽樣。

## 證據路徑

`artifacts/fortune_council/seo_geo_fix_execution/evidence/ai_visibility/`
