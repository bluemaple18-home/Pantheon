import {
  enforceArticlePolicy,
  getArticleRecord,
  getArticleSectionRecord,
  getLifeIntentRecord,
  getProductThemeRecord,
} from "./article-registry.js";

const INTERNAL_DISPLAY_TAGS = new Set([
  "Pantheon",
  "繁體中文",
  "公開文章",
  "非個人化解讀",
  "SEO",
  "AEO",
  "GEO",
  "公開文章邊界",
]);

const ARTICLE_BODY_LIBRARY = {
  "mbti-meaning": [
    {
      heading: "MBTI 是什麼？",
      paragraphs: [
        "MBTI 是一套描述人格偏好的分類工具，常用四組傾向來理解一個人比較習慣怎麼取得能量、接收資訊、做決定和安排生活。它不是心理診斷，也不是用來判定一個人好壞的標籤。",
        "如果你第一次查 MBTI，可以先把它當成一張自我理解地圖：它能幫你整理溝通、工作和關係裡的習慣模式，但不能替你決定職涯、感情或人生結果。",
      ],
    },
    {
      heading: "16 型人格怎麼看？",
      paragraphs: [
        "16 型人格來自 E/I、S/N、T/F、J/P 四組偏好組合。例如有人偏外向互動，有人需要獨處充電；有人重視具體經驗，有人習慣先看可能性。這些差異可以幫你理解自己為什麼在某些情境特別順或特別卡。",
        "比較健康的用法，是用 MBTI 找出你常見的反應模式，再回頭檢查現實情境。不要只看四個字母就認定自己只能做某種工作、只能愛某種人，或一定會有某種命運。",
      ],
    },
    {
      heading: "MBTI 適合拿來做什麼？",
      paragraphs: [
        "MBTI 適合用在自我理解、團隊溝通、關係磨合和職涯偏好討論。它能提供一套比較容易開口的語言，讓你說清楚自己需要什麼、容易被什麼消耗、做決定時會卡在哪裡。",
        "MBTI 不適合拿來當診斷、不適合替別人貼永久標籤，也不適合拿來預測感情成敗。真正有用的不是類型名稱，而是你能不能把偏好放回具體情境裡觀察。",
      ],
    },
  ],
  "16-personalities": [
    {
      heading: "16 型人格是什麼？",
      paragraphs: [
        "16 型人格是把 MBTI 的四組偏好組合成 16 種常見類型，用來快速整理一個人在思考、感受、工作和人際裡的傾向。它比較像分類索引，不是人格的完整說明書。",
        "同一型的人仍然可能差很多，因為成長背景、壓力狀態、價值觀和生活經驗都會影響表現。類型可以當入口，但不能當結論。",
      ],
    },
    {
      heading: "每一型可以看哪些面向？",
      paragraphs: [
        "看 16 型人格時，可以先看四個面向：怎麼補充能量、怎麼吸收資訊、怎麼做判斷、怎麼安排生活。這比只背類型綽號更實用，也比較不容易變成刻板印象。",
        "放到感情、人際和工作裡，可以觀察一個人比較需要空間還是互動、偏好明確規則還是彈性探索、遇到衝突時重視效率還是關係感受。",
      ],
    },
    {
      heading: "怎麼避免把 16 型人格看歪？",
      paragraphs: [
        "最常見的問題，是把類型當成身份標籤。像 INTJ 不一定冷漠，INFP 不一定脆弱，ENFP 不一定三分鐘熱度。類型描述的是偏好，不是固定人格。",
        "比較好的讀法，是把每一型當成提問清單：我在什麼情境會像這個描述？什麼時候不像？哪些是偏好，哪些只是壓力下的反應？",
      ],
    },
  ],
  "mbti-test": [
    {
      heading: "MBTI 測驗能幫你看什麼？",
      paragraphs: [
        "MBTI 測驗可以幫你整理人格偏好，尤其是你在做決定、接收資訊、與人互動和安排生活時，通常會靠近哪一種模式。它適合作為自我理解的起點。",
        "測驗結果比較像一份當下狀態的回饋，不是永久身份。你的壓力、心情、題目理解方式，甚至近期工作和關係經驗，都可能影響答案。",
      ],
    },
    {
      heading: "為什麼不同 MBTI 測驗結果會不一樣？",
      paragraphs: [
        "不同測驗的題目設計、計分方式和翻譯語氣都不一樣，所以結果有落差很正常。尤其是偏好本來就接近中間的人，更容易在不同測驗中得到不同類型。",
        "如果你測出來的結果不穩，先不要急著找一個最像自己的標籤。你可以回頭看四組偏好各自的分數，找出真正穩定的傾向，以及容易受情境影響的部分。",
      ],
    },
    {
      heading: "MBTI 測驗結果怎麼用才合理？",
      paragraphs: [
        "合理用法是把結果當成討論工具：它可以幫你描述工作偏好、溝通方式、壓力來源和關係需求。它不能證明你適合或不適合某個人，也不能保證你會成為某種樣子。",
        "如果你想用 MBTI 做自我整理，建議搭配實際例子：最近一次衝突、一次工作決策、一次感情卡住的經驗。能對照現實的結果，才有參考價值。",
      ],
    },
  ],
  "mbti-accuracy": [
    {
      heading: "MBTI 準嗎？",
      paragraphs: [
        "MBTI 會讓人覺得準，通常是因為它描述的是常見偏好：有人習慣先想清楚再說，有人邊說邊整理；有人看重邏輯一致，有人更在意關係感受。這些描述很容易對上生活經驗。",
        "但 MBTI 不應被當成絕對準確的人格判定。它不是臨床診斷，也不能預測一個人的感情、工作和人生結果。它比較適合拿來整理問題，而不是直接下結論。",
      ],
    },
    {
      heading: "為什麼有人覺得 MBTI 很像？",
      paragraphs: [
        "很多人覺得 MBTI 很像，是因為類型文字抓到了自己長期的行為偏好。例如你可能一直知道自己需要安靜整理，或很容易在關係裡感受到別人的情緒，MBTI 只是給了這些經驗一組名字。",
        "這種命名有幫助，但也有風險。當一個人太依賴類型，他可能會把可以調整的習慣誤以為不能改，或把複雜的人際問題簡化成一句「因為我是某型」。",
      ],
    },
    {
      heading: "怎麼判斷 MBTI 對你有沒有用？",
      paragraphs: [
        "如果 MBTI 幫你說清楚自己的需求、改善溝通、看見壓力反應，它就是有用的。如果它讓你開始逃避改變、否定別人，或把自己困在標籤裡，它就被用錯了。",
        "真正值得留下的不是測驗結果本身，而是你從結果延伸出的觀察：我在哪些情境會這樣？哪些描述不符合我？我可以怎麼和別人說得更清楚？",
      ],
    },
  ],
  "intj-meaning": [
    {
      heading: "INTJ 是什麼？",
      paragraphs: [
        "INTJ 通常被描述為重視策略、結構和長期目標的人格類型。他們習慣先理解系統怎麼運作，再思考怎麼改進，比起臨場反應，更在意方向是否合理。",
        "這不代表 INTJ 一定冷漠，也不代表每個 INTJ 都適合當領導者。INTJ 只是偏好模式，不是一個人的全部人格。",
      ],
    },
    {
      heading: "INTJ 在感情和人際裡常見什麼模式？",
      paragraphs: [
        "在感情裡，INTJ 常常需要時間確認關係是否有長期價值。他們不一定擅長即時表達情緒，但通常會用規劃、承諾和解決問題來表示在意。",
        "在人際裡，INTJ 可能不喜歡過多寒暄，更在意對話是否有內容。這有時會被誤解成距離感，但很多時候只是他們需要更明確的交流目的。",
      ],
    },
    {
      heading: "INTJ 在工作裡適合怎麼理解？",
      paragraphs: [
        "INTJ 在工作上通常重視效率、架構和長期成果，適合處理需要分析、規劃和系統優化的任務。但如果環境充滿反覆溝通、臨時變動或不合理規則，也容易消耗他們。",
        "如果你是 INTJ，重點不是把自己包裝成完美策略家，而是練習把想法說得更可合作，讓別人知道你不是只挑問題，而是在找更穩的解法。",
      ],
    },
  ],
  "infp-meaning": [
    {
      heading: "INFP 是什麼？",
      paragraphs: [
        "INFP 通常被描述為重視價值感、真實關係和內在一致的人格類型。他們常常不是沒有想法，而是需要確認一件事是否符合自己的感受、信念和長期意義。",
        "INFP 不等於脆弱，也不等於不切實際。很多 INFP 對細節和現實其實很敏感，只是他們不喜歡把自己放進完全違背價值的框架裡。",
      ],
    },
    {
      heading: "INFP 在感情裡常見什麼模式？",
      paragraphs: [
        "在感情裡，INFP 往往重視真誠、理解和情緒安全感。他們可能需要比別人更多時間確認自己是否真的被看見，也可能因為太在意關係的意義而反覆思考。",
        "這種細膩是優點，但也可能讓 INFP 容易把沒說出口的期待放在心裡。關係要穩，不只需要感受，也需要把需求講清楚。",
      ],
    },
    {
      heading: "INFP 在工作和人生方向怎麼看？",
      paragraphs: [
        "INFP 做選擇時，常常會問這件事有沒有意義、能不能保留自己的完整感。單純用薪水、頭銜或外界期待推動他們，通常效果有限。",
        "比較適合 INFP 的方式，是把理想拆成可以執行的小步驟。不是每個夢都要一次到位，但每一步最好都能和真正重視的方向有關。",
      ],
    },
  ],
  "infj-meaning": [
    {
      heading: "INFJ 是什麼？",
      paragraphs: [
        "INFJ 通常被描述為重視洞察、理想和深層關係的人格類型。他們常會注意到別人沒有明說的情緒或模式，也容易思考一段關係或一個選擇背後的長期意義。",
        "INFJ 稀有不代表比較優越，也不代表一定神秘。它只是指出一種偏好：更常從整體脈絡、關係感受和內在價值來理解世界。",
      ],
    },
    {
      heading: "INFJ 在關係裡容易卡在哪裡？",
      paragraphs: [
        "INFJ 在關係裡常常很在意真誠和深度，如果只停留在表面互動，容易覺得消耗。可是他們也可能太早替別人理解、太慢替自己表達需求。",
        "健康的 INFJ 關係不是永遠理解別人，而是知道什麼時候要說清楚界線。你可以敏銳，但不需要負責消化所有人的情緒。",
      ],
    },
    {
      heading: "INFJ 怎麼看人生方向？",
      paragraphs: [
        "INFJ 很容易被有意義、有願景的方向吸引，但也可能因為理想太大而遲遲不開始。當現實和理想落差太大時，容易陷入自責或迷惘。",
        "比較實際的做法，是把理想拆成能驗證的小行動。先確認哪一部分真的重要，再決定要投入多少時間和資源。",
      ],
    },
  ],
  "enfp-meaning": [
    {
      heading: "ENFP 是什麼？",
      paragraphs: [
        "ENFP 通常被描述為重視可能性、連結和探索的人格類型。他們擅長從不同想法之間看到關聯，也容易被新的計畫、人和方向點燃熱情。",
        "ENFP 不等於三分鐘熱度。很多時候，他們不是沒有方向，而是需要找到足夠有生命力、能和人產生連結的方向。",
      ],
    },
    {
      heading: "ENFP 在關係裡常見什麼模式？",
      paragraphs: [
        "ENFP 在關係裡通常很重視互動感和真實交流。他們喜歡被理解，也喜歡看見對方更多可能性，因此常能帶動氣氛和對話。",
        "但 ENFP 也需要留意，熱情不等於承諾，理解別人不等於要替對方解決人生。關係要穩，仍然需要清楚的界線和節奏。",
      ],
    },
    {
      heading: "ENFP 在工作和人生方向怎麼看？",
      paragraphs: [
        "ENFP 通常適合需要創意、溝通、探索和連結的工作環境。太封閉、太重複、缺乏彈性的系統，容易讓他們很快失去能量。",
        "如果你是 ENFP，重點不是壓掉熱情，而是替熱情建立篩選機制。哪些想法值得做？哪些只是當下興奮？能分辨這件事，方向就會穩很多。",
      ],
    },
  ],
  "tarot-card-meanings": [
    {
      heading: "塔羅牌意思怎麼看？",
      paragraphs: [
        "塔羅牌意思是理解牌面象徵的入口。78 張牌分成大阿爾克那和小阿爾克那，大牌多半看人生主題與轉折，小牌更常落在情緒、行動、資源和日常情境。",
        "初學塔羅時，不需要一開始背完整牌義。先抓每張牌的核心畫面、關鍵情緒和常見提醒，再慢慢放進問題與牌陣裡理解。",
      ],
    },
    {
      heading: "正位和逆位一定代表好壞嗎？",
      paragraphs: [
        "正位和逆位不是單純的好壞。正位通常表示能量比較順、比較容易表現出牌的核心意義；逆位可能代表阻塞、過度、延遲，或需要換角度看。",
        "例如一張牌在感情、工作和人生方向裡的語氣可能不同。不能只看到某張牌就說一定會分手、一定成功或一定失敗。",
      ],
    },
    {
      heading: "塔羅牌義怎麼用在實際問題？",
      paragraphs: [
        "真正判讀塔羅時，要把牌義、牌陣位置、問題問法和當事人的狀態放在一起看。單張牌可以給提醒，但不能取代完整脈絡。",
        "比較好的問題不是「他會不會愛我一輩子」，而是「這段關係現在卡在哪裡」、「我能看見什麼盲點」、「下一步怎麼做比較清楚」。",
      ],
    },
  ],
  "upright-reversed": [
    {
      heading: "塔羅牌正位逆位是什麼？",
      paragraphs: [
        "塔羅牌正位逆位是同一張牌的兩種表現方式。正位常表示牌義比較順暢地出現，逆位則可能代表能量被壓住、過度表現、延遲發生，或需要回頭檢查。",
        "逆位不一定比較壞，正位也不一定就是好。重點是這張牌在你的問題裡提醒什麼，而不是只看牌是否倒過來。",
      ],
    },
    {
      heading: "正位逆位在感情和工作裡怎麼讀？",
      paragraphs: [
        "在感情問題裡，逆位常提醒溝通不順、期待落差、情緒沒有被看見，或關係裡某個力量沒有被好好使用。在工作問題裡，逆位可能是卡關、準備不足、資源沒有到位。",
        "但這些都需要搭配問題和牌陣位置。逆位不是恐嚇，也不是命令，它比較像提醒你：這件事目前哪裡不順？",
      ],
    },
    {
      heading: "初學者要不要使用逆位？",
      paragraphs: [
        "初學者可以先只讀正位，把每張牌的核心意思熟悉後，再加入逆位。否則一開始同時背正逆位，很容易變成機械式解釋。",
        "如果要使用逆位，可以先用三個方向判斷：這張牌的能量被阻塞了嗎？過度了嗎？還是需要用另一種方式表達？",
      ],
    },
  ],
  "fool-card-meaning": [
    {
      heading: "愚者牌意思是什麼？",
      paragraphs: [
        "愚者牌通常代表新的開始、未知旅程和願意踏出去的狀態。它不是什麼都不想，而是還沒被既有規則完全限制，願意用開放的心態接近新經驗。",
        "在占卜裡，愚者牌常提醒你看見可能性，但也要分辨自由和衝動。真正的開始需要勇氣，也需要基本準備。",
      ],
    },
    {
      heading: "愚者牌正位和逆位怎麼看？",
      paragraphs: [
        "愚者牌正位偏向開放、探索、出發和新的機會。它可能表示你正在進入一個還不確定結果的階段，但這個階段有學習和成長空間。",
        "愚者牌逆位則常提醒逃避、準備不足、衝動決定，或只是想離開現狀卻沒有想清楚下一步。逆位不是叫你不要開始，而是叫你看清風險。",
      ],
    },
    {
      heading: "愚者牌在感情和工作裡代表什麼？",
      paragraphs: [
        "在感情裡，愚者牌可能代表新關係、重新開始，或對未知關係的好奇。但它不保證穩定，也不保證對方已經準備好承諾。",
        "在工作裡，愚者牌可能指向新計畫、新職位或想轉換方向。它鼓勵探索，但也提醒你確認資源、時間和基本風險。",
      ],
    },
  ],
  "magician-card-meaning": [
    {
      heading: "魔術師牌意思是什麼？",
      paragraphs: [
        "魔術師牌通常代表資源、行動、創造力和把想法落地的能力。它提醒你手上已經有一些工具，關鍵在於能不能整合並開始使用。",
        "這張牌不是空想，而是啟動。它常出現在一個人需要把能力、資訊、人脈或機會轉成實際行動的時候。",
      ],
    },
    {
      heading: "魔術師牌正位和逆位怎麼看？",
      paragraphs: [
        "魔術師牌正位偏向掌握資源、開始行動、創造機會和有效表達。它表示事情不只停在想法層面，而是有機會被推進。",
        "魔術師牌逆位可能提醒空談、操控、準備不足或過度自信。你可能有工具，但還沒真正整合；也可能有人把話說得漂亮，實際行動卻跟不上。",
      ],
    },
    {
      heading: "魔術師牌在感情和事業裡怎麼看？",
      paragraphs: [
        "在感情裡，魔術師牌可能代表主動表達、創造互動機會，也可能提醒你分辨真誠行動和話術。在關係初期尤其要看對方是否說到做到。",
        "在事業裡，魔術師牌常是啟動專案、整合資源和展現能力的訊號。它適合問：我現在有哪些資源？下一步可以怎麼具體行動？",
      ],
    },
  ],
};

