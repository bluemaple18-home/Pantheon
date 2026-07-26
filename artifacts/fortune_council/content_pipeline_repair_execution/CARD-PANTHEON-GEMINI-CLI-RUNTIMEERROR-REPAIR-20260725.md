# CARD-PANTHEON-GEMINI-CLI-RUNTIMEERROR-REPAIR-20260725

## 任務定位

- Chain：`pantheon-gemini-cli-runtimeerror-repair-20260725`
- Role：implementation only
- Source：`origin/main` at `162f5668ffa9b2c79bca6ec29069b7889d088de0`
- Thickness / risk：strict / high
- Root question：修復新文與舊文 Writer 大量 `RuntimeError`、沒有 APPROVE candidate 而使發布數停滯；先讓失敗原因可安全觀測，再依證據修正本機程式根因。

## 已知證據與假說

- 六個 launchd 服務 loaded；publisher `status=ok/exit0`，但 create/rewrite/translation 無可發布候選。
- Coordinator 持續 seed，排除 seeder deadlock。
- 新舊 worker 有大量 `RuntimeError`；failed receipt 只有 `error_type`，SEO pipeline 的例外訊息與暫存 CLI log 未被安全保存。
- 優先驗證：
  1. CLI nonzero / timeout / not-found / envelope error 未安全分類。
  2. JSON / schema 不合格被誤歸類為 transport runtime。
  3. quota / login / backend outage；若只能由外部修復，fail closed 並回報 `BLOCKED_EXTERNAL_RUNTIME`。

## 可修改範圍

- `scripts/agy_gemini_runner.py`
- `scripts/agy_gemini_outbox.py`
- `scripts/agy_seo_copy_pipeline.py`
- `scripts/agy_gemini_coordinator.py`
- `tests/test_agy_gemini_outbox.py`
- `tests/test_agy_seo_copy_pipeline.py`
- `tests/test_agy_gemini_coordinator.py`
- 本卡與其 evidence 目錄。

## 禁止範圍

- 不新增、改寫、翻譯或發布文章。
- 不刪除、截短、重建或批量重送 queue、failed receipts、ledger、candidate、run state。
- 不降低品質 gate、schema、禁詞或 Reviewer 門檻。
- 不修改登入、credential、API key、全域 Gemini 設定，不更新或替換 CLI，不加入 fallback。
- 不把 V4 升為預設，不改 LaunchAgents，不 reload、push、merge 或 deploy。
- 不保存 prompt、response、raw stdout/stderr、private path、token 或 credential。

## RED → GREEN 契約

1. Public runner 對 CLI nonzero、timeout、not-found、envelope error 產生 closed、stable、redacted `error_code`。
2. Receipt 不含 prompt、response、raw stdout/stderr、credential 或 home path。
3. Coordinator 保留 closed code，且失敗 run 不回到前排阻擋後續候選。
4. JSON/schema、V4 shadow、legacy CLI 與 publisher flow 不退化。
5. Diagnostic 僅允許固定 allowlist 欄位與長度，不保存任意 exception text。

## Controlled probe gate

本 thread 不自行執行真實 Gemini probe。Synthetic 驗證後若仍需要真實 probe，只交付 `READY_FOR_CONTROLLED_PROBE`、candidate SHA、精確工具/model/prompt 摘要、一次請求影響、遮蔽策略與不發布/不寫 queue 命令；由主線再次取得使用者確認。

## 驗證與交付

- 指定 pytest：outbox、SEO pipeline、coordinator，以及受影響 suites（含 content publisher）。
- full pytest、`git diff --check`、`[DBG-` 掃描、secret/prompt/raw stderr leakage 掃描。
- Evidence 至少包含 `root-cause.md`、`red-green.md`、`failure-taxonomy.md`、`verification.md`、`changed-files.txt`。
- 交付只能為：
  - `DELIVERED_CANDIDATE + full SHA`
  - `READY_FOR_CONTROLLED_PROBE + candidate SHA / payload 摘要`
  - `BLOCKED_EXTERNAL_RUNTIME`
- 候選必須單一 commit、worktree clean，不 push；不得自稱已整合、部署或恢復產文。
