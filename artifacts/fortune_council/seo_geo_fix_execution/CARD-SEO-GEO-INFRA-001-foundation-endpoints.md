# CARD-SEO-GEO-INFRA-001｜SEO / GEO 基礎端點修復

## 任務目的

先暫停關鍵字對標，補齊 Pantheon 公開站的基礎 SEO / GEO endpoint，避免 audit、AI crawler 與搜尋引擎拿到 SPA fallback 或 404。

## 請讀

- `main.py`
- `app/web/_redirects`
- `app/web/robots.txt`
- `app/web/sitemap.xml`
- `scripts/competitor_seo_tool.py`
- `docs/competitor_seo_tool.md`

## 任務範圍

- `/llms.txt` 回真文字檔，不可回 HTML fallback。
- `/ai.txt` 回真文字檔，不可回 HTML fallback。
- `/feed/` 與 `/feed.xml` 回 RSS XML。
- FastAPI 與 Cloudflare Pages `_redirects` 都要支援。
- 本機 audit 不可因 feed 內 production 絕對 URL 混到 live 頁面。

## 接受標準

- `own_site/seo_audit.md` 顯示 `llms.txt：present`。
- `own_site/seo_audit.md` 顯示 `ai.txt：present`。
- endpoint 表顯示 `feed: present`、`llms_txt: present`、`ai_txt: present`。
- 本機 audit 的 page audits 使用 `http://127.0.0.1:8799/...`，不混 `https://mysticpantheon.com/...` live HTML。
- `pytest tests/test_web.py tests/test_competitor_seo_tool.py` 通過。
- `git diff --check` 通過。

## 證據路徑

`artifacts/fortune_council/seo_geo_fix_execution/evidence/foundation_endpoints/`
