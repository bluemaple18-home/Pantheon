export const GLOBAL_ARTICLE_POLICY = {
  requiredTags: ["Pantheon", "繁體中文", "公開文章", "通用知識"],
  requiredKeywordTags: ["SEO", "AEO", "GEO"],
  publicContentBoundary: "公開文章只講通用知識，不給個人結論，不承諾結果。",
};

export const HUMANIZER_POLICY = {
  purpose: "文章內容要具體、可追問、保留限制，不用模板語氣假裝客觀。",
  bannedGenericPhrases: [
    "全面解析",
    "深度解析",
    "快速變化的時代",
    "不可或缺",
    "賦能",
    "不僅",
    "更是",
    "總而言之",
    "值得注意的是",
  ],
  requiredChecks: [
    "前 80 字直接回答主關鍵字",
    "摘要要說清楚適用情境與限制",
    "FAQ 不寫正確廢話，要回答真問題",
    "不得加入未提供的數據、經歷或承諾",
    "每篇至少保留一個不能代表什麼的邊界",
  ],
};

export const ARTICLE_SERIAL_REGISTRY = {
  "MBTI-BASE-01": "personality-0001",
  "MBTI-BASE-02": "personality-0002",
  "MBTI-BASE-03": "personality-0003",
  "MBTI-BASE-04": "personality-0004",
  "MBTI-TYPE-INTJ": "personality-0005",
  "MBTI-TYPE-INFP": "personality-0006",
  "MBTI-TYPE-INFJ": "personality-0007",
  "MBTI-TYPE-ENFP": "personality-0008",
  "TAROT-BASE-01": "tarot-0001",
  "TAROT-BASE-02": "tarot-0002",
  "TAROT-M00": "tarot-0003",
  "TAROT-M01": "tarot-0004",
  "TAROT-M06": "tarot-0005",
  "TAROT-M13": "tarot-0006",
  "TAROT-M16": "tarot-0007",
  "TAROT-M21": "tarot-0008",
  "CHART-BASE-01": "fortune-0001",
  "CHART-BASE-02": "fortune-0002",
  "CHART-ZIWEI-01": "fortune-0003",
  "CHART-ZIWEI-02": "fortune-0004",
  "CHART-ZIWEI-03": "fortune-0005",
  "CHART-ZIWEI-04": "fortune-0006",
  "ASTRO-BASE-01": "astrology-0001",
  "ASTRO-BASE-02": "astrology-0002",
  "ASTRO-BASE-03": "astrology-0003",
  "ASTRO-LOVE-01": "astrology-0004",
  "THEME-LOVE-01": "love-0001",
  "THEME-CAREER-01": "career-0001",
  "THEME-INTERPERSONAL-01": "interpersonal-0001",
  "THEME-WEALTH-01": "wealth-0001",
  "THEME-LIFE-01": "life-direction-0001",
};

export const PRODUCT_THEME_REGISTRY = {
  fortune: {
    label: "命盤",
    glyph: "命",
    description: "承接命書、八字、紫微與人生深題的暗金高信任視覺。",
  },
  personality: {
    label: "人格",
    glyph: "64",
    description: "承接 64 分支人格的矩陣、進度與身份標籤視覺。",
  },
  tarot: {
    label: "塔羅",
    glyph: "XVII",
    description: "承接塔羅日常儀式、牌陣與光門視覺。",
  },
  astro: {
    label: "星座",
    glyph: "星",
    description: "承接星場、軌道與星盤關聯視覺。",
  },
};

export const ARTICLE_URL_CONTRACT = {
  articlePattern: "/articles/{category}/{category}-{number}",
  productHubPattern: "/articles/{product}",
  intentHubPattern: "/articles/intents/{intent}",
  topicPattern: "/topics/{topic-slug}",
  categories: ["fortune", "personality", "tarot", "astrology", "love", "career", "interpersonal", "wealth", "life-direction"],
};

export const TOPIC_REGISTRY = [
  { id: "topic-0001", slug: "mbti", label: "MBTI", aliases: ["MBTI 是什麼", "MBTI 人格", "MBTI 測驗", "人格測驗"] },
  { id: "topic-0002", slug: "16-personalities", label: "16 型人格", aliases: ["16 型人格", "人格類型", "INTJ", "INFP", "INFJ", "ENFP"] },
  { id: "topic-0003", slug: "tarot", label: "塔羅", aliases: ["塔羅", "塔羅牌意思", "塔羅牌牌義", "牌義", "大阿爾克那", "魔術師牌意思", "愚者牌意思", "戀人牌意思", "死神牌意思", "高塔牌意思", "世界牌意思"] },
  { id: "topic-0004", slug: "upright-reversed", label: "正位逆位", aliases: ["正位逆位", "塔羅牌正位逆位", "塔羅逆位", "塔羅正位"] },
  { id: "topic-0005", slug: "fortune", label: "命盤", aliases: ["命盤", "個人命盤", "八字命盤", "紫微命盤"] },
  { id: "topic-0006", slug: "bazi", label: "八字", aliases: ["八字", "八字是什麼", "生辰八字", "干支"] },
  { id: "topic-0007", slug: "ziwei-doushu", label: "紫微斗數", aliases: ["紫微斗數", "紫微命盤", "命宮", "夫妻宮", "財帛宮"] },
  { id: "topic-0008", slug: "astrology", label: "星盤", aliases: ["星盤", "星盤是什麼", "個人星盤", "星盤查詢", "星座命盤", "占星命盤", "星座", "上升星座", "月亮星座"] },
  { id: "topic-0009", slug: "love", label: "感情", aliases: ["感情", "感情塔羅", "關係", "相處模式"] },
  { id: "topic-0010", slug: "career", label: "事業", aliases: ["事業", "工作", "職涯", "轉職"] },
  { id: "topic-0011", slug: "interpersonal", label: "人際", aliases: ["人際", "人際關係", "溝通", "關係界線"] },
  { id: "topic-0012", slug: "wealth", label: "財富", aliases: ["財富", "財運", "金錢觀", "資源"] },
  { id: "topic-0013", slug: "life-direction", label: "人生方向", aliases: ["人生方向", "人生迷惘", "自我理解", "選擇"] },
];

