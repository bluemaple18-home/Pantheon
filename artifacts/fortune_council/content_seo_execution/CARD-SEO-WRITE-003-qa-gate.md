# CARD-SEO-WRITE-003｜文章上稿 QA Gate

## 任務目的

建立每篇文章上稿前的 SEO / AEO / GEO / 內容邊界檢查表，避免大量撰文後品質失控。

## 請讀

- `docs/pantheon_article_publication_standard.md`
- `docs/competitor_seo_tool.md`
- `app/web/static/article-registry.js`
- `app/web/static/article-seo.js`

## 必交付

產出 QA gate 文件：

```text
artifacts/fortune_council/content_seo_execution/evidence/qa_gate/article_qa_gate.md
```

## 檢查項目

每篇文章至少檢查：

- H1 有主攻關鍵字。
- 第一段前 80 字有主攻關鍵字。
- 前 150 字直接回答搜尋問題。
- 有 50 字內 answer。
- meta description 70-95 字，且有情境與限制。
- 至少 2 個 H2 放次要關鍵字。
- FAQ 3-5 題。
- 有公開文章邊界。
- 有產品線入口、五大情境入口、同分類、跨分類內鏈。
- CTA 合理，不硬賣。
- 不含保證、恐嚇、醫療、法律、投資建議。
- 可轉成 Article JSON-LD、FAQPage、BreadcrumbList。

## 加分項

- 有一段適合被 AI 搜尋引用的 120-150 字完整答案。
- 有表格或條列幫助掃讀。
- 標題可讀，但沒有誇大承諾。
- 內鏈錨文字使用關鍵字。

## 驗收條件

- QA 文件可以直接拿來逐篇打勾。
- 能區分 blocker / warning / pass。
- 能回扣 Pantheon 現有 `auditArticleVoice` 概念。

## 證據路徑

- `artifacts/fortune_council/content_seo_execution/evidence/qa_gate/`
