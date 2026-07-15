# CARD-SEO-GEO-FIX-004 Verification

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
- `pytest tests/test_web.py tests/test_competitor_seo_tool.py`：33 passed, 1 existing deprecation warning
- brief 數量：19
- 本機 comparison：`output/competitor_seo/local_vs_click108/comparison.md`
- Content Gap：由 19 個降為「小樣本未發現競品命中但自己缺席的 keyword」
- Own keyword hits：19 個第一批 gap keyword 皆在 `own_site/keyword_gap.csv` 命中
- SEO / GEO score 未倒退：Schema depth 80、E-E-A-T 100、Citability 100、Entity 100

## 工具修正

- `keyword_matches()` 原本只比 title、description、OG、H1、H2，未納入正文與 anchor text。
- 已新增 `PageAudit.visible_text`，抽取去除 `script` / `style` 後的頁面可見文字，讓 content gap audit 能檢查可爬正文與導覽。
- 新增測試：`test_keyword_matches_include_visible_page_text`。

## 證據檔

- `artifacts/fortune_council/seo_geo_fix_execution/evidence/content_gap/content_gap_briefs.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/content_gap/local_comparison.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/content_gap/local_own_site_seo_audit.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/content_gap/local_own_site_keyword_gap.csv`

## 限制

- 此次驗收為本機 `http://127.0.0.1:8799`。
- `https://mysticpantheon.com` 需部署後再跑 live audit，才可宣稱 production Content Gap 已下降。
- `錢幣十` 已有 brief 與入口曝光，但仍需下一張寫稿卡補正式 registry / body。
