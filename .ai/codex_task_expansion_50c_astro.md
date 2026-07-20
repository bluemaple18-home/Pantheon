# 任務卡：CARD-EXPANSION-50C-ASTRO

任務ID / 卡片類型｜派工對象：`CARD-EXPANSION-50C-ASTRO` / implementation｜gpt-5.5 medium

請讀：`app/web/static/article-expansion-50.js` 的 record/body export 契約與 `app/web/static/article-registry.js` 的 HUMANIZER_POLICY。

任務目的：新增 17 篇星座／星盤文章，serial 固定為 `astrology-0011` 至 `astrology-0027`。前 12 篇依序為牡羊、金牛、雙子、巨蟹、獅子、處女、天秤、天蠍、射手、摩羯、水瓶、雙魚；後 5 篇為星盤相位、合相、對分相、三分相、四分相。每篇要有唯一 ID、semantic slug、標題、metadata、3 FAQ、published/updated=`2026-07-16`，以及 4 節、至少 650 個中文字的專屬正文。

可改檔案：repo 內完全唯讀；只能在派工訊息指定的 `<isolated-draft-root>` 寫入 `article-expansion-50c-astro.js` 與 `astro.json`。不可修改 registry、meta、tests、HTML、Python、其他內容模組，不可 commit/push/deploy。

驗收條件：export 名稱必須是 `EXPANSION_50C_ASTRO_ARTICLE_RECORDS`、`EXPANSION_50C_ASTRO_ARTICLE_BODY_LIBRARY`；records=17、bodies=17、serial/slug/title 唯一、每篇 4 節、正文 >=650 字、至少兩個專屬情境、明確說明單一太陽星座或相位不能代表完整人格／事件，長句重複超過 3 次為 0，禁詞 `全面解析/深度解析/總而言之/值得注意的是/不可或缺/賦能/必看/一定/保證/注定/入口` 為 0。跑 `node --check`，寫 evidence JSON；不得修改 repo。

證據路徑：`artifacts/fortune_council/content_seo_execution/evidence/article_expansion_50c/astro.json`
