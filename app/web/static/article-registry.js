import { EXPANSION_50_ARTICLE_RECORDS } from "./article-expansion-50.js?v=article-expansion-20260716-1";
import { EXPANSION_50C_MBTI_ARTICLE_RECORDS } from "./article-expansion-50c-mbti.js?v=article-expansion-50c-20260716-1";
import { EXPANSION_50C_ASTRO_ARTICLE_RECORDS } from "./article-expansion-50c-astro.js?v=article-expansion-50c-20260716-1";
import { EXPANSION_50C_FORTUNE_ARTICLE_RECORDS } from "./article-expansion-50c-fortune.js?v=article-expansion-50c-20260716-1";
import { EXPANSION_50D_MBTI_ARTICLE_RECORDS } from "./article-expansion-50d-mbti.js?v=article-expansion-50d-20260716-1";
import { EXPANSION_50D_ASTRO_ARTICLE_RECORDS } from "./article-expansion-50d-astro.js?v=article-expansion-50d-20260716-1";
import { EXPANSION_50D_FORTUNE_ARTICLE_RECORDS } from "./article-expansion-50d-fortune.js?v=article-expansion-50d-20260716-1";

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
    "通常不是想背牌義",
    "不能替任何人下結論",
    "正位不等於好消息",
  ],
  requiredChecks: [
    "前 80 字直接回答主關鍵字",
    "摘要要說清楚適用情境與限制",
    "FAQ 不寫正確廢話，要回答真問題",
    "不得加入未提供的數據、經歷或承諾",
    "每篇至少保留一個不能代表什麼的邊界",
    "每篇至少有兩個專屬生活場景與兩個可觀察動詞",
    "同批文章固定完整句型不得超過三次",
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
  "TAROT-M03": "tarot-0012",
  "TAROT-M04": "tarot-0013",
  "TAROT-M05": "tarot-0014",
  "TAROT-M07": "tarot-0015",
  "TAROT-M08": "tarot-0016",
  "TAROT-M09": "tarot-0017",
  "TAROT-M10": "tarot-0018",
  "TAROT-M11": "tarot-0019",
  "TAROT-M12": "tarot-0020",
  "TAROT-M15": "tarot-0021",
  "TAROT-M17": "tarot-0022",
  "TAROT-M19": "tarot-0023",
  "TAROT-M20": "tarot-0024",
  "TAROT-PENTACLES-KING": "tarot-0025",
  "TAROT-SWORDS-07": "tarot-0026",
  "TAROT-WANDS-03": "tarot-0027",
  "TAROT-WANDS-05": "tarot-0028",
  "TAROT-PENTACLES-05": "tarot-0029",
  "TAROT-SWORDS-09": "tarot-0030",
  "TAROT-SWORDS-02": "tarot-0031",
  "TAROT-CUPS-02": "tarot-0032",
  "MBTI-TYPE-INTP": "personality-0012",
  "MBTI-TYPE-ISTJ": "personality-0013",
  "MBTI-TYPE-ISTP": "personality-0014",
  "MBTI-TYPE-ISFP": "personality-0015",
  "MBTI-TYPE-ENFJ": "personality-0016",
  "MBTI-TYPE-ESTJ": "personality-0017",
  "MBTI-TYPE-ESFJ": "personality-0018",
  "MBTI-TYPE-ESTP": "personality-0019",
  "MBTI-TYPE-ESFP": "personality-0020",

  "TAROT-WANDS-01": "tarot-0033",
  "TAROT-WANDS-02": "tarot-0034",
  "TAROT-WANDS-04": "tarot-0035",
  "TAROT-WANDS-06": "tarot-0036",
  "TAROT-WANDS-07": "tarot-0037",
  "TAROT-WANDS-08": "tarot-0038",
  "TAROT-WANDS-09": "tarot-0039",
  "TAROT-WANDS-10": "tarot-0040",
  "TAROT-WANDS-PAGE": "tarot-0041",
  "TAROT-WANDS-KNIGHT": "tarot-0042",
  "TAROT-WANDS-QUEEN": "tarot-0043",
  "TAROT-WANDS-KING": "tarot-0044",
  "TAROT-CUPS-01": "tarot-0045",
  "TAROT-CUPS-03": "tarot-0046",
  "TAROT-CUPS-04": "tarot-0047",
  "TAROT-CUPS-05": "tarot-0048",
  "TAROT-CUPS-06": "tarot-0049",
  "TAROT-CUPS-07": "tarot-0050",
  "TAROT-CUPS-08": "tarot-0051",
  "TAROT-CUPS-09": "tarot-0052",
  "TAROT-CUPS-10": "tarot-0053",
  "TAROT-CUPS-PAGE": "tarot-0054",
  "TAROT-CUPS-KNIGHT": "tarot-0055",
  "TAROT-CUPS-QUEEN": "tarot-0056",
  "TAROT-CUPS-KING": "tarot-0057",
  "TAROT-SWORDS-01": "tarot-0058",
  "TAROT-SWORDS-03": "tarot-0059",
  "TAROT-SWORDS-04": "tarot-0060",
  "TAROT-SWORDS-05": "tarot-0061",
  "TAROT-SWORDS-06": "tarot-0062",
  "TAROT-SWORDS-08": "tarot-0063",
  "TAROT-SWORDS-10": "tarot-0064",
  "TAROT-SWORDS-PAGE": "tarot-0065",
  "TAROT-SWORDS-KNIGHT": "tarot-0066",
  "TAROT-SWORDS-QUEEN": "tarot-0067",
  "TAROT-SWORDS-KING": "tarot-0068",
  "TAROT-PENTACLES-01": "tarot-0069",
  "TAROT-PENTACLES-02": "tarot-0070",
  "TAROT-PENTACLES-03": "tarot-0071",
  "TAROT-PENTACLES-04": "tarot-0072",
  "TAROT-PENTACLES-06": "tarot-0073",
  "TAROT-PENTACLES-07": "tarot-0074",
  "TAROT-PENTACLES-08": "tarot-0075",
  "TAROT-PENTACLES-09": "tarot-0076",
  "TAROT-PENTACLES-10": "tarot-0077",
  "TAROT-PENTACLES-PAGE": "tarot-0078",
  "TAROT-PENTACLES-KNIGHT": "tarot-0079",
  "TAROT-PENTACLES-QUEEN": "tarot-0080",
};

