# Pantheon Release Log

每次正式文章發布都必須同步更新 `pyproject.toml`、`package.json` 與本檔，並以同版本 annotated tag 指向 release commit。

## [0.2.0] - 2026-07-20

- Release tag：`v0.2.0`
- 公開文章總數：352
- 發布範圍：整合 Venus 補充文章與 Article Expansion 50E，新增 52 篇公開文章；保留 Gemini rewrite release cache 契約。
- 發布 commits：`90c5860`、`b6742f9`、`6087cdb`、`f7a5fb2`、`98fd144`
- 驗證：177 tests passed；352 個 article ID、slug 與公開路徑皆唯一；prerender 生成器冪等；`git diff --check` 通過。
- 證據：`artifacts/fortune_council/content_seo_execution/evidence/article_expansion_50e/`
