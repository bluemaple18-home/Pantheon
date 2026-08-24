# Pantheon Content Prior-Art Registry

更新：2026-08-24

## 原則

本檔是 Content Plane 的 prior-art 索引。目標是把「查資料」成本前置一次做完，後續 Codex 施工卡直接讀這裡指定的 donor / exact path，不再每張卡重新廣搜。

規則：

1. generic capability 先查本檔；已有 donor 時直接讀指定 path，禁止重新做泛搜尋。
2. donor 只提供 implementation pattern / test pattern / algorithm；Pantheon 既有 authority（NEW / REWRITE / i18n / Publisher / G8 / Rule 24 / Rule 25）不得被 donor 取代。
3. copy code 前必須遵守 license；不確定 license 時只允許參考 architecture / algorithm。
4. 若 Pantheon 已有等價能力，優先 KEEP，不為了 donor 重寫。
5. 新增 donor 必須寫清楚「要看哪個檔案／哪一段」，不能只丟 repo URL。

---

## PA-001 — WP Content Autopilot

- Repo: https://github.com/max-rogue/wp-content-autopilot
- License: MIT
- 用途：大量文章 pipeline 的 queue、dedup、stage separation、QA、idempotency、quota / scheduling pattern。
- 不吸收：它自己的 Publisher authority、整套 Agent framework、WordPress ownership。

### Codex 最小閱讀範圍

先讀，不要掃整 repo：

1. `README.md`
   - `Pipeline Stages`：Stage 0 queue → Stage 1 dedup → Stage 2 research → Stage 3 writing → 3.5 edit → Stage 5 QA → Stage 6 publish。
   - `Configuration`：`PUBLISH_POSTURE`、`DAILY_JOB_QUOTA`。
   - `Automated Scheduling`：cron pattern。
2. `src/stages/stage0.ts` + `src/stages/stage0.test.ts`
   - 只參考 next-job / queue selection 與測試切法。
3. `src/stages/stage1.ts` + `src/stages/stage1.test.ts`
   - 只參考 dedup / similarity gate。
4. `src/stages/idempotency.test.ts`
   - 只參考 stage idempotency regression pattern。
5. `src/stages/stage3.ts` + `src/stages/stage3.test.ts`
   - 只在 Pantheon NEW batch runner 缺 orchestration pattern 時讀；不要搬 prompt authority。
6. `src/stages/stage3_5.ts` + test
   - 只在 REWRITE orchestration gap 存在時讀。
7. `src/gates/`
   - 只比對 generic QA gate composition；Pantheon `article_publication_policy_v2` 仍是唯一內容 hard-gate authority。
8. `src/config/taxonomy_config.yaml`
   - 參考 cluster → category / tag whitelist 的 config pattern。
9. `prompts/template_prompts.md`
   - 只參考 prompt 分 stage 的檔案組織，不複製內容策略。

### Pantheon 決策

- Queue / batch selection：`ABSORB PATTERN`
- Dedup / similarity：`ABSORB PATTERN`
- Idempotency tests：`ABSORB TEST PATTERN`
- Writer / editor agent：`KEEP PANTHEON`
- QA authority：`KEEP PANTHEON`
- Publisher：`KEEP PANTHEON`
- Scheduler：只有 throughput 需要時才 `ADAPT`，不得現在新增第二套 scheduler。

---

## PA-002 — PageForge

- Repo: https://github.com/ShubhamTuts/PageForge
- License: GPLv2-or-later（README 宣告；copy 前仍需以 repo LICENSE 為準）
- 用途：Programmatic SEO 的 structured rows → reusable template → bulk WordPress pages；duplicate slug、metadata、schema、internal-link hub。
- 不吸收：PageForge plugin 本身、Pro-only workflow、WordPress page ownership。

### Codex 最小閱讀範圍

1. `README.md`
   - `How PageForge Works / Prepare CSV / Create One WordPress Template / Generate SEO Pages / Add SEO Meta`。
   - `Main Features`：dynamic token、duplicate slug protection、Yoast/Rank Math sync、schema、sitemap/internal-link hub。
   - `Recommended First Campaign`：小批驗證後放量的 batch pattern。
2. 只有當 Topic Matrix / ContentSpec implementation 需要 template/token donor 時，才往 repo 內追 CSV importer / token replacement / duplicate-slug 實作；不要預先掃全 repo。

### Pantheon 決策

