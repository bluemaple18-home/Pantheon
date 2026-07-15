# CARD-CONTENT-REWRITE-004｜命盤與人格基礎文章重寫

## 任務ID / 卡片類型｜派工對象

`CARD-CONTENT-REWRITE-004` / content rewrite｜gpt-5.5

## 請讀

- `docs/pantheon_article_publication_standard.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/tool_hardening/click108_seo_audit.md`
- `app/web/static/article-registry.js`
- `app/web/static/article-bodies-second-batch.js`
- `app/web/static/article-bodies-next-30.js`
- `app/web/static/article-bodies-scale-44.js`

## 文章範圍

- MBTI、16 型人格與已收錄人格文章的基礎／單型頁。
- 命盤、八字、紫微、十二宮與已收錄命盤文章的基礎／單宮位頁。

## 任務目的

人格文章寫偏好與互動行為；命盤文章寫觀察層次與資料限制。兩者都不寫成診斷、永久標籤或單一宮位的完整人生結論。

## 驗收條件

- 基礎定義文至少一個生活場景；情境文至少兩個。
- 每個核心解釋都能對應到行為、條件或可觀察反應。
- MBTI 不寫診斷；命盤不把單一宮位／星曜當成完整判斷。
- 感情、工作、人際、財富段落只在題目需要時出現，不硬湊五大情境。
- 不保留「搜尋者不是想背定義」「公開文章的任務」等站方或模板語。

## 驗證與證據

執行文章 QA gate、`tests/test_web.py`、`git diff --check`；輸出逐篇 blocker / warning / pass。

證據：`artifacts/fortune_council/content_rewrite_execution/evidence/fortune_personality/`
