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

export const LIFE_TOPIC_INTENTS = {
  love: {
    label: "感情",
    category: "relation",
  },
  career: {
    label: "事業",
    category: "career",
  },
  interpersonal: {
    label: "人際",
    category: "interpersonal",
  },
  wealth: {
    label: "財富",
    category: "wealth",
  },
  life: {
    label: "人生方向",
    category: "life",
  },
};

export const TOPIC_REGISTRY = {
  astro: {
    productTheme: "astro",
    topicIntent: "astro",
    label: "星座",
    description: "整理星座、星盤與運勢文章，先用白話回答搜尋問題，再補充適用情境與限制。",
    seoDescription: "Pantheon 星座文章主頁，整理星座、星盤、感情運勢與人生主題的繁體中文解釋。",
    primaryKeyword: "星座",
    requiredTags: ["星座", "星盤", "運勢"],
  },
  astrology: {
    productTheme: "astro",
    topicIntent: "astro",
    label: "星座",
    description: "整理星座、星盤與運勢文章，先用白話回答搜尋問題，再補充適用情境與限制。",
    seoDescription: "Pantheon 星座文章主頁，整理星座、星盤、感情運勢與人生主題的繁體中文解釋。",
    primaryKeyword: "星座",
    requiredTags: ["星座", "星盤", "運勢"],
  },
  bazi: {
    productTheme: "fortune",
    topicIntent: "bazi",
    label: "八字",
    description: "整理八字、命盤與出生年月日時相關概念，保留公開文章與個人化解讀的邊界。",
    seoDescription: "Pantheon 八字文章主頁，整理八字是什麼、命盤怎麼看與常見命理概念。",
    primaryKeyword: "八字是什麼",
    requiredTags: ["八字", "命盤", "出生年月日時"],
  },
  career: {
    productTheme: "fortune",
    topicIntent: "career",
    label: "事業",
    description: "整理事業、工作節奏與職涯選擇相關文章，聚焦可理解、可延伸的公開知識。",
    seoDescription: "Pantheon 事業文章主頁，整理事業運勢、工作模式與職涯選擇的繁體中文內容。",
    primaryKeyword: "事業運勢",
    requiredTags: ["事業", "工作", "職涯"],
  },
  interpersonal: {
    productTheme: "personality",
    topicIntent: "interpersonal",
    label: "人際",
    description: "整理人際關係、互動界線與溝通模式文章，先釐清情境，再連到人格、命盤與塔羅脈絡。",
    seoDescription: "Pantheon 人際文章主頁，整理人際關係、互動界線、溝通模式與自我理解內容。",
    primaryKeyword: "人際關係",
    requiredTags: ["人際", "關係界線", "溝通模式"],
  },
  life: {
    productTheme: "fortune",
    topicIntent: "life",
    label: "人生方向",
    description: "整理人生方向、自我理解與選擇節奏相關文章，協助讀者先釐清問題。",
    seoDescription: "Pantheon 人生方向文章主頁，整理自我理解、選擇節奏與人生主題內容。",
    primaryKeyword: "人生方向",
    requiredTags: ["人生方向", "自我理解", "選擇"],
  },
  mbti: {
    productTheme: "personality",
    topicIntent: "mbti",
    label: "人格",
    description: "整理 MBTI、16 型人格與 Pantheon 64 分支人格文章，說明能看什麼與不能代表什麼。",
    seoDescription: "Pantheon 人格文章主頁，整理 MBTI 是什麼、16 型人格與 64 分支人格解析。",
    primaryKeyword: "MBTI 人格",
    requiredTags: ["MBTI", "16 型人格", "64 分支人格"],
  },
  relation: {
    productTheme: "tarot",
    topicIntent: "love",
    label: "感情",
    description: "整理感情、關係互動與相處模式文章，先回答問題，再連到人格、塔羅與命盤脈絡。",
    seoDescription: "Pantheon 感情文章主頁，整理感情塔羅、人格相處與關係問題的繁體中文內容。",
    primaryKeyword: "感情塔羅",
    requiredTags: ["感情", "關係", "相處模式"],
  },
  tarot: {
    productTheme: "tarot",
    topicIntent: "tarot",
    label: "塔羅",
    description: "整理塔羅牌義、正逆位與提問方式，建立可搜尋、可內鏈的牌義內容庫。",
    seoDescription: "Pantheon 塔羅文章主頁，整理塔羅牌意思、正位逆位與感情工作牌義。",
    primaryKeyword: "塔羅牌意思",
    requiredTags: ["塔羅", "塔羅牌意思", "正位逆位"],
  },
  wealth: {
    productTheme: "fortune",
    topicIntent: "wealth",
    label: "財富",
    description: "整理財富、資源節奏與金錢觀相關文章，不提供投資建議或財務承諾。",
    seoDescription: "Pantheon 財富文章主頁，整理財富運勢、資源節奏與金錢觀內容。",
    primaryKeyword: "財富運勢",
    requiredTags: ["財富", "資源", "金錢觀"],
  },
  ziwei: {
    productTheme: "fortune",
    topicIntent: "ziwei",
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
    category: "mbti",
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
    category: "mbti",
    slug: "16-personalities",
    primaryKeyword: "16 型人格",
    secondaryKeywords: ["MBTI 是什麼", "MBTI 人格", "人格特質"],
    title: "16 型人格完整整理：每一型的特質、感情、工作與人際",
    description: "16 型人格把 MBTI 四組偏好組合成不同類型，適合作為理解特質、感情、工作與人際的入口。",
    answer: "16 型人格能快速整理常見偏好差異，但它只是入口；同一型裡仍然會因情境、壓力與個人經驗而不同。",
    tags: ["人格類型", "人際", "工作"],
  },
  {
    id: "TAROT-M00",
    category: "tarot",
    slug: "fool-card-meaning",
    primaryKeyword: "愚者牌意思",
    secondaryKeywords: ["塔羅牌意思", "愚者牌正位", "愚者牌逆位"],
    title: "愚者牌意思：正位、逆位、感情與工作怎麼看",
    description: "愚者牌常指向開始、探索與未知，也提醒讀者分辨自由、衝動與準備程度。",
    answer: "愚者牌通常代表新的開始與未知旅程；正位偏向開放與探索，逆位則需要留意衝動、逃避或準備不足。",
    tags: ["大阿爾克那", "牌義", "感情塔羅", "工作塔羅"],
  },
  {
    id: "CHART-BASE-02",
    category: "bazi",
    slug: "bazi-meaning",
    primaryKeyword: "八字是什麼",
    secondaryKeywords: ["命盤是什麼", "出生年月日時", "八字命盤"],
    title: "八字是什麼？出生年月日時怎麼看人生節奏",
    description: "八字用出生年月日時組成命盤語言，適合理解節奏與傾向，不應被當成單一命運答案。",
    answer: "八字是把出生年月日時轉成干支組合的命理系統，常用來討論節奏、傾向與關係，不代表固定命運。",
    tags: ["命盤", "干支", "人生節奏"],
  },
  {
    id: "ASTRO-LOVE-01",
    category: "astro",
    slug: "love-forecast",
    primaryKeyword: "星座感情運勢",
    secondaryKeywords: ["星座感情", "感情運勢", "星盤感情"],
    title: "星座感情運勢怎麼看？先分清太陽、月亮與上升",
    description: "星座感情運勢適合作為關係觀察入口，但需要分清太陽、月亮、上升與實際相處情境。",
    answer: "星座感情運勢可以先看關係裡的表達、安全感與互動節奏，但不能直接替你判斷某段關係一定會怎樣。",
    tags: ["星座感情", "感情", "月亮星座"],
  },
];

