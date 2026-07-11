# Pantheon Article QA Gate

## 使用方式

每篇文章上稿前都用本表檢查。結果只允許三種：

- `PASS`：可進入上稿或工程登錄。
- `WARNING`：可上稿，但要留下原因與下一輪修正點。
- `BLOCKER`：不得上稿，需先重寫或補齊。

## 0. 基本資料

```text
article_id:
分類:
主攻關鍵字:
正式 URL:
檢查者:
檢查日期:
結果: PASS / WARNING / BLOCKER
```

## 1. SEO 基礎

| 項目 | 判定 | 標準 |
|---|---|---|
| H1 有主攻關鍵字 | BLOCKER | H1 必須自然包含主攻關鍵字。 |
| 第一段前 80 字有主攻關鍵字 | BLOCKER | 搜尋者第一眼要知道這篇回答什麼。 |
| 前 150 字直接回答搜尋問題 | BLOCKER | 不能先鋪陳工具背景或站方說明。 |
| meta title 28-36 字優先 | WARNING | 可略超，但不能失去可讀性。 |
| meta description 70-95 字 | BLOCKER | 要同時說明適用情境與限制。 |
| canonical 使用正式流水號 URL | BLOCKER | 不使用舊語意 slug 當 canonical。 |

## 2. AEO / GEO 結構

| 項目 | 判定 | 標準 |
|---|---|---|
| answer 50 字內 | BLOCKER | 能被摘要引用，不能寫成廣告語。 |
| 有 120-150 字完整答案段 | WARNING | 方便 AI 搜尋摘要引用。 |
| FAQ 3-5 題 | BLOCKER | 少於 3 題或超過 5 題都退回。 |
| FAQ 回答真問題 | BLOCKER | 不寫「依個人情況而定」這種空話。 |
| 可轉成 Article JSON-LD | BLOCKER | title、description、author、date、canonical 要完整。 |
| 可轉成 FAQPage JSON-LD | BLOCKER | FAQ 題答必須乾淨，不含站方管理語。 |
| 可轉成 BreadcrumbList | BLOCKER | 分類與文章層級明確。 |

## 3. 寫文規範

| 項目 | 判定 | 標準 |
|---|---|---|
| 問題先於工具 | BLOCKER | 先處理讀者卡住的情境，再補塔羅、命盤、人格或星盤語言。 |
| 每個 H2 下至少 2 段 | WARNING | 避免只有標題和一句話。 |
| 每段 80-160 字 | WARNING | 手機閱讀不能連續大段。 |
| 有「不能代表什麼」限制段 | BLOCKER | 每篇至少一段清楚降級。 |
| 不像工具課 | BLOCKER | 不能把正文主軸寫成教讀者學塔羅、命盤、人格或星盤。 |
| 不出現站方管理語 | BLOCKER | 禁用：入口、標籤頁、集結頁、五大主題文章、公開文章的任務。 |
| 沒有 AI 腔套語 | WARNING | 避免全面解析、深度解析、不可或缺、賦能、總而言之、值得注意的是。 |

## 4. 邊界與風險

| 項目 | 判定 | 標準 |
|---|---|---|
| 不承諾結果 | BLOCKER | 禁用一定、保證、注定、必定復合、財運爆發。 |
| 不做心理診斷 | BLOCKER | MBTI / 人格只能說偏好，不說診斷。 |
| 不提供醫療、法律、投資建議 | BLOCKER | 財富文尤其要明確排除投資建議。 |
| 不恐嚇讀者 | BLOCKER | 不能用災難、失敗、錯過機會製造焦慮。 |
| 不替讀者做人生決定 | BLOCKER | 只能整理條件，不替讀者決定離職、分手、投資或搬家。 |

## 5. 內鏈檢查

| 項目 | 判定 | 標準 |
|---|---|---|
| 上一篇 / 下一篇規則正確 | WARNING | 有前後文才顯示，放在 FAQ 上方。 |
| 延伸閱讀最多 5 篇 | BLOCKER | 只放真實文章，不放產品線入口或工具入口。 |
| 同分類最多 2 篇 | WARNING | 避免整篇只在同一 cluster 內打轉。 |
| 跨分類最多 3 篇且不重複 | WARNING | 讓內容網有橫向連結。 |
| topic 連結最多 8 個 | WARNING | 只連本篇主攻或次攻 SEO 標籤。 |
| 錨文字是關鍵字 | WARNING | 禁用「點這裡」。 |

## 6. CTA 與收束

| 項目 | 判定 | 標準 |
|---|---|---|
| 單篇文章沒有獨立 CTA 區塊 | BLOCKER | 舊版「免費入口 + 五大主題小報告」不再沿用。 |
| 最後一節自然收束 | BLOCKER | 要說清限制、適用情境與下一個可讀問題。 |
| 不硬賣工具 | BLOCKER | 不能把文章寫成導購頁。 |

## 7. Blocker 清單

任一命中即不得上稿：

```text
全面解析
深度解析
不可或缺
賦能
必看
一定
保證
注定
入口
標籤頁
集結頁
五大主題文章
公開文章負責
公開文章的任務
抽到這張牌代表他一定會回來
命盤有這顆星注定
財運爆發
心理診斷
投資建議
```

## 8. 回報格式

```text
article_id:
result: PASS / WARNING / BLOCKER
blockers:
- ...
warnings:
- ...
required_edits:
- ...
notes:
- ...
```

## 9. 對應現有程式 gate

正式登錄到前台時，應同步通過：

- `auditArticleVoice`
- `listArticleVoiceAudits`
- `tests/test_web.py` 的公開文章標準測試
- `git diff --check`

內容端先用本 QA gate；工程端再用現有測試與 browser 驗收。
