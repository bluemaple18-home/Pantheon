# CARD-CONTENT-REWRITE-005｜五大情境文章重寫

## 任務ID / 卡片類型｜派工對象

`CARD-CONTENT-REWRITE-005` / content rewrite｜gpt-5.5

## 依賴

- `CARD-CONTENT-REWRITE-001`
- `CARD-CONTENT-REWRITE-002`
- `CARD-CONTENT-REWRITE-003`
- `CARD-CONTENT-REWRITE-004`

## 文章範圍

- 感情：曖昧、復合、安全感、關係卡住。
- 事業：轉職、工作卡住、被看見、創業。
- 人際：界線、關係變淡、溝通與社交疲憊。
- 財富：金錢焦慮、收入、支出與資源節奏。
- 人生方向：迷惘、選擇、該動或該等。

## 任務目的

從讀者正在經歷的事件開頭，不先講工具。每篇讓讀者知道正在處理的是哪個條件，而不是得到一個命理判決。

## 驗收條件

- 前段直接回答情境問題。
- 至少兩個具體生活場景與三個可觀察動詞。
- 工具解釋只補足問題，不變成工具課。
- 小提醒只在題目需要時出現，且是可執行、可檢查的動作。
- 限制附在推論後，不使用固定免責段落堆疊。
- 不替讀者決定分手、離職、投資、搬家或其他重大選擇。

## 驗證與證據

執行文章 QA gate、`tests/test_web.py`、`git diff --check`；抽查手機／桌機文章頁內容不溢出、不改版。

證據：`artifacts/fortune_council/content_rewrite_execution/evidence/scenarios/`
