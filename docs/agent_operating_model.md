# Pantheon Agent 營運模型筆記

日期：2026-06-12
狀態：商業模式與營運架構備忘

## 核心觀念

Pantheon 後續不應一開始就追求一個什麼都會做的全能 Agent。

比較可控的做法是先建立一個主 Agent，負責把每日重複工作整理成固定流程，持續測試、修正與穩定化。當某些流程已經成熟，再拆成專職 Agent，讓每個 Agent 只負責清楚邊界內的任務。

這個模型適合 Pantheon 的原因：

- Pantheon 商模本身包含網站、Threads、Discord、內容、算命報告、社群互動與付費轉換。
- 如果全部塞進單一 Agent，流程會變複雜，管理成本會快速上升。
- 先用主 Agent 跑通循環，再拆分專職 Agent，比較容易維持品質與可觀測性。

## 發展順序

### Phase 1：主 Agent

主 Agent 先負責整體營運節奏：

- 整理每日內容主題。
- 產生 Threads 短文方向。
- 規劃網站知識文題目。
- 規劃 Discord 每日抽卡與互動問題。
- 追蹤哪些內容帶來回流、互動與付費。
- 維護 Pantheon 商業飛輪的整體節奏。

此階段重點不是自動化全部工作，而是把流程跑順、跑穩。

### Phase 2：專職 Agent

當某些工作足夠成熟後，再拆出專職 Agent。

候選分工：

| Agent | 職責 | 成熟條件 |
|---|---|---|
| Content Agent | 網站知識文、Threads 短文、社群主題 | 內容日曆穩定、有明確語氣與格式 |
| SEO Agent | 關鍵字、文章結構、內部連結 | 網站文章開始累積流量 |
| Discord Ops Agent | 每日抽卡、投票、回覆、活動提醒 | Discord 有固定會員與每日互動 |
| Report Agent | 個人命書、年度命書、主題報告草稿 | 報告格式穩定且可重複交付 |
| Growth Agent | 導流、CTA、轉換漏斗、分享圖策略 | 已有基本流量與轉換數據 |
| Customer Agent | 常見問題、付款後指引、報告追問 | 付費用戶與會員開始增加 |

每個 Agent 都應有自己的：

- 記憶範圍。
- 輸入格式。
- 輸出格式。
- 可做與不可做的邊界。
- 驗收指標。

### Phase 3：編排機制

專職 Agent 分工穩定後，再加入編排層。

編排層負責：

- 接收任務。
- 判斷任務類型。
- 分派給適合的 Agent。
- 收集結果。
- 檢查是否需要人工審核。
- 將結果發布到網站、Threads 或 Discord。

適合事件觸發的例子：

- 每天固定時間產生 Discord 今日抽卡。
- 每週產生本週主題與 Threads 內容。
- 新文章發布後，自動拆成 Threads 短文。
- 使用者從文章入口完成問題整理後，引導加入 Discord。
- 使用者購買命書後，觸發報告產生與交付流程。
- Discord 某主題互動升高時，回推成網站文章或付費報告題材。

## 與 Pantheon 商業飛輪的關係

Pantheon 的循環流程是：

```text
外部曝光
→ 文章入口
→ 命中感
→ Discord 進群
→ 每日儀式
→ 深問題出現
→ 付費啟動
→ 命書與追問
→ 分享擴散
→ 回到外部曝光 / Discord
```

Agent 營運模型要服務這條循環，而不是變成另一套獨立系統。

對應關係：

| 循環節點 | Agent 支援 |
|---|---|
| 外部曝光 | Content Agent、SEO Agent、Growth Agent |
| 文章入口 | Content Agent、Growth Agent |
| 命中感 | Report Agent、Growth Agent |
| Discord 進群 | Discord Ops Agent、Customer Agent |
| 每日儀式 | Discord Ops Agent |
| 深問題出現 | Discord Ops Agent、Report Agent |
| 付費啟動 | Growth Agent、Customer Agent |
| 命書與追問 | Report Agent、Customer Agent |
| 分享擴散 | Content Agent、Growth Agent |

## 設計原則

1. 先跑順主流程，再拆 Agent。
2. 每個 Agent 只負責一個穩定任務域。
3. 不用全能 Agent 取代流程設計。
4. 每個 Agent 都要有清楚驗收標準。
5. 編排層只負責分派、收斂與檢查，不負責重新發明每個流程。
6. 自動化應優先用在高重複、低風險、格式穩定的工作。
7. 付費命書、對外發布與投資相關內容仍需保留人工審核邊界。

## 短期下一步

短期先不急著拆多 Agent。

先用主 Agent 建立以下固定流程：

- 30 天內容日曆。
- 每日 Discord 抽卡與互動格式。
- Threads 短文模板。
- 網站知識文模板。
- 個人命書交付模板。
- 轉換漏斗追蹤表。

等這些流程跑順，再決定第一個要拆出去的專職 Agent。
