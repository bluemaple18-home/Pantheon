# CARD-PANTHEON-CODEX-EMERGENCY-CONTENT-BATCH-C-20260726

## 任務契約

- ownership: 舊文改寫與英日韓翻譯
- thickness standard
- model: gpt-5.5 medium
- allowed output: `artifacts/fortune_council/codex_emergency_content_20260726/batch_c/`
- fixed rewrite ids: `codex-emergency-rewrite-c-001`, `codex-emergency-rewrite-c-002`

## 工作範圍

- 先掃 registry/rewrite mapping。
- 從尚未有 rewrite 對應的 legacy 占星文章選 2 篇，記錄 source ID/file。
- 完成實質繁中改寫。
- 每篇各做 EN/JA/KO 翻譯。
- manifest 每份翻譯標 `source_kind: rewrite` 與 rewrite ID。

## 交付物

- `manifest.json`
- 2 份改寫
- 6 份翻譯
- `quality-report.md`

## 禁止範圍

- 禁止修改原始舊文、`app/**`、registry、sitemap、feed、redirect、publisher、queue、ledger、launchd、V4、production。
- 不得處理 rejected/failed/quarantined/deferred。
- 禁止發布、push、merge、Gemini、API。
- 禁止使用 5.6。

## 驗證

- worktree capability preflight
- 實質差異、語言、結構、術語、禁詞、重複句與翻譯來源檢查
- `git diff --check`
- 單一 candidate commit
