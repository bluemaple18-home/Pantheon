---
card_id: CARD-EXPANSION-50D-REPAIR-MBTI-PUBLIC-LANGUAGE
card_type: repair
thickness: minimal
risk: low
source_candidate: 739777e372e67d8a4b2b4f5b8e1c50dae06edfba
review_thread: 019f6aa5-ca54-70a3-b8bb-c5cb3992d2e4
candidate_commit_required: true
---

# Article Expansion 50D｜MBTI 公開文案禁語 Repair

## Finding

主線完整發布 gate 發現 16 篇共用正文含「自我提問的入口」，違反全專案公開文案禁止「入口」的契約。

## Allowlist

- `app/web/static/article-expansion-50d-mbti.js`

## Repair

- 只將該句的「入口」改成自然的公開讀者語言（例如「起點」），不改其他正文與 metadata。
- 重跑原內容 gate，加驗公開禁語「入口」命中 0。
- 只提交單檔，回原 reviewer 複驗；不得 push、merge、deploy。