export function buildArticleContent(pathname, origin, defaults = {}) {
  const route = parseArticleRoute(pathname);
  const isLatestHub = !route.product && !route.slug && !route.intent;
  const intent = route.intent ? getLifeIntentRecord(route.intent) : null;
  const article = route.product && route.slug ? getArticleRecord(route.product, route.slug) : null;
  const section = article ? getArticleSectionRecord(article.section) : getArticleSectionRecord(route.product);
  const productThemeRecord = getProductThemeRecord(article?.product || route.product || section?.product);
  const canonicalPath = route.intent
    ? `/articles/intents/${route.intent}`
    : route.product && route.slug
      ? `/articles/${route.product}/${route.slug}`
      : route.product
        ? `/articles/${route.product}`
      : "/articles";
  const title = article?.title || route.title;
  const pageTitle = route.slug
    ? `${title} | Pantheon`
    : route.intent
      ? `${intent?.label || route.intentLabel}文章 | Pantheon`
      : route.product
      ? `${productThemeRecord.label}文章 | Pantheon`
      : "最新文章 | Pantheon";
  const description = buildDescription(route, article, section, intent, productThemeRecord);
  const updated = defaults.updated || new Date().toISOString().slice(0, 10);
  const author = defaults.author || "Pantheon 編輯部";
  const managedArticle = enforceArticlePolicy({
    section: article?.section || route.product,
    slug: route.slug,
    title,
    product: article?.product || route.product,
    primaryKeyword: article?.primaryKeyword || title,
    secondaryKeywords: article?.secondaryKeywords || [],
    tags: article?.tags || [],
  }, section);
  const productTheme = isLatestHub
    ? {
      label: "最新文章",
      glyph: "文",
      description: "Pantheon 最新文章入口，整理命盤、人格、塔羅、星座與人生方向主題。",
    }
    : getProductThemeRecord(managedArticle.productTheme);
  const displayTitle = route.slug
    ? title
    : route.intent
      ? `${intent?.label || route.intentLabel}文章`
      : route.product
        ? `${productTheme.label}文章`
        : "最新文章";
  return {
    title: displayTitle,
    pageTitle,
    description,
    canonicalPath,
    canonicalUrl: `${origin}${canonicalPath}`,
    product: managedArticle.product,
    productLabel: productTheme.label,
    productHref: route.product ? `/articles/${route.product}` : "/articles",
    section: managedArticle.section || "",
    productCrumb: route.product,
    productCrumbLabel: route.intent ? "搜尋意圖" : productTheme.label,
    slug: route.slug,
    author,
    updated,
    published: defaults.published || updated,
    sectionDescription: buildSectionDescription(route, section, intent, productTheme),
    productTheme: isLatestHub ? "latest" : managedArticle.productTheme,
    productThemeLabel: productTheme.label,
    productThemeGlyph: productTheme.glyph,
    productThemeDescription: productTheme.description,
    intent: route.intent || managedArticle.intent,
    keywords: managedArticle.keywords,
    tags: managedArticle.tags,
    displayTags: buildDisplayTags(article, managedArticle, productTheme),
    answer: article?.answer || buildAnswer(route),
    bodySections: buildBodySections(route, article, section, intent, productTheme, managedArticle),
    faq: article?.faq || buildFallbackFaq(route, article, productTheme),
  };
}

