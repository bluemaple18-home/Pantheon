---
card_id: CARD-PANTHEON-JA-LOCALE-PLAN-TOPOLOGY-REBUILD-REPAIR-20260806
chain_id: pantheon-ja-locale-plan-topology-rebuild-20260806
role: implementation
cycle: 1
status: INTEGRATED_TO_MAIN_AWAITING_PRODUCTION_ALIGNMENT
thickness: standard
risk: medium
model: gpt-5.5
reasoning: medium
model_reason: bounded cross-file prompt and regression repair; no production mutation
implementation_base_sha: d9380d94910eaedb10b4ad8e8b0398a2cdbcce5d
---

# 修正日文 locale plan topology 重建

## 目的

沿用既有 multilingual pipeline，修正真實 Gemini 在 `rebuild_outline=true` 時只改日文標題同義詞、卻保留完全相同 `planned_h2_slot` 配置，最後被既有 deterministic gate 正確拒絕的 production-shaped 缺口。

## 已確認根因

- 失敗格：`ja/i18n-new`，來源 `V2-MBTI-PAIR-ISFJ-ESTJ-LOVE`。
- 第三代 plan 已更換四個日文 H2，但 17 個 fact 的 slot 序列仍完全相同：
  `[h2-1,h2-4,h2-4,h2-3,h2-1,h2-4,h2-3,h2-3,h2-2,h2-1,h2-4,h2-2,h2-4,h2-2,h2-2,h2-4,h2-3]`。
- `_hydrate_locale_plan(...)` 因 `locale plan rebuild reused prior outline topology for article-01` fail closed；此 gate 不應放寬。
- 現有 scripted regression 會主動做 `coverage_shift=1`，只證明模型遵守時 gate 可通過，未覆蓋真實模型對 prompt 的誤解。

## 可修改範圍

- `scripts/agy_multilingual_pipeline.py`
- `tests/test_agy_multilingual_pipeline.py`
- 本卡狀態與同目錄、同卡 ID 的最小驗證 receipt（如有必要）

## 任務

1. 先新增 production-shaped regression fixture／測試，重現「H2 全換成同義詞，但 fact-to-`planned_h2_slot` topology 完全相同」；先證明舊行為不足。
2. 最小強化既有 `_plan_prompt`／repair instruction，明確定義 topology 是各 fact 的 `planned_h2_slot` 配置；當 `rebuild_outline=true` 時，要求在保留全部 fact、safety boundary 與 schema 的前提下，至少一個有意義的 fact 必須改派到不同 H2，且不得只換標題或順序文字。
3. 保留既有 hydration／validation fail-closed 行為；不得以自動 canonicalize、隨機搬移、降低 gate 或忽略 Reviewer findings 來製造通過。
4. 若要調整 prompt 輸入，維持既有 locale plan JSON schema 與正常英文／韓文路徑相容。

## 禁止範圍

- 不改 coordinator、runner、publisher、exact-run routing、queue 或 launchd。
- 不動 production actor、production 排程、credentials、外部 API 或真實產文。
- 不降低 deterministic gate、Reviewer 標準、fact coverage 或 safety boundary。
- 不重寫 multilingual pipeline；不碰 registry、metadata、sitemap、feed、redirects。
- 不 push、不 merge、不部署；只交付候選 commit 給主線整合。

## 驗收

- production-shaped regression 必須能辨識「標題改了但 topology 未改」並驗證新 prompt 給出可機器判讀的重建要求。
- 既有 topology 拒絕測試與 repeated-native-finding 測試保持通過。
- 執行完整 `tests/test_agy_multilingual_pipeline.py`。
- 執行受影響的 exact-run 測試，確認 routing isolation 未回歸。
- 執行 Python compile check 與 `git diff --check`。
- 工作樹只含本卡允許的檔案；交付候選 commit SHA、變更檔、測試證據與殘餘風險。

## 交付狀態語意

此任務最多可回報「已交付候選 commit」。只有主線完成獨立 review、整合、驗收與另行授權的單格 production rerun，才可稱為已整合或已修復上線。

## 主線驗收（2026-08-06）

- 正式 thread：`019fd2ef-cae8-71c3-acf4-1e83780e65ee`
- 原候選 commit：`8c8dfc50e8a3a20fa50fe45710403181e4438d0b`
- 最新主線重放 commit：`b6f8ac31c9114f8b9a1ce406902e3a8d118a7e73`
- 整合 receipt commit：`fb18bdde5942137372cf0882bee4a565e4f7577c`
- 變更範圍：只含 `scripts/agy_multilingual_pipeline.py`、`tests/test_agy_multilingual_pipeline.py`
- 獨立 review：未發現阻塞問題；未放寬 deterministic gate、Reviewer 或 routing isolation
- Multilingual 完整測試：`176 passed`
- Exact-run 所屬測試：`6 passed, 168 deselected`
- Python compile、`git diff --check`、整合 worktree clean：通過
- 全 `tests/ -k exact_run` 的廣域收集另被無關的 `playwright` 未安裝擋住；改以 exact-run 三個所屬測試檔重跑並通過，不影響本卡 verdict
- `origin/main` 已快轉整合；production actor 仍固定在 `d9380d94910eaedb10b4ad8e8b0398a2cdbcce5d`
- 剩餘風險：尚未對齊 production actor，亦未執行真實 Gemini 單格 canary
