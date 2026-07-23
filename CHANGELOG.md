# Pantheon Release Log

每次正式文章發布都必須同步更新 `pyproject.toml`、`package.json` 與本檔，並以同版本 annotated tag 指向 release commit。

## [0.3.8] - 2026-07-23

- Release tag：`v0.3.8`
- 公開文章總數：370
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-36。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.8`

## [0.3.7] - 2026-07-23

- Release tag：`v0.3.7`
- 公開文章總數：369
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-75。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.7`

## [0.3.6] - 2026-07-23

- Release tag：`v0.3.6`
- 公開文章總數：368
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-82。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.6`

## [0.3.5] - 2026-07-23

- Release tag：`v0.3.5`
- 公開文章總數：367
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-65。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.5`

## [0.3.4] - 2026-07-23

- Release tag：`v0.3.4`
- 公開文章總數：366
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-43。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.4`

## [0.3.3] - 2026-07-23

- Release tag：`v0.3.3`
- 公開文章總數：365
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-95。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.3`

## [0.3.2] - 2026-07-23

- Release tag：`v0.3.2`
- 公開文章總數：364
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 10 個 run；run_id：harness-new-20260723-79, harness-new-20260723-99, harness-new-20260723-73, harness-new-20260723-21, harness-new-20260723-62, harness-new-20260723-97, harness-new-20260723-50, harness-new-20260723-93, harness-new-20260723-56, harness-new-20260723-30。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.2`

## [0.3.1] - 2026-07-23

- Release tag：`v0.3.1`
- 公開文章總數：354
- 發布範圍：自動發布 Gemini Reviewer APPROVE 且 deterministic gate 通過的新文章 1 個 run；run_id：harness-new-20260723-24。
- 驗證：publisher clean-origin gate、Reviewer hash gate、deterministic quality gate、batch uniqueness gate、focused article pipeline tests 與 release record gate。
- 證據：`.work/content-publisher/evidence/publish-0.3.1`

## [0.3.0] - 2026-07-23

- Release tag：`v0.3.0`
- 公開文章總數：353
- 發布範圍：新增 opt-in Gemini V4 broker、durable ledger／replay、agy CLI compatibility 與 canary 基礎設施；受監督產文維持 legacy CLI 並與 V4 解耦。另新增「土星回歸是什麼？30歲前後的工作與關係觀察」，每日產文 CLI 可明確鎖定零次內容修補。
- 相容性：既有 API 與預設產文 transport 不變；V4 必須明確設定 `AGY_GEMINI_V4_BROKER=1` 才啟用。
- 驗證：Gemini Writer 與 fresh Reviewer 通過；255 tests passed；V4 synthetic／canary evidence、prerender、feed、sitemap、本機 desktop／mobile browser acceptance 與 `git diff --check` 通過。
- 證據：`artifacts/fortune_council/content_pipeline_repair_execution/evidence/`、`artifacts/fortune_council/content_seo_execution/evidence/daily_publishing/daily-20260723-repair-01/`

## [0.2.0] - 2026-07-20

- Release tag：`v0.2.0`
- 公開文章總數：352
- 發布範圍：整合 Venus 補充文章與 Article Expansion 50E，新增 52 篇公開文章；保留 Gemini rewrite release cache 契約。
- 發布 commits：`90c5860`、`b6742f9`、`6087cdb`、`f7a5fb2`、`98fd144`
- 驗證：177 tests passed；352 個 article ID、slug 與公開路徑皆唯一；prerender 生成器冪等；`git diff --check` 通過。
- 證據：`artifacts/fortune_council/content_seo_execution/evidence/article_expansion_50e/`
