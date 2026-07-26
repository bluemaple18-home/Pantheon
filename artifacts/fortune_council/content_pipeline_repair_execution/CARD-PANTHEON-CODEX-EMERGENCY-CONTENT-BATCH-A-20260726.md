# CARD-PANTHEON-CODEX-EMERGENCY-CONTENT-BATCH-A-20260726

## 任務目的

Pantheon Codex Emergency Content Batch A 正式內容線。建立 artifact-only 候選內容，不修改正式前台、registry、發布佇列或 production 檔案。

## Ownership

- 新文 A 與英日韓翻譯。
- Thickness standard。
- Model target: gpt-5.5 medium。
- 唯一輸出目錄：`artifacts/fortune_council/codex_emergency_content_20260726/batch_a/`。

## 必交付

- 2 篇全新繁中公開文章。
- 固定 ID：`codex-emergency-new-a-001`、`codex-emergency-new-a-002`。
- 每篇各做 EN / JA / KO。
- `manifest.json`。
- `quality-report.md`。

## 內容契約

- 主題限占星 x 職涯 / 人際的可操作解讀。
- 每份翻譯 manifest 必標 `source_kind:new` 與對應 source ID。
- 先掃 registry / 既有文章，證明 title / slug / search intent 不重複。
- 內容需檢查語言、結構、術語、禁詞、重複句、唯一性與翻譯來源。
- 禁止命理結果承諾、醫療承諾、財務承諾、法律承諾。

## 禁止範圍

不得修改：

- `app/**`
- registry
- sitemap
- feed
- redirects
- publisher
- queue
- ledger
- launchd
- V4
- production

不得執行：

- 發布
- push
- merge
- Gemini
- 外部 API
- 5.6

## 驗證與交付

- 執行 worktree capability preflight。
- 執行 `git diff --check`。
- 交付單一 candidate commit。
- 最終只回：`DELIVERED_CANDIDATE`、完整 SHA、數量：新文2、舊文0、EN2(new2)、JA2(new2)、KO2(new2)。
