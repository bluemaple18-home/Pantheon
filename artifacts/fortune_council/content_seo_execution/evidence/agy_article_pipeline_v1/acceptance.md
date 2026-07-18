# AGY Article Pipeline V1 驗收證據

日期：2026-07-18

## 隔離狀態

- 實作 worktree：隔離的乾淨 worktree（未將主工作區未追蹤檔帶入）
- branch：`codex/agy-article-pipeline-v1`
- 起始 commit：`5f2a5d677445fa8de66683e1d9448a226b5a48a4`
- Pantheon `main` 原有未追蹤檔未帶入實作 worktree。
- 尚未 commit、整合 `main`、push 或部署。

## 測試

```text
122 passed, 2 warnings in 8.69s
```

warnings 為既有 Starlette `httpx` 相容性棄用，以及既有測試字串的 escape sequence 警告，與本次 pipeline 無關。`git diff --check` 通過。

## 矩陣盤點

Registry 語意去重後共有 8 篇真實缺口：

```text
MBTI-INTP-AH
MBTI-INTP-AC
MBTI-INTP-OH
MBTI-INTP-OC
CHART-CYCLE-DECADE
ASC-ARIES
ASC-TAURUS
ASC-GEMINI
```

`官祿宮` 已由既有 `事業宮` 內容覆蓋；泛用 `流年` 已由既有 `八字流年` 內容覆蓋，因此未重複建立。

## 真實模型原型

- run：`prototype-v1-01`
- article：`MBTI-INTP-AH`
- Writer：`Gemini 3.5 Flash (Low)`
- Reviewer：`Gemini 3.1 Pro (Low)`，獨立 headless process
- Reviewer verdict：`APPROVE`
- Candidate article SHA-256：`9567ac2952530bcf27493894d9c3f55f18f14916e4fe623561df9d3208117d90`
- Findings：0
- `approval.json` 已綁定候選稿 SHA-256，核准者為 `mattkuo`。

## 外部資料最小化

原始實作會把內部 brief 一併送給外部 CLI，因此被私人 repo 資料外傳政策阻擋。修正後採 allowlist outbound contract：

- 只傳預計公開的主題關鍵字、內容規範、現有公開文案與臨時 `article-XX` slot。
- 不傳 run ID、matrix ID、article ID、serial、slug、repo path、source file、GSC property 或 clicks／impressions／CTR／position。
- Writer 回傳後才在本機綁定 target identity；Reviewer 回傳後才在本機綁 candidate SHA-256。
- 測試會檢查 outbound payload 不含上述內部 metadata。

## 第一輪產文結果

- 8 篇 candidate 均已產生。
- Writer：`Gemini 3.5 Flash (Low)`。
- Reviewer：每次使用全新 `Gemini 3.1 Pro (Low)` headless process。
- 8/8 最終 verdict 為 `APPROVE`，0 個剩餘 finding。
- 合併 8 篇執行跨批重複句、禁詞、篇幅、段落、固定 tags、去模板詞、產品定位與關鍵字 deterministic gate，0 個 finding。
- 有效文章正文均為 1,300 到 2,000 字、至少 5 節；初次超長的上升金牛／上升雙子 run 已正式退件，改由新 run 重新生成，退件稿不進 approval。
- 8 篇的 `approval.json` 均已綁定各自候選稿 SHA-256，並已套用到三個 expansion module。
- 退件 run `matrix-backlog-v1-02` 沒有 `approval.json`，不在 apply 範圍。

## 本機瀏覽器驗收

- 本機服務：`http://127.0.0.1:9878`
- Chromium headless；事件監聽在首次 navigation 前完成。
- viewport：desktop `1440×1000`、mobile `390×844`。
- 每個 viewport 驗收文章中心、文章管理，以及人格、紫微、星座各一篇新文章，共 10 個案例。
- 10/10 HTTP 200；三篇抽查文章皆呈現 5 個正文標題與 5 組 FAQ。
- 初驗發現文章模板在 390px viewport 有 2px 水平溢出；定位為 `.article-page-header::before` 的負水平 inset 與縮放動畫。
- 手機 breakpoint 將該 pseudo-element 的 `inset-inline` 收回為 `0`，保留背景動畫；修正後三篇文章的 document overflow delta 均為 0。
- 實際載入 CSS cache token：`article-mobile-overflow-20260718-1`。
- console error：0；page error：0；request failed：0。
