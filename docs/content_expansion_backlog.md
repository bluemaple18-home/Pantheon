# Pantheon Content Expansion Master Backlog

更新：2026-08-24
狀態：`ACTIVE PLANNING / PUBLISHING FIRST`
商業目標：先讓自動發文穩定動起來，再快速鋪約 10,000 篇命理內容；之後才進四語系 GSC-driven SEO optimization，最終服務付費算命產品。

## 0. 不可改變的主線

```text
現在：Publishing Closeout → 10K Expansion
之後：GSC × 4 locales → SEO Optimization
最後：Content Traffic → Free Reading → Paid Reading
```

目前不做 feedback-driven expansion；10K coverage 不等待 GSC 學習迴圈。

Prior-art 強制索引：`docs/content_prior_art_registry.md`。

任何 generic capability 開工前：

1. 先查 registry 指定 donor / exact path。
2. 已有 donor 時禁止重新泛搜。
3. Pantheon 已有能力則 KEEP，不因 donor 重寫。
4. 只有 registry 無 donor 且 repo 內也無現有能力時，才允許 bounded research。

---

# P0 — 先讓發文動起來

## CONTENT-P0-01 — Current Production Read-Only Reconciliation

**狀態：NEXT / BLOCKING**

目的：依 `handoff_20260822_g8_exit78_release_v0370.md`，只讀確認 `v0.3.370` 後當下 production truth。

輸入：

- `handoff_20260822_g8_exit78_release_v0370.md`
- `PANTHEON-G8-RELEASE-STATE-CONTRACT-V1-20260821.md`
- `PANTHEON-G8-TRANSITION-EDGE-MAP-V1-20260821.md`
- Cycle 33/34 + exit78 provenance review evidence

輸出唯一 gate matrix：`GO / NO-GO / UNKNOWN`。

必驗：release baseline、runtime phase、generation、Publisher identity、loaded/no-PID、reset receipt freshness、other-six unchanged proof、Rule 24、Rule 25 current evidence。

禁止：任何 reset / Capacity mutation / activation / restage / canary / deploy。

Prior art：不需要外部研究；完全使用現有 G8 contract/evidence。

完成：若 GO，停下取得一次 bounded canary 人工授權。

---

## CONTENT-P0-02 — Bounded End-to-End Publishing Canary

**狀態：BLOCKED by P0-01 + human authorization**

目的：證明既有 Content Plane 真的能完成一次 production publication，不再擴 G8。

現有合法 lineage：

```text
NEW → i18n-new
REWRITE → i18n-rewrite
Publisher exact-run → fresh legal i18n-new → transaction → published result
```

驗收 evidence：campaign/generation/manifest identity、四 lanes receipts、Publisher receipt、transaction、published URL/result。

禁止把 lineage 改成 `new → rewrite → translate`。

Prior art：不需要外部研究；這是 Pantheon production acceptance。

完成：`BOUNDED_CANARY_COMPLETE`。

---

## CONTENT-P0-03 — G8 Publishing Control Plane Closeout / Freeze

**狀態：BLOCKED by P0-02**

目的：canary 成功後凍結 G8 feature work，把 frontier 移到 10K Expansion。

規則：

- 同一 transition edge 以一個 bounded repair unit 處理。
- 禁止一個 error code 一張 Cycle 35/36 symptom card。
- 只有 production regression 證明 contract 被破壞才重開 G8。
- steady autonomy 仍需獨立 production checkpoint，不隨 canary 自動授權。

完成：`G8_FEATURE_FROZEN_FOR_EXPANSION`。

---

# P1 — 10K Content Expansion

## CONTENT-P1-00 — Existing Capability Reconciliation（先做，限時）

**狀態：READY AFTER P0 CLOSEOUT**

目的：不是研究新架構，而是把「現有什麼、缺什麼」一次列清楚，後面不重工。

只讀範圍：

- `docs/pantheon_article_publication_standard.md`
- `app/core/article_publication_policy_v2.json`
- `artifacts/fortune_council/content_seo_matrix/`
- `app/web/static/article-registry.js`
- `app/web/static/article-seo.js`
- NEW / REWRITE / i18n / Publisher 現有 source + tests
- `docs/content_prior_art_registry.md`

輸出 capability matrix：

```text
capability | existing authority | gap | donor ID | exact donor path | decision
```

判定只能：`KEEP / ABSORB PATTERN / ADAPT / GAP`。

禁止泛搜；外部閱讀只限 registry 已指定 path。

完成後直接合併／刪除下面不必要 backlog，不得因 reconciliation 再長一套 architecture。

---

## CONTENT-P1-01 — Topic Matrix v1 / 10K Coverage Plan

