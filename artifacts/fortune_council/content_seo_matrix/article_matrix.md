# Pantheon 五大主題文章矩陣

任務ID：CARD-FORTUNE-CONTENT-MATRIX-001
範圍：文章清單與內部連結架構，不寫正文、不開發頁面

## 1. 目標

這份矩陣用來大量產出文章，服務三種搜尋需求：

```text
SEO：搜尋排名，讓 Google / Bing 這類搜尋引擎找到文章。
AEO：答案引擎，讓問答型搜尋可以直接引用文章段落回答問題。
GEO：生成式搜尋引用，讓 AI 搜尋整理答案時容易引用 Pantheon 的內容。
```

目前先不做關鍵字流量驗證，先建立內容地圖與連結架構。

## 2. 主題架構

總入口：

- [五大人生主題命理指南](/topics/)

五大分類入口：

- [感情命理指南](/topics/love/)
- [事業命理指南](/topics/career/)
- [人際命理指南](/topics/relationships/)
- [財富命理指南](/topics/wealth/)
- [人生方向命理指南](/topics/life-direction/)

## 3. 內部連結規則

每篇文章都要有 5 種連結：

```text
1. 連到總入口：五大人生主題命理指南
2. 連到所屬分類入口
3. 連到同分類上一篇 / 下一篇
4. 連到同分類 2 篇相關文章
5. 連到跨分類 2 篇相關文章
```

文章開頭建議放：

```text
你正在閱讀：[分類入口] > [本篇文章]
相關主題：[跨分類文章 1]、[跨分類文章 2]
```

文章結尾建議放：

```text
上一篇：[同分類上一篇]
下一篇：[同分類下一篇]
延伸閱讀：[同分類相關]、[跨分類相關]
```

## 4. 總入口與分類入口

| ID | 標題連結 | 目的 | 必連文章 |
|---|---|---|---|
| HUB-00 | [五大人生主題命理指南](/topics/) | 總入口，解釋感情、事業、人際、財富、人生方向 | HUB-01, HUB-02, HUB-03, HUB-04, HUB-05 |
| HUB-01 | [感情命理指南](/topics/love/) | 感情分類入口 | L01, L02, L03, L04 |
| HUB-02 | [事業命理指南](/topics/career/) | 事業分類入口 | C01, C02, C03, C04 |
| HUB-03 | [人際命理指南](/topics/relationships/) | 人際分類入口 | R01, R02, R03, R04 |
| HUB-04 | [財富命理指南](/topics/wealth/) | 財富分類入口 | W01, W02, W03, W04 |
| HUB-05 | [人生方向命理指南](/topics/life-direction/) | 人生方向分類入口 | D01, D02, D03, D04 |

## 5. 感情文章矩陣

| ID | 標題連結 | 回答問題 | 上下篇 | 跨分類連結 |
|---|---|---|---|---|
| L01 | [塔羅怎麼看一段關係現在卡在哪](/topics/love/tarot-relationship-stuck/) | 這段關係現在卡住是因為什麼？ | 上：HUB-01 / 下：L02 | R01, D01 |
| L02 | [曖昧關係怎麼用塔羅整理訊號](/topics/love/tarot-situationship-signals/) | 曖昧到底該繼續還是停下？ | 上：L01 / 下：L03 | R02, D02 |
| L03 | [復合前先看清楚三件事](/topics/love/before-getting-back-together/) | 復合前我該先確認什麼？ | 上：L02 / 下：L04 | R03, D03 |
| L04 | [為什麼我總是遇到同一種感情模式](/topics/love/repeating-relationship-patterns/) | 我是不是一直重複同一種關係？ | 上：L03 / 下：L05 | R04, D04 |
| L05 | [感情裡的不安全感從哪裡來](/topics/love/relationship-insecurity/) | 我為什麼在感情裡一直不安？ | 上：L04 / 下：L06 | W02, R05 |
| L06 | [伴侶相處卡住時可以問自己的五個問題](/topics/love/couple-conflict-questions/) | 伴侶關係卡住時我該怎麼整理？ | 上：L05 / 下：L07 | R06, D05 |
| L07 | [命盤可以怎麼看感情裡的長期模式](/topics/love/birth-chart-love-patterns/) | 命盤能看出我的感情模式嗎？ | 上：L06 / 下：L08 | D06, R07 |
| L08 | [塔羅抽到逆位牌時感情一定不好嗎](/topics/love/tarot-reversed-love/) | 逆位牌是不是代表感情沒救？ | 上：L07 / 下：L09 | D07, R08 |
| L09 | [感情選擇題：該主動、等待，還是放下](/topics/love/love-choice-active-wait-let-go/) | 我該主動、等待還是放下？ | 上：L08 / 下：L10 | D08, C03 |
| L10 | [如何分辨直覺、焦慮和真正的感情提醒](/topics/love/intuition-anxiety-love/) | 我現在是直覺還是焦慮？ | 上：L09 / 下：L11 | D09, R09 |
| L11 | [感情塔羅問題怎麼問才不會越問越亂](/topics/love/how-to-ask-love-tarot/) | 感情問題怎麼問塔羅比較清楚？ | 上：L10 / 下：L12 | D10, R10 |
| L12 | [感情主題命書適合看什麼](/topics/love/love-report-guide/) | 感情主題報告應該包含什麼？ | 上：L11 / 下：HUB-01 | D11, W04 |

