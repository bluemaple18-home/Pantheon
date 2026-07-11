# SEO / GEO Repo Intake Manifest

日期：2026-07-11
範圍：專門用於 SEO、GEO、AEO、AI visibility、competitor audit、crawler、schema、citation monitoring 的公開 GitHub 專案。

## 結論

這批 repo 才是 Pantheon 競品 SEO/GEO 工具應該優先吸收的來源。前一份 `artifacts/fortune_council/competitor_git_intake/source_manifest.md` 是命理產品題材與資料邊界，不是 SEO/GEO 工具來源。

短期策略：

1. 不 clone、不執行未知 repo code。
2. 先抽功能設計、檢查清單、score 維度、輸出格式與 agent workflow。
3. 只把穩定、可驗證、授權清楚的概念併進 `scripts/competitor_seo_tool.py` 與內容 QA gate。
4. API 型或需外部金鑰的 AI visibility 測試先做 interface，不硬接 provider。

## 第一梯隊：直接參考架構

| 專案 | GitHub | 授權 | 可抽取元件 | 對 Pantheon 的接法 |
|---|---|---|---|---|
| Auriti Labs GEO Optimizer | `https://github.com/Auriti-Labs/geo-optimizer-skill` | MIT | GEO/AEO audit、AI citation 檢查、llms.txt、ai.txt、schema、MCP/CLI 入口 | 作為我們 SEO/GEO Reviewer Agent 的最高優先參考；先抽 scoring 維度與檢查清單 |
| Aperture | `https://github.com/anyin-ai/aperture` | MIT | AI visibility monitoring、brand mention tracking、competitor comparison、BYOK self-host | 抽「品牌在 ChatGPT/Perplexity/Google AI Overviews 是否被提及」的監控資料模型 |
| GEO AEO Tracker | `https://github.com/danishashko/geo-aeo-tracker` | 未標明 | Local-first AI visibility dashboard、6 AI models、品牌曝光監控 | 只抽 dashboard 指標與資料結構；license 未標明，不碰 code |

## 第二梯隊：Audit / Skill 工作流

| 專案 | GitHub | 授權 | 可抽取元件 | 對 Pantheon 的接法 |
|---|---|---|---|---|
| Ultimate SEO GEO | `https://github.com/mykpono/ultimate-seo-geo` | MIT | Audit / Plan / Execute 三模式、SEO+GEO score、E-E-A-T、schema generation、診斷腳本 | 抽 agent 模式、report layout、scored finding 格式 |
| SEO GEO Audit | `https://github.com/dageno-agents/seo-geo-audit` | MIT | Collect / Audit / Fix / Monitor / Report、competitive analysis、多層輸出模板 | 抽五階段流程與 boss/operator/specialist 報告格式 |
| geo-seo-claude | `https://github.com/zubair-trabzada/geo-seo-claude` | MIT | GEO-first SEO skill、citability scoring、AI crawler analysis、schema、PDF reports | 抽 citability、crawler accessibility、platform-specific optimization 維度 |
| GeoSkills | `https://github.com/Cognitic-Labs/geoskills` | Apache-2.0 | 6 個 Agent Skill：audit、fix、schema、citation、monitor、report | 抽 skill 切分方式，轉成 Pantheon 多 agent reviewer pipeline |

## Knowledge Base / Crawler

| 專案 | GitHub | 授權 | 可抽取元件 | 對 Pantheon 的接法 |
|---|---|---|---|---|
| Awesome GEO | `https://github.com/amplifying-ai/awesome-generative-engine-optimization` | CC0-1.0 | GEO/AEO/LLMO 工具、paper、framework 清單 | 作為研究更新來源，不直接併 code |
| Firecrawl | `https://github.com/firecrawl/firecrawl` | AGPL-3.0 | 網站 crawl、scrape、search、agent-ready context | 不 vendoring；若要用只走外部服務或 MCP 邊界 |
| Firecrawl MCP Server | `https://github.com/firecrawl/firecrawl-mcp-server` | MIT | MCP crawler/search/scrape 入口 | 可參考 MCP 介面；是否接入要另開工具邊界卡 |

## 對我們工具的元件拆解

### 現有 `competitor_seo_tool.py` 已有

- crawler：首頁、RSS、分類、文章樣本。
- technical SEO：robots、sitemap、canonical、meta description、H1/H2、JSON-LD。
- competitor gap：用 Pantheon keyword matrix 對照競品標題/摘要/分類/H1/H2。
- playbook：30/60/90 天內容作戰。

### 應從 SEO/GEO repo 補進來

- `llms.txt` / `ai.txt` audit。
- AI crawler accessibility：是否封鎖 GPTBot、Google-Extended、PerplexityBot、ClaudeBot。
- Schema 深度：Article、FAQPage、BreadcrumbList、Organization、Person、WebSite、SearchAction。
- E-E-A-T：作者、更新日期、來源引用、about/contact/editorial policy。
- Citability score：頁面是否有可引用短答案、來源、統計、FAQ、定義句。
- Entity audit：品牌、產品、人物、主題 entity 是否一致。
- AI visibility monitor：同一組 prompt 定期問 ChatGPT/Gemini/Perplexity/Claude，記錄是否提到 Pantheon 和競品。
- Competitor comparison：同題 prompt 下的 share of voice、引用網址、語氣、排名位置。
- Report modes：Boss summary / operator task list / specialist evidence。

### 暫不直接接入

- 任何需要商業 API key 的 provider，不先綁死。
- AGPL crawler code 不 vendoring。
- license 未標明 repo 不複製 code。
- 不宣稱能真實測 Google AI Overview citation，除非有可重現的瀏覽器/搜尋證據。

## SEO/GEO Reviewer Agent 目標流程

```text
輸入：自己網站 + 3 到 10 個競品網址
↓
Crawler Agent
↓
Technical SEO Agent
↓
GEO / AEO Agent
↓
Schema / Entity Agent
↓
Content Gap Agent
↓
AI Visibility Agent
↓
Report Agent
```

輸出：

- SEO score
- GEO score
- AI visibility score
- content gap
- keyword gap
- schema gap
- citation gap
- llms.txt / ai.txt 建議
- 逐頁修正清單
- 30 / 60 / 90 天作戰計劃

## 給 `competitor_seo_tool.py` 的接法

- 這份 manifest 是工具預設 `--source-intake`。
- 先讓 playbook 引用這份 repo intake，確保另一個對話框知道我們要吸收的是 SEO/GEO 專案，不是命理題材 repo。
- 下一版工具優先補 `llms.txt`、`ai.txt`、AI bot robots、E-E-A-T、citability、entity/schema score。
