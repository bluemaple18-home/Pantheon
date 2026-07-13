# CARD-SEO-VOICE-LEGACY-002-REPAIR-001｜修復下一批 30 篇固定句型

任務ID / 卡片類型｜`CARD-SEO-VOICE-LEGACY-002-REPAIR-001` / Repair
派工對象｜`gpt-5.4`，推理 `medium`；只修已確認的語氣缺陷，主線保留 re-review 與整合
請讀｜`docs/pantheon_article_publication_standard.md`、`artifacts/fortune_council/content_seo_execution/evidence/click108_voice_research_v2.md`、`app/web/static/article-bodies-next-30.js`
任務目的｜從乾淨基線重新撰寫下一批 30 篇正文，移除候選版本批量複製的固定句型，維持情境先行、具體動詞、限制/反例與自然收尾
驗收證據｜`artifacts/fortune_council/content_seo_execution/evidence/legacy_voice_next_30_repair_001/`；需附逐篇 diff、同批完整句型頻率、段落重複掃描與受影響測試結果

## Review Findings

- `這比只問「……好不好」更能貼近現實` 在多篇文章中以固定位置重複。
- `尤其要回到……才不會只停在抽象形容` 形成每篇 3 至 5 次的共用收尾。
- `讀……這一節時，可以先把問題寫成一句生活描述` 跨 30 篇重複。
- 原候選版本的固定句型掃描沒有檢查同批新句型，因此不得沿用其驗收結果。

## 執行邊界

- 只修改 `app/web/static/article-bodies-next-30.js` 與必要的文字驗收證據。
- 不修改版面、DOM、CSS、路由、slug、H1、meta、FAQ、Schema、內鏈規則或關鍵字策略。
- 每篇至少有兩個專屬生活場景、兩個可觀察動詞、一個限制或反例，以及一個自然收尾。
- 同一完整句型在 30 篇合計不得超過 3 次；不得用同義替換批量複製同一段落功能。
- 不使用保證式預測、人格品格判決、心理診斷、醫療、法律或投資建議。
- 不推送、不部署；完成後交回主線 re-review。
