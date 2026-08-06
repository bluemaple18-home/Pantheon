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

## Follow-up candidate evidence

- 新增同一 entrypoint 的 local-only prepare 模式：提供
  `--prepare-exact-fresh-ja-source-run-id SOURCE_RUN_ID` 與
  `--prepare-exact-fresh-ja-article-id ARTICLE_ID`，並回傳唯一可重算的 `run_id`。
- prepare 僅透過既有 `enqueue_article_translations(..., locales=["ja"])`
  建立 `brief.json` 與 coordinator queue state；不手寫 queue JSON、不建立 EN／KO、
  不掃描、不呼叫 provider，也不改 Publisher transaction。
- 兩個 ID 缺一、replacement lineage、legacy rewrite source、既有 target run、
  非預期／非單一 queue 回傳都 fail closed。完成 queue run 後仍須使用既有
  `--exact-fresh-ja-run-id` transaction path 才會發布。
- RED：單一 JA queue fixture 因 enqueue API 不接受 `locales` 而失敗。
- GREEN：單一 JA queue fixture與 selector／prepare cases 通過；完整回歸、compile、
  `git diff --check` 見本次 candidate receipt。

## Review repair — deterministic run-ID contract

- Review 發現原 prepare 同時讓 caller 提供任意 `run_id`，卻要求它等於 enqueue
  的 deterministic ID；canary alias 因此永遠 fail closed。
- 選擇契約 A：`translation_run_id(source_run_id, article_id, "ja")` 是唯一可接受
  ID。prepare 不再接收 caller-supplied run ID，而是透過既有 queue API 回傳
  `{"run_id", "locale", "run_dir"}`；CLI JSON output 是後續
  `--exact-fresh-ja-run-id` 的可靠輸入。
- 真實 integration test 使用實際 repository source、`prepare_exact_fresh_ja_translation_run`
  與既有 enqueue contract，驗證回傳 ID、queue state 與 `brief.json` 的 ID 完全一致，
  且僅有一筆 JA run；未 monkeypatch enqueue。
- 仍拒絕 replacement source、legacy/i18n-rewrite、既有 run 與非單一 queue record。
