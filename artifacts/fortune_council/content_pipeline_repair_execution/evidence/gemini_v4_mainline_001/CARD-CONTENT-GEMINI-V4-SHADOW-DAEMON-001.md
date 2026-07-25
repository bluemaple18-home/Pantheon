---
card_id: CARD-CONTENT-GEMINI-V4-SHADOW-DAEMON-001
chain_id: CONTENT-GEMINI-V4-MAINLINE-001
status: DELIVERED_CANDIDATE
ownership: v4_shadow_daemon_only
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
base_candidate: 4ca327bf8b2a27dfad0132c6585855c55aeabe66
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_mainline_001/shadow-daemon-001/
---

# Gemini V4 常駐 shadow daemon

## Root question

建立與正式產文完全隔離的使用者層常駐 shadow health check；每六小時最多送出
一筆公開合成 request，持續驗證 V4 broker、credential pool、ledger、anchor、
schema 與 replay，且不讀文章、不發布、不切預設 transport。

## Immutable contract

- 獨立 label、queue root、state、log與lock；不得復用正式產文 coordinator queue。
- 預設每六小時一個 deterministic UTC bucket，每日最多四筆。
- 同一 bucket 只允許一個 operation；launchd重入或重啟不得重送。
- 每個 operation只選一個credential slot；失敗不得retry、fallback或換key。
- payload固定為公開、非文章、closed schema health check。
- 僅保存job ID、時間、slot ID、ledger／anchor摘要、closed outcome與result validation；
  不保存credential、完整環境或provider error body。
- shadow失敗不得阻擋或觸發文章流程。
- 必須提供status與可逆stop／uninstall方式。
- 不merge、不deploy網站、不publish文章、不切正式transport。

## Default operating envelope

- cadence：21600秒（6小時）
- maximum：4 external operations／UTC day
- model：`gemini-3.5-flash`
- timeout：沿用V4 runner 120秒
- retry／fallback／redirect：0

## Allowed files

- 本卡與 `shadow-daemon-001/` evidence
- `scripts/agy_gemini_v4_shadow.py`
- `scripts/install_agy_gemini_v4_shadow_launchd.sh`
- `ops/launchd/com.pantheon.agy-gemini-v4-shadow.plist.example`
- `tests/test_agy_gemini_v4_shadow.py`
- `docs/pantheon_gemini_outbox_runner.md`
- `docs/pantheon_gemini_reviewer_v4_architecture.md`

## Forbidden

- `scripts/agy_seo_copy_pipeline.py`
- `scripts/agy_content_publisher.py`
- 既有Gemini coordinator／publisher plist或installer
- `app/**`、文章、queue registry、sitemap、feed、prerender
- login、OAuth、credential value、global CLI設定
- retry、fallback、within-operation key rotation
- merge、網站deploy、文章publish、default transport promotion

## Gate 1

`PASS`

- 實體卡已建立，base為已推送quota-sharding candidate。
- 已確認現有正式coordinator每60秒巡檢另一個queue，不得復用。
- 採獨立daemon與保守6小時cadence；可逆停止。
- frontier：先補RED測試，再做最小shadow runtime與launchd installer。

## Gate 2

`PASS`

- 獨立runtime、UTC六小時bucket、per-bucket queue、lock與closed observation已落地。
- 同一bucket重入實測只回cached observation，沒有第二個process或resend。
- installer `check`、plist lint與可逆stop／uninstall介面通過。
- 既有Gemini coordinator plist、queue、state與程式均未修改。

## Gate 3

`PASS_WITH_LIVE_OBSERVATION`

- focused shadow：6 passed。
- affected suites：235 passed。
- `py_compile`、`bash -n`、`plutil -lint`、installer check與
  `git diff --check`通過。
- LaunchAgent已啟用，interval為21600秒，RunAtLoad執行一筆。
- 第一筆選擇`account-1`，durable `COMPLETE/1/CLI_NONZERO`，
  closed diagnostic為`PROVIDER_UNAVAILABLE`；automatic resend為false。
- 同bucket實測cached，不重送。下一bucket維持常駐觀察。
- 未讀文章、未publish、未deploy、未切正式transport。
