# Gemini Rewrite Queue

只列 `GEMINI_REWRITE`，不執行改寫。

排序契約：後續 Gemini 改寫必須從流水號數字最小的舊文章開始；queue 使用 `priority -> serial 尾碼數字 -> product/category -> id`。Batch 1 取此全域順序前 5 篇，第一篇必須是所有 `GEMINI_REWRITE` 中流水號數字最小者。

## Batch 1 | P0-batch-01

排序契約：priority -> serial 尾碼數字 -> product/category -> id；本批不得包含 KEEP。Batch 1 第一篇為所有 GEMINI_REWRITE 中流水號數字最小者：MBTI-BASE-01 / personality-0001。

可供 pipeline 包裝使用的 public brief：

```json
{
  "schema_version": 1,
  "run_id": "gemini_rewrite_audit_001_batch_01",
  "mode": "rewrite_existing_body",
  "sort_contract": "priority -> serial_suffix_number_ascending -> product/category -> id; do not include KEEP",
  "articles": [
    {
      "slot": "article-01",
      "article_id": "MBTI-BASE-01",
      "product": "personality",
      "category": "personality",
      "serial": "personality-0001",
      "slug": "personality-0001",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-meta.js::fallback-or-inline",
      "primaryKeyword": "MBTI 是什麼",
      "title": "MBTI 是什麼？16 型人格、測驗與自我理解怎麼看",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "SHORT_BODY",
        "LOW_SCENARIO_DENSITY",
        "SEARCH_INTENT_LAG"
      ],
      "brief": [
        "保留 id=MBTI-BASE-01、product=personality、slug=personality-0001、title=MBTI 是什麼？16 型人格、測驗與自我理解怎麼看、primaryKeyword=MBTI 是什麼，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「MBTI 是什麼」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-meta.js::fallback-or-inline，正文 736 字。 正文僅 736 字，低於基礎概念文建議長度。 具體情境/可觀察動詞密度偏低，偵測到 5 個具體訊號。 主關鍵字「MBTI 是什麼」未在正文前 130 字內自然回答。"
      ]
    },
    {
      "slot": "article-02",
      "article_id": "THEME-LIFE-03",
      "product": "fortune",
      "category": "life-direction",
      "serial": "life-direction-0003",
      "slug": "life-direction-0003",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "人生方向塔羅",
      "title": "塔羅怎麼整理人生方向？先把大問題切成下一步",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-LIFE-03、product=fortune、slug=life-direction-0003、title=塔羅怎麼整理人生方向？先把大問題切成下一步、primaryKeyword=人生方向塔羅，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「人生方向塔羅」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1127 字。 「人生方向塔羅」正文小標高度模板化，實際小標包含「人生方向塔羅真正要整理的是什麼？」、「人生方向塔羅有哪些可觀察線索？」、「把人生方向塔羅變成下一步」、「人生方向塔羅不能代表什麼？」。 「人生方向塔羅」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-03",
      "article_id": "THEME-INTERPERSONAL-03",
      "product": "personality",
      "category": "interpersonal",
      "serial": "interpersonal-0003",
      "slug": "interpersonal-0003",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "社交後很累",
      "title": "為什麼社交後很累？先分清刺激量、角色壓力與界線",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-INTERPERSONAL-03、product=personality、slug=interpersonal-0003、title=為什麼社交後很累？先分清刺激量、角色壓力與界線、primaryKeyword=社交後很累，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「社交後很累」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1127 字。 「社交後很累」正文小標高度模板化，實際小標包含「社交後很累真正要整理的是什麼？」、「社交後很累有哪些可觀察線索？」、「把社交後很累變成下一步」、「社交後很累不能代表什麼？」。 「社交後很累」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-04",
      "article_id": "THEME-LIFE-04",
      "product": "fortune",
      "category": "life-direction",
      "serial": "life-direction-0004",
      "slug": "life-direction-0004",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "人格選擇偏好",
      "title": "人格結果怎麼看長期選擇？理解偏好，不把選項鎖死",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-LIFE-04、product=fortune、slug=life-direction-0004、title=人格結果怎麼看長期選擇？理解偏好，不把選項鎖死、primaryKeyword=人格選擇偏好，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「人格選擇偏好」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1130 字。 「人格選擇偏好」正文小標高度模板化，實際小標包含「人格選擇偏好真正要整理的是什麼？」、「人格選擇偏好有哪些可觀察線索？」、「把人格選擇偏好變成下一步」、「人格選擇偏好不能代表什麼？」。 「人格選擇偏好」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-05",
      "article_id": "THEME-WEALTH-04",
      "product": "fortune",
      "category": "wealth",
      "serial": "wealth-0004",
      "slug": "wealth-0004",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "命盤資源節奏",
      "title": "命盤怎麼看資源節奏？把收入、支出與承擔分開",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-WEALTH-04、product=fortune、slug=wealth-0004、title=命盤怎麼看資源節奏？把收入、支出與承擔分開、primaryKeyword=命盤資源節奏，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「命盤資源節奏」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1100 字。 「命盤資源節奏」正文小標高度模板化，實際小標包含「命盤資源節奏真正要整理的是什麼？」、「命盤資源節奏有哪些可觀察線索？」、「把命盤資源節奏變成下一步」、「命盤資源節奏不能代表什麼？」。 「命盤資源節奏」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    }
  ]
}
```

### MBTI-BASE-01 | personality-0001 | MBTI 是什麼？16 型人格、測驗與自我理解怎麼看

- 不可變更欄位：product=personality; category=personality; serial=personality-0001; slug=personality-0001; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-meta.js::fallback-or-inline
- Gemini batch：P0-batch-01
- 改寫 brief：
  - 保留 id=MBTI-BASE-01、product=personality、slug=personality-0001、title=MBTI 是什麼？16 型人格、測驗與自我理解怎麼看、primaryKeyword=MBTI 是什麼，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「MBTI 是什麼」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-meta.js::fallback-or-inline，正文 736 字。 正文僅 736 字，低於基礎概念文建議長度。 具體情境/可觀察動詞密度偏低，偵測到 5 個具體訊號。 主關鍵字「MBTI 是什麼」未在正文前 130 字內自然回答。

### THEME-LIFE-03 | life-direction-0003 | 塔羅怎麼整理人生方向？先把大問題切成下一步

- 不可變更欄位：product=fortune; category=life-direction; serial=life-direction-0003; slug=life-direction-0003; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-01
- 改寫 brief：
  - 保留 id=THEME-LIFE-03、product=fortune、slug=life-direction-0003、title=塔羅怎麼整理人生方向？先把大問題切成下一步、primaryKeyword=人生方向塔羅，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「人生方向塔羅」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1127 字。 「人生方向塔羅」正文小標高度模板化，實際小標包含「人生方向塔羅真正要整理的是什麼？」、「人生方向塔羅有哪些可觀察線索？」、「把人生方向塔羅變成下一步」、「人生方向塔羅不能代表什麼？」。 「人生方向塔羅」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-INTERPERSONAL-03 | interpersonal-0003 | 為什麼社交後很累？先分清刺激量、角色壓力與界線

- 不可變更欄位：product=personality; category=interpersonal; serial=interpersonal-0003; slug=interpersonal-0003; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-01
- 改寫 brief：
  - 保留 id=THEME-INTERPERSONAL-03、product=personality、slug=interpersonal-0003、title=為什麼社交後很累？先分清刺激量、角色壓力與界線、primaryKeyword=社交後很累，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「社交後很累」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1127 字。 「社交後很累」正文小標高度模板化，實際小標包含「社交後很累真正要整理的是什麼？」、「社交後很累有哪些可觀察線索？」、「把社交後很累變成下一步」、「社交後很累不能代表什麼？」。 「社交後很累」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-LIFE-04 | life-direction-0004 | 人格結果怎麼看長期選擇？理解偏好，不把選項鎖死

- 不可變更欄位：product=fortune; category=life-direction; serial=life-direction-0004; slug=life-direction-0004; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-01
- 改寫 brief：
  - 保留 id=THEME-LIFE-04、product=fortune、slug=life-direction-0004、title=人格結果怎麼看長期選擇？理解偏好，不把選項鎖死、primaryKeyword=人格選擇偏好，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「人格選擇偏好」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1130 字。 「人格選擇偏好」正文小標高度模板化，實際小標包含「人格選擇偏好真正要整理的是什麼？」、「人格選擇偏好有哪些可觀察線索？」、「把人格選擇偏好變成下一步」、「人格選擇偏好不能代表什麼？」。 「人格選擇偏好」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-WEALTH-04 | wealth-0004 | 命盤怎麼看資源節奏？把收入、支出與承擔分開

- 不可變更欄位：product=fortune; category=wealth; serial=wealth-0004; slug=wealth-0004; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-01
- 改寫 brief：
  - 保留 id=THEME-WEALTH-04、product=fortune、slug=wealth-0004、title=命盤怎麼看資源節奏？把收入、支出與承擔分開、primaryKeyword=命盤資源節奏，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「命盤資源節奏」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1100 字。 「命盤資源節奏」正文小標高度模板化，實際小標包含「命盤資源節奏真正要整理的是什麼？」、「命盤資源節奏有哪些可觀察線索？」、「把命盤資源節奏變成下一步」、「命盤資源節奏不能代表什麼？」。 「命盤資源節奏」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

## Batch 2 | P0-batch-02

排序契約：priority -> serial 尾碼數字 -> product/category -> id；本批不得包含 KEEP。

可供 pipeline 包裝使用的 public brief：

