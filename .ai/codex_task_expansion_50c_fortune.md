# 任務卡：CARD-EXPANSION-50C-FORTUNE

任務ID / 卡片類型｜派工對象：`CARD-EXPANSION-50C-FORTUNE` / implementation｜gpt-5.5 medium

請讀：`app/web/static/article-expansion-50.js` 的 record/body export 契約與 `app/web/static/article-registry.js` 的 HUMANIZER_POLICY。

任務目的：新增 17 篇紫微／八字文章，serial 固定為 `fortune-0010` 至 `fortune-0026`。前 5 篇補十二宮：兄弟宮、子女宮、遷移宮、疾厄宮、交友宮；接著 7 篇主星：紫微、天機、太陽、武曲、天同、廉貞、天府；最後 5 篇八字基礎：日主、五行、十神、大運、流年。每篇要有唯一 ID、semantic slug、metadata、3 FAQ、published/updated=`2026-07-16`，以及 4 節、至少 650 個中文字的專屬正文。

可改檔案：repo 內完全唯讀；只能在派工訊息指定的 `<isolated-draft-root>` 寫入 `article-expansion-50c-fortune.js` 與 `fortune.json`。不可修改 registry、meta、tests、HTML、Python、其他內容模組，不可 commit/push/deploy。

驗收條件：export 名稱必須是 `EXPANSION_50C_FORTUNE_ARTICLE_RECORDS`、`EXPANSION_50C_FORTUNE_ARTICLE_BODY_LIBRARY`；records=17、bodies=17、serial/slug/title 唯一、每篇 4 節、正文 >=650 字、至少兩個生活情境、不得把宮位／主星／八字單點寫成命運，長句重複超過 3 次為 0，禁詞 `全面解析/深度解析/總而言之/值得注意的是/不可或缺/賦能/必看/一定/保證/注定/入口` 為 0。跑 `node --check`，寫 evidence JSON；不得修改 repo。

證據路徑：`artifacts/fortune_council/content_seo_execution/evidence/article_expansion_50c/fortune.json`
