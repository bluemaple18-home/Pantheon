# Pantheon Multi-Entry Council Final Brief

任務ID：CARD-FORTUNE-MULTI-ENTRY-COUNCIL-001
用途：PM 只讀這份 brief，不讀完整 council 討論

## Metadata

```text
產品構想: 以 64 人格、塔羅、命盤/命書組成 Pantheon 命理產品入口 portfolio
目標客群: 對自我理解、感情、職涯方向、人生節奏有興趣的年輕華語使用者
命理類型: 64 人格、塔羅、八字/紫微命盤、後續完整命書
收費想法: 免費低摩擦入口先測；付費命書與追問包等入口驗證後再定
對應飛輪節點: 外部曝光 -> 免費入口 -> 命中感 -> Discord / 每日儀式 -> 深問題 -> 付費命書 / 追問 -> 分享
可用 Pantheon 能力: bazi / ziwei / mbti / tarot slot / unified_report
Council 角色數: 6
討論輪數: 2
狀態: recommend
```

## 1. 一句話結論

`recommend`，但不要把 64 人格、塔羅、命盤硬做成同一條流程，也不要把它們定成固定第一、第二、第三入口；三者都可獨立作第一入口，本輪只需要選一個最低成本假設優先驗證。

## 2. 建議方向

```text
第一版應該做:
先做入口策略與驗證設計。把 64 人格定義成 identity / share 入口，把塔羅定義成 daily ritual / current question 入口，把命盤/命書定義成 depth / paid report 入口；三者都可獨立作第一入口。

第一版不應該做:
不做前端、不做 API、不做 council runner、不做完整命書自動交付、不把三種系統硬包成單一 onboarding 流程。

最適合的命理元素:
64 人格負責身份感與分享；塔羅負責當下問題與回訪；八字/紫微負責長期底色與付費深度。

最適合的付費形式:
先不定價。先測入口吸引力、分享率、回訪率、Discord 意圖與深度探索意圖；付費命書與追問包等入口訊號明確後再設計。

應接到哪個下一步:
開產品需求卡，不開 MVP 技術切片。
```

## 3. 主要理由

| 理由 | 依據 | 信心 |
|---|---|---|
| 三個入口回答不同使用者問題 | 64 人格是「我是誰」、塔羅是「現在怎麼看」、命盤是「長期底色」 | high |
| 64 人格是最低成本優先驗證候選 | TASK-002 已完成 64 分支、low-margin 降級、UnifiedReport 回流 | high |
| 塔羅可作問題導向第一入口 | 現有策略文件把塔羅定義為當下議題與象徵反思，適合抓「我現在想問」 | high |
| 命盤/命書可作高意圖第一入口 | 八字/紫微目前是 MVP scaffold，強結論需要 evidence/confidence，因此本輪不做完整交付 | medium |
| 先做 portfolio 可避免產品失焦 | 硬串三系統會造成證據錯配、文案過重、開發過早 | high |

## 4. 入口地圖

| 入口 | 使用者問題 | 飛輪節點 | 成功指標 | 不該承擔 |
|---|---|---|---|---|
| 64 人格 | 我是什麼類型？我跟別人差在哪？ | 外部曝光、免費入口、分享、Discord 角色 | 完成率、分享率、進群意圖 | 不作心理診斷，不覆蓋命盤 |
| 塔羅 | 我現在這件事怎麼看？今天要留意什麼？ | 外部曝光、每日儀式、Discord 互動、回訪 | 回訪率、抽卡頻率、提問率 | 不作命運保證，不回推出生盤因果 |
| 命盤/命書 | 我的長期底色與人生節奏是什麼？ | 外部曝光、深問題、付費啟動、命書與追問 | 付費意圖、追問深度、報告滿意度 | 不在 MVP 階段講成完整傳統排盤 |

## 5. 最大風險

| 風險 | 為什麼重要 | 降級方式 |
|---|---|---|
| 產品被做成命理大雜燴 | 使用者不知道每一步為什麼存在 | 三個入口各自有一句話定位與成功指標 |
| 64 人格太像一般測驗 | 會削弱 Pantheon 的命理差異 | 接上命理世界觀，但保留 MBTI 自評邊界 |
| 塔羅文案過度預言 | 容易變成恐嚇或保證結果 | 只寫反思角度、提醒與可選行動 |
| 命盤講太滿 | MVP 算力不足時會傷信任 | 強結論必須有 evidence / confidence，不足則降級成問題 |
| 太早開發 | 需求還沒決定，會再次把產品策略變成畫面 | 下一張只開產品需求卡 |

## 6. 反對意見

```text
Skeptic / Risk Lead 最大反對:
不要因為三個入口都看起來有用，就把它們塞成一條很完整但失焦的流程。

這個反對是否成立:
成立。

若成立，怎麼縮小版本:
先定義入口 portfolio，再選一個低成本假設優先驗證。建議優先驗證 64 人格 identity/share，原因是既有完成度最高；但塔羅與命盤/命書仍可獨立作第一入口，不應被降級為第二或第三入口。
```

## 7. 成本摘要

```text
角色數: 6
輪數: 2
final brief token 上限: 1,500
使用模型層級: 中階模型即可
是否升級高階模型: no
升級理由: 本輪是產品入口收斂，不是定價、法規或 go/no-go 高風險決策
是否提前停止: no
停止原因: 已收斂到入口 portfolio 與下一張產品卡
```

## 8. Pantheon 接線

```text
需要新增 report signal:
本輪不新增。64 人格已有 signals；塔羅與命盤後續若進產品才補 signal 定義。

需要新增 combo card:
本輪不新增。後續產品卡可再定義 identity_share、daily_reflection、deep_report_intent。

可直接用既有能力:
MBTI 64 分支、UnifiedReport、八字/紫微 MVP、tarot reserved slot、現有飛輪模型。

需要另開技術卡:
不需要。下一張仍是產品需求卡。

不該現在開發的部分:
前端畫面、API、runner、完整命書自動交付、常駐 agent team。
```

## 9. 下一步

```text
[x] 開產品需求卡
[ ] 補目標客群
[ ] 補命理類型策略
[ ] 補 offer / pricing
[ ] 開 MVP 技術切片
[ ] 暫停
```

建議下一張卡：

```text
任務ID: CARD-FORTUNE-ENTRY-PORTFOLIO-PRD-001
卡片類型｜派工對象: product / fortune-project
請讀: artifacts/fortune_council/runs/multi_entry_001/final_brief.md, TASK-002/result.md, docs/mbti_tarot_hd_fusion_strategy.md, docs/agent_operating_model.md
任務目的: 把 64 人格、塔羅、命盤/命書三個入口整理成 PRD：定義每個入口可獨立作第一入口的使用者情境、飛輪節點、成功指標、風險邊界與本輪優先驗證建議；不開發前端/API/runner
證據路徑: artifacts/fortune_council/entry_portfolio_prd/
```

## 品質檢查

- PM 不需要看完整討論。
- 有反對意見。
- 有成本摘要。
- 沒有把命理講成保證。
- 沒有恐嚇式銷售。
- 有接上 Pantheon 飛輪。
- 有說清楚可用既有能力，且明確不開技術卡。
- 不提供醫療、法律、投資等專業建議或保證結果。
