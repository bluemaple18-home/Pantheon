# Lite Council 角色設計

任務ID：CARD-FORTUNE-COUNCIL-TEAM-DESIGN-001
範圍：臨時自組 council，不建立常駐 agent team，不開發 runner

## 原則

- Council 只用來幫 PM 判斷產品方向，不是固定團隊。
- 預設 5 個角色，必要時才加人。
- PM 只看 final brief，不看完整討論。
- 反對者是必備角色，避免大家只是在幫想法找理由。

## Pantheon 既有脈絡

Council 評估時要以目前專案方向為基準：

- 產品不是單純排盤 API，而是「免費入口 → 命中感 → Discord → 深問題 → 付費命書 / 追問 → 分享」的商業飛輪。
- 目前已有 FastAPI 算命引擎骨架、八字/紫微 MVP、MBTI 64 分支、UnifiedReport 與證據鏈語法。
- 報告語法以「主題報告型 + 證據鏈型 + 格局卡型」為主，不追求傳統術語堆滿。
- MBTI 只作自評偏好與人格語言，不作正式心理測驗。
- 塔羅適合當下問題與象徵反思，不回推出生盤因果。
- 人類圖與外部 life-chart 類工具目前偏欄位參考 / 驗證靶，未驗證前不能作強結論。
- 短期不拆常駐多 Agent；先把主流程、內容、命書、Discord 互動跑順。

## 預設角色

| 角色 | 負責問題 |
|---|---|
| Product Lead | 這個 offer 放在 Pantheon 飛輪哪一段？第一版交付免費入口、命中感、命書還是追問？哪些先不做？ |
| Fortune Content Lead | 八字、紫微、MBTI、塔羅、人類圖各自該扮演什麼角色？哪些能進證據鏈，哪些只能作反思語言？ |
| Offer Lead | 免費入口、低價報告、付費命書、Discord 追問要怎麼包裝，才不會成本失控或承諾過重？ |
| Skeptic / Risk Lead | 哪裡太 AI 感、太宿命、太像收割焦慮、太容易造成客訴或信任崩壞？ |
| Cost Governor | 這輪討論有沒有超過角色數、輪數、token、模型成本？是否應該先停在 brief 而不是開發？ |

## 可選角色

| 角色 | 何時才加 |
|---|---|
| Community Lead | 要討論 Threads、Discord、社群互動時 |
| Technical Feasibility Lead | 已經要判斷現有 Pantheon engine 能不能做時 |
| Copy Lead | 已經有 offer，要檢查銷售頁或報告語氣時 |

## 每個角色輸入

```text
產品構想:
目標客群:
命理類型:
收費想法:
目前模型/API資源:
對應飛輪節點:
可用 report signal / combo card:
本輪要回答的問題:
```

## 每個角色輸出

```text
角色:
結論:
理由:
最大風險:
建議下一步:
信心: high / medium / low
```

## 驗收對照

- 不要求常駐 agent team。
- 支援臨時自組 council。
- 有反對者 / 風險角色。
- 不開發 runner。
