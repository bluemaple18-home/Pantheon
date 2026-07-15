# CARD-SEO-GEO-FIX-001 Verification

## Scope

- 修正 `scripts/competitor_seo_tool.py` 的 `llms.txt` / `ai.txt` endpoint false positive。
- 同步 `docs/competitor_seo_tool.md` 的 endpoint 狀態定義。
- 新增 `tests/test_competitor_seo_tool.py` 覆蓋 HTML fallback、XML/feed fallback、真文字檔、404 missing。

## Commands

```bash
.venv/bin/python -m py_compile scripts/competitor_seo_tool.py
.venv/bin/python scripts/competitor_seo_tool.py --help
.venv/bin/python -m pytest tests/test_competitor_seo_tool.py
.venv/bin/python scripts/competitor_seo_tool.py \
  --own-site-url https://mysticpantheon.com \
  --own-name Pantheon \
  --site-url https://news.click108.com.tw \
  --name Click108 \
  --since 2024-07-10 \
  --max-feed-pages 2 \
  --max-category-pages 1 \
  --sample-limit 5
```

## Result

- `py_compile` passed。
- `--help` passed。
- `pytest tests/test_competitor_seo_tool.py` passed：6 tests。
- 實站 audit passed，輸出：`output/competitor_seo/news.click108.com.tw/`。

## Endpoint Evidence

- Pantheon `llms.txt`：`fallback_html`，`body_looks_like_html`，`text/html; charset=utf-8`。
- Pantheon `ai.txt`：`fallback_html`，`body_looks_like_html`，`text/html; charset=utf-8`。
- Click108 `llms.txt`：`missing`，HTTP 404。
- Click108 `ai.txt`：`missing`，HTTP 404。

## Acceptance

- Pantheon fallback 不再被標成 `present`。
- Click108 `/llms.txt`、`/ai.txt` 仍是 `missing`。
- `comparison.md` 不再把 Pantheon fallback 當 endpoint 優勢。