## 6. 事業文章矩陣

| ID | 標題連結 | 回答問題 | 上下篇 | 跨分類連結 |
|---|---|---|---|---|
| C01 | [現在適合轉職嗎：先整理三個訊號](/topics/career/should-i-change-job/) | 我現在適合轉職嗎？ | 上：HUB-02 / 下：C02 | D01, W01 |
| C02 | [工作卡住時塔羅可以幫你看什麼](/topics/career/tarot-career-stuck/) | 工作卡住可以問塔羅什麼？ | 上：C01 / 下：C03 | D02, R01 |
| C03 | [職場選擇題：穩定、成長、自由怎麼取捨](/topics/career/stability-growth-freedom/) | 工作選擇要看什麼取捨？ | 上：C02 / 下：C04 | W02, D03 |
| C04 | [人格特質如何影響你的工作方式](/topics/career/personality-work-style/) | 我適合什麼工作節奏？ | 上：C03 / 下：C05 | R02, D04 |
| C05 | [命盤可以怎麼看事業節奏](/topics/career/birth-chart-career-timing/) | 命盤能看事業節奏嗎？ | 上：C04 / 下：C06 | W03, D05 |
| C06 | [創業前可以先問自己的五個命理問題](/topics/career/before-starting-business/) | 我適合創業嗎？ | 上：C05 / 下：C07 | W04, D06 |
| C07 | [主管同事關係不順時要先看哪裡](/topics/career/workplace-relationship-stuck/) | 職場人際卡住怎麼整理？ | 上：C06 / 下：C08 | R03, R04 |
| C08 | [為什麼我工作很努力但一直沒被看見](/topics/career/not-being-seen-at-work/) | 為什麼努力沒有回報？ | 上：C07 / 下：C09 | R05, W05 |
| C09 | [職涯迷惘時不要急著問該做什麼](/topics/career/career-confusion/) | 職涯迷惘時第一步是什麼？ | 上：C08 / 下：C10 | D07, D08 |
| C10 | [塔羅看工作選擇時最適合問的問題](/topics/career/how-to-ask-career-tarot/) | 工作問題怎麼問塔羅？ | 上：C09 / 下：C11 | L11, D09 |
| C11 | [年度事業主題報告適合看什麼](/topics/career/annual-career-report-guide/) | 年度事業報告應該包含什麼？ | 上：C10 / 下：C12 | W06, D10 |
| C12 | [事業主題命書可以幫你整理什麼](/topics/career/career-report-guide/) | 事業命書該看哪些面向？ | 上：C11 / 下：HUB-02 | W07, D11 |

## 7. 人際文章矩陣

