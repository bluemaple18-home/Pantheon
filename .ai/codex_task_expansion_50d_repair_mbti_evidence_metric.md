---
card_id: CARD-EXPANSION-50D-REPAIR-MBTI-EVIDENCE-METRIC
card_type: repair
thickness: minimal
risk: low
source_candidate: 6deaf6df9b29aa1c7b985c45308faed690a276c9
review_thread: 019f6aa5-ca54-70a3-b8bb-c5cb3992d2e4
candidate_commit_required: true
---

# Article Expansion 50D｜MBTI evidence 指標 Repair

## Finding

第二次獨立 review 確認正文、結構、禁詞與重複句皆通過，但 `mbti.json` 的 `bodyLengthCheck.minChineseCharacters` 記為 1105；該數字是所有字元長度，與欄位宣稱的中文字符口徑不符。Reviewer 重算最短中文字符為 927。

## Allowlist

- `artifacts/fortune_council/content_seo_execution/evidence/article_expansion_50d/mbti.json`

## Repair 與驗證

- 直接從 source candidate 的 JS export 重算每篇正文中文字符數，將 `minChineseCharacters` 更新為實際最小值。
- 不修改文章 JS 或任何其他檔案。
- JSON parse、禁詞 0、正文最短中文字符 >=650、`git diff --check`。
- 只提交 allowlist 檔，回報完整 commit SHA；不得 push、merge、deploy。
- 送回原 reviewer thread 複驗，reviewed commit 必須等於 repair commit。
