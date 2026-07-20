# 最新文章頁日期參數化

## 目的

讓 `/articles` 的發布日期與最後更新日期由單一後端參數注入，避免可見文字、Open Graph 與 Schema.org 日期各自硬編碼而失去同步。

## 可修改

- `main.py`
- `app/web/articles.html`
- `tests/test_web.py`
- `scripts/update_articles_hub_dates.py`

## 禁止範圍

- 不修改文章內容、文章 registry、圖片或其他頁面設計。
- 不改動個別文章既有的發布／更新日期規則。

## 驗證

- `/articles` 可見日期、`article:*_time` 與 `CollectionPage` Schema 使用同一組參數值。
- 模板不再含舊的硬編碼日期。
- 受影響測試、完整測試與 `git diff --check` 通過。

## 交付

- 最小差異 commit，推送目前分支。
