# CARD-CONTENT-REWRITE-000｜全站文章重寫主計劃

## 任務ID / 卡片類型｜派工對象

`CARD-CONTENT-REWRITE-000` / 主線契約與整合｜Pantheon 主線

## 任務目的

把既有文章改成同一套讀者優先模板：先回答搜尋問題，再放入必要的生活場景、工具解釋與限制；不把四項功能硬塞成固定段落。

## 不可變更

- 不改版面、CSS、手機／桌機結構。
- 不改正式 URL、文章編號、canonical、Schema 與既有內鏈契約。
- 不加入保證式運勢、恐嚇、心理診斷、醫療、法律或投資建議。
- 不把 Click108 正文或句子直接複製到 Pantheon。

## 依賴圖與 frontier

```text
001 runtime/content contract
        ↓
002 astrology core ─┐
003 tarot foundation ─┼→ 005 scenario batch
004 fortune/personality ─┘
        ↓
006 review and release gate
```

目前 frontier：`001`、`002`、`003`、`004` 可在獨立 worktree 平行執行；`005` 等待 `001` 完成並抽樣確認內容形狀；`006` 等所有執行卡完成。

## 單一文章契約

```text
讀者問題 → 直接答案 → 必要生活場景 → 工具如何提供整理角度
→ 題目需要時才給小提醒 → 推論後自然附限制 → FAQ / 延伸閱讀
```

- 基礎定義文：至少一個具體場景；不硬塞行動建議。
- 情境問題文：至少兩個具體場景與可觀察行為。
- 限制要接在具體解釋後，不重複成模板免責句。
- 不把「搜尋者通常不是想背定義」「Pantheon 公開文章會……」等內部語言寫給讀者。

## 主線驗收

- 逐張讀 diff 與正文，不接受只看完成回報。
- 每張卡都有可重現證據、文章清單、修改前後字數／段落與 blocker 狀態。
- 執行卡只可修改分配的內容檔；runtime 卡可修改指定生成器與測試。
- 任何 blocker 未關閉，不得進入 `006` 或宣稱完成。

## 證據路徑

`artifacts/fortune_council/content_rewrite_execution/evidence/`
