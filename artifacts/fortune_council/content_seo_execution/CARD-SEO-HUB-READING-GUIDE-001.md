# CARD-SEO-HUB-READING-GUIDE-001｜修正分類文章 hub 導讀

任務ID / 卡片類型｜`CARD-SEO-HUB-READING-GUIDE-001` / Content UX Repair
派工對象｜主線整合
任務目的｜移除分類 hub 把全部文章標題串成單一長段落的寫法，改成可掃讀的數量、閱讀目的與情境路徑
執行範圍｜`app/web/static/article-meta.js`、必要 cache query、prerender shell、測試與證據
不包含｜不改版面 CSS、DOM 結構、URL、文章正文、FAQ、Schema、分類連結規則
驗收證據｜`artifacts/fortune_council/content_seo_execution/evidence/hub_reading_guide_001.md`

## 成功標準

- 塔羅 hub 不再輸出 80 篇標題串成的單一段落。
- 導讀直接回答：只查牌義、卡在感情、想看工作或人生方向時先讀什麼。
- 桌機與手機保留既有 12 條分類文章連結，無水平溢位與前端錯誤。