export const PRODUCT_THEME_REGISTRY = {
  fortune: {
    label: "命盤",
    glyph: "命",
    description: "整理八字、紫微與命盤概念，說明觀察層次與資料限制。",
  },
  personality: {
    label: "人格",
    glyph: "人",
    description: "整理 MBTI 與人格偏好，說明互動模式與不能代表什麼。",
  },
  tarot: {
    label: "塔羅",
    glyph: "XVII",
    description: "整理塔羅牌義、正逆位與情境提醒，保留提問限制。",
  },
  astro: {
    label: "星座",
    glyph: "星",
    description: "整理星盤、太陽、月亮與上升星座，避免單點定論。",
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

export const TAG_TAXONOMY_POLICY = {
  publicTopicMinArticles: PUBLIC_TOPIC_MIN_ARTICLES,
  defaultIndexPolicy: "blocked",
  indexPolicies: {
    min_articles: "達到公開文章數門檻才可進 sitemap、prerender 與 index。",
    blocked: "只能當內部或候選標籤，不可產生公開 topic URL。",
  },
  internalOnlyTags: [
    ...GLOBAL_ARTICLE_POLICY.requiredTags,
    ...GLOBAL_ARTICLE_POLICY.requiredKeywordTags,
  ],
};

export const TAG_TAXONOMY_REGISTRY = [
  { topicSlug: "mbti", canonicalLabel: "MBTI", indexPolicy: "min_articles", matchPatterns: ["MBTI"] },
  { topicSlug: "personality", canonicalLabel: "人格", indexPolicy: "min_articles", matchPatterns: ["16\\s*型", "人格", "INTJ", "INFP", "INFJ", "ENFP", "64\\s*分支"] },
  { topicSlug: "tarot", canonicalLabel: "塔羅", indexPolicy: "min_articles", matchPatterns: ["塔羅", "牌義", "阿爾克那", "牌意思"] },
  { topicSlug: "upright", canonicalLabel: "正位", indexPolicy: "min_articles", matchPatterns: ["正位"] },
  { topicSlug: "fortune", canonicalLabel: "命盤", indexPolicy: "min_articles", matchPatterns: ["命盤", "紫微", "八字", "命宮", "夫妻宮", "財帛宮"] },
  { topicSlug: "bazi", canonicalLabel: "八字", indexPolicy: "min_articles", matchPatterns: ["八字", "生辰八字", "干支"] },
  { topicSlug: "ziwei", canonicalLabel: "紫微", indexPolicy: "min_articles", matchPatterns: ["紫微"] },
  { topicSlug: "astrology", canonicalLabel: "星盤", indexPolicy: "min_articles", matchPatterns: ["星盤", "星座", "上升", "月亮", "占星"] },
  { topicSlug: "love", canonicalLabel: "感情", indexPolicy: "min_articles", matchPatterns: ["感情", "關係", "復合", "曖昧", "相處"] },
  { topicSlug: "career", canonicalLabel: "工作", indexPolicy: "min_articles", matchPatterns: ["工作", "事業", "職涯", "轉職", "創業"] },
  { topicSlug: "interpersonal", canonicalLabel: "人際", indexPolicy: "min_articles", matchPatterns: ["人際", "溝通", "界線"] },
  { topicSlug: "wealth", canonicalLabel: "財富", indexPolicy: "min_articles", matchPatterns: ["財富", "財運", "金錢", "資源"] },
  { topicSlug: "life-direction", canonicalLabel: "人生方向", indexPolicy: "min_articles", matchPatterns: ["人生方向", "人生迷惘", "自我理解", "選擇"] },
  { topicSlug: "reversed", canonicalLabel: "逆位", indexPolicy: "min_articles", matchPatterns: ["逆位"] },
  { topicSlug: "fool", canonicalLabel: "愚者", indexPolicy: "min_articles", matchPatterns: ["愚者"] },
  { topicSlug: "magician", canonicalLabel: "魔術師", indexPolicy: "min_articles", matchPatterns: ["魔術師"] },
  { topicSlug: "lovers", canonicalLabel: "戀人", indexPolicy: "min_articles", matchPatterns: ["戀人"] },
  { topicSlug: "death", canonicalLabel: "死神", indexPolicy: "min_articles", matchPatterns: ["死神"] },
  { topicSlug: "tower", canonicalLabel: "高塔", indexPolicy: "min_articles", matchPatterns: ["高塔"] },
  { topicSlug: "world", canonicalLabel: "世界", indexPolicy: "min_articles", matchPatterns: ["世界"] },
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
    description: "整理 MBTI 與 16 型人格文章，說明互動偏好、適用情境與不能代表什麼。",
    seoDescription: "Pantheon 人格文章主頁，整理 MBTI 是什麼、16 型人格與人格偏好解析。",
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
    description: "整理財富、資源節奏與金錢觀相關文章，不提供投資判斷或財務承諾。",
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

import { AGY_PROTOTYPE_V1_01_ARTICLE_RECORDS } from "./article-expansion-agy-prototype-v1-01.js?v=agy-prototype-v1-01";

import { AGY_MATRIX_BACKLOG_V1_01_ARTICLE_RECORDS } from "./article-expansion-agy-matrix-backlog-v1-01.js?v=agy-matrix-backlog-v1-01";

import { AGY_MATRIX_BACKLOG_V1_RETRY_01_ARTICLE_RECORDS } from "./article-expansion-agy-matrix-backlog-v1-retry-01.js?v=agy-matrix-backlog-v1-retry-01";

import { AGY_ASC_BATCH_02_01_ARTICLE_RECORDS } from "./article-expansion-agy-asc-batch-02-01.js?v=agy-asc-batch-02-01";

import { AGY_ASC_BATCH_02_MECHANICAL_REPAIR_01_ARTICLE_RECORDS } from "./article-expansion-agy-asc-batch-02-mechanical-repair-01.js?v=agy-asc-batch-02-mechanical-repair-01";

export const ARTICLE_REGISTRY = [
  {
    id: "MBTI-BASE-01",
    section: "mbti",
    slug: "mbti-meaning",
    primaryKeyword: "MBTI 是什麼",
    secondaryKeywords: ["16 型人格", "MBTI 測驗", "MBTI 人格"],
    title: "MBTI 是什麼？16 型人格、測驗與自我理解怎麼看",
    description: "MBTI 是人格偏好工具，適合整理自我理解、互動模式與工作偏好；它不能取代專業評估，也不能直接判定感情或人生結果。",
    answer: "MBTI 是描述人格偏好的工具，可整理互動與決策傾向，但不能取代專業評估。",
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
    description: "MBTI 測驗可以輔助自我理解，整理偏好與互動模式；但結果會受狀態、題目理解和情境影響，不應當作專業評估。",
    answer: "MBTI 測驗可整理人格偏好，但不能代表專業評估或人生結果。",
    tags: ["人格測驗", "16 型人格", "自我理解"],
  },
  {
    id: "MBTI-BASE-04",
    section: "mbti",
    slug: "mbti-accuracy",
    primaryKeyword: "MBTI 準嗎",
    secondaryKeywords: ["MBTI 準確度", "MBTI 不準", "MBTI 科學嗎"],
    title: "MBTI 準嗎？準確度、限制與自我理解怎麼看",
    description: "MBTI 會讓人覺得準，常是因為它描述偏好模式；但偏好不等於固定人格，也不等於專業評估，結果仍要放回情境理解。",
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
    description: "財帛宮可用來理解資源、金錢觀與財富節奏，但不提供投資判斷，也不承諾財運。",
    answer: "財帛宮常被用來看資源與金錢傾向；它不是投資判斷，也不能承諾某個人會賺錢。",
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
    description: "財富運勢文章可以整理資源節奏與金錢焦慮，但不得提供投資判斷、報酬承諾或發財承諾。",
    answer: "財富運勢適合用來理解金錢觀、資源節奏和風險感；它不是投資判斷，也不能承諾財富結果。",
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
    description: "金錢焦慮未必只是收入問題，也可能和安全感、風險感、家庭經驗或資源節奏有關；本文不提供投資判斷。",
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
    description: "金星星座常被用來看喜歡方式、審美和感情需求，但不能單獨判斷一段關係；仍要對照實際互動。",
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
    description: "存不住錢不只是不夠自律，也可能和壓力、補償心理、收入結構和安全感有關；本文不提供投資判斷。",
    answer: "存不住錢要分清楚收入不足、支出結構、情緒消費和安全感需求，不要只怪自己。",
    tags: ["財富", "存錢", "金錢焦慮", "花錢模式", "人格"],
    faq: [
      { question: "存不住錢是不是我不自律？", answer: "不宜只這樣看。可能是收入結構、支出設計、壓力和安全感共同作用。" },
      { question: "財富運勢可以看存錢嗎？", answer: "可以作為資源節奏參考，但不能取代記帳、預算和現實財務安排。" },
      { question: "存錢要從哪裡開始？", answer: "先分固定支出、變動支出和非必要支出，再找出最常被情緒觸發的部分。" },
    ],
  },
  {
    id: "TAROT-M03",
    section: "tarot",
    slug: "empress-card-meaning",
    primaryKeyword: "皇后牌意思",
    secondaryKeywords: ["皇后牌正位", "皇后牌逆位", "皇后牌感情"],
    title: "皇后牌意思：正位、逆位與感情安全感怎麼看",
    description: "皇后牌常和照顧、吸引力、資源與安全感有關；本文整理正位、逆位、感情與工作情境，也說明不能直接代表結果。",
    answer: "皇后牌提醒照顧、資源、吸引力與安全感，但仍不能單獨決定感情或工作結果，也要回到實際情境。",
    tags: ["皇后牌", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "皇后牌感情代表對方喜歡我嗎？", answer: "未必。它比較像提醒關係裡的吸引、照顧和安全感，不替對方下結論。" },
      { question: "皇后牌逆位怎麼看？", answer: "可能是照顧失衡、需求沒被說清楚，或太依賴外界肯定。" },
      { question: "皇后牌工作怎麼看？", answer: "可以看資源、創造力和支持條件，但不能承諾升職或收入。" },
    ],
  },
  {
    id: "TAROT-M04",
    section: "tarot",
    slug: "emperor-card-meaning",
    primaryKeyword: "皇帝牌意思",
    secondaryKeywords: ["皇帝牌正位", "皇帝牌逆位", "皇帝牌感情"],
    title: "皇帝牌意思：正位、逆位與關係控制感怎麼看",
    description: "皇帝牌常和規則、責任、掌控與界線有關；本文整理正位、逆位、感情與工作情境，避免把牌義寫成固定結果。",
    answer: "皇帝牌提醒責任、規則、界線和掌控感，重點是看控制穩定還是過度，也要回到實際情境。",
    tags: ["皇帝牌", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "皇帝牌感情代表控制欲嗎？", answer: "可能有控制感議題，但也可能是責任、承諾或界線需要被談清楚。" },
      { question: "皇帝牌逆位是不是很糟？", answer: "未必。它可能提醒規則太硬、承擔不足，或有人想掌控太多。" },
      { question: "皇帝牌工作代表主管嗎？", answer: "可能指主管、制度或責任結構，但仍要看問題情境。" },
    ],
  },
  {
    id: "TAROT-M05",
    section: "tarot",
    slug: "hierophant-card-meaning",
    primaryKeyword: "教皇牌意思",
    secondaryKeywords: ["教皇牌正位", "教皇牌逆位", "教皇牌感情"],
    title: "教皇牌意思：正位、逆位與承諾壓力怎麼看",
    description: "教皇牌常和承諾、規範、價值觀與關係壓力有關；本文整理正位、逆位、感情與工作情境，也保留限制。",
    answer: "教皇牌提醒承諾、規範和價值觀，重點是看這些規則是否適合當下關係，也要回到實際情境。",
    tags: ["教皇牌", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "教皇牌代表結婚嗎？", answer: "未必。它可能和承諾、傳統或關係規範有關，但不能單獨判斷婚姻結果。" },
      { question: "教皇牌逆位代表不適合嗎？", answer: "可能代表規則不合、價值觀衝突或不想照舊方式走。" },
      { question: "教皇牌工作怎麼看？", answer: "常和制度、資格、師長、組織規範有關。" },
    ],
  },
  {
    id: "TAROT-M07",
    section: "tarot",
    slug: "chariot-card-meaning",
    primaryKeyword: "戰車牌意思",
    secondaryKeywords: ["戰車牌正位", "戰車牌逆位", "戰車牌工作"],
    title: "戰車牌意思：正位、逆位與行動卡住怎麼看",
    description: "戰車牌常和行動、方向、意志與控制節奏有關；本文整理正位、逆位、感情與工作情境，不把它寫成勝利承諾。",
    answer: "戰車牌提醒行動和方向感，重點是你是否掌握局面，而不是只靠意志硬推，也要回到實際情境。",
    tags: ["戰車牌", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "戰車牌代表會成功嗎？", answer: "不代表。它提醒行動力和方向，但成果仍取決於資源、條件和現實執行。" },
      { question: "戰車牌逆位是停下來嗎？", answer: "可能是方向不清、節奏失控或需要重新整理方法。" },
      { question: "戰車牌感情怎麼看？", answer: "要看關係是否被一方硬推，或雙方是否真的往同一方向走。" },
    ],
  },
  {
    id: "TAROT-M08",
    section: "tarot",
    slug: "strength-card-meaning",
    primaryKeyword: "力量牌意思",
    secondaryKeywords: ["力量牌正位", "力量牌逆位", "力量牌感情"],
    title: "力量牌意思：正位、逆位與壓力自控怎麼看",
    description: "力量牌常和耐心、自控、溫柔力量與壓力有關；本文整理感情、工作與逆位情境，也說明不能直接代表結果。",
    answer: "力量牌提醒耐心、自控和溫柔處理壓力，但不是叫你一直忍耐，也要回到實際情境與條件。",
    tags: ["力量牌", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "力量牌感情代表復合嗎？", answer: "不代表。它比較像提醒關係是否需要耐心、修復和界線。" },
      { question: "力量牌逆位是沒力量嗎？", answer: "可能是壓抑太久、情緒失控，或對某件事太用力。" },
      { question: "力量牌工作怎麼看？", answer: "可以看抗壓、協調和長期投入，但不能承諾成果。" },
    ],
  },
  {
    id: "TAROT-M09",
    section: "tarot",
    slug: "hermit-card-meaning",
    primaryKeyword: "隱者牌意思",
    secondaryKeywords: ["隱者牌正位", "隱者牌逆位", "隱者牌感情"],
    title: "隱者牌意思：正位、逆位與需要冷靜怎麼看",
    description: "隱者牌常和冷靜、退一步、內在整理與距離有關；本文整理正位、逆位、感情與工作情境，不把沉默寫成結論。",
    answer: "隱者牌提醒你先拉開距離整理，不代表關係會結束或工作停滯，也要回到實際情境與條件。",
    tags: ["隱者牌", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "隱者牌感情代表分手嗎？", answer: "未必。它可能只是提醒雙方需要冷靜、觀察或暫時拉開距離。" },
      { question: "隱者牌逆位怎麼看？", answer: "可能是逃避、孤立太久，或不願意把想法說清楚。" },
      { question: "隱者牌工作代表離職嗎？", answer: "未必。它也可能代表需要專注、研究或暫時降低外界干擾。" },
    ],
  },
  {
    id: "TAROT-M10",
    section: "tarot",
    slug: "wheel-of-fortune-card-meaning",
    primaryKeyword: "命運之輪牌意思",
    secondaryKeywords: ["命運之輪正位", "命運之輪逆位", "命運之輪感情"],
    title: "命運之輪牌意思：正位、逆位與時機變動怎麼看",
    description: "命運之輪牌常和變動、時機、循環與轉折有關；本文整理感情、工作與逆位情境，也避免把它寫成命運承諾。",
    answer: "命運之輪提醒局勢正在變動，重點是看你能掌握什麼、不能掌握什麼，也要回到實際情境。",
    tags: ["命運之輪牌", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "命運之輪代表好運嗎？", answer: "未必。它代表變動與循環，不承諾結果會變好。" },
      { question: "命運之輪逆位是不是壞運？", answer: "未必。可能是時機未到、重複舊模式，或需要調整做法。" },
      { question: "命運之輪感情怎麼看？", answer: "可以看關係節奏和轉折，但不能承諾復合或分開。" },
    ],
  },
  {
    id: "TAROT-M11",
    section: "tarot",
    slug: "justice-card-meaning",
    primaryKeyword: "正義牌意思",
    secondaryKeywords: ["正義牌正位", "正義牌逆位", "正義牌感情"],
    title: "正義牌意思：正位、逆位與關係公平怎麼看",
    description: "正義牌常和公平、責任、選擇與後果有關；本文整理正位、逆位、感情與工作情境，不提供法律或結果判斷。",
    answer: "正義牌提醒公平、責任和後果，重點是把事實、承擔和選擇分清楚，也要回到實際情境。",
    tags: ["正義牌", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "正義牌感情代表分手嗎？", answer: "未必。它可能提醒關係要談公平、承擔和界線。" },
      { question: "正義牌逆位代表對方不公平嗎？", answer: "可能，但也可能是你掌握的資訊不完整。" },
      { question: "正義牌可以看法律問題嗎？", answer: "公開文章不能提供個案法律判斷，只能說牌義提醒的責任與後果。" },
    ],
  },
  {
    id: "TAROT-M12",
    section: "tarot",
    slug: "hanged-man-card-meaning",
    primaryKeyword: "吊人牌意思",
    secondaryKeywords: ["吊人牌正位", "吊人牌逆位", "吊人牌感情"],
    title: "吊人牌意思：正位、逆位與暫停等待怎麼看",
    description: "吊人牌常和暫停、等待、換角度與犧牲感有關；本文整理感情與工作情境，避免把等待寫成唯一答案。",
    answer: "吊人牌提醒暫停和換角度，但不代表你必須一直等待或犧牲，也要回到實際情境與條件。",
    tags: ["吊人牌", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "吊人牌感情代表等待嗎？", answer: "可能，但要看等待是否有訊息、界線和時間感。" },
      { question: "吊人逆位是不是該放棄？", answer: "未必。它可能提醒你卡太久，需要重新看問題。" },
      { question: "吊人牌工作怎麼看？", answer: "可能代表暫停、轉換視角或計畫未成熟。" },
    ],
  },
  {
    id: "TAROT-M15",
    section: "tarot",
    slug: "devil-card-meaning",
    primaryKeyword: "惡魔牌意思",
    secondaryKeywords: ["惡魔牌正位", "惡魔牌逆位", "惡魔牌感情"],
    title: "惡魔牌意思：正位、逆位與執著依賴怎麼看",
    description: "惡魔牌常和執著、依賴、慾望與界線有關；本文整理感情、工作與逆位情境，不把牌義寫成恐嚇。",
    answer: "惡魔牌提醒執著、依賴和界線失衡，重點是看你被什麼綁住，也要回到實際情境與條件。",
    tags: ["惡魔牌", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "惡魔牌感情是不是不好？", answer: "未必。它提醒依賴、執著和界線，不代表關係會結束。" },
      { question: "惡魔牌逆位是好事嗎？", answer: "可能代表開始鬆動束縛，但仍要看現實行動。" },
      { question: "惡魔牌代表誘惑嗎？", answer: "可能，也可能代表壓力、利益或不健康的交換。" },
    ],
  },
  {
    id: "TAROT-M17",
    section: "tarot",
    slug: "star-card-meaning",
    primaryKeyword: "星星牌意思",
    secondaryKeywords: ["星星牌正位", "星星牌逆位", "星星牌感情"],
    title: "星星牌意思：正位、逆位與重新有希望怎麼看",
    description: "星星牌常和希望、修復、信任與重新整理有關；本文整理正位、逆位、感情與工作情境，不承諾結果。",
    answer: "星星牌提醒希望和修復，但希望需要時間、信任和可執行的下一步，也要回到實際情境。",
    tags: ["星星牌", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "星星牌感情代表復合嗎？", answer: "不代表。它可能提醒修復和希望，但仍要看雙方行動。" },
      { question: "星星牌逆位是不是沒希望？", answer: "未必。可能是你還沒恢復信任，或期待放得太遠。" },
      { question: "星星牌工作怎麼看？", answer: "可以看願景、長期累積和信心，但不能承諾成功。" },
    ],
  },
  {
    id: "TAROT-M19",
    section: "tarot",
    slug: "sun-card-meaning",
    primaryKeyword: "太陽牌意思",
    secondaryKeywords: ["太陽牌正位", "太陽牌逆位", "太陽牌感情"],
    title: "太陽牌意思：正位、逆位與關係變明朗怎麼看",
    description: "太陽牌常和明朗、坦白、活力與看見真相有關；本文整理感情、工作與逆位情境，也保留牌義限制。",
    answer: "太陽牌提醒事情可能變明朗，但明朗不代表局面會照期待發展，也要回到實際情境與條件。",
    tags: ["太陽牌", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "太陽牌感情代表好結果嗎？", answer: "未必。它可能代表明朗和互動增加，但不承諾最後結果。" },
      { question: "太陽牌逆位是壞牌嗎？", answer: "未必。可能是快樂感不足、資訊不完整，或期待太高。" },
      { question: "太陽牌工作代表被看見嗎？", answer: "可能，但仍要看成果、角色和現實條件。" },
    ],
  },
  {
    id: "TAROT-M20",
    section: "tarot",
    slug: "judgement-card-meaning",
    primaryKeyword: "審判牌意思",
    secondaryKeywords: ["審判牌正位", "審判牌逆位", "審判牌復合"],
    title: "審判牌意思：正位、逆位與是否重新開始怎麼看",
    description: "審判牌常和回顧、覺醒、重新開始與關係復盤有關；本文整理感情與工作情境，不把它寫成復合承諾。",
    answer: "審判牌提醒復盤和重新選擇，重點是你是否真的看懂過去的問題，也要回到實際情境。",
    tags: ["審判牌", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "審判牌代表復合嗎？", answer: "未必。它可能指向回顧與重新選擇，但不承諾對方回來。" },
      { question: "審判牌逆位怎麼看？", answer: "可能是不想面對問題、還沒準備好，或仍卡在舊模式。" },
      { question: "審判牌工作代表轉職嗎？", answer: "可能代表重新評估方向，但不能直接等於轉職成功。" },
    ],
  },
  {
    id: "TAROT-PENTACLES-KING",
    section: "tarot",
    slug: "king-of-pentacles-meaning",
    primaryKeyword: "錢幣國王",
    secondaryKeywords: ["錢幣國王感情", "錢幣國王工作", "錢幣國王逆位"],
    title: "錢幣國王意思：正位、逆位、感情與工作怎麼看",
    description: "錢幣國王常和資源、穩定、承擔與現實安全感有關；本文整理感情、工作與逆位提醒，不提供財務建議。",
    answer: "錢幣國王提醒資源與穩定承擔，但不能承諾感情結果或財務結果，也要回到實際情境。",
    tags: ["錢幣國王", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "錢幣國王感情代表穩定嗎？", answer: "可能代表穩定需求或承擔，但不承諾關係結果。" },
      { question: "錢幣國王逆位怎麼看？", answer: "可能是控制資源、過度保守或安全感不足。" },
      { question: "錢幣國王可以看財運嗎？", answer: "只能看資源提醒，不提供個人財務決策或賺錢承諾。" },
    ],
  },
  {
    id: "TAROT-SWORDS-07",
    section: "tarot",
    slug: "seven-of-swords-meaning",
    primaryKeyword: "寶劍七",
    secondaryKeywords: ["寶劍七感情", "寶劍七工作", "寶劍七逆位"],
    title: "寶劍七意思：正位、逆位、感情與工作怎麼看",
    description: "寶劍七常和隱瞞、策略、逃避與不正面處理有關；本文整理感情與工作情境，不用牌義直接指控任何人。",
    answer: "寶劍七提醒隱瞞、逃避或策略行動，重點是先分清事實與猜測，也要回到實際情境與條件。",
    tags: ["寶劍七", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "寶劍七感情代表對方騙我嗎？", answer: "不能直接這樣下結論。它提醒資訊不透明或逃避，但仍要看事實。" },
      { question: "寶劍七逆位是被發現嗎？", answer: "可能是事情浮出、想坦白，或逃避策略失效。" },
      { question: "寶劍七工作怎麼看？", answer: "可能是溝通不透明、策略行動或有人避開責任。" },
    ],
  },
  {
    id: "TAROT-WANDS-03",
    section: "tarot",
    slug: "three-of-wands-meaning",
    primaryKeyword: "權杖三",
    secondaryKeywords: ["權杖三感情", "權杖三工作", "權杖三逆位"],
    title: "權杖三意思：正位、逆位、感情與工作怎麼看",
    description: "權杖三常和等待成果、拓展、遠方合作與下一步佈局有關；本文整理感情與工作情境，不把等待寫成承諾。",
    answer: "權杖三提醒你看遠一點，但也要檢查等待是否有實際進展，也要回到實際情境與條件。",
    tags: ["權杖三", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "權杖三感情代表對方會來嗎？", answer: "不承諾。它比較像提醒等待、距離和未來規劃。" },
      { question: "權杖三逆位怎麼看？", answer: "可能是延遲、計畫卡住，或期待太遠。" },
      { question: "權杖三工作代表機會嗎？", answer: "可能代表拓展機會，但仍要看資源和執行。" },
    ],
  },
  {
    id: "TAROT-WANDS-05",
    section: "tarot",
    slug: "five-of-wands-meaning",
    primaryKeyword: "權杖五",
    secondaryKeywords: ["權杖五感情", "權杖五工作", "權杖五逆位"],
    title: "權杖五意思：正位、逆位、感情與工作怎麼看",
    description: "權杖五常和衝突、競爭、摩擦與意見不合有關；本文整理感情與工作情境，幫你分清衝突是否值得處理。",
    answer: "權杖五提醒衝突與競爭，重點是看摩擦在推進問題還是消耗彼此，也要回到實際情境。",
    tags: ["權杖五", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "權杖五感情代表會分手嗎？", answer: "未必。它可能只是提醒衝突、競爭或溝通方式需要調整。" },
      { question: "權杖五逆位怎麼看？", answer: "可能是避免衝突、暗中不滿，或摩擦逐漸緩和。" },
      { question: "權杖五工作代表競爭嗎？", answer: "常見是競爭和意見不合，但未必是壞事。" },
    ],
  },
  {
    id: "TAROT-PENTACLES-05",
    section: "tarot",
    slug: "five-of-pentacles-meaning",
    primaryKeyword: "錢幣五",
    secondaryKeywords: ["錢幣五感情", "錢幣五工作", "錢幣五逆位"],
    title: "錢幣五意思：正位、逆位、感情與工作怎麼看",
    description: "錢幣五常和匱乏、被排除、資源不足與安全感有關；本文整理感情與工作情境，不提供財務建議。",
    answer: "錢幣五提醒匱乏感和資源不足，重點是分清現實缺口與安全感焦慮，也要回到實際情境。",
    tags: ["錢幣五", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "錢幣五感情代表被放棄嗎？", answer: "未必。它可能是被忽略、資源不足或安全感受傷。" },
      { question: "錢幣五逆位是好轉嗎？", answer: "可能代表開始找回資源，但仍要看現實條件。" },
      { question: "錢幣五可以看財務嗎？", answer: "只能整理資源提醒，不提供個人財務決策。" },
    ],
  },
  {
    id: "TAROT-SWORDS-09",
    section: "tarot",
    slug: "nine-of-swords-meaning",
    primaryKeyword: "寶劍九",
    secondaryKeywords: ["寶劍九感情", "寶劍九逆位", "寶劍九工作"],
    title: "寶劍九意思：正位、逆位、感情與工作怎麼看",
    description: "寶劍九常和焦慮、失眠、想太多與心理壓力有關；本文整理感情與工作情境，但不提供健康專業判斷。",
    answer: "寶劍九提醒焦慮和反覆擔心，重點是把事實、猜測和身心壓力分開，也要回到實際情境。",
    tags: ["寶劍九", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "寶劍九感情代表壞結果嗎？", answer: "不代表。它常提醒焦慮，而不是事情已經定案。" },
      { question: "寶劍九逆位是好轉嗎？", answer: "可能代表開始面對壓力或找到出口。" },
      { question: "寶劍九可以看心理狀態嗎？", answer: "只能作為情緒提醒，不是健康或心理專業判斷。" },
    ],
  },
  {
    id: "TAROT-SWORDS-02",
    section: "tarot",
    slug: "two-of-swords-meaning",
    primaryKeyword: "寶劍二",
    secondaryKeywords: ["寶劍二感情", "寶劍二逆位", "寶劍二工作"],
    title: "寶劍二意思：正位、逆位、感情與工作怎麼看",
    description: "寶劍二常和猶豫、僵局、暫時不決定與資訊不足有關；本文整理感情與工作情境，協助縮小問題。",
    answer: "寶劍二提醒你卡在選擇或資訊不足，重點是先看不想面對的是什麼，也要回到實際情境。",
    tags: ["寶劍二", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "寶劍二感情代表冷戰嗎？", answer: "可能是冷戰、僵局或不願面對問題，但不能單獨下結論。" },
      { question: "寶劍二逆位怎麼看？", answer: "可能是僵局鬆動，或你無法再拖延選擇。" },
      { question: "寶劍二工作代表要離職嗎？", answer: "不代表。它提醒資訊不足或決策卡住。" },
    ],
  },
  {
    id: "TAROT-CUPS-02",
    section: "tarot",
    slug: "two-of-cups-meaning",
    primaryKeyword: "聖杯二",
    secondaryKeywords: ["聖杯二感情", "聖杯二逆位", "聖杯二工作"],
    title: "聖杯二意思：正位、逆位、感情與工作怎麼看",
    description: "聖杯二常和互相靠近、對等、合作與關係連結有關；本文整理感情與工作情境，但不承諾復合或承諾。",
    answer: "聖杯二提醒關係連結與互相靠近，但是否穩定仍要看實際互動，也要回到實際情境與條件。",
    tags: ["聖杯二", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "聖杯二感情代表在一起嗎？", answer: "未必。它代表連結和靠近，但不承諾關係結果。" },
      { question: "聖杯二逆位是沒緣分嗎？", answer: "未必。可能是期待不對等、互動失衡或溝通不足。" },
      { question: "聖杯二工作怎麼看？", answer: "常見是合作、協調和互信問題。" },
    ],
  },
  {
    id: "MBTI-TYPE-INTP",
    section: "mbti",
    slug: "intp-meaning",
    primaryKeyword: "INTP 是什麼",
    secondaryKeywords: ["INTP 感情", "INTP 工作", "INTP 人際"],
    title: "INTP 是什麼？感情、工作與想太多怎麼看",
    description: "INTP 常被連到分析、好奇、想太多與距離感；本文整理感情、工作與人際情境，也說明人格類型不能當專業評估。",
    answer: "INTP 重視理解和邏輯，但不代表沒有感受，只是需要時間整理想法，也要回到實際情境。",
    tags: ["INTP", "16 型人格", "感情", "工作", "人際"],
    faq: [
      { question: "INTP 喜歡一個人會怎樣？", answer: "可能會先觀察、提問或用行動協助，未必直接表達情緒。" },
      { question: "INTP 為什麼想太多？", answer: "常和需要理解系統、害怕做無效決定有關。" },
      { question: "INTP 適合什麼工作？", answer: "適合分析、研究和解決問題，但仍要看能力與環境。" },
    ],
  },
  {
    id: "MBTI-TYPE-ISTJ",
    section: "mbti",
    slug: "istj-meaning",
    primaryKeyword: "ISTJ 是什麼",
    secondaryKeywords: ["ISTJ 感情", "ISTJ 工作", "ISTJ 人際"],
    title: "ISTJ 是什麼？感情、工作與責任壓力怎麼看",
    description: "ISTJ 常被連到責任、秩序、務實與穩定；本文整理感情、工作與人際情境，也說明類型不能代表全部。",
    answer: "ISTJ 重視責任和可預期性，但不代表沒有彈性，需要清楚規則和承諾，也要回到實際情境。",
    tags: ["ISTJ", "16 型人格", "感情", "工作", "人際"],
    faq: [
      { question: "ISTJ 喜歡一個人會怎樣？", answer: "常用穩定行動和負責任的方式表達，未必甜言蜜語。" },
      { question: "ISTJ 適合什麼工作？", answer: "常適合流程、管理、執行和長期累積，但仍要看個人能力。" },
      { question: "ISTJ 很固執嗎？", answer: "未必。可能只是需要足夠理由才願意改變。" },
    ],
  },
  {
    id: "MBTI-TYPE-ISTP",
    section: "mbti",
    slug: "istp-meaning",
    primaryKeyword: "ISTP 是什麼",
    secondaryKeywords: ["ISTP 感情", "ISTP 工作", "ISTP 人際"],
    title: "ISTP 是什麼？感情、工作與保持距離怎麼看",
    description: "ISTP 常被連到冷靜、實作、自由感與距離感；本文整理感情、工作與人際情境，也保留人格類型限制。",
    answer: "ISTP 常需要空間和自主感，但不代表不在乎，只是不喜歡被過度推進，也要回到實際情境。",
    tags: ["ISTP", "16 型人格", "感情", "工作", "人際"],
    faq: [
      { question: "ISTP 喜歡一個人會怎樣？", answer: "可能用陪伴、解決問題或默默協助表達，未必直接說情緒。" },
      { question: "ISTP 為什麼忽冷忽熱？", answer: "有時是需要空間，未必是不在乎。" },
      { question: "ISTP 適合什麼工作？", answer: "常適合實作、技術、危機處理或需要獨立判斷的工作。" },
    ],
  },
  {
    id: "MBTI-TYPE-ISFP",
    section: "mbti",
    slug: "isfp-meaning",
    primaryKeyword: "ISFP 是什麼",
    secondaryKeywords: ["ISFP 感情", "ISFP 工作", "ISFP 人際"],
    title: "ISFP 是什麼？感情、工作與情緒界線怎麼看",
    description: "ISFP 常被連到感受、審美、自由與界線；本文整理感情、工作與人際情境，也說明人格類型不能決定人生。",
    answer: "ISFP 重視真實感受和自由空間，但不代表任性或不負責任，也要回到實際情境。",
    tags: ["ISFP", "16 型人格", "感情", "工作", "人際"],
    faq: [
      { question: "ISFP 喜歡一個人會怎樣？", answer: "可能透過陪伴、細節和生活感表達，未必高調。" },
      { question: "ISFP 為什麼需要空間？", answer: "通常是為了整理感受和保護界線。" },
      { question: "ISFP 適合什麼工作？", answer: "常適合創作、服務、體驗和需要細膩感受的工作，但不是固定答案。" },
    ],
  },
  {
    id: "MBTI-TYPE-ENFJ",
    section: "mbti",
    slug: "enfj-meaning",
    primaryKeyword: "ENFJ 是什麼",
    secondaryKeywords: ["ENFJ 感情", "ENFJ 工作", "ENFJ 人際"],
    title: "ENFJ 是什麼？感情、工作與照顧別人怎麼看",
    description: "ENFJ 常被連到照顧、帶領、關係敏銳與他人期待；本文整理感情、工作與人際情境，也保留限制。",
    answer: "ENFJ 擅長理解他人需求，但也容易把別人的期待扛成自己的責任，也要回到實際情境。",
    tags: ["ENFJ", "16 型人格", "感情", "工作", "人際"],
    faq: [
      { question: "ENFJ 喜歡一個人會怎樣？", answer: "常主動關心、安排和支持，但也可能太快承擔對方情緒。" },
      { question: "ENFJ 適合什麼工作？", answer: "常適合協調、教學、顧問、管理和需要理解人的工作。" },
      { question: "ENFJ 會不會太討好？", answer: "可能有這個傾向，但不是每個 ENFJ 都如此。" },
    ],
  },
  {
    id: "MBTI-TYPE-ESTJ",
    section: "mbti",
    slug: "estj-meaning",
    primaryKeyword: "ESTJ 是什麼",
    secondaryKeywords: ["ESTJ 感情", "ESTJ 工作", "ESTJ 人際"],
    title: "ESTJ 是什麼？感情、工作與控制節奏怎麼看",
    description: "ESTJ 常被連到執行、規劃、責任與控制感；本文整理感情、工作與人際情境，也說明類型不能代表全部。",
    answer: "ESTJ 重視效率和責任，但要看控制感是否讓關係或合作失衡，也要回到實際情境。",
    tags: ["ESTJ", "16 型人格", "感情", "工作", "人際"],
    faq: [
      { question: "ESTJ 喜歡一個人會怎樣？", answer: "可能用安排、承擔和實際行動表達。" },
      { question: "ESTJ 很控制嗎？", answer: "未必。控制感可能來自責任壓力，也可能是溝通方式需要調整。" },
      { question: "ESTJ 適合什麼工作？", answer: "常適合管理、營運、執行和流程改善，但仍要看個人能力。" },
    ],
  },
  {
    id: "MBTI-TYPE-ESFJ",
    section: "mbti",
    slug: "esfj-meaning",
    primaryKeyword: "ESFJ 是什麼",
    secondaryKeywords: ["ESFJ 感情", "ESFJ 工作", "ESFJ 人際"],
    title: "ESFJ 是什麼？感情、工作與被需要感怎麼看",
    description: "ESFJ 常被連到照顧、群體、責任與被需要感；本文整理感情、工作與人際情境，也保留人格類型限制。",
    answer: "ESFJ 重視關係和照顧，但也需要分清關心別人和失去自己界線，也要回到實際情境。",
    tags: ["ESFJ", "16 型人格", "感情", "工作", "人際"],
    faq: [
      { question: "ESFJ 喜歡一個人會怎樣？", answer: "常會主動照顧、安排和確認對方需求。" },
      { question: "ESFJ 為什麼怕衝突？", answer: "可能因為重視關係氣氛，但不代表不能建立界線。" },
      { question: "ESFJ 適合什麼工作？", answer: "常適合服務、協調、管理和需要穩定互動的工作。" },
    ],
  },
  {
    id: "MBTI-TYPE-ESTP",
    section: "mbti",
    slug: "estp-meaning",
    primaryKeyword: "ESTP 是什麼",
    secondaryKeywords: ["ESTP 感情", "ESTP 工作", "ESTP 人際"],
    title: "ESTP 是什麼？感情、工作與衝動決定怎麼看",
    description: "ESTP 常被連到行動力、刺激、臨場反應與衝動決定；本文整理感情、工作與人際情境，也說明限制。",
    answer: "ESTP 擅長當下反應和行動，但也需要檢查衝動背後的代價，也要回到實際情境。",
    tags: ["ESTP", "16 型人格", "感情", "工作", "人際"],
    faq: [
      { question: "ESTP 喜歡一個人會怎樣？", answer: "可能直接靠近、邀約或用行動製造互動。" },
      { question: "ESTP 很衝動嗎？", answer: "可能行動快，但不代表沒有判斷；要看是否願意承擔後果。" },
      { question: "ESTP 適合什麼工作？", answer: "常適合業務、危機處理、現場執行和需要反應快的工作。" },
    ],
  },
  {
    id: "MBTI-TYPE-ESFP",
    section: "mbti",
    slug: "esfp-meaning",
    primaryKeyword: "ESFP 是什麼",
    secondaryKeywords: ["ESFP 感情", "ESFP 工作", "ESFP 人際"],
    title: "ESFP 是什麼？感情、工作與當下感受怎麼看",
    description: "ESFP 常被連到表達、社交、當下感受與生活熱度；本文整理感情、工作與人際情境，也說明人格類型限制。",
    answer: "ESFP 重視當下感受和互動熱度，但不代表沒有長期思考，也要回到實際情境與條件。",
    tags: ["ESFP", "16 型人格", "感情", "工作", "人際"],
    faq: [
      { question: "ESFP 喜歡一個人會怎樣？", answer: "常會明顯互動、分享生活，或用陪伴表達好感。" },
      { question: "ESFP 只看當下嗎？", answer: "未必。只是他們常先從當下感受和人際回饋理解事情。" },
      { question: "ESFP 適合什麼工作？", answer: "常適合服務、表演、銷售、活動和需要現場互動的工作。" },
    ],
  },
  {
    id: "TAROT-WANDS-01",
    section: "tarot",
    slug: "ace-of-wands-meaning",
    primaryKeyword: "權杖一",
    secondaryKeywords: ["權杖一感情", "權杖一工作", "權杖一逆位"],
    title: "權杖一意思：正位、逆位、感情與工作怎麼看",
    description: "權杖一常和新行動、熱情和開始有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "權杖一提醒新行動、熱情和開始，逆位可看行動衝動或準備不足；但不能單靠一張牌決定結果。",
    tags: ["權杖一", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "權杖一感情代表什麼？", answer: "多半可看新火花、主動靠近與試探，但不能直接判定關係結果。" },
      { question: "權杖一逆位怎麼看？", answer: "常見是行動衝動或準備不足，仍要搭配問題和牌陣位置。" },
      { question: "權杖一工作怎麼看？", answer: "可放在專案啟動、點子出現與行動力裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-WANDS-02",
    section: "tarot",
    slug: "two-of-wands-meaning",
    primaryKeyword: "權杖二",
    secondaryKeywords: ["權杖二感情", "權杖二工作", "權杖二逆位"],
    title: "權杖二意思：正位、逆位、感情與工作怎麼看",
    description: "權杖二常和選擇、計劃和等待出手有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "權杖二提醒選擇、計劃和等待出手，逆位可看猶豫太久或計畫停在想像；但不能單靠一張牌決定結果。",
    tags: ["權杖二", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "權杖二感情代表什麼？", answer: "多半可看關係未定、距離感與未來規劃，但不能直接判定關係結果。" },
      { question: "權杖二逆位怎麼看？", answer: "常見是猶豫太久或計畫停在想像，仍要搭配問題和牌陣位置。" },
      { question: "權杖二工作怎麼看？", answer: "可放在策略規劃、觀望機會與下一步安排裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-WANDS-04",
    section: "tarot",
    slug: "four-of-wands-meaning",
    primaryKeyword: "權杖四",
    secondaryKeywords: ["權杖四感情", "權杖四工作", "權杖四逆位"],
    title: "權杖四意思：正位、逆位、感情與工作怎麼看",
    description: "權杖四常和穩定、慶祝和關係落地有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "權杖四提醒穩定、慶祝和關係落地，逆位可看表面和諧或安全感不穩；但不能單靠一張牌決定結果。",
    tags: ["權杖四", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "權杖四感情代表什麼？", answer: "多半可看關係定下來、被接納與共同生活感，但不能直接判定關係結果。" },
      { question: "權杖四逆位怎麼看？", answer: "常見是表面和諧或安全感不穩，仍要搭配問題和牌陣位置。" },
      { question: "權杖四工作怎麼看？", answer: "可放在團隊成果、里程碑與工作氛圍裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-WANDS-06",
    section: "tarot",
    slug: "six-of-wands-meaning",
    primaryKeyword: "權杖六",
    secondaryKeywords: ["權杖六感情", "權杖六工作", "權杖六逆位"],
    title: "權杖六意思：正位、逆位、感情與工作怎麼看",
    description: "權杖六常和被看見、肯定和階段成果有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "權杖六提醒被看見、肯定和階段成果，逆位可看太在意掌聲或成績不穩；但不能單靠一張牌決定結果。",
    tags: ["權杖六", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "權杖六感情代表什麼？", answer: "多半可看被重視、關係曝光與期待被肯定，但不能直接判定關係結果。" },
      { question: "權杖六逆位怎麼看？", answer: "常見是太在意掌聲或成績不穩，仍要搭配問題和牌陣位置。" },
      { question: "權杖六工作怎麼看？", answer: "可放在成果展示、升遷能見度與外部評價裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-WANDS-07",
    section: "tarot",
    slug: "seven-of-wands-meaning",
    primaryKeyword: "權杖七",
    secondaryKeywords: ["權杖七感情", "權杖七工作", "權杖七逆位"],
    title: "權杖七意思：正位、逆位、感情與工作怎麼看",
    description: "權杖七常和防守、壓力和堅持立場有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "權杖七提醒防守、壓力和堅持立場，逆位可看過度防衛或撐到失衡；但不能單靠一張牌決定結果。",
    tags: ["權杖七", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "權杖七感情代表什麼？", answer: "多半可看關係裡的界線、立場和安全感拉扯，但不能直接判定關係結果。" },
      { question: "權杖七逆位怎麼看？", answer: "常見是過度防衛或撐到失衡，仍要搭配問題和牌陣位置。" },
      { question: "權杖七工作怎麼看？", answer: "可放在競爭壓力、守住位置與說清底線裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-WANDS-08",
    section: "tarot",
    slug: "eight-of-wands-meaning",
    primaryKeyword: "權杖八",
    secondaryKeywords: ["權杖八感情", "權杖八工作", "權杖八逆位"],
    title: "權杖八意思：正位、逆位、感情與工作怎麼看",
    description: "權杖八常和訊息、推進和節奏加快有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "權杖八提醒訊息、推進和節奏加快，逆位可看太快、混亂或溝通延遲；但不能單靠一張牌決定結果。",
    tags: ["權杖八", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "權杖八感情代表什麼？", answer: "多半可看訊息變多、互動升溫與進展速度，但不能直接判定關係結果。" },
      { question: "權杖八逆位怎麼看？", answer: "常見是太快、混亂或溝通延遲，仍要搭配問題和牌陣位置。" },
      { question: "權杖八工作怎麼看？", answer: "可放在快速決策、任務推進與時程壓力裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-WANDS-09",
    section: "tarot",
    slug: "nine-of-wands-meaning",
    primaryKeyword: "權杖九",
    secondaryKeywords: ["權杖九感情", "權杖九工作", "權杖九逆位"],
    title: "權杖九意思：正位、逆位、感情與工作怎麼看",
    description: "權杖九常和戒備、疲憊和還要不要撐有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "權杖九提醒戒備、疲憊和還要不要撐，逆位可看防線太高或不敢放鬆；但不能單靠一張牌決定結果。",
    tags: ["權杖九", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "權杖九感情代表什麼？", answer: "多半可看受過傷後的防備、信任感和距離，但不能直接判定關係結果。" },
      { question: "權杖九逆位怎麼看？", answer: "常見是防線太高或不敢放鬆，仍要搭配問題和牌陣位置。" },
      { question: "權杖九工作怎麼看？", answer: "可放在壓力尾聲、風險控管與疲勞累積裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-WANDS-10",
    section: "tarot",
    slug: "ten-of-wands-meaning",
    primaryKeyword: "權杖十",
    secondaryKeywords: ["權杖十感情", "權杖十工作", "權杖十逆位"],
    title: "權杖十意思：正位、逆位、感情與工作怎麼看",
    description: "權杖十常和責任過重、壓力累積和負擔有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "權杖十提醒責任過重、壓力累積和負擔，逆位可看硬撐、分工失衡或責任不清；但不能單靠一張牌決定結果。",
    tags: ["權杖十", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "權杖十感情代表什麼？", answer: "多半可看關係裡扛太多、期待壓力和沉重感，但不能直接判定關係結果。" },
      { question: "權杖十逆位怎麼看？", answer: "常見是硬撐、分工失衡或責任不清，仍要搭配問題和牌陣位置。" },
      { question: "權杖十工作怎麼看？", answer: "可放在工作量過載、責任分配與優先順序裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-WANDS-PAGE",
    section: "tarot",
    slug: "page-of-wands-meaning",
    primaryKeyword: "權杖侍者",
    secondaryKeywords: ["權杖侍者感情", "權杖侍者工作", "權杖侍者逆位"],
    title: "權杖侍者意思：正位、逆位、感情與工作怎麼看",
    description: "權杖侍者常和新興趣、試探和行動訊號有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "權杖侍者提醒新興趣、試探和行動訊號，逆位可看三分鐘熱度或準備不足；但不能單靠一張牌決定結果。",
    tags: ["權杖侍者", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "權杖侍者感情代表什麼？", answer: "多半可看曖昧試探、好奇靠近與新鮮感，但不能直接判定關係結果。" },
      { question: "權杖侍者逆位怎麼看？", answer: "常見是三分鐘熱度或準備不足，仍要搭配問題和牌陣位置。" },
      { question: "權杖侍者工作怎麼看？", answer: "可放在新任務、學習動機與嘗試機會裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-WANDS-KNIGHT",
    section: "tarot",
    slug: "knight-of-wands-meaning",
    primaryKeyword: "權杖騎士",
    secondaryKeywords: ["權杖騎士感情", "權杖騎士工作", "權杖騎士逆位"],
    title: "權杖騎士意思：正位、逆位、感情與工作怎麼看",
    description: "權杖騎士常和熱情、衝刺和快速變動有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "權杖騎士提醒熱情、衝刺和快速變動，逆位可看急躁、來得快去得快或承擔不足；但不能單靠一張牌決定結果。",
    tags: ["權杖騎士", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "權杖騎士感情代表什麼？", answer: "多半可看強烈吸引、快速靠近與關係節奏，但不能直接判定關係結果。" },
      { question: "權杖騎士逆位怎麼看？", answer: "常見是急躁、來得快去得快或承擔不足，仍要搭配問題和牌陣位置。" },
      { question: "權杖騎士工作怎麼看？", answer: "可放在快速推進、冒險行動與臨場決策裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-WANDS-QUEEN",
    section: "tarot",
    slug: "queen-of-wands-meaning",
    primaryKeyword: "權杖皇后",
    secondaryKeywords: ["權杖皇后感情", "權杖皇后工作", "權杖皇后逆位"],
    title: "權杖皇后意思：正位、逆位、感情與工作怎麼看",
    description: "權杖皇后常和自信、吸引力和主導感有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "權杖皇后提醒自信、吸引力和主導感，逆位可看過度逞強或把需求藏起來；但不能單靠一張牌決定結果。",
    tags: ["權杖皇后", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "權杖皇后感情代表什麼？", answer: "多半可看魅力、自我價值與主動表達，但不能直接判定關係結果。" },
      { question: "權杖皇后逆位怎麼看？", answer: "常見是過度逞強或把需求藏起來，仍要搭配問題和牌陣位置。" },
      { question: "權杖皇后工作怎麼看？", answer: "可放在帶動團隊、展現影響力與穩定自信裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-WANDS-KING",
    section: "tarot",
    slug: "king-of-wands-meaning",
    primaryKeyword: "權杖國王",
    secondaryKeywords: ["權杖國王感情", "權杖國王工作", "權杖國王逆位"],
    title: "權杖國王意思：正位、逆位、感情與工作怎麼看",
    description: "權杖國王常和決斷、領導和掌控節奏有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "權杖國王提醒決斷、領導和掌控節奏，逆位可看控制太強或只看自己的方向；但不能單靠一張牌決定結果。",
    tags: ["權杖國王", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "權杖國王感情代表什麼？", answer: "多半可看明確態度、承擔能力與互動主導權，但不能直接判定關係結果。" },
      { question: "權杖國王逆位怎麼看？", answer: "常見是控制太強或只看自己的方向，仍要搭配問題和牌陣位置。" },
      { question: "權杖國王工作怎麼看？", answer: "可放在領導決策、方向設定與行動整合裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-CUPS-01",
    section: "tarot",
    slug: "ace-of-cups-meaning",
    primaryKeyword: "聖杯一",
    secondaryKeywords: ["聖杯一感情", "聖杯一工作", "聖杯一逆位"],
    title: "聖杯一意思：正位、逆位、感情與工作怎麼看",
    description: "聖杯一常和新感情、情緒流動和敞開有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "聖杯一提醒新感情、情緒流動和敞開，逆位可看情緒封閉或期待太滿；但不能單靠一張牌決定結果。",
    tags: ["聖杯一", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "聖杯一感情代表什麼？", answer: "多半可看新好感、告白可能性與情緒回應，但不能直接判定關係結果。" },
      { question: "聖杯一逆位怎麼看？", answer: "常見是情緒封閉或期待太滿，仍要搭配問題和牌陣位置。" },
      { question: "聖杯一工作怎麼看？", answer: "可放在創意合作、人際支持與工作感受裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-CUPS-03",
    section: "tarot",
    slug: "three-of-cups-meaning",
    primaryKeyword: "聖杯三",
    secondaryKeywords: ["聖杯三感情", "聖杯三工作", "聖杯三逆位"],
    title: "聖杯三意思：正位、逆位、感情與工作怎麼看",
    description: "聖杯三常和朋友、社群和第三方影響有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "聖杯三提醒朋友、社群和第三方影響，逆位可看圈子干擾或過度依賴認同；但不能單靠一張牌決定結果。",
    tags: ["聖杯三", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "聖杯三感情代表什麼？", answer: "多半可看朋友介入、公開互動與相處氣氛，但不能直接判定關係結果。" },
      { question: "聖杯三逆位怎麼看？", answer: "常見是圈子干擾或過度依賴認同，仍要搭配問題和牌陣位置。" },
      { question: "聖杯三工作怎麼看？", answer: "可放在團隊合作、慶祝成果與人際協調裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-CUPS-04",
    section: "tarot",
    slug: "four-of-cups-meaning",
    primaryKeyword: "聖杯四",
    secondaryKeywords: ["聖杯四感情", "聖杯四工作", "聖杯四逆位"],
    title: "聖杯四意思：正位、逆位、感情與工作怎麼看",
    description: "聖杯四常和冷淡、無感和錯過機會有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "聖杯四提醒冷淡、無感和錯過機會，逆位可看情緒停滯或看不見選項；但不能單靠一張牌決定結果。",
    tags: ["聖杯四", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "聖杯四感情代表什麼？", answer: "多半可看互動變淡、失去興趣與被動等待，但不能直接判定關係結果。" },
      { question: "聖杯四逆位怎麼看？", answer: "常見是情緒停滯或看不見選項，仍要搭配問題和牌陣位置。" },
      { question: "聖杯四工作怎麼看？", answer: "可放在職場倦怠、機會無感與動力下降裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-CUPS-05",
    section: "tarot",
    slug: "five-of-cups-meaning",
    primaryKeyword: "聖杯五",
    secondaryKeywords: ["聖杯五感情", "聖杯五工作", "聖杯五逆位"],
    title: "聖杯五意思：正位、逆位、感情與工作怎麼看",
    description: "聖杯五常和失落、後悔和還沒看見的支持有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "聖杯五提醒失落、後悔和還沒看見的支持，逆位可看沉在遺憾裡或忽略可用條件；但不能單靠一張牌決定結果。",
    tags: ["聖杯五", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "聖杯五感情代表什麼？", answer: "多半可看分離後的失望、放不下與修復可能，但不能直接判定關係結果。" },
      { question: "聖杯五逆位怎麼看？", answer: "常見是沉在遺憾裡或忽略可用條件，仍要搭配問題和牌陣位置。" },
      { question: "聖杯五工作怎麼看？", answer: "可放在失誤復盤、情緒低落與重新整理裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-CUPS-06",
    section: "tarot",
    slug: "six-of-cups-meaning",
    primaryKeyword: "聖杯六",
    secondaryKeywords: ["聖杯六感情", "聖杯六工作", "聖杯六逆位"],
    title: "聖杯六意思：正位、逆位、感情與工作怎麼看",
    description: "聖杯六常和舊人、回憶和熟悉感有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "聖杯六提醒舊人、回憶和熟悉感，逆位可看懷舊過度或把過去美化；但不能單靠一張牌決定結果。",
    tags: ["聖杯六", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "聖杯六感情代表什麼？", answer: "多半可看舊情、熟悉安全感與復合想像，但不能直接判定關係結果。" },
      { question: "聖杯六逆位怎麼看？", answer: "常見是懷舊過度或把過去美化，仍要搭配問題和牌陣位置。" },
      { question: "聖杯六工作怎麼看？", answer: "可放在過往經驗、舊同事合作與熟悉流程裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-CUPS-07",
    section: "tarot",
    slug: "seven-of-cups-meaning",
    primaryKeyword: "聖杯七",
    secondaryKeywords: ["聖杯七感情", "聖杯七工作", "聖杯七逆位"],
    title: "聖杯七意思：正位、逆位、感情與工作怎麼看",
    description: "聖杯七常和幻想、選項太多和投射有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "聖杯七提醒幻想、選項太多和投射，逆位可看想太多、看不清或逃避選擇；但不能單靠一張牌決定結果。",
    tags: ["聖杯七", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "聖杯七感情代表什麼？", answer: "多半可看曖昧想像、理想化對方與選擇混亂，但不能直接判定關係結果。" },
      { question: "聖杯七逆位怎麼看？", answer: "常見是想太多、看不清或逃避選擇，仍要搭配問題和牌陣位置。" },
      { question: "聖杯七工作怎麼看？", answer: "可放在方向太多、點子發散與決策失焦裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-CUPS-08",
    section: "tarot",
    slug: "eight-of-cups-meaning",
    primaryKeyword: "聖杯八",
    secondaryKeywords: ["聖杯八感情", "聖杯八工作", "聖杯八逆位"],
    title: "聖杯八意思：正位、逆位、感情與工作怎麼看",
    description: "聖杯八常和離開、放下和情緒抽離有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "聖杯八提醒離開、放下和情緒抽離，逆位可看想走又不敢走或逃避整理；但不能單靠一張牌決定結果。",
    tags: ["聖杯八", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "聖杯八感情代表什麼？", answer: "多半可看從關係抽離、失望離開與重新找自己，但不能直接判定關係結果。" },
      { question: "聖杯八逆位怎麼看？", answer: "常見是想走又不敢走或逃避整理，仍要搭配問題和牌陣位置。" },
      { question: "聖杯八工作怎麼看？", answer: "可放在離開不適合環境、調整方向與收尾裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-CUPS-09",
    section: "tarot",
    slug: "nine-of-cups-meaning",
    primaryKeyword: "聖杯九",
    secondaryKeywords: ["聖杯九感情", "聖杯九工作", "聖杯九逆位"],
    title: "聖杯九意思：正位、逆位、感情與工作怎麼看",
    description: "聖杯九常和滿足、自我需求和願望感有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "聖杯九提醒滿足、自我需求和願望感，逆位可看沉溺舒適或只顧自己的感受；但不能單靠一張牌決定結果。",
    tags: ["聖杯九", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "聖杯九感情代表什麼？", answer: "多半可看被滿足、享受關係與需求是否對等，但不能直接判定關係結果。" },
      { question: "聖杯九逆位怎麼看？", answer: "常見是沉溺舒適或只顧自己的感受，仍要搭配問題和牌陣位置。" },
      { question: "聖杯九工作怎麼看？", answer: "可放在成果感、個人成就與工作滿意度裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-CUPS-10",
    section: "tarot",
    slug: "ten-of-cups-meaning",
    primaryKeyword: "聖杯十",
    secondaryKeywords: ["聖杯十感情", "聖杯十工作", "聖杯十逆位"],
    title: "聖杯十意思：正位、逆位、感情與工作怎麼看",
    description: "聖杯十常和家庭、長期幸福和共同期待有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "聖杯十提醒家庭、長期幸福和共同期待，逆位可看理想化圓滿或忽略現實分工；但不能單靠一張牌決定結果。",
    tags: ["聖杯十", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "聖杯十感情代表什麼？", answer: "多半可看長期關係、家庭期待與共同生活想像，但不能直接判定關係結果。" },
      { question: "聖杯十逆位怎麼看？", answer: "常見是理想化圓滿或忽略現實分工，仍要搭配問題和牌陣位置。" },
      { question: "聖杯十工作怎麼看？", answer: "可放在團隊願景、組織歸屬與合作穩定裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-CUPS-PAGE",
    section: "tarot",
    slug: "page-of-cups-meaning",
    primaryKeyword: "聖杯侍者",
    secondaryKeywords: ["聖杯侍者感情", "聖杯侍者工作", "聖杯侍者逆位"],
    title: "聖杯侍者意思：正位、逆位、感情與工作怎麼看",
    description: "聖杯侍者常和告白、敏感和情緒訊號有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "聖杯侍者提醒告白、敏感和情緒訊號，逆位可看情緒幼嫩或表達不成熟；但不能單靠一張牌決定結果。",
    tags: ["聖杯侍者", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "聖杯侍者感情代表什麼？", answer: "多半可看曖昧訊息、告白試探與細膩感受，但不能直接判定關係結果。" },
      { question: "聖杯侍者逆位怎麼看？", answer: "常見是情緒幼嫩或表達不成熟，仍要搭配問題和牌陣位置。" },
      { question: "聖杯侍者工作怎麼看？", answer: "可放在創意提案、柔性溝通與新合作苗頭裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-CUPS-KNIGHT",
    section: "tarot",
    slug: "knight-of-cups-meaning",
    primaryKeyword: "聖杯騎士",
    secondaryKeywords: ["聖杯騎士感情", "聖杯騎士工作", "聖杯騎士逆位"],
    title: "聖杯騎士意思：正位、逆位、感情與工作怎麼看",
    description: "聖杯騎士常和浪漫、靠近和承諾是否落地有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "聖杯騎士提醒浪漫、靠近和承諾是否落地，逆位可看只會說好聽話或行動不足；但不能單靠一張牌決定結果。",
    tags: ["聖杯騎士", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "聖杯騎士感情代表什麼？", answer: "多半可看浪漫追求、靠近方式與真實承擔，但不能直接判定關係結果。" },
      { question: "聖杯騎士逆位怎麼看？", answer: "常見是只會說好聽話或行動不足，仍要搭配問題和牌陣位置。" },
      { question: "聖杯騎士工作怎麼看？", answer: "可放在提案說服、關係經營與合作誠意裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-CUPS-QUEEN",
    section: "tarot",
    slug: "queen-of-cups-meaning",
    primaryKeyword: "聖杯皇后",
    secondaryKeywords: ["聖杯皇后感情", "聖杯皇后工作", "聖杯皇后逆位"],
    title: "聖杯皇后意思：正位、逆位、感情與工作怎麼看",
    description: "聖杯皇后常和情緒照顧、共感和界線有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "聖杯皇后提醒情緒照顧、共感和界線，逆位可看過度吸收情緒或失去自己；但不能單靠一張牌決定結果。",
    tags: ["聖杯皇后", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "聖杯皇后感情代表什麼？", answer: "多半可看照顧對方、情緒安全與互相理解，但不能直接判定關係結果。" },
      { question: "聖杯皇后逆位怎麼看？", answer: "常見是過度吸收情緒或失去自己，仍要搭配問題和牌陣位置。" },
      { question: "聖杯皇后工作怎麼看？", answer: "可放在支持團隊、同理協調與情緒界線裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-CUPS-KING",
    section: "tarot",
    slug: "king-of-cups-meaning",
    primaryKeyword: "聖杯國王",
    secondaryKeywords: ["聖杯國王感情", "聖杯國王工作", "聖杯國王逆位"],
    title: "聖杯國王意思：正位、逆位、感情與工作怎麼看",
    description: "聖杯國王常和成熟情緒、穩定支持和自我控制有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "聖杯國王提醒成熟情緒與穩定支持，逆位可看壓抑感受，但不能單牌定結果。",
    tags: ["聖杯國王", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "聖杯國王感情代表什麼？", answer: "多半可看穩定陪伴、成熟回應與情緒承接，但不能直接判定關係結果。" },
      { question: "聖杯國王逆位怎麼看？", answer: "常見是壓抑感受或用冷靜避開真話，仍要搭配問題和牌陣位置。" },
      { question: "聖杯國王工作怎麼看？", answer: "可放在危機處理、穩住團隊與理性表達感受裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-SWORDS-01",
    section: "tarot",
    slug: "ace-of-swords-meaning",
    primaryKeyword: "寶劍一",
    secondaryKeywords: ["寶劍一感情", "寶劍一工作", "寶劍一逆位"],
    title: "寶劍一意思：正位、逆位、感情與工作怎麼看",
    description: "寶劍一常和看清事實、切入重點和說真話有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "寶劍一提醒看清事實、切入重點和說真話，逆位可看話太利、資訊不足或判斷過快；但不能單靠一張牌決定結果。",
    tags: ["寶劍一", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "寶劍一感情代表什麼？", answer: "多半可看把話說清楚、看見真相與溝通開端，但不能直接判定關係結果。" },
      { question: "寶劍一逆位怎麼看？", answer: "常見是話太利、資訊不足或判斷過快，仍要搭配問題和牌陣位置。" },
      { question: "寶劍一工作怎麼看？", answer: "可放在明確判斷、提出方案與釐清問題裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-SWORDS-03",
    section: "tarot",
    slug: "three-of-swords-meaning",
    primaryKeyword: "寶劍三",
    secondaryKeywords: ["寶劍三感情", "寶劍三工作", "寶劍三逆位"],
    title: "寶劍三意思：正位、逆位、感情與工作怎麼看",
    description: "寶劍三常和受傷、失望和真相刺痛有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "寶劍三提醒受傷、失望和真相刺痛，逆位可看卡在傷口或反覆回想；但不能單靠一張牌決定結果。",
    tags: ["寶劍三", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "寶劍三感情代表什麼？", answer: "多半可看心碎、失望、第三方壓力與修復距離，但不能直接判定關係結果。" },
      { question: "寶劍三逆位怎麼看？", answer: "常見是卡在傷口或反覆回想，仍要搭配問題和牌陣位置。" },
      { question: "寶劍三工作怎麼看？", answer: "可放在壞消息、衝突代價與冷靜復盤裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-SWORDS-04",
    section: "tarot",
    slug: "four-of-swords-meaning",
    primaryKeyword: "寶劍四",
    secondaryKeywords: ["寶劍四感情", "寶劍四工作", "寶劍四逆位"],
    title: "寶劍四意思：正位、逆位、感情與工作怎麼看",
    description: "寶劍四常和休息、暫停和需要整理有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "寶劍四提醒休息、暫停和需要整理，逆位可看逃避溝通或休息不足；但不能單靠一張牌決定結果。",
    tags: ["寶劍四", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "寶劍四感情代表什麼？", answer: "多半可看冷靜期、暫停互動與恢復空間，但不能直接判定關係結果。" },
      { question: "寶劍四逆位怎麼看？", answer: "常見是逃避溝通或休息不足，仍要搭配問題和牌陣位置。" },
      { question: "寶劍四工作怎麼看？", answer: "可放在暫停決策、恢復能量與重新排程裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-SWORDS-05",
    section: "tarot",
    slug: "five-of-swords-meaning",
    primaryKeyword: "寶劍五",
    secondaryKeywords: ["寶劍五感情", "寶劍五工作", "寶劍五逆位"],
    title: "寶劍五意思：正位、逆位、感情與工作怎麼看",
    description: "寶劍五常和爭輸贏、消耗和關係破裂有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "寶劍五提醒爭輸贏、消耗和關係破裂，逆位可看為贏而傷人或衝突未收拾；但不能單靠一張牌決定結果。",
    tags: ["寶劍五", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "寶劍五感情代表什麼？", answer: "多半可看吵架後的代價、面子和道歉問題，但不能直接判定關係結果。" },
      { question: "寶劍五逆位怎麼看？", answer: "常見是為贏而傷人或衝突未收拾，仍要搭配問題和牌陣位置。" },
      { question: "寶劍五工作怎麼看？", answer: "可放在辦公室角力、溝通消耗與合作破口裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-SWORDS-06",
    section: "tarot",
    slug: "six-of-swords-meaning",
    primaryKeyword: "寶劍六",
    secondaryKeywords: ["寶劍六感情", "寶劍六工作", "寶劍六逆位"],
    title: "寶劍六意思：正位、逆位、感情與工作怎麼看",
    description: "寶劍六常和離開困境、過渡期和慢慢恢復有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "寶劍六提醒離開困境、過渡期和慢慢恢復，逆位可看拖著問題走或不願面對根因；但不能單靠一張牌決定結果。",
    tags: ["寶劍六", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "寶劍六感情代表什麼？", answer: "多半可看走出低潮、保持距離與關係過渡，但不能直接判定關係結果。" },
      { question: "寶劍六逆位怎麼看？", answer: "常見是拖著問題走或不願面對根因，仍要搭配問題和牌陣位置。" },
      { question: "寶劍六工作怎麼看？", answer: "可放在換環境、交接過渡與逐步修復裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-SWORDS-08",
    section: "tarot",
    slug: "eight-of-swords-meaning",
    primaryKeyword: "寶劍八",
    secondaryKeywords: ["寶劍八感情", "寶劍八工作", "寶劍八逆位"],
    title: "寶劍八意思：正位、逆位、感情與工作怎麼看",
    description: "寶劍八常和被困住、想法限制和害怕行動有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "寶劍八提醒被困住、想法限制和害怕行動，逆位可看自我設限或把選項看得太窄；但不能單靠一張牌決定結果。",
    tags: ["寶劍八", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "寶劍八感情代表什麼？", answer: "多半可看害怕表態、被關係困住與不敢選擇，但不能直接判定關係結果。" },
      { question: "寶劍八逆位怎麼看？", answer: "常見是自我設限或把選項看得太窄，仍要搭配問題和牌陣位置。" },
      { question: "寶劍八工作怎麼看？", answer: "可放在壓力框架、職場卡住與行動障礙裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-SWORDS-10",
    section: "tarot",
    slug: "ten-of-swords-meaning",
    primaryKeyword: "寶劍十",
    secondaryKeywords: ["寶劍十感情", "寶劍十工作", "寶劍十逆位"],
    title: "寶劍十意思：正位、逆位、感情與工作怎麼看",
    description: "寶劍十常和結束、痛到谷底和重新整理有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "寶劍十提醒結束、痛到谷底和重新整理，逆位可看把結束拖長或沉在受害感；但不能單靠一張牌決定結果。",
    tags: ["寶劍十", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "寶劍十感情代表什麼？", answer: "多半可看關係低點、分開後整理與重新站起來，但不能直接判定關係結果。" },
      { question: "寶劍十逆位怎麼看？", answer: "常見是把結束拖長或沉在受害感，仍要搭配問題和牌陣位置。" },
      { question: "寶劍十工作怎麼看？", answer: "可放在專案收尾、失敗復盤與止損調整裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-SWORDS-PAGE",
    section: "tarot",
    slug: "page-of-swords-meaning",
    primaryKeyword: "寶劍侍者",
    secondaryKeywords: ["寶劍侍者感情", "寶劍侍者工作", "寶劍侍者逆位"],
    title: "寶劍侍者意思：正位、逆位、感情與工作怎麼看",
    description: "寶劍侍者常和觀察、試探和訊息敏感有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "寶劍侍者提醒觀察、試探和訊息敏感，逆位可看多疑、嘴快或資訊未確認；但不能單靠一張牌決定結果。",
    tags: ["寶劍侍者", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "寶劍侍者感情代表什麼？", answer: "多半可看偷偷觀察、訊息試探與溝通敏感，但不能直接判定關係結果。" },
      { question: "寶劍侍者逆位怎麼看？", answer: "常見是多疑、嘴快或資訊未確認，仍要搭配問題和牌陣位置。" },
      { question: "寶劍侍者工作怎麼看？", answer: "可放在蒐集資訊、提問測試與新人學習裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-SWORDS-KNIGHT",
    section: "tarot",
    slug: "knight-of-swords-meaning",
    primaryKeyword: "寶劍騎士",
    secondaryKeywords: ["寶劍騎士感情", "寶劍騎士工作", "寶劍騎士逆位"],
    title: "寶劍騎士意思：正位、逆位、感情與工作怎麼看",
    description: "寶劍騎士常和急著說清、衝突溝通和快速行動有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "寶劍騎士提醒急著說清、衝突溝通和快速行動，逆位可看太衝、太利或忽略感受；但不能單靠一張牌決定結果。",
    tags: ["寶劍騎士", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "寶劍騎士感情代表什麼？", answer: "多半可看急著攤牌、說話刺耳與情緒反應，但不能直接判定關係結果。" },
      { question: "寶劍騎士逆位怎麼看？", answer: "常見是太衝、太利或忽略感受，仍要搭配問題和牌陣位置。" },
      { question: "寶劍騎士工作怎麼看？", answer: "可放在快速決策、強勢溝通與風險控管裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-SWORDS-QUEEN",
    section: "tarot",
    slug: "queen-of-swords-meaning",
    primaryKeyword: "寶劍皇后",
    secondaryKeywords: ["寶劍皇后感情", "寶劍皇后工作", "寶劍皇后逆位"],
    title: "寶劍皇后意思：正位、逆位、感情與工作怎麼看",
    description: "寶劍皇后常和界線、清醒和理性防衛有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "寶劍皇后提醒界線、清醒和理性防衛，逆位可看過度冷硬或不讓自己有感受；但不能單靠一張牌決定結果。",
    tags: ["寶劍皇后", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "寶劍皇后感情代表什麼？", answer: "多半可看清楚界線、看清關係與保護自己，但不能直接判定關係結果。" },
      { question: "寶劍皇后逆位怎麼看？", answer: "常見是過度冷硬或不讓自己有感受，仍要搭配問題和牌陣位置。" },
      { question: "寶劍皇后工作怎麼看？", answer: "可放在專業判斷、制度界線與客觀溝通裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-SWORDS-KING",
    section: "tarot",
    slug: "king-of-swords-meaning",
    primaryKeyword: "寶劍國王",
    secondaryKeywords: ["寶劍國王感情", "寶劍國王工作", "寶劍國王逆位"],
    title: "寶劍國王意思：正位、逆位、感情與工作怎麼看",
    description: "寶劍國王常和判斷、規則和冷靜決策有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "寶劍國王提醒判斷、規則和冷靜決策，逆位可看冷漠、控制話語權或只講原則；但不能單靠一張牌決定結果。",
    tags: ["寶劍國王", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "寶劍國王感情代表什麼？", answer: "多半可看理性評估、關係規則與溝通責任，但不能直接判定關係結果。" },
      { question: "寶劍國王逆位怎麼看？", answer: "常見是冷漠、控制話語權或只講原則，仍要搭配問題和牌陣位置。" },
      { question: "寶劍國王工作怎麼看？", answer: "可放在制度決策、管理判斷與清楚標準裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-PENTACLES-01",
    section: "tarot",
    slug: "ace-of-pentacles-meaning",
    primaryKeyword: "錢幣一",
    secondaryKeywords: ["錢幣一感情", "錢幣一工作", "錢幣一逆位"],
    title: "錢幣一意思：正位、逆位、感情與工作怎麼看",
    description: "錢幣一常和新的實際機會、落地開始和安全感有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "錢幣一提醒新的實際機會、落地開始和安全感，逆位可看機會未成熟或準備不足；但不能單靠一張牌決定結果。",
    tags: ["錢幣一", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "錢幣一感情代表什麼？", answer: "多半可看關係落地、穩定互動與現實條件，但不能直接判定關係結果。" },
      { question: "錢幣一逆位怎麼看？", answer: "常見是機會未成熟或準備不足，仍要搭配問題和牌陣位置。" },
      { question: "錢幣一工作怎麼看？", answer: "可放在新職務、新專案與具體起點裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-PENTACLES-02",
    section: "tarot",
    slug: "two-of-pentacles-meaning",
    primaryKeyword: "錢幣二",
    secondaryKeywords: ["錢幣二感情", "錢幣二工作", "錢幣二逆位"],
    title: "錢幣二意思：正位、逆位、感情與工作怎麼看",
    description: "錢幣二常和平衡、分配和忙亂中的選擇有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "錢幣二提醒平衡、分配和忙亂中的選擇，逆位可看兩邊都想顧或節奏失控；但不能單靠一張牌決定結果。",
    tags: ["錢幣二", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "錢幣二感情代表什麼？", answer: "多半可看時間分配、關係優先順序與不穩定感，但不能直接判定關係結果。" },
      { question: "錢幣二逆位怎麼看？", answer: "常見是兩邊都想顧或節奏失控，仍要搭配問題和牌陣位置。" },
      { question: "錢幣二工作怎麼看？", answer: "可放在多工壓力、排程協調與取捨裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-PENTACLES-03",
    section: "tarot",
    slug: "three-of-pentacles-meaning",
    primaryKeyword: "錢幣三",
    secondaryKeywords: ["錢幣三感情", "錢幣三工作", "錢幣三逆位"],
    title: "錢幣三意思：正位、逆位、感情與工作怎麼看",
    description: "錢幣三常和合作、技能和被看見有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "錢幣三提醒合作、技能和被看見，逆位可看合作不順或標準沒對齊；但不能單靠一張牌決定結果。",
    tags: ["錢幣三", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "錢幣三感情代表什麼？", answer: "多半可看一起努力、關係分工與互相欣賞，但不能直接判定關係結果。" },
      { question: "錢幣三逆位怎麼看？", answer: "常見是合作不順或標準沒對齊，仍要搭配問題和牌陣位置。" },
      { question: "錢幣三工作怎麼看？", answer: "可放在團隊協作、專業累積與成果驗收裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-PENTACLES-04",
    section: "tarot",
    slug: "four-of-pentacles-meaning",
    primaryKeyword: "錢幣四",
    secondaryKeywords: ["錢幣四感情", "錢幣四工作", "錢幣四逆位"],
    title: "錢幣四意思：正位、逆位、感情與工作怎麼看",
    description: "錢幣四常和保守、控制和害怕失去有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "錢幣四提醒保守、控制和害怕失去，逆位可看抓太緊或安全感不足；但不能單靠一張牌決定結果。",
    tags: ["錢幣四", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "錢幣四感情代表什麼？", answer: "多半可看佔有慾、界線拉扯與信任壓力，但不能直接判定關係結果。" },
      { question: "錢幣四逆位怎麼看？", answer: "常見是抓太緊或安全感不足，仍要搭配問題和牌陣位置。" },
      { question: "錢幣四工作怎麼看？", answer: "可放在成本控管、保守策略與權限掌握裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-PENTACLES-06",
    section: "tarot",
    slug: "six-of-pentacles-meaning",
    primaryKeyword: "錢幣六",
    secondaryKeywords: ["錢幣六感情", "錢幣六工作", "錢幣六逆位"],
    title: "錢幣六意思：正位、逆位、感情與工作怎麼看",
    description: "錢幣六常和給予、互惠和權力不對等有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "錢幣六提醒給予、互惠和權力不對等，逆位可看單方付出或交換失衡；但不能單靠一張牌決定結果。",
    tags: ["錢幣六", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "錢幣六感情代表什麼？", answer: "多半可看付出是否對等、照顧和被照顧的位置，但不能直接判定關係結果。" },
      { question: "錢幣六逆位怎麼看？", answer: "常見是單方付出或交換失衡，仍要搭配問題和牌陣位置。" },
      { question: "錢幣六工作怎麼看？", answer: "可放在支援分配、資源交換與職場公平裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-PENTACLES-07",
    section: "tarot",
    slug: "seven-of-pentacles-meaning",
    primaryKeyword: "錢幣七",
    secondaryKeywords: ["錢幣七感情", "錢幣七工作", "錢幣七逆位"],
    title: "錢幣七意思：正位、逆位、感情與工作怎麼看",
    description: "錢幣七常和等待成果、投入是否值得和耐心有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "錢幣七提醒等待成果、投入是否值得和耐心，逆位可看看不到回報或拖延檢討；但不能單靠一張牌決定結果。",
    tags: ["錢幣七", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "錢幣七感情代表什麼？", answer: "多半可看長期等待、關係投入與耐心檢查，但不能直接判定關係結果。" },
      { question: "錢幣七逆位怎麼看？", answer: "常見是看不到回報或拖延檢討，仍要搭配問題和牌陣位置。" },
      { question: "錢幣七工作怎麼看？", answer: "可放在專案成效、績效回顧與長期投入裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-PENTACLES-08",
    section: "tarot",
    slug: "eight-of-pentacles-meaning",
    primaryKeyword: "錢幣八",
    secondaryKeywords: ["錢幣八感情", "錢幣八工作", "錢幣八逆位"],
    title: "錢幣八意思：正位、逆位、感情與工作怎麼看",
    description: "錢幣八常和練習、投入和把事情做實有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "錢幣八提醒練習、投入和把事情做實，逆位可看只顧細節或看不見關係需求；但不能單靠一張牌決定結果。",
    tags: ["錢幣八", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "錢幣八感情代表什麼？", answer: "多半可看用行動累積信任、磨合和穩定付出，但不能直接判定關係結果。" },
      { question: "錢幣八逆位怎麼看？", answer: "常見是只顧細節或看不見關係需求，仍要搭配問題和牌陣位置。" },
      { question: "錢幣八工作怎麼看？", answer: "可放在技能練習、品質要求與工作紀律裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-PENTACLES-09",
    section: "tarot",
    slug: "nine-of-pentacles-meaning",
    primaryKeyword: "錢幣九",
    secondaryKeywords: ["錢幣九感情", "錢幣九工作", "錢幣九逆位"],
    title: "錢幣九意思：正位、逆位、感情與工作怎麼看",
    description: "錢幣九常和獨立、安全感和自我價值有關；本文整理正位、逆位、感情與工作情境，不把單牌寫成個人結論。",
    answer: "錢幣九提醒獨立、安全感和自我價值，逆位可看太獨立或不願依靠別人；但不能單靠一張牌決定結果。",
    tags: ["錢幣九", "塔羅", "正位", "逆位", "感情", "工作"],
    faq: [
      { question: "錢幣九感情代表什麼？", answer: "多半可看獨處舒服、自我價值與關係自主，但不能直接判定關係結果。" },
      { question: "錢幣九逆位怎麼看？", answer: "常見是太獨立或不願依靠別人，仍要搭配問題和牌陣位置。" },
      { question: "錢幣九工作怎麼看？", answer: "可放在個人成果、專業身價與穩定節奏裡理解，但不等於工作結果已定。" },
    ],
  },
  {
    id: "TAROT-PENTACLES-10",
    section: "tarot",
    slug: "ten-of-pentacles-meaning",
    primaryKeyword: "錢幣十",
    secondaryKeywords: ["錢幣十感情", "錢幣十工作", "錢幣十逆位", "錢幣十牌面"],
    title: "錢幣十意思：牌面、正位、逆位、感情與工作怎麼看",
    description: "錢幣十牌面呈現家族、居所與跨世代累積，適合整理長期穩定和共同基礎；它無法確認婚姻、繼承或財務結果。",
    answer: "錢幣十關注長期累積、家族與共同基礎；正位偏向穩定成形，逆位則提醒制度、資源或家庭期待出現裂縫。",
    tags: ["錢幣十", "塔羅", "牌面", "正位", "逆位", "感情", "工作"],
    published: "2026-07-16",
    updated: "2026-07-16",
    faq: [
      { question: "錢幣十牌面有哪些重要象徵？", answer: "老人、伴侶、孩子、犬隻與城鎮拱門把焦點放在跨世代關係、歸屬和長期累積；象徵仍須配合提問解讀。" },
      { question: "錢幣十感情代表結婚嗎？", answer: "它可以帶出家庭整合、共同生活和長期承諾，但不能只靠單張牌判定會結婚。" },
      { question: "錢幣十逆位怎麼看？", answer: "可檢查家庭期待、共同資源或長期安排是否失衡，不宜直接解成破產或關係失敗。" },
    ],
  },
  {
    id: "TAROT-PENTACLES-PAGE",
    section: "tarot",
    slug: "page-of-pentacles-meaning",
    primaryKeyword: "錢幣侍者",
    secondaryKeywords: ["錢幣侍者感情", "錢幣侍者工作", "錢幣侍者逆位", "錢幣侍者牌面"],
    title: "錢幣侍者意思：牌面、正位、逆位、感情與工作怎麼看",
    description: "錢幣侍者牌面把注意力放在手中的錢幣與尚待耕作的土地，適合整理學習、提案和落地起點；它不代表成果已經到手。",
    answer: "錢幣侍者關注願意學、仔細看和開始實作；正位偏向務實起步，逆位則提醒分心、準備不足或計畫停在想像。",
    tags: ["錢幣侍者", "塔羅", "牌面", "正位", "逆位", "感情", "工作"],
    published: "2026-07-16",
    updated: "2026-07-16",
    faq: [
      { question: "錢幣侍者牌面在看什麼？", answer: "人物凝視手中錢幣，周圍是田地與遠山，常用來整理專注學習、評估資源和把想法帶到現實的起點。" },
      { question: "錢幣侍者感情代表新對象嗎？", answer: "可能對應謹慎認識或用小行動建立信任，但不能單靠這張牌確認新關係會發生。" },
      { question: "錢幣侍者逆位怎麼看？", answer: "可檢查是否只有想法、缺少練習，或承諾與實際投入不一致，而不是直接把人貼成不可靠。" },
    ],
  },
  {
    id: "TAROT-PENTACLES-KNIGHT",
    section: "tarot",
    slug: "knight-of-pentacles-meaning",
    primaryKeyword: "錢幣騎士",
    secondaryKeywords: ["錢幣騎士感情", "錢幣騎士工作", "錢幣騎士逆位", "錢幣騎士牌面"],
    title: "錢幣騎士意思：牌面、正位、逆位、感情與工作怎麼看",
    description: "錢幣騎士牌面中的黑馬停在田野前，騎士穩穩托住錢幣，適合整理責任、節奏與持續執行；它不能把等待直接換算成回報。",
    answer: "錢幣騎士關注穩定執行、責任與可持續節奏；正位偏向按部就班，逆位則提醒僵化、拖延或只剩例行公事。",
    tags: ["錢幣騎士", "塔羅", "牌面", "正位", "逆位", "感情", "工作"],
    published: "2026-07-16",
    updated: "2026-07-16",
    faq: [
      { question: "錢幣騎士的馬為什麼停著？", answer: "靜止的黑馬讓重點落在評估、耐心和穩定推進，不是沒有行動；仍要看現實中是否真的持續投入。" },
      { question: "錢幣騎士感情代表進展很慢嗎？", answer: "它常對應慢而穩的互動，但慢不等於承諾；要觀察回應、安排與責任是否持續。" },
      { question: "錢幣騎士逆位怎麼看？", answer: "可檢查穩定是否變成僵化、拖延或敷衍，也可能是過度工作讓關係與生活失去彈性。" },
    ],
  },
  {
    id: "TAROT-PENTACLES-QUEEN",
    section: "tarot",
    slug: "queen-of-pentacles-meaning",
    primaryKeyword: "錢幣皇后",
    secondaryKeywords: ["錢幣皇后感情", "錢幣皇后工作", "錢幣皇后逆位", "錢幣皇后牌面"],
    title: "錢幣皇后意思：牌面、正位、逆位、感情與工作怎麼看",
    description: "錢幣皇后牌面把照顧、資源和現實生活放在同一幅景象裡，適合整理支持與安全感；它不代表女性角色或財富結果已定。",
    answer: "錢幣皇后關注有能力照顧，也保有自己的生活基礎；正位偏向務實支持，逆位則提醒耗竭、控制或忽略自身需求。",
    tags: ["錢幣皇后", "塔羅", "牌面", "正位", "逆位", "感情", "工作"],
    published: "2026-07-16",
    updated: "2026-07-16",
    faq: [
      { question: "錢幣皇后牌面的兔子代表什麼？", answer: "兔子和繁茂植物常把視線帶向生命力、日常照料與感官世界；它是閱讀線索，不能據此判定懷孕或財富結果。" },
      { question: "錢幣皇后感情代表對方會照顧我嗎？", answer: "它可以提示務實支持與生活照料，但要看對方是否真的付出、尊重界線並共同承擔。" },
      { question: "錢幣皇后逆位怎麼看？", answer: "可檢查照顧是否變成過度付出、控制或耗竭，也要確認自己是否把所有人的需要都放在前面。" },
    ],
  },
  ...EXPANSION_50_ARTICLE_RECORDS,
  ...EXPANSION_50C_MBTI_ARTICLE_RECORDS,
  ...EXPANSION_50C_ASTRO_ARTICLE_RECORDS,
  ...EXPANSION_50C_FORTUNE_ARTICLE_RECORDS,
  ...EXPANSION_50D_MBTI_ARTICLE_RECORDS.map(withExpansion50DDate),
  ...EXPANSION_50D_ASTRO_ARTICLE_RECORDS.map(withExpansion50DDate),
  ...EXPANSION_50D_FORTUNE_ARTICLE_RECORDS.map(withExpansion50DDate),
  ...AGY_PROTOTYPE_V1_01_ARTICLE_RECORDS,
  ...AGY_MATRIX_BACKLOG_V1_01_ARTICLE_RECORDS,
  ...AGY_MATRIX_BACKLOG_V1_RETRY_01_ARTICLE_RECORDS,
  ...AGY_ASC_BATCH_02_01_ARTICLE_RECORDS,
  ...AGY_ASC_BATCH_02_MECHANICAL_REPAIR_01_ARTICLE_RECORDS,
];

function withExpansion50DDate(article) {
  const date = article.updated || article.published || article.date || "2026-07-16";
  return { ...article, published: date, updated: date };
}

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
  TAG_TAXONOMY_REGISTRY.forEach((rule) => {
    if (tagRuleMatches(raw, rule)) push(rule.canonicalLabel);
  });
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

function findTagTaxonomyRule(topicSlug = "") {
  return TAG_TAXONOMY_REGISTRY.find((rule) => rule.topicSlug === topicSlug) || null;
}

function tagRuleMatches(value, rule) {
  return (rule.matchPatterns || []).some((pattern) => new RegExp(pattern, "i").test(value));
}

function articleMatchesTopic(article, topic) {
  const labels = listPublicTagLabelsForArticle(article);
  const taxonomy = findTagTaxonomyRule(topic.slug);
  const managedLabels = uniqueValues([
    topic.label,
    ...(topic.aliases || []),
    taxonomy?.canonicalLabel,
  ]);
  return labels.some((label) => managedLabels.includes(label));
}

function enrichTopicRecord(topic) {
  const taxonomy = findTagTaxonomyRule(topic.slug);
  const articles = listArticleRecords().filter((article) => articleMatchesTopic(article, topic));
  const indexPolicy = taxonomy?.indexPolicy || TAG_TAXONOMY_POLICY.defaultIndexPolicy;
  const minArticles = TAG_TAXONOMY_POLICY.publicTopicMinArticles;
  const isGenerated = indexPolicy === "min_articles" && articles.length >= minArticles;
  return {
    ...topic,
    articleCount: articles.length,
    minArticles,
    taxonomyStatus: taxonomy ? "managed" : "unmanaged",
    canonicalLabel: taxonomy?.canonicalLabel || topic.label,
    indexPolicy,
    isGenerated,
    href: isGenerated ? `/topics/${topic.slug}` : "",
  };
}

export function listTagTaxonomyRecords() {
  return TAG_TAXONOMY_REGISTRY.map((rule) => {
    const topic = findTopicCandidate(rule.topicSlug);
    const enriched = topic ? enrichTopicRecord(topic) : null;
    return {
      ...rule,
      topicLabel: topic?.label || rule.canonicalLabel,
      articleCount: enriched?.articleCount || 0,
      minArticles: TAG_TAXONOMY_POLICY.publicTopicMinArticles,
      isGenerated: Boolean(enriched?.isGenerated),
      href: enriched?.href || "",
    };
  });
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
