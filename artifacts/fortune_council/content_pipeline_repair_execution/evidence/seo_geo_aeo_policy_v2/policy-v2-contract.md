# Pantheon Article Publication Policy v2 Contract

- Policy version: `pantheon-article-publication-v2.0.0`
- Effective date: `2026-07-25`
- Source commit: `162f5668ffa9b2c79bca6ec29069b7889d088de0`
- Scope: create、rewrite、publisher apply、prerender acceptance 與 migration audit。

## Level contract

- `required`: 發布前 fail closed；一般 override 不得放行。
- `recommended`: 有官方或產品理由，但不保證排名、索引、rich result 或 citation。
- `measured`: 只能由 GSC、Bing 或分析證據驗證；本地 validator 不得自證。
- `migration_only`: 只建立舊文 repair queue，不等同 published、accepted 或 required pass。

## Shared validator contract

Create 與 rewrite candidate 都必須帶 `publicationPolicy`，並由
`scripts/agy_seo_copy_pipeline.py` 的同版 loader 與 validator 驗證。Publisher 重新執行
required gate，記錄 `policy_version`、`validator_result`、article IDs、failure codes 與 input
hash；policy rejection 是 terminal content state，`retry_eligible=false`。Prerender acceptance
驗證 initial HTML、可見正文／answer／FAQ、Article 與 FAQ JSON-LD、author identity、日期與
canonical 一致性。

## Audit contract

全量 audit 是唯讀、deterministic 的 migration inventory；不得修改 registry、文章內容、
sitemap、feed、redirects 或生成頁。`migration_count` 只表示現有 artifact 尚未通過 v2，
不代表文章品質判決或外部搜尋成效。
