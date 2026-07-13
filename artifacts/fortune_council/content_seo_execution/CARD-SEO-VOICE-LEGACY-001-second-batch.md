# CARD-SEO-VOICE-LEGACY-001｜舊文章語氣重寫：第二批 20 篇

任務ID / 卡片類型｜`CARD-SEO-VOICE-LEGACY-001` / 內容改寫
派工對象｜`gpt-5.5`，推理 `medium`；主線負責整合、退件與最終驗收
請讀｜`docs/pantheon_article_publication_standard.md`、`artifacts/fortune_council/content_seo_execution/evidence/click108_voice_research_v2.md`、`app/web/static/article-bodies-second-batch.js`
任務目的｜逐篇重寫 20 篇舊文章正文，移除固定 AI 句型，改為情境先行、具體動詞、可觀察判斷與自然收尾；保留 slug、title、meta、FAQ、Schema、內鏈與版面
驗收證據｜`artifacts/fortune_council/content_seo_execution/evidence/legacy_voice_second_batch/`；需附逐篇內容 diff、固定句型掃描、文章長度/段落檢查與受影響測試結果

## 執行邊界

- 只修改 `app/web/static/article-bodies-second-batch.js` 與必要的文字測試/證據檔。
- 不修改版面、DOM、CSS、路由、slug、H1、meta、FAQ、Schema、內鏈規則或關鍵字策略。
- 每篇至少加入兩個專屬生活情境、兩個可觀察動詞、一個限制或反例，以及一個可執行收尾。
- 不使用保證式占卜、心理診斷、醫療、法律、投資或替讀者下個人結論的寫法。
- 先產出 20 篇逐篇 diff 與驗收證據，不直接宣稱全站完成。