```json
{
  "schema_version": 1,
  "run_id": "gemini_rewrite_audit_001_batch_02",
  "mode": "rewrite_existing_body",
  "sort_contract": "priority -> serial_suffix_number_ascending -> product/category -> id; do not include KEEP",
  "articles": [
    {
      "slot": "article-01",
      "article_id": "THEME-INTERPERSONAL-04",
      "product": "personality",
      "category": "interpersonal",
      "serial": "interpersonal-0004",
      "slug": "interpersonal-0004",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "職場私人界線",
      "title": "職場人際和私人關係怎麼劃界線？先看角色與責任",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-INTERPERSONAL-04、product=personality、slug=interpersonal-0004、title=職場人際和私人關係怎麼劃界線？先看角色與責任、primaryKeyword=職場私人界線，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「職場私人界線」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1135 字。 「職場私人界線」正文小標高度模板化，實際小標包含「職場私人界線真正要整理的是什麼？」、「職場私人界線有哪些可觀察線索？」、「把職場私人界線變成下一步」、「職場私人界線不能代表什麼？」。 「職場私人界線」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-02",
      "article_id": "THEME-CAREER-05",
      "product": "fortune",
      "category": "career",
      "serial": "career-0005",
      "slug": "career-0005",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "工作卡住塔羅",
      "title": "工作卡住時，塔羅適合幫你整理什麼？",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-CAREER-05、product=fortune、slug=career-0005、title=工作卡住時，塔羅適合幫你整理什麼？、primaryKeyword=工作卡住塔羅，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「工作卡住塔羅」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1131 字。 「工作卡住塔羅」正文小標高度模板化，實際小標包含「工作卡住塔羅真正要整理的是什麼？」、「工作卡住塔羅有哪些可觀察線索？」、「把工作卡住塔羅變成下一步」、「工作卡住塔羅不能代表什麼？」。 「工作卡住塔羅」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-03",
      "article_id": "THEME-LIFE-05",
      "product": "fortune",
      "category": "life-direction",
      "serial": "life-direction-0005",
      "slug": "life-direction-0005",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "命盤人生階段",
      "title": "命盤怎麼看人生階段？用週期回顧，不把時間寫成事件",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-LIFE-05、product=fortune、slug=life-direction-0005、title=命盤怎麼看人生階段？用週期回顧，不把時間寫成事件、primaryKeyword=命盤人生階段，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「命盤人生階段」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1123 字。 「命盤人生階段」正文小標高度模板化，實際小標包含「命盤人生階段真正要整理的是什麼？」、「命盤人生階段有哪些可觀察線索？」、「把命盤人生階段變成下一步」、「命盤人生階段不能代表什麼？」。 「命盤人生階段」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-04",
      "article_id": "THEME-WEALTH-05",
      "product": "fortune",
      "category": "wealth",
      "serial": "wealth-0005",
      "slug": "wealth-0005",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "創業財務問題",
      "title": "創業談財富，不能只問會不會賺錢",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-WEALTH-05、product=fortune、slug=wealth-0005、title=創業談財富，不能只問會不會賺錢、primaryKeyword=創業財務問題，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「創業財務問題」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1123 字。 「創業財務問題」正文小標高度模板化，實際小標包含「創業財務問題真正要整理的是什麼？」、「創業財務問題有哪些可觀察線索？」、「把創業財務問題變成下一步」、「創業財務問題不能代表什麼？」。 「創業財務問題」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-05",
      "article_id": "THEME-INTERPERSONAL-05",
      "product": "personality",
      "category": "interpersonal",
      "serial": "interpersonal-0005",
      "slug": "interpersonal-0005",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "渴望被看見",
      "title": "渴望被看見怎麼影響人際？觀察你用什麼交換認可",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-INTERPERSONAL-05、product=personality、slug=interpersonal-0005、title=渴望被看見怎麼影響人際？觀察你用什麼交換認可、primaryKeyword=渴望被看見，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「渴望被看見」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1118 字。 「渴望被看見」正文小標高度模板化，實際小標包含「渴望被看見真正要整理的是什麼？」、「渴望被看見有哪些可觀察線索？」、「把渴望被看見變成下一步」、「渴望被看見不能代表什麼？」。 「渴望被看見」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    }
  ]
}
```

### THEME-INTERPERSONAL-04 | interpersonal-0004 | 職場人際和私人關係怎麼劃界線？先看角色與責任

- 不可變更欄位：product=personality; category=interpersonal; serial=interpersonal-0004; slug=interpersonal-0004; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-02
- 改寫 brief：
  - 保留 id=THEME-INTERPERSONAL-04、product=personality、slug=interpersonal-0004、title=職場人際和私人關係怎麼劃界線？先看角色與責任、primaryKeyword=職場私人界線，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「職場私人界線」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1135 字。 「職場私人界線」正文小標高度模板化，實際小標包含「職場私人界線真正要整理的是什麼？」、「職場私人界線有哪些可觀察線索？」、「把職場私人界線變成下一步」、「職場私人界線不能代表什麼？」。 「職場私人界線」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-CAREER-05 | career-0005 | 工作卡住時，塔羅適合幫你整理什麼？

- 不可變更欄位：product=fortune; category=career; serial=career-0005; slug=career-0005; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-02
- 改寫 brief：
  - 保留 id=THEME-CAREER-05、product=fortune、slug=career-0005、title=工作卡住時，塔羅適合幫你整理什麼？、primaryKeyword=工作卡住塔羅，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「工作卡住塔羅」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1131 字。 「工作卡住塔羅」正文小標高度模板化，實際小標包含「工作卡住塔羅真正要整理的是什麼？」、「工作卡住塔羅有哪些可觀察線索？」、「把工作卡住塔羅變成下一步」、「工作卡住塔羅不能代表什麼？」。 「工作卡住塔羅」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-LIFE-05 | life-direction-0005 | 命盤怎麼看人生階段？用週期回顧，不把時間寫成事件

- 不可變更欄位：product=fortune; category=life-direction; serial=life-direction-0005; slug=life-direction-0005; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-02
- 改寫 brief：
  - 保留 id=THEME-LIFE-05、product=fortune、slug=life-direction-0005、title=命盤怎麼看人生階段？用週期回顧，不把時間寫成事件、primaryKeyword=命盤人生階段，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「命盤人生階段」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1123 字。 「命盤人生階段」正文小標高度模板化，實際小標包含「命盤人生階段真正要整理的是什麼？」、「命盤人生階段有哪些可觀察線索？」、「把命盤人生階段變成下一步」、「命盤人生階段不能代表什麼？」。 「命盤人生階段」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-WEALTH-05 | wealth-0005 | 創業談財富，不能只問會不會賺錢

- 不可變更欄位：product=fortune; category=wealth; serial=wealth-0005; slug=wealth-0005; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-02
- 改寫 brief：
  - 保留 id=THEME-WEALTH-05、product=fortune、slug=wealth-0005、title=創業談財富，不能只問會不會賺錢、primaryKeyword=創業財務問題，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「創業財務問題」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1123 字。 「創業財務問題」正文小標高度模板化，實際小標包含「創業財務問題真正要整理的是什麼？」、「創業財務問題有哪些可觀察線索？」、「把創業財務問題變成下一步」、「創業財務問題不能代表什麼？」。 「創業財務問題」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-INTERPERSONAL-05 | interpersonal-0005 | 渴望被看見怎麼影響人際？觀察你用什麼交換認可

- 不可變更欄位：product=personality; category=interpersonal; serial=interpersonal-0005; slug=interpersonal-0005; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-02
- 改寫 brief：
  - 保留 id=THEME-INTERPERSONAL-05、product=personality、slug=interpersonal-0005、title=渴望被看見怎麼影響人際？觀察你用什麼交換認可、primaryKeyword=渴望被看見，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「渴望被看見」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1118 字。 「渴望被看見」正文小標高度模板化，實際小標包含「渴望被看見真正要整理的是什麼？」、「渴望被看見有哪些可觀察線索？」、「把渴望被看見變成下一步」、「渴望被看見不能代表什麼？」。 「渴望被看見」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

## Batch 3 | P0-batch-03

排序契約：priority -> serial 尾碼數字 -> product/category -> id；本批不得包含 KEEP。

可供 pipeline 包裝使用的 public brief：

```json
{
  "schema_version": 1,
  "run_id": "gemini_rewrite_audit_001_batch_03",
  "mode": "rewrite_existing_body",
  "sort_contract": "priority -> serial_suffix_number_ascending -> product/category -> id; do not include KEEP",
  "articles": [
    {
      "slot": "article-01",
      "article_id": "THEME-LOVE-05",
      "product": "tarot",
      "category": "love",
      "serial": "love-0005",
      "slug": "love-0005",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "關係卡住",
      "title": "一段關係卡住怎麼辦？先看互動循環，不急著猜結果",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-LOVE-05、product=tarot、slug=love-0005、title=一段關係卡住怎麼辦？先看互動循環，不急著猜結果、primaryKeyword=關係卡住，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「關係卡住」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1078 字。 「關係卡住」正文小標高度模板化，實際小標包含「關係卡住真正要整理的是什麼？」、「關係卡住有哪些可觀察線索？」、「把關係卡住變成下一步」、「關係卡住不能代表什麼？」。 「關係卡住」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-02",
      "article_id": "ASTRO-MERCURY-01",
      "product": "astro",
      "category": "astrology",
      "serial": "astrology-0006",
      "slug": "astrology-0006",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "水星星座",
      "title": "水星星座是什麼？溝通、思考與學習方式怎麼看",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=ASTRO-MERCURY-01、product=astro、slug=astrology-0006、title=水星星座是什麼？溝通、思考與學習方式怎麼看、primaryKeyword=水星星座，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「水星星座」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1068 字。 「水星星座」正文小標高度模板化，實際小標包含「水星星座真正要整理的是什麼？」、「水星星座有哪些可觀察線索？」、「把水星星座變成下一步」、「水星星座不能代表什麼？」。 「水星星座」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-03",
      "article_id": "THEME-CAREER-06",
      "product": "fortune",
      "category": "career",
      "serial": "career-0006",
      "slug": "career-0006",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "工作穩定成長自由",
      "title": "工作要選穩定、成長還是自由？先比較你真正交換了什麼",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-CAREER-06、product=fortune、slug=career-0006、title=工作要選穩定、成長還是自由？先比較你真正交換了什麼、primaryKeyword=工作穩定成長自由，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「工作穩定成長自由」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1187 字。 「工作穩定成長自由」正文小標高度模板化，實際小標包含「工作穩定成長自由真正要整理的是什麼？」、「工作穩定成長自由有哪些可觀察線索？」、「把工作穩定成長自由變成下一步」、「工作穩定成長自由不能代表什麼？」。 「工作穩定成長自由」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-04",
      "article_id": "THEME-LIFE-06",
      "product": "fortune",
      "category": "life-direction",
      "serial": "life-direction-0006",
      "slug": "life-direction-0006",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "人生重大變動",
      "title": "創業、轉職、搬家怎麼整理？重大變動先看可逆性",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-LIFE-06、product=fortune、slug=life-direction-0006、title=創業、轉職、搬家怎麼整理？重大變動先看可逆性、primaryKeyword=人生重大變動，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「人生重大變動」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1130 字。 「人生重大變動」正文小標高度模板化，實際小標包含「人生重大變動真正要整理的是什麼？」、「人生重大變動有哪些可觀察線索？」、「把人生重大變動變成下一步」、「人生重大變動不能代表什麼？」。 「人生重大變動」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-05",
      "article_id": "THEME-WEALTH-06",
      "product": "fortune",
      "category": "wealth",
      "serial": "wealth-0006",
      "slug": "wealth-0006",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "收入與安全感",
      "title": "為什麼努力工作仍沒有安全感？收入不是唯一變數",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-WEALTH-06、product=fortune、slug=wealth-0006、title=為什麼努力工作仍沒有安全感？收入不是唯一變數、primaryKeyword=收入與安全感，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「收入與安全感」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1142 字。 「收入與安全感」正文小標高度模板化，實際小標包含「收入與安全感真正要整理的是什麼？」、「收入與安全感有哪些可觀察線索？」、「把收入與安全感變成下一步」、「收入與安全感不能代表什麼？」。 「收入與安全感」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    }
  ]
}
```

