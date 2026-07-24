---
card_id: TASK-004
chain_id: SEO-INDEX-20260724
state: CARD_DRAFTED
ownership: implementation
thickness: standard
risk: medium
model: user-configured-default
reasoning: user-configured-default
model_reason: 正式 thread 必須沿用使用者在 Codex 選定的模型與推理設定
main_cwd: <repo-root>
worktree_path: pending
provisioning_source: clean repository default branch
---

# TASK-004：歷史索引異常頁面診斷與修復

## 目標

針對 5 個不是單純「新頁等待中」的 URL 建立可重現診斷，區分現行網站缺陷與 GSC 歷史殘留；只修有證據的 repository 問題。

## 目標 URL

- `/articles/career/career-0001`
- `/articles/personality/personality-0017`
- `/articles/tarot/tarot-0048`
- `/articles/tarot/tarot-0009`
- `/articles`

## 已知證據

- `career-0001`：GSC 顯示已發現但從未檢索。
- `personality-0017`、`tarot-0048`：GSC 保存 7/12 的舊 noindex／X-Robots 狀態，但目前 HEAD 已無該 header。
- `tarot-0009`：GSC 保存 7/11 的舊 alternate canonical，目前頁面 canonical 已 self-reference。
- `/articles`：GSC 曾選首頁為 canonical，目前頁面 canonical 已 self-reference。

## 工作範圍

- 建立 deterministic audit，檢查狀態碼、robots、canonical、可被內部連結發現性與關鍵 rendered metadata。
- 對每個 URL 給出「目前仍有 bug／目前已修復等待重抓／需要更多證據」分類。
- 只有找到現行 repository 問題時才修改；不得為了刺激索引而亂改內容。

## 可修改檔案

- `scripts/index_anomaly_audit.py`（可新增）
- `tests/test_index_anomaly_audit.py`（可新增）
- `docs/gsc_index_anomaly_runbook.md`（可新增）

## 禁止範圍

- 不修改文章本文、文章 registry、生成頁、sitemap、feed。
- 不修改 `scripts/gsc_*`。
- 不部署、不送出 GSC 要求建立索引、不修改外部控制面。
- 不碰其他任務卡檔案。

## 驗收

1. 稽核工具可對 fixture／指定 base URL 執行，不依賴個人瀏覽器狀態。
2. 五個 URL 都有可追溯分類與下一步。
3. 測試涵蓋 noindex header、meta robots、canonical mismatch、不可發現頁面。
4. 執行受影響測試與 `git diff --check`。

## 回報契約

回報 `status`、`summary`、`per_url_findings`、`files_changed`、`tests_run`、`remaining_external_action`、`ready_for_review`。
