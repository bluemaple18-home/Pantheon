# Lite Cost Policy

任務ID：CARD-FORTUNE-COUNCIL-TEAM-DESIGN-001
範圍：限制臨時 council 的角色數、輪數、token 與模型升級

## 預設上限

```text
角色數: 5
輪數: 最多 2
Round 1 每角色輸出上限: 350 tokens
Round 2 總輸出上限: 1,000 tokens
Final brief 上限: 1,500 tokens
```

## Pantheon 預設節省策略

- 先引用既有文件脈絡，不讓角色重新發明產品方向。
- 已知主線是外部曝光、免費入口、Discord、命書、追問、分享；每次 council 只判斷本次 offer 卡在哪一段。
- 已知輸出語法是主題報告、證據鏈、格局卡；不再討論完整命理文體。
- 已知 MBTI 已有 64 分支與 UnifiedReport 回流；不再把 MBTI 當未定義功能。
- 已知塔羅、人類圖偏策略與插槽；除非要開技術卡，不用花 token 討論實作細節。

## 預設模型策略

- Round 1：小型或中階模型。
- Round 2：中階模型。
- Final brief：中階模型即可。
- 不為了「多想一點」升級高階模型。

## 何時才升級 GPT / Gemini 高階模型

只有 3 種情況：

- 產品方向已接近付費測試，需要把定位、offer、風險一次收斂清楚。
- Product Lead 和 Skeptic / Risk Lead 的結論相反，且 PM 需要做 go / no-go。
- 多個命理元素互相衝突，需要整理成一份不誤導使用者的 final brief。
- 需要把既有八字、紫微、MBTI、塔羅、人類圖訊號收斂成一個付費命書 offer。

## 何時直接停止

- 缺目標客群。
- 缺收費想法。
- 產品價值依賴恐嚇式銷售。
- 需要超過 2 輪才講得清楚。
- 角色開始重複輸出空泛建議。
- 還沒確認對應飛輪節點。

## 成本摘要格式

final brief 必須附：

```text
角色數:
輪數:
Final brief token 上限:
使用模型層級:
是否升級高階模型:
升級理由:
是否提前停止:
停止原因:
```

## 驗收對照

- 有 token/cost 上限。
- 有每輪角色數與輸出上限。
- 有 GPT / Gemini 升級條件。
- 不要求常駐 agent team。
