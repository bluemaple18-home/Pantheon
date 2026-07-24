# Pantheon GSC 每日資料管線

這條管線只使用 Google Search Console `webmasters.readonly` scope，抓取
`sc-domain:mysticpantheon.com` 中 `/articles/` 的 finalized `page × query` 資料。

## Credential

本機 credential 放在 `~/.config/pantheon-gsc/`：

- `client.json`：Google Desktop OAuth client
- `token.json`：OAuth refresh/access token

兩檔均須為 `0600`，不得加入 Git。也可用 `GSC_CONFIG_DIR` 指定其他目錄；
臨時執行仍支援 `GSC_ACCESS_TOKEN`。

Google Auth Platform 必須維持 Production（控制台顯示「實際運作中」）。
Testing 模式簽發的 refresh token 會帶短期到期限制，不適合每日排程。

## 手動抓取

預設抓取三天前的 finalized 成效資料：

```bash
.venv/bin/python -m scripts.gsc_daily_fetch
```

指定日期或重抓：

```bash
.venv/bin/python -m scripts.gsc_daily_fetch \
  --start-date 2026-07-21 \
  --end-date 2026-07-21 \
  --force
```

快照寫入 `.work/gsc-data/daily/<property>/<date>.json`。同一天已存在時預設
不覆寫；使用 `--force` 才會原子替換。快照保留查詢範圍、產生時間、分頁狀態、
可見列合計與結構化 warnings。

## 每日索引與 Breadcrumb URL 快照

`scripts.gsc_daily_inspection` 以正式站 Sitemap 作為每日 URL inventory，逐頁保存：

- GSC 索引 verdict、coverage、robots/noindex、抓取狀態、最後抓取時間與 canonical。
- GSC 是否辨識到 Breadcrumb rich result 及其 errors/warnings。
- 正式頁面 JSON-LD `BreadcrumbList` 的 `position / name / URL`。
- 與前一份快照相比的 URL 新增／移除、索引欄位變化與 Breadcrumb URL chain 變化。

Sitemap 只提供「要檢查哪些已知公開 URL」，不被當作索引成功證據。報表依實際
URL Inspection 與頁面 JSON-LD 分成：

- `indexed_gsc_breadcrumb`
- `indexed_declared_not_recognized`
- `indexed_no_declared_breadcrumb`
- `not_indexed_declared_breadcrumb`
- `not_indexed_no_declared_breadcrumb`
- `unknown`

其中 `diagnosis_queue` 收斂需要研究的 URL，保留 coverage、fetch、indexing、
robots 與 canonical 欄位；`non_indexed_reason_counts` 則彙總未索引原因。未知或
API 失敗不會被誤算成未索引。

手動執行：

```bash
.venv/bin/python -m scripts.gsc_daily_inspection
```

快照寫入 `.work/gsc-data/url-inspection/YYYY-MM-DD.json`。首日標為 baseline，
第二天起才產生跨日變化。Sitemap 或單頁抓取失敗會保留結構化 warning，不會
把 URL 靜默排除。

## 每日排程

macOS 使用者排程預設每天 06:15 依序抓取 finalized 成效資料，以及當天的
索引／Breadcrumb URL 快照：

```bash
bash scripts/install_gsc_daily_fetch_launchd.sh
```

檢查狀態：

```bash
launchctl print "gui/$(id -u)/com.pantheon.gsc-daily-fetch"
```

停止排程：

```bash
launchctl bootout "gui/$(id -u)" \
  "$HOME/Library/LaunchAgents/com.pantheon.gsc-daily-fetch.plist"
```

stdout/stderr 位於 `~/Library/Logs/Pantheon/`。安裝程式不會複製或改寫 OAuth
credential。

## 資料邊界

- 每頁最多 25,000 rows，使用 `startRow` 持續分頁。
- 預設安全上限 250,000 rows；碰到上限時輸出 `MAX_ROWS_REACHED`，程序以
  exit code `2` 結束，快照標為 partial。
- 查詢結果為零時輸出 `NO_ROWS` 並標為 partial，避免資料消失時靜默成功。
- `visible_row_totals` 只代表 API 回傳列的加總，不等於 GSC UI 的全站總計。
- `.work/` 已被 `.gitignore` 排除，原始查詢資料不進版控。
