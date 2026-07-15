# CARD-CONTENT-REWRITE-001｜停止泛用段落自動附加

## 任務ID / 卡片類型｜派工對象

`CARD-CONTENT-REWRITE-001` / implementation｜gpt-5.5

## 請讀

- `docs/pantheon_article_publication_standard.md`
- `app/web/static/article-meta.js`
- `app/web/static/article-registry.js`
- `artifacts/fortune_council/content_rewrite_execution/CARD-CONTENT-REWRITE-000-master-plan.md`

## 任務目的

修正 `enrichArticleBody()` 與 fallback body 契約，讓完成的文章正文不再被自動追加重複的搜尋意圖、情境、限制與下一步段落。

## 允許修改

- `app/web/static/article-meta.js`
- 受影響的 web tests
- `artifacts/fortune_council/content_rewrite_execution/evidence/runtime/`

## 禁止修改

- HTML 結構、CSS、版面、URL、Schema 欄位名稱。
- 不批量改文章正文；正文由後續內容卡負責。

## 驗收條件

- 有明確的 custom body / fallback body 行為契約。
- 完整 custom body 不再自動重複追加泛用段落。
- fallback 仍能輸出最小可讀文章，不產生站方管理語言或固定免責堆疊。
- 現有文章 SEO metadata、FAQ、related links 與 policy 測試不回歸。

## 驗證與證據

```text
pytest tests/test_web.py
git diff --check
```

證據：`artifacts/fortune_council/content_rewrite_execution/evidence/runtime/`

## 停損

若需要改版面或改公開 URL，立即退回主線，不自行擴大範圍。
