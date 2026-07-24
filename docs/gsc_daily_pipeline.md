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

預設抓取三天前的 finalized data：

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

## 每日排程

macOS 使用者排程預設每天 06:15 執行，抓取三天前 finalized data：

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
