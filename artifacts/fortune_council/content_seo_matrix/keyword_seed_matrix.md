# Pantheon 關鍵字導向文章矩陣 v1

任務ID：CARD-FORTUNE-KEYWORD-SEED-MATRIX-001
範圍：SEO / AEO / GEO 種子關鍵字矩陣，不寫正文、不開發頁面

## 1. 先修正

前一版 `article_matrix.md` 是「產品主題矩陣」，不是「熱門關鍵字矩陣」。

這一版改成：

```text
先用使用者真的會搜的詞建立文章。
每篇文章都對準一個主關鍵字。
再用內部連結把 MBTI、塔羅、命盤、星座、五大人生主題串起來。
```

重要限制：

```text
這份是種子關鍵字矩陣。
它不是搜尋量報告。
真正熱門程度需要再用 Google Search Console、Google Ads 關鍵字規劃工具、Ahrefs、Semrush 或 Similarweb 驗證。
```

## 2. 關鍵字主軸

先分 6 條內容線：

| 內容線 | 核心搜尋詞 | 文章型態 |
|---|---|---|
| MBTI 基礎 | MBTI 是什麼、16 型人格、MBTI 測驗、MBTI 人格 | 解釋文、類型文、比較文 |
| MBTI 64 分支 | INTJ 是什麼、INTJ-A、INTJ-T、16 型人格完整解析 | 類型頁、分支頁 |
| 塔羅牌義 | 塔羅牌意思、塔羅牌正位逆位、愚者牌意思 | 單牌頁、牌義頁 |
| 命盤 / 命書 | 命盤是什麼、八字是什麼、紫微斗數是什麼、命宮是什麼 | 解釋頁、宮位頁、星曜頁 |
| 星座 / 星盤 | 上升星座是什麼、月亮星座是什麼、星盤是什麼 | 星座頁、星盤頁 |
| 五大人生主題 | 感情塔羅、事業運勢、人際關係、財富運勢、人生方向 | 主題頁、問題頁 |

## 3. MBTI 基礎關鍵字文章

| ID | 主關鍵字 | 標題 | 搜尋意圖 | 內部連結 |
|---|---|---|---|---|
| MBTI-BASE-01 | MBTI 是什麼 | MBTI 是什麼？16 型人格怎麼看、適合拿來做什麼 | 解釋 MBTI | MBTI-BASE-02, MBTI-TYPE-HUB |
| MBTI-BASE-02 | 16 型人格 | 16 型人格完整整理：每一型的特質、感情、工作與人際 | 查 16 型總覽 | MBTI-BASE-01, MBTI-TYPE-HUB |
| MBTI-BASE-03 | MBTI 測驗 | MBTI 測驗前先知道：它能幫你看什麼、不能代表什麼 | 找測驗與限制 | MBTI-BASE-01, THEME-DIRECTION |
| MBTI-BASE-04 | MBTI 人格 | MBTI 人格怎麼用在自我理解、感情與事業選擇 | 應用 MBTI | THEME-LOVE, THEME-CAREER |
| MBTI-BASE-05 | MBTI 準嗎 | MBTI 準嗎？為什麼有人覺得很像、有人覺得不準 | 查可信度 | MBTI-BASE-03, RISK-PSYCHOLOGY |
| MBTI-BASE-06 | MBTI 代表什麼 | MBTI 四個字母代表什麼？E/I、S/N、T/F、J/P 白話解釋 | 查字母意思 | MBTI-BASE-01, MBTI-TYPE-HUB |
| MBTI-BASE-07 | MBTI 感情 | MBTI 怎麼看感情模式？適合看相處，不適合決定命運 | 感情應用 | THEME-LOVE, TAROT-LOVE |
| MBTI-BASE-08 | MBTI 工作 | MBTI 怎麼看工作方式？適合看節奏，不適合當職涯答案 | 工作應用 | THEME-CAREER, CHART-CAREER |

## 4. MBTI 16 型總頁