### THEME-LOVE-05 | love-0005 | 一段關係卡住怎麼辦？先看互動循環，不急著猜結果

- 不可變更欄位：product=tarot; category=love; serial=love-0005; slug=love-0005; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-03
- 改寫 brief：
  - 保留 id=THEME-LOVE-05、product=tarot、slug=love-0005、title=一段關係卡住怎麼辦？先看互動循環，不急著猜結果、primaryKeyword=關係卡住，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「關係卡住」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1078 字。 「關係卡住」正文小標高度模板化，實際小標包含「關係卡住真正要整理的是什麼？」、「關係卡住有哪些可觀察線索？」、「把關係卡住變成下一步」、「關係卡住不能代表什麼？」。 「關係卡住」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### ASTRO-MERCURY-01 | astrology-0006 | 水星星座是什麼？溝通、思考與學習方式怎麼看

- 不可變更欄位：product=astro; category=astrology; serial=astrology-0006; slug=astrology-0006; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-03
- 改寫 brief：
  - 保留 id=ASTRO-MERCURY-01、product=astro、slug=astrology-0006、title=水星星座是什麼？溝通、思考與學習方式怎麼看、primaryKeyword=水星星座，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「水星星座」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1068 字。 「水星星座」正文小標高度模板化，實際小標包含「水星星座真正要整理的是什麼？」、「水星星座有哪些可觀察線索？」、「把水星星座變成下一步」、「水星星座不能代表什麼？」。 「水星星座」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-CAREER-06 | career-0006 | 工作要選穩定、成長還是自由？先比較你真正交換了什麼

- 不可變更欄位：product=fortune; category=career; serial=career-0006; slug=career-0006; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-03
- 改寫 brief：
  - 保留 id=THEME-CAREER-06、product=fortune、slug=career-0006、title=工作要選穩定、成長還是自由？先比較你真正交換了什麼、primaryKeyword=工作穩定成長自由，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「工作穩定成長自由」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1187 字。 「工作穩定成長自由」正文小標高度模板化，實際小標包含「工作穩定成長自由真正要整理的是什麼？」、「工作穩定成長自由有哪些可觀察線索？」、「把工作穩定成長自由變成下一步」、「工作穩定成長自由不能代表什麼？」。 「工作穩定成長自由」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-LIFE-06 | life-direction-0006 | 創業、轉職、搬家怎麼整理？重大變動先看可逆性

- 不可變更欄位：product=fortune; category=life-direction; serial=life-direction-0006; slug=life-direction-0006; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-03
- 改寫 brief：
  - 保留 id=THEME-LIFE-06、product=fortune、slug=life-direction-0006、title=創業、轉職、搬家怎麼整理？重大變動先看可逆性、primaryKeyword=人生重大變動，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「人生重大變動」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1130 字。 「人生重大變動」正文小標高度模板化，實際小標包含「人生重大變動真正要整理的是什麼？」、「人生重大變動有哪些可觀察線索？」、「把人生重大變動變成下一步」、「人生重大變動不能代表什麼？」。 「人生重大變動」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-WEALTH-06 | wealth-0006 | 為什麼努力工作仍沒有安全感？收入不是唯一變數

- 不可變更欄位：product=fortune; category=wealth; serial=wealth-0006; slug=wealth-0006; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-03
- 改寫 brief：
  - 保留 id=THEME-WEALTH-06、product=fortune、slug=wealth-0006、title=為什麼努力工作仍沒有安全感？收入不是唯一變數、primaryKeyword=收入與安全感，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「收入與安全感」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1142 字。 「收入與安全感」正文小標高度模板化，實際小標包含「收入與安全感真正要整理的是什麼？」、「收入與安全感有哪些可觀察線索？」、「把收入與安全感變成下一步」、「收入與安全感不能代表什麼？」。 「收入與安全感」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

## Batch 4 | P0-batch-04

排序契約：priority -> serial 尾碼數字 -> product/category -> id；本批不得包含 KEEP。

可供 pipeline 包裝使用的 public brief：

```json
{
  "schema_version": 1,
  "run_id": "gemini_rewrite_audit_001_batch_04",
  "mode": "rewrite_existing_body",
  "sort_contract": "priority -> serial_suffix_number_ascending -> product/category -> id; do not include KEEP",
  "articles": [
    {
      "slot": "article-01",
      "article_id": "THEME-INTERPERSONAL-06",
      "product": "personality",
      "category": "interpersonal",
      "serial": "interpersonal-0006",
      "slug": "interpersonal-0006",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "人際界線塔羅",
      "title": "塔羅怎麼整理人際界線？把注意力放回自己的位置",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-INTERPERSONAL-06、product=personality、slug=interpersonal-0006、title=塔羅怎麼整理人際界線？把注意力放回自己的位置、primaryKeyword=人際界線塔羅，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「人際界線塔羅」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1144 字。 「人際界線塔羅」正文小標高度模板化，實際小標包含「人際界線塔羅真正要整理的是什麼？」、「人際界線塔羅有哪些可觀察線索？」、「把人際界線塔羅變成下一步」、「人際界線塔羅不能代表什麼？」。 「人際界線塔羅」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-02",
      "article_id": "THEME-LOVE-06",
      "product": "tarot",
      "category": "love",
      "serial": "love-0006",
      "slug": "love-0006",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "重複感情模式",
      "title": "為什麼總遇到同一種感情模式？從選擇與界線找線索",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-LOVE-06、product=tarot、slug=love-0006、title=為什麼總遇到同一種感情模式？從選擇與界線找線索、primaryKeyword=重複感情模式，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「重複感情模式」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1137 字。 「重複感情模式」正文小標高度模板化，實際小標包含「重複感情模式真正要整理的是什麼？」、「重複感情模式有哪些可觀察線索？」、「把重複感情模式變成下一步」、「重複感情模式不能代表什麼？」。 「重複感情模式」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-03",
      "article_id": "ASTRO-MARS-01",
      "product": "astro",
      "category": "astrology",
      "serial": "astrology-0007",
      "slug": "astrology-0007",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "火星星座",
      "title": "火星星座是什麼？行動、衝突與慾望怎麼看",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=ASTRO-MARS-01、product=astro、slug=astrology-0007、title=火星星座是什麼？行動、衝突與慾望怎麼看、primaryKeyword=火星星座，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「火星星座」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1064 字。 「火星星座」正文小標高度模板化，實際小標包含「火星星座真正要整理的是什麼？」、「火星星座有哪些可觀察線索？」、「把火星星座變成下一步」、「火星星座不能代表什麼？」。 「火星星座」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-04",
      "article_id": "THEME-CAREER-07",
      "product": "fortune",
      "category": "career",
      "serial": "career-0007",
      "slug": "career-0007",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "人格工作方式",
      "title": "人格特質怎麼影響工作方式？看偏好，不拿類型選職業",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-CAREER-07、product=fortune、slug=career-0007、title=人格特質怎麼影響工作方式？看偏好，不拿類型選職業、primaryKeyword=人格工作方式，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「人格工作方式」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1126 字。 「人格工作方式」正文小標高度模板化，實際小標包含「人格工作方式真正要整理的是什麼？」、「人格工作方式有哪些可觀察線索？」、「把人格工作方式變成下一步」、「人格工作方式不能代表什麼？」。 「人格工作方式」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-05",
      "article_id": "THEME-LIFE-07",
      "product": "fortune",
      "category": "life-direction",
      "serial": "life-direction-0007",
      "slug": "life-direction-0007",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "害怕還是不適合",
      "title": "迷惘時怎麼分辨害怕和真的不適合？",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-LIFE-07、product=fortune、slug=life-direction-0007、title=迷惘時怎麼分辨害怕和真的不適合？、primaryKeyword=害怕還是不適合，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「害怕還是不適合」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1177 字。 「害怕還是不適合」正文小標高度模板化，實際小標包含「害怕還是不適合真正要整理的是什麼？」、「害怕還是不適合有哪些可觀察線索？」、「把害怕還是不適合變成下一步」、「害怕還是不適合不能代表什麼？」。 「害怕還是不適合」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    }
  ]
}
```

### THEME-INTERPERSONAL-06 | interpersonal-0006 | 塔羅怎麼整理人際界線？把注意力放回自己的位置

- 不可變更欄位：product=personality; category=interpersonal; serial=interpersonal-0006; slug=interpersonal-0006; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-04
- 改寫 brief：
  - 保留 id=THEME-INTERPERSONAL-06、product=personality、slug=interpersonal-0006、title=塔羅怎麼整理人際界線？把注意力放回自己的位置、primaryKeyword=人際界線塔羅，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「人際界線塔羅」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1144 字。 「人際界線塔羅」正文小標高度模板化，實際小標包含「人際界線塔羅真正要整理的是什麼？」、「人際界線塔羅有哪些可觀察線索？」、「把人際界線塔羅變成下一步」、「人際界線塔羅不能代表什麼？」。 「人際界線塔羅」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-LOVE-06 | love-0006 | 為什麼總遇到同一種感情模式？從選擇與界線找線索

- 不可變更欄位：product=tarot; category=love; serial=love-0006; slug=love-0006; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-04
- 改寫 brief：
  - 保留 id=THEME-LOVE-06、product=tarot、slug=love-0006、title=為什麼總遇到同一種感情模式？從選擇與界線找線索、primaryKeyword=重複感情模式，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「重複感情模式」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1137 字。 「重複感情模式」正文小標高度模板化，實際小標包含「重複感情模式真正要整理的是什麼？」、「重複感情模式有哪些可觀察線索？」、「把重複感情模式變成下一步」、「重複感情模式不能代表什麼？」。 「重複感情模式」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### ASTRO-MARS-01 | astrology-0007 | 火星星座是什麼？行動、衝突與慾望怎麼看

- 不可變更欄位：product=astro; category=astrology; serial=astrology-0007; slug=astrology-0007; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-04
- 改寫 brief：
  - 保留 id=ASTRO-MARS-01、product=astro、slug=astrology-0007、title=火星星座是什麼？行動、衝突與慾望怎麼看、primaryKeyword=火星星座，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「火星星座」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1064 字。 「火星星座」正文小標高度模板化，實際小標包含「火星星座真正要整理的是什麼？」、「火星星座有哪些可觀察線索？」、「把火星星座變成下一步」、「火星星座不能代表什麼？」。 「火星星座」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-CAREER-07 | career-0007 | 人格特質怎麼影響工作方式？看偏好，不拿類型選職業

