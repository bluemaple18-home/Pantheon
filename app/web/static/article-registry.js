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
  "TAROT-M02": "tarot-0009",
  "TAROT-M18": "tarot-0010",
  "TAROT-M14": "tarot-0011",
  "CHART-BASE-01": "fortune-0001",
  "CHART-BASE-02": "fortune-0002",
  "CHART-ZIWEI-01": "fortune-0003",
  "CHART-ZIWEI-02": "fortune-0004",
  "CHART-ZIWEI-03": "fortune-0005",
  "CHART-ZIWEI-04": "fortune-0006",
  "CHART-ZIWEI-05": "fortune-0007",
  "CHART-ZIWEI-06": "fortune-0008",
  "CHART-ZIWEI-07": "fortune-0009",
  "ASTRO-BASE-01": "astrology-0001",
  "ASTRO-BASE-02": "astrology-0002",
  "ASTRO-BASE-03": "astrology-0003",
  "ASTRO-LOVE-01": "astrology-0004",
  "ASTRO-VENUS-01": "astrology-0005",
  "MBTI-TYPE-ENTJ": "personality-0009",
  "MBTI-TYPE-ENTP": "personality-0010",
  "MBTI-TYPE-ISFJ": "personality-0011",
  "THEME-LOVE-01": "love-0001",
  "THEME-LOVE-02": "love-0002",
  "THEME-LOVE-03": "love-0003",
  "THEME-LOVE-04": "love-0004",
  "THEME-CAREER-01": "career-0001",
  "THEME-CAREER-02": "career-0002",
  "THEME-CAREER-03": "career-0003",
  "THEME-CAREER-04": "career-0004",
  "THEME-INTERPERSONAL-01": "interpersonal-0001",
  "THEME-INTERPERSONAL-02": "interpersonal-0002",
  "THEME-WEALTH-01": "wealth-0001",
  "THEME-WEALTH-02": "wealth-0002",
  "THEME-WEALTH-03": "wealth-0003",
  "THEME-LIFE-01": "life-direction-0001",
  "THEME-LIFE-02": "life-direction-0002",
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

export const PUBLIC_TOPIC_MIN_ARTICLES = 10;

export const TOPIC_REGISTRY = [
  { id: "topic-0001", slug: "mbti", label: "MBTI", aliases: ["MBTI 是什麼", "MBTI 人格", "MBTI 測驗", "人格測驗"] },
  { id: "topic-0002", slug: "personality", label: "人格", aliases: ["16 型人格", "16 型人格測驗", "人格類型", "64 分支人格", "INTJ", "INFP", "INFJ", "ENFP"] },
  { id: "topic-0003", slug: "tarot", label: "塔羅", aliases: ["塔羅", "塔羅牌意思", "塔羅牌牌義", "牌義", "大阿爾克那", "阿爾克那"] },
  { id: "topic-0004", slug: "upright", label: "正位", aliases: ["正位", "塔羅正位", "塔羅牌正位"] },
  { id: "topic-0005", slug: "fortune", label: "命盤", aliases: ["命盤", "個人命盤", "八字命盤", "紫微命盤"] },
  { id: "topic-0006", slug: "bazi", label: "八字", aliases: ["八字", "八字是什麼", "生辰八字", "干支"] },
  { id: "topic-0007", slug: "ziwei", label: "紫微", aliases: ["紫微", "紫微斗數", "紫微命盤", "命宮", "夫妻宮", "財帛宮"] },
  { id: "topic-0008", slug: "astrology", label: "星盤", aliases: ["星盤", "星盤是什麼", "個人星盤", "星盤查詢", "星座命盤", "占星命盤", "星座", "上升星座", "月亮星座"] },
  { id: "topic-0009", slug: "love", label: "感情", aliases: ["感情", "感情塔羅", "關係", "相處模式"] },
  { id: "topic-0010", slug: "career", label: "工作", aliases: ["工作", "事業", "職涯", "轉職"] },
  { id: "topic-0011", slug: "interpersonal", label: "人際", aliases: ["人際", "人際關係", "溝通", "關係界線"] },
  { id: "topic-0012", slug: "wealth", label: "財富", aliases: ["財富", "財運", "金錢觀", "資源"] },
  { id: "topic-0013", slug: "life-direction", label: "人生方向", aliases: ["人生方向", "人生迷惘", "自我理解", "選擇"] },
  { id: "topic-0014", slug: "reversed", label: "逆位", aliases: ["逆位", "塔羅逆位", "塔羅牌逆位"] },
  { id: "topic-0015", slug: "fool", label: "愚者", aliases: ["愚者", "愚者牌", "愚者牌意思"] },
  { id: "topic-0016", slug: "magician", label: "魔術師", aliases: ["魔術師", "魔術師牌", "魔術師牌意思"] },
  { id: "topic-0017", slug: "lovers", label: "戀人", aliases: ["戀人", "戀人牌", "戀人牌意思"] },
  { id: "topic-0018", slug: "death", label: "死神", aliases: ["死神", "死神牌", "死神牌意思"] },
  { id: "topic-0019", slug: "tower", label: "高塔", aliases: ["高塔", "高塔牌", "高塔牌意思"] },
  { id: "topic-0020", slug: "world", label: "世界", aliases: ["世界", "世界牌", "世界牌意思"] },
];