| ID | 主關鍵字 | 標題 | 上下篇 | 跨線連結 |
|---|---|---|---|---|
| MBTI-TYPE-HUB | 16 型人格 | 16 型人格總覽：INTJ 到 ESFP 的差異與使用方式 | 上：MBTI-BASE-02 / 下：MBTI-INTJ | THEME-DIRECTION, MBTI-BASE-06 |
| MBTI-INTJ | INTJ | INTJ 是什麼？INTJ 人格特質、感情、事業與人際模式 | 上：MBTI-TYPE-HUB / 下：MBTI-INTP | THEME-CAREER, THEME-DIRECTION |
| MBTI-INTP | INTP | INTP 是什麼？INTP 人格特質、感情、事業與人際模式 | 上：MBTI-INTJ / 下：MBTI-INFJ | THEME-DIRECTION, THEME-INTERPERSONAL |
| MBTI-INFJ | INFJ | INFJ 是什麼？INFJ 人格特質、感情、事業與人際模式 | 上：MBTI-INTP / 下：MBTI-INFP | THEME-LOVE, THEME-DIRECTION |
| MBTI-INFP | INFP | INFP 是什麼？INFP 人格特質、感情、事業與人際模式 | 上：MBTI-INFJ / 下：MBTI-ISTJ | THEME-LOVE, TAROT-LOVE |
| MBTI-ISTJ | ISTJ | ISTJ 是什麼？ISTJ 人格特質、感情、事業與人際模式 | 上：MBTI-INFP / 下：MBTI-ISFJ | THEME-CAREER, THEME-WEALTH |
| MBTI-ISFJ | ISFJ | ISFJ 是什麼？ISFJ 人格特質、感情、事業與人際模式 | 上：MBTI-ISTJ / 下：MBTI-ISTP | THEME-INTERPERSONAL, THEME-LOVE |
| MBTI-ISTP | ISTP | ISTP 是什麼？ISTP 人格特質、感情、事業與人際模式 | 上：MBTI-ISFJ / 下：MBTI-ISFP | THEME-CAREER, THEME-WEALTH |
| MBTI-ISFP | ISFP | ISFP 是什麼？ISFP 人格特質、感情、事業與人際模式 | 上：MBTI-ISTP / 下：MBTI-ENTJ | THEME-LOVE, THEME-DIRECTION |
| MBTI-ENTJ | ENTJ | ENTJ 是什麼？ENTJ 人格特質、感情、事業與人際模式 | 上：MBTI-ISFP / 下：MBTI-ENTP | THEME-CAREER, THEME-WEALTH |
| MBTI-ENTP | ENTP | ENTP 是什麼？ENTP 人格特質、感情、事業與人際模式 | 上：MBTI-ENTJ / 下：MBTI-ENFJ | THEME-CAREER, THEME-INTERPERSONAL |
| MBTI-ENFJ | ENFJ | ENFJ 是什麼？ENFJ 人格特質、感情、事業與人際模式 | 上：MBTI-ENTP / 下：MBTI-ENFP | THEME-INTERPERSONAL, THEME-LOVE |
| MBTI-ENFP | ENFP | ENFP 是什麼？ENFP 人格特質、感情、事業與人際模式 | 上：MBTI-ENFJ / 下：MBTI-ESTJ | THEME-DIRECTION, THEME-INTERPERSONAL |
| MBTI-ESTJ | ESTJ | ESTJ 是什麼？ESTJ 人格特質、感情、事業與人際模式 | 上：MBTI-ENFP / 下：MBTI-ESFJ | THEME-CAREER, THEME-WEALTH |
| MBTI-ESFJ | ESFJ | ESFJ 是什麼？ESFJ 人格特質、感情、事業與人際模式 | 上：MBTI-ESTJ / 下：MBTI-ESTP | THEME-INTERPERSONAL, THEME-LOVE |
| MBTI-ESTP | ESTP | ESTP 是什麼？ESTP 人格特質、感情、事業與人際模式 | 上：MBTI-ESFJ / 下：MBTI-ESFP | THEME-CAREER, THEME-WEALTH |
| MBTI-ESFP | ESFP | ESFP 是什麼？ESFP 人格特質、感情、事業與人際模式 | 上：MBTI-ESTP / 下：MBTI-TYPE-HUB | THEME-INTERPERSONAL, THEME-DIRECTION |