function buildDisplayTags(article, managedArticle, productTheme) {
  const source = article
    ? [
      article.primaryKeyword,
      ...(article.secondaryKeywords || []),
      ...(article.originalTags || []),
    ]
    : [
      managedArticle.primaryKeyword,
      productTheme.label,
      ...(managedArticle.originalTags || []),
    ];
  return uniqueList(source)
    .filter((tag) => tag && !INTERNAL_DISPLAY_TAGS.has(tag))
    .slice(0, 8);
}

function uniqueList(values = []) {
  const seen = new Set();
  return values
    .map((value) => String(value || "").trim())
    .filter((value) => {
      if (!value || seen.has(value)) return false;
      seen.add(value);
      return true;
    });
}

function parseArticleRoute(pathname) {
  const segments = pathname.split("/").filter(Boolean);
  const [, productOrScope = "", slug = ""] = segments;
  const isIntentHub = productOrScope === "intents";
  const intent = isIntentHub ? slug : "";
  const legacySection = isIntentHub ? null : getArticleSectionRecord(productOrScope);
  const product = isIntentHub ? "" : legacySection?.product || productOrScope;
  return {
    product,
    productLabel: getProductThemeRecord(product).label,
    requestedSection: legacySection ? productOrScope : "",
    slug: isIntentHub ? "" : slug,
    intent,
    intentLabel: intent ? getLifeIntentRecord(intent)?.label || humanizeSlug(intent) : "",
    title: humanizeSlug(slug) || "文章",
  };
}

