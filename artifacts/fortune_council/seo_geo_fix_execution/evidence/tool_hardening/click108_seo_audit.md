# Click108 SEO 競品工具報告

- 網站：https://news.click108.com.tw
- 產出時間：2026-07-12T04:20:12+00:00
- RSS 樣本：20 篇
- 頁面 audit：5 頁

## 技術 SEO 缺口

- 競品 sitemap 不完整或不可用；Pantheon 必須保持 sitemap 可讀並列出正式 URL。
- 競品多數頁面 meta description 為空；Pantheon 每篇都要有 70-95 字 description。
- 競品部分分類頁缺 canonical；Pantheon 分類頁、topic 頁、文章頁都要有 canonical。
- 競品 H1 有空值或多 H1 雜訊；Pantheon 每頁維持單一清楚 H1。

## GEO / AEO / AI Visibility 訊號

- llms.txt：missing
- ai.txt：missing
- Schema depth score：14
- E-E-A-T score：64
- Citability score：40
- Entity score：65
- AI bot policy：{'GPTBot': 'allowed_or_partial', 'OAI-SearchBot': 'allowed_or_partial', 'ChatGPT-User': 'allowed_or_partial', 'ClaudeBot': 'allowed_or_partial', 'PerplexityBot': 'allowed_or_partial', 'Google-Extended': 'allowed_or_partial', 'CCBot': 'allowed_or_partial'}

### GEO Findings

- 缺 `llms.txt`；可新增 AI crawler 友善的網站摘要、重要頁面與引用規則。
- 缺 `ai.txt`；可新增 AI 使用政策、品牌描述與允許引用邊界。
- Schema depth 偏低；應補 Article、FAQPage、BreadcrumbList、Organization、WebSite 等結構化資料。
- Citability 偏弱；應補短答案、FAQ、清楚小標、來源/證據段落，讓 AI 更容易引用。

## 端點

- robots: present status=200 bytes=67 http_200
- sitemap: missing status=404 bytes=623551 http_404
- feed: present status=200 bytes=99256 http_200
- llms_txt: missing status=404 bytes=623551 http_404
- ai_txt: missing status=404 bytes=623551 http_404

## 頁面摘要

### https://news.click108.com.tw
- status：200
- title：發燒文章 | 科技紫微網 | The most popular fortune telling website in the world（68）
- description：<empty>（0）
- canonical：https://news.click108.com.tw/
- JSON-LD：[]
- H1：[]
- 內鏈/外鏈/文章/分類：257/40/53/19
- E-E-A-T：author=True published=True modified=False about_contact=False
- Citability markers：['answer_headings', 'structured_blocks', 'scannable_length']

### https://news.click108.com.tw/category/astro/
- status：200
- title：星座 | 發燒文章 | 科技紫微網（17）
- description：<empty>（0）
- canonical：<missing>
- JSON-LD：['BreadcrumbList']
- H1：['星座 好文']
- 內鏈/外鏈/文章/分類：183/40/42/17
- E-E-A-T：author=True published=True modified=False about_contact=False
- Citability markers：['answer_headings', 'structured_blocks', 'scannable_length']

### https://news.click108.com.tw/category/career-main/
- status：200
- title：事業 | 發燒文章 | 科技紫微網（17）
- description：<empty>（0）
- canonical：<missing>
- JSON-LD：['BreadcrumbList']
- H1：['事業 好文']
- 內鏈/外鏈/文章/分類：183/40/46/19
- E-E-A-T：author=True published=True modified=False about_contact=True
- Citability markers：['answer_headings', 'structured_blocks', 'scannable_length']

### https://news.click108.com.tw/category/career-tarot/
- status：200
- title：塔羅事業 | 發燒文章 | 科技紫微網（19）
- description：<empty>（0）
- canonical：<missing>
- JSON-LD：['BreadcrumbList']
- H1：['塔羅事業 好文']
- 內鏈/外鏈/文章/分類：183/40/39/18
- E-E-A-T：author=True published=True modified=False about_contact=False
- Citability markers：['answer_headings', 'structured_blocks', 'scannable_length']

### https://news.click108.com.tw/category/fate-tarot/
- status：200
- title：塔羅總運 | 發燒文章 | 科技紫微網（19）
- description：<empty>（0）
- canonical：<missing>
- JSON-LD：['BreadcrumbList']
- H1：['塔羅總運 好文']
- 內鏈/外鏈/文章/分類：183/40/42/17
- E-E-A-T：author=True published=True modified=False about_contact=False
- Citability markers：['answer_headings', 'structured_blocks', 'scannable_length']
