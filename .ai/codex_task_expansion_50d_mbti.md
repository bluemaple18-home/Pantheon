---
card_id: CARD-EXPANSION-50D-MBTI
card_type: content-implementation
thickness: standard
risk: medium
model: gpt-5.5
reasoning: medium
model_reason: 16 篇結構化長文與機械品質閘門，需穩定內容生成但不涉及高風險控制面。
ownership_matrix: .ai/ownership_expansion_50d.md
evidence_path: artifacts/fortune_council/content_seo_execution/evidence/article_expansion_50d/mbti.json
candidate_commit_required: true
---

# Pantheon 文章擴張 50D｜人格卡

## 任務

新增 16 篇全新 MBTI 64 分支人格公開文章，作為總數 229 → 279 的一部分。

## 範圍

- Serial：`personality-0037` 至 `personality-0052`。
- 類型：ENTJ、ENTP、ISFJ、ENFJ。
- 每型四分支：AH、AC、OH、OC。
- 發布與更新日期：`2026-07-16`。

## 唯一可修改檔案

- `app/web/static/article-expansion-50d-mbti.js`
- `artifacts/fortune_council/content_seo_execution/evidence/article_expansion_50d/mbti.json`

不要修改 registry、meta、HTML、Python、測試、sitemap、feed、redirects 或其他文章檔。

## 匯出契約

- `EXPANSION_50D_MBTI_ARTICLE_RECORDS`
- `EXPANSION_50D_MBTI_ARTICLE_BODY_LIBRARY`

## 內容契約

- 16 筆 record、16 份 body；ID、serial、slug、title 唯一。
- 每篇 4 節正文、3 至 5 題 FAQ、正文至少 650 個中文字元。
- 每篇至少兩個專屬生活場景與可觀察行為。
- 明確說明人格分類不是診斷、能力評分或命運判定。
- 禁止保證、注定、必看、全面解析、深度解析、總而言之、值得注意的是、不可或缺、賦能。
- 同批完整句不得重複超過三次。

## 驗證

- `node --check app/web/static/article-expansion-50d-mbti.js`
- 產出 JSON 證據，記錄數量、唯一性、最短字數、段落／FAQ、禁詞與重複句檢查。

## 完成回報

回報修改檔、16 篇 serial 範圍、檢查結果與尚存限制。原始執行禁止 commit、push 或部署；收卡階段經主線補充授權後，只允許把兩個 allowlist 檔案做成單一候選 commit，仍禁止 push 或部署。
