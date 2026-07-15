# CARD-SEO-GEO-INFRA-001 Verification

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
- `pytest tests/test_web.py tests/test_competitor_seo_tool.py`：35 passed, 1 existing deprecation warning
- 本機 audit：`output/competitor_seo/local_vs_click108/own_site/seo_audit.md`
- `feed`：present
- `llms_txt`：present / `valid_llms_txt`
- `ai_txt`：present / `valid_ai_txt`
- Score：Schema depth 80、E-E-A-T 100、Citability 68、Entity 100
- P1 GEO/AEO blocker：未發現

## 修正內容

- 新增 `app/web/llms.txt`
- 新增 `app/web/ai.txt`
- 新增 `app/web/feed.xml`
- `main.py` 新增 `/llms.txt`、`/ai.txt`、`/feed/`、`/feed.xml`
- `app/web/_redirects` 新增對應靜態部署規則
- `scripts/competitor_seo_tool.py` 在 local audit 下 remap feed item URL，避免本機驗收混入 production live 頁
- `tests/test_web.py` 補 endpoint 與 redirect contract 測試
- `tests/test_competitor_seo_tool.py` 補 local feed URL remap 測試

## 證據檔

- `artifacts/fortune_council/seo_geo_fix_execution/evidence/foundation_endpoints/local_own_site_seo_audit.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/foundation_endpoints/local_comparison.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/foundation_endpoints/local_own_site_competitor_audit.json`

## 限制

- 此次驗收為本機 `http://127.0.0.1:8799`。
- `https://mysticpantheon.com` 需部署後再跑 live audit，才可宣稱 production endpoint 已更新。
- 關鍵字對標與 content gap 先暫停，後續等基礎工程穩定後再恢復。