- 不可變更欄位：product=fortune; category=career; serial=career-0007; slug=career-0007; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-04
- 改寫 brief：
  - 保留 id=THEME-CAREER-07、product=fortune、slug=career-0007、title=人格特質怎麼影響工作方式？看偏好，不拿類型選職業、primaryKeyword=人格工作方式，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「人格工作方式」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1126 字。 「人格工作方式」正文小標高度模板化，實際小標包含「人格工作方式真正要整理的是什麼？」、「人格工作方式有哪些可觀察線索？」、「把人格工作方式變成下一步」、「人格工作方式不能代表什麼？」。 「人格工作方式」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-LIFE-07 | life-direction-0007 | 迷惘時怎麼分辨害怕和真的不適合？

- 不可變更欄位：product=fortune; category=life-direction; serial=life-direction-0007; slug=life-direction-0007; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-04
- 改寫 brief：
  - 保留 id=THEME-LIFE-07、product=fortune、slug=life-direction-0007、title=迷惘時怎麼分辨害怕和真的不適合？、primaryKeyword=害怕還是不適合，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「害怕還是不適合」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1177 字。 「害怕還是不適合」正文小標高度模板化，實際小標包含「害怕還是不適合真正要整理的是什麼？」、「害怕還是不適合有哪些可觀察線索？」、「把害怕還是不適合變成下一步」、「害怕還是不適合不能代表什麼？」。 「害怕還是不適合」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

## Batch 5 | P0-batch-05

排序契約：priority -> serial 尾碼數字 -> product/category -> id；本批不得包含 KEEP。

可供 pipeline 包裝使用的 public brief：

```json
{
  "schema_version": 1,
  "run_id": "gemini_rewrite_audit_001_batch_05",
  "mode": "rewrite_existing_body",
  "sort_contract": "priority -> serial_suffix_number_ascending -> product/category -> id; do not include KEEP",
  "articles": [
    {
      "slot": "article-01",
      "article_id": "THEME-WEALTH-07",
      "product": "fortune",
      "category": "wealth",
      "serial": "wealth-0007",
      "slug": "wealth-0007",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "年度財富報告",
      "title": "年度財富報告適合看什麼？先看資源配置，不猜明牌",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-WEALTH-07、product=fortune、slug=wealth-0007、title=年度財富報告適合看什麼？先看資源配置，不猜明牌、primaryKeyword=年度財富報告，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「年度財富報告」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1118 字。 「年度財富報告」正文小標高度模板化，實際小標包含「年度財富報告真正要整理的是什麼？」、「年度財富報告有哪些可觀察線索？」、「把年度財富報告變成下一步」、「年度財富報告不能代表什麼？」。 「年度財富報告」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-02",
      "article_id": "THEME-INTERPERSONAL-07",
      "product": "personality",
      "category": "interpersonal",
      "serial": "interpersonal-0007",
      "slug": "interpersonal-0007",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "人格溝通習慣",
      "title": "人格結果怎麼看溝通習慣？從偏好找可調整的落差",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-INTERPERSONAL-07、product=personality、slug=interpersonal-0007、title=人格結果怎麼看溝通習慣？從偏好找可調整的落差、primaryKeyword=人格溝通習慣，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「人格溝通習慣」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1146 字。 「人格溝通習慣」正文小標高度模板化，實際小標包含「人格溝通習慣真正要整理的是什麼？」、「人格溝通習慣有哪些可觀察線索？」、「把人格溝通習慣變成下一步」、「人格溝通習慣不能代表什麼？」。 「人格溝通習慣」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-03",
      "article_id": "THEME-LOVE-07",
      "product": "tarot",
      "category": "love",
      "serial": "love-0007",
      "slug": "love-0007",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "伴侶衝突",
      "title": "伴侶相處卡住時，先問哪五個問題？",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-LOVE-07、product=tarot、slug=love-0007、title=伴侶相處卡住時，先問哪五個問題？、primaryKeyword=伴侶衝突，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「伴侶衝突」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1089 字。 「伴侶衝突」正文小標高度模板化，實際小標包含「伴侶衝突真正要整理的是什麼？」、「伴侶衝突有哪些可觀察線索？」、「把伴侶衝突變成下一步」、「伴侶衝突不能代表什麼？」。 「伴侶衝突」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-04",
      "article_id": "ASTRO-JUPITER-01",
      "product": "astro",
      "category": "astrology",
      "serial": "astrology-0008",
      "slug": "astrology-0008",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "木星星座",
      "title": "木星星座是什麼？成長、信念與機會感怎麼看",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=ASTRO-JUPITER-01、product=astro、slug=astrology-0008、title=木星星座是什麼？成長、信念與機會感怎麼看、primaryKeyword=木星星座，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「木星星座」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1049 字。 「木星星座」正文小標高度模板化，實際小標包含「木星星座真正要整理的是什麼？」、「木星星座有哪些可觀察線索？」、「把木星星座變成下一步」、「木星星座不能代表什麼？」。 「木星星座」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-05",
      "article_id": "THEME-CAREER-08",
      "product": "fortune",
      "category": "career",
      "serial": "career-0008",
      "slug": "career-0008",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "命盤事業節奏",
      "title": "命盤怎麼看事業節奏？先分清傾向、時機與決策",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-CAREER-08、product=fortune、slug=career-0008、title=命盤怎麼看事業節奏？先分清傾向、時機與決策、primaryKeyword=命盤事業節奏，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「命盤事業節奏」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1134 字。 「命盤事業節奏」正文小標高度模板化，實際小標包含「命盤事業節奏真正要整理的是什麼？」、「命盤事業節奏有哪些可觀察線索？」、「把命盤事業節奏變成下一步」、「命盤事業節奏不能代表什麼？」。 「命盤事業節奏」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    }
  ]
}
```

### THEME-WEALTH-07 | wealth-0007 | 年度財富報告適合看什麼？先看資源配置，不猜明牌

- 不可變更欄位：product=fortune; category=wealth; serial=wealth-0007; slug=wealth-0007; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-05
- 改寫 brief：
  - 保留 id=THEME-WEALTH-07、product=fortune、slug=wealth-0007、title=年度財富報告適合看什麼？先看資源配置，不猜明牌、primaryKeyword=年度財富報告，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「年度財富報告」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1118 字。 「年度財富報告」正文小標高度模板化，實際小標包含「年度財富報告真正要整理的是什麼？」、「年度財富報告有哪些可觀察線索？」、「把年度財富報告變成下一步」、「年度財富報告不能代表什麼？」。 「年度財富報告」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-INTERPERSONAL-07 | interpersonal-0007 | 人格結果怎麼看溝通習慣？從偏好找可調整的落差

- 不可變更欄位：product=personality; category=interpersonal; serial=interpersonal-0007; slug=interpersonal-0007; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-05
- 改寫 brief：
  - 保留 id=THEME-INTERPERSONAL-07、product=personality、slug=interpersonal-0007、title=人格結果怎麼看溝通習慣？從偏好找可調整的落差、primaryKeyword=人格溝通習慣，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「人格溝通習慣」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1146 字。 「人格溝通習慣」正文小標高度模板化，實際小標包含「人格溝通習慣真正要整理的是什麼？」、「人格溝通習慣有哪些可觀察線索？」、「把人格溝通習慣變成下一步」、「人格溝通習慣不能代表什麼？」。 「人格溝通習慣」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-LOVE-07 | love-0007 | 伴侶相處卡住時，先問哪五個問題？

- 不可變更欄位：product=tarot; category=love; serial=love-0007; slug=love-0007; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-05
- 改寫 brief：
  - 保留 id=THEME-LOVE-07、product=tarot、slug=love-0007、title=伴侶相處卡住時，先問哪五個問題？、primaryKeyword=伴侶衝突，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「伴侶衝突」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1089 字。 「伴侶衝突」正文小標高度模板化，實際小標包含「伴侶衝突真正要整理的是什麼？」、「伴侶衝突有哪些可觀察線索？」、「把伴侶衝突變成下一步」、「伴侶衝突不能代表什麼？」。 「伴侶衝突」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### ASTRO-JUPITER-01 | astrology-0008 | 木星星座是什麼？成長、信念與機會感怎麼看

- 不可變更欄位：product=astro; category=astrology; serial=astrology-0008; slug=astrology-0008; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-05
- 改寫 brief：
  - 保留 id=ASTRO-JUPITER-01、product=astro、slug=astrology-0008、title=木星星座是什麼？成長、信念與機會感怎麼看、primaryKeyword=木星星座，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「木星星座」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1049 字。 「木星星座」正文小標高度模板化，實際小標包含「木星星座真正要整理的是什麼？」、「木星星座有哪些可觀察線索？」、「把木星星座變成下一步」、「木星星座不能代表什麼？」。 「木星星座」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-CAREER-08 | career-0008 | 命盤怎麼看事業節奏？先分清傾向、時機與決策

- 不可變更欄位：product=fortune; category=career; serial=career-0008; slug=career-0008; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-05
- 改寫 brief：
  - 保留 id=THEME-CAREER-08、product=fortune、slug=career-0008、title=命盤怎麼看事業節奏？先分清傾向、時機與決策、primaryKeyword=命盤事業節奏，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「命盤事業節奏」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1134 字。 「命盤事業節奏」正文小標高度模板化，實際小標包含「命盤事業節奏真正要整理的是什麼？」、「命盤事業節奏有哪些可觀察線索？」、「把命盤事業節奏變成下一步」、「命盤事業節奏不能代表什麼？」。 「命盤事業節奏」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

## Batch 6 | P0-batch-06

排序契約：priority -> serial 尾碼數字 -> product/category -> id；本批不得包含 KEEP。

可供 pipeline 包裝使用的 public brief：

