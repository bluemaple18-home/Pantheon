# Content SEO Execution Result

## 狀態

`CARD-SEO-WRITE-000` 已完成。
`CARD-SEO-WRITE-002` 已完成初版：`evidence/scale_clusters/cluster_plan.md`。
`CARD-SEO-WRITE-003` 已完成初版：`evidence/qa_gate/article_qa_gate.md`。
`NEXT-30-DRAFTS` 已完成初版：`evidence/next_30/next_30_article_drafts.md`。
`FULL-DRAFTS-FIRST-10` 已完成初版：`evidence/next_30/full_drafts_first_10.md`。
`FULL-DRAFTS-11-20` 已完成初版：`evidence/next_30/full_drafts_11_20.md`。
`FULL-DRAFTS-21-30` 已完成初版：`evidence/next_30/full_drafts_21_30.md`。
`NEXT-30-PUBLISH` 已完成：30 篇已登錄前台 registry/body，sitemap 已同步，前台公開文章總數為 81 篇。
`CARD-SEO-VISIBLE-LINKS-001` 已完成：文章頁底部新增可見延伸閱讀模組，桌機/手機證據在 `evidence/visible_links_001/`。
`CARD-SEO-VISIBLE-LINKS-001` 正式站驗收已完成：公開頁載入 `article-visible-links-20260713-1`，桌機/手機各 6 條可見內鏈且無水平 overflow，SEO/GEO live audit 維持 Schema / E-E-A-T / Citability / Entity 100；證據在 `evidence/visible_links_001/live/`。
`CARD-SEO-HUB-VISIBLE-LINKS-001` 已開卡：下一步在 product hub / topic hub 補低調可見文章導流，不改首頁、hero 或文章正文。
`VOICE-RESEARCH-V2` 已完成：重新分析既有 Click108 近兩年爬蟲資料，確認 Pantheon 生硬主因是固定句型與抽象動詞過密；新規範與證據在 `evidence/click108_voice_research_v2.md`。
`VOICE-PILOT-TAROT-44` 已完成本機驗證：44 篇塔羅小牌輸出依牌組加入生活場景與具體動詞，未改版面；文章腳本快取升至 `article-voice-20260713-3`。
`VOICE-REPAIR-NEXT-30` 已完成本機修復驗證：移除候選版本批量固定句型，30 篇正文通過同批句型頻率、空段落與 web 回歸測試；證據在 `evidence/legacy_voice_next_30_repair_001/`。
`ARTICLE-UPDATE-DATE-20260714` 已完成本機同步：94 篇實際改稿文章的 SSR、prerender shell、JSON-LD、`article:modified_time` 與可見更新時間已壓至 `2026-07-14`；未改稿文章維持 `2026-07-12`。證據在 `evidence/article_update_date_20260714.md`。

本檔承接撰文計劃與內容規格；截至 `NEXT-30-PUBLISH`，新 30 篇已進前台文章資料與 sitemap，但不代表已部署到正式環境。

## 現況判斷

截至本次接手，前台 registry 已有 51 篇公開文章：

| 分類 | 目前篇數 |
|---|---:|
| 人格 | 11 |
| 塔羅 | 11 |
| 命盤 / 紫微 | 9 |
| 星座 / 星盤 | 5 |
| 感情 | 4 |
| 事業 | 4 |
| 人際 | 2 |
| 財富 | 3 |
| 人生方向 | 2 |

因此 `CARD-SEO-WRITE-001` 的「第一批 30 篇」不能當成全新待寫清單重跑。接下來要做的是：

1. 先用 QA gate 檢查既有 51 篇是否仍符合新版寫文規範。
2. 再補「已在矩陣內、尚未上線」的缺口文章。
3. 文章主軸改成讀者問題，不把塔羅、命盤、人格、星盤寫成工具課。

## 核心原則