export function listTopicRecords() {
  return Object.entries(TOPIC_REGISTRY).map(([slug, topic]) => ({ slug, ...topic }));
}

export function listArticleRecords() {
  return ARTICLE_REGISTRY.map((article) => enforceArticlePolicy(article, getTopicRecord(article.category)));
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
    articleId: article.id || `${article.category}/${article.slug}`,
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

  listTopicRecords().forEach((topic) => {
    const topicId = `topic:${topic.slug}`;
    addNode({
      id: topicId,
      kind: "topic",
      label: topic.label,
      keyword: topic.primaryKeyword,
    });
    topic.requiredTags.forEach((tag) => {
      const tagId = `tag:${tag}`;
      addNode({ id: tagId, kind: "tag", label: tag });
      addLink(topicId, tagId, "requires_tag");
    });
  });

  listArticleRecords().forEach((article) => {
    const articleId = `article:${article.category}/${article.slug}`;
    const topicId = `topic:${article.category}`;
    addNode({
      id: articleId,
      kind: "article",
      label: article.title,
      keyword: article.primaryKeyword,
      url: `/articles/${article.category}/${article.slug}`,
    });
    addLink(topicId, articleId, "contains_article");
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

export function getTopicRecord(category = "") {
  return TOPIC_REGISTRY[category] || null;
}

export function getProductThemeRecord(productTheme = "fortune") {
  return PRODUCT_THEME_REGISTRY[productTheme] || PRODUCT_THEME_REGISTRY.fortune;
}

export function getArticleRecord(category = "", slug = "") {
  const record = ARTICLE_REGISTRY.find((article) => article.category === category && article.slug === slug);
  return record ? enforceArticlePolicy(record, getTopicRecord(category)) : null;
}

export function enforceArticlePolicy(article, topic = null) {
  const productTheme = article?.productTheme || topic?.productTheme || "fortune";
  const topicIntent = article?.topicIntent || topic?.topicIntent || article?.category || "";
  const keywords = uniqueList([
    article?.primaryKeyword,
    ...(article?.secondaryKeywords || []),
    topic?.primaryKeyword,
  ]);
  const tags = uniqueList([
    ...GLOBAL_ARTICLE_POLICY.requiredTags,
    ...GLOBAL_ARTICLE_POLICY.requiredKeywordTags,
    ...(topic?.requiredTags || []),
    ...(article?.tags || []),
    ...keywords,
  ]);
  return {
    ...article,
    topicDescription: topic?.description || "",
    topicSeoDescription: topic?.seoDescription || topic?.description || "",
    productTheme,
    topicIntent,
    keywords,
    tags,
  };
}

export function fallbackTopicLabel(category = "") {
  return getTopicRecord(category)?.label || humanizeSlug(category) || "文章";
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