```json
{
  "schema_version": 1,
  "run_id": "gemini_rewrite_audit_001_batch_06",
  "mode": "rewrite_existing_body",
  "sort_contract": "priority -> serial_suffix_number_ascending -> product/category -> id; do not include KEEP",
  "articles": [
    {
      "slot": "article-01",
      "article_id": "THEME-LIFE-08",
      "product": "fortune",
      "category": "life-direction",
      "serial": "life-direction-0008",
      "slug": "life-direction-0008",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "人生方向分階段",
      "title": "人生方向不用一次選完，可以怎麼分階段整理？",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-LIFE-08、product=fortune、slug=life-direction-0008、title=人生方向不用一次選完，可以怎麼分階段整理？、primaryKeyword=人生方向分階段，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「人生方向分階段」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1174 字。 「人生方向分階段」正文小標高度模板化，實際小標包含「人生方向分階段真正要整理的是什麼？」、「人生方向分階段有哪些可觀察線索？」、「把人生方向分階段變成下一步」、「人生方向分階段不能代表什麼？」。 「人生方向分階段」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-02",
      "article_id": "THEME-WEALTH-08",
      "product": "fortune",
      "category": "wealth",
      "serial": "wealth-0008",
      "slug": "wealth-0008",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "財富與事業差別",
      "title": "財富和事業差在哪？一個看資源，一個看工作位置",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-WEALTH-08、product=fortune、slug=wealth-0008、title=財富和事業差在哪？一個看資源，一個看工作位置、primaryKeyword=財富與事業差別，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「財富與事業差別」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1166 字。 「財富與事業差別」正文小標高度模板化，實際小標包含「財富與事業差別真正要整理的是什麼？」、「財富與事業差別有哪些可觀察線索？」、「把財富與事業差別變成下一步」、「財富與事業差別不能代表什麼？」。 「財富與事業差別」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-03",
      "article_id": "THEME-INTERPERSONAL-08",
      "product": "personality",
      "category": "interpersonal",
      "serial": "interpersonal-0008",
      "slug": "interpersonal-0008",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "命盤人際課題",
      "title": "命盤怎麼看長期人際課題？把象徵轉成可核對的模式",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-INTERPERSONAL-08、product=personality、slug=interpersonal-0008、title=命盤怎麼看長期人際課題？把象徵轉成可核對的模式、primaryKeyword=命盤人際課題，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「命盤人際課題」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1146 字。 「命盤人際課題」正文小標高度模板化，實際小標包含「命盤人際課題真正要整理的是什麼？」、「命盤人際課題有哪些可觀察線索？」、「把命盤人際課題變成下一步」、「命盤人際課題不能代表什麼？」。 「命盤人際課題」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-04",
      "article_id": "THEME-LOVE-08",
      "product": "tarot",
      "category": "love",
      "serial": "love-0008",
      "slug": "love-0008",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "命盤感情模式",
      "title": "命盤怎麼看感情裡的長期模式？先理解傾向與現實差別",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-LOVE-08、product=tarot、slug=love-0008、title=命盤怎麼看感情裡的長期模式？先理解傾向與現實差別、primaryKeyword=命盤感情模式，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「命盤感情模式」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1140 字。 「命盤感情模式」正文小標高度模板化，實際小標包含「命盤感情模式真正要整理的是什麼？」、「命盤感情模式有哪些可觀察線索？」、「把命盤感情模式變成下一步」、「命盤感情模式不能代表什麼？」。 「命盤感情模式」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-05",
      "article_id": "ASTRO-SATURN-01",
      "product": "astro",
      "category": "astrology",
      "serial": "astrology-0009",
      "slug": "astrology-0009",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "土星星座",
      "title": "土星星座是什麼？責任、限制與成熟怎麼看",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=ASTRO-SATURN-01、product=astro、slug=astrology-0009、title=土星星座是什麼？責任、限制與成熟怎麼看、primaryKeyword=土星星座，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「土星星座」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1071 字。 「土星星座」正文小標高度模板化，實際小標包含「土星星座真正要整理的是什麼？」、「土星星座有哪些可觀察線索？」、「把土星星座變成下一步」、「土星星座不能代表什麼？」。 「土星星座」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    }
  ]
}
```

### THEME-LIFE-08 | life-direction-0008 | 人生方向不用一次選完，可以怎麼分階段整理？

- 不可變更欄位：product=fortune; category=life-direction; serial=life-direction-0008; slug=life-direction-0008; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-06
- 改寫 brief：
  - 保留 id=THEME-LIFE-08、product=fortune、slug=life-direction-0008、title=人生方向不用一次選完，可以怎麼分階段整理？、primaryKeyword=人生方向分階段，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「人生方向分階段」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1174 字。 「人生方向分階段」正文小標高度模板化，實際小標包含「人生方向分階段真正要整理的是什麼？」、「人生方向分階段有哪些可觀察線索？」、「把人生方向分階段變成下一步」、「人生方向分階段不能代表什麼？」。 「人生方向分階段」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-WEALTH-08 | wealth-0008 | 財富和事業差在哪？一個看資源，一個看工作位置

- 不可變更欄位：product=fortune; category=wealth; serial=wealth-0008; slug=wealth-0008; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-06
- 改寫 brief：
  - 保留 id=THEME-WEALTH-08、product=fortune、slug=wealth-0008、title=財富和事業差在哪？一個看資源，一個看工作位置、primaryKeyword=財富與事業差別，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「財富與事業差別」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1166 字。 「財富與事業差別」正文小標高度模板化，實際小標包含「財富與事業差別真正要整理的是什麼？」、「財富與事業差別有哪些可觀察線索？」、「把財富與事業差別變成下一步」、「財富與事業差別不能代表什麼？」。 「財富與事業差別」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-INTERPERSONAL-08 | interpersonal-0008 | 命盤怎麼看長期人際課題？把象徵轉成可核對的模式

- 不可變更欄位：product=personality; category=interpersonal; serial=interpersonal-0008; slug=interpersonal-0008; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-06
- 改寫 brief：
  - 保留 id=THEME-INTERPERSONAL-08、product=personality、slug=interpersonal-0008、title=命盤怎麼看長期人際課題？把象徵轉成可核對的模式、primaryKeyword=命盤人際課題，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「命盤人際課題」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1146 字。 「命盤人際課題」正文小標高度模板化，實際小標包含「命盤人際課題真正要整理的是什麼？」、「命盤人際課題有哪些可觀察線索？」、「把命盤人際課題變成下一步」、「命盤人際課題不能代表什麼？」。 「命盤人際課題」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-LOVE-08 | love-0008 | 命盤怎麼看感情裡的長期模式？先理解傾向與現實差別

- 不可變更欄位：product=tarot; category=love; serial=love-0008; slug=love-0008; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-06
- 改寫 brief：
  - 保留 id=THEME-LOVE-08、product=tarot、slug=love-0008、title=命盤怎麼看感情裡的長期模式？先理解傾向與現實差別、primaryKeyword=命盤感情模式，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「命盤感情模式」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1140 字。 「命盤感情模式」正文小標高度模板化，實際小標包含「命盤感情模式真正要整理的是什麼？」、「命盤感情模式有哪些可觀察線索？」、「把命盤感情模式變成下一步」、「命盤感情模式不能代表什麼？」。 「命盤感情模式」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### ASTRO-SATURN-01 | astrology-0009 | 土星星座是什麼？責任、限制與成熟怎麼看

- 不可變更欄位：product=astro; category=astrology; serial=astrology-0009; slug=astrology-0009; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-06
- 改寫 brief：
  - 保留 id=ASTRO-SATURN-01、product=astro、slug=astrology-0009、title=土星星座是什麼？責任、限制與成熟怎麼看、primaryKeyword=土星星座，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「土星星座」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1071 字。 「土星星座」正文小標高度模板化，實際小標包含「土星星座真正要整理的是什麼？」、「土星星座有哪些可觀察線索？」、「把土星星座變成下一步」、「土星星座不能代表什麼？」。 「土星星座」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

## Batch 7 | P0-batch-07

排序契約：priority -> serial 尾碼數字 -> product/category -> id；本批不得包含 KEEP。

可供 pipeline 包裝使用的 public brief：

```json
{
  "schema_version": 1,
  "run_id": "gemini_rewrite_audit_001_batch_07",
  "mode": "rewrite_existing_body",
  "sort_contract": "priority -> serial_suffix_number_ascending -> product/category -> id; do not include KEEP",
  "articles": [
    {
      "slot": "article-01",
      "article_id": "THEME-CAREER-09",
      "product": "fortune",
      "category": "career",
      "serial": "career-0009",
      "slug": "career-0009",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "職場人際卡住",
      "title": "主管同事關係不順，先看權責、溝通還是信任？",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-CAREER-09、product=fortune、slug=career-0009、title=主管同事關係不順，先看權責、溝通還是信任？、primaryKeyword=職場人際卡住，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「職場人際卡住」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1143 字。 「職場人際卡住」正文小標高度模板化，實際小標包含「職場人際卡住真正要整理的是什麼？」、「職場人際卡住有哪些可觀察線索？」、「把職場人際卡住變成下一步」、「職場人際卡住不能代表什麼？」。 「職場人際卡住」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-02",
      "article_id": "THEME-LIFE-09",
      "product": "fortune",
      "category": "life-direction",
      "serial": "life-direction-0009",
      "slug": "life-direction-0009",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "人生問題優先順序",
      "title": "感情、事業、人際、財富、方向，現在該先處理哪一個？",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-LIFE-09、product=fortune、slug=life-direction-0009、title=感情、事業、人際、財富、方向，現在該先處理哪一個？、primaryKeyword=人生問題優先順序，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「人生問題優先順序」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1184 字。 「人生問題優先順序」正文小標高度模板化，實際小標包含「人生問題優先順序真正要整理的是什麼？」、「人生問題優先順序有哪些可觀察線索？」、「把人生問題優先順序變成下一步」、「人生問題優先順序不能代表什麼？」。 「人生問題優先順序」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-03",
      "article_id": "THEME-WEALTH-09",
      "product": "fortune",
      "category": "wealth",
      "serial": "wealth-0009",
      "slug": "wealth-0009",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "人格花錢模式",
      "title": "人格特質怎麼影響花錢與冒險？看決策習慣，不貼標籤",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-WEALTH-09、product=fortune、slug=wealth-0009、title=人格特質怎麼影響花錢與冒險？看決策習慣，不貼標籤、primaryKeyword=人格花錢模式，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「人格花錢模式」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1142 字。 「人格花錢模式」正文小標高度模板化，實際小標包含「人格花錢模式真正要整理的是什麼？」、「人格花錢模式有哪些可觀察線索？」、「把人格花錢模式變成下一步」、「人格花錢模式不能代表什麼？」。 「人格花錢模式」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-04",
      "article_id": "THEME-INTERPERSONAL-09",
      "product": "personality",
      "category": "interpersonal",
      "serial": "interpersonal-0009",
      "slug": "interpersonal-0009",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "人群中的孤獨感",
      "title": "為什麼有人陪仍覺得孤獨？看連結品質，不只看人數",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-INTERPERSONAL-09、product=personality、slug=interpersonal-0009、title=為什麼有人陪仍覺得孤獨？看連結品質，不只看人數、primaryKeyword=人群中的孤獨感，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「人群中的孤獨感」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1168 字。 「人群中的孤獨感」正文小標高度模板化，實際小標包含「人群中的孤獨感真正要整理的是什麼？」、「人群中的孤獨感有哪些可觀察線索？」、「把人群中的孤獨感變成下一步」、「人群中的孤獨感不能代表什麼？」。 「人群中的孤獨感」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-05",
      "article_id": "THEME-LOVE-09",
      "product": "tarot",
      "category": "love",
      "serial": "love-0009",
      "slug": "love-0009",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "感情塔羅逆位",
      "title": "感情塔羅抽到逆位代表不好嗎？先看阻塞、過度與延遲",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-LOVE-09、product=tarot、slug=love-0009、title=感情塔羅抽到逆位代表不好嗎？先看阻塞、過度與延遲、primaryKeyword=感情塔羅逆位，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「感情塔羅逆位」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1139 字。 「感情塔羅逆位」正文小標高度模板化，實際小標包含「感情塔羅逆位真正要整理的是什麼？」、「感情塔羅逆位有哪些可觀察線索？」、「把感情塔羅逆位變成下一步」、「感情塔羅逆位不能代表什麼？」。 「感情塔羅逆位」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    }
  ]
}
```

