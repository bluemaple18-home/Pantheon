# APF-001 自動來源與 Campaign 契約

## 邊界

`build_campaign_dry_run_workset` 只讀取題庫、既有 article registry、coordinator queue 與 Publisher rewrite ledger，回傳排序固定的 JSON。它不建立 run、queue、lock、outbox、ledger 或 article；`dry-run-campaign --output` 唯一可選寫入是明示指定的報告檔。

## 穩定 identity

每個 work 的 `work_id` 是下列 canonical JSON 的 SHA-256 前 24 碼：`source_kind`、`article_id`、`locale`、`campaign_version`。同一輸入重跑結果不變；版本變更必定產生不同 identity。

## 四 lane 與 owner／I/O

| Lane | 來源 | 去重 | 本卡輸出 | 下游 seam |
| --- | --- | --- | --- | --- |
| `new` | `build_matrix_backlog`（已排除已發布 registry） | 任一既有 create run 的 article id | `matrix` work item | 既有 `seed_new_matrix_runs` / coordinator |
| `rewrite` | `legacy_article_records` + `_existing_rewrite_inventory` | 任一既有 rewrite run 的 article id | `legacy` work item | 既有 `seed_legacy_rewrite_runs` / Publisher backlog |
| `i18n-new` | `new` publication candidate | 現存 translation run 的 `(source_article_id, locale)` | 衍生 work item，無 translation run | 既有 multilingual enqueue |
| `i18n-rewrite` | `rewrite` publication candidate | 現存 translation run 的 `(source_article_id, locale)` | 衍生 work item，無 translation run | 既有 multilingual enqueue |

Coordinator 仍是 queue、state、lock 與 lane routing 的唯一 owner；Existing Publisher 仍是 rewrite backlog 與 publication owner。本卡沒有新增任何 owner。

## 使用方式

```bash
.venv/bin/python -m scripts.agy_gemini_coordinator \
  --repo-root . --queue-root /path/to/queue \
  dry-run-campaign --state-root /path/to/publisher-state \
  --campaign-version apf-001-v1 --output /path/to/workset.json
```

不傳 `--output` 時，CLI 只將 JSON 印到 stdout。i18n 預設 locales 為 `en`、`ja`、`ko`；可重複傳入 `--locale` 取得受限子集合。