export const LIFE_INTENT_REGISTRY = {
  love: {
    label: "感情",
  },
  career: {
    label: "事業",
  },
  interpersonal: {
    label: "人際",
  },
  wealth: {
    label: "財富",
  },
  life: {
    label: "人生方向",
  },
};

export const ARTICLE_SECTION_REGISTRY = {
  fortune: {
    product: "fortune",
    intent: "",
    label: "命盤",
    description: "整理命盤、八字、紫微與人生主題文章，先建立公開知識，再說明適用情境與限制。",
    seoDescription: "Pantheon 命盤文章主頁，整理命盤是什麼、八字、紫微斗數與五大人生主題。",
    primaryKeyword: "命盤是什麼",
    requiredTags: ["命盤", "八字", "紫微斗數"],
  },
  astro: {
    product: "astro",
    intent: "",
    label: "星座",
    description: "整理星座、星盤與運勢文章，先用白話回答搜尋問題，再補充適用情境與限制。",
    seoDescription: "Pantheon 星座文章主頁，整理星座、星盤、感情運勢與人生主題的繁體中文解釋。",
    primaryKeyword: "星座",
    requiredTags: ["星座", "星盤", "運勢"],
  },
  astrology: {
    product: "astro",
    intent: "",
    label: "星座",
    description: "整理星座、星盤與運勢文章，先用白話回答搜尋問題，再補充適用情境與限制。",
    seoDescription: "Pantheon 星座文章主頁，整理星座、星盤、感情運勢與人生主題的繁體中文解釋。",
    primaryKeyword: "星座",
    requiredTags: ["星座", "星盤", "運勢"],
  },
  love: {
    product: "tarot",
    intent: "love",
    label: "感情",
    description: "整理感情、關係互動與相處模式文章，先回答問題，再連到人格、塔羅與命盤脈絡。",
    seoDescription: "Pantheon 感情文章主頁，整理感情塔羅、人格相處與關係問題的繁體中文內容。",
    primaryKeyword: "感情塔羅",
    requiredTags: ["感情", "關係", "相處模式"],
  },
  bazi: {
    product: "fortune",
    intent: "",
    label: "八字",
    description: "整理八字、命盤與出生年月日時相關概念，保留公開文章與個人判讀的邊界。",
    seoDescription: "Pantheon 八字文章主頁，整理八字是什麼、命盤怎麼看與常見命理概念。",
    primaryKeyword: "八字是什麼",
    requiredTags: ["八字", "命盤", "出生年月日時"],
  },
  career: {
    product: "fortune",
    intent: "career",
    label: "事業",
    description: "整理事業、工作節奏與職涯選擇相關文章，聚焦可理解、可延伸的公開知識。",
    seoDescription: "Pantheon 事業文章主頁，整理事業運勢、工作模式與職涯選擇的繁體中文內容。",
    primaryKeyword: "事業運勢",
    requiredTags: ["事業", "工作", "職涯"],
  },
  interpersonal: {
    product: "personality",
    intent: "interpersonal",
    label: "人際",
    description: "整理人際關係、互動界線與溝通模式文章，先釐清情境，再連到人格、命盤與塔羅脈絡。",
    seoDescription: "Pantheon 人際文章主頁，整理人際關係、互動界線、溝通模式與自我理解內容。",
    primaryKeyword: "人際關係",
    requiredTags: ["人際", "關係界線", "溝通模式"],
  },
  life: {
    product: "fortune",
    intent: "life",
    label: "人生方向",
    description: "整理人生方向、自我理解與選擇節奏相關文章，協助讀者先釐清問題。",
    seoDescription: "Pantheon 人生方向文章主頁，整理自我理解、選擇節奏與人生主題內容。",
    primaryKeyword: "人生方向",
    requiredTags: ["人生方向", "自我理解", "選擇"],
  },
  "life-direction": {
    product: "fortune",
    intent: "life",
    label: "人生方向",
    description: "整理人生方向、自我理解與選擇節奏相關文章，協助讀者先釐清問題。",
    seoDescription: "Pantheon 人生方向文章主頁，整理自我理解、選擇節奏與人生主題內容。",
    primaryKeyword: "人生方向",
    requiredTags: ["人生方向", "自我理解", "選擇"],
  },
  mbti: {
    product: "personality",
    intent: "",
    label: "人格",
    description: "整理 MBTI、16 型人格與 Pantheon 64 分支人格文章，說明能看什麼與不能代表什麼。",
    seoDescription: "Pantheon 人格文章主頁，整理 MBTI 是什麼、16 型人格與 64 分支人格解析。",
    primaryKeyword: "MBTI 人格",
    requiredTags: ["MBTI", "16 型人格", "64 分支人格"],
  },
  relation: {
    product: "tarot",
    intent: "love",
    label: "感情",
    description: "整理感情、關係互動與相處模式文章，先回答問題，再連到人格、塔羅與命盤脈絡。",
    seoDescription: "Pantheon 感情文章主頁，整理感情塔羅、人格相處與關係問題的繁體中文內容。",
    primaryKeyword: "感情塔羅",
    requiredTags: ["感情", "關係", "相處模式"],
  },
  tarot: {
    product: "tarot",
    intent: "",
    label: "塔羅",
    description: "整理塔羅牌義、正逆位與提問方式，建立可搜尋、可內鏈的牌義內容庫。",
    seoDescription: "Pantheon 塔羅文章主頁，整理塔羅牌意思、正位逆位與感情工作牌義。",
    primaryKeyword: "塔羅牌意思",
    requiredTags: ["塔羅", "塔羅牌意思", "正位逆位"],
  },
  wealth: {
    product: "fortune",
    intent: "wealth",
    label: "財富",
    description: "整理財富、資源節奏與金錢觀相關文章，不提供投資建議或財務承諾。",
    seoDescription: "Pantheon 財富文章主頁，整理財富運勢、資源節奏與金錢觀內容。",
    primaryKeyword: "財富運勢",
    requiredTags: ["財富", "資源", "金錢觀"],
  },
  ziwei: {
    product: "fortune",
    intent: "",
    label: "紫微",
    description: "整理紫微斗數、十二宮、主星與命盤概念，建立命理公開知識。",
    seoDescription: "Pantheon 紫微文章主頁，整理紫微斗數是什麼、命宮、夫妻宮與十四主星。",
    primaryKeyword: "紫微斗數是什麼",
    requiredTags: ["紫微斗數", "命盤", "十二宮"],
  },
};

