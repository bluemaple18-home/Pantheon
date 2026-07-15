# CARD-CONTENT-REWRITE-003｜塔羅基礎與牌義文章重寫

## 任務ID / 卡片類型｜派工對象

`CARD-CONTENT-REWRITE-003` / content rewrite｜gpt-5.5

## 請讀

- `docs/pantheon_article_publication_standard.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/tool_hardening/click108_seo_audit.md`
- `app/web/static/article-registry.js`
- `app/web/static/article-bodies-second-batch.js`
- `app/web/static/article-bodies-next-30.js`
- `app/web/static/article-bodies-scale-44.js`

## 文章範圍

- 塔羅牌意思總覽
- 塔羅牌正位逆位
- 已收錄的 22 張大牌文章
- 已收錄的小牌文章先處理共用段落與最明顯模板句，再依批次補完

## 任務目的

把「牌義定義」改成「牌義如何出現在感情、工作或選擇卡住的場景」，不把文章寫成塔羅課程，也不把正逆位直接翻成好壞結果。

## 驗收條件

- 每篇先回答牌名／正逆位搜尋問題。
- 至少一個牌義專屬生活場景；情境型文章至少兩個。
- 牌義使用具體動詞，例如試探、等待、收尾、拒絕、推進、補資源。
- 逆位描述阻塞、過度或未完成狀態，不寫成固定壞事。
- 感情、工作段落有實際條件；限制附在解釋後。
- FAQ 3-5 題，避免「依個人情況而定」空答。

## 驗證與證據

執行文章 QA gate、`tests/test_web.py`、`git diff --check`；輸出文章清單與逐篇結果。

證據：`artifacts/fortune_council/content_rewrite_execution/evidence/tarot/`