| ID | 標題連結 | 回答問題 | 上下篇 | 跨分類連結 |
|---|---|---|---|---|
| R01 | [人際關係卡住時先看互動模式](/topics/relationships/relationship-patterns/) | 我的人際為什麼總卡住？ | 上：HUB-03 / 下：R02 | L01, C02 |
| R02 | [為什麼我在人群裡容易累](/topics/relationships/social-energy/) | 我為什麼社交後很累？ | 上：R01 / 下：R03 | C04, D01 |
| R03 | [朋友關係變淡，是自然變化還是需要處理](/topics/relationships/friendship-changing/) | 朋友變淡要怎麼看？ | 上：R02 / 下：R04 | L03, D02 |
| R04 | [職場人際和私人關係為什麼不能混在一起看](/topics/relationships/work-personal-boundaries/) | 工作與私人關係界線怎麼看？ | 上：R03 / 下：R05 | C07, L04 |
| R05 | [被看見的渴望會怎麼影響人際選擇](/topics/relationships/need-to-be-seen/) | 我為什麼很想被看見？ | 上：R04 / 下：R06 | C08, L05 |
| R06 | [人際界線感不足時塔羅可以提醒什麼](/topics/relationships/tarot-boundaries/) | 人際界線怎麼整理？ | 上：R05 / 下：R07 | L06, D03 |
| R07 | [人格結果如何看你的溝通習慣](/topics/relationships/personality-communication/) | 我溝通時容易卡在哪？ | 上：R06 / 下：R08 | L07, C04 |
| R08 | [命盤可以怎麼看長期人際課題](/topics/relationships/birth-chart-relationship-lessons/) | 命盤能看人際課題嗎？ | 上：R07 / 下：R09 | L08, D04 |
| R09 | [孤獨感不一定等於沒有人陪](/topics/relationships/loneliness-meaning/) | 我為什麼在人群裡也孤獨？ | 上：R08 / 下：R10 | L10, D05 |
| R10 | [人際問題怎麼問塔羅才不會變成控制別人](/topics/relationships/how-to-ask-relationship-tarot/) | 人際塔羅問題怎麼問才健康？ | 上：R09 / 下：R11 | L11, D06 |
| R11 | [社群角色和人格結果可以怎麼連起來](/topics/relationships/community-role-personality/) | 人格結果能怎麼用在社群？ | 上：R10 / 下：R12 | C08, W08 |
| R12 | [人際主題命書適合看什麼](/topics/relationships/relationship-report-guide/) | 人際主題報告應該包含什麼？ | 上：R11 / 下：HUB-03 | L12, D07 |

## 8. 財富文章矩陣

| ID | 標題連結 | 回答問題 | 上下篇 | 跨分類連結 |
|---|---|---|---|---|
| W01 | [財富不是只看會不會賺錢](/topics/wealth/wealth-is-not-only-income/) | 財富主題到底看什麼？ | 上：HUB-04 / 下：W02 | C01, D01 |
| W02 | [金錢焦慮從哪裡來](/topics/wealth/money-anxiety/) | 我為什麼一直為錢焦慮？ | 上：W01 / 下：W03 | L05, C03 |
| W03 | [命盤可以怎麼看資源節奏](/topics/wealth/birth-chart-resource-timing/) | 命盤能看財富節奏嗎？ | 上：W02 / 下：W04 | C05, D02 |
| W04 | [創業和財富問題不能只問會不會賺](/topics/wealth/business-money-questions/) | 創業財運該怎麼看？ | 上：W03 / 下：W05 | C06, L12 |
| W05 | [為什麼努力工作不一定等於安全感](/topics/wealth/work-and-security/) | 為什麼收入高還是不安？ | 上：W04 / 下：W06 | C08, D03 |
| W06 | [年度財富主題報告適合看什麼](/topics/wealth/annual-wealth-report-guide/) | 年度財富報告該看什麼？ | 上：W05 / 下：W07 | C11, D04 |
| W07 | [財富與事業的差別：一個看收入，一個看資源](/topics/wealth/wealth-vs-career/) | 財富和事業差在哪？ | 上：W06 / 下：W08 | C12, D05 |
| W08 | [人格特質如何影響花錢與冒險](/topics/wealth/personality-money-risk/) | 我花錢和冒險模式是什麼？ | 上：W07 / 下：W09 | R11, C04 |
| W09 | [塔羅可以怎麼看短期金錢提醒](/topics/wealth/tarot-money-reflection/) | 金錢問題可以問塔羅嗎？ | 上：W08 / 下：W10 | D06, C10 |
| W10 | [財富問題最不該問的三種命理問法](/topics/wealth/bad-money-tarot-questions/) | 金錢問題怎麼問才不誤導？ | 上：W09 / 下：W11 | L11, R10 |
| W11 | [財富主題小報告適合怎麼設計](/topics/wealth/wealth-mini-report-guide/) | 財富小報告應該包含什麼？ | 上：W10 / 下：W12 | C11, D10 |
| W12 | [財富主題命書適合看什麼](/topics/wealth/wealth-report-guide/) | 財富命書該看哪些面向？ | 上：W11 / 下：HUB-04 | C12, D11 |

## 9. 人生方向文章矩陣