**目標：把 10K 題目變成 deterministic inventory，不讓 Writer 自由想一萬題。**

先讀 Pantheon：

- `artifacts/fortune_council/content_seo_matrix/`（先盤點；不得另建平行 SEO matrix）
- `docs/pantheon_article_publication_standard.md` §1、§2.1

Prior art 最小讀取：

- `PA-002 PageForge`
- 只讀 README 的 `Prepare CSV`、`Create One WordPress Template`、`Generate SEO Pages`、dynamic token / duplicate slug sections。

吸收：structured row / reusable dimension pattern。
不吸收：PageForge WordPress generator。

Topic dimensions 先從既有矩陣推導；至少能表示：

```text
domain
entity
intent
scenario
relationship/context
time_window
template_family
product_intent
```

輸出：

- canonical `topic_id`
- 10K candidate inventory
- exact duplicate removal
- coverage counts by domain / template family
- 每個 topic 預留 product intent

完成標準：Writer 不需自行發明 topic；可從 inventory deterministic 取下一題。

---

## CONTENT-P1-02 — ContentSpec + Locale Instance Contract

**目標：一個 canonical topic 對四個 locale instance；不是四套系統。**

先檢查現有 article registry / content model；有等價欄位就擴充，禁止第二套 registry。

最低欄位：

```text
content_id
topic_id
domain
semantic_intent
product_intent
template_family
locale
localized_title
source_lineage
generation
status
published_url
wordpress_post_id
publisher_transaction_id
```

四語系共享 canonical topic identity；SEO performance/action 未來 locale-specific。

Prior art：

- `PA-002 PageForge`：structured row → template variable concept only。
- `PA-001 WP Content Autopilot`：`data/keyword.csv` / taxonomy config 的 queue-input organization only。

完成：NEW / i18n / Publisher 可引用同一 ContentSpec identity，不改它們既有 authority。

---

## CONTENT-P1-03 — Coverage / Dedup / Next-Topic Selection

**目標：10K 不能重複發，也要知道剩哪些沒發。**

Pantheon authority 優先：

- `article_publication_policy_v2` 已有 full-corpus duplicate / duplicate ID / duplicate route hard gates；不得另造第二套 duplicate truth。

Prior art 精讀：

- `PA-001`
  - `src/stages/stage0.ts` + test：next keyword / queue selection pattern。
  - `src/stages/stage1.ts` + test：dedup / similarity pattern。
  - `src/stages/idempotency.test.ts`：idempotency regression pattern。
- `PA-002` README duplicate slug protection：只做對照。

實作原則：

- selection 可以新增；duplicate authority 必須重用／呼叫既有 publication policy / registry。
- 不新增 Knowledge Graph。
- 不新增 Content Registry DB，除非 P1-00 證明 repo 無任何可延伸 durable inventory；若真的需要，先停下回報 authority gap。

完成：`next_topic()` 類能力可 deterministic 取得未完成 topic；重跑不重複 publish。

---

## CONTENT-P1-04 — Bulk NEW Generation Vertical Slice

**目標：從一批 ContentSpec 直接餵現有 NEW lane，批量產 candidate。**

Prior art 精讀：

- `PA-001 src/stages/stage0.ts`：batch job selection。
- `PA-001 src/stages/stage3.ts` + test：stage boundary / failure handling；只參考 orchestration，不搬 prompt。
- `PA-001 src/config/taxonomy_config.yaml`：cluster/category config pattern（若 Pantheon taxonomy gap存在才用）。

KEEP：Pantheon NEW prompt、publication policy、domain rules。

禁止：新 Writer Agent framework、新 scheduler、新 Publisher。

完成：bounded batch（先 10，再 100）可產生可追蹤 NEW candidates；單篇失敗不污染其他 topic identity；可安全 resume。

---

## CONTENT-P1-05 — Four-Locale Batch i18n Vertical Slice

**目標：NEW candidate 走現有 i18n-new；REWRITE candidate 走現有 i18n-rewrite；批量化而不改 lineage。**

Prior art：目前不需要新增 donor；先 KEEP 現有 i18n implementation。

只有 P1-00 證明 translation mechanics 有 gap 才允許新增 donor research。

完成：同一 canonical topic 的四 locale instance identity 可追蹤；locale failure 可單獨 retry；不得把 SEO keyword truth直接由中文翻譯過去。

---

## CONTENT-P1-06 — Bulk Publisher Throughput + Idempotency

**目標：讓現有 Publisher 能吃 expansion batch，而不是重寫 Publisher。**

Prior art 精讀：

