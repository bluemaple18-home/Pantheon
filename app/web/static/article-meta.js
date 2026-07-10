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
        "比較健康的用法，是用 MBTI 找出你常見的反應模式，再回頭檢查現實情境。不要只看四個字母就認定自己只能做某種工作、只能愛某種人，或會有固定命運。",
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
        "最常見的問題，是把類型當成身份標籤。像 INTJ 不代表冷漠，INFP 不代表脆弱，ENFP 不代表三分鐘熱度。類型描述的是偏好，不是固定人格。",
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
        "合理用法是把結果當成討論工具：它可以幫你描述工作偏好、溝通方式、壓力來源和關係需求。它不能證明你適合或不適合某個人，也無法承諾你會成為某種樣子。",
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
        "這不代表 INTJ 冷漠，也不代表每個 INTJ 都適合當領導者。INTJ 只是偏好模式，不是一個人的全部人格。",
      ],
    },
    {
      heading: "INTJ 在感情和人際裡常見什麼模式？",
      paragraphs: [
        "在感情裡，INTJ 常常需要時間確認關係是否有長期價值。他們未必擅長即時表達情緒，但通常會用規劃、承諾和解決問題來表示在意。",
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
        "INFJ 稀有不代表比較優越，也不代表神秘。它只是指出一種偏好：更常從整體脈絡、關係感受和內在價值來理解世界。",
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
      heading: "正位和逆位等於好壞嗎？",
      paragraphs: [
        "正位和逆位不是單純的好壞。正位通常表示能量比較順、比較容易表現出牌的核心意義；逆位可能代表阻塞、過度、延遲，或需要換角度看。",
        "例如一張牌在感情、工作和人生方向裡的語氣可能不同。不能只看到某張牌就說會分手、會成功或會失敗。",
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
        "逆位未必比較壞，正位也未必就是好。重點是這張牌在你的問題裡提醒什麼，而不是只看牌是否倒過來。",
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
        "在感情裡，愚者牌可能代表新關係、重新開始，或對未知關係的好奇。但它無法承諾穩定，也無法替對方確認是否準備好承諾。",
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
    faq: buildArticleFaq(route, article, productTheme),
    relatedLinks: buildRelatedLinks(article, managedArticle, productTheme),
    cta: buildArticleCta(article, productTheme),
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
  if (customBody) return enrichArticleBody(article, productTheme, managedArticle, customBody);
  const primary = article.primaryKeyword || article.title;
  const related = [primary, ...(article.secondaryKeywords || [])].slice(0, 4).join("、");
  const tagText = (article.originalTags?.length ? article.originalTags : managedArticle.tags).slice(0, 4).join("、");
  return enrichArticleBody(article, productTheme, managedArticle, [
    {
      heading: buildDefinitionHeading(primary),
      paragraphs: [
        article.answer,
        article.description,
      ],
    },
    buildFallbackAngleSection(article, productTheme, primary, related),
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
  ]);
}

function enrichArticleBody(article, productTheme, managedArticle, customBody) {
  const [opening, ...rest] = customBody;
  return [
    opening,
    buildSearchIntentSection(article, productTheme),
    ...rest,
    buildScenarioSection(article, productTheme),
    buildRelatedReadingSection(article, productTheme),
    buildNextStepSection(article, productTheme, managedArticle),
  ];
}

function buildFallbackAngleSection(article, productTheme, primary, related) {
  if (article.product === "personality") {
    return {
      heading: "先看偏好，不急著貼標籤",
      paragraphs: [
        `閱讀 ${primary} 時，重點不是把人固定成某一型，而是看它能不能幫你說清楚偏好、壓力反應和互動節奏。`,
        `如果你是從「${related}」這類搜尋進來，建議先分清楚你想理解的是人格偏好、關係互動、工作合作，還是只是想找一個身份名稱。`,
      ],
    };
  }
  if (article.product === "tarot") {
    return {
      heading: "先把牌義放回提問",
      paragraphs: [
        `閱讀 ${primary} 時，不要只把牌義翻成好壞結果。塔羅文章更適合幫你看見問題裡的狀態、阻力和下一步提醒。`,
        `如果你是從「${related}」這類搜尋進來，先確認你問的是單張牌義、正逆位語氣、感情互動，還是工作與人生方向裡的短期卡點。`,
      ],
    };
  }
  if (article.product === "fortune") {
    return {
      heading: "先分清系統、觀察點和問題",
      paragraphs: [
        `閱讀 ${primary} 時，先看它屬於命盤、八字、紫微宮位還是人生主題。不同系統的語言不能直接混成同一句結論。`,
        `如果你是從「${related}」這類搜尋進來，建議先確認自己要查的是概念、宮位意義、長期節奏，還是想把它套回感情、事業或財富問題。`,
        "這樣讀會比較慢一點，但能避免把單一名詞誤讀成命書結論，也比較容易知道下一篇該補哪個背景。",
      ],
    };
  }
  if (article.product === "astro") {
    return {
      heading: "先分清落點，再談情境",
      paragraphs: [
        `閱讀 ${primary} 時，先分清太陽、月亮、上升或整張星盤各自在看什麼。單一落點只能提供一個角度，不是完整答案。`,
        `如果你是從「${related}」這類搜尋進來，建議先確認你想理解的是個性語言、情緒安全感、關係互動，還是人生方向裡的節奏感。`,
        "星盤文章最有用的地方，是把不同落點分工說清楚；讀者才不會把一個星座詞直接套成感情或人生判斷。",
      ],
    };
  }
  return {
    heading: `${productTheme.label}文章先處理哪一層？`,
    paragraphs: [
      `閱讀 ${primary} 時，先把它當成理解問題的入口，而不是最後答案。`,
      `如果你是從「${related}」這類搜尋進來，建議先確認你要問的是概念定義、使用方式、關係判斷，還是想把它套到自己的情境。`,
    ],
  };
}

function buildSearchIntentSection(article, productTheme) {
  const primary = article.primaryKeyword || article.title;
  const related = [primary, ...(article.secondaryKeywords || [])].slice(0, 4).join("、");
  return {
    heading: buildSearchIntentHeading(article, primary),
    paragraphs: [
      `搜尋「${primary}」的人，多半不是只想背一個定義，而是想知道這個概念能不能解釋自己正在遇到的狀況。可以先把問題分成三層：名詞本身是什麼、它能看哪些生活情境、它不能直接替你判斷什麼。`,
      `如果你是從「${related}」這類關鍵字進來，建議先不要急著把結果套到自己身上。先確認你要找的是自我理解、關係互動、工作節奏，還是只是想知道某個詞在網路上常被怎麼使用。`,
      `Pantheon 的公開文章會先把通用意思說清楚，再把限制講出來。這樣讀者可以拿到可搜尋、可引用的答案，但不會被推向沒有根據的個人結論。`,
    ],
  };
}

function buildSearchIntentHeading(article, primary) {
  const topic = cleanFaqTopic(primary);
  if (article.product === "personality" && /^[A-Z]{4}$/.test(topic)) return `查「${primary}」時，先別急著套標籤`;
  if (article.product === "personality") return `查「${primary}」時，先看它能解哪種問題`;
  if (article.product === "tarot") return `查「${primary}」時，不只是在背牌義`;
  if (article.product === "fortune") return `查「${primary}」時，先分清是哪個觀察點`;
  if (article.product === "astro") return `查「${primary}」時，別只看單一星座`;
  return `查「${primary}」時，先問自己想解哪一層`;
}

function buildScenarioSection(article, productTheme) {
  if (article.product === "personality") {
    return {
      heading: "感情、工作、人際各看哪一層？",
      paragraphs: [
        "放到感情裡，人格文章適合看相處偏好、溝通節奏和安全感來源。它可以提醒你為什麼有些互動特別消耗，或為什麼你會在某種關係裡反覆卡住，但不能直接判定兩個人合不合。",
        "放到工作裡，人格可以整理你偏好的決策方式、資訊處理方式和合作節奏。這能幫你理解自己適合怎樣的環境，也能幫你把需求說清楚，而不是把職涯選擇交給四個字母。",
        "放到人際與人生方向裡，人格比較像一張反應模式地圖。它能幫你看見慣性，但不能替你決定要不要離職、分手、轉換跑道或做任何重大人生選擇。",
      ],
    };
  }
  if (article.product === "tarot") {
    return {
      heading: "牌義進入感情或工作題時，會改變什麼？",
      paragraphs: [
        "放到感情裡，塔羅牌義適合整理當下互動狀態、期待落差和下一步可以注意的盲點。它可以幫你把問題問清楚，但不能替對方發言，也不能承諾關係結果。",
        "放到工作裡，塔羅比較適合看短期卡點、資源是否到位、行動是否清楚。它不是職涯承諾，也不是投資或財務建議；真正的選擇仍要回到能力、環境、時間和風險。",
        "放到人生方向裡，單張牌可以提供一個反思角度，牌陣則能把選項、阻力和提醒整理得更清楚。它提醒你看見問題，但不替你做重大人生決策。",
      ],
    };
  }
  if (article.product === "fortune") {
    return {
      heading: "感情、事業與財富題，命盤各自看哪一層？",
      paragraphs: [
        "放到感情裡，命盤文章適合整理長期關係課題、互動模式和安全感來源，但不能只用單一宮位或星曜判定一段關係。",
        "放到事業與財富裡，命盤可以協助讀者理解資源節奏、工作傾向和選擇壓力。它不是投資建議，也不能承諾收入、升遷或創業結果。",
        "放到人生方向裡，命盤比較適合看階段主題和反覆出現的課題。真正的選擇仍要回到現實條件、個人資料和當下問題。",
      ],
    };
  }
  if (article.product === "astro") {
    return {
      heading: "太陽、月亮、上升不能混成同一個答案",
      paragraphs: [
        "放到感情裡，星座與星盤文章適合整理情緒、安全感和互動節奏，但不能只靠太陽星座判斷一段關係。",
        "放到人際裡，上升、月亮和星盤落點可以幫讀者描述自己如何被看見、如何感到安全，以及在互動中容易出現的反應。",
        "放到人生方向裡，星盤比較像一張傾向地圖。它能幫你整理主題和提醒，但不替你決定未來，也不把星座寫成固定命運。",
      ],
    };
  }
  return {
    heading: "五大情境裡，先分清問題層次",
    paragraphs: [
      `${productTheme.label}文章可以協助整理感情、事業、人際、財富和人生方向的共通問題。公開內容只說明概念和限制，不把單一訊號寫成完整人生判斷。`,
      "如果問題牽涉金錢、健康、法律或重大風險，文章只能當作背景知識，不能取代專業意見或你自己的資料判斷。",
    ],
  };
}

function buildNextStepSection(article, productTheme, managedArticle) {
  const productEntry = getProductEntry(productTheme.label);
  const intentEntry = getIntentEntry(article, managedArticle);
  return {
    heading: buildNextStepHeading(article, productTheme),
    paragraphs: [
      `如果你只是想理解「${article.primaryKeyword}」這個概念，讀到這裡已經足夠。公開文章的任務是幫你建立語言、釐清情境和知道限制，不會把通用知識包裝成你的個人答案。`,
      `如果你想把它放回自己的狀況裡，可以先選一個入口：${productEntry}；如果你已經有明確問題，再往 ${intentEntry} 這類五大主題小報告整理。`,
      "比較好的順序是：先把問題寫清楚，再選工具，再看結果能不能回到現實情境。不要把任何一篇文章、單一人格類型或單張牌，直接當成最後判斷，也不要省略自己的限制條件。",
    ],
  };
}

function buildNextStepHeading(article, productTheme) {
  if (article.product === "personality") return "什麼時候需要回到自己的互動經驗？";
  if (article.product === "tarot") return "什麼時候該從牌義進到抽牌？";
  if (article.product === "fortune") return "什麼時候需要完整資料，而不是只看單點？";
  if (article.product === "astro") return "什麼時候需要看整張星盤？";
  return `什麼時候需要把${productTheme.label}放回個人情境？`;
}

function buildRelatedReadingSection(article, productTheme) {
  if (article.product === "personality") {
    return {
      heading: "人格文章不要只讀單一類型",
      paragraphs: [
        "讀人格文章時，建議不要只停在單一類型。你可以先讀 MBTI 是什麼，再看 16 型人格的整體架構，最後回到某一型在感情、工作和人際裡的表現。這樣比較不會把一個類型描述誤讀成固定身份。",
        "如果你正在處理關係或職場問題，也可以跨讀塔羅和命盤文章。人格看反應模式，塔羅看當下互動盲點，命盤看長期課題；三者分工不同，不需要互相取代。",
      ],
    };
  }
  if (article.product === "tarot") {
    return {
      heading: "牌義、逆位和情境要分開讀",
      paragraphs: [
        "讀塔羅文章時，建議先理解 78 張牌的基本牌義，再看正位逆位，最後才回到單張牌在感情、工作和人生方向裡的語氣。這樣比較不會只靠一個關鍵字解讀整個牌陣。",
        "如果問題牽涉某個人的反應模式，可以搭配人格文章一起看；如果問題牽涉長期節奏，可以再看命盤或人生方向入口。公開文章負責建立脈絡，不替任何工具製造權威感。",
        "看到比較緊繃的牌時，也不要急著把它翻成壞結果。先回到問題本身：它是在提醒溝通、資源、時機、界線，還是提醒你需要換一種問法。",
      ],
    };
  }
  if (article.product === "fortune") {
    return {
      heading: "命盤文章建議照層次讀",
      paragraphs: [
        "讀命盤文章時，可以先看命盤是什麼，再分別閱讀八字、紫微、命宮、夫妻宮和財帛宮。先建立共同語言，再回到自己真正想問的情境。",
        "如果問題牽涉感情、事業、財富或人生方向，可以跨讀人格、塔羅和星座文章。命盤看長期課題，其他工具則補上當下互動、反應模式和情緒節奏。",
        "看到某個宮位或星曜時，也要避免只取單點解讀。比較穩的讀法，是把它放回完整命盤、時間節奏和讀者當下的問題裡一起看，再確認這個判斷能否回到現實行動。",
      ],
    };
  }
  if (article.product === "astro") {
    return {
      heading: "星座文章先分清落點",
      paragraphs: [
        "讀星座文章時，可以先看星盤是什麼，再看上升星座和月亮星座。太陽、月亮和上升各自說明不同層次，不適合只抓一個落點下結論。",
        "如果你是從感情或人生方向問題進來，可以搭配人格與塔羅文章一起讀。星盤整理情緒和安全感，其他工具補上互動模式與當下選項。",
        "看到某個星座落點時，也要記得它只是整張星盤的一部分。公開文章能提供語言和方向，但不能把單一落點寫成固定人生劇本，也不能替讀者做最後選擇。",
      ],
    };
  }
  return {
    heading: "下一篇應該補哪一層？",
    paragraphs: [
      `讀${productTheme.label}文章時，可以先看產品線入口，再回到同分類文章補概念，最後用五大情境入口整理自己的問題。`,
      "延伸閱讀不是為了堆連結，而是讓讀者知道下一篇要解決哪一層問題：定義、情境、限制，還是個人化入口。",
      "如果你已經有一個具體問題，先把情境寫成一句話，再選文章或工具。這能避免把通用內容誤讀成個人判斷。",
    ],
  };
}

function buildFallbackFaq(route, article, productTheme) {
  const primary = article?.primaryKeyword || route.title || productTheme.label;
  const topic = cleanFaqTopic(primary);
  const definitionQuestion = /[？?]$/.test(primary) || primary.includes("是什麼")
    ? buildDefinitionHeading(primary)
    : `${primary}是什麼？`;
  return [
    {
      question: definitionQuestion,
      answer: article?.answer || `${primary} 是理解${productTheme.label}主題的入口，適合先看定義、適用情境與限制。`,
    },
    {
      question: buildUseQuestion(article, productTheme, topic),
      answer: buildUseAnswer(article, productTheme, topic),
    },
    {
      question: buildMistakeQuestion(article, productTheme, topic),
      answer: buildMistakeAnswer(article, productTheme, topic),
    },
  ];
}

function buildArticleFaq(route, article, productTheme) {
  const base = article?.faq?.length ? article.faq : buildFallbackFaq(route, article, productTheme);
  const primary = article?.primaryKeyword || route.title || productTheme.label;
  const topic = cleanFaqTopic(primary);
  return uniqueFaq([
    ...base,
    {
      question: buildLimitQuestion(article, productTheme, topic),
      answer: buildLimitAnswer(article, productTheme, topic),
    },
    {
      question: `想看自己的狀況，應該從哪個入口開始？`,
      answer: buildEntryAnswer(article, productTheme),
    },
  ]).slice(0, 5);
}

function uniqueFaq(items = []) {
  const seen = new Set();
  return items.filter((item) => {
    if (!item?.question || seen.has(item.question)) return false;
    seen.add(item.question);
    return true;
  });
}

function buildUseQuestion(article, productTheme, topic) {
  const subject = formatInlineTopic(topic);
  if (article?.product === "personality") return `讀${subject}時，應該先看哪一層？`;
  if (article?.product === "tarot") return `${topic}在不同問題裡會一樣嗎？`;
  if (article?.product === "fortune") return `看${subject}時，為什麼不能只看單點？`;
  if (article?.product === "astro") return `${topic}要和哪些星盤資訊一起看？`;
  return `${productTheme.label}文章適合先解決什麼問題？`;
}

function buildUseAnswer(article, productTheme, topic) {
  const prefix = formatFaqTopicPrefix(topic);
  if (article?.product === "personality") return `先看${prefix}描述的偏好和壓力反應，再對照真實互動；不要只把類型名稱當成身份標籤。`;
  if (article?.product === "tarot") return "不會完全一樣。同一張牌放在感情、工作或人生方向裡，會因問題和牌陣位置而有不同語氣。";
  if (article?.product === "fortune") return `${prefix}通常只是命盤或命理系統中的一個觀察點，需要搭配其他資料和當下問題一起看。`;
  if (article?.product === "astro") return `${prefix}最好搭配太陽、月亮、上升或完整星盤理解，避免把單一落點寫成完整人格。`;
  return `${productTheme.label}文章適合先建立背景知識，再依照具體問題判斷下一步閱讀。`;
}

function buildMistakeQuestion(article, productTheme, topic) {
  const subject = formatInlineTopic(topic);
  if (article?.product === "personality") return `最容易把${subject}誤會成什麼？`;
  if (article?.product === "tarot") return `看${subject}時，最容易問錯什麼？`;
  if (article?.product === "fortune") return `${topic}最常被過度解讀在哪裡？`;
  if (article?.product === "astro") return `${topic}最容易被簡化成什麼？`;
  return `讀${productTheme.label}文章時，最該避免什麼？`;
}

function buildMistakeAnswer(article, productTheme, topic) {
  const prefix = formatFaqTopicPrefix(topic);
  if (article?.product === "personality") return `最常見的誤會，是把${prefix}當成固定人格或感情答案；它比較適合用來整理偏好，不適合替人下定論。`;
  if (article?.product === "tarot") return "最容易問成「會不會一定發生」。比較好的問法，是問目前卡在哪裡、自己能看見什麼、下一步如何更清楚。";
  if (article?.product === "fortune") return `最常被過度解讀成固定命運。${prefix}可以提供語言和角度，但不能離開完整資料和現實情境。`;
  if (article?.product === "astro") return `最容易被簡化成單一個性描述。${prefix}只能說明一部分，不能取代完整星盤和實際相處。`;
  return `最該避免把通用${productTheme.label}知識直接套成個人結論。`;
}

function buildLimitQuestion(article, productTheme, topic) {
  const subject = formatInlineTopic(topic);
  if (article?.product === "personality") return `哪些情況不適合用${subject}下結論？`;
  if (article?.product === "tarot") return `可以用${subject}直接判斷結果嗎？`;
  if (article?.product === "fortune") return `什麼時候需要完整資料，而不是只看${subject}？`;
  if (article?.product === "astro") return `可以只靠${subject}判斷一個人嗎？`;
  return `${productTheme.label}文章不能替你判斷什麼？`;
}

function buildLimitAnswer(article, productTheme, topic) {
  if (article?.product === "personality") return `${formatFaqTopicPrefix(topic)}只能整理常見偏好，不能取代心理診斷，也不能單獨判定感情、工作或人生結果。`;
  if (article?.product === "tarot") return `${formatFaqTopicPrefix(topic)}只能提供牌義和情境提醒，不能替對方下結論，也不能承諾復合、成功或最終結果。`;
  return `${formatFaqTopicPrefix(topic)}只能當成理解${productTheme.label}的入口，不能替代個人資料、具體問題與專業判斷。`;
}

function buildEntryAnswer(article, productTheme) {
  if (article?.product === "personality") return "如果想看自己的反應模式，可以先做 64 分支人格測試；如果已有明確感情、事業或人際問題，再用五大主題小報告整理。";
  if (article?.product === "tarot") return "如果只是想理解牌義，讀文章即可；如果想整理當下問題，可以先抽一張塔羅，再把問題放回感情、事業或人生方向入口。";
  return `可以先從${productTheme.label}入口建立背景，再依照感情、事業、人際、財富或人生方向選擇更具體的問題。`;
}

function buildRelatedLinks(article, managedArticle, productTheme) {
  if (!article) return [];
  const currentPath = `/articles/${article.product}/${article.slug}`;
  const productLinks = [
    { label: `${productTheme.label}文章入口`, href: `/articles/${article.product}`, kind: "產品線入口" },
    { label: "感情文章入口", href: "/articles/intents/love", kind: "五大情境" },
    { label: "事業文章入口", href: "/articles/intents/career", kind: "五大情境" },
    { label: "人際文章入口", href: "/articles/intents/interpersonal", kind: "五大情境" },
    { label: "人生方向文章入口", href: "/articles/intents/life", kind: "五大情境" },
  ];
  const sameProduct = getRelatedArticleLinks(article.product)
    .filter((item) => item.href !== currentPath)
    .slice(0, 3);
  const crossProduct = article.product === "personality"
    ? [
      { label: "塔羅牌意思總覽", href: "/articles/tarot/tarot-card-meanings", kind: "跨分類" },
      { label: "人生方向文章入口", href: "/articles/intents/life", kind: "跨分類" },
    ]
    : [
      { label: "MBTI 是什麼", href: "/articles/personality/mbti-meaning", kind: "跨分類" },
      { label: "人際文章入口", href: "/articles/intents/interpersonal", kind: "跨分類" },
    ];
  return uniqueLinks([...productLinks, ...sameProduct, ...crossProduct]).slice(0, 8);
}

function getRelatedArticleLinks(product) {
  if (product === "personality") {
    return [
      { label: "MBTI 是什麼", href: "/articles/personality/mbti-meaning", kind: "同分類" },
      { label: "16 型人格完整整理", href: "/articles/personality/16-personalities", kind: "同分類" },
      { label: "MBTI 測驗前先知道", href: "/articles/personality/mbti-test", kind: "同分類" },
      { label: "MBTI 準嗎", href: "/articles/personality/mbti-accuracy", kind: "同分類" },
      { label: "INTJ 是什麼", href: "/articles/personality/intj-meaning", kind: "同分類" },
      { label: "INFP 是什麼", href: "/articles/personality/infp-meaning", kind: "同分類" },
    ];
  }
  if (product === "tarot") {
    return [
      { label: "塔羅牌意思總覽", href: "/articles/tarot/tarot-card-meanings", kind: "同分類" },
      { label: "塔羅牌正位逆位", href: "/articles/tarot/upright-reversed", kind: "同分類" },
      { label: "愚者牌意思", href: "/articles/tarot/fool-card-meaning", kind: "同分類" },
      { label: "魔術師牌意思", href: "/articles/tarot/magician-card-meaning", kind: "同分類" },
      { label: "戀人牌意思", href: "/articles/tarot/lovers-card-meaning", kind: "同分類" },
      { label: "死神牌意思", href: "/articles/tarot/death-card-meaning", kind: "同分類" },
    ];
  }
  if (product === "fortune") {
    return [
      { label: "命盤是什麼", href: "/articles/fortune/birth-chart-meaning", kind: "同分類" },
      { label: "八字是什麼", href: "/articles/fortune/bazi-meaning", kind: "同分類" },
      { label: "紫微斗數是什麼", href: "/articles/fortune/ziwei-doushu-meaning", kind: "同分類" },
      { label: "命宮是什麼", href: "/articles/fortune/ming-gong-meaning", kind: "同分類" },
      { label: "夫妻宮是什麼", href: "/articles/fortune/spouse-palace-meaning", kind: "同分類" },
      { label: "財帛宮是什麼", href: "/articles/fortune/wealth-palace-meaning", kind: "同分類" },
    ];
  }
  if (product === "astro") {
    return [
      { label: "星盤是什麼", href: "/articles/astro/birth-chart-astrology", kind: "同分類" },
      { label: "上升星座是什麼", href: "/articles/astro/ascendant-sign-meaning", kind: "同分類" },
      { label: "月亮星座是什麼", href: "/articles/astro/moon-sign-meaning", kind: "同分類" },
      { label: "感情塔羅怎麼問", href: "/articles/tarot/love-tarot-questions", kind: "跨分類" },
    ];
  }
  return [];
}

function uniqueLinks(items = []) {
  const seen = new Set();
  return items.filter((item) => {
    if (!item?.href || seen.has(item.href)) return false;
    seen.add(item.href);
    return true;
  });
}

function buildArticleCta(article, productTheme) {
  if (!article) return null;
  const productLinks = (() => {
    if (article.product === "personality") return [
      { label: "看人格熱門文章", href: "/articles/personality" },
      { label: "看人際主題小報告", href: "/articles/intents/interpersonal" },
      { label: "整理人生方向問題", href: "/articles/intents/life" },
    ];
    if (article.product === "tarot") return [
      { label: "看塔羅熱門文章", href: "/articles/tarot" },
      { label: "看感情主題小報告", href: "/articles/intents/love" },
      { label: "整理事業主題問題", href: "/articles/intents/career" },
    ];
    if (article.product === "fortune") return [
      { label: "看命盤熱門文章", href: "/articles/fortune" },
      { label: "看事業主題小報告", href: "/articles/intents/career" },
      { label: "整理財富主題問題", href: "/articles/intents/wealth" },
    ];
    return [
      { label: "看星盤與星座入口", href: "/articles/astro" },
      { label: "整理感情主題問題", href: "/articles/intents/love" },
      { label: "整理人生方向問題", href: "/articles/intents/life" },
    ];
  })();
  return {
    title: "下一步",
    body: `如果你只是想理解這個概念，這篇文章已經足夠。${getProductBoundarySentence(productTheme.label)}如果你想知道它放到自己的狀況裡代表什麼，可以先選一個入口。`,
    links: productLinks,
  };
}

function getProductEntry(label) {
  if (label === "人格") return "做 64 分支人格測試，看你的反應模式";
  if (label === "塔羅") return "抽一張塔羅，看當下問題";
  if (label === "命盤") return "看命盤簡介，了解長期底色";
  if (label === "星座") return "看星盤或星座落點，整理情緒和安全感";
  return "先選一個最接近你問題的 Pantheon 入口";
}

function getIntentEntry(article, managedArticle) {
  const tags = [...(article?.originalTags || []), ...(managedArticle?.tags || [])].join(" ");
  if (/感情|關係/.test(tags)) return "感情";
  if (/事業|工作|職涯/.test(tags)) return "事業";
  if (/人際|溝通/.test(tags)) return "人際";
  if (/財富|金錢|資源/.test(tags)) return "財富";
  return "人生方向";
}

function getProductBoundarySentence(label) {
  if (label === "人格") return "類型只能說明常見偏好，不是你的完整人格。";
  if (label === "塔羅") return "單張牌只能提供一個反思角度，不是預言。";
  if (label === "命盤") return "單一宮位只能說明一個觀察角度。";
  if (label === "星座") return "單一星座落點只能說明一部分。";
  return "公開文章只能講通用意思。";
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
  if (article.product === "fortune") return "命盤、八字或紫微適合整理人生主題與節奏，不適合被說成固定命運或結果承諾。";
  return `${productTheme.label}文章適合建立概念，但不能替代個人化判斷。`;
}

function humanizeSlug(value = "") {
  return decodeURIComponent(value)
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}