export const ARTICLE_REGISTRY = [
  {
    id: "MBTI-BASE-01",
    section: "mbti",
    slug: "mbti-meaning",
    primaryKeyword: "MBTI 是什麼",
    secondaryKeywords: ["16 型人格", "MBTI 測驗", "MBTI 人格"],
    title: "MBTI 是什麼？16 型人格、測驗與自我理解怎麼看",
    description: "MBTI 是人格偏好工具，適合整理自我理解、互動模式與工作偏好；它不能取代心理診斷，也不能直接判定感情或人生結果。",
    answer: "MBTI 是描述人格偏好的工具，可整理互動與決策傾向，但不能取代診斷。",
    tags: ["人格測驗", "自我理解"],
    faq: [
      {
        question: "MBTI 是什麼意思？",
        answer: "MBTI 是一套人格偏好分類，常用 E/I、S/N、T/F、J/P 四組傾向組合成 16 型。",
      },
      {
        question: "MBTI 可以看感情嗎？",
        answer: "可以幫你理解相處模式，但不應用來判定兩個人合不合。",
      },
      {
        question: "想看自己的 MBTI 狀況要從哪裡開始？",
        answer: "可以先用人格文章整理偏好，再把描述放回實際關係、工作和人際情境。",
      },
    ],
  },
  {
    id: "MBTI-BASE-02",
    section: "mbti",
    slug: "16-personalities",
    primaryKeyword: "16 型人格",
    secondaryKeywords: ["MBTI 是什麼", "MBTI 人格", "人格特質"],
    title: "16 型人格完整整理：特質、感情、工作與人際怎麼看",
    description: "16 型人格把 MBTI 四組偏好組合成不同類型，適合用來理解特質、感情、工作與人際；同一型仍會因情境和經驗而不同。",
    answer: "16 型人格能整理偏好差異，但不是結論，同一型仍會因情境不同。",
    tags: ["人格類型", "人際", "工作"],
  },
  {
    id: "MBTI-BASE-03",
    section: "mbti",
    slug: "mbti-test",
    primaryKeyword: "MBTI 測驗",
    secondaryKeywords: ["免費 MBTI 測驗", "16 型人格測驗", "人格測驗"],
    title: "MBTI 測驗前先知道：能看什麼、不能代表什麼",
    description: "MBTI 測驗可以輔助自我理解，整理偏好與互動模式；但結果會受狀態、題目理解和情境影響，不應當作診斷。",
    answer: "MBTI 測驗可整理人格偏好，但不能代表診斷或人生結果。",
    tags: ["人格測驗", "16 型人格", "自我理解"],
  },
  {
    id: "MBTI-BASE-04",
    section: "mbti",
    slug: "mbti-accuracy",
    primaryKeyword: "MBTI 準嗎",
    secondaryKeywords: ["MBTI 準確度", "MBTI 不準", "MBTI 科學嗎"],
    title: "MBTI 準嗎？準確度、限制與自我理解怎麼看",
    description: "MBTI 會讓人覺得準，常是因為它描述偏好模式；但偏好不等於固定人格，也不等於心理診斷，結果仍要放回情境理解。",
    answer: "MBTI 可作為理解偏好的語言，但不適合當成絕對人格判定。",
    tags: ["人格測驗", "準確度", "公開文章邊界"],
  },
  {
    id: "MBTI-TYPE-INTJ",
    section: "mbti",
    slug: "intj-meaning",
    primaryKeyword: "INTJ 是什麼",
    secondaryKeywords: ["INTJ 人格", "INTJ 特質", "INTJ 感情", "INTJ 工作"],
    title: "INTJ 是什麼？感情、事業、人際與長期規劃怎麼看",
    description: "INTJ 常被描述為重視策略、結構與長期目標的人格類型；可用來理解感情、事業和人際偏好，但不能概括一個人的全部樣貌。",
    answer: "INTJ 常偏向長期規劃與系統思考，但仍要回到個人情境判斷。",
    tags: ["INTJ", "16 型人格", "事業", "人生方向"],
  },
  {
    id: "MBTI-TYPE-INFP",
    section: "mbti",
    slug: "infp-meaning",
    primaryKeyword: "INFP 是什麼",
    secondaryKeywords: ["INFP 人格", "INFP 特質", "INFP 感情", "INFP 工作"],
    title: "INFP 是什麼？感情、事業、人際與內在價值怎麼看",
    description: "INFP 常被描述為重視價值感、情緒細節與內在一致的人格類型；適合理解感情和人生方向偏好，但不能被簡化成脆弱。",
    answer: "INFP 重視內在價值與真實感，可理解選擇偏好，但不能替你下結論。",
    tags: ["INFP", "16 型人格", "感情", "人生方向"],
  },
  {
    id: "MBTI-TYPE-INFJ",
    section: "mbti",
    slug: "infj-meaning",
    primaryKeyword: "INFJ 是什麼",
    secondaryKeywords: ["INFJ 人格", "INFJ 特質", "INFJ 感情", "INFJ 稀有"],
    title: "INFJ 是什麼？關係、理想、人際與人生方向怎麼看",
    description: "INFJ 常被描述為重視洞察、理想與深層關係的人格類型；可整理關係和人生方向偏好，但稀有不代表優越。",
    answer: "INFJ 可理解關係中的洞察與理想感，但仍要回到實際互動。",
    tags: ["INFJ", "16 型人格", "感情", "人際"],
  },
  {
    id: "MBTI-TYPE-ENFP",
    section: "mbti",
    slug: "enfp-meaning",
    primaryKeyword: "ENFP 是什麼",
    secondaryKeywords: ["ENFP 人格", "ENFP 特質", "ENFP 感情", "ENFP 工作"],
    title: "ENFP 是什麼？熱情、關係、人際與人生方向怎麼看",
    description: "ENFP 常被描述為重視可能性、連結與探索的人格類型；可用來整理人際和人生方向，但熱情不等於缺乏方向。",
    answer: "ENFP 擅長看見可能性與建立連結，但不能只用類型判定結果。",
    tags: ["ENFP", "16 型人格", "人際", "人生方向"],
  },
  {
    id: "TAROT-BASE-01",
    section: "tarot",
    slug: "tarot-card-meanings",
    primaryKeyword: "塔羅牌意思",
    secondaryKeywords: ["塔羅牌牌義", "78 張塔羅牌", "塔羅牌正位逆位"],
    title: "塔羅牌意思總覽：78 張牌、正位逆位與情境怎麼看",
    description: "塔羅牌意思適合先理解單牌象徵、正逆位語氣與常見情境；但不能取代牌陣、問題問法和個人狀態的整合判讀。",
    answer: "塔羅牌意思能幫你理解牌面提醒；正位和逆位提供不同語氣，但單張牌不能直接決定感情、工作或人生結果。",
    tags: ["塔羅", "塔羅牌意思", "正位逆位"],
  },
  {
    id: "TAROT-BASE-02",
    section: "tarot",
    slug: "upright-reversed",
    primaryKeyword: "塔羅牌正位逆位",
    secondaryKeywords: ["正位逆位意思", "塔羅逆位", "塔羅正位"],
    title: "塔羅牌正位逆位是什麼？好壞、阻塞與提醒怎麼看",
    description: "塔羅牌正位逆位不是絕對好壞，而是提醒能量表現、阻塞、過度或需要調整的方向；仍要搭配問題和牌陣位置理解。",
    answer: "正位逆位不是好壞二分；正位通常代表能量較順，逆位可能代表阻塞、過度或需要回頭檢查的地方。",
    tags: ["塔羅", "正位逆位", "牌義"],
  },
  {
    id: "TAROT-M00",
    section: "tarot",
    slug: "fool-card-meaning",
    primaryKeyword: "愚者牌意思",
    secondaryKeywords: ["塔羅牌意思", "愚者牌正位", "愚者牌逆位"],
    title: "愚者牌意思：正位、逆位、感情與工作情境怎麼看",
    description: "愚者牌常指向新的開始、探索與未知，也提醒讀者分辨自由、衝動與準備程度；單張牌不能直接決定感情或工作結果。",
    answer: "愚者牌通常代表新的開始與未知旅程；正位偏向開放與探索，逆位則需要留意衝動、逃避或準備不足。",
    tags: ["大阿爾克那", "牌義", "感情塔羅", "工作塔羅"],
  },
  {
    id: "TAROT-M01",
    section: "tarot",
    slug: "magician-card-meaning",
    primaryKeyword: "魔術師牌意思",
    secondaryKeywords: ["魔術師正位", "魔術師逆位", "魔術師感情", "魔術師工作"],
    title: "魔術師牌意思：正位、逆位、感情與事業情境怎麼看",
    description: "魔術師牌常指向資源、行動與創造力，也提醒分辨準備完成、真誠行動、操控、空談或過度自信等不同情境。",
    answer: "魔術師牌通常代表把資源轉成行動；正位偏向啟動與掌握，逆位則要留意空談、操控或準備不足。",
    tags: ["大阿爾克那", "牌義", "事業", "人生方向"],
  },
  {
    id: "TAROT-M06",
    section: "tarot",
    slug: "lovers-card-meaning",
    primaryKeyword: "戀人牌意思",
    secondaryKeywords: ["戀人正位", "戀人逆位", "戀人牌感情", "戀人牌復合"],
    title: "戀人牌意思：正位、逆位、感情與選擇怎麼看",
    description: "戀人牌常和關係、選擇與價值一致有關，但不能直接承諾復合、告白成功或關係結果。",
    answer: "戀人牌通常代表關係中的選擇、吸引與價值對齊；在感情問題裡要看牌陣位置和提問方式，不能單牌定論。",
    tags: ["大阿爾克那", "牌義", "感情塔羅"],
  },
  {
    id: "TAROT-M13",
    section: "tarot",
    slug: "death-card-meaning",
    primaryKeyword: "死神牌意思",
    secondaryKeywords: ["死神正位", "死神逆位", "死神牌感情", "死神牌工作"],
    title: "死神牌意思：正位、逆位、結束與轉變怎麼看",
    description: "死神牌常代表結束、轉化與舊模式退場，不應被寫成恐嚇式預言或災難承諾。",
    answer: "死神牌多半指向轉變和舊模式退場；它不等於壞事，也不代表某件事會照劇本發生。",
    tags: ["大阿爾克那", "牌義", "轉變", "人生方向"],
  },
  {
    id: "TAROT-M16",
    section: "tarot",
    slug: "tower-card-meaning",
    primaryKeyword: "高塔牌意思",
    secondaryKeywords: ["高塔正位", "高塔逆位", "高塔牌感情", "高塔牌工作"],
    title: "高塔牌意思：正位、逆位、關係與工作變動怎麼看",
    description: "高塔牌常指向結構鬆動、突發變化或真相浮現，但不應被用來恐嚇讀者或承諾災難。",
    answer: "高塔牌提醒既有結構可能需要被看見或調整；它可以是變動訊號，但不是災難承諾。",
    tags: ["大阿爾克那", "牌義", "事業", "人生方向"],
  },
  {
    id: "TAROT-M21",
    section: "tarot",
    slug: "world-card-meaning",
    primaryKeyword: "世界牌意思",
    secondaryKeywords: ["世界正位", "世界逆位", "世界牌感情", "世界牌工作"],
    title: "世界牌意思：正位、逆位、完成與下一階段怎麼看",
    description: "世界牌常指向完成、整合與進入下一階段，也提醒讀者分辨收尾、停滯與新的循環。",
    answer: "世界牌通常代表一個階段的完成或整合；逆位時可能提醒尚未收尾，而不是直接否定結果。",
    tags: ["大阿爾克那", "牌義", "人生方向"],
  },
  {
    id: "CHART-BASE-01",
    section: "fortune",
    slug: "birth-chart-meaning",
    primaryKeyword: "命盤是什麼",
    secondaryKeywords: ["個人命盤", "八字命盤", "紫微命盤", "星盤"],
    title: "命盤是什麼？八字、紫微斗數和星盤差在哪",
    description: "命盤是把出生資料轉成不同命理系統的分析語言，適合理解傾向與節奏，不適合當成固定命運。",
    answer: "命盤是命理系統用來整理出生資料的圖表或結構；八字、紫微斗數和星盤各有語言，不能混成同一套結論。",
    tags: ["命盤", "八字", "紫微斗數", "星盤"],
  },
  {
    id: "CHART-BASE-02",
    section: "bazi",
    slug: "bazi-meaning",
    primaryKeyword: "八字是什麼",
    secondaryKeywords: ["命盤是什麼", "出生年月日時", "八字命盤"],
    title: "八字是什麼？出生年月日時怎麼看人生節奏",
    description: "八字用出生年月日時組成命盤語言，適合理解節奏與傾向，不應被當成單一命運答案。",
    answer: "八字是把出生年月日時轉成干支組合的命理系統，常用來討論節奏、傾向與關係，不代表固定命運。",
    tags: ["命盤", "干支", "人生節奏"],
  },
  {
    id: "CHART-ZIWEI-01",
    section: "ziwei",
    slug: "ziwei-doushu-meaning",
    primaryKeyword: "紫微斗數是什麼",
    secondaryKeywords: ["紫微斗數命盤", "紫微命盤", "十二宮", "十四主星"],
    title: "紫微斗數是什麼？命盤十二宮和主星怎麼看",
    description: "紫微斗數用十二宮、主星與流年等語言整理人生主題，公開文章只能說明概念，不能替個人下命書結論。",
    answer: "紫微斗數是以命盤十二宮與星曜配置理解人生主題的命理系統；單一宮位或主星不能代表完整人生答案。",
    tags: ["紫微斗數", "命盤", "十二宮", "十四主星"],
  },
  {
    id: "CHART-ZIWEI-02",
    section: "ziwei",
    slug: "ming-gong-meaning",
    primaryKeyword: "命宮是什麼",
    secondaryKeywords: ["紫微命宮", "命宮代表什麼", "命宮主星"],
    title: "命宮是什麼？它在紫微斗數裡代表什麼",
    description: "命宮是紫微斗數的重要觀察點，常用來理解自我感與人生方向，但不能單獨決定一個人的命運。",
    answer: "命宮可以幫你理解自我傾向和人生主題，但仍需要搭配其他宮位、主星與問題脈絡一起看。",
    tags: ["紫微斗數", "命宮", "人生方向"],
  },
  {
    id: "CHART-ZIWEI-03",
    section: "ziwei",
    slug: "spouse-palace-meaning",
    primaryKeyword: "夫妻宮是什麼",
    secondaryKeywords: ["紫微夫妻宮", "夫妻宮感情", "夫妻宮代表什麼"],
    title: "夫妻宮是什麼？感情關係可以怎麼看",
    description: "夫妻宮可以幫你觀察感情互動與關係模式，但不能承諾婚姻、復合或特定對象結果。",
    answer: "夫妻宮常被用來看關係互動和伴侶模式，但感情問題仍需要回到實際關係、選擇與相處脈絡。",
    tags: ["紫微斗數", "夫妻宮", "感情"],
  },
  {
    id: "CHART-ZIWEI-04",
    section: "ziwei",
    slug: "wealth-palace-meaning",
    primaryKeyword: "財帛宮是什麼",
    secondaryKeywords: ["紫微財帛宮", "財帛宮財運", "財帛宮代表什麼"],
    title: "財帛宮是什麼？財富和資源節奏可以怎麼看",
    description: "財帛宮可用來理解資源、金錢觀與財富節奏，但公開文章不提供投資建議，也不承諾財運。",
    answer: "財帛宮常被用來看資源與金錢傾向；它不是投資建議，也不能承諾某個人會賺錢。",
    tags: ["紫微斗數", "財帛宮", "財富"],
  },
  {
    id: "ASTRO-BASE-01",
    section: "astro",
    slug: "birth-chart-astrology",
    primaryKeyword: "星盤是什麼",
    secondaryKeywords: ["個人星盤", "星盤查詢", "星座命盤", "占星命盤"],
    title: "星盤是什麼？太陽、月亮、上升星座怎麼看",
    description: "星盤用出生時間與地點整理行星和星座位置，適合理解不同面向，不應只用單一星座下結論。",
    answer: "星盤是占星用來整理出生時天空配置的圖；太陽、月亮、上升各看不同面向，不能只用一個點代表完整人格。",
    tags: ["星盤", "星座", "上升星座", "月亮星座"],
  },
  {
    id: "ASTRO-BASE-02",
    section: "astro",
    slug: "ascendant-sign-meaning",
    primaryKeyword: "上升星座是什麼",
    secondaryKeywords: ["上升星座查詢", "上升星座代表什麼", "上升星座個性"],
    title: "上升星座是什麼？它和太陽星座差在哪",
    description: "上升星座常被用來理解外在呈現與人際第一印象，但不能單獨代表完整個性或人生方向。",
    answer: "上升星座通常描述外在呈現、面對世界的方式和第一印象；它和太陽星座不同，也不能單獨定義一個人。",
    tags: ["上升星座", "星盤", "人際"],
  },
  {
    id: "ASTRO-BASE-03",
    section: "astro",
    slug: "moon-sign-meaning",
    primaryKeyword: "月亮星座是什麼",
    secondaryKeywords: ["月亮星座查詢", "月亮星座代表什麼", "月亮星座感情"],
    title: "月亮星座是什麼？情緒與安全感怎麼看",
    description: "月亮星座常被用來理解情緒、安全感與親密關係需求，但不能直接判定感情結果。",
    answer: "月亮星座通常和情緒反應、安全感與親密需求有關；它能補充感情理解，但不能替代完整星盤或實際相處。",
    tags: ["月亮星座", "星盤", "感情", "人際"],
  },
  {
    id: "ASTRO-LOVE-01",
    section: "astro",
    slug: "love-forecast",
    primaryKeyword: "星座感情運勢",
    secondaryKeywords: ["星座感情", "感情運勢", "星盤感情"],
    title: "星座感情運勢怎麼看？先分清太陽、月亮與上升",
    description: "星座感情運勢可以輔助關係觀察，但需要分清太陽、月亮、上升與實際相處情境。",
    answer: "星座感情運勢可以先看關係裡的表達、安全感與互動節奏，但不能直接替你判斷某段關係會怎樣。",
    tags: ["星座感情", "感情", "月亮星座"],
  },
  {
    id: "THEME-LOVE-01",
    section: "relation",
    slug: "love-tarot-questions",
    primaryKeyword: "感情塔羅",
    secondaryKeywords: ["感情占卜", "塔羅感情", "復合塔羅", "曖昧塔羅"],
    title: "感情塔羅怎麼問？復合、曖昧、關係卡住怎麼看",
    description: "感情塔羅適合整理關係問題與提問方式，但不應用來控制他人、承諾復合或替對方下定論。",
    answer: "感情塔羅要先把問題問清楚，例如看互動、狀態或下一步，而不是要求牌直接承諾對方想法或關係結果。",
    tags: ["感情塔羅", "感情", "塔羅", "關係"],
  },
  {
    id: "THEME-CAREER-01",
    section: "career",
    slug: "career-fortune",
    primaryKeyword: "事業運勢",
    secondaryKeywords: ["工作運勢", "轉職運勢", "創業運勢", "事業塔羅"],
    title: "事業運勢怎麼看？轉職、創業、工作卡住的整理方式",
    description: "事業運勢文章適合整理工作問題、時機與選擇脈絡，但不能承諾升遷、轉職或創業結果。",
    answer: "事業運勢可以幫你拆解現在卡在方向、時機、人際或資源，但不能替你承諾某個工作選擇會成功。",
    tags: ["事業", "工作", "轉職", "人生方向"],
  },
  {
    id: "THEME-INTERPERSONAL-01",
    section: "interpersonal",
    slug: "relationships-stuck",
    primaryKeyword: "人際關係",
    secondaryKeywords: ["人際關係改善", "人際關係問題", "人際塔羅", "人際溝通"],
    title: "人際關係卡住怎麼辦？人格、塔羅與命盤可以看什麼",
    description: "人際關係文章適合整理互動模式、界線與溝通問題，但不能替他人貼標籤或要求對方改變。",
    answer: "人際關係卡住時，可以先分清是界線、期待、溝通還是角色問題，再決定要用人格、塔羅或命盤補充哪個角度。",
    tags: ["人際關係", "溝通", "人格", "關係界線"],
  },
  {
    id: "THEME-WEALTH-01",
    section: "wealth",
    slug: "wealth-fortune",
    primaryKeyword: "財富運勢",
    secondaryKeywords: ["財運", "金錢運勢", "財富命盤", "財富塔羅"],
    title: "財富運勢怎麼看？金錢焦慮、資源節奏與風險感",
    description: "財富運勢文章可以整理資源節奏與金錢焦慮，但不得提供投資建議、報酬承諾或發財承諾。",
    answer: "財富運勢適合用來理解金錢觀、資源節奏和風險感；它不是投資建議，也不能承諾財富結果。",
    tags: ["財富", "財運", "金錢觀", "風險"],
  },
  {
    id: "THEME-LIFE-01",
    section: "life",
    slug: "life-direction",
    primaryKeyword: "人生方向",
    secondaryKeywords: ["人生迷惘", "人生方向塔羅", "人生方向命盤", "未來方向"],
    title: "人生方向迷惘怎麼辦？塔羅、人格與命盤能幫你整理什麼",
    description: "人生方向文章適合協助讀者拆解迷惘與選擇，不應假裝提供唯一答案或承諾未來。",
    answer: "人生方向迷惘時，重點不是立刻找唯一答案，而是先分清感情、事業、人際、財富或自我節奏哪裡最卡。",
    tags: ["人生方向", "迷惘", "塔羅", "人格", "命盤"],
  },
];

