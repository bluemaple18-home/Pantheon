# CARD-SEO-GEO-INFRA-003 Verification

狀態：`BLOCKED (deploy scope mixed)`

## 已執行

```bash
.venv/bin/python -m pytest
git diff --check
.venv/bin/python scripts/competitor_seo_tool.py --own-site-url https://mysticpantheon.com --own-name PantheonLive --site-url https://news.click108.com.tw --name Click108 --since 2024-07-10 --max-feed-pages 2 --max-category-pages 1 --sample-limit 5 --out-dir output/competitor_seo/live_vs_click108_predeploy
```

## 證據

- 全套測試：71 passed, 1 existing deprecation warning
- `git diff --check`：pass
- Live baseline audit：`output/competitor_seo/live_vs_click108_predeploy/own_site/seo_audit.md`

## Live Baseline 結果

- `llms.txt`：fallback_html
- `ai.txt`：fallback_html
- `feed`：present status=200 bytes=1053，但內容仍像 fallback HTML
- Schema depth：20
- E-E-A-T：0
- Citability：60
- Entity：50

## Blocker

目前 worktree dirty scope 混合：

- 基礎工程變更。
- 先前 keyword/content-gap 變更。
- 多組任務卡與 evidence。

依 `docs/pantheon_deployment_workflow.md`，不能把不屬於本次上線目的的 dirty files 混進 production commit。使用者也已要求關鍵字對標先暫停，所以 production deploy 需要先切乾淨 scope。

## 建議處理

- 先建立乾淨 deployment slice，只帶 `CARD-SEO-GEO-INFRA-001` / `002` 必要檔案。
- 或由 PM 明確批准把目前整包 SEO/GEO 修復一起部署。

## 歸檔證據

- `artifacts/fortune_council/seo_geo_fix_execution/evidence/live_predeploy/live_own_site_seo_audit.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/live_predeploy/live_comparison.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/live_predeploy/live_own_site_competitor_audit.json`