- `PA-001 README` Stage 6 publish / `PUBLISH_POSTURE` / daily quota：只參考 throughput / posture knobs。
- `PA-001 src/stages/idempotency.test.ts`：重跑安全測試 pattern。
- `PA-002 README` duplicate slug protection：對照 route safety。

Pantheon existing Publisher / transaction / G8 authority全部 KEEP。

先量現有 throughput；只有證明 bottleneck 才加 batch knob / quota。禁止先加 cron/daemon。

完成：同 `content_id × locale × generation` 不會意外二次發布；批量中斷後可 resume；publication result回寫既有 inventory/registry authority。

---

## CONTENT-P1-07 — 10K Expansion Runner

**目標：把 P1-01~06 串成最小 expansion runner；不打造新 control plane。**

```text
Topic inventory
→ next eligible ContentSpec batch
→ NEW
→ i18n-new
→ existing QA / publication policy
→ existing Publisher
→ publication result
→ coverage update
```

REWRITE 不作為 10K expansion 的必要串行步驟；它保持獨立 lane，供既有舊文或後期 SEO optimization使用。

Prior art：只重讀 `PA-001 README Pipeline Stages` 作 sanity check；禁止再掃 repo。

Ramp：

1. 10 topics
2. 100 topics
3. 500 topics
4. sustained expansion toward ~10K

每一級只驗 throughput、failure rate、duplicate rate、policy rejection、publish success；不要因此建立 dashboard。

完成：可持續放量，不需人工逐篇批准。

---

# P2 — GSC / 四語系 SEO Optimization（10K 後）

## 重要：GSC ingestion 已存在，禁止重做

現有：

- `docs/gsc_daily_pipeline.md`
- `scripts.gsc_daily_fetch`
- `scripts.gsc_daily_inspection`
- Search Analytics page × query snapshots
- URL Inspection / Breadcrumb snapshots

所以沒有 `build GSC ingestion` backlog。

---

## CONTENT-P2-01 — GSC Data → Locale SEO Opportunity View

讀現有 GSC snapshot，按 locale / URL / query 分開建立 derived opportunity view。

官方 source：`PA-005 Google Search Analytics API`。

禁止新 collector；只消費現有 snapshot。

---

## CONTENT-P2-02 — SEO Action Classifier

輸出 action：

```text
KEEP
RETITLE
META_OPTIMIZE
EXPAND
REFRESH
REWRITE
INTERNAL_LINK
MERGE
SPLIT
REDIRECT
NOINDEX
PRODUCT_CTA_OPTIMIZE
```

Prior art 最小讀取：

- `PA-004 WordPressAISEO README`
  - SEO Analysis & Optimization
  - Bulk Operations
  - Content & Linking
  - Multilingual endpoints

只在確定 action 要落地時才讀對應 `includes/` class。

---

## CONTENT-P2-03 — Locale-Specific Rewrite / Merge / Relink Queue

四語系分開做 SEO decision；不得中文優化後直接翻成其他語系 SEO truth。

REWRITE 重用既有 lane；merge/redirect/internal-link先找現有能力，再參考 PA-004。

---

## CONTENT-P2-04 — SEO Republish + Outcome Tracking

重用 existing Publisher + existing GSC snapshots。

不新增 SEO Publisher。

---

# P3 — Product Conversion（後續）

## CONTENT-P3-01 — Topic → Product Intent Mapping

現在 P1 ContentSpec 已保留 `product_intent`；此卡只在 10K / SEO 收斂後正式使用。

## CONTENT-P3-02 — Article → Free Reading CTA

依 topic/product intent導入 Pantheon 免費算命入口。

## CONTENT-P3-03 — Free → Paid Reading Funnel

最後才優化付費轉換。

---

# 明文禁止

- 重寫 Publisher。
- 重寫 NEW / REWRITE / i18n。
- 新 Agent framework。
- 新 scheduler / daemon / database，除非現有 authority gap 被證明且先停下評估。
- 第二套 Content Registry / duplicate truth。
- 一個 locale 一套 orchestration。
- 10K 前先做完整 GSC intelligence。
- 10K 前先做完整 conversion analytics。
- 一個 error code 一張卡。
- donor repo 全庫掃描；只讀 `content_prior_art_registry.md` 指定 exact paths。
- 已有 donor 的 capability 重新做泛研究。
- 沒核對 license 就 copy code。

# Frontier 規則

當前唯一 frontier：`CONTENT-P0-01`。

P0 closeout後，P1 的第一拍只能是 `CONTENT-P1-00 Existing Capability Reconciliation`；它是限時去重，不是新架構研究。

從 P1-01 起，每張 implementation card 必須引用：

```text
Pantheon existing authority
Prior-art registry ID
Exact donor path/section
Absorption decision
```

若沒有這四項，不得開工。