export function listArticleSectionRecords() {
  return Object.entries(ARTICLE_SECTION_REGISTRY).map(([slug, section]) => ({ slug, ...section }));
}

export function listArticleRecords() {
  return ARTICLE_REGISTRY.map((article) => enforceArticlePolicy(article, getArticleSectionRecord(article.section)));
}

export function getArticlePath(article) {
  const record = article?.urlSlug ? article : enforceArticlePolicy(article, getArticleSectionRecord(article?.section));
  return `/articles/${record.articleCategory || record.product}/${record.urlSlug || record.slug}`;
}

export function listTopicRecords() {
  return TOPIC_REGISTRY.map((topic) => ({
    ...topic,
    href: `/topics/${topic.slug}`,
  }));
}

export function getTopicRecord(slug = "") {
  return listTopicRecords().find((topic) => topic.slug === slug) || null;
}

export function getTopicForLabel(label = "") {
  const normalized = String(label || "").trim();
  return listTopicRecords().find((topic) => topic.label === normalized || topic.aliases.includes(normalized)) || null;
}

export function listArticlesForTopic(topicSlug = "") {
  const topic = getTopicRecord(topicSlug);
  if (!topic) return [];
  return listArticleRecords().filter((article) => {
    const values = [
      article.primaryKeyword,
      ...(article.secondaryKeywords || []),
      ...(article.originalTags || []),
      ...(article.tags || []),
    ].filter(Boolean);
    return values.some((value) => topic.label === value || topic.aliases.includes(value));
  });
}

