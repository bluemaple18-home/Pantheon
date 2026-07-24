# GSC 歷史索引異常診斷 Runbook

## 目的與判定邊界

本 runbook 只診斷五個歷史異常 URL 的現行網站輸出，不把 GSC 保存的舊狀態當成目前仍有 repository bug，也不以改寫內容刺激索引。

固定目標：

- `/articles/career/career-0001`
- `/articles/personality/personality-0017`
- `/articles/tarot/tarot-0048`
- `/articles/tarot/tarot-0009`
- `/articles`

`scripts/index_anomaly_audit.py` 檢查 HTTP status、`X-Robots-Tag`、meta robots、self-path canonical、title、description、H1、`og:url`、JSON-LD URL，以及完整 sitemap HTML 掃描所得的 inbound internal links。

分類契約：

- `目前仍有 bug`：現行 response 有非 200、noindex、canonical／metadata 問題，或完整掃描證明沒有 inbound internal link。
- `目前已修復等待重抓`：現行輸出健康，已知異常是舊 noindex／canonical 訊號。
- `需要更多證據`：現行輸出健康，但只有「已發現、從未檢索」訊號；或內鏈掃描不完整。這不授權修改內容。

## 對指定 base URL 執行

從 repository root 執行：

```bash
uv run python scripts/index_anomaly_audit.py \
  --base-url http://127.0.0.1:8000 \
  --pretty
```

base URL 模式先讀 `/sitemap.xml`，再以相同 base URL 抓取 sitemap 內頁面；因此可測 local／preview 環境，即使 sitemap `<loc>` 使用 production origin。若 sitemap 無效、超過 `--max-discovery-pages`，或任一 discovery response 失敗，`discovery_complete` 會是 `false`，缺少 inbound link 不會被判成 bug。

掃描預設使用 8 個 workers，可用 `--workers` 調低；JSON 僅列前 20 個 inbound sources，完整數量保留在 `inbound_source_count`。

有 `目前仍有 bug` 時程序回傳 1；其餘回傳 0。HTTP 失敗會留在對應 URL 的 `status` 與 `current_issues`，不會被歷史訊號掩蓋。

## 對保存 fixture 執行

fixture 適合重播 response 證據，不依賴個人瀏覽器：

```json
{
  "discovery_complete": true,
  "responses": {
    "/articles": {
      "status": 200,
      "headers": {"content-type": "text/html"},
      "body": "<!doctype html>..."
    },
    "/some-internal-source": {
      "status": 200,
      "headers": {},
      "body": "<a href=\"/articles\">最新文章</a>"
    }
  }
}
```

```bash
uv run python scripts/index_anomaly_audit.py \
  --fixture <fixture.json> \
  --pretty
```

只有 fixture 確實包含宣稱範圍內全部 HTML discovery sources 時，才可設 `discovery_complete: true`。header 名稱不分大小寫；fixture loader 會正規化。

## 本卡五個 URL 的現況與下一步

以本卡乾淨 baseline 的預渲染頁、Cloudflare exact rewrite，以及 2026-07-24 對 `https://mysticpantheon.com` 執行的完整 sitemap audit 判讀。production audit 結果為 0 個現行 bug、4 個等待重抓、1 個需要更多證據：

| URL | 現行 repository 證據 | 分類 | 下一步 |
| --- | --- | --- | --- |
| `/articles/career/career-0001` | 200、無 X-Robots noindex、index/follow、self-path canonical、完整 metadata/JSON-LD；22 個 inbound sources | 需要更多證據 | 不改內容；用 GSC live test 或後續抓取紀錄確認 Googlebot 是否實際取得現行 response |
| `/articles/personality/personality-0017` | 200、無 X-Robots noindex、index/follow、self-path canonical、完整 metadata/JSON-LD；2 個 inbound sources | 目前已修復等待重抓 | 等待 Google 重抓，覆寫 7/12 舊 noindex／X-Robots 狀態 |
| `/articles/tarot/tarot-0048` | 200、無 X-Robots noindex、index/follow、self-path canonical、完整 metadata/JSON-LD；2 個 inbound sources | 目前已修復等待重抓 | 等待 Google 重抓，覆寫 7/12 舊 noindex／X-Robots 狀態 |
| `/articles/tarot/tarot-0009` | 200、無 X-Robots noindex、index/follow、self-path canonical、完整 metadata/JSON-LD；4 個 inbound sources | 目前已修復等待重抓 | 等待 Google 重抓，覆寫 7/11 舊 alternate canonical |
| `/articles` | 200、無 X-Robots noindex、index/follow、self-path canonical、完整 metadata/JSON-LD；448 個 inbound sources | 目前已修復等待重抓 | 等待 Google 重抓並重新評估 canonical |

## 外部動作邊界

本 audit 不部署、不呼叫 GSC API、不送出「要求建立索引」，也不證明 Google 已重抓。若要執行 GSC URL Inspection live test、要求索引或部署，必須由外部控制面 owner 另行授權並保存時間戳與結果。
