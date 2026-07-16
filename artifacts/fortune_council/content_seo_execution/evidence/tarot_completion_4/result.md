---
id: TAROT-COMPLETION-4-ACCEPTANCE
status: partial
type: acceptance
---

# Tarot Completion 4 驗收結果

## root question

補齊錢幣十、錢幣侍者、錢幣騎士、錢幣皇后，使正式牌義頁覆蓋完整 78 張牌。

## blocker

手機寬度 `390px` 下，既有 `.article-theme-visual i` 動態漸層層超出 viewport：`left=-177px`、`right=529px`，造成文件水平 overflow。父層已有 `overflow: hidden`；嘗試加入 `contain: paint` 後仍可重現，已撤回無效變更。依同一 blocker 三次停損規則，不再進行第 4 次瀏覽器嘗試。

## fork

候選獨立修復：文章產品視覺的 transformed child 應改用不影響 scroll overflow 的裁切或背景實作。這是既有跨文章 UI 問題，不併入本次內容產製。

## 目前狀態

- 78 / 78 張牌義頁已登錄。
- 4 篇新文各有 6 個正文段落群、3–5 題 FAQ、牌面象徵、正逆位、感情、工作與閱讀邊界。
- 四篇正文皆達 1,300 字以上。
- `pytest`: 90 passed。
- Browser desktop：內容、日期、FAQ、資產與錯誤監聽通過。
- Browser mobile：內容、日期、FAQ、console、pageerror、request failure 通過；horizontal overflow 未通過。

## 證據

- `artifacts/fortune_council/content_seo_execution/evidence/tarot_completion_4/browser_acceptance.py`
- `artifacts/fortune_council/content_seo_execution/evidence/tarot_completion_4/pentacles_ten_desktop.png`
- `artifacts/fortune_council/content_seo_execution/evidence/tarot_completion_4/pentacles_queen_mobile.png`

## 下一步

另開 UI 修復切片處理 `.article-theme-visual i` 的 mobile scroll overflow，修復後重跑同一支 browser acceptance。

## 等待條件

無；內容與工程登錄可 review，但整體 browser acceptance 維持 `PARTIAL`。

## 限制

未部署正式站，未做 live URL 驗收。