export function listArticleVoiceAudits() {
  return listArticleRecords().map((article) => auditArticleVoice(article));
}

export function auditArticleVoice(article) {
  const text = [
    article.title,
    article.description,
    article.answer,
    ...(article.faq || []).flatMap((item) => [item.question, item.answer]),
  ].filter(Boolean).join(" ");
  const phraseHits = HUMANIZER_POLICY.bannedGenericPhrases.filter((phrase) => text.includes(phrase));
  const issues = [];
  if (phraseHits.length) issues.push(`套板詞：${phraseHits.join("、")}`);
  if ((article.description || "").length < 32) issues.push("description 太短，可能缺少具體限制或情境");
  if ((article.answer || "").length < 38) issues.push("answer 太短，AEO 摘要可能不夠可引用");
  if (!/不|不能|不應|不是|不代表|不可以/.test(text)) issues.push("缺少公開文章邊界");
  return {
    articleId: article.id || `${article.product}/${article.slug}`,
    serial: article.serial,
    title: article.title,
    status: issues.length ? "needs_review" : "pass",
    issues,
  };
}

export function buildArticleGraph() {
  const nodeMap = new Map();
  const links = [];
  const addNode = (node) => {
    if (!nodeMap.has(node.id)) nodeMap.set(node.id, node);
  };
  const addLink = (source, target, kind) => {
    links.push({ source, target, kind });
  };

  listArticleSectionRecords().forEach((section) => {
    const sectionId = `section:${section.slug}`;
    addNode({
      id: sectionId,
      kind: "section",
      label: section.label,
      keyword: section.primaryKeyword,
    });
    section.requiredTags.forEach((tag) => {
      const tagId = `tag:${tag}`;
      addNode({ id: tagId, kind: "tag", label: tag });
      addLink(sectionId, tagId, "requires_tag");
    });
  });

  listArticleRecords().forEach((article) => {
    const articleId = `article:${article.product}/${article.slug}`;
    const sectionId = `section:${article.section}`;
    addNode({
      id: articleId,
      kind: "article",
      label: article.title,
      serial: article.serial,
      keyword: article.primaryKeyword,
      url: getArticlePath(article),
    });
    addLink(sectionId, articleId, "contains_article");
    article.tags.forEach((tag) => {
      const tagId = `tag:${tag}`;
      addNode({ id: tagId, kind: "tag", label: tag });
      addLink(articleId, tagId, "has_tag");
    });
  });

  return {
    nodes: [...nodeMap.values()],
    links,
  };
}