function buildDescription(route, article, section, intent, productTheme) {
  if (route.slug && article?.description) return article.description;
  if (route.slug) return `${route.title}：Pantheon 以繁體中文整理${productTheme.label}主題，提供清楚摘要、背景脈絡與延伸閱讀。`;
  if (route.intent) return `Pantheon ${intent?.label || route.intentLabel}文章主題入口，整理相關問題、產品脈絡與延伸閱讀。`;
  if (route.product) return section?.seoDescription || `Pantheon ${productTheme.label}文章列表，整理基礎概念、常見問題與延伸閱讀。`;
  return "Pantheon 最新文章，整理命盤、人格、塔羅、星座與人生方向主題。";
}

function buildSectionDescription(route, section, intent, productTheme) {
  if (route.intent) return `${intent?.label || route.intentLabel}文章會作為搜尋意圖入口，再連回對應產品文章與工具。`;
  if (route.product && section?.description) return section.description;
  if (route.product) return `${productTheme.label}文章列表，整理基礎概念、常見問題與延伸閱讀。`;
  return "最新文章入口，集中整理命盤、人格、塔羅、星座與人生方向主題。";
}

function buildAnswer(route) {
  if (route.slug) return `${route.title} 的重點會先用短摘要回答，再補充適用情境、限制與下一步閱讀。`;
  if (route.intent) return `${route.intentLabel}文章會先整理搜尋者真正想解決的問題，再連到相關產品內容。`;
  if (route.product) return `${route.productLabel}文章會先整理核心概念，再連到相關主題與個人化工具。`;
  return "最新文章會把命盤、人格、塔羅、星座與人生方向主題整理成可搜尋、可引用、可延伸的內容。";
}