### THEME-CAREER-09 | career-0009 | 主管同事關係不順，先看權責、溝通還是信任？

- 不可變更欄位：product=fortune; category=career; serial=career-0009; slug=career-0009; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-07
- 改寫 brief：
  - 保留 id=THEME-CAREER-09、product=fortune、slug=career-0009、title=主管同事關係不順，先看權責、溝通還是信任？、primaryKeyword=職場人際卡住，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「職場人際卡住」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1143 字。 「職場人際卡住」正文小標高度模板化，實際小標包含「職場人際卡住真正要整理的是什麼？」、「職場人際卡住有哪些可觀察線索？」、「把職場人際卡住變成下一步」、「職場人際卡住不能代表什麼？」。 「職場人際卡住」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-LIFE-09 | life-direction-0009 | 感情、事業、人際、財富、方向，現在該先處理哪一個？

- 不可變更欄位：product=fortune; category=life-direction; serial=life-direction-0009; slug=life-direction-0009; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-07
- 改寫 brief：
  - 保留 id=THEME-LIFE-09、product=fortune、slug=life-direction-0009、title=感情、事業、人際、財富、方向，現在該先處理哪一個？、primaryKeyword=人生問題優先順序，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「人生問題優先順序」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1184 字。 「人生問題優先順序」正文小標高度模板化，實際小標包含「人生問題優先順序真正要整理的是什麼？」、「人生問題優先順序有哪些可觀察線索？」、「把人生問題優先順序變成下一步」、「人生問題優先順序不能代表什麼？」。 「人生問題優先順序」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-WEALTH-09 | wealth-0009 | 人格特質怎麼影響花錢與冒險？看決策習慣，不貼標籤

- 不可變更欄位：product=fortune; category=wealth; serial=wealth-0009; slug=wealth-0009; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-07
- 改寫 brief：
  - 保留 id=THEME-WEALTH-09、product=fortune、slug=wealth-0009、title=人格特質怎麼影響花錢與冒險？看決策習慣，不貼標籤、primaryKeyword=人格花錢模式，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「人格花錢模式」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1142 字。 「人格花錢模式」正文小標高度模板化，實際小標包含「人格花錢模式真正要整理的是什麼？」、「人格花錢模式有哪些可觀察線索？」、「把人格花錢模式變成下一步」、「人格花錢模式不能代表什麼？」。 「人格花錢模式」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-INTERPERSONAL-09 | interpersonal-0009 | 為什麼有人陪仍覺得孤獨？看連結品質，不只看人數

- 不可變更欄位：product=personality; category=interpersonal; serial=interpersonal-0009; slug=interpersonal-0009; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-07
- 改寫 brief：
  - 保留 id=THEME-INTERPERSONAL-09、product=personality、slug=interpersonal-0009、title=為什麼有人陪仍覺得孤獨？看連結品質，不只看人數、primaryKeyword=人群中的孤獨感，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「人群中的孤獨感」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1168 字。 「人群中的孤獨感」正文小標高度模板化，實際小標包含「人群中的孤獨感真正要整理的是什麼？」、「人群中的孤獨感有哪些可觀察線索？」、「把人群中的孤獨感變成下一步」、「人群中的孤獨感不能代表什麼？」。 「人群中的孤獨感」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-LOVE-09 | love-0009 | 感情塔羅抽到逆位代表不好嗎？先看阻塞、過度與延遲

- 不可變更欄位：product=tarot; category=love; serial=love-0009; slug=love-0009; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-07
- 改寫 brief：
  - 保留 id=THEME-LOVE-09、product=tarot、slug=love-0009、title=感情塔羅抽到逆位代表不好嗎？先看阻塞、過度與延遲、primaryKeyword=感情塔羅逆位，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「感情塔羅逆位」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1139 字。 「感情塔羅逆位」正文小標高度模板化，實際小標包含「感情塔羅逆位真正要整理的是什麼？」、「感情塔羅逆位有哪些可觀察線索？」、「把感情塔羅逆位變成下一步」、「感情塔羅逆位不能代表什麼？」。 「感情塔羅逆位」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

## Batch 8 | P0-batch-08

排序契約：priority -> serial 尾碼數字 -> product/category -> id；本批不得包含 KEEP。

可供 pipeline 包裝使用的 public brief：

```json
{
  "schema_version": 1,
  "run_id": "gemini_rewrite_audit_001_batch_08",
  "mode": "rewrite_existing_body",
  "sort_contract": "priority -> serial_suffix_number_ascending -> product/category -> id; do not include KEEP",
  "articles": [
    {
      "slot": "article-01",
      "article_id": "ASTRO-HOUSES-01",
      "product": "astro",
      "category": "astrology",
      "serial": "astrology-0010",
      "slug": "astrology-0010",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "星盤宮位",
      "title": "星盤宮位是什麼？十二宮如何對應不同生活領域",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=ASTRO-HOUSES-01、product=astro、slug=astrology-0010、title=星盤宮位是什麼？十二宮如何對應不同生活領域、primaryKeyword=星盤宮位，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「星盤宮位」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1079 字。 「星盤宮位」正文小標高度模板化，實際小標包含「星盤宮位真正要整理的是什麼？」、「星盤宮位有哪些可觀察線索？」、「把星盤宮位變成下一步」、「星盤宮位不能代表什麼？」。 「星盤宮位」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-02",
      "article_id": "THEME-CAREER-10",
      "product": "fortune",
      "category": "career",
      "serial": "career-0010",
      "slug": "career-0010",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "職涯迷惘",
      "title": "職涯迷惘時，第一步不是找天職，而是縮小問題",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-CAREER-10、product=fortune、slug=career-0010、title=職涯迷惘時，第一步不是找天職，而是縮小問題、primaryKeyword=職涯迷惘，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「職涯迷惘」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1088 字。 「職涯迷惘」正文小標高度模板化，實際小標包含「職涯迷惘真正要整理的是什麼？」、「職涯迷惘有哪些可觀察線索？」、「把職涯迷惘變成下一步」、「職涯迷惘不能代表什麼？」。 「職涯迷惘」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-03",
      "article_id": "THEME-LIFE-10",
      "product": "fortune",
      "category": "life-direction",
      "serial": "life-direction-0010",
      "slug": "life-direction-0010",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "人生方向問題",
      "title": "人生方向問題怎麼問，才不會太空泛？",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-LIFE-10、product=fortune、slug=life-direction-0010、title=人生方向問題怎麼問，才不會太空泛？、primaryKeyword=人生方向問題，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「人生方向問題」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1121 字。 「人生方向問題」正文小標高度模板化，實際小標包含「人生方向問題真正要整理的是什麼？」、「人生方向問題有哪些可觀察線索？」、「把人生方向問題變成下一步」、「人生方向問題不能代表什麼？」。 「人生方向問題」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-04",
      "article_id": "THEME-WEALTH-10",
      "product": "fortune",
      "category": "wealth",
      "serial": "wealth-0010",
      "slug": "wealth-0010",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "金錢塔羅",
      "title": "塔羅可以怎麼整理短期金錢提醒？",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-WEALTH-10、product=fortune、slug=wealth-0010、title=塔羅可以怎麼整理短期金錢提醒？、primaryKeyword=金錢塔羅，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「金錢塔羅」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1070 字。 「金錢塔羅」正文小標高度模板化，實際小標包含「金錢塔羅真正要整理的是什麼？」、「金錢塔羅有哪些可觀察線索？」、「把金錢塔羅變成下一步」、「金錢塔羅不能代表什麼？」。 「金錢塔羅」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-05",
      "article_id": "THEME-INTERPERSONAL-10",
      "product": "personality",
      "category": "interpersonal",
      "serial": "interpersonal-0010",
      "slug": "interpersonal-0010",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "人際塔羅問題",
      "title": "人際問題怎麼問塔羅，才不會變成控制別人？",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-INTERPERSONAL-10、product=personality、slug=interpersonal-0010、title=人際問題怎麼問塔羅，才不會變成控制別人？、primaryKeyword=人際塔羅問題，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「人際塔羅問題」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1126 字。 「人際塔羅問題」正文小標高度模板化，實際小標包含「人際塔羅問題真正要整理的是什麼？」、「人際塔羅問題有哪些可觀察線索？」、「把人際塔羅問題變成下一步」、「人際塔羅問題不能代表什麼？」。 「人際塔羅問題」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    }
  ]
}
```

### ASTRO-HOUSES-01 | astrology-0010 | 星盤宮位是什麼？十二宮如何對應不同生活領域

- 不可變更欄位：product=astro; category=astrology; serial=astrology-0010; slug=astrology-0010; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-08
- 改寫 brief：
  - 保留 id=ASTRO-HOUSES-01、product=astro、slug=astrology-0010、title=星盤宮位是什麼？十二宮如何對應不同生活領域、primaryKeyword=星盤宮位，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「星盤宮位」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1079 字。 「星盤宮位」正文小標高度模板化，實際小標包含「星盤宮位真正要整理的是什麼？」、「星盤宮位有哪些可觀察線索？」、「把星盤宮位變成下一步」、「星盤宮位不能代表什麼？」。 「星盤宮位」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-CAREER-10 | career-0010 | 職涯迷惘時，第一步不是找天職，而是縮小問題

- 不可變更欄位：product=fortune; category=career; serial=career-0010; slug=career-0010; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-08
- 改寫 brief：
  - 保留 id=THEME-CAREER-10、product=fortune、slug=career-0010、title=職涯迷惘時，第一步不是找天職，而是縮小問題、primaryKeyword=職涯迷惘，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「職涯迷惘」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1088 字。 「職涯迷惘」正文小標高度模板化，實際小標包含「職涯迷惘真正要整理的是什麼？」、「職涯迷惘有哪些可觀察線索？」、「把職涯迷惘變成下一步」、「職涯迷惘不能代表什麼？」。 「職涯迷惘」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-LIFE-10 | life-direction-0010 | 人生方向問題怎麼問，才不會太空泛？

