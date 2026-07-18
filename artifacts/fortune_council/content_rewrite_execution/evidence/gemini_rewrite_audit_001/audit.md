# CARD-CONTENT-GEMINI-REWRITE-AUDIT-001

## 總覽

- Runtime registry 原始列數：287
- 以 `id + product + slug` 去重後 inventory：287
- 全量掃描與 inventory 排序：全域 serial 尾碼數字升冪，再以 product/category 與 id 作為 tie-breaker。
- 後續 Gemini rewrite queue 排序：priority → serial 尾碼數字 → product/category → id。
- **後續 Gemini Rewrite Batch 1 從最小流水號且 verdict=GEMINI_REWRITE 的文章開始：MBTI-BASE-01 / personality-0001。**
- KEEP：125
- LIGHT_EDIT：111
- GEMINI_REWRITE：51
- BLOCKED：0

## 判定準則

- KEEP：正文具體、能回答搜尋意圖、保留邊界，未命中明顯模板或禁用句。
- LIGHT_EDIT：局部可修，例如 FAQ、導言、主關鍵字位置或少量模板句。
- GEMINI_REWRITE：同時有模板結構、批次固定句型、正文過短、搜尋意圖延遲或情境密度不足，全文重寫比局部修補更划算。
- BLOCKED：runtime 有 registry record 但正文缺失、過薄或 body 解析失敗。

## Verdict 分布

| Verdict | Count |
|---|---:|
| KEEP | 125 |
| LIGHT_EDIT | 111 |
| GEMINI_REWRITE | 51 |
| BLOCKED | 0 |

## 問題分布

| Issue code | Count |
|---|---:|
| SEARCH_INTENT_LAG | 56 |
| SHORT_BODY | 55 |
| TEMPLATE_STRUCTURE | 50 |
| REPEATED_BATCH_COPY | 50 |
| LOW_SCENARIO_DENSITY | 9 |
| BANNED_PHRASE | 3 |

## Gemini 優先批次

| Priority | Count |
|---|---:|
| P0 | 51 |
| P1 | 0 |
| P2 | 0 |

Queue batch size：每批最多 5 篇；Batch 1 取全域排序前 5 篇，第一篇必須是所有 GEMINI_REWRITE 中流水號數字最小者。

## 代表案例

- P0-batch-01 MBTI-BASE-01 / personality-0001：app/web/static/article-meta.js::fallback-or-inline，正文 736 字。 正文僅 736 字，低於基礎概念文建議長度。 具體情境/可觀察動詞密度偏低，偵測到 5 個具體訊號。 主關鍵字「MBTI 是什麼」未在正文前 130 字內自然回答。
- P0-batch-01 THEME-LIFE-03 / life-direction-0003：app/web/static/article-expansion-50.js，正文 1127 字。 「人生方向塔羅」正文小標高度模板化，實際小標包含「人生方向塔羅真正要整理的是什麼？」、「人生方向塔羅有哪些可觀察線索？」、「把人生方向塔羅變成下一步」、「人生方向塔羅不能代表什麼？」。 「人生方向塔羅」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。
- P0-batch-01 THEME-INTERPERSONAL-03 / interpersonal-0003：app/web/static/article-expansion-50.js，正文 1127 字。 「社交後很累」正文小標高度模板化，實際小標包含「社交後很累真正要整理的是什麼？」、「社交後很累有哪些可觀察線索？」、「把社交後很累變成下一步」、「社交後很累不能代表什麼？」。 「社交後很累」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。
- P0-batch-01 THEME-LIFE-04 / life-direction-0004：app/web/static/article-expansion-50.js，正文 1130 字。 「人格選擇偏好」正文小標高度模板化，實際小標包含「人格選擇偏好真正要整理的是什麼？」、「人格選擇偏好有哪些可觀察線索？」、「把人格選擇偏好變成下一步」、「人格選擇偏好不能代表什麼？」。 「人格選擇偏好」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。
- P0-batch-01 THEME-WEALTH-04 / wealth-0004：app/web/static/article-expansion-50.js，正文 1100 字。 「命盤資源節奏」正文小標高度模板化，實際小標包含「命盤資源節奏真正要整理的是什麼？」、「命盤資源節奏有哪些可觀察線索？」、「把命盤資源節奏變成下一步」、「命盤資源節奏不能代表什麼？」。 「命盤資源節奏」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。
- P0-batch-02 THEME-INTERPERSONAL-04 / interpersonal-0004：app/web/static/article-expansion-50.js，正文 1135 字。 「職場私人界線」正文小標高度模板化，實際小標包含「職場私人界線真正要整理的是什麼？」、「職場私人界線有哪些可觀察線索？」、「把職場私人界線變成下一步」、「職場私人界線不能代表什麼？」。 「職場私人界線」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。
- P0-batch-02 THEME-CAREER-05 / career-0005：app/web/static/article-expansion-50.js，正文 1131 字。 「工作卡住塔羅」正文小標高度模板化，實際小標包含「工作卡住塔羅真正要整理的是什麼？」、「工作卡住塔羅有哪些可觀察線索？」、「把工作卡住塔羅變成下一步」、「工作卡住塔羅不能代表什麼？」。 「工作卡住塔羅」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。
- P0-batch-02 THEME-LIFE-05 / life-direction-0005：app/web/static/article-expansion-50.js，正文 1123 字。 「命盤人生階段」正文小標高度模板化，實際小標包含「命盤人生階段真正要整理的是什麼？」、「命盤人生階段有哪些可觀察線索？」、「把命盤人生階段變成下一步」、「命盤人生階段不能代表什麼？」。 「命盤人生階段」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。
- P0-batch-02 THEME-WEALTH-05 / wealth-0005：app/web/static/article-expansion-50.js，正文 1123 字。 「創業財務問題」正文小標高度模板化，實際小標包含「創業財務問題真正要整理的是什麼？」、「創業財務問題有哪些可觀察線索？」、「把創業財務問題變成下一步」、「創業財務問題不能代表什麼？」。 「創業財務問題」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。
- P0-batch-02 THEME-INTERPERSONAL-05 / interpersonal-0005：app/web/static/article-expansion-50.js，正文 1118 字。 「渴望被看見」正文小標高度模板化，實際小標包含「渴望被看見真正要整理的是什麼？」、「渴望被看見有哪些可觀察線索？」、「把渴望被看見變成下一步」、「渴望被看見不能代表什麼？」。 「渴望被看見」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。
- P0-batch-03 THEME-LOVE-05 / love-0005：app/web/static/article-expansion-50.js，正文 1078 字。 「關係卡住」正文小標高度模板化，實際小標包含「關係卡住真正要整理的是什麼？」、「關係卡住有哪些可觀察線索？」、「把關係卡住變成下一步」、「關係卡住不能代表什麼？」。 「關係卡住」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。
- P0-batch-03 ASTRO-MERCURY-01 / astrology-0006：app/web/static/article-expansion-50.js，正文 1068 字。 「水星星座」正文小標高度模板化，實際小標包含「水星星座真正要整理的是什麼？」、「水星星座有哪些可觀察線索？」、「把水星星座變成下一步」、「水星星座不能代表什麼？」。 「水星星座」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

## 結論

本卡只完成盤點、判定與 Gemini 改寫佇列；未改寫任何正式文章，也未呼叫 Gemini 或外部寫入服務。