function buildBodySections(route, article, section, intent, productTheme, managedArticle) {
  if (route.slug && article) {
    return buildArticleBody(article, productTheme, managedArticle);
  }
  if (route.intent) {
    const label = intent?.label || route.intentLabel;
    return [
      {
        heading: `${label}文章先看什麼？`,
        paragraphs: [
          `${label}相關搜尋通常不是只想看一個名詞，而是想知道現在遇到的問題可以從哪些角度理解。這個入口會整理人格、塔羅、命盤與星盤中和${label}有關的文章。`,
          "公開文章適合先建立概念、看常見問題與限制；如果要做個人化判斷，仍需要回到具體資料與情境。",
        ],
      },
    ];
  }
  if (route.product) {
    return [
      {
        heading: `${productTheme.label}文章怎麼讀？`,
        paragraphs: [
          section?.description || `${productTheme.label}文章會先整理常見概念，再補充使用限制與延伸閱讀。`,
          `建議先從「${section?.primaryKeyword || productTheme.label}」開始，再依照你真正想解決的問題往下閱讀。`,
        ],
      },
    ];
  }
  return [
    {
      heading: "最新文章怎麼使用？",
      paragraphs: [
        "最新文章頁整理 Pantheon 已公開的命盤、人格、塔羅、星座與人生方向內容，適合先用搜尋問題找到一篇可讀答案。",
        "公開文章只處理通用概念、適用情境與限制，不直接替任何人的人生、感情或工作下結論。",
      ],
    },
  ];
}

