# SEO / GEO Fix Execution Result

狀態：關鍵字對標先暫停；`CARD-SEO-GEO-INFRA-003` 已完成 live predeploy baseline，但 production deploy 因 dirty scope 混合而 blocked。

## 已完成

- 建立 handoff。
- 建立 `CARD-SEO-GEO-FIX-000` 到 `CARD-SEO-GEO-FIX-005`。
- 明確切出工具 hardening、schema/entity、E-E-A-T、content gap、AI visibility monitor。
- `CARD-SEO-GEO-FIX-001`：修正 `scripts/competitor_seo_tool.py` 對 `llms.txt` / `ai.txt` 的 200 fallback false positive。
- 新增 endpoint content validation：`present` / `missing` / `blocked` / `fallback_html` / `invalid_content`。
- 實站重跑後，Pantheon `/llms.txt` 與 `/ai.txt` 皆判定為 `fallback_html`；Click108 仍為 `missing`。
- `CARD-SEO-GEO-FIX-002`：補文章列表頁與單篇模板的 Organization / WebSite entity、列表頁 FAQPage、OG image / Twitter image。
- `CARD-SEO-GEO-FIX-002`：動態 Article / CollectionPage JSON-LD 改為引用同一個 `#organization` / `#website`。
- `CARD-SEO-GEO-FIX-002`：工具 Schema depth core types 校準為 `Article`、`FAQPage`、`BreadcrumbList`、`Organization`、`WebSite`。
- 本地 audit 已達標：Schema depth 80、Entity 100。
- `CARD-SEO-GEO-FIX-003`：補文章入口與單篇模板的 author、published / modified metadata、內容信任入口、編輯政策、聯絡入口與外部參考來源。
- `CARD-SEO-GEO-FIX-003`：動態文章 metadata 預設日期改為固定發布 / 更新日期，避免每天因 runtime 產生假更新日。
- 本地 audit 已達標：E-E-A-T 100、Citability 100。
- `CARD-SEO-GEO-FIX-004`：產出第一批 19 個 Content Gap brief，包含 meta title、description、H1、FAQ 3 題與內鏈 5 條。
- `CARD-SEO-GEO-FIX-004`：文章入口新增「塔羅與人際補強」cluster，讓第一批 gap keyword 可被前台爬到。
- `CARD-SEO-GEO-FIX-004`：修正 content gap matcher，納入頁面可見文字與 anchor text，不再只看 title / description / H1 / H2。
- 本地 audit 已達標：Content Gap 由 19 個降為「小樣本未發現競品命中但自己缺席的 keyword」。
- 依主線調整：關鍵字對標先暫停，優先打理 SEO / GEO 基礎工程。
- `CARD-SEO-GEO-INFRA-001`：新增真實 `/llms.txt`、`/ai.txt`、`/feed/`、`/feed.xml` endpoint。
- `CARD-SEO-GEO-INFRA-001`：FastAPI 與 Cloudflare Pages `_redirects` 都已接上基礎端點。
- `CARD-SEO-GEO-INFRA-001`：工具 local audit 會把 feed 內同站 production URL 映射回本機 base URL，避免本機驗收混入 live 頁。
- 本地 audit 已達標：feed / llms_txt / ai_txt 皆 present，P1 GEO/AEO blocker 未發現。
- `CARD-SEO-GEO-INFRA-002`：新增 server-side article SEO shell，讓單篇文章 raw HTML 有 path-specific title / description / canonical / JSON-LD。
- `CARD-SEO-GEO-INFRA-002`：文章 raw HTML 的 `article-jsonld`、`breadcrumb-jsonld`、`faq-jsonld` 不再是空 script。
- 本地 audit 已達標：Schema depth 100、E-E-A-T 100、Citability 84、Entity 100，文章頁不再出現 JSON-LD `parse_error`。
- `CARD-SEO-GEO-INFRA-003`：完成 production predeploy audit baseline。
- Production baseline 仍是舊版：`llms.txt=fallback_html`、`ai.txt=fallback_html`、Schema depth 20、E-E-A-T 0、Entity 50。
- Production deploy 尚未執行，原因是目前 worktree 同時混有基礎工程、先前 keyword/content-gap、schema/entity、E-E-A-T 與多組 evidence；依部署 workflow 不可整包推。

## 證據

- `artifacts/fortune_council/seo_geo_fix_execution/evidence/tool_hardening/verification.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/tool_hardening/comparison.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/tool_hardening/own_site_seo_audit.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/tool_hardening/click108_seo_audit.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/tool_hardening/own_site_competitor_audit.json`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/schema_entity/verification.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/schema_entity/local_own_site_seo_audit.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/schema_entity/local_comparison.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/eeat/verification.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/eeat/local_own_site_seo_audit.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/eeat/local_comparison.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/content_gap/verification.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/content_gap/content_gap_briefs.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/content_gap/local_comparison.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/content_gap/local_own_site_seo_audit.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/content_gap/local_own_site_keyword_gap.csv`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/foundation_endpoints/verification.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/foundation_endpoints/local_own_site_seo_audit.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/foundation_endpoints/local_comparison.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/foundation_endpoints/local_own_site_competitor_audit.json`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/raw_article_shell/verification.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/raw_article_shell/local_own_site_seo_audit.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/raw_article_shell/local_comparison.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/raw_article_shell/local_own_site_competitor_audit.json`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/live_predeploy/verification.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/live_predeploy/live_own_site_seo_audit.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/live_predeploy/live_comparison.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/live_predeploy/live_own_site_competitor_audit.json`

## 下一步

先接基礎工程，不接關鍵字對標。建議下一張：

- `CARD-SEO-GEO-INFRA-004`：切乾淨 deployment slice，只包含基礎工程必要檔案；不要納入 keyword/content-gap 對標變更，除非 PM 重新批准。
- `CARD-SEO-GEO-INFRA-005`：部署後 live audit，確認 `https://mysticpantheon.com/llms.txt`、`/ai.txt`、`/feed/` 與文章 raw HTML 不再 fallback。
- `CARD-SEO-GEO-INFRA-006`：建立全量 article raw metadata manifest，讓所有文章 URL 不只核心 feed articles 有 path-specific SEO shell。
- `錢幣十` 與 keyword gap 補文先暫停，等基礎工程穩定後再接。