## 5. MBTI 64 分支展開規則

Pantheon 的 64 分支不要硬搶官方 MBTI 詞。文章標題建議用：

```text
INTJ-AH 是什麼？Pantheon 64 分支人格解析
INTJ-AC 是什麼？Pantheon 64 分支人格解析
INTJ-OH 是什麼？Pantheon 64 分支人格解析
INTJ-OC 是什麼？Pantheon 64 分支人格解析
```

64 篇矩陣：

| 主型 | 分支文章 |
|---|---|
| INTJ | INTJ-AH, INTJ-AC, INTJ-OH, INTJ-OC |
| INTP | INTP-AH, INTP-AC, INTP-OH, INTP-OC |
| INFJ | INFJ-AH, INFJ-AC, INFJ-OH, INFJ-OC |
| INFP | INFP-AH, INFP-AC, INFP-OH, INFP-OC |
| ISTJ | ISTJ-AH, ISTJ-AC, ISTJ-OH, ISTJ-OC |
| ISFJ | ISFJ-AH, ISFJ-AC, ISFJ-OH, ISFJ-OC |
| ISTP | ISTP-AH, ISTP-AC, ISTP-OH, ISTP-OC |
| ISFP | ISFP-AH, ISFP-AC, ISFP-OH, ISFP-OC |
| ENTJ | ENTJ-AH, ENTJ-AC, ENTJ-OH, ENTJ-OC |
| ENTP | ENTP-AH, ENTP-AC, ENTP-OH, ENTP-OC |
| ENFJ | ENFJ-AH, ENFJ-AC, ENFJ-OH, ENFJ-OC |
| ENFP | ENFP-AH, ENFP-AC, ENFP-OH, ENFP-OC |
| ESTJ | ESTJ-AH, ESTJ-AC, ESTJ-OH, ESTJ-OC |
| ESFJ | ESFJ-AH, ESFJ-AC, ESFJ-OH, ESFJ-OC |
| ESTP | ESTP-AH, ESTP-AC, ESTP-OH, ESTP-OC |
| ESFP | ESFP-AH, ESFP-AC, ESFP-OH, ESFP-OC |

每篇都要連：

```text
上層：該主型頁，例如 INTJ 是什麼
同層：同主型其他 3 個分支
跨線：感情 / 事業 / 人際 / 財富 / 人生方向中最適合的 2 個主題頁
```

## 6. 塔羅牌義矩陣

塔羅應該先搶這種搜尋詞：

```text
塔羅牌意思
塔羅牌正位
塔羅牌逆位
愚者牌意思
魔術師牌正位逆位
塔羅感情
塔羅工作
塔羅問題怎麼問
```

### 大阿爾克那 22 篇