| ID | 標題連結 | 回答問題 | 上下篇 | 跨分類連結 |
|---|---|---|---|---|
| D01 | [人生方向卡住時不要急著找答案](/topics/life-direction/life-direction-stuck/) | 我不知道人生往哪走怎麼辦？ | 上：HUB-05 / 下：D02 | L01, C01 |
| D02 | [塔羅可以怎麼整理人生方向問題](/topics/life-direction/tarot-life-direction/) | 人生方向可以問塔羅嗎？ | 上：D01 / 下：D03 | L02, C02 |
| D03 | [現在該動還是該等：時機問題怎麼看](/topics/life-direction/timing-move-or-wait/) | 現在該行動還是等待？ | 上：D02 / 下：D04 | L03, C03 |
| D04 | [人格結果如何看你的長期選擇偏好](/topics/life-direction/personality-life-choices/) | 我的選擇模式是什麼？ | 上：D03 / 下：D05 | L04, C04 |
| D05 | [命盤可以怎麼看人生階段](/topics/life-direction/birth-chart-life-stage/) | 命盤能看人生階段嗎？ | 上：D04 / 下：D06 | C05, R09 |
| D06 | [創業、轉職、搬家都算人生方向問題嗎](/topics/life-direction/life-change-decisions/) | 大變動該怎麼整理？ | 上：D05 / 下：D07 | C06, W09 |
| D07 | [迷惘時如何分辨害怕和真的不適合](/topics/life-direction/fear-or-misalignment/) | 我是害怕還是真的不適合？ | 上：D06 / 下：D08 | C09, R12 |
| D08 | [人生方向不是一次選完，而是分階段整理](/topics/life-direction/life-direction-stages/) | 人生方向可以分階段看嗎？ | 上：D07 / 下：D09 | C09, L09 |
| D09 | [如何用五大主題整理現在最重要的問題](/topics/life-direction/five-theme-priority/) | 我現在最該先看哪個主題？ | 上：D08 / 下：D10 | L10, C10 |
| D10 | [人生方向問題怎麼問才不會太空泛](/topics/life-direction/how-to-ask-life-direction/) | 人生方向問題怎麼問比較清楚？ | 上：D09 / 下：D11 | L11, W11 |
| D11 | [年度人生方向報告適合看什麼](/topics/life-direction/annual-life-direction-report/) | 年度方向報告應該包含什麼？ | 上：D10 / 下：D12 | L12, W12 |
| D12 | [完整命書和人生方向小報告差在哪](/topics/life-direction/full-report-vs-mini-report/) | 小報告和完整命書差在哪？ | 上：D11 / 下：HUB-05 | C12, W12 |

## 10. 第一批發布建議

不要一次寫 60 篇。第一批先寫 15 篇，讓五大主題都有骨架：

```text
總入口:
- HUB-00

分類入口:
- HUB-01
- HUB-02
- HUB-03
- HUB-04
- HUB-05

每類先寫前 2 篇:
- L01, L02
- C01, C02
- R01, R02
- W01, W02
- D01, D02
```

第一批目的：

- 先建立五大主題架構。
- 讓文章能互相連結。
- 讓搜尋引擎看得出 Pantheon 的主題範圍。
- 讓答案引擎與生成式搜尋能抓到清楚問答段落。

## 11. 每篇文章固定結構

```text
H1: 主標題
導言: 直接回答使用者問題
H2: 這個問題通常在問什麼
H2: 塔羅可以看什麼
H2: 64 人格可以補什麼
H2: 命盤/命書可以看什麼
H2: 五大主題裡它屬於哪一類
H2: 不該怎麼問或怎麼解讀
H2: 延伸閱讀
FAQ: 3 到 5 題短問短答
```

## 12. 答案引擎段落規則

每篇文章前 150 字要直接回答問題，例如：

```text
「這段關係卡住，不一定代表感情不好。比較準確的看法是：先分清楚它卡在溝通、期待、安全感，還是未來方向。塔羅適合整理當下狀態，人格適合看相處模式，命盤/命書適合看長期關係課題。」
```

每篇都要有：

- 一段 50 字內短答案。
- 一段 150 字內完整答案。
- 3 到 5 題常見問答。
- 內部連結到主題入口與相關文章。

## 13. 生成式搜尋引用規則

為了讓生成式搜尋更容易引用，每篇要固定包含：

```text
定義：這篇在講什麼
適用情境：什麼人會需要
不適用情境：什麼問題不該用命理回答
三種工具分工：塔羅 / 64 人格 / 命盤命書
下一步：讀哪一篇或看哪個主題
```

## 14. 禁止事項

```text
不可寫「保證復合」。
不可寫「一定發財」。
不可寫「注定失敗」。
不可提供醫療、法律、投資建議。
不可用恐嚇式標題。
不可把人格測驗寫成心理診斷。
不可把塔羅寫成預言。
不可把命盤/命書寫成絕對命運。
```
