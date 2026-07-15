# CARD-SEO-GEO-FIX-001｜工具 Hardening：Endpoint 誤判修正

## 任務目的

修正 `scripts/competitor_seo_tool.py` 對 `llms.txt` / `ai.txt` 的 false positive。現在 Pantheon 顯示 `present`，但回傳大小與 feed 相同，可能是 SPA fallback HTML，不一定是真檔案。

## 請讀

- `scripts/competitor_seo_tool.py`
- `docs/competitor_seo_tool.md`
- `output/competitor_seo/news.click108.com.tw/own_site/seo_audit.md`
- `artifacts/fortune_council/seo_geo_repo_intake/source_manifest.md`

## 任務範圍

- 增加 endpoint content validation。
- `llms.txt` 應檢查 content-type、body 是否為純文字或 markdown、是否包含合理的站點摘要/URL/section。
- `ai.txt` 應檢查 content-type、body 是否為純文字或 markdown、是否包含 AI policy / usage / citation 類資訊。
- 404 fallback HTML、SPA fallback、首頁 HTML 不得標為 `present`。
- 報告中要顯示 `present` / `missing` / `blocked` / `fallback_html` / `invalid_content`。

## 接受標準

- `mysticpantheon.com/llms.txt` 和 `/ai.txt` 若是 fallback，必須被標為 `fallback_html` 或 `invalid_content`。
- Click108 的 `/llms.txt`、`/ai.txt` 仍應標為 `missing`。
- `comparison.md` 不能再把 fallback 當優勢。

## 驗證

```bash
.venv/bin/python -m py_compile scripts/competitor_seo_tool.py
.venv/bin/python scripts/competitor_seo_tool.py --help
.venv/bin/python scripts/competitor_seo_tool.py \
  --own-site-url https://mysticpantheon.com \
  --own-name Pantheon \
  --site-url https://news.click108.com.tw \
  --name Click108 \
  --since 2024-07-10 \
  --max-feed-pages 2 \
  --max-category-pages 1 \
  --sample-limit 5
git diff --check
```

## 證據路徑

`artifacts/fortune_council/seo_geo_fix_execution/evidence/tool_hardening/`