- 不可變更欄位：product=fortune; category=life-direction; serial=life-direction-0010; slug=life-direction-0010; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-08
- 改寫 brief：
  - 保留 id=THEME-LIFE-10、product=fortune、slug=life-direction-0010、title=人生方向問題怎麼問，才不會太空泛？、primaryKeyword=人生方向問題，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「人生方向問題」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1121 字。 「人生方向問題」正文小標高度模板化，實際小標包含「人生方向問題真正要整理的是什麼？」、「人生方向問題有哪些可觀察線索？」、「把人生方向問題變成下一步」、「人生方向問題不能代表什麼？」。 「人生方向問題」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-WEALTH-10 | wealth-0010 | 塔羅可以怎麼整理短期金錢提醒？

- 不可變更欄位：product=fortune; category=wealth; serial=wealth-0010; slug=wealth-0010; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-08
- 改寫 brief：
  - 保留 id=THEME-WEALTH-10、product=fortune、slug=wealth-0010、title=塔羅可以怎麼整理短期金錢提醒？、primaryKeyword=金錢塔羅，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「金錢塔羅」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1070 字。 「金錢塔羅」正文小標高度模板化，實際小標包含「金錢塔羅真正要整理的是什麼？」、「金錢塔羅有哪些可觀察線索？」、「把金錢塔羅變成下一步」、「金錢塔羅不能代表什麼？」。 「金錢塔羅」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-INTERPERSONAL-10 | interpersonal-0010 | 人際問題怎麼問塔羅，才不會變成控制別人？

- 不可變更欄位：product=personality; category=interpersonal; serial=interpersonal-0010; slug=interpersonal-0010; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-08
- 改寫 brief：
  - 保留 id=THEME-INTERPERSONAL-10、product=personality、slug=interpersonal-0010、title=人際問題怎麼問塔羅，才不會變成控制別人？、primaryKeyword=人際塔羅問題，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「人際塔羅問題」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1126 字。 「人際塔羅問題」正文小標高度模板化，實際小標包含「人際塔羅問題真正要整理的是什麼？」、「人際塔羅問題有哪些可觀察線索？」、「把人際塔羅問題變成下一步」、「人際塔羅問題不能代表什麼？」。 「人際塔羅問題」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

## Batch 9 | P0-batch-09

排序契約：priority -> serial 尾碼數字 -> product/category -> id；本批不得包含 KEEP。

可供 pipeline 包裝使用的 public brief：

```json
{
  "schema_version": 1,
  "run_id": "gemini_rewrite_audit_001_batch_09",
  "mode": "rewrite_existing_body",
  "sort_contract": "priority -> serial_suffix_number_ascending -> product/category -> id; do not include KEEP",
  "articles": [
    {
      "slot": "article-01",
      "article_id": "THEME-LOVE-10",
      "product": "tarot",
      "category": "love",
      "serial": "love-0010",
      "slug": "love-0010",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "主動等待放下",
      "title": "感情裡該主動、等待還是放下？用三種成本做選擇",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-LOVE-10、product=tarot、slug=love-0010、title=感情裡該主動、等待還是放下？用三種成本做選擇、primaryKeyword=主動等待放下，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「主動等待放下」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1129 字。 「主動等待放下」正文小標高度模板化，實際小標包含「主動等待放下真正要整理的是什麼？」、「主動等待放下有哪些可觀察線索？」、「把主動等待放下變成下一步」、「主動等待放下不能代表什麼？」。 「主動等待放下」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-02",
      "article_id": "THEME-CAREER-11",
      "product": "fortune",
      "category": "career",
      "serial": "career-0011",
      "slug": "career-0011",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "工作塔羅問題",
      "title": "工作問題怎麼問塔羅？把預測題改成可行動的問題",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-CAREER-11、product=fortune、slug=career-0011、title=工作問題怎麼問塔羅？把預測題改成可行動的問題、primaryKeyword=工作塔羅問題，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「工作塔羅問題」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1131 字。 「工作塔羅問題」正文小標高度模板化，實際小標包含「工作塔羅問題真正要整理的是什麼？」、「工作塔羅問題有哪些可觀察線索？」、「把工作塔羅問題變成下一步」、「工作塔羅問題不能代表什麼？」。 「工作塔羅問題」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-03",
      "article_id": "THEME-LIFE-11",
      "product": "fortune",
      "category": "life-direction",
      "serial": "life-direction-0011",
      "slug": "life-direction-0011",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "年度人生方向報告",
      "title": "年度人生方向報告適合看什麼？用主題追蹤變化",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-LIFE-11、product=fortune、slug=life-direction-0011、title=年度人生方向報告適合看什麼？用主題追蹤變化、primaryKeyword=年度人生方向報告，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「年度人生方向報告」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1191 字。 「年度人生方向報告」正文小標高度模板化，實際小標包含「年度人生方向報告真正要整理的是什麼？」、「年度人生方向報告有哪些可觀察線索？」、「把年度人生方向報告變成下一步」、「年度人生方向報告不能代表什麼？」。 「年度人生方向報告」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-04",
      "article_id": "THEME-WEALTH-11",
      "product": "fortune",
      "category": "wealth",
      "serial": "wealth-0011",
      "slug": "wealth-0011",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "金錢命理問法",
      "title": "財富問題最不該怎麼問？避開必中、翻倍與讀心",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-WEALTH-11、product=fortune、slug=wealth-0011、title=財富問題最不該怎麼問？避開必中、翻倍與讀心、primaryKeyword=金錢命理問法，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「金錢命理問法」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1117 字。 「金錢命理問法」正文小標高度模板化，實際小標包含「金錢命理問法真正要整理的是什麼？」、「金錢命理問法有哪些可觀察線索？」、「把金錢命理問法變成下一步」、「金錢命理問法不能代表什麼？」。 「金錢命理問法」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-05",
      "article_id": "THEME-INTERPERSONAL-11",
      "product": "personality",
      "category": "interpersonal",
      "serial": "interpersonal-0011",
      "slug": "interpersonal-0011",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "社群角色與人格",
      "title": "社群裡總扮演同一個角色？用人格偏好看分工與壓力",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-INTERPERSONAL-11、product=personality、slug=interpersonal-0011、title=社群裡總扮演同一個角色？用人格偏好看分工與壓力、primaryKeyword=社群角色與人格，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「社群角色與人格」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1175 字。 「社群角色與人格」正文小標高度模板化，實際小標包含「社群角色與人格真正要整理的是什麼？」、「社群角色與人格有哪些可觀察線索？」、「把社群角色與人格變成下一步」、「社群角色與人格不能代表什麼？」。 「社群角色與人格」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    }
  ]
}
```

### THEME-LOVE-10 | love-0010 | 感情裡該主動、等待還是放下？用三種成本做選擇

- 不可變更欄位：product=tarot; category=love; serial=love-0010; slug=love-0010; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-09
- 改寫 brief：
  - 保留 id=THEME-LOVE-10、product=tarot、slug=love-0010、title=感情裡該主動、等待還是放下？用三種成本做選擇、primaryKeyword=主動等待放下，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「主動等待放下」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1129 字。 「主動等待放下」正文小標高度模板化，實際小標包含「主動等待放下真正要整理的是什麼？」、「主動等待放下有哪些可觀察線索？」、「把主動等待放下變成下一步」、「主動等待放下不能代表什麼？」。 「主動等待放下」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-CAREER-11 | career-0011 | 工作問題怎麼問塔羅？把預測題改成可行動的問題

- 不可變更欄位：product=fortune; category=career; serial=career-0011; slug=career-0011; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-09
- 改寫 brief：
  - 保留 id=THEME-CAREER-11、product=fortune、slug=career-0011、title=工作問題怎麼問塔羅？把預測題改成可行動的問題、primaryKeyword=工作塔羅問題，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「工作塔羅問題」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1131 字。 「工作塔羅問題」正文小標高度模板化，實際小標包含「工作塔羅問題真正要整理的是什麼？」、「工作塔羅問題有哪些可觀察線索？」、「把工作塔羅問題變成下一步」、「工作塔羅問題不能代表什麼？」。 「工作塔羅問題」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-LIFE-11 | life-direction-0011 | 年度人生方向報告適合看什麼？用主題追蹤變化

- 不可變更欄位：product=fortune; category=life-direction; serial=life-direction-0011; slug=life-direction-0011; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-09
- 改寫 brief：
  - 保留 id=THEME-LIFE-11、product=fortune、slug=life-direction-0011、title=年度人生方向報告適合看什麼？用主題追蹤變化、primaryKeyword=年度人生方向報告，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「年度人生方向報告」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1191 字。 「年度人生方向報告」正文小標高度模板化，實際小標包含「年度人生方向報告真正要整理的是什麼？」、「年度人生方向報告有哪些可觀察線索？」、「把年度人生方向報告變成下一步」、「年度人生方向報告不能代表什麼？」。 「年度人生方向報告」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-WEALTH-11 | wealth-0011 | 財富問題最不該怎麼問？避開必中、翻倍與讀心

- 不可變更欄位：product=fortune; category=wealth; serial=wealth-0011; slug=wealth-0011; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-09
- 改寫 brief：
  - 保留 id=THEME-WEALTH-11、product=fortune、slug=wealth-0011、title=財富問題最不該怎麼問？避開必中、翻倍與讀心、primaryKeyword=金錢命理問法，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「金錢命理問法」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1117 字。 「金錢命理問法」正文小標高度模板化，實際小標包含「金錢命理問法真正要整理的是什麼？」、「金錢命理問法有哪些可觀察線索？」、「把金錢命理問法變成下一步」、「金錢命理問法不能代表什麼？」。 「金錢命理問法」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-INTERPERSONAL-11 | interpersonal-0011 | 社群裡總扮演同一個角色？用人格偏好看分工與壓力

- 不可變更欄位：product=personality; category=interpersonal; serial=interpersonal-0011; slug=interpersonal-0011; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-09
- 改寫 brief：
  - 保留 id=THEME-INTERPERSONAL-11、product=personality、slug=interpersonal-0011、title=社群裡總扮演同一個角色？用人格偏好看分工與壓力、primaryKeyword=社群角色與人格，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「社群角色與人格」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1175 字。 「社群角色與人格」正文小標高度模板化，實際小標包含「社群角色與人格真正要整理的是什麼？」、「社群角色與人格有哪些可觀察線索？」、「把社群角色與人格變成下一步」、「社群角色與人格不能代表什麼？」。 「社群角色與人格」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

## Batch 10 | P0-batch-10

排序契約：priority -> serial 尾碼數字 -> product/category -> id；本批不得包含 KEEP。

可供 pipeline 包裝使用的 public brief：