| ID | 主關鍵字 | 標題 |
|---|---|---|
| TAROT-M00 | 愚者牌意思 | 愚者牌意思：正位、逆位、感情與工作怎麼看 |
| TAROT-M01 | 魔術師牌意思 | 魔術師牌意思：正位、逆位、感情與工作怎麼看 |
| TAROT-M02 | 女祭司牌意思 | 女祭司牌意思：正位、逆位、感情與工作怎麼看 |
| TAROT-M03 | 皇后牌意思 | 皇后牌意思：正位、逆位、感情與工作怎麼看 |
| TAROT-M04 | 皇帝牌意思 | 皇帝牌意思：正位、逆位、感情與工作怎麼看 |
| TAROT-M05 | 教皇牌意思 | 教皇牌意思：正位、逆位、感情與工作怎麼看 |
| TAROT-M06 | 戀人牌意思 | 戀人牌意思：正位、逆位、感情與工作怎麼看 |
| TAROT-M07 | 戰車牌意思 | 戰車牌意思：正位、逆位、感情與工作怎麼看 |
| TAROT-M08 | 力量牌意思 | 力量牌意思：正位、逆位、感情與工作怎麼看 |
| TAROT-M09 | 隱者牌意思 | 隱者牌意思：正位、逆位、感情與工作怎麼看 |
| TAROT-M10 | 命運之輪牌意思 | 命運之輪牌意思：正位、逆位、感情與工作怎麼看 |
| TAROT-M11 | 正義牌意思 | 正義牌意思：正位、逆位、感情與工作怎麼看 |
| TAROT-M12 | 吊人牌意思 | 吊人牌意思：正位、逆位、感情與工作怎麼看 |
| TAROT-M13 | 死神牌意思 | 死神牌意思：正位、逆位、感情與工作怎麼看 |
| TAROT-M14 | 節制牌意思 | 節制牌意思：正位、逆位、感情與工作怎麼看 |
| TAROT-M15 | 惡魔牌意思 | 惡魔牌意思：正位、逆位、感情與工作怎麼看 |
| TAROT-M16 | 高塔牌意思 | 高塔牌意思：正位、逆位、感情與工作怎麼看 |
| TAROT-M17 | 星星牌意思 | 星星牌意思：正位、逆位、感情與工作怎麼看 |
| TAROT-M18 | 月亮牌意思 | 月亮牌意思：正位、逆位、感情與工作怎麼看 |
| TAROT-M19 | 太陽牌意思 | 太陽牌意思：正位、逆位、感情與工作怎麼看 |
| TAROT-M20 | 審判牌意思 | 審判牌意思：正位、逆位、感情與工作怎麼看 |
| TAROT-M21 | 世界牌意思 | 世界牌意思：正位、逆位、感情與工作怎麼看 |

### 小阿爾克那 56 篇展開

| 牌組 | 文章 |
|---|---|
| 權杖 | 權杖一、權杖二、權杖三、權杖四、權杖五、權杖六、權杖七、權杖八、權杖九、權杖十、權杖侍者、權杖騎士、權杖皇后、權杖國王 |
| 聖杯 | 聖杯一、聖杯二、聖杯三、聖杯四、聖杯五、聖杯六、聖杯七、聖杯八、聖杯九、聖杯十、聖杯侍者、聖杯騎士、聖杯皇后、聖杯國王 |
| 寶劍 | 寶劍一、寶劍二、寶劍三、寶劍四、寶劍五、寶劍六、寶劍七、寶劍八、寶劍九、寶劍十、寶劍侍者、寶劍騎士、寶劍皇后、寶劍國王 |
| 錢幣 | 錢幣一、錢幣二、錢幣三、錢幣四、錢幣五、錢幣六、錢幣七、錢幣八、錢幣九、錢幣十、錢幣侍者、錢幣騎士、錢幣皇后、錢幣國王 |

每篇標題格式：

```text
權杖一意思：正位、逆位、感情與工作怎麼看
聖杯二意思：正位、逆位、感情與工作怎麼看
寶劍三意思：正位、逆位、感情與工作怎麼看
錢幣十意思：正位、逆位、感情與工作怎麼看
```

每篇都要連：

```text
塔羅牌意思總覽
同牌組上一篇 / 下一篇
感情塔羅總頁
事業塔羅總頁
五大主題中最相關的一篇
```

## 7. 命盤 / 紫微 / 八字矩陣

先搶解釋型關鍵字：

