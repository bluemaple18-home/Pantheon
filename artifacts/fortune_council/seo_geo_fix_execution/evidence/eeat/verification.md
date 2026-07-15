# CARD-SEO-GEO-FIX-003 Verification

狀態：`GO (local)`；`PARTIAL (live pending deploy)`

## 驗證命令

```bash
.venv/bin/python -m py_compile scripts/competitor_seo_tool.py
.venv/bin/python -m pytest tests/test_web.py tests/test_competitor_seo_tool.py
.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8799
.venv/bin/python scripts/competitor_seo_tool.py --own-site-url http://127.0.0.1:8799 --own-name PantheonLocal --site-url https://news.click108.com.tw --name Click108 --since 2024-07-10 --max-feed-pages 2 --max-category-pages 1 --sample-limit 5 --out-dir output/competitor_seo/local_vs_click108
```

## 結果

- `py_compile`：pass
- `pytest tests/test_web.py tests/test_competitor_seo_tool.py`：32 passed, 1 existing deprecation warning
- 本機 audit：`output/competitor_seo/local_vs_click108/own_site/seo_audit.md`
- PantheonLocal E-E-A-T score：100
- PantheonLocal page flags：`author=True published=True modified=True about_contact=True`
- PantheonLocal 外鏈數：1
- 對 Click108 比較：PantheonLocal E-E-A-T 100，Click108 64

## 證據檔

- `artifacts/fortune_council/seo_geo_fix_execution/evidence/eeat/local_own_site_seo_audit.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/eeat/local_comparison.md`

## 限制

- 此次驗收為本機 `http://127.0.0.1:8799`。
- `https://mysticpantheon.com` 需部署後再跑 live audit，才可宣稱 production 分數已更新。
