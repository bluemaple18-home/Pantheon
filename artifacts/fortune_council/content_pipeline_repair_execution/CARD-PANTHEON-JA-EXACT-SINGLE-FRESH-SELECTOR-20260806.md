---
card_id: CARD-PANTHEON-JA-EXACT-SINGLE-FRESH-SELECTOR-20260806
status: DELIVERED_CANDIDATE
type: implementation
risk: production-control-plane
base_sha: cb845df125a3acabfcd4661fd3919ccf251b97bc
---

# 補齊 JA single-fresh exact selector

## 目標

在既有 queue → multilingual pipeline → Publisher 骨架中，補最小 selector，使一個全新 `ja/i18n-new` run 能由既有 publisher transaction 發布，並保留 commit、tag、`pushed: true` 證據。

## 邊界

- 不新增第二套 pipeline，不直接 apply locale module／registry，不手建 queue JSON。
- selector 必須只處理明確指定的新 run ID，禁止 fallback、broad sweep、KO、rewrite、舊 run 或 replacement lineage。
- 不修改品質 gate、Reviewer、模型、queue schema、publisher release gate 或 i18n LaunchAgent。
- production 不執行；交付 candidate commit、測試與 evidence，主線另行 review／部署／canary。

## 驗收

- RED/GREEN：只選取指定 JA fresh run；拒絕缺 selector、非 JA、非 fresh、舊 run、或多 run。
- 端到端 fixture 證明路徑會走既有 publisher transaction contract，而不是 direct apply。
- 受影響測試、compile、`git diff --check` 通過；changed files 限於入口、selector、測試與本卡 evidence。

## Candidate evidence

👉 [假設與目標確認]：目標是以單一 `--exact-fresh-ja-run-id` 將既有完整
translation transaction 限縮為一個 fresh `ja/i18n-new` run；邊界是不變更
queue schema、locale apply、Reviewer、品質或 release gate；驗收為 selector
fail-closed 與既有 transaction evidence contract 保持完整。

- 新入口：`scripts/agy_content_publisher.py --exact-fresh-ja-run-id RUN_ID`。
- selector 拒絕：缺失／多個 selector、找不到或多筆 state、非 `ja`、
  `i18n-rewrite`、retry 舊 run、terminal ledger 舊 run，以及 ID／state 的
  replacement lineage。
- 只呼叫既有 `publish_ready_translation_runs(..., max_runs=1,
  exact_run_ids=[RUN_ID])`；完整 transaction 仍產出 `commit_sha`、tag 與
  `pushed` evidence，未改 direct apply 或 release gate。
- RED：新增測試後，因專用 entrypoint 尚不存在而有 6 例失敗。
- GREEN：`uv run pytest -q tests/test_agy_content_publisher.py -k
  'exact_fresh_ja_selector'` → `7 passed, 94 deselected`。
- 回歸：`uv run pytest -q tests/test_agy_content_publisher.py` → `101 passed`
  （既有一個 SyntaxWarning）；`uv run pytest -q
  tests/test_agy_multilingual_pipeline.py` → `177 passed`；`uv run python -m
  py_compile scripts/agy_content_publisher.py tests/test_agy_content_publisher.py`
  與 `git diff --check` 通過。
- 風險：這是本機 fixture 證據，未執行 production、provider、LaunchAgent 或
  push；實際指定 run 仍須由主線核對 fresh state 與另行授權的 transaction。