- 問題先於工具：先回答讀者卡在感情、工作、人際、財富或人生方向的哪一層。
- 關鍵字仍要搶：`愚者牌意思`、`命宮是什麼`、`INTJ 是什麼` 這類搜尋詞可以寫，但正文不能變成講師課綱。
- 不承諾結果：不寫復合、升職、發財、轉運、人格判定或命運結論。
- 每篇都要有 50 字內 answer、150 字內導言、3-5 題 FAQ、限制段與真實文章內鏈。
- 單篇文章不放獨立 CTA 區塊；收束要在正文、FAQ、上一篇/下一篇、延伸閱讀裡完成。

## 30 天撰文計劃

目標：在不重複既有 51 篇的前提下，新增 30 篇可上稿草稿或完整上稿大綱。

### 第 1 週：QA 與缺口鎖定

產出：

- `evidence/qa_gate/article_qa_gate.md`
- `evidence/first_30/existing_51_gap_audit.md`
- 既有 51 篇的問題清單：哪些文章太像工具課、哪些缺少問題導向、哪些內鏈不足。

驗收：

- 每篇都能判斷 `pass / warning / blocker`。
- 明確標出不用重寫、只需小修、需要重寫的文章。
- 舊 brief 裡的硬導流 CTA 視為過期規格，不再沿用。

### 第 2-4 週：新增 30 篇缺口文章

優先寫這 30 篇：

| 優先 | ID | 分類 | 主關鍵字 | 建議標題 |
|---:|---|---|---|---|
| 1 | TAROT-M03 | 塔羅 | 皇后牌意思 | 皇后牌意思：正位、逆位與感情安全感怎麼看 |
| 2 | TAROT-M04 | 塔羅 | 皇帝牌意思 | 皇帝牌意思：正位、逆位與關係控制感怎麼看 |
| 3 | TAROT-M05 | 塔羅 | 教皇牌意思 | 教皇牌意思：正位、逆位與承諾壓力怎麼看 |
| 4 | TAROT-M07 | 塔羅 | 戰車牌意思 | 戰車牌意思：正位、逆位與行動卡住怎麼看 |
| 5 | TAROT-M08 | 塔羅 | 力量牌意思 | 力量牌意思：正位、逆位與壓力自控怎麼看 |
| 6 | TAROT-M09 | 塔羅 | 隱者牌意思 | 隱者牌意思：正位、逆位與需要冷靜怎麼看 |
| 7 | TAROT-M10 | 塔羅 | 命運之輪牌意思 | 命運之輪牌意思：正位、逆位與時機變動怎麼看 |
| 8 | TAROT-M11 | 塔羅 | 正義牌意思 | 正義牌意思：正位、逆位與關係公平怎麼看 |
| 9 | TAROT-M12 | 塔羅 | 吊人牌意思 | 吊人牌意思：正位、逆位與暫停等待怎麼看 |
| 10 | TAROT-M15 | 塔羅 | 惡魔牌意思 | 惡魔牌意思：正位、逆位與執著依賴怎麼看 |
| 11 | TAROT-M17 | 塔羅 | 星星牌意思 | 星星牌意思：正位、逆位與重新有希望怎麼看 |
| 12 | TAROT-M19 | 塔羅 | 太陽牌意思 | 太陽牌意思：正位、逆位與關係變明朗怎麼看 |
| 13 | TAROT-M20 | 塔羅 | 審判牌意思 | 審判牌意思：正位、逆位與是否重新開始怎麼看 |
| 14 | MBTI-INTP | 人格 | INTP 是什麼 | INTP 是什麼？感情、工作與想太多怎麼看 |
| 15 | MBTI-ISTJ | 人格 | ISTJ 是什麼 | ISTJ 是什麼？感情、工作與責任壓力怎麼看 |
| 16 | MBTI-ISTP | 人格 | ISTP 是什麼 | ISTP 是什麼？感情、工作與保持距離怎麼看 |
| 17 | MBTI-ISFP | 人格 | ISFP 是什麼 | ISFP 是什麼？感情、工作與情緒界線怎麼看 |
| 18 | MBTI-ENFJ | 人格 | ENFJ 是什麼 | ENFJ 是什麼？感情、工作與照顧別人怎麼看 |
| 19 | MBTI-ESTJ | 人格 | ESTJ 是什麼 | ESTJ 是什麼？感情、工作與控制節奏怎麼看 |
| 20 | MBTI-ESFJ | 人格 | ESFJ 是什麼 | ESFJ 是什麼？感情、工作與被需要感怎麼看 |
| 21 | MBTI-ESTP | 人格 | ESTP 是什麼 | ESTP 是什麼？感情、工作與衝動決定怎麼看 |
| 22 | MBTI-ESFP | 人格 | ESFP 是什麼 | ESFP 是什麼？感情、工作與當下感受怎麼看 |
| 23 | CHART-BASE-07 | 命盤 | 官祿宮是什麼 | 官祿宮是什麼？工作定位與被看見怎麼看 |
| 24 | CHART-BASE-08 | 命盤 | 遷移宮是什麼 | 遷移宮是什麼？外部環境與人生變動怎麼看 |
| 25 | CHART-BASE-09 | 命盤 | 大限是什麼 | 大限是什麼？十年節奏與人生轉換怎麼看 |
| 26 | CHART-BASE-10 | 命盤 | 流年是什麼 | 流年是什麼？年度節奏與選擇壓力怎麼看 |
| 27 | ASTRO-BASE-04 | 星座 | 太陽星座是什麼 | 太陽星座是什麼？個性表達與人生方向怎麼看 |
| 28 | ASTRO-BASE-06 | 星座 | 火星星座是什麼 | 火星星座是什麼？行動力、衝突與慾望怎麼看 |
| 29 | ASTRO-BASE-07 | 星座 | 水星星座是什麼 | 水星星座是什麼？溝通方式與想法卡住怎麼看 |
| 30 | THEME-INTERPERSONAL-03 | 人際 | 社交疲憊 | 社交疲憊怎麼辦？先分清消耗、界線與期待 |

