---
card_id: CARD-EXPANSION-50D-FORTUNE
card_type: content-implementation
thickness: standard
risk: medium
model: gpt-5.5
reasoning: medium
model_reason: 17 篇結構化長文與機械品質閘門，需穩定內容生成但不涉及高風險控制面。
ownership_matrix: .ai/ownership_expansion_50d.md
evidence_path: artifacts/fortune_council/content_seo_execution/evidence/article_expansion_50d/fortune.json
candidate_commit_required: true
---

# Pantheon 文章擴張 50D｜命理卡

## 任務

新增 17 篇全新紫微斗數與八字公開文章，作為總數 229 → 279 的一部分。

## 範圍

- Serial：`fortune-0027` 至 `fortune-0043`。
- 紫微主星 7 篇：太陰、貪狼、巨門、天相、天梁、七殺、破軍。
- 八字基礎 10 篇：天干、地支、四柱、月令、藏干、用神、喜忌、合沖刑害、格局、納音。
- 發布與更新日期：`2026-07-16`。

## 唯一可修改檔案

- `app/web/static/article-expansion-50d-fortune.js`
- `artifacts/fortune_council/content_seo_execution/evidence/article_expansion_50d/fortune.json`

不要修改 registry、meta、HTML、Python、測試、sitemap、feed、redirects 或其他文章檔。

## 匯出契約

- `EXPANSION_50D_FORTUNE_ARTICLE_RECORDS`
- `EXPANSION_50D_FORTUNE_ARTICLE_BODY_LIBRARY`

## 內容契約

- 17 筆 record、17 份 body；ID、serial、slug、title 唯一。
- 每篇 4 節正文、3 至 5 題 FAQ、正文至少 650 個中文字元。
- 每篇至少兩個專屬生活場景與可觀察行為。
- 明確說明命理符號不是醫療、法律、財務建議，也不能保證事件結果。
- 禁止保證、注定、必看、全面解析、深度解析、總而言之、值得注意的是、不可或缺、賦能。
- 同批完整句不得重複超過三次。

## 驗證

- `node --check app/web/static/article-expansion-50d-fortune.js`
- 產出 JSON 證據，記錄數量、唯一性、最短字數、段落／FAQ、禁詞與重複句檢查。

## 完成回報

回報修改檔、17 篇 serial 範圍、檢查結果與尚存限制。原始執行禁止 commit、push 或部署；收卡階段經主線補充授權後，只允許把兩個 allowlist 檔案做成單一候選 commit，仍禁止 push 或部署。
