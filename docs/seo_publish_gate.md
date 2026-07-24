# 內容發布與索引驗收閘門

`scripts/seo_publish_gate.py` 離線讀取每日 URL Inspection snapshot，將新發布頁面的正常索引等待期與真正需要處理的異常分開。它不呼叫或修改 Google Search Console。

## Pantheon GSC snapshot 輸入

每日產出的 snapshot 使用 `observation_date` 與 `records`。GSC inspection 欄位保留原始 camelCase：

```json
{
  "observation_date": "2026-07-24",
  "records": [
    {
      "url": "https://example.com/article",
      "inspection": {
        "available": true,
        "index": {
          "verdict": "NEUTRAL",
          "coverageState": "Discovered - currently not indexed",
          "indexingState": "INDEXING_ALLOWED",
          "robotsTxtState": "ALLOWED",
          "pageFetchState": "SUCCESSFUL",
          "userCanonical": "https://example.com/article",
          "googleCanonical": "https://example.com/article"
        }
      }
    }
  ]
}
```

snapshot 沒有發布日，因此另建 URL→ISO date mapping，例如 `published-dates.json`：

```json
{
  "https://example.com/article": "2026-07-23"
}
```

```bash
uv run python scripts/seo_publish_gate.py snapshot.json \
  --published-dates published-dates.json \
  --observation-days 7 \
  --json
```

每筆 record 也可直接帶 `published_date`，或帶明確 ISO timestamp `published_at`；record 內的日期優先於 mapping。缺少該 URL 的發布日會回報 ERROR 並以 exit code `2` 結束，不會從 URL 或其他欄位猜測。

當 `inspection.available` 為 `true`，`inspection.index` 與上述七個 GSC 欄位都必須存在。若為 `false`，可省略 `index`，gate 會依發布日判定為觀察中或超期 unknown。

## 舊扁平格式相容

仍接受 `inspection_date` 與 `urls[]`。每列使用 snake_case inspection 欄位：`verdict`、`coverage_state`、`indexing_state`、`robots_txt_state`、`page_fetch_state`、`user_canonical`、`google_canonical`，並帶 `published_date`／`published_at` 或搭配相同的 `--published-dates` mapping。

所有日期使用 ISO 格式；欄位缺漏、日期無效或發布日晚於觀察日，都會以 exit code `2` 結束。

## 使用方式

```bash
uv run python scripts/seo_publish_gate.py snapshot.json
uv run python scripts/seo_publish_gate.py snapshot.json --published-dates published-dates.json --json
```

`--json` 僅輸出 machine-readable JSON。exit code：

- `0`：全部已索引，或只有觀察期內的 warning。
- `1`：至少一頁超過觀察期仍未索引，或存在明確技術阻擋。
- `2`：snapshot 或 CLI 輸入不符合契約。

## 分類與嚴重度

| 分類 | 判定 | 嚴重度 |
| --- | --- | --- |
| `indexed` | GSC verdict 明確為 `PASS` | pass |
| `new_under_observation` | 尚未索引，且發布日差不超過觀察天數 | warning |
| `overdue_discovered` | 超過觀察期，coverage 仍為 discovered | fail |
| `overdue_unknown` | 超過觀察期，且無法確認為 discovered/indexed | fail |
| `blocked_by_noindex` | indexing state 明確指出 noindex | fail |
| `blocked_by_robots` | robots.txt state 明確阻擋 | fail |
| `fetch_failed` | page fetch state 明確失敗 | fail |
| `canonical_split` | user canonical 與 Google canonical 同時存在但不同 | fail |

預設觀察期為 7 天，日差等於 7 仍屬觀察中；從第 8 天起才判定超期。技術阻擋與 canonical 分裂不等待觀察期，會立即失敗。

`INDEXING_ALLOWED` 只表示允許索引，不代表已索引；例如 `NEUTRAL` + `Discovered - currently not indexed` 在觀察期內為 warning，第 8 天起為 `overdue_discovered`。
