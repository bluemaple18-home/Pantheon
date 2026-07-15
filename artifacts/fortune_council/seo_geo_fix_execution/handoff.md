# Pantheon SEO / GEO 修復派工 Handoff

## Root Question

如何把 `output/competitor_seo/news.click108.com.tw/comparison.md` 暴露的 Pantheon 缺口，轉成可驗收的前台與工具修復，讓 Pantheon 在 SEO / GEO / AI visibility 上短期超過 Click108？

## 目前狀態

- 工具已支援 `--own-site-url` 對比競品。
- 最新比較輸出：`output/competitor_seo/news.click108.com.tw/comparison.md`
- Pantheon 目前相對 Click108：
  - `llms.txt` / `ai.txt` 顯示 present，但需先確認是否為真檔案，不是 SPA fallback。
  - Schema depth：14，偏低。
  - E-E-A-T：0，明顯落後。
  - Entity：50，落後。
  - Citability：60，暫時領先。
  - Content Gap 集中在塔羅小牌與情境詞。

## Blocker

`llms.txt` / `ai.txt` 目前可能是 200 fallback，不一定是真文字檔。修前台前，需先讓工具能辨識 endpoint false positive。

## Fork

- P0：工具 hardening，避免錯誤驗收。
- P1：前台 schema / entity / E-E-A-T 修復。
- P2：Content Gap 文章補強。
- P3：AI visibility monitor，需外部模型/API key 或人工 dry-run。

## 請讀

1. `output/competitor_seo/news.click108.com.tw/comparison.md`
2. `output/competitor_seo/news.click108.com.tw/own_site/seo_audit.md`
3. `docs/competitor_seo_tool.md`
4. `docs/pantheon_article_publication_standard.md`
5. `artifacts/fortune_council/seo_geo_repo_intake/source_manifest.md`

## 派工卡

`CARD-SEO-GEO-FIX-000` / 主線校準｜SEO/GEO 修復對話框
請讀: `artifacts/fortune_council/seo_geo_fix_execution/CARD-SEO-GEO-FIX-000-master-plan.md`
任務目的: 校準修復順序、驗收命令與分數門檻
證據路徑: `artifacts/fortune_council/seo_geo_fix_execution/evidence/master_plan/`

`CARD-SEO-GEO-FIX-001` / 工具 hardening｜SEO/GEO 工具對話框
請讀: `artifacts/fortune_council/seo_geo_fix_execution/CARD-SEO-GEO-FIX-001-tool-hardening.md`
任務目的: 修正 `llms.txt` / `ai.txt` false positive，讓 endpoint 驗收可信
證據路徑: `artifacts/fortune_council/seo_geo_fix_execution/evidence/tool_hardening/`

`CARD-SEO-GEO-FIX-002` / Schema + Entity｜前台 SEO 對話框
請讀: `artifacts/fortune_council/seo_geo_fix_execution/CARD-SEO-GEO-FIX-002-schema-entity.md`
任務目的: 提升 Pantheon Schema depth 與 Entity score
證據路徑: `artifacts/fortune_council/seo_geo_fix_execution/evidence/schema_entity/`

`CARD-SEO-GEO-FIX-003` / E-E-A-T｜前台內容信任對話框
請讀: `artifacts/fortune_council/seo_geo_fix_execution/CARD-SEO-GEO-FIX-003-eeat.md`
任務目的: 補作者、更新日期、about/contact/editorial policy 與來源信任訊號
證據路徑: `artifacts/fortune_council/seo_geo_fix_execution/evidence/eeat/`

`CARD-SEO-GEO-FIX-004` / Content Gap｜內容 SEO 對話框
請讀: `artifacts/fortune_council/seo_geo_fix_execution/CARD-SEO-GEO-FIX-004-content-gap.md`
任務目的: 針對 Click108 命中但 Pantheon 未命中的關鍵字補文章/FAQ/內鏈
證據路徑: `artifacts/fortune_council/seo_geo_fix_execution/evidence/content_gap/`

`CARD-SEO-GEO-FIX-005` / AI Visibility Monitor｜Agent 工作流對話框
請讀: `artifacts/fortune_council/seo_geo_fix_execution/CARD-SEO-GEO-FIX-005-ai-visibility-monitor.md`
任務目的: 設計 P3 prompt monitor，追蹤 ChatGPT / Gemini / Perplexity 對 Pantheon 與競品的提及
證據路徑: `artifacts/fortune_council/seo_geo_fix_execution/evidence/ai_visibility/`

## 下一步

先執行 `CARD-SEO-GEO-FIX-001`。如果工具把 fallback HTML 誤判成 `llms.txt` / `ai.txt` present，後面所有比較分數都會被污染。
