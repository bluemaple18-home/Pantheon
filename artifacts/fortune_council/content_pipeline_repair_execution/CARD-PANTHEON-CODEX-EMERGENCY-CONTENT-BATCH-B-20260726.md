# CARD-PANTHEON-CODEX-EMERGENCY-CONTENT-BATCH-B-20260726

## 任務契約

- ownership：新文 B 與英日韓翻譯。
- model：gpt-5.5 medium。
- thickness：standard。
- 唯一輸出目錄：`artifacts/fortune_council/codex_emergency_content_20260726/batch_b/`。
- 固定新文 ID：`codex-emergency-new-b-001`、`codex-emergency-new-b-002`。
- 每篇輸出繁中公開文章各 1 份，並各做 EN、JA、KO 翻譯。
- manifest 中每份翻譯必標 `source_kind:new` 與 source ID。

## 可改範圍

- 允許建立本卡。
- 允許建立 `artifacts/fortune_council/codex_emergency_content_20260726/batch_b/` 下內容包。

## 禁止範圍

- 禁止修改 `app/**`、registry、sitemap、feed、redirect、publisher、queue、ledger、launchd、V4、production。
- 禁止發布、push、merge、Gemini、API。
- 禁止命理保證與醫療、財務、法律承諾。

## 驗收

- 輸出必含 `manifest.json`、2 份繁中、6 份翻譯、`quality-report.md`。
- 先掃 registry/既有文章，證明 title、slug、search intent 不重複。
- 檢查語言、結構、術語、禁詞、重複句、唯一性與翻譯來源。
- 執行 worktree capability preflight、`git diff --check`。
- 交付單一 candidate commit。
