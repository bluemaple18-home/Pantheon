---
card_id: TASK-005
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

# TASK-005：內容發布與索引驗收閘門

## 目標

建立發布後索引觀察閘門，避免把「發布隔天尚未索引」誤判成故障，同時能抓出超過觀察期仍未索引、noindex、canonical 分裂與無法發現的頁面。

## 已知證據

- 2026-07-19 發布批次目前 50/50 已索引。
- 2026-07-23 發布 68 頁；到 7/24 為 8 已索引、57 已發現未索引、3 unknown。
- 2026-07-24 發布 8 頁；同日皆仍在等待或 unknown。
- 目前資料不足以把 7/23、7/24 批次判成 Google 停止檢索；需要至少 7 天觀察窗口與每日差異。

## 工作範圍

- 實作可讀取每日 URL inspection snapshot 的離線 gate。
- 分類至少包含：`indexed`、`new_under_observation`、`overdue_discovered`、`overdue_unknown`、`blocked_by_noindex`、`canonical_split`。
- 預設觀察窗口 7 天，可由 CLI 調整。
- 同日／隔日未索引只能警告，不得讓 gate 失敗；超期或明確技術阻擋才失敗。

## 輸入契約

Snapshot JSON 至少可含：

- `inspection_date`
- 每列 `url`
- `published_date`（或可推導日期）
- `verdict`
- `coverage_state`
- `indexing_state`
- `robots_txt_state`
- `page_fetch_state`
- `user_canonical`
- `google_canonical`

工具需清楚回報缺欄位，不得靜默猜測。

## 可修改檔案

- `scripts/seo_publish_gate.py`（可新增）
- `tests/test_seo_publish_gate.py`（可新增）
- `docs/seo_publish_gate.md`（可新增）

## 禁止範圍

- 不修改文章本文、registry、生成頁、sitemap、feed。
- 不修改 `scripts/gsc_*`。
- 不部署、不修改 GSC 或外部控制面。
- 不碰其他任務卡檔案。

## 驗收

1. CLI 支援指定 snapshot、觀察天數與 machine-readable JSON 輸出。
2. 測試覆蓋所有分類與 gate exit code。
3. 使用 fixture 證明隔日未索引不失敗、超過 7 天仍未索引會失敗。
4. 執行受影響測試與 `git diff --check`。

## 回報契約

回報 `status`、`summary`、`files_changed`、`tests_run`、`example_result`、`ready_for_review`。