| ID | 主關鍵字 | 標題 |
|---|---|---|
| CHART-BASE-01 | 命盤是什麼 | 命盤是什麼？八字、紫微斗數和星盤差在哪 |
| CHART-BASE-02 | 八字是什麼 | 八字是什麼？出生年月日時怎麼看人生節奏 |
| CHART-BASE-03 | 紫微斗數是什麼 | 紫微斗數是什麼？命盤十二宮和主星怎麼看 |
| CHART-BASE-04 | 命宮是什麼 | 命宮是什麼？它在紫微斗數裡代表什麼 |
| CHART-BASE-05 | 夫妻宮是什麼 | 夫妻宮是什麼？感情關係可以怎麼看 |
| CHART-BASE-06 | 財帛宮是什麼 | 財帛宮是什麼？財富和資源節奏可以怎麼看 |
| CHART-BASE-07 | 官祿宮是什麼 | 官祿宮是什麼？事業與工作定位可以怎麼看 |
| CHART-BASE-08 | 遷移宮是什麼 | 遷移宮是什麼？外部環境和人生變動怎麼看 |
| CHART-BASE-09 | 大限是什麼 | 大限是什麼？紫微斗數裡的十年節奏怎麼看 |
| CHART-BASE-10 | 流年是什麼 | 流年是什麼？年度運勢和人生方向怎麼看 |

紫微十四主星文章：

| 主關鍵字 | 標題 |
|---|---|
| 紫微星 | 紫微星代表什麼？個性、事業與人生方向怎麼看 |
| 天機星 | 天機星代表什麼？思考、變動與人生方向怎麼看 |
| 太陽星 | 太陽星代表什麼？表達、能見度與人際怎麼看 |
| 武曲星 | 武曲星代表什麼？財富、執行力與事業怎麼看 |
| 天同星 | 天同星代表什麼？情緒、享受與人際怎麼看 |
| 廉貞星 | 廉貞星代表什麼？界線、慾望與關係怎麼看 |
| 天府星 | 天府星代表什麼？資源、穩定與財富怎麼看 |
| 太陰星 | 太陰星代表什麼？安全感、感情與內在怎麼看 |
| 貪狼星 | 貪狼星代表什麼？慾望、人際與感情怎麼看 |
| 巨門星 | 巨門星代表什麼？溝通、懷疑與人際怎麼看 |
| 天相星 | 天相星代表什麼？合作、形象與人際怎麼看 |
| 天梁星 | 天梁星代表什麼？保護、責任與人生方向怎麼看 |
| 七殺星 | 七殺星代表什麼？突破、壓力與事業怎麼看 |
| 破軍星 | 破軍星代表什麼？改變、破局與人生方向怎麼看 |

## 8. 星座 / 星盤矩陣

先搶高搜尋意圖解釋詞：

| ID | 主關鍵字 | 標題 |
|---|---|---|
| ASTRO-BASE-01 | 星盤是什麼 | 星盤是什麼？太陽、月亮、上升星座怎麼看 |
| ASTRO-BASE-02 | 上升星座是什麼 | 上升星座是什麼？它和太陽星座差在哪 |
| ASTRO-BASE-03 | 月亮星座是什麼 | 月亮星座是什麼？它和情緒、安全感有什麼關係 |
| ASTRO-BASE-04 | 太陽星座是什麼 | 太陽星座是什麼？它代表個性還是人生方向 |
| ASTRO-BASE-05 | 金星星座是什麼 | 金星星座是什麼？感情、喜好與關係怎麼看 |
| ASTRO-BASE-06 | 火星星座是什麼 | 火星星座是什麼？行動力、慾望與衝突怎麼看 |
| ASTRO-BASE-07 | 水星星座是什麼 | 水星星座是什麼？溝通與思考方式怎麼看 |

12 上升星座：

| 主關鍵字 | 標題 |
|---|---|
| 上升牡羊 | 上升牡羊是什麼？外在氣質、感情與事業怎麼看 |
| 上升金牛 | 上升金牛是什麼？外在氣質、感情與事業怎麼看 |
| 上升雙子 | 上升雙子是什麼？外在氣質、感情與事業怎麼看 |
| 上升巨蟹 | 上升巨蟹是什麼？外在氣質、感情與事業怎麼看 |
| 上升獅子 | 上升獅子是什麼？外在氣質、感情與事業怎麼看 |
| 上升處女 | 上升處女是什麼？外在氣質、感情與事業怎麼看 |
| 上升天秤 | 上升天秤是什麼？外在氣質、感情與事業怎麼看 |
| 上升天蠍 | 上升天蠍是什麼？外在氣質、感情與事業怎麼看 |
| 上升射手 | 上升射手是什麼？外在氣質、感情與事業怎麼看 |
| 上升摩羯 | 上升摩羯是什麼？外在氣質、感情與事業怎麼看 |
| 上升水瓶 | 上升水瓶是什麼？外在氣質、感情與事業怎麼看 |
| 上升雙魚 | 上升雙魚是什麼？外在氣質、感情與事業怎麼看 |

