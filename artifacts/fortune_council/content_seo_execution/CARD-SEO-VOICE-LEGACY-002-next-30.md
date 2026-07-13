# CARD-SEO-VOICE-LEGACY-002｜舊文章語氣重寫：下一批 30 篇

任務ID / 卡片類型｜`CARD-SEO-VOICE-LEGACY-002` / 內容改寫
派工對象｜`gpt-5.5`，推理 `medium`；主線負責整合、退件與最終驗收
請讀｜`docs/pantheon_article_publication_standard.md`、`artifacts/fortune_council/content_seo_execution/evidence/click108_voice_research_v2.md`、`app/web/static/article-bodies-next-30.js`、`artifacts/fortune_council/content_seo_execution/evidence/legacy_voice_second_batch/voice_rewrite_checks.md`
任務目的｜依最新版 v2 規範逐篇重寫 30 篇舊文章正文，延續情境先行、具體動詞、可觀察判斷與自然收尾；保留 slug、title、meta、FAQ、Schema、內鏈與版面
驗收證據｜`artifacts/fortune_council/content_seo_execution/evidence/legacy_voice_next_30/`；需附逐篇內容 diff、固定句型掃描、場景/動詞/限制檢查、文章長度/段落檢查與受影響測試結果

## 執行邊界

- 只修改 `app/web/static/article-bodies-next-30.js` 與必要的文字測試/證據檔。
- 不修改版面、DOM、CSS、路由、slug、H1、meta、FAQ、Schema、內鏈規則或關鍵字策略。
- 每篇至少有兩個專屬生活場景、兩個可觀察動詞、一個限制或反例，以及一個可執行收尾。
- 不把人格、塔羅、命盤或星座寫成診斷、品格判決、保證式預測或個人命運結論。
- 不複製第二批 20 篇的完整句子；同批固定完整句型不得超過三次。
- 先產出 30 篇逐篇 diff 與驗收證據，不宣稱全站完成。
