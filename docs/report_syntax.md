# 統一輸出語法 v0.2

## 目標

本文件用來統一 `bazi`、`ziwei-doushu`、`taibu`、`life-chart-engine` 類輸出。它不是宣稱這些 repo 都使用同一套論述，而是把它們的原始輸出、資料集、工具欄位整理成產品可用的候選語法。

## 來源狀態標記

| 標記 | 意義 |
|---|---|
| `DIRECT` | repo README 或範例明確出現的輸出或欄位 |
| `INFERRED` | 從 repo 欄位、資料集或知識庫可合理推導，但不是原文格式 |
| `PRODUCT_NORMALIZED` | 本產品為了統一 API、前端與 Prompt 新增的中介語法 |

## 預設核心句法

目前 API 先採用 `PRODUCT_NORMALIZED` 的證據鏈句法：

```text
命盤訊號 -> 組合牌 -> 白話翻譯 -> 適合/不適合 -> 建議
```

這不是唯一解，只是第一版最容易防止 AI 無依據下結論。

## 來源欄位匯總

### 八字來源

參考 `china-testing/bazi` 的輸出方向：

- `DIRECT` 四柱：年柱、月柱、日柱、時柱
- `DIRECT` 日主：日干、五行、強弱
- `DIRECT` 五行分數：木、火、土、金、水
- `DIRECT` 十神：比劫、食傷、財、官殺、印
- `DIRECT` 關係：天干合沖、地支合沖刑害會
- `DIRECT` 格局：財、官、殺、印、食傷等組合判斷
- `DIRECT` 評判文字：由上述訊號推導性格、婚姻、財運、事業

### 紫微來源

參考 `Renhuai123/ziwei-doushu` 的輸出方向：

- `DIRECT` 十二宮：命宮、兄弟、夫妻、子女、財帛、疾厄、遷移、僕役、官祿、田宅、福德、父母
- `DIRECT` 星曜：十四主星、輔星、雜曜
- `DIRECT` 四化：祿、權、科、忌
- `DIRECT` 格局：紫府同宮、日月並明、七殺朝斗等
- `DIRECT` 主題解讀：命格總覽、財運、事業、感情、健康等
- `DIRECT` 運限：大限、流年、流月、流日

### 太卜來源

參考 `hhszzzz/taibu` 的功能欄位：

- `DIRECT` 八字：真太陽時、四柱、五行、十神、神煞、十二長生、刑害合沖、大運流年
- `DIRECT` 紫微：十二宮、三方四正、主星輔星、四化、飛星、運限
- `DIRECT` 運勢：每日、每月、未來走線
- `DIRECT` 關係：情侶、商業、親子合盤

### Life Chart Engine 來源

參考 `zhenheco/life-chart-engine` 的 JSON 契約方向；詳細 intake 見 `docs/life_chart_engine_intake.md`。

- `DIRECT` 西洋星盤：Ascendant、Midheaven、planets、houses、aspects
- `DIRECT` 人類圖：type、authority、profile、definition、incarnation_cross、centers、channels、gates
- `DIRECT` 紫微：five_elements_class、soul、body、hour_index、palaces、horoscope
- `INFERRED` 外部驗證：可作為 Pantheon golden sample 與欄位映射參考
- `PRODUCT_NORMALIZED` 授權邊界：只採欄位契約與驗證策略，不直接複製/import AGPL code

## 候選論述方式

### A. 專業排盤型

來源狀態：`DIRECT`

接近 `china-testing/bazi` 的命令列輸出：先把盤列出來，再附評判。

```text
四柱 / 五行分數 / 十神 / 合沖刑害 / 格局
---
評判文字
```

優點：

- 看起來最有命理專業感。
- 方便專家檢查。
- 最接近原始 repo 輸出。

缺點：

- 一般使用者可能看不懂。
- 產品感較弱。
- 需要很多術語教育。

適合：

- 專業版、進階模式、命理師工具。

### B. 主題報告型

來源狀態：`DIRECT + INFERRED`

接近 `ziwei-doushu` 51.8 萬樣本資料的「命盤 JSON + 13 主題解讀文本」方向。

```text
命格總覽
事業
財運
感情
健康
未來運勢
```

優點：

- 使用者最容易讀。
- 很適合做付費報告。
- 容易做 UI 分頁與圖表。

缺點：

- 如果每段不標依據，容易變成 AI 感想。
- 需要把每段文字掛回命盤訊號，否則可信度下降。

適合：

- 第一版消費者產品。

### C. 證據鏈型

來源狀態：`PRODUCT_NORMALIZED`

這是目前 API 採用的預設語法，用來把不同命理系統統一成同一個中介格式。

```text
因為你有【訊號 A】+【訊號 B】，
所以代表【白話性質】。
因此適合【適合清單】，
不適合【不適合清單】。
接下來建議你【具體行動】。
```

優點：

