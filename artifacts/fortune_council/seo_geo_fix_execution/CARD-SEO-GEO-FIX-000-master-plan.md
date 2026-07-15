# CARD-SEO-GEO-FIX-000｜SEO/GEO 修復主計劃

## 任務目的

把目前 Pantheon vs Click108 的比較結果收斂成可執行修復順序、驗收門檻與交接證據，避免多個對話框各修各的。

## 請讀

- `output/competitor_seo/news.click108.com.tw/comparison.md`
- `output/competitor_seo/news.click108.com.tw/own_site/seo_audit.md`
- `docs/competitor_seo_tool.md`
- `artifacts/fortune_council/seo_geo_fix_execution/handoff.md`

## 修復順序

1. `CARD-SEO-GEO-FIX-001`：工具 hardening，先讓 endpoint 分數可信。
2. `CARD-SEO-GEO-FIX-002`：修 schema depth 與 entity metadata。
3. `CARD-SEO-GEO-FIX-003`：補 E-E-A-T 信任訊號。
4. `CARD-SEO-GEO-FIX-004`：依 content gap 補文章、FAQ、內鏈。
5. `CARD-SEO-GEO-FIX-005`：設計 AI visibility monitor，不先接商業 API。

## 驗收門檻

- `comparison.md` 必須產出。
- `own_site/seo_audit.md` 不得把 HTML fallback 誤判成 `llms.txt` / `ai.txt`。
- Schema depth 目標：至少 70。
- E-E-A-T 目標：至少 60。
- Entity 目標：至少 70。
- Content Gap 至少轉成第一批可上稿文章/FAQ/內鏈計劃。

## 驗證命令

```bash
.venv/bin/python scripts/competitor_seo_tool.py \
  --own-site-url https://mysticpantheon.com \
  --own-name Pantheon \
  --site-url https://news.click108.com.tw \
  --name Click108 \
  --since 2024-07-10 \
  --max-feed-pages 2 \
  --max-category-pages 1 \
  --sample-limit 5
```

## 證據路徑

`artifacts/fortune_council/seo_geo_fix_execution/evidence/master_plan/`