function buildArticleBody(article, productTheme, managedArticle) {
  const customBody = ARTICLE_BODY_LIBRARY[article.slug];
  if (customBody) return customBody;
  const primary = article.primaryKeyword || article.title;
  const related = [primary, ...(article.secondaryKeywords || [])].slice(0, 4).join("、");
  const tagText = (article.originalTags?.length ? article.originalTags : managedArticle.tags).slice(0, 4).join("、");
  return [
    {
      heading: buildDefinitionHeading(primary),
      paragraphs: [
        article.answer,
        article.description,
      ],
    },
    {
      heading: `這篇文章會怎麼看 ${primary}？`,
      paragraphs: [
        `閱讀 ${primary} 時，先把它當成一個理解問題的入口，而不是最後答案。${productTheme.label}文章會先整理定義，再說明它通常能看什麼、不能直接代表什麼。`,
        `如果你是從「${related}」這類搜尋進來，建議先確認你要問的是概念定義、使用方式、關係判斷，還是想把它套到自己的情境。`,
      ],
    },
    {
      heading: "常見誤解",
      paragraphs: [
        buildMisunderstandingParagraph(article, productTheme),
        "公開文章可以幫你釐清語言與邏輯，但不應把單一名詞、牌義、宮位、星座或人格類型直接變成個人結論。",
      ],
    },
    {
      heading: "下一步可以讀什麼？",
      paragraphs: [
        tagText
          ? `你可以沿著 ${tagText} 這幾個主題繼續閱讀，先把相關概念串起來。`
          : `你可以沿著 ${productTheme.label} 的其他文章繼續閱讀，先把相關概念串起來。`,
        "如果你要的是個人化判斷，文章只能當作背景知識；真正套用到個人情境時，仍需要明確問題、資料與限制。",
      ],
    },
  ];
}

