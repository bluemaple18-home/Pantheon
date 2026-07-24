# CARD-CONTENT-GEMINI-V4-PUBLISH-FINAL-SYNC-001

- card_id: `CARD-CONTENT-GEMINI-V4-PUBLISH-FINAL-SYNC-001`
- chain_id: `CONTENT-GEMINI-V4-PUBLISH-FINAL-SYNC-001`
- ownership: `v4_publish_final_sync_only`
- strictness: `strict`
- risk: `high`
- status: `DELIVERED_CANDIDATE`
- decision: `READY_FOR_ACTIVATION_REVIEW`

## 目標

將已獨立 Review 為 `GO / READY_FOR_FINAL_SYNC` 的 V4×發布主線候選，
與固定發布提交 `1eb311f49c720925501a1fa3dfc9e2b492e71451`（v0.3.8）
做一次可重現的本地 final sync，確認 V4 transport 與最新文章發布內容可共存。

## 固定輸入

- reviewed integration lineage:
  `37c98fa4bbf66c896c4a97b1beccd25593583b0b`
- fixed publisher commit:
  `1eb311f49c720925501a1fa3dfc9e2b492e71451`
- prior integration candidate:
  `b0d0f6dd855bb185c9958c7a9cf6bd0ad178a8cc`
- independent review commit:
  `37c98fa4bbf66c896c4a97b1beccd25593583b0b`

## 允許

- 建立本卡與指定 evidence。
- 將固定 publisher commit 合併至目前候選分支。
- 僅在合併衝突確實發生時，做最小且可證明的衝突解決。
- 跑 V4、legacy、coordinator、publisher 與受影響測試及靜態 gates。

## 禁止

- 不追逐後續浮動的 `origin/main`。
- 不呼叫 Gemini／agy。
- 不修改登入、憑證或全域 CLI 設定。
- 不切換 V4 預設、不移除 legacy fallback path。
- 不 push、deploy、publish、activation。
- 不額外修改文章、registry、metadata、sitemap、feed、prerender 或 automation。

## 驗證

1. 合併提交同時包含 reviewed integration lineage 與固定 publisher commit。
2. V4 production 檔案相對 reviewed lineage byte-identical。
3. 發布內容相對 fixed publisher commit byte-identical。
4. V4 74、legacy 57、coordinator 6、publisher 5，共 142 tests 全綠。
5. `py_compile`、privacy、allowlist、DBG scan、`git diff --check` 全綠。
6. 外部 invocation、push、deploy、publish、activation 均為 `0`。

## Evidence

`artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_publish_final_sync_001/`

必須包含：

- `merge-report.md`
- `verification.txt`
- `changed-files.txt`
- `decision.md`

## 交付

狀態只能：

- `DELIVERED_CANDIDATE / READY_FOR_ACTIVATION_REVIEW`
- `BLOCKED`

本卡不授權把候選推上遠端或切換 production transport。

## 執行結果

- final-sync merge:
  `dcaddc49acd812798a058b36b833fe4fe2a022ec`
- merge parents:
  - `f4a3b71bf0177cc056825a592e05d483185366a9`
  - `1eb311f49c720925501a1fa3dfc9e2b492e71451`
- merge conflicts: `0`
- tests: `205 passed`
- external invocation / push / deploy / publish / activation: `0`
- verdict: `DELIVERED_CANDIDATE / READY_FOR_ACTIVATION_REVIEW`
