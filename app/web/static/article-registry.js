export const GLOBAL_ARTICLE_POLICY = {
  requiredTags: ["Pantheon", "繁體中文", "公開文章", "非個人化解讀"],
  requiredKeywordTags: ["SEO", "AEO", "GEO"],
  publicContentBoundary: "公開文章只講通用知識，不給個人化結論，不承諾結果。",
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
  articlePattern: "/articles/{product}/{slug}",
  productHubPattern: "/articles/{product}",
  intentHubPattern: "/articles/intents/{intent}",
  products: ["fortune", "personality", "tarot", "astro"],
};

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
    description: "整理命盤、八字、紫微與人生主題文章，先建立公開知識入口，再導向個人化解讀。",
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
  bazi: {
    product: "fortune",
    intent: "",
    label: "八字",
    description: "整理八字、命盤與出生年月日時相關概念，保留公開文章與個人化解讀的邊界。",
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
    description: "整理紫微斗數、十二宮、主星與命盤概念，建立命理公開知識入口。",
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
    title: "MBTI 是什麼？16 型人格怎麼看、適合拿來做什麼",
    description: "MBTI 是人格偏好工具，適合看自我理解、互動模式與工作偏好，不適合當成心理診斷或命運結論。",
    answer: "MBTI 是一套描述人格偏好的工具，可以幫你理解做決策、接收資訊與互動時的傾向，但不能取代心理診斷或個人化判斷。",
    tags: ["人格測驗", "自我理解"],
    faq: [
      {
        question: "MBTI 是什麼意思？",
        answer: "MBTI 是一套人格偏好分類，常用 E/I、S/N、T/F、J/P 四組傾向組合成 16 型。",
      },
      {
        question: "MBTI 可以看感情嗎？",
        answer: "可以作為理解相處模式的入口，但不應用來判定兩個人一定合或不合。",
      },
    ],
  },
  {
    id: "MBTI-BASE-02",
    section: "mbti",
    slug: "16-personalities",
    primaryKeyword: "16 型人格",
    secondaryKeywords: ["MBTI 是什麼", "MBTI 人格", "人格特質"],
    title: "16 型人格完整整理：每一型的特質、感情、工作與人際",
    description: "16 型人格把 MBTI 四組偏好組合成不同類型，適合作為理解特質、感情、工作與人際的入口。",
    answer: "16 型人格能快速整理常見偏好差異，但它只是入口；同一型裡仍然會因情境、壓力與個人經驗而不同。",
    tags: ["人格類型", "人際", "工作"],
  },
  {
    id: "MBTI-BASE-03",
    section: "mbti",
    slug: "mbti-test",
    primaryKeyword: "MBTI 測驗",
    secondaryKeywords: ["免費 MBTI 測驗", "16 型人格測驗", "人格測驗"],
    title: "MBTI 測驗前先知道：它能幫你看什麼、不能代表什麼",
    description: "MBTI 測驗適合當作自我理解入口，但測驗結果會受情境、狀態與題目理解影響，不應當作診斷。",
    answer: "MBTI 測驗可以幫你整理人格偏好，但它不能代表心理診斷，也不能保證你的感情、工作或人生結果。",
    tags: ["人格測驗", "16 型人格", "自我理解"],
  },
  {
    id: "MBTI-BASE-04",
    section: "mbti",
    slug: "mbti-accuracy",
    primaryKeyword: "MBTI 準嗎",
    secondaryKeywords: ["MBTI 準確度", "MBTI 不準", "MBTI 科學嗎"],
    title: "MBTI 準嗎？為什麼有人覺得很像、有人覺得不準",
    description: "MBTI 會讓人覺得準，通常是因為它描述了偏好模式；但偏好不等於固定人格，也不等於科學診斷。",
    answer: "MBTI 可以作為理解偏好的語言，但不應被當成絕對準確的人格判定；結果變動通常和情境、壓力與自我理解有關。",
    tags: ["人格測驗", "準確度", "公開文章邊界"],
  },
  {
    id: "MBTI-TYPE-INTJ",
    section: "mbti",
    slug: "intj-meaning",
    primaryKeyword: "INTJ 是什麼",
    secondaryKeywords: ["INTJ 人格", "INTJ 特質", "INTJ 感情", "INTJ 工作"],
    title: "INTJ 是什麼？感情、事業、人際裡常見的思考模式",
    description: "INTJ 常被描述為重視策略、結構與長期目標的人格類型，但不能只用四個字母判定一個人的全部樣貌。",
    answer: "INTJ 通常偏向長期規劃與系統思考，在感情、事業與人際裡會重視效率和一致性，但仍要回到個人情境判斷。",
    tags: ["INTJ", "16 型人格", "事業", "人生方向"],
  },
  {
    id: "MBTI-TYPE-INFP",
    section: "mbti",
    slug: "infp-meaning",
    primaryKeyword: "INFP 是什麼",
    secondaryKeywords: ["INFP 人格", "INFP 特質", "INFP 感情", "INFP 工作"],
    title: "INFP 是什麼？感情、事業、人際裡常見的內在模式",
    description: "INFP 常被描述為重視價值感、情緒細節與內在一致的人格類型，但不應被簡化成脆弱或不切實際。",
    answer: "INFP 通常重視內在價值與關係真實感，適合用來理解感情和人生方向裡的選擇偏好，但不能替你下結論。",
    tags: ["INFP", "16 型人格", "感情", "人生方向"],
  },
  {
    id: "MBTI-TYPE-INFJ",
    section: "mbti",
    slug: "infj-meaning",
    primaryKeyword: "INFJ 是什麼",
    secondaryKeywords: ["INFJ 人格", "INFJ 特質", "INFJ 感情", "INFJ 稀有"],
    title: "INFJ 是什麼？關係、理想與人生方向怎麼看",
    description: "INFJ 常被描述為重視洞察、理想與深層關係的人格類型，但稀有不代表優越，也不代表命運固定。",
    answer: "INFJ 適合用來理解關係裡的洞察與理想感，但感情、人際和人生方向仍需要放回實際互動脈絡。",
    tags: ["INFJ", "16 型人格", "感情", "人際"],
  },
  {
    id: "MBTI-TYPE-ENFP",
    section: "mbti",
    slug: "enfp-meaning",
    primaryKeyword: "ENFP 是什麼",
    secondaryKeywords: ["ENFP 人格", "ENFP 特質", "ENFP 感情", "ENFP 工作"],
    title: "ENFP 是什麼？熱情、關係與人生方向怎麼看",
    description: "ENFP 常被描述為重視可能性、連結與探索的人格類型，但熱情不等於三分鐘熱度，也不代表缺乏方向。",
    answer: "ENFP 通常擅長看見可能性與建立連結，適合用來整理人際和人生方向，但不能只用類型判定能力或關係結果。",
    tags: ["ENFP", "16 型人格", "人際", "人生方向"],
  },
  {
    id: "TAROT-BASE-01",
    section: "tarot",
    slug: "tarot-card-meanings",
    primaryKeyword: "塔羅牌意思",
    secondaryKeywords: ["塔羅牌牌義", "78 張塔羅牌", "塔羅牌正位逆位"],
    title: "塔羅牌意思總覽：78 張牌正位、逆位怎麼看",
    description: "塔羅牌意思適合先理解單牌象徵與正逆位語氣，但不能直接取代牌陣、問題與個人狀態的整合。",
    answer: "塔羅牌意思是理解牌面象徵的入口；正位和逆位提供不同提醒，但單張牌不能直接決定感情、工作或人生結果。",
    tags: ["塔羅", "塔羅牌意思", "正位逆位"],
  },
  {
    id: "TAROT-BASE-02",
    section: "tarot",
    slug: "upright-reversed",
    primaryKeyword: "塔羅牌正位逆位",
    secondaryKeywords: ["正位逆位意思", "塔羅逆位", "塔羅正位"],
    title: "塔羅牌正位逆位是什麼？一定代表好壞嗎",
    description: "塔羅牌正位逆位不是絕對好壞，而是提醒能量表現、阻塞、過度或需要調整的方向。",
    answer: "正位逆位不是好壞二分；正位通常代表能量較順，逆位可能代表阻塞、過度或需要回頭檢查的地方。",
    tags: ["塔羅", "正位逆位", "牌義"],
  },
  {
    id: "TAROT-M00",
    section: "tarot",
    slug: "fool-card-meaning",
    primaryKeyword: "愚者牌意思",
    secondaryKeywords: ["塔羅牌意思", "愚者牌正位", "愚者牌逆位"],
    title: "愚者牌意思：正位、逆位、感情與工作怎麼看",
    description: "愚者牌常指向開始、探索與未知，也提醒讀者分辨自由、衝動與準備程度。",
    answer: "愚者牌通常代表新的開始與未知旅程；正位偏向開放與探索，逆位則需要留意衝動、逃避或準備不足。",
    tags: ["大阿爾克那", "牌義", "感情塔羅", "工作塔羅"],
  },
  {
    id: "TAROT-M01",
    section: "tarot",
    slug: "magician-card-meaning",
    primaryKeyword: "魔術師牌意思",
    secondaryKeywords: ["魔術師正位", "魔術師逆位", "魔術師感情", "魔術師工作"],
    title: "魔術師牌意思：正位、逆位、感情與事業怎麼看",
    description: "魔術師牌常指向資源、行動與創造力，也提醒分辨準備完成與操控、空談或過度自信。",
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
    description: "戀人牌常和關係、選擇與價值一致有關，但不能直接保證復合、告白成功或關係結果。",
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
    description: "死神牌常代表結束、轉化與舊模式退場，不應被寫成恐嚇式預言或災難保證。",
    answer: "死神牌多半指向轉變和結束舊模式；它不等於壞事，也不代表某件事一定會發生。",
    tags: ["大阿爾克那", "牌義", "轉變", "人生方向"],
  },
  {
    id: "TAROT-M16",
    section: "tarot",
    slug: "tower-card-meaning",
    primaryKeyword: "高塔牌意思",
    secondaryKeywords: ["高塔正位", "高塔逆位", "高塔牌感情", "高塔牌工作"],
    title: "高塔牌意思：正位、逆位、關係與工作變動怎麼看",
    description: "高塔牌常指向結構鬆動、突發變化或真相浮現，但不應被用來恐嚇讀者或保證災難。",
    answer: "高塔牌提醒既有結構可能需要被看見或調整；它可以是變動訊號，但不是災難保證。",
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
    answer: "命宮可以作為理解自我傾向和人生主題的入口，但仍需要搭配其他宮位、主星與問題脈絡一起看。",
    tags: ["紫微斗數", "命宮", "人生方向"],
  },
  {
    id: "CHART-ZIWEI-03",
    section: "ziwei",
    slug: "spouse-palace-meaning",
    primaryKeyword: "夫妻宮是什麼",
    secondaryKeywords: ["紫微夫妻宮", "夫妻宮感情", "夫妻宮代表什麼"],
    title: "夫妻宮是什麼？感情關係可以怎麼看",
    description: "夫妻宮可以作為觀察感情互動與關係模式的入口，但不能保證婚姻、復合或特定對象結果。",
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
    description: "財帛宮可用來理解資源、金錢觀與財富節奏，但公開文章不提供投資建議，也不保證財運。",
    answer: "財帛宮常被用來看資源與金錢傾向；它不是投資建議，也不能保證某個人一定會賺錢。",
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
    description: "星座感情運勢適合作為關係觀察入口，但需要分清太陽、月亮、上升與實際相處情境。",
    answer: "星座感情運勢可以先看關係裡的表達、安全感與互動節奏，但不能直接替你判斷某段關係一定會怎樣。",
    tags: ["星座感情", "感情", "月亮星座"],
  },
  {
    id: "THEME-LOVE-01",
    section: "relation",
    slug: "love-tarot-questions",
    primaryKeyword: "感情塔羅",
    secondaryKeywords: ["感情占卜", "塔羅感情", "復合塔羅", "曖昧塔羅"],
    title: "感情塔羅怎麼問？復合、曖昧、關係卡住怎麼看",
    description: "感情塔羅適合整理關係問題與提問方式，但不應用來控制他人、保證復合或替對方下定論。",
    answer: "感情塔羅要先把問題問清楚，例如看互動、狀態或下一步，而不是要求牌直接保證對方想法或關係結果。",
    tags: ["感情塔羅", "感情", "塔羅", "關係"],
  },
  {
    id: "THEME-CAREER-01",
    section: "career",
    slug: "career-fortune",
    primaryKeyword: "事業運勢",
    secondaryKeywords: ["工作運勢", "轉職運勢", "創業運勢", "事業塔羅"],
    title: "事業運勢怎麼看？轉職、創業、工作卡住的整理方式",
    description: "事業運勢文章適合整理工作問題、時機與選擇脈絡，但不能保證升遷、轉職或創業結果。",
    answer: "事業運勢可以幫你拆解現在卡在方向、時機、人際或資源，但不能替你保證某個工作選擇一定成功。",
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
    description: "財富運勢文章可以整理資源節奏與金錢焦慮，但不得提供投資建議、報酬承諾或發財保證。",
    answer: "財富運勢適合用來理解金錢觀、資源節奏和風險感；它不是投資建議，也不能保證財富結果。",
    tags: ["財富", "財運", "金錢觀", "風險"],
  },
  {
    id: "THEME-LIFE-01",
    section: "life",
    slug: "life-direction",
    primaryKeyword: "人生方向",
    secondaryKeywords: ["人生迷惘", "人生方向塔羅", "人生方向命盤", "未來方向"],
    title: "人生方向迷惘怎麼辦？塔羅、人格與命盤能幫你整理什麼",
    description: "人生方向文章適合協助讀者拆解迷惘與選擇，不應假裝提供唯一答案或保證未來。",
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
      keyword: article.primaryKeyword,
      url: `/articles/${article.product}/${article.slug}`,
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
  const record = ARTICLE_REGISTRY.find((article) => resolveArticleProduct(article) === product && article.slug === slug);
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
