# Pantheon Multi-Entry Council Final Brief

任務ID：CARD-FORTUNE-MULTI-ENTRY-COUNCIL-001
來源架構：CARD-FORTUNE-COUNCIL-TEAM-DESIGN-001
狀態：discussion-ready

## Metadata

```text
產品構想: 命理/人格產品先用 council 討論入口組合，不先做前端、不先做 runner
核心問題: 64 人格、塔羅、命盤/命書應該各自作為入口，還是被包成同一條流程？
目標客群: 對自我理解、感情、職涯方向、人生節奏有興趣的年輕華語使用者
候選入口: 64 人格、塔羅、八字/紫微命盤、後續完整命書
收費想法: 免費/低摩擦入口先測興趣；付費命書或追問包等入口驗證後再定
可用 Pantheon 能力: bazi / ziwei / mbti / unified_report
Council 角色數: 6
討論輪數: 最多 3
```

## 1. 一句話結論

先不要把塔羅、64 人格、命盤硬合成一條產品流程；應該先組一個臨時 council，評估三個入口各自的定位、吸引力、風險與商業接法，再決定第一個要測的入口。

## 2. 入口假設

| 入口 | 最適合解的問題 | 商業用途 | 主要風險 |
|---|---|---|---|
| 64 人格 | 「我是什麼樣的人？」、「我跟別人有什麼差異？」 | 分享、社群角色、低摩擦 onboarding | 太像一般人格測驗，命理感不足 |
| 塔羅 | 「我現在這件事怎麼看？」、「今天/這週要注意什麼？」 | 日常回訪、短問題、互動儀式 | 容易變成占卜保證或恐嚇式文案 |
| 命盤/命書 | 「我的長期底色與人生節奏是什麼？」 | 付費深報告、個人化命書、進階追問 | 算法與文案若講太滿會傷信任 |

## 3. Council 團隊

| 角色 | 要負責回答的問題 |
|---|---|
| Product Lead | 入口彼此是並行、串接，還是只先選一個？第一版驗證目標是什麼？ |
| Tarot Lead | 塔羅適合做日常 ritual、單題互動，還是第一個主入口？ |
| 64 Personality Lead | 64 人格如何做出分享感、辨識度、社群身份，而不是普通測驗？ |
| Destiny Chart Lead | 八字/紫微/命書應該何時出現，負責免費信任還是付費深度？ |
| Community / Offer Lead | Discord、追問包、命書、分享應該接在哪個行為之後？ |
| Skeptic / Risk Lead | 哪些說法會變成醫療、法律、投資保證、恐嚇銷售或平台風險？ |

## 4. 討論流程

```text
第 1 輪: 各角色獨立提出「自己的入口為何值得先測」。
第 2 輪: Skeptic / Risk Lead 指出混在一起會造成的產品混亂、成本失控、信任風險。
第 3 輪: Product Lead 收斂成 PM brief，只給入口地圖與下一張產品討論卡，不給技術實作卡。
```

## 5. 本輪不做的事

```text
不做前端畫面。
不做 API。
不做 council runner。
不做常駐 agent team。
不決定完整命書交付形式。
不把「塔羅 + 64 人格 + 命盤」硬包成單一路徑。
```

## 6. 風險邊界

```text
可以做:
自我理解、關係反思、職涯偏好、生活節奏、儀式感、娛樂性洞察。

不可以做:
醫療診斷或治療建議。
法律判斷或合規保證。
投資報酬保證。
「不買會倒楣」這類恐嚇式銷售。
宣稱命理結果必然發生。
利用焦慮、失戀、重大人生危機逼迫升級付費。
```

## 7. 成本政策

```text
角色數上限: 6
討論輪數上限: 3
每位角色每輪輸出: 300 到 500 tokens
Final brief 上限: 1,500 tokens
預設模型: 中階模型即可
升級高階模型條件: 需要定價、法規風險、品牌定位重大取捨時才升級
PM 可見內容: 只看 final brief，不看完整討論紀錄
```

## 8. 下一步

建議下一張仍是產品討論卡，不是技術卡：

```text
任務ID: CARD-FORTUNE-MULTI-ENTRY-COUNCIL-001
卡片類型｜派工對象: product / fortune-project
請讀: artifacts/fortune_council/team_design/, Pantheon 既有 bazi / ziwei / mbti / unified_report 能力摘要
任務目的: 讓 council 評估 64 人格、塔羅、命盤/命書三個入口是否並行、串接或擇一先測，產出 PM 可讀的入口地圖與第一個驗證建議；不開發前端/API/runner
證據路徑: artifacts/fortune_council/runs/multi_entry_001/
```

## 品質檢查

- 不要求常駐 agent team。
- 支援臨時自組 council。
- PM 只看 final brief，不看完整討論。
- 有反對者 / 風險倫理角色。
- 明確限制醫療、法律、投資保證、恐嚇式銷售。
- 有 token/cost 上限。
- 沒有產生前端/API/runner 開發卡。
