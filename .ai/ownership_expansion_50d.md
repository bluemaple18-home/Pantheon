# Ownership Matrix｜Article Expansion 50D

| Card | Owner | Allowlist | Forbidden shared scope | Verification |
|---|---|---|---|---|
| `CARD-EXPANSION-50D-MBTI` | visible implementation thread | `app/web/static/article-expansion-50d-mbti.js`; `artifacts/fortune_council/content_seo_execution/evidence/article_expansion_50d/mbti.json` | registry、meta、HTML、Python、tests、生成頁、sitemap、feed、redirects | 16 records/bodies、唯一性、內容 gate、`node --check`、JSON、diff check |
| `CARD-EXPANSION-50D-ASTRO` | visible implementation thread | `app/web/static/article-expansion-50d-astro.js`; `artifacts/fortune_council/content_seo_execution/evidence/article_expansion_50d/astro.json` | registry、meta、HTML、Python、tests、生成頁、sitemap、feed、redirects | 17 records/bodies、唯一性、內容 gate、`node --check`、JSON、diff check |
| `CARD-EXPANSION-50D-FORTUNE` | visible implementation thread | `app/web/static/article-expansion-50d-fortune.js`; `artifacts/fortune_council/content_seo_execution/evidence/article_expansion_50d/fortune.json` | registry、meta、HTML、Python、tests、生成頁、sitemap、feed、redirects | 17 records/bodies、唯一性、內容 gate、`node --check`、JSON、diff check |
| `CARD-EXPANSION-50D-INTEGRATE-LATEST` | mainline | registry、meta、cache chain、route/date、tests、generated SEO artifacts、latest ordering、final evidence | 三個 candidate modules 的文章正文（除驗收退卡外不得改） | 跨卡 gate、279 total、完整 pytest、generator、diff check、browser acceptance |

## Integration dependency

主線只能在三張內容卡都有 candidate commit、獨立 review `GO` 且主線重算通過後，開始共享整合。
