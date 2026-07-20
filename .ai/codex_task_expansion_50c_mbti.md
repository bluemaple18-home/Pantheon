# 任務卡：CARD-EXPANSION-50C-MBTI

任務ID / 卡片類型｜派工對象：`CARD-EXPANSION-50C-MBTI` / implementation｜gpt-5.5 medium

請讀：`app/web/static/article-expansion-50.js` 的 record/body export 契約與 `app/web/static/article-registry.js` 的 HUMANIZER_POLICY。

任務目的：新增 16 篇 Pantheon 64 分支人格文章，serial 固定為 `personality-0021` 至 `personality-0036`。依序為 INTJ、INFP、INFJ、ENFP 各四分支：AH、AC、OH、OC。每篇要有唯一 ID、semantic slug、標題、primary/secondary keywords、description、answer、tags、3 FAQ、published/updated=`2026-07-16`，以及 4 節、至少 650 個中文字的專屬正文。

可改檔案：repo 內完全唯讀；只能在派工訊息指定的 `<isolated-draft-root>` 寫入 `article-expansion-50c-mbti.js` 與 `mbti.json`。不可修改 registry、meta、tests、HTML、Python、其他內容模組，不可 commit/push/deploy。

驗收條件：export 名稱必須是 `EXPANSION_50C_MBTI_ARTICLE_RECORDS`、`EXPANSION_50C_MBTI_ARTICLE_BODY_LIBRARY`；records=16、bodies=16、serial/slug/title 唯一、每篇 4 節、正文 >=650 字、每篇至少兩個專屬生活場景、邊界句包含「不／不能／無法」、完整長句重複超過 3 次為 0，禁詞 `全面解析/深度解析/總而言之/值得注意的是/不可或缺/賦能/必看/一定/保證/注定/入口` 為 0。跑 `node --check`，把結構化結果寫入指定 evidence JSON；不得修改 repo。

證據路徑：`artifacts/fortune_council/content_seo_execution/evidence/article_expansion_50c/mbti.json`