短期槓桿：

- 塔羅補完大阿爾克那，可立刻改善塔羅 cluster 完整度。
- MBTI 補完 16 型，可承接競品未命中的 `INTP / ISTJ / ESFP` 等搜尋。
- 命盤補 `官祿宮 / 遷移宮 / 大限 / 流年`，補上紫微高意圖詞。
- 星座補 `太陽 / 火星 / 水星`，讓星盤基礎線不只停在月亮、上升、金星。

## 60 天 Cluster 擴張計劃

目標：規劃至少 120 篇，並先挑前 30 篇進入寫作。

### 塔羅 Cluster

- 大阿爾克那補完後，進入小阿爾克那 56 篇。
- 優先順序依 Click108 小樣本命中：`錢幣國王`、`寶劍七`、`權杖三`、`權杖五`、`錢幣五`、`寶劍九`、`聖杯二`、`聖杯十`。
- 每篇不是教牌義表，而是回答：這張牌在感情、工作、人際、財富或人生方向裡提醒哪種卡點。

### MBTI / 64 分支 Cluster

- 先補完 16 型。
- 第二層再做 64 分支，不急著一次全寫。
- 64 分支標題要同時保留 Pantheon 品牌與讀者問題，例如：`INTJ-AH 是什麼？高標準、控制感與工作壓力怎麼看`。

### 紫微 / 命盤 Cluster

- 十二宮：命宮、夫妻宮、財帛宮已上線；下一批補官祿、遷移、福德、田宅、疾厄、子女、兄弟、父母、僕役。
- 十四主星：從 `紫微星`、`天機星`、`武曲星`、`太陰星`、`貪狼星`、`巨門星` 優先。
- 每篇都要保留「單一宮位或星曜不能做完整個人判斷」。

### 星盤 / 星座 Cluster

- 基礎：太陽、火星、水星補完。
- 12 上升星座、12 月亮星座、12 金星星座、12 火星星座依序展開。
- 每篇要回到關係需求、情緒安全感、溝通或行動卡點，不寫星座決定論。

## 90 天 Search Console / CTR / 內鏈優化計劃

目標：用 Search Console 與實際曝光資料修正方向，不再只靠種子矩陣判斷。

### 每週檢查