const publicTagLabelCache = new Map();
let topicCandidateRecordCache = null;

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
  {
    id: "TAROT-M02",
    section: "tarot",
    slug: "high-priestess-card-meaning",
    primaryKeyword: "女祭司牌意思",
    secondaryKeywords: ["女祭司正位", "女祭司逆位", "女祭司感情", "直覺"],
    title: "女祭司牌意思：正位、逆位與感情直覺怎麼看",
    description: "女祭司牌常出現在看不清、等不到答案或直覺很強的時候；適合整理觀察與不安，但不能把單張牌寫成結果承諾。",
    answer: "女祭司牌多半和直覺、等待、未說出口的事有關，但不能單靠它判斷結果。",
    tags: ["女祭司", "正位", "逆位", "感情", "人生方向"],
    faq: [
      { question: "女祭司牌感情代表對方有秘密嗎？", answer: "未必。它可能代表資訊未明、情緒未說出口，或你需要先觀察，不適合直接下結論。" },
      { question: "女祭司逆位是不是不好？", answer: "不是。逆位比較常提醒混亂、逃避或焦慮干擾，不等於結果會變差。" },
      { question: "女祭司牌可以看人生方向嗎？", answer: "可以作為等待和內在訊號的提醒，但不能替你決定要不要換工作、分手或搬家。" },
    ],
  },
  {
    id: "CHART-ZIWEI-05",
    section: "ziwei",
    slug: "fude-palace-meaning",
    primaryKeyword: "福德宮是什麼",
    secondaryKeywords: ["紫微福德宮", "福德宮代表什麼", "情緒安全感", "內在狀態"],
    title: "福德宮是什麼？情緒安全感與內在狀態怎麼看",
    description: "福德宮常被拿來看內在狀態、壓力消化和精神安全感；它是觀察起點，但不能單獨判斷完整人生。",
    answer: "福德宮常用來看內在安定感、壓力消化方式和精神需求，但單一宮位不能代表完整人生。",
    tags: ["紫微斗數", "福德宮", "人生方向", "人際"],
    faq: [
      { question: "福德宮是看有沒有福氣嗎？", answer: "不建議這樣簡化。福德宮比較適合看內在狀態、精神需求和壓力消化。" },
      { question: "福德宮不好代表我很難快樂嗎？", answer: "不代表。它可能提醒你比較難放鬆，但不能直接判斷人生結果。" },
      { question: "福德宮可以看感情嗎？", answer: "可以補充安全感和情緒需求，但感情還要看互動、夫妻宮和實際關係狀態。" },
    ],
  },
  {
    id: "MBTI-TYPE-ENTJ",
    section: "mbti",
    slug: "entj-meaning",
    primaryKeyword: "ENTJ 是什麼",
    secondaryKeywords: ["ENTJ 人格", "ENTJ 感情", "ENTJ 工作", "ENTJ 特質"],
    title: "ENTJ 是什麼？感情、事業與控制感怎麼看",
    description: "ENTJ 常被說成強勢或有企圖心，但這不等於冷酷；這篇整理 ENTJ 在感情、工作與人際裡的常見困擾與限制。",
    answer: "ENTJ 常重視方向、效率和掌控感，但人格類型只能說明偏好，不能代表一個人的全部。",
    tags: ["ENTJ", "16 型人格", "感情", "事業", "人際"],
    faq: [
      { question: "ENTJ 是什麼人格？", answer: "ENTJ 通常重視方向、效率、決策和組織能力，但這只是偏好描述，不是完整人格。" },
      { question: "ENTJ 在感情裡會很強勢嗎？", answer: "有可能表現得很直接，但不代表不在乎；重點是能不能分清解決問題和理解情緒。" },
      { question: "ENTJ 適合什麼工作？", answer: "常見適合需要策略、管理、推進和決策的工作，但仍要看能力、價值觀和實際環境。" },
    ],
  },
  {
    id: "THEME-LOVE-02",
    section: "love",
    slug: "long-situationship-stuck",
    primaryKeyword: "曖昧很久",
    secondaryKeywords: ["曖昧沒有進展", "曖昧該繼續嗎", "感情塔羅", "關係卡住"],
    title: "曖昧很久沒有進展，該繼續還是停下？",
    description: "曖昧很久沒有進展時，問題未必是喜不喜歡，而是期待、界線和未來方向沒有被說清楚；文章不替讀者做決定。",
    answer: "曖昧卡住時，先分清楚是時機未到、期待不同，還是其中一方不想負責任地說清楚。",
    tags: ["感情", "曖昧", "感情塔羅", "關係", "人格"],
    faq: [
      { question: "曖昧很久沒有進展，是不是代表沒機會？", answer: "未必，但代表目前缺少清楚方向。要看對方是否穩定行動，是否願意談現實安排。" },
      { question: "曖昧可以用塔羅看嗎？", answer: "可以看當下卡點和自己的盲點，但不能承諾對方最後會不會選擇你。" },
      { question: "曖昧該繼續還是停下？", answer: "先看你等的是具體進展，還是只是在等焦慮被安撫。" },
    ],
  },
  {
    id: "THEME-CAREER-02",
    section: "career",
    slug: "hard-work-not-seen",
    primaryKeyword: "工作很努力卻沒被看見",
    secondaryKeywords: ["努力沒回報", "職場被看見", "事業運勢", "工作卡住"],
    title: "工作很努力卻沒被看見，問題可能在哪？",
    description: "工作很努力卻沒被看見時，未必是能力不夠；這篇從成果、溝通、位置和節奏整理卡點，不承諾升職或轉運。",
    answer: "努力沒被看見時，先分清楚是成果不清、溝通不足、位置不對，還是環境本來就不重視你的貢獻。",
    tags: ["事業", "工作", "職場", "人格", "命盤"],
    faq: [
      { question: "工作很努力卻沒被看見，是不是運勢不好？", answer: "未必。先檢查成果是否清楚、主管是否知道、工作是否靠近組織重點。" },
      { question: "我不想邀功，怎麼讓自己被看見？", answer: "可以用事實回報成果、影響和下一步，不需要誇大；讓貢獻可見不等於搶功。" },
      { question: "塔羅或命盤可以看事業卡點嗎？", answer: "可以作為整理工具，但不能承諾升職、加薪或轉職結果。" },
    ],
  },
  {
    id: "TAROT-M18",
    section: "tarot",
    slug: "moon-card-meaning",
    primaryKeyword: "月亮牌意思",
    secondaryKeywords: ["月亮正位", "月亮逆位", "月亮牌感情", "焦慮"],
    title: "月亮牌意思：正位、逆位與感情焦慮怎麼看",
    description: "月亮牌常出現在不安、猜測和看不清真相的時候；適合先整理焦慮來源，不適合急著下結論。",
    answer: "月亮牌常提醒情緒和資訊都不夠清楚，適合先整理焦慮來源，不適合急著下結論。",
    tags: ["月亮牌", "正位", "逆位", "感情", "焦慮"],
    faq: [
      { question: "月亮牌感情代表欺騙嗎？", answer: "不直接代表欺騙。它比較常指向資訊不清、猜測變多，或情緒正在放大不安。" },
      { question: "月亮逆位是不是比較好？", answer: "它可能表示混亂正在散開，但仍需要看具體問題和牌陣位置。" },
      { question: "抽到月亮牌該相信直覺嗎？", answer: "可以重視直覺，但要回到事實檢查；焦慮和直覺有時很像，需要分開整理。" },
    ],
  },
  {
    id: "CHART-ZIWEI-06",
    section: "ziwei",
    slug: "tianzhai-palace-meaning",
    primaryKeyword: "田宅宮是什麼",
    secondaryKeywords: ["紫微田宅宮", "田宅宮代表什麼", "家庭安全感", "居住關係"],
    title: "田宅宮是什麼？家庭、安全感與居住關係怎麼看",
    description: "田宅宮不只看房子，也常被用來理解家庭、居住安全感和資源安定；這不是單宮命運判定。",
    answer: "田宅宮常用來看居住、家庭資源和安全感來源，但不能只靠單一宮位判斷財富或人生。",
    tags: ["紫微斗數", "田宅宮", "家庭", "安全感", "財富"],
    faq: [
      { question: "田宅宮是看房產嗎？", answer: "它可以涉及房產和居住，但也常用來看家庭、安全感和資源穩定。" },
      { question: "田宅宮不好代表不能買房嗎？", answer: "不代表。買房需要看現實財務、風險和需求，不能只靠單一宮位判斷。" },
      { question: "田宅宮和感情有關嗎？", answer: "有時有關，尤其牽涉同居、家庭介入、空間需求和共同生活安排。" },
    ],
  },
  {
    id: "MBTI-TYPE-ENTP",
    section: "mbti",
    slug: "entp-meaning",
    primaryKeyword: "ENTP 是什麼",
    secondaryKeywords: ["ENTP 人格", "ENTP 感情", "ENTP 工作", "ENTP 特質"],
    title: "ENTP 是什麼？感情、工作與三分鐘熱度怎麼看",
    description: "ENTP 常被說成愛辯論或三分鐘熱度，但背後可能是好奇、需要刺激和不喜歡被固定；類型不是逃避承諾的理由。",
    answer: "ENTP 常重視可能性、辯證和新鮮感，但人格類型只能說明偏好，不能當成逃避承諾的理由。",
    tags: ["ENTP", "16 型人格", "感情", "工作", "人際"],
    faq: [
      { question: "ENTP 是什麼人格？", answer: "ENTP 通常重視新想法、辯證、變化和可能性，但這只是偏好，不是完整人格。" },
      { question: "ENTP 真的很花心嗎？", answer: "不能這樣直接判斷。ENTP 可能需要新鮮感，但是否負責任要看實際行為。" },
      { question: "ENTP 為什麼容易三分鐘熱度？", answer: "有時是刺激需求高，有時是缺少落地結構；重點是分清楚探索和逃避。" },
    ],
  },
  {
    id: "THEME-LOVE-03",
    section: "love",
    slug: "before-getting-back-together",
    primaryKeyword: "復合前要想清楚什麼",
    secondaryKeywords: ["復合", "感情復合", "復合塔羅", "關係模式"],
    title: "復合前要想清楚什麼？先看三個關係問題",
    description: "復合前最重要的不是對方會不會回來，而是分手原因、改變是否真實，以及你想回去的是人還是不甘心。",
    answer: "復合前先看分手原因、改變是否具體、你想回去的是關係本身，還是不甘心和習慣。",
    tags: ["感情", "復合", "關係模式", "感情塔羅", "人格"],
    faq: [
      { question: "復合前最該確認什麼？", answer: "先確認分手原因是否清楚，以及雙方是否有具體改變，不要只看還有沒有感情。" },
      { question: "塔羅可以看復合嗎？", answer: "可以整理關係卡點和自己的盲點，但不能承諾對方會回來。" },
      { question: "復合後會不會重蹈覆轍？", answer: "要看原本問題是否有新的處理方式。如果互動模式沒變，就容易回到舊循環。" },
    ],
  },
  {
    id: "THEME-CAREER-03",
    section: "career",
    slug: "should-i-change-job",
    primaryKeyword: "現在適合轉職嗎",
    secondaryKeywords: ["轉職", "轉職運勢", "工作卡住", "事業方向"],
    title: "現在適合轉職嗎？先分清逃離、成長與方向",
    description: "想知道現在適合轉職嗎，先不要只看運勢；這篇從逃離、成長、環境和方向整理判斷角度，不承諾轉職結果。",
    answer: "轉職前先看問題來自環境、成長停滯、價值不合，還是短期疲憊；不要只用運勢決定。",
    tags: ["事業", "轉職", "工作", "人生方向", "命盤", "塔羅"],
    faq: [
      { question: "現在適合轉職嗎？", answer: "先看你是想逃離、想成長，還是想轉向。不同原因需要不同準備。" },
      { question: "轉職可以問塔羅嗎？", answer: "可以整理短期卡點和選項，但不能承諾面試、錄取或薪資結果。" },
      { question: "事業運勢可以決定轉職時間嗎？", answer: "不建議只靠運勢。現實條件、市場、能力和財務緩衝都要一起看。" },
    ],
  },
  {
    id: "THEME-INTERPERSONAL-02",
    section: "interpersonal",
    slug: "friendship-changing",
    primaryKeyword: "朋友關係變淡",
    secondaryKeywords: ["友情變淡", "人際關係", "關係界線", "社交疲憊"],
    title: "朋友關係變淡，是自然變化還是需要處理？",
    description: "朋友關係變淡時，先不要急著怪自己或怪對方；這篇從生活階段、期待落差、界線和社交能量整理判斷角度。",
    answer: "友情變淡可能是生活階段改變，也可能是期待、界線或情緒負擔累積；先分清楚是哪一種。",
    tags: ["人際", "朋友", "友情", "關係界線", "人格"],
    faq: [
      { question: "朋友關係變淡要主動聯絡嗎？", answer: "如果你還在意，可以先用輕量方式聯絡，不必一開始就談很重的問題。" },
      { question: "友情變淡是不是代表對方不在乎？", answer: "未必。可能是生活階段、互動頻率和表達方式改變，也可能是真的有距離。" },
      { question: "人際關係可以用塔羅看嗎？", answer: "可以整理互動盲點和自己的感受，但不能替對方下結論。" },
    ],
  },
  {
    id: "THEME-WEALTH-02",
    section: "wealth",
    slug: "money-anxiety",
    primaryKeyword: "金錢焦慮",
    secondaryKeywords: ["財富運勢", "存不住錢", "財富安全感", "金錢觀"],
    title: "金錢焦慮從哪裡來？先分清收入、支出與安全感",
    description: "金錢焦慮未必只是收入問題，也可能和安全感、風險感、家庭經驗或資源節奏有關；本文不提供投資建議。",
    answer: "金錢焦慮要分成收入壓力、支出失控、風險感太高，以及把安全感全放在錢上。",
    tags: ["財富", "金錢焦慮", "財富運勢", "安全感", "命盤"],
    faq: [
      { question: "金錢焦慮是財運不好嗎？", answer: "未必。它可能和現金流、風險感、家庭經驗或安全感有關，不適合只用財運解釋。" },
      { question: "命盤可以看財富嗎？", answer: "可以作為資源節奏和傾向參考，但不能提供投資判斷或收入承諾。" },
      { question: "一直存不住錢怎麼辦？", answer: "先看花錢前的壓力情境，再看收入、固定支出和衝動消費來源。" },
    ],
  },
  {
    id: "THEME-LIFE-02",
    section: "life",
    slug: "move-or-wait",
    primaryKeyword: "該動還是該等",
    secondaryKeywords: ["時機問題", "人生方向", "塔羅人生方向", "選擇卡住"],
    title: "該動還是該等？時機問題先看三個條件",
    description: "卡在該動還是該等時，先不要急著找答案；這篇從資訊、資源和承擔能力整理時機問題，不替讀者做人生決定。",
    answer: "時機問題先看資訊是否足夠、資源是否能承擔、以及你是在準備還是在拖延。",
    tags: ["人生方向", "選擇", "時機", "塔羅", "命盤"],
    faq: [
      { question: "該動還是該等要怎麼判斷？", answer: "先看資訊是否足夠、資源是否能承擔，以及等待期間是否有具體準備。" },
      { question: "塔羅可以看時機嗎？", answer: "可以整理當下卡點和風險，但不能替你決定重大人生選擇。" },
      { question: "一直猶豫是不是代表不適合？", answer: "未必。猶豫可能來自資訊不足、害怕風險，也可能是方向真的不合。" },
    ],
  },
  {
    id: "TAROT-M14",
    section: "tarot",
    slug: "temperance-card-meaning",
    primaryKeyword: "節制牌意思",
    secondaryKeywords: ["節制正位", "節制逆位", "節制牌感情", "關係修復"],
    title: "節制牌意思：正位、逆位與關係修復怎麼看",
    description: "節制牌常出現在需要調整節奏、修復關係或重新取得平衡的時候；它講的是協調，不是單方面忍耐。",
    answer: "節制牌常提醒節奏、溝通和修復，但不能單靠一張牌判斷關係會不會變好。",
    tags: ["節制", "正位", "逆位", "感情", "關係修復"],
    faq: [
      { question: "節制牌感情代表會和好嗎？", answer: "它可能代表有修復空間，但不能承諾和好。要看雙方是否都有具體調整。" },
      { question: "節制逆位是不是關係失衡？", answer: "常見是節奏失衡、過度退讓或溝通卡住，但仍要看完整問題。" },
      { question: "節制牌是要我繼續忍嗎？", answer: "不是。節制是協調和平衡，不是單方面忍耐。" },
    ],
  },
  {
    id: "CHART-ZIWEI-07",
    section: "ziwei",
    slug: "career-palace-meaning",
    primaryKeyword: "事業宮是什麼",
    secondaryKeywords: ["紫微事業宮", "官祿宮", "工作方向", "職涯"],
    title: "事業宮是什麼？工作方向與被看見怎麼看",
    description: "事業宮常被用來看工作方式、職涯舞台與被看見的位置；它能提供觀察角度，但不能單獨決定職業。",
    answer: "事業宮常用來看工作方式、職涯舞台和被看見的位置，但不能單靠一個宮位決定職業。",
    tags: ["紫微斗數", "事業宮", "工作", "職涯"],
    faq: [
      { question: "事業宮和官祿宮一樣嗎？", answer: "很多語境會把事業宮和官祿宮連在一起談，重點是工作角色、職涯舞台和外在成就。" },
      { question: "事業宮可以看適合職業嗎？", answer: "可以提供方向參考，但不能單靠它決定職業，還要看能力、資源和市場。" },
      { question: "轉職前可以看事業宮嗎？", answer: "可以作為自我理解，但轉職仍要看職缺、薪資、履歷和風險承擔。" },
    ],
  },
  {
    id: "MBTI-TYPE-ISFJ",
    section: "mbti",
    slug: "isfj-meaning",
    primaryKeyword: "ISFJ 是什麼",
    secondaryKeywords: ["ISFJ 人格", "ISFJ 感情", "ISFJ 工作", "責任感"],
    title: "ISFJ 是什麼？感情、工作與責任感怎麼看",
    description: "ISFJ 常被形容為照顧型人格，但這不代表只能付出；文章整理 ISFJ 在感情、工作與人際裡的責任感和界線。",
    answer: "ISFJ 常重視照顧、穩定和責任，但人格類型不能把一個人固定成只會付出的角色。",
    tags: ["ISFJ", "16 型人格", "感情", "工作", "人際"],
    faq: [
      { question: "ISFJ 是什麼人格？", answer: "ISFJ 通常重視穩定、責任、照顧和細節，但這只是偏好描述。" },
      { question: "ISFJ 在感情裡容易委屈嗎？", answer: "有可能，尤其當付出沒有被看見，或很難表達自己的需要時。" },
      { question: "ISFJ 要怎麼練習界線？", answer: "先從小範圍拒絕開始，把「我不方便」說清楚，不必每次都解釋到對方滿意。" },
    ],
  },
  {
    id: "ASTRO-VENUS-01",
    section: "astro",
    slug: "venus-sign-meaning",
    primaryKeyword: "金星星座是什麼",
    secondaryKeywords: ["金星星座", "金星星座感情", "喜歡方式", "感情需求"],
    title: "金星星座是什麼？感情需求與喜歡方式怎麼看",
    description: "金星星座常被用來看喜歡方式、審美和感情需求，但不能單獨判斷一段關係；星盤語言要回到生活互動。",
    answer: "金星星座常用來看喜歡方式、審美和親密需求，但不能單獨決定感情結果。",
    tags: ["星盤", "金星星座", "感情", "喜歡方式", "星座"],
    faq: [
      { question: "金星星座是什麼？", answer: "金星星座常用來看喜歡方式、審美、吸引力和感情需求，但只是星盤的一部分。" },
      { question: "金星星座可以看感情嗎？", answer: "可以補充親密需求和表達方式，但不能單獨判斷感情結果。" },
      { question: "金星和月亮星座差在哪？", answer: "金星偏向喜歡和吸引，月亮偏向情緒、安全感和親密需求。" },
    ],
  },
  {
    id: "THEME-LOVE-04",
    section: "love",
    slug: "relationship-insecurity",
    primaryKeyword: "感情不安全感",
    secondaryKeywords: ["感情焦慮", "安全感", "關係不安", "月亮星座感情"],
    title: "感情不安全感從哪裡來？先分清對方和自己",
    description: "感情不安全感可能來自對方行為，也可能來自過去經驗和內在焦慮；文章整理判斷角度，不替對方下結論。",
    answer: "感情不安全感要分成對方行為、關係狀態、過去經驗和自己的情緒放大，不能全部混在一起。",
    tags: ["感情", "不安全感", "關係", "月亮星座", "人格"],
    faq: [
      { question: "感情不安全感是不是我的問題？", answer: "不宜直接這樣判斷。要看對方行為、關係規則、過去經驗和你的情緒反應。" },
      { question: "月亮星座可以看安全感嗎？", answer: "可以作為情緒需求參考，但不能單獨判斷關係。" },
      { question: "什麼時候該設界線？", answer: "當對方長期忽冷忽熱、逃避溝通或讓你承擔所有焦慮時，就需要重新談界線。" },
    ],
  },
  {
    id: "THEME-CAREER-04",
    section: "career",
    slug: "before-starting-business",
    primaryKeyword: "創業前要想清楚什麼",
    secondaryKeywords: ["適合創業嗎", "創業運勢", "事業方向", "財富風險"],
    title: "創業前要想清楚什麼？先看資源、風險與動機",
    description: "創業前不要只問適不適合或運勢好不好；這篇從動機、資源、風險和承擔能力整理判斷角度，不承諾創業結果。",
    answer: "創業前先看動機、資源、風險承擔和現實驗證，不要只靠運勢或一時不想上班來決定。",
    tags: ["事業", "創業", "財富", "人生方向", "命盤"],
    faq: [
      { question: "我適合創業嗎？", answer: "先看動機、能力、資源和風險承擔，不要只用性格或運勢判斷。" },
      { question: "創業可以看命盤嗎？", answer: "可以作為節奏和資源模式參考，但不能承諾商業結果。" },
      { question: "不想上班是不是就該創業？", answer: "未必。不想上班可能是環境問題，也可能是疲憊，不等於創業條件成熟。" },
    ],
  },
  {
    id: "THEME-WEALTH-03",
    section: "wealth",
    slug: "hard-to-save-money",
    primaryKeyword: "存不住錢",
    secondaryKeywords: ["金錢焦慮", "花錢模式", "財富安全感", "財富運勢"],
    title: "存不住錢怎麼辦？先看花錢模式與安全感",
    description: "存不住錢不只是不夠自律，也可能和壓力、補償心理、收入結構和安全感有關；本文不提供投資建議。",
    answer: "存不住錢要分清楚收入不足、支出結構、情緒消費和安全感需求，不要只怪自己。",
    tags: ["財富", "存錢", "金錢焦慮", "花錢模式", "人格"],
    faq: [
      { question: "存不住錢是不是我不自律？", answer: "不宜只這樣看。可能是收入結構、支出設計、壓力和安全感共同作用。" },
      { question: "財富運勢可以看存錢嗎？", answer: "可以作為資源節奏參考，但不能取代記帳、預算和現實財務安排。" },
      { question: "存錢要從哪裡開始？", answer: "先分固定支出、變動支出和非必要支出，再找出最常被情緒觸發的部分。" },
    ],
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

function uniqueValues(values = []) {
  return [...new Set(values.filter(Boolean))];
}

export function expandPublicTagLabels(value = "") {
  const raw = String(value || "").trim();
  if (!raw) return [];
  const labels = [];
  const push = (label) => {
    if (label && !labels.includes(label)) labels.push(label);
  };
  if (/MBTI/i.test(raw)) push("MBTI");
  if (/16\s*型|人格|INTJ|INFP|INFJ|ENFP|64\s*分支/.test(raw)) push("人格");
  if (/愚者/.test(raw)) push("愚者");
  if (/魔術師/.test(raw)) push("魔術師");
  if (/戀人/.test(raw)) push("戀人");
  if (/死神/.test(raw)) push("死神");
  if (/高塔/.test(raw)) push("高塔");
  if (/世界/.test(raw)) push("世界");
  if (/正位/.test(raw)) push("正位");
  if (/逆位/.test(raw)) push("逆位");
  if (/塔羅|牌義|阿爾克那|牌意思/.test(raw)) push("塔羅");
  if (/命盤|紫微|八字|命宮|夫妻宮|財帛宮/.test(raw)) push("命盤");
  if (/紫微/.test(raw)) push("紫微");
  if (/八字|生辰八字|干支/.test(raw)) push("八字");
  if (/星盤|星座|上升|月亮|占星/.test(raw)) push("星盤");
  if (/感情|關係|復合|曖昧|相處/.test(raw)) push("感情");
  if (/工作|事業|職涯|轉職|創業/.test(raw)) push("工作");
  if (/人際|溝通|界線/.test(raw)) push("人際");
  if (/財富|財運|金錢|資源/.test(raw)) push("財富");
  if (/人生方向|人生迷惘|自我理解|選擇/.test(raw)) push("人生方向");
  return labels.length ? labels : [raw];
}

export function normalizePublicTagLabel(value = "") {
  return expandPublicTagLabels(value)[0] || "";
}

export function listPublicTagLabelsForArticle(article = {}) {
  const cacheKey = article.id || article.serial || article.slug || JSON.stringify([
    article.primaryKeyword,
    article.secondaryKeywords,
    article.originalTags,
    article.tags,
  ]);
  if (publicTagLabelCache.has(cacheKey)) return publicTagLabelCache.get(cacheKey);
  const source = [
    article.product === "tarot" ? "塔羅" : "",
    article.product === "fortune" ? "命盤" : "",
    article.product === "personality" ? "人格" : "",
    article.product === "astro" ? "星盤" : "",
    article.primaryKeyword,
    ...(article.secondaryKeywords || []),
    ...(article.originalTags || []),
    ...(article.tags || []),
  ];
  const labels = uniqueValues(source.flatMap(expandPublicTagLabels))
    .filter((label) => label && !GLOBAL_ARTICLE_POLICY.requiredTags.includes(label))
    .filter((label) => !GLOBAL_ARTICLE_POLICY.requiredKeywordTags.includes(label));
  publicTagLabelCache.set(cacheKey, labels);
  return labels;
}

function findTopicCandidate(slug = "") {
  return TOPIC_REGISTRY.find((topic) => topic.slug === slug) || null;
}

function articleMatchesTopic(article, topic) {
  const labels = listPublicTagLabelsForArticle(article);
  return labels.includes(topic.label) || labels.some((label) => topic.aliases.includes(label));
}

function enrichTopicRecord(topic) {
  const articles = listArticleRecords().filter((article) => articleMatchesTopic(article, topic));
  const isGenerated = articles.length >= PUBLIC_TOPIC_MIN_ARTICLES;
  return {
    ...topic,
    articleCount: articles.length,
    minArticles: PUBLIC_TOPIC_MIN_ARTICLES,
    isGenerated,
    href: isGenerated ? `/topics/${topic.slug}` : "",
  };
}

export function listTopicCandidateRecords() {
  if (!topicCandidateRecordCache) {
    topicCandidateRecordCache = TOPIC_REGISTRY.map(enrichTopicRecord);
  }
  return topicCandidateRecordCache;
}

export function listTopicRecords() {
  return listTopicCandidateRecords().filter((topic) => topic.isGenerated);
}

export function getTopicRecord(slug = "") {
  return listTopicRecords().find((topic) => topic.slug === slug) || null;
}

export function getTopicForLabel(label = "") {
  const normalized = String(label || "").trim();
  return listTopicRecords().find((topic) => topic.label === normalized || topic.aliases.includes(normalized)) || null;
}

export function listArticlesForTopic(topicSlug = "") {
  const topic = findTopicCandidate(topicSlug);
  if (!topic) return [];
  return listArticleRecords().filter((article) => articleMatchesTopic(article, topic));
}

export function listTagManagementRecords() {
  return listTopicCandidateRecords()
    .map((topic) => ({
      ...topic,
      articles: listArticlesForTopic(topic.slug).map((article) => ({
        title: article.title,
        path: getArticlePath(article),
        serial: article.serial,
      })),
    }))
    .sort((a, b) => b.articleCount - a.articleCount || a.label.localeCompare(b.label));
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