- 最能避免「AI 沒依據亂講」。
- 很適合前端做展開依據。
- 可以同時接八字、紫微、塔羅、人類圖、MBTI、西洋星盤。

缺點：

- 文字如果處理不好會顯得機械。
- 不像傳統命理師自然說話。

適合：

- 產品中介層、Prompt 約束、可追溯解讀。

### D. 格局卡型

來源狀態：`DIRECT + PRODUCT_NORMALIZED`

來自八字格局、紫微 `patterns.ts`、太卜的格局/神煞/飛星欄位，再產品化成卡牌。

```text
組合牌：官祿 + 六秀
含義：才華、表現、被看見
適合：內容、品牌、教學、顧問
風險：想很多但沒有作品
建議：固定輸出作品
```

優點：

- 很有產品記憶點。
- 適合視覺化與分享。
- 可以做成規則庫與權重系統。

缺點：

- 需要先建立大量格局卡。
- 如果規則庫太薄，容易看起來像套模板。

適合：

- 核心產品特色、付費報告、每日/每月運勢。

### E. 對話追問型

來源狀態：`INFERRED + PRODUCT_NORMALIZED`

先給主要訊號，再讓使用者追問「為什麼」或「那我感情呢」。

```text
你盤裡最明顯的是金旺與官祿訊號。
這通常和判斷力、職涯企圖、標準感有關。
你想先看職涯、感情，還是未來 12 個月？
```

優點：

- 不會一次塞太多。
- 很適合 AI chat。
- 可以根據使用者關心的問題動態展開。

缺點：

- 不像完整報告。
- 需要對話狀態管理。

適合：

- Chat UI、免費版入口、報告後續追問。

## 建議產品組合

第一版不要只選一種。建議採用：

```text
B 主題報告型作為頁面結構
+ C 證據鏈型作為每段解釋規則
+ D 格局卡型作為亮點與可分享內容
```

也就是：

```text
報告看起來像主題報告，
每段都能展開看到證據鏈，
重要組合用格局卡呈現。
```

## 統一資料結構

### 1. Signal

單一命盤訊號。它是所有解讀的最小依據。

```json
{
  "id": "bazi.element.fire",
  "system": "bazi",
  "category": "element",
  "label": "火",
  "value": 6,
  "polarity": "high",
  "basis": "五行分數",
  "plain_meaning": "火代表表達、熱情、現場感與反應速度"
}
```

### 2. ComboCard

組合牌。它把多個 Signal 合在一起，產出可解釋的推論。

```json
{
  "id": "combo.expression_drive",
  "title": "表達驅動組合",
  "evidence_ids": ["bazi.element.fire", "ziwei.life_palace"],
  "formula": "火偏強 + 命宮/官祿訊號",
  "because": "因為火能量偏強，又有命宮或官祿的表現訊號",
  "therefore": "所以使用者較容易靠熱情、審美、表達與現場反應建立影響力",
  "suitable": ["內容", "品牌", "教學", "顧問", "社群", "表演型工作"],
  "unsuitable": ["高度重複", "完全照 SOP", "不能表達", "沒有回饋的環境"],
  "advice": "先累積可展示作品，不要只停留在靈感或口才。"
}
```

### 3. ReadingBlock

報告段落。每段都必須引用至少一張組合牌或一個 Signal。

```json
{
  "topic": "career",
  "title": "職涯定位",
  "source_card_ids": ["combo.expression_drive"],
  "summary": "你比較適合靠表達、審美或影響力形成職涯價值。",
  "reasoning": "因為火能量偏強，且命盤有表現/官祿訊號，所以不適合只做封閉重複型工作。",
  "actions": ["整理作品集", "建立公開輸出節奏", "避開無回饋的工作環境"]
}
```

## 文字模板

每一段固定用這個語法：

```text
因為你有【訊號 A】+【訊號 B】，
所以這代表【白話性質】。
因此你適合【適合清單】，
不適合【不適合清單】。
接下來建議你【具體行動】。
```

禁止輸出：

```text
你很有創造力，所以適合做內容。
```

原因：沒有依據，使用者不知道是哪個命盤訊號導致這個判斷。

允許輸出：

```text
因為你的五行裡火能量偏強，又有官祿宮的表現訊號，所以你不是純執行型，而是比較靠表達、審美、熱情與現場反應建立價值的人。因此你適合內容、品牌、教學、顧問、社群這類工作；不適合長期做高度重複、不能表達、沒有回饋的工作。接下來建議你先累積可展示作品。
```

## API 欄位

`/api/v1/predict` 應回傳：

```json
{
  "charts": {},
  "ai": {},
  "report": {
    "syntax_version": "0.2",
    "narrative_strategy": "evidence_chain",
    "signals": [],
    "combo_cards": [],
    "reading_blocks": []
  }
}
```

`charts` 保留原始排盤資料；`report` 是產品輸出層；`ai` 只負責根據 `report` 生成自然語言。