```json
{
  "schema_version": 1,
  "run_id": "gemini_rewrite_audit_001_batch_10",
  "mode": "rewrite_existing_body",
  "sort_contract": "priority -> serial_suffix_number_ascending -> product/category -> id; do not include KEEP",
  "articles": [
    {
      "slot": "article-01",
      "article_id": "THEME-LOVE-11",
      "product": "tarot",
      "category": "love",
      "serial": "love-0011",
      "slug": "love-0011",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "感情直覺與焦慮",
      "title": "如何分辨感情直覺和焦慮？看訊息來源與身體反應",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-LOVE-11、product=tarot、slug=love-0011、title=如何分辨感情直覺和焦慮？看訊息來源與身體反應、primaryKeyword=感情直覺與焦慮，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「感情直覺與焦慮」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1166 字。 「感情直覺與焦慮」正文小標高度模板化，實際小標包含「感情直覺與焦慮真正要整理的是什麼？」、「感情直覺與焦慮有哪些可觀察線索？」、「把感情直覺與焦慮變成下一步」、「感情直覺與焦慮不能代表什麼？」。 「感情直覺與焦慮」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-02",
      "article_id": "THEME-CAREER-12",
      "product": "fortune",
      "category": "career",
      "serial": "career-0012",
      "slug": "career-0012",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "年度事業報告",
      "title": "年度事業報告該看什麼？用季度節點整理工作計畫",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-CAREER-12、product=fortune、slug=career-0012、title=年度事業報告該看什麼？用季度節點整理工作計畫、primaryKeyword=年度事業報告，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「年度事業報告」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1144 字。 「年度事業報告」正文小標高度模板化，實際小標包含「年度事業報告真正要整理的是什麼？」、「年度事業報告有哪些可觀察線索？」、「把年度事業報告變成下一步」、「年度事業報告不能代表什麼？」。 「年度事業報告」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-03",
      "article_id": "THEME-LIFE-12",
      "product": "fortune",
      "category": "life-direction",
      "serial": "life-direction-0012",
      "slug": "life-direction-0012",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "完整命書與小報告",
      "title": "完整命書和主題小報告差在哪？先看問題範圍",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-LIFE-12、product=fortune、slug=life-direction-0012、title=完整命書和主題小報告差在哪？先看問題範圍、primaryKeyword=完整命書與小報告，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「完整命書與小報告」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1187 字。 「完整命書與小報告」正文小標高度模板化，實際小標包含「完整命書與小報告真正要整理的是什麼？」、「完整命書與小報告有哪些可觀察線索？」、「把完整命書與小報告變成下一步」、「完整命書與小報告不能代表什麼？」。 「完整命書與小報告」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-04",
      "article_id": "THEME-WEALTH-12",
      "product": "fortune",
      "category": "wealth",
      "serial": "wealth-0012",
      "slug": "wealth-0012",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "財富小報告",
      "title": "財富小報告怎麼設計才有用？聚焦一個決策週期",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-WEALTH-12、product=fortune、slug=wealth-0012、title=財富小報告怎麼設計才有用？聚焦一個決策週期、primaryKeyword=財富小報告，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「財富小報告」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1086 字。 「財富小報告」正文小標高度模板化，實際小標包含「財富小報告真正要整理的是什麼？」、「財富小報告有哪些可觀察線索？」、「把財富小報告變成下一步」、「財富小報告不能代表什麼？」。 「財富小報告」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    },
    {
      "slot": "article-05",
      "article_id": "THEME-INTERPERSONAL-12",
      "product": "personality",
      "category": "interpersonal",
      "serial": "interpersonal-0012",
      "slug": "interpersonal-0012",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "人際主題報告",
      "title": "人際主題報告適合看什麼？從互動模式到界線練習",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-INTERPERSONAL-12、product=personality、slug=interpersonal-0012、title=人際主題報告適合看什麼？從互動模式到界線練習、primaryKeyword=人際主題報告，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「人際主題報告」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1126 字。 「人際主題報告」正文小標高度模板化，實際小標包含「人際主題報告真正要整理的是什麼？」、「人際主題報告有哪些可觀察線索？」、「把人際主題報告變成下一步」、「人際主題報告不能代表什麼？」。 「人際主題報告」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    }
  ]
}
```

### THEME-LOVE-11 | love-0011 | 如何分辨感情直覺和焦慮？看訊息來源與身體反應

- 不可變更欄位：product=tarot; category=love; serial=love-0011; slug=love-0011; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-10
- 改寫 brief：
  - 保留 id=THEME-LOVE-11、product=tarot、slug=love-0011、title=如何分辨感情直覺和焦慮？看訊息來源與身體反應、primaryKeyword=感情直覺與焦慮，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「感情直覺與焦慮」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1166 字。 「感情直覺與焦慮」正文小標高度模板化，實際小標包含「感情直覺與焦慮真正要整理的是什麼？」、「感情直覺與焦慮有哪些可觀察線索？」、「把感情直覺與焦慮變成下一步」、「感情直覺與焦慮不能代表什麼？」。 「感情直覺與焦慮」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-CAREER-12 | career-0012 | 年度事業報告該看什麼？用季度節點整理工作計畫

- 不可變更欄位：product=fortune; category=career; serial=career-0012; slug=career-0012; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-10
- 改寫 brief：
  - 保留 id=THEME-CAREER-12、product=fortune、slug=career-0012、title=年度事業報告該看什麼？用季度節點整理工作計畫、primaryKeyword=年度事業報告，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「年度事業報告」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1144 字。 「年度事業報告」正文小標高度模板化，實際小標包含「年度事業報告真正要整理的是什麼？」、「年度事業報告有哪些可觀察線索？」、「把年度事業報告變成下一步」、「年度事業報告不能代表什麼？」。 「年度事業報告」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-LIFE-12 | life-direction-0012 | 完整命書和主題小報告差在哪？先看問題範圍

- 不可變更欄位：product=fortune; category=life-direction; serial=life-direction-0012; slug=life-direction-0012; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-10
- 改寫 brief：
  - 保留 id=THEME-LIFE-12、product=fortune、slug=life-direction-0012、title=完整命書和主題小報告差在哪？先看問題範圍、primaryKeyword=完整命書與小報告，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「完整命書與小報告」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1187 字。 「完整命書與小報告」正文小標高度模板化，實際小標包含「完整命書與小報告真正要整理的是什麼？」、「完整命書與小報告有哪些可觀察線索？」、「把完整命書與小報告變成下一步」、「完整命書與小報告不能代表什麼？」。 「完整命書與小報告」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-WEALTH-12 | wealth-0012 | 財富小報告怎麼設計才有用？聚焦一個決策週期

- 不可變更欄位：product=fortune; category=wealth; serial=wealth-0012; slug=wealth-0012; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-10
- 改寫 brief：
  - 保留 id=THEME-WEALTH-12、product=fortune、slug=wealth-0012、title=財富小報告怎麼設計才有用？聚焦一個決策週期、primaryKeyword=財富小報告，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「財富小報告」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1086 字。 「財富小報告」正文小標高度模板化，實際小標包含「財富小報告真正要整理的是什麼？」、「財富小報告有哪些可觀察線索？」、「把財富小報告變成下一步」、「財富小報告不能代表什麼？」。 「財富小報告」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

### THEME-INTERPERSONAL-12 | interpersonal-0012 | 人際主題報告適合看什麼？從互動模式到界線練習

- 不可變更欄位：product=personality; category=interpersonal; serial=interpersonal-0012; slug=interpersonal-0012; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-10
- 改寫 brief：
  - 保留 id=THEME-INTERPERSONAL-12、product=personality、slug=interpersonal-0012、title=人際主題報告適合看什麼？從互動模式到界線練習、primaryKeyword=人際主題報告，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「人際主題報告」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1126 字。 「人際主題報告」正文小標高度模板化，實際小標包含「人際主題報告真正要整理的是什麼？」、「人際主題報告有哪些可觀察線索？」、「把人際主題報告變成下一步」、「人際主題報告不能代表什麼？」。 「人際主題報告」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。

## Batch 11 | P0-batch-11

排序契約：priority -> serial 尾碼數字 -> product/category -> id；本批不得包含 KEEP。

可供 pipeline 包裝使用的 public brief：

```json
{
  "schema_version": 1,
  "run_id": "gemini_rewrite_audit_001_batch_11",
  "mode": "rewrite_existing_body",
  "sort_contract": "priority -> serial_suffix_number_ascending -> product/category -> id; do not include KEEP",
  "articles": [
    {
      "slot": "article-01",
      "article_id": "THEME-LOVE-12",
      "product": "tarot",
      "category": "love",
      "serial": "love-0012",
      "slug": "love-0012",
      "source_file": "app/web/static/article-registry.js",
      "body_source": "app/web/static/article-expansion-50.js",
      "primaryKeyword": "感情主題報告",
      "title": "感情主題報告適合看什麼？先確認資料、問題與邊界",
      "verdict": "GEMINI_REWRITE",
      "issue_codes": [
        "TEMPLATE_STRUCTURE",
        "REPEATED_BATCH_COPY"
      ],
      "brief": [
        "保留 id=THEME-LOVE-12、product=tarot、slug=love-0012、title=感情主題報告適合看什麼？先確認資料、問題與邊界、primaryKeyword=感情主題報告，不得改 URL/serial/date/metadata。",
        "重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「感情主題報告」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。",
        "專屬證據：app/web/static/article-expansion-50.js，正文 1147 字。 「感情主題報告」正文小標高度模板化，實際小標包含「感情主題報告真正要整理的是什麼？」、「感情主題報告有哪些可觀察線索？」、「把感情主題報告變成下一步」、「感情主題報告不能代表什麼？」。 「感情主題報告」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。"
      ]
    }
  ]
}
```

### THEME-LOVE-12 | love-0012 | 感情主題報告適合看什麼？先確認資料、問題與邊界

- 不可變更欄位：product=tarot; category=love; serial=love-0012; slug=love-0012; source_file=app/web/static/article-registry.js; body_source=app/web/static/article-expansion-50.js
- Gemini batch：P0-batch-11
- 改寫 brief：
  - 保留 id=THEME-LOVE-12、product=tarot、slug=love-0012、title=感情主題報告適合看什麼？先確認資料、問題與邊界、primaryKeyword=感情主題報告，不得改 URL/serial/date/metadata。
  - 重寫方向：先用搜尋者正在卡住的具體場景開場，前 80 字回答「感情主題報告」；重建 3-5 個 H2，至少兩個專屬生活場景、兩個可觀察動詞、一段不能代表什麼。
  - 專屬證據：app/web/static/article-expansion-50.js，正文 1147 字。 「感情主題報告」正文小標高度模板化，實際小標包含「感情主題報告真正要整理的是什麼？」、「感情主題報告有哪些可觀察線索？」、「把感情主題報告變成下一步」、「感情主題報告不能代表什麼？」。 「感情主題報告」使用「核心不是找一句立刻生效的答案」或「公開文章能提供整理框架」這類批次完整句型。
