---
card_id: CARD-CONTENT-GEMINI-REWRITE-RELEASE-001
status: RUNNING
chain_id: CONTENT-GEMINI-REWRITE-RELEASE-001
risk: high
source_commit: dd46ffe614be602b4f30795c203ddbe0d752ac4a
candidate_manifest: artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_to_050/summary.json
candidate_manifest_sha256: cd2f284f87fdd2a8519ead1d65b3619fffd8ccf22d17d222c691707d920efd1d
target: READY_TO_DEPLOY
deploy_authorized: false
---

# 50 篇 Gemini 改寫候選｜Release Repair 1

## 目標

把既有 50 篇候選修到 50/50 Reviewer APPROVE，deterministic quality 與 uniqueness findings 全部歸零；再以 immutable identity、current-body SHA 與完整 approval manifest 為 gate，套用至正式文章正文並完成可部署驗收。不得執行 deploy 或 publish。

## 固定範圍

- 文章集合與順序以 candidate manifest 的 50 個 `article_ids` 為唯一來源，不得換文、跳號、重複或加入第 51 篇。
- Release repair 每批沿用 Batch 1–10 的五篇邊界；已 APPROVE 文章預設沿用，Writer 只處理 REJECT 文章，Reviewer 每次仍同審完整五篇。
- 每個 Writer 只接收單篇公開 brief、該篇前一版候選、公開 findings 與 variation contract；不得傳送憑證、私人資料或未公開 metadata。
- 不得降低既有字數、段落、禁詞、完整句、H2、24-char n-gram、段落開頭、抽象句型與骨架 gates。
- 單批每一 release generation 最多兩次 Writer/Reviewer attempt；未達 5/5 時保留 evidence，再開下一 generation，不覆寫既有 receipts。

## 套用契約

- 只有總結 evidence 同時證明 50/50 APPROVE、quality findings=0、uniqueness findings=0，才可建立 approval manifest。
- 套用前逐篇驗證 article ID、product、serial、slug、URL、title、description、answer、FAQ、tags、published、updated 與 current-body SHA；只允許 `bodySections` 改變。
- 套用後驗證 50 篇正式正文 SHA 等於 approved candidate SHA，registry 與 metadata identity 零漂移。
- 執行受影響 tests、生成器、`git diff --check`、內容 gate 與必要瀏覽器驗收。
- 終局只可為 `READY_TO_DEPLOY` 或 `BLOCKED`；`READY_TO_DEPLOY` 不代表已部署。

## 可改範圍

- `scripts/agy_seo_copy_pipeline.py`
- `tests/test_agy_seo_copy_pipeline.py`
- `artifacts/fortune_council/content_rewrite_execution/evidence/gemini_rewrite_release_001/**`
- 正式文章 body library 的唯一必要檔案
- 本卡狀態與驗收紀錄

## 禁止範圍

- registry identity、URL、metadata、日期、FAQ、tags、sitemap、feed、redirects
- deploy、publish、遠端控制面、秘密與憑證
- 使用者既有未追蹤 `.ai/`、`AGENTS.md` 與 PNG artifacts
