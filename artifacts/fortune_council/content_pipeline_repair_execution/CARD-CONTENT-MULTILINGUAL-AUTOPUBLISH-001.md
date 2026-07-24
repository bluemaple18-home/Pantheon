---
card_id: CARD-CONTENT-MULTILINGUAL-AUTOPUBLISH-001
status: IN_PROGRESS
type: implementation
project: Pantheon
created_at: 2026-07-24
owner: mainline
---

# 新文多語自動發布與優先序

## 目標

新繁中文章發布後，同步為英文、日文、韓文建立獨立母語重寫工作。已通過的語系先發布；未通過的工作完整保留，等正常 queue 清空後再處理，不得阻塞其他文章或語系。

## 範圍

- 新文發布後自動 fan-out：`en`、`ja`、`ko`。
- 每個語系使用獨立 run、source hash、deterministic gate、Reviewer 與發布狀態。
- clean approve 的 run 可獨立發布。
- REJECT、schema failure、source drift 與外部失敗保留為 deferred。
- 排序固定為：正常新文／首次翻譯 → clean approve 發布 → deferred 重處理。

## 範圍外

- 舊文 rewrite 流程。
- Gemini V4 預設放量。
- 未通過 gate 的強制核准或自動發布。

## Requirements

- `FR-I18N-AUTO-001`：WHEN 新繁中文章成功發布，系統 SHALL 為 `en`、`ja`、`ko` 各建立一個獨立翻譯 run。
- `FR-I18N-AUTO-002`：WHEN 任一語系 clean approve，系統 SHALL 允許該語系先發布，不等待其他語系。
- `FR-I18N-AUTO-003`：IF 語系 run 未通過，系統 SHALL 保留完整狀態與 evidence，且不得阻塞其他 run。
- `FR-I18N-AUTO-004`：WHILE 正常 queue 尚有可處理工作，系統 SHALL 將 deferred run 排在最後。
- `SC-I18N-AUTO-001`：單一來源文章的三語結果可呈現部分發布，例如 `en=published`、`ja=deferred`、`ko=published`。
- `SC-I18N-AUTO-002`：既有繁中 URL、舊文 rewrite 與 V4 預設 transport 不變。

## Slices

### `SL-I18N-AUTO-QUEUE`

- traces_to：`FR-I18N-AUTO-001`、`FR-I18N-AUTO-003`、`FR-I18N-AUTO-004`
- 內容：定義單語系 run 與 pending／deferred 排序契約。
- 驗證：unit tests 覆蓋 fan-out 唯一性、失敗保留與 deferred-last。
- blocker：無。

### `SL-I18N-AUTO-PUBLISH`

- traces_to：`FR-I18N-AUTO-002`、`SC-I18N-AUTO-001`
- 內容：publisher 獨立套用 clean approve 語系，不要求三語全過。
- 驗證：unit tests 覆蓋部分成功與 source drift fail closed。
- blocker：`SL-I18N-AUTO-QUEUE`。

### `SL-I18N-AUTO-RUNTIME`

- traces_to：全部 requirements 與 success criteria。
- 內容：接入主機 launchd、release record、prerender、feed 與 sitemap。
- 驗證：focused tests、full pytest、`git diff --check`、dry-run 與 launchd exit code。
- blocker：`SL-I18N-AUTO-PUBLISH`。

## 限制

- 不使用 Codex App automation。
- 不把 V4 broker 設為預設。
- 不自動 retry 外部 generation；deferred 必須可稽核。
- 發布仍需 clean origin、測試、release record、tag 與同次 push gate。

## 驗收證據

- focused content pipeline：`89 passed`。
- full pytest：`384 passed, 1 warning`。
- `git diff --check`：PASS。
- runtime：待主線整合後更新 publisher actor 並恢復 launchd。
