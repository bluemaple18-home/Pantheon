# CARD-CONTENT-REWRITE-006｜文章重寫總驗收

## 任務ID / 卡片類型｜派工對象

`CARD-CONTENT-REWRITE-006` / review + release gate｜gpt-5.5；strict finding 才升 gpt-5.6-sol

## 依賴

`CARD-CONTENT-REWRITE-001` 至 `CARD-CONTENT-REWRITE-005` 全部完成，且各卡 blocker 已清零。

## 驗收範圍

- 逐篇比對正文 diff，不只看 metadata。
- 檢查文章是否自然，不是把模板標籤露給讀者。
- 檢查重複句、抽象句、泛用開場與過度限制句。
- 檢查 H1、前 80 字、answer、FAQ、更新日期、canonical、Article／FAQPage／BreadcrumbList。
- 檢查既有版面、手機／桌機內容呈現與內鏈數量。

## PASS 條件

- 沒有 blocker。
- 每篇已標示文章類型與對應模板。
- 每篇有可追溯 QA 結果與證據路徑。
- `pytest tests/test_web.py`、必要的內容 gate 與 `git diff --check` 通過。
- 主線讀過所有卡片 diff，確認沒有混入版面或 URL 變更。

## 退件條件

- 只改最後一節，沒有重寫完整正文。
- 文章仍有「搜尋者通常不是……」或站方管理語。
- 每篇都硬塞工具解釋、小提醒與獨立限制節。
- 出現保證式結果、診斷、醫療、法律或投資建議。
- 需要修改版面或公開 URL 才能通過。

## 證據

`artifacts/fortune_council/content_rewrite_execution/evidence/review/`
