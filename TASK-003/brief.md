---
card_id: TASK-003
chain_id: SEO-INDEX-20260724
state: CARD_DRAFTED
ownership: implementation
thickness: standard
risk: high
model: user-configured-default
reasoning: user-configured-default
model_reason: 正式 thread 必須沿用使用者在 Codex 選定的模型與推理設定
main_cwd: <repo-root>
worktree_path: pending
provisioning_source: clean repository default branch
---

# TASK-003：統一 www 與 non-www canonical

## 目標

消除 `www.mysticpantheon.com` 與 `mysticpantheon.com` 同時回傳 `200` 所造成的 canonical 分裂，讓 Google 穩定選擇 non-www 正式網址。

## 已知證據

- 38 個 non-www 網址在 GSC 被判定為「重複頁面，Google 選擇的標準網址與使用者不同」。
- 相同路徑的 38 個 www 網址皆為索引通過。
- 現況 www 與 non-www 都回傳 `200`，沒有 host-level redirect。

## 工作範圍

- 先確認 repository 實際可控制的 host redirect／部署設定邊界。
- 若 repository 可安全表達規則，實作 www → non-www 的單一步驟永久轉址並補自動測試。
- 若轉址屬於 Cloudflare、DNS 或其他外部控制面，只交付可直接執行的設定方案與驗證腳本，不得假裝已修改外部狀態。

## 可修改檔案

- `app/web/_redirects`
- `tests/test_host_canonical_redirect.py`（可新增）
- `scripts/verify_host_canonical.py`（可新增）
- `docs/www_canonical_runbook.md`（可新增）

## 禁止範圍

- 不修改文章內容、文章 registry、生成頁、sitemap、feed。
- 不修改 `scripts/gsc_*`。
- 不部署、不修改 Cloudflare、DNS、Google Search Console 或任何外部控制面。
- 不碰其他任務卡檔案。

## 驗收

1. 有明確證據說明轉址應放在 repository 或外部控制面。
2. 若可在 repository 實作，測試覆蓋 HTTP 與 HTTPS、保留 path/query、避免 redirect loop。
3. 執行受影響測試與 `git diff --check`。
4. 在任務 final 列出修改檔案、測試結果、尚需人工執行的外部步驟。

## 回報契約

回報 `status`、`summary`、`files_changed`、`tests_run`、`remaining_external_action`、`ready_for_review`。
