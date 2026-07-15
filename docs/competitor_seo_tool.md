# 競品 SEO 作戰工具

## 目的

`scripts/competitor_seo_tool.py` 用來把公開競品網站拆成可執行的 Pantheon SEO 作戰資料。

## 內部網站介面

啟動 FastAPI 後開啟 `/seo-intel`，可用表單輸入競品網址與選填的自家網站網址。頁面會呼叫 `POST /api/v1/seo/audit`，使用同一套稽核核心回傳：

- Schema depth、E-E-A-T、Citability、Entity 四項分數。
- robots、sitemap、RSS、`llms.txt`、`ai.txt` 端點狀態。
- 抽樣頁面、優先觀察項目與關鍵字內容缺口。
- 有填自家網站時的並排分數與差距。

網站版固定限制 RSS 3 頁、分類 1 頁、抽樣 2–10 頁，只允許公開網站的 HTTP 80 / HTTPS 443，避免內部分享頁成為任意網路掃描器。CLI 參數與完整報告輸出維持不變。

它不是用來複製競品正文、圖片或品牌資產；它只抽取：

- 技術 SEO 缺口：robots、sitemap、canonical、meta description、JSON-LD、H1、內鏈。
- GEO / AEO 缺口：`llms.txt`、`ai.txt`、AI bot robots policy、schema depth、E-E-A-T、citability、entity signals。
- 內容結構：標題公式、分類頻率、RSS 文章樣本、H2/小標模板。
- 關鍵字差距：把競品內容和 `artifacts/fortune_council/content_seo_matrix/keyword_seed_matrix.md` 對照。
- SEO / GEO Git 來源邊界：把 `artifacts/fortune_council/seo_geo_repo_intake/source_manifest.md` 寫進 playbook，提醒本工具應吸收哪些 audit、GEO、AI visibility、schema、citation 方向。
- 作戰手冊：30 / 60 / 90 天要補哪些內容與結構。

## 基本用法

```bash
.venv/bin/python scripts/competitor_seo_tool.py \
  --site-url https://news.click108.com.tw \
  --name Click108 \
  --since 2024-07-10 \
  --max-feed-pages 5 \
  --max-category-pages 1 \
  --sample-limit 10 \
  --source-intake artifacts/fortune_council/seo_geo_repo_intake/source_manifest.md
```

## 自己網站 + 競品比較

```bash
.venv/bin/python scripts/competitor_seo_tool.py \
  --own-site-url https://mysticpantheon.com \
  --own-name Pantheon \
  --site-url https://news.click108.com.tw \
  --name Click108 \
  --since 2024-07-10 \
  --max-feed-pages 5 \
  --max-category-pages 1 \
  --sample-limit 10
```

輸出預設會放在：

```text
output/competitor_seo/<hostname>/
```

以 Click108 為例：

```text
output/competitor_seo/news.click108.com.tw/
```

## 輸出檔

| 檔案 | 用途 |
|---|---|
| `competitor_audit.json` | 完整機器可讀資料 |
| `seo_audit.md` | 技術 SEO 缺口與頁面摘要 |
| `keyword_gap.csv` | Pantheon 關鍵字與競品命中對照 |
| `playbook.md` | 30 / 60 / 90 天 SEO 超車作戰手冊，含 Git / 研究來源邊界 |
| `own_site/seo_audit.md` | 自己網站的同規格 audit |
| `comparison.md` | 自己網站與競品的 SEO/GEO score delta、content gap、優先修正清單 |

## 判讀方式

優先看 `seo_audit.md`：

- 競品缺 sitemap，我們就要保持 sitemap 全量可讀。
- 競品缺 meta description，我們每篇都要補 70-95 字描述。
- 競品缺 Article / FAQPage JSON-LD，我們每篇固定輸出 `Article + FAQPage + BreadcrumbList`。
- 競品分類頁缺 canonical，我們分類頁、topic 頁、文章頁都不能缺。

再看 `keyword_gap.csv`：

- `competitor_hit_count > 0`：競品已經碰到的詞，我們要用更乾淨的 SEO 結構與更完整 FAQ 超過它。
- `competitor_hit_count = 0`：競品沒碰到或覆蓋弱的詞，優先卡位。

最後看 `playbook.md`：

- 30 天：先補第一批 30 篇。
- 60 天：展開塔羅 78 張、MBTI 16 型、紫微十二宮/十四主星。
- 90 天：用 Search Console 看曝光與 CTR，再重寫 title / description / FAQ。

## Click108 目前小樣本結論

小樣本命令已驗證可跑，結果在：

```text
output/competitor_seo/news.click108.com.tw/
```

目前能確認：

- RSS 可讀，適合持續追蹤競品新文。
- sitemap 回 404，是技術 SEO 缺口。
- 多數頁面 meta description 為空。
- 文章頁 canonical 有，但分類頁 canonical 缺。
- JSON-LD 主要只有 BreadcrumbList，缺 Article 和 FAQPage。
- P1 GEO/AEO checks 會另外輸出 `llms.txt`、`ai.txt`、AI bot policy、Schema depth、E-E-A-T、Citability、Entity scores。
- 它的內容強在量、分類內鏈與固定標題公式；我們短期應該用更乾淨的 technical SEO + FAQ/AEO 結構超過它。

### `llms.txt` / `ai.txt` endpoint 狀態

- `present`：HTTP 200，且 content-type / body 看起來是真正的純文字或 Markdown endpoint。
- `missing`：HTTP 404。
- `blocked`：HTTP 401 / 403 或請求錯誤。
- `fallback_html`：HTTP 200，但 body 看起來是 HTML / SPA fallback。
- `invalid_content`：HTTP 200，但 content-type 或 body 不符合該 endpoint 應有內容。

## 已整合的 SEO / GEO Git 來源

工具預設會嘗試讀：

```text
artifacts/fortune_council/seo_geo_repo_intake/source_manifest.md
```

目前判定：

- `Auriti-Labs/geo-optimizer-skill`、`anyin-ai/aperture`、`danishashko/geo-aeo-tracker` 是第一批要研究的 GEO / AI visibility 來源。
- `ultimate-seo-geo`、`seo-geo-audit`、`geo-seo-claude`、`geoskills` 是 Audit / Plan / Execute / Monitor workflow 的主要參考。
- `Firecrawl` 類 crawler 可參考介面，但 AGPL 或 API key 邊界不能直接混進產品。
- 短期要贏 Click108，重點是把 technical SEO、GEO、schema、citability、entity、AI visibility、內鏈與內容量一起做成 reviewer pipeline。

## 注意

這個工具只使用公開頁面資料。不要把競品正文、圖片、Logo、品牌文案直接搬進 Pantheon。
