# Lite Council 流程

任務ID：CARD-FORTUNE-COUNCIL-TEAM-DESIGN-001
範圍：最多 2 輪，不建立 runner，不保存完整討論作為 PM 預設交付物

## 目標

用最小成本回答一件事：這個命理產品方向值不值得繼續開下一張產品或工程卡。

Council 的判斷必須接上 Pantheon 既有主線：

```text
外部曝光
→ 免費入口
→ 命中感
→ Discord 進群
→ 每日儀式
→ 深問題出現
→ 付費啟動
→ 命書與追問
→ 分享擴散
```

如果一個想法接不上這條飛輪，final brief 要明確說它是旁支、實驗，或暫停。

Council 不負責：

- 寫程式。
- 設計常駐 agent team。
- 產生完整銷售頁。
- 取代 PM 決策。

## 啟動輸入

```text
產品構想:
目標客群:
想使用的命理類型:
收費想法:
目前可用模型/API資源:
對應飛輪節點:
目前可用 report signal / combo card:
```

缺資料可以跑，但 final brief 要標出「缺什麼」。

## Round 1：各角色短評

每個角色只輸出：

```text
結論:
理由:
最大風險:
建議下一步:
```

Round 1 後，如果大家方向一致，就直接產出 final brief。

Round 1 必須先判斷：

- 這個方向對應哪個飛輪節點。
- 是否能使用現有八字、紫微、MBTI、UnifiedReport 證據鏈。
- 是否只是需要產品 brief，而不是工程開發。

## Round 2：只處理分歧

只有出現以下情況才跑 Round 2：

- Product Lead 和 Skeptic / Risk Lead 結論衝突。
- Offer Lead 的收費方案看起來成本或承諾失控。
- Fortune Content Lead 認為命理類型和使用者問題不匹配。
- Cost Governor 判定需要縮小範圍。
- 方向會讓 Pantheon 偏離「主流程先跑順，再拆 Agent」原則。

Round 2 只回答：

```text
主要分歧:
反對理由:
可接受的降級版本:
PM 需要決定什麼:
```

## Final Brief

最後只輸出 `council_brief_template.md` 的 brief。

PM 預設不看：

- 完整討論。
- 每個角色長篇推理。
- 模型原始輸出。

PM 預設看：

- 一句話結論。
- 推薦 / 修改 / 暫停。
- 最大風險。
- 下一步。
- 成本摘要。

## 停止條件

- 已跑 2 輪。
- 還缺關鍵輸入，繼續討論只是在猜。
- 產品價值依賴恐嚇式銷售或過度宿命論。
- 成本超過 `cost_policy.md` 預設上限。
- 需要先補 report signal / combo card，而不是繼續商業討論。

## 驗收對照

- 最多 2 輪。
- 臨時自組 council。
- PM 只看 final brief。
- 有反對者 / 風險角色。