export function getArticleSectionRecord(section = "") {
  return ARTICLE_SECTION_REGISTRY[section] || null;
}

export function getLifeIntentRecord(intent = "") {
  return LIFE_INTENT_REGISTRY[intent] || null;
}

export function getProductThemeRecord(productTheme = "fortune") {
  return PRODUCT_THEME_REGISTRY[productTheme] || PRODUCT_THEME_REGISTRY.fortune;
}

export function getArticleRecord(product = "", slug = "") {
  const record = ARTICLE_REGISTRY.find((article) => {
    const managed = enforceArticlePolicy(article, getArticleSectionRecord(article.section));
    const routeMatches = managed.product === product || managed.articleCategory === product || managed.section === product;
    const slugMatches = managed.slug === slug || managed.urlSlug === slug;
    return routeMatches && slugMatches;
  });
  return record ? enforceArticlePolicy(record, getArticleSectionRecord(record.section)) : null;
}

export function enforceArticlePolicy(article, section = null) {
  const product = article?.product || section?.product || "fortune";
  const productTheme = article?.productTheme || product;
  const intent = article?.intent || section?.intent || "";
  const keywords = uniqueList([
    article?.primaryKeyword,
    ...(article?.secondaryKeywords || []),
    section?.primaryKeyword,
  ]);
  const tags = uniqueList([
    ...GLOBAL_ARTICLE_POLICY.requiredTags,
    ...GLOBAL_ARTICLE_POLICY.requiredKeywordTags,
    ...(section?.requiredTags || []),
    ...(article?.tags || []),
    ...keywords,
  ]);
  return {
    ...article,
    serial: article?.serial || ARTICLE_SERIAL_REGISTRY[article?.id] || "",
    articleCategory: getArticleCategory(article?.serial || ARTICLE_SERIAL_REGISTRY[article?.id] || "", product),
    urlSlug: article?.urlSlug || buildArticleUrlSlug(article?.serial || ARTICLE_SERIAL_REGISTRY[article?.id] || ""),
    sectionDescription: section?.description || "",
    sectionSeoDescription: section?.seoDescription || section?.description || "",
    product,
    productTheme,
    intent,
    keywords,
    originalTags: article?.tags || [],
    tags,
  };
}

function buildArticleUrlSlug(serial) {
  return serial || "";
}

function getArticleCategory(serial, fallbackProduct) {
  const match = String(serial || "").match(/^(.+)-\d{4}$/);
  return match ? match[1] : fallbackProduct;
}

export function fallbackArticleSectionLabel(section = "") {
  return getArticleSectionRecord(section)?.label || humanizeSlug(section) || "文章";
}

function resolveArticleProduct(article) {
  return article?.product || getArticleSectionRecord(article?.section)?.product || "fortune";
}

function uniqueList(items) {
  return [...new Set(items.filter(Boolean))];
}

function humanizeSlug(value = "") {
  return decodeURIComponent(value)
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}
