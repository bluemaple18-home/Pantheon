# Red → green reproduction

## H1 — create repair contract

可證偽預測：若現況仍是 full-candidate repair，第二次 Writer schema 會包含
已通過的 `title`、`tags`、`faq` 等欄位，而且第一次 deterministic fail
仍會消耗 Reviewer 呼叫。

Red-capable command：

```bash
uv run pytest tests/test_agy_seo_copy_pipeline.py::test_create_machine_length_repair_is_field_bounded_and_reviews_only_after_green -q
```

Red evidence：

```text
FAILED
assert repair schema fields == {slot, description, bodySections}
actual schema additionally allowed answer, faq, primaryKeyword,
secondaryKeywords, tags, title
```

最小修復：

- 由本機 deterministic findings 建立 per-article、per-field repair contract。
- 長度 finding 只授權 `description`／`bodySections`。
- partial payload 合回 prior candidate；未授權欄位保持原值。
- create deterministic gate 未轉綠前建立本機 rejection，不呼叫 Reviewer。
- gate 轉綠後仍執行既有 `validate_candidate`、quality findings、publication
  policy 與獨立 Reviewer。

Green evidence：

```text
4 passed
```

包含 bounded fixture、既有 measured prompt、Reviewer machine-ownership 與
schema/content repair budget 回歸。

## H2 — publisher deployment drift

可證偽預測：若缺少 deployment preflight seam，正確 fixture 無法產生唯讀計畫，
actor／queue／state／runtime／dirty／origin-main／push drift 也不會在同一入口
fail closed。

Red-capable command：

```bash
uv run pytest \
  tests/test_agy_content_publisher.py::test_deployment_preflight_returns_read_only_plan_without_mutation \
  tests/test_agy_content_publisher.py::test_deployment_preflight_fails_closed_on_contract_drift \
  -q
```

Red evidence：

```text
8 failed
AttributeError: module scripts.agy_content_publisher has no attribute deployment_preflight
```

最小修復：

- 新增純唯讀 `deployment_preflight`。
- 鎖定 actor、queue、state、runtime SHA 與 push mode。
- dirty actor、runtime mismatch、local `HEAD != origin/main` 全部
  `PublishBlocked`。
- CLI `--deployment-preflight` 在建立 state root 或進入 publisher 前返回。
- launchd 範本嵌入部署契約；installer 支援 `--preflight`，安裝前亦先執行
  同一唯讀 gate。

Green evidence：

```text
10 passed
bash -n scripts/install_agy_content_publisher_launchd.sh: exit 0
plutil -lint ops/launchd/com.pantheon.agy-content-publisher.plist.example: OK
```

Fixture 在 preflight 前後比對完整檔案 inventory 相同，且 fake Git 僅收到
`status --porcelain`、`rev-parse HEAD`、`rev-parse origin/main`。

## H3 — NEW_ONLY disabled backlog

可證偽預測：若只是 runner disabled 而 summary 未分流，2 個 new active、
3 個 disabled lane active 仍會被合併回報為 top-level `active=5`。

Red-capable command：

```bash
uv run pytest tests/test_agy_gemini_coordinator.py::test_new_only_cycle_advances_one_new_and_skips_non_new_lanes -q
```

Red evidence：

```text
FAILED
assert summary["active"] == 2
actual: 5
```

最小修復：

- `active`／`runnable_active` 在 NEW_ONLY 下只計 `new` lane。
- 非 new active、outbox、processing 以 `disabled_backlog` 分 lane 保留 inventory。
- fixture 比對 stale rewrite outbox bytes，確認未搬動、未刪除、未改寫。

Green evidence：

```text
2 passed
```

包含 NEW_ONLY 與一般 lane-mode summary 回歸。

## Hypothesis decision

- H1：支持。問題位於 repair transport contract 過寬與 Reviewer 呼叫時機。
- H2：支持。核心 publisher 原有 publish-time Git gate，但缺少部署設定的
  獨立唯讀 contract gate。
- H3：支持。runner 已 fail closed；缺口位於 coordinator reporting/lifecycle
  inventory，不需要 queue mutation。