- 曝光高但 CTR 低：重寫 title / meta description。
- 排名 8-20 名：補 FAQ、answer 段與內文 topic 連結。
- 點擊進來但停留弱：檢查導言是否太像定義課，改成問題導向。
- topic 頁曝光弱：補足達標 topic 的內鏈密度。

### 每月檢查

- 把自然流量前 20 篇標為「支柱頁」。
- 每個支柱頁至少補 5 條新內鏈。
- 觀察塔羅、MBTI、命盤、星座哪條 cluster 起量最快，再調整下一批撰文比例。

## 每篇固定規格

```text
id:
分類:
主攻關鍵字:
次要關鍵字:
搜尋意圖:
H1:
meta title:
meta description: 70-95 字，說清適用情境與限制
answer: 50 字內
導言: 150 字內，前 80 字含主攻關鍵字
H2 結構:
  - 這個問題通常在問什麼
  - 這個工具可以看什麼
  - 放到感情 / 工作 / 人際 / 財富 / 人生方向裡怎麼理解
  - 常見誤解與不能代表什麼
  - 如果想看自己的狀況，先把問題縮小
FAQ: 3-5 題
內部連結:
  - 上一篇 / 下一篇
  - 同分類最多 2 篇
  - 跨分類最多 3 篇，且分類不重複
  - topic 連結最多 8 個
正文收束:
公開邊界:
QA 狀態:
```

## 第一批 30 篇的處理方式

`article_briefs_first_30.md` 保留為基礎 brief，但以下條款要覆蓋：

- 舊版硬導流 CTA 不再沿用。
- 「如果想看你自己下一步做什麼」要改成「如果想看自己的狀況，先把問題縮小」。
- 每篇收束要回到可檢查條件，不導向硬銷工具。
- 已上線文章不重複產出，只做 QA、補洞或二修。

## 不做事項

- 不承諾排名結果。
- 不直接複製 Click108 正文、圖片、分類名稱或品牌文案。
- 不寫復合、財富或命運的斷言式結果。
- 不把 MBTI 寫成健康或人格判定。
- 不提供健康、個案法律或個人財務決策。
- 不把單一牌、宮位、主星、星座落點寫成個人命運。
- 不把站方管理語言寫進正文。
- 不在單篇文章底部放獨立 CTA 區塊。

## 下一步

建議執行順序：

1. `CARD-SEO-WRITE-003` 已先建立 QA gate：`evidence/qa_gate/article_qa_gate.md`。
2. `CARD-SEO-WRITE-002` 已建立 125 篇 cluster 規劃：`evidence/scale_clusters/cluster_plan.md`。
3. `NEXT-30-DRAFTS` 已產出 30 篇可上稿草稿規格：`evidence/next_30/next_30_article_drafts.md`。
4. `FULL-DRAFTS-FIRST-10` 已產出前 10 篇完整正文稿：`evidence/next_30/full_drafts_first_10.md`。
5. `FULL-DRAFTS-11-20` 與 `FULL-DRAFTS-21-30` 已補齊，且 `NEXT-30-PUBLISH` 已轉入正式 registry/body。
6. 下一步可從 Search Console / sitemap 提交與前台抽樣瀏覽驗收開始。

目前品質風險不在「不知道寫什麼」，而在「大量寫完後又滑回工具課或舊式導流」。後續每篇文章先過 QA gate，再進入上稿或工程登錄。

## SCALE-TO-125 Publish

- 已補 44 篇塔羅小牌正式文章，前台 registry 總數由 81 篇補到 125 篇。
- 新增正文庫：`app/web/static/article-bodies-scale-44.js`。
- 新增 URL：`/articles/tarot/tarot-0033` 到 `/articles/tarot/tarot-0076`。
- 內容邊界：不寫產品使用教學，不承諾感情、工作或財務結果；每篇以正位、逆位、感情、工作困擾為主。
- 驗證狀態：`node --check`、新增 44 篇 voice/body gate、sitemap 對齊檢查、`pytest tests/test_web.py -q`、`git diff --check` 已通過。
