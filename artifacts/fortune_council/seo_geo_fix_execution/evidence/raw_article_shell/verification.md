# CARD-SEO-GEO-INFRA-002 Verification

狀態：`GO (local)`；`PARTIAL (live pending deploy)`

## 驗證命令

```bash
.venv/bin/python -m py_compile main.py scripts/competitor_seo_tool.py
.venv/bin/python -m pytest tests/test_web.py tests/test_competitor_seo_tool.py
.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8799
.venv/bin/python scripts/competitor_seo_tool.py --own-site-url http://127.0.0.1:8799 --own-name PantheonLocal --site-url https://news.click108.com.tw --name Click108 --since 2024-07-10 --max-feed-pages 2 --max-category-pages 1 --sample-limit 5 --out-dir output/competitor_seo/local_vs_click108
```

## 結果

- `py_compile`：pass
- `pytest tests/test_web.py tests/test_competitor_seo_tool.py`：36 passed, 1 existing deprecation warning
- 本機 audit：`output/competitor_seo/local_vs_click108/own_site/seo_audit.md`
- Schema depth：100
- E-E-A-T：100
- Citability：84
- Entity：100
- 文章頁 JSON-LD：`Organization`、`WebSite`、`Article`、`BreadcrumbList`、`FAQPage`
- 文章頁 canonical：已對應到各 article URL
- JSON-LD `parse_error`：未出現

## 修正內容

- `main.py` 新增 server-side article SEO shell。
- `/articles/{product}`、`/articles/{product}/{slug}`、`/articles/intents/{intent}`、`/topics/{topic}` 改回 HTMLResponse，注入 raw title / description / canonical / JSON-LD。
- 重要 feed article path 先建立 raw metadata，避免 no-JS audit 只看到 generic `最新文章`。
- `tests/test_web.py` 新增 raw article shell 合約測試。

## 證據檔

- `artifacts/fortune_council/seo_geo_fix_execution/evidence/raw_article_shell/local_own_site_seo_audit.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/raw_article_shell/local_comparison.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/raw_article_shell/local_own_site_competitor_audit.json`

## 限制

- 此次驗收為本機 `http://127.0.0.1:8799`。
- `https://mysticpantheon.com` 需部署後再跑 live audit，才可宣稱 production raw article shell 已更新。
- 目前 raw metadata 先覆蓋 feed 裡的核心文章；全量文章 metadata manifest 可列為後續基礎工程。