function buildFallbackFaq(route, article, productTheme) {
  const primary = article?.primaryKeyword || route.title || productTheme.label;
  const topic = cleanFaqTopic(primary);
  const topicQuestionPrefix = formatFaqTopicPrefix(topic);
  const topicInline = formatInlineTopic(topic);
  const definitionQuestion = /[？?]$/.test(primary) || primary.includes("是什麼")
    ? buildDefinitionHeading(primary)
    : `${primary}是什麼？`;
  return [
    {
      question: definitionQuestion,
      answer: article?.answer || `${primary} 是理解${productTheme.label}主題的入口，適合先看定義、適用情境與限制。`,
    },
    {
      question: `${topicQuestionPrefix}可以怎麼用？`,
      answer: `可以用來整理問題、建立背景知識和延伸閱讀，但不要直接把${topicInline}當成個人化結論。`,
    },
    {
      question: `${topicQuestionPrefix}不能代表什麼？`,
      answer: `${topicQuestionPrefix}不能單獨決定感情、工作或人生結果；真正判斷仍需要放回具體問題和情境。`,
    },
  ];
}

function cleanFaqTopic(primary) {
  return String(primary || "")
    .replace(/[？?]$/g, "")
    .replace(/\s*是什麼$/g, "")
    .trim();
}

function formatFaqTopicPrefix(topic) {
  return /^[A-Za-z0-9]+$/.test(topic) ? `${topic} ` : topic;
}

function formatInlineTopic(topic) {
  return /^[A-Za-z0-9]+$/.test(topic) ? ` ${topic} ` : topic;
}

function buildDefinitionHeading(primary) {
  if (/[？?]$/.test(primary)) return primary;
  if (primary.includes("是什麼")) return `${primary}？`;
  return `${primary}是什麼？`;
}

function buildMisunderstandingParagraph(article, productTheme) {
  if (article.product === "personality") return "人格類型適合描述偏好與互動模式，不適合拿來替一個人貼永久標籤，也不能取代心理診斷。";
  if (article.product === "tarot") return "塔羅牌義適合先理解象徵和提醒，但不能只看單張牌就斷定感情、工作或人生結果。";
  if (article.product === "astro") return "星盤與星座適合看傾向和主題，不能只用單一星座就推論一個人的完整樣貌。";
  if (article.product === "fortune") return "命盤、八字或紫微適合整理人生主題與節奏，不適合被說成固定命運或保證結果。";
  return `${productTheme.label}文章適合建立概念，但不能替代個人化判斷。`;
}

function humanizeSlug(value = "") {
  return decodeURIComponent(value)
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}
