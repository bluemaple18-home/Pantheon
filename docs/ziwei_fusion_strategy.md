# 紫微融合策略 v0.1

## 結論

Pantheon 的紫微主線以 `ziwei-doushu` / Pantheon 內部紫微 layer 為主，`life-chart-engine` 只作為優化材料、外部驗證器與欄位補充來源。

採用原則：

```text
主線 provider 決定核心命盤
外部 provider 補 confidence、補缺欄位、標出 conflict
report 只用可追溯且可信度足夠的欄位下結論
```

## Provider 角色

| Provider | 角色 | 權重 | 用途 |
|---|---|---:|---|
| `pantheon_ziwei` | 產品主線 provider | 1.0 | 最終 API 與 report 的預設來源 |
| `ziwei_doushu_reference` | 開源資料/格局主參考 | 0.9 | 格局庫、語料、golden sample |
| `life_chart_engine` | secondary validator | 0.6 | 西洋/HD/紫微欄位校準與補缺 |

`life_chart_engine` 不可直接覆蓋主線欄位；只有在主線欄位缺失時可補值，並必須標 `source=life_chart_engine` 與 `confidence=external_only`。

## 融合欄位

第一階段只融合穩定欄位：

- `five_elements_class`
- `life_palace`
- `body_palace`
- `life_palace_stars`
- `body_palace_stars`
- `palaces`
- `soul_star`
- `body_star`
- `hour_index`

第二階段再融合高風險欄位：

- `four_transformations`
- `major_limit`
- `annual_flow`
- `horoscope`
- 格局判斷

## Confidence 規則

| 狀態 | confidence | 說明 |
|---|---|---|
| 主線 provider 有值，外部 provider 一致 | `high` | 可進 report 強結論 |
| 主線 provider 有值，外部 provider 缺值 | `primary` | 可進 report，但文字不要假裝已交叉驗證 |
| 主線 provider 缺值，外部 provider 有值 | `external_only` | 可顯示，暫不作強結論 |
| 主線 provider 與外部 provider 不一致 | `conflict` | 可顯示 conflict，不進 AI 強結論 |
| 所有 provider 都缺值 | `missing` | 不顯示或顯示待補 |

## Conflict 處理

若同一欄位出現不同值：

```json
{
  "key": "life_palace",
  "value": "官祿",
  "confidence": "conflict",
  "primary": {
    "provider": "pantheon_ziwei",
    "value": "官祿"
  },
  "candidates": [
    {
      "provider": "life_chart_engine",
      "value": "命宮"
    }
  ]
}
```

規則：

- 前端可顯示「待校準」。
- AI prompt 不可用 conflict 欄位產生強結論。
- golden sample 測試要保留 conflict，不能 silent overwrite。

## Report 使用規則

`app/ai/report.py` 只應將以下欄位轉成強 Signal：

- `confidence in {"high", "primary"}`
- 或明確標成 `external_only` 且文字降級為「外部參考訊號」

禁止：

- 把 `conflict` 欄位寫成肯定命盤結論。
- 把 `life_chart_engine` 的紫微結果直接視為更準。
- 在沒有 golden sample 的情況下宣稱「已校準」。

## 第一階段實作

新增：

```text
app/calculators/ziwei_fusion.py
```

責任：

- 接受 primary chart 與 external charts。
- 產出 `fusion` metadata。
- 保留每個欄位的 provider、confidence、candidates。
- 不直接呼叫外部 AGPL code。

`app/calculators/ziwei.py` 仍是目前 API 的 primary provider。未來若接入 `ziwei-doushu` 完整 engine，先替換 primary provider，再讓 fusion 層做外部校準。
