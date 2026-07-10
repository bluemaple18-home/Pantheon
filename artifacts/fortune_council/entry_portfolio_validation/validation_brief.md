# Entry Portfolio Council Validation Brief

任務ID：CARD-FORTUNE-ENTRY-PORTFOLIO-VALIDATION-001
狀態：completed
範圍：臨時 council 內部驗證，不開發前端/API/runner，不做外部訪談

## 1. 最終結論

```text
三個入口都可以獨立作第一入口。
本輪若只選一個低成本假設優先驗證，建議選 64 人格 identity/share。
塔羅不是第二入口，而是「當下問題 / daily ritual」第一入口候選。
命盤/命書不是第三入口，而是「高意圖 / 深度報告」第一入口候選。
允許進下一張產品驗證卡，但卡片必須仍是 council / product validation，不是工程卡。
```

## 2. 已解問題

| 問題 | Council 結論 |
|---|---|
| 是否一定要有第一、第二、第三入口？ | 不需要。這是三種不同起心動念，不是固定漏斗順序。 |
| 三個入口是否都可作第一入口？ | 可以。64 人格抓身份，塔羅抓當下問題，命盤/命書抓高意圖深度。 |
| 本輪最低成本優先驗證誰？ | 64 人格。原因是既有完成度最高、成本最低、最容易測分享與社群角色。 |
| 塔羅是否被降級？ | 沒有。塔羅是獨立入口，適合日常回訪、情緒/問題導向流量。 |
| 命盤/命書是否被延後？ | 完整交付延後，但入口地位不延後。它仍可作高意圖第一入口。 |
| 是否需要外部訪談？ | 目前不需要。先完成 council validation，避免問題還沒收斂就去問使用者。 |
| 是否可以開發？ | 不可以。下一步仍是產品驗證，不是前端/API/runner。 |

## 3. 各角色判斷

### Product Lead

判斷：入口 portfolio 成立。

理由：三個入口對應三種不同使用者意圖。若硬串成單一路徑，會讓產品同時背上身份測驗、占卜互動、深度命書三種承諾，範圍會失控。

建議：下一張卡只驗證「哪一個入口假設最值得先測」，不要開功能。

### 64 Personality Lead

判斷：64 人格適合本輪低成本優先驗證。

理由：已有 64 分支、low-margin 降級、UnifiedReport 回流；可驗證命中感、分享感、Discord 角色意圖。

最大疑點：它容易被看成一般人格測驗。必須測使用者是否理解它和 Pantheon 命理世界觀的關係。

### Tarot Lead

判斷：塔羅可以獨立作第一入口，不該被寫成第二入口。

理由：塔羅抓的是「我現在有一件事想問」，這種意圖不需要先通過 64 人格或命盤。它也最適合 daily ritual 和 Discord 每日互動。

最大疑點：容易被誤解成預言或保證結果。文案必須固定在 symbolic reflection。

### Destiny Chart Lead

判斷：命盤/命書可以獨立作第一入口，但不建議本輪做完整交付。

理由：高意圖使用者可能一開始就想看命盤，不會先想做人格測驗或塔羅。但目前八字/紫微仍是 MVP scaffold，完整命書會拉高承諾與品質風險。

最大疑點：如果不展示足夠深度，命理感不足；如果展示太深，會超出目前證據鏈。

### Community / Offer Lead

判斷：三個入口都能接社群，但接法不同。

```text
64 人格 -> Discord 角色 / 自我介紹 / 分享
塔羅 -> 每日抽卡 / 今日問題 / 討論串
命盤/命書 -> 深問題 / 付費命書意圖 / 追問包
```

建議：不要把 Discord CTA 放成通用下一步；每個入口要有自己的進群理由。

### Skeptic / Risk Lead

判斷：最大風險是把「入口 portfolio」又做成「什麼都要的流程」。

禁止：

- 64 人格被寫成心理診斷。
- 塔羅被寫成命運保證。
- 命盤/命書在 MVP 算力下講成完整傳統排盤。
- 用焦慮、恐嚇、不買會後悔推付費。

建議：下一張卡只允許驗證一個入口假設，不能同時驗證三個完整產品。

### Cost Governor

判斷：本輪已足夠收斂，停止討論。

理由：繼續在 council 內部討論不會得到更多確定性。剩餘問題是 PM 策略取捨，不是 council 能自動解的問題。

建議：開 validation card，但不升級高階模型、不開 runner、不做工程。

## 4. Council 決策

```text
入口模型: 三入口 portfolio
固定入口順序: no
本輪優先驗證: 64 人格 identity/share
替代優先驗證 A: 塔羅 daily ritual，如果要先抓當下問題與回訪
替代優先驗證 B: 命盤/命書深度意圖，如果要先抓高意圖與付費深度
是否允許進下一張卡: yes
下一張卡類型: product validation
工程狀態: blocked by product decision
```

## 5. 需要 Matt 拍板的問題

以下問題 council 無法代替 PM 決定：

1. **本輪優先抓哪種使用者心情？**
   - 自我身份 / 分享：選 64 人格。
   - 當下問題 / 回訪：選塔羅。
   - 高意圖 / 深度付費：選命盤/命書。

2. **Pantheon 第一個對外訊號要像什麼？**
   - 像「很懂我的人格身份工具」。
   - 像「每天可問的塔羅儀式」。
   - 像「有深度的命盤/命書品牌」。

3. **短期最想優先驗證哪個商業訊號？**
   - 分享與社群角色。
   - 回訪與日常互動。
   - 付費深度意圖。

4. **是否接受 64 人格先測，但不代表它是 Pantheon 主產品？**
   - 若接受，下一張 validation card 以 64 人格為主。
   - 若不接受，改選塔羅或命盤/命書作優先驗證。

## 6. 建議下一張卡

```text
任務ID: CARD-FORTUNE-FIRST-ENTRY-VALIDATION-001
卡片類型｜派工對象: product / fortune-project
請讀: artifacts/fortune_council/entry_portfolio_validation/validation_brief.md, artifacts/fortune_council/entry_portfolio_prd/prd.md, artifacts/fortune_council/entry_portfolio_prd/experiment_plan.md
任務目的: 由 PM 選定本輪優先驗證入口（64 人格 / 塔羅 / 命盤命書三選一），並定義該入口的非開發驗證方式、成功訊號、失敗訊號與停止條件；不得開發前端/API/runner，不做外部訪談，未拍板前不得拆技術卡
證據路徑: artifacts/fortune_council/first_entry_validation/
```

## 7. 驗收

- 已跑完 7 個 council 角色。
- 已解完 council 能解的產品結構問題。
- 已列出需要 Matt 拍板的策略問題。
- 未要求前端/API/runner。
- 未要求外部使用者訪談。
- 下一步是 PM 選擇優先驗證入口。