月亮星座也可拆 12 篇，格式：

```text
月亮牡羊是什麼？情緒模式、安全感與感情怎麼看
月亮金牛是什麼？情緒模式、安全感與感情怎麼看
...
月亮雙魚是什麼？情緒模式、安全感與感情怎麼看
```

## 9. 五大主題關鍵字矩陣

這條線負責把高流量解釋文導回產品主題。

| ID | 主關鍵字 | 標題 |
|---|---|---|
| THEME-LOVE | 感情塔羅 | 感情塔羅怎麼問？復合、曖昧、關係卡住怎麼看 |
| THEME-CAREER | 事業運勢 | 事業運勢怎麼看？轉職、創業、工作卡住的整理方式 |
| THEME-INTERPERSONAL | 人際關係 | 人際關係卡住怎麼辦？人格、塔羅與命盤可以看什麼 |
| THEME-WEALTH | 財富運勢 | 財富運勢怎麼看？金錢焦慮、資源節奏與風險感 |
| THEME-DIRECTION | 人生方向 | 人生方向迷惘怎麼辦？塔羅、人格與命盤能幫你整理什麼 |

## 10. 第一批發布建議

第一批不要先寫五大主題問題文，應先搶高搜尋量解釋詞。

建議第一批 30 篇：

```text
MBTI:
- MBTI 是什麼
- 16 型人格
- MBTI 測驗
- MBTI 準嗎
- INTJ 是什麼
- INFP 是什麼
- INFJ 是什麼
- ENFP 是什麼

塔羅:
- 塔羅牌意思
- 塔羅牌正位逆位
- 愚者牌意思
- 魔術師牌意思
- 戀人牌意思
- 死神牌意思
- 高塔牌意思
- 世界牌意思

命盤:
- 命盤是什麼
- 八字是什麼
- 紫微斗數是什麼
- 命宮是什麼
- 夫妻宮是什麼
- 財帛宮是什麼

星座:
- 星盤是什麼
- 上升星座是什麼
- 月亮星座是什麼
- 太陽星座是什麼

五大主題:
- 感情塔羅
- 事業運勢
- 財富運勢
- 人生方向
```

## 11. 連結策略

每篇文章都要連三種頁：

```text
1. 同系列頁：例如愚者牌 -> 魔術師牌 -> 女祭司牌
2. 解釋總頁：例如愚者牌 -> 塔羅牌意思總覽
3. 產品主題頁：例如戀人牌 -> 感情塔羅，財帛宮 -> 財富運勢
```

不要讓文章只在同一分類內互連。每篇都至少跨到一個五大主題頁。

## 12. 標題規則

標題優先使用使用者會搜的短詞：

```text
MBTI 是什麼
INTJ 是什麼
塔羅牌意思
愚者牌意思
上升星座是什麼
命宮是什麼
紫微星代表什麼
感情塔羅怎麼問
```

不要先用太品牌化或太文青的標題，例如：

```text
你靈魂裡的高塔正在倒塌
宇宙如何提醒你愛情的方向
人生卡住時的神祕訊號
```

這些可以放正文，不適合當 SEO 主標題。

## 13. 驗證待辦

下一步要把這份種子矩陣丟進關鍵字工具查：

```text
月搜尋量
競爭度
相關問題
長尾詞
搜尋結果頁競品
是否適合做總頁或單篇
```

沒有這一步，不能宣稱「已確認熱門」。
