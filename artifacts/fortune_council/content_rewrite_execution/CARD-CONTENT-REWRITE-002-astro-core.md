# CARD-CONTENT-REWRITE-002｜星盤核心文章重寫

## 任務ID / 卡片類型｜派工對象

`CARD-CONTENT-REWRITE-002` / content rewrite｜gpt-5.5

## 請讀

- `docs/pantheon_article_publication_standard.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/tool_hardening/click108_seo_audit.md`
- `app/web/static/article-registry.js`
- `app/web/static/article-meta.js`
- `artifacts/fortune_council/content_rewrite_execution/CARD-CONTENT-REWRITE-000-master-plan.md`

## 文章範圍

- `astrology-0001`：星盤是什麼？太陽、月亮、上升星座怎麼看
- `astrology-0002`：上升星座是什麼？它和太陽星座差在哪
- `astrology-0003`：月亮星座是什麼？情緒與安全感怎麼看
- `astrology-0004`：星座感情運勢怎麼看？先分清太陽、月亮與上升
- `astrology-0005`：金星星座是什麼？感情需求與喜歡方式怎麼看

## 任務目的

逐篇重寫完整正文，不只修最後一個 H2。基礎文回答定義與讀法；情境文從讀者正在遇到的互動開始。

## 驗收條件

- 每篇前 80 字有主攻關鍵字，前 150 字直接回答。
- 基礎文至少一個具體場景；情境文至少兩個具體場景。
- 使用自然可觀察動詞，不保留「抓住基本語氣」「星盤語言要能回到」等抽象模板句。
- 太陽、月亮、上升、金星的說明是觀察角度，不寫成固定性格或命運。
- 限制接在具體解釋後；不重複「不能代表完整人格」作為每段結尾。
- FAQ 3-5 題，保留既有 metadata 契約。

## 禁止

- 不改版面、URL、文章編號與內鏈配置。
- 不加入占星保證、感情判決或健康／財務建議。

## 驗證與證據

執行 `tests/test_web.py`、文章 QA gate、`git diff --check`；逐篇輸出 blocker / warning / pass。

證據：`artifacts/fortune_council/content_rewrite_execution/evidence/astro/`