- Topic Matrix → structured row：`ABSORB CONCEPT`
- ContentSpec → template variables：`ABSORB CONCEPT`
- Duplicate slug / route protection：`COMPARE WITH EXISTING, KEEP SINGLE AUTHORITY`
- Metadata/schema/internal links：`ADAPT ONLY IF EXISTING GAP`
- Bulk WordPress generator：`IGNORE`，Pantheon已有 Publisher。

---

## PA-003 — WordPress AI

- Repo: https://github.com/WordPress/ai
- License: 以 repo LICENSE 為準；預設只參考官方 WordPress implementation pattern，不直接 copy 未核對 code。
- 用途：WordPress-native editorial / metadata / guidelines patterns。

### Codex 最小閱讀範圍

只在對應 backlog 卡真的需要時讀：

1. README feature sections：
   - `Editorial Notes`
   - `Editorial Updates`
   - `Guidelines`
   - `Meta Description Generation`
   - `Multi-Provider Support`
2. 不為了研究而掃 experiments 全目錄。

### Pantheon 決策

- Editorial policy：`KEEP PANTHEON article_publication_policy_v2`
- Meta description integration pattern：`REFERENCE`
- Guidelines/provider abstraction：`REFERENCE IF GAP`
- 不引入 WordPress AI 作第二套 content authority。

---

## PA-004 — WordPressAISEO

- Repo: https://github.com/MervinPraison/WordPressAISEO
- License: implementation 前必須再核對 repo LICENSE；目前只做 reference donor。
- 用途：Phase 2 SEO optimization；bulk metadata、analysis、internal linking、orphan detection、rewrite actions、REST/WP-CLI automation。

### Codex 最小閱讀範圍

Phase 1 不讀 source，只記錄。

Phase 2 才讀：

1. `README.md`
   - `SEO Analysis & Optimization`
   - `Bulk Operations Commands`
   - `Content & Linking Commands`
   - `Multilingual & CPT Endpoints`
   - retry / rate-limit / circuit-breaker 說明。
2. 只有選定要吸收的 capability 才追 `includes/` 對應 class；禁止先掃 25k+ lines。

### Pantheon 決策

- GSC ingestion：`IGNORE`，Pantheon 已有正式 `docs/gsc_daily_pipeline.md` 與 scripts。
- Bulk SEO metadata：`REFERENCE / ADAPT LATER`
- Internal linking / orphan detection：`REFERENCE / ADAPT LATER`
- Rewrite action vocabulary：`REFERENCE / ADAPT LATER`
- Multilingual SEO decision：只參考 API pattern；Pantheon 四語系 SEO truth 必須獨立。

---

## PA-005 — Google Search 官方文件

Pantheon 已經有 GSC pipeline，禁止重做 ingestion。

- Search Analytics API: https://developers.google.com/webmaster-tools/v1/searchanalytics/query
- Search Console API: https://developers.google.com/webmaster-tools
- Helpful content: https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- Structured data policies: https://developers.google.com/search/docs/appearance/structured-data/sd-policies
- Canonical consolidation: https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls

### Pantheon 既有實作

- `docs/gsc_daily_pipeline.md`
- `scripts.gsc_daily_fetch`
- `scripts.gsc_daily_inspection`
- `.work/gsc-data/daily/...`
- `.work/gsc-data/url-inspection/...`

決策：`KEEP / EXTEND LATER`，不得另造 GSC collector。

---

## PA-006 — Pantheon 既有內容研究／規範（內部 prior art）

這些不是待研究項，而是現有 authority / evidence，施工前直接讀指定文件：

1. `docs/pantheon_article_publication_standard.md`
   - machine authority：`app/core/article_publication_policy_v2.json`
   - full-corpus duplicate / route / canonical / FAQ / evidence / rewrite modified-date hard gates。
2. `artifacts/fortune_council/content_seo_matrix/`
   - 既有 SEO / AEO / GEO content matrix；Topic Matrix v1 必須先盤點這裡，禁止重建一份平行矩陣。
3. `output/click108_research/report.md`
   - Click108 近兩年內容研究。
4. `artifacts/fortune_council/content_seo_execution/evidence/click108_voice_research_v2.md`
   - 寫法 donor；只吸收形式，不吸收結果承諾。
5. `app/web/static/article-registry.js`
   - 現有文章 registry / 前台 identity。
6. `app/web/static/article-seo.js`
   - 現有前台 SEO / JSON-LD。

---

## 後續新增 donor 的最低格式

```text
ID
repo / paper / official URL
license
Pantheon capability
exact file / exact section
why this donor
KEEP / ABSORB / ADAPT / REPLACE / IGNORE
copy allowed?
tests reusable?
authority boundary
```

沒有 exact file / section 的 donor 不得進 implementation card。
