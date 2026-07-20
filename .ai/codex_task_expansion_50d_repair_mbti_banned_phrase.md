---
card_id: CARD-EXPANSION-50D-REPAIR-MBTI-BANNED-PHRASE
card_type: repair
thickness: standard
risk: medium
model: gpt-5.5
reasoning: medium
model_reason: 單一卡片內的精準禁詞修正與 evidence 重算，不擴大內容範圍。
source_candidate: 98a165864c6c8cc911cae854b9929fd3f6dbbd60
review_thread: 019f6aa5-ca54-70a3-b8bb-c5cb3992d2e4
candidate_commit_required: true
---

# Article Expansion 50D｜MBTI 禁詞 Repair

## Finding

獨立 review 判定 `NO-GO`：既有 QA 禁詞包含「保證」，候選模組的共用模板出現「不能保證／提供保證」，使 raw banned phrase hit 不為 0；`mbti.json` 卻記為 0。

## Allowlist

- `app/web/static/article-expansion-50d-mbti.js`
- `artifacts/fortune_council/content_seo_execution/evidence/article_expansion_50d/mbti.json`

## Repair 契約

- 以 source candidate 為基礎，只改寫命中「保證」的句子，維持原本非診斷、非能力排行、非固定命運的邊界語意。
- 重新計算並更新 evidence JSON，不得手填與實際輸出不一致的數字。
- 保持 16 records / 16 bodies、`personality-0037`~`personality-0052`、每篇 4 節、FAQ 3~5、正文至少 650 字、至少兩個場景。
- 禁詞 0、正文完整句重複超過三次為 0。
- 執行 `node --check`、JSON parse、`git diff --check`。
- 只提交 allowlist 兩檔，回報 repair commit SHA；不得 push、merge、deploy。

## 收卡

Repair commit 必須送回原 review thread `019f6aa5-ca54-70a3-b8bb-c5cb3992d2e4` 複驗，且 reviewed commit 必須等於 repair commit。
