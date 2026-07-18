const DATE = "2026-07-19";

const SIGN_PROFILES = {
  aries: ["牡羊", "直接啟動、快速回應與自主空間", "臨時收到新任務時先動手做出第一版，再回頭補齊資訊", "對方改變約定時立刻表態，之後才發現語氣比原意更強"],
  taurus: ["金牛", "穩定累積、感官確認與可預期節奏", "比較工作選項時先核對薪資、通勤與日常是否能長期維持", "共同生活出現變動時，需要把成本與替代方案攤開才願意調整"],
  gemini: ["雙子", "資訊交換、觀點切換與保持好奇", "會議遇到模糊需求時連續提問，把不同版本整理成可比較的清單", "關係進入日常後主動安排新活動，確認彼此是否仍有話可談"],
  cancer: ["巨蟹", "情境記憶、照顧反應與歸屬需求", "家人一句話勾起舊經驗時，先分辨眼前事件和過去記憶的差別", "朋友低潮時準備餐點與陪伴，也需要確認自己是否有餘裕承接"],
  leo: ["獅子", "創造表達、被具體看見與自尊界線", "作品完成後希望收到具體回饋，而不是只有一句籠統的稱讚", "團隊公開討論成果時，主動說明自己的貢獻也替合作夥伴留位置"],
  virgo: ["處女", "細節分析、改善流程與可執行標準", "交付前把缺漏逐項核對，並標示哪些錯誤真的會影響結果", "伴侶談到不滿時先問具體事件，避免把改善建議變成全面挑剔"],
  libra: ["天秤", "比較觀點、協調互惠與關係公平", "兩個方案各有利弊時先列共同標準，再決定哪些取捨可以接受", "朋友發生衝突時協助翻譯立場，也保留自己不介入的界線"],
  scorpio: ["天蠍", "深度查核、信任建立與資源界線", "合作涉及敏感資料時先確認權限、責任與退出條件再投入", "關係出現疑問時回看持續行為，不用一次坦白交換永久信任"],
  sagittarius: ["射手", "跨域探索、意義連結與行動空間", "對工作感到停滯時安排短期課程或訪談，先測試新的方向", "旅行或進修計畫很吸引人時，也把預算、期限與原有責任列入"],
  capricorn: ["摩羯", "結構規劃、長期承擔與成果節點", "接下長期專案前先拆里程碑、資源與最晚停止條件", "習慣先處理責任再談感受時，刻意安排一次不以交付為目的的對話"],
  aquarius: ["水瓶", "獨立觀察、系統改造與群體位置", "團隊沿用低效流程時提出替代方案，並先找小範圍驗證", "需要獨處整理想法時清楚說明回應時間，避免距離被誤讀成冷淡"],
  pisces: ["雙魚", "意象聯想、共感接收與能量界線", "環境氣氛緊繃時先記錄身體反應，再確認哪些情緒屬於自己", "創作或助人工作投入過深時安排休息，避免共感變成無限承擔"],
};

const PLANET_PROFILES = {
  venus: {
    label: "金星",
    focus: "喜歡方式、價值選擇與關係中的交換",
    question: "哪些互動讓人感到被重視，以及彼此如何協調親近與界線",
    action: "挑一段最近的互動，分開記錄示好、回應、沒有說出口的期待與下一次可確認的界線",
    boundary: "不能判定誰會愛上誰、是否忠誠或一段關係能維持多久",
  },
  mercury: {
    label: "水星",
    focus: "資訊處理、表達順序與學習溝通偏好",
    question: "自己如何接收資訊、形成想法，又在哪種溝通節奏下容易誤解",
    action: "回顧一次溝通落差，把收到的資訊、自己的推論、實際回應與待確認問題分成四欄",
    boundary: "不能判定智力高低、學習成敗，也不能替不尊重的表達方式開脫",
  },
  mars: {
    label: "火星",
    focus: "行動動機、競爭方式與衝突升高的節點",
    question: "壓力出現時會直接推進、持續忍耐、改換路線，還是先保護重要界線",
    action: "選一件正在推進的事，寫下啟動條件、可用資源、衝突訊號與需要暫停的門檻",
    boundary: "不能判定暴力傾向、慾望強弱或行動必然成功，也不能合理化傷害",
  },
  jupiter: {
    label: "木星",
    focus: "成長信念、機會判斷與擴張時的成本",
    question: "在哪些情境願意嘗試、分享或承擔風險，又可能在哪裡高估資源",
    action: "把想擴張的方向縮成一個兩週實驗，先設定投入上限、觀察指標與退出條件",
    boundary: "不能預測好運、中獎、升遷或財富結果，也不能取代風險評估",
  },
  saturn: {
    label: "土星",
    focus: "責任壓力、限制感與需要時間建立的能力",
    question: "哪個領域容易害怕犯錯、延後行動或承擔過量責任，以及界線如何形成",
    action: "把一項長期壓力拆成固定頻率的小責任，寫清楚完成標準、求助對象與重新評估日期",
    boundary: "不能宣告懲罰、厄運或命定困難，也不能把過度負荷寫成應該忍耐",
  },
};

const TOPIC_SETS = {
  venus: ["libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"],
  mercury: Object.keys(SIGN_PROFILES),
  mars: Object.keys(SIGN_PROFILES),
  jupiter: Object.keys(SIGN_PROFILES),
  saturn: Object.keys(SIGN_PROFILES).slice(0, 8),
};

const topics = [];
let serialNumber = 65;
for (const [planetKey, signKeys] of Object.entries(TOPIC_SETS)) {
  const planet = PLANET_PROFILES[planetKey];
  for (const signKey of signKeys) {
    const [signLabel, trait, sceneOne, sceneTwo] = SIGN_PROFILES[signKey];
    const label = `${planet.label}${signLabel}`;
    topics.push({
      ...planet,
      id: `${planetKey.toUpperCase()}-${signKey.toUpperCase()}`,
      serial: `astrology-${String(serialNumber).padStart(4, "0")}`,
      slug: `${planetKey}-${signKey}-meaning`,
      label,
      signLabel,
      trait,
      sceneOne,
      sceneTwo,
    });
    serialNumber += 1;
  }
}

function makeFaq(topic) {
  return [
    {
      question: `${topic.label}可以看完整人格嗎？`,
      answer: `不可以。${topic.label}只提供${topic.focus}的觀察角度，仍要合看完整星盤、生活經驗與實際行為。`,
    },
    {
      question: `${topic.label}在感情中有固定表現嗎？`,
      answer: `沒有固定表現。可以先觀察${topic.trait}是否在特定互動中反覆出現，再直接確認當事人的需要。`,
    },
    {
      question: `讀到${topic.label}後可以做什麼？`,
      answer: `${topic.action}，用新證據修正原本的占星假設。`,
    },
    {
      question: `${topic.label}能預測結果嗎？`,
      answer: `不能。它${topic.boundary}；重要決定仍需核對現實條件與專業意見。`,
    },
  ];
}

function makeBody(topic) {
  return [
    {
      heading: `${topic.label}先看哪個核心問題`,
      paragraphs: [
        `${topic.label}在占星裡常被用來整理${topic.focus}。${topic.label}提供的是一個提問角度，不是替人貼標籤。閱讀${topic.label}時，可以先問：${topic.question}？把${topic.label}問題放回最近一件真實事件，會比只背星座形容詞更容易看見差異。`,
        `${topic.label}帶出的${topic.trait}，可能在不同環境呈現不同做法。${topic.label}的表達有人會直接說明，有人要等到安全感足夠才表態，也有人完全不符合通用描述。解讀${topic.label}時，先保留反例，不要把一次反應寫成永久個性。`,
      ],
    },
    {
      heading: `${topic.label}放進兩個生活場景`,
      paragraphs: [
        `在${topic.label}的第一個場景中，${topic.sceneOne}。若這讓你想到${topic.label}，先記錄事件發生前有哪些資訊、當事人實際做了什麼，以及後果是否符合原本預期。連續行為和時間順序，比一句「因為我是${topic.label}」更能說明問題。`,
        `在${topic.label}的第二個場景中，${topic.sceneTwo}。這時可以觀察${topic.label}所連結的${topic.trait}帶來的是幫助、壓力，還是兩者同時存在。若對${topic.label}的解讀不同，先把各自需要的回應、可接受界線與下一次確認時間說清楚。`,
      ],
    },
    {
      heading: `${topic.label}如何變成可驗證行動`,
      paragraphs: [
        `使用${topic.label}比較實際的方法是：${topic.action}。這個${topic.label}步驟不是用來證明占星永遠正確，而是產生可以回看的資料。完成${topic.label}紀錄後再問，原本的假設是否更清楚、是否出現反例，以及下一步成本是否仍在可承受範圍。`,
        `把${topic.label}放進關係時，要看雙方回應與界線；放進工作時，要看權責、資源和期限；放進人生選擇時，則要看風險與可撤回程度。${topic.label}跨場景可能呈現不同做法，環境和練習也會改變表現。`,
      ],
    },
    {
      heading: `${topic.label}不能代表什麼`,
      paragraphs: [
        `${topic.label}${topic.boundary}。單一${topic.label}也不能取代完整星盤、當事人的說法與長期可觀察行為。若${topic.label}解讀沒有交代資料、時間範圍、反例和限制，就不適合拿來做高成本決定。`,
        `讀完${topic.label}後，可以留下三件事：一個已確認的事實、一個仍待查證的推測，以及一個低風險行動。若${topic.label}問題涉及安全、健康、法律或重大財務風險，應優先尋求相應專業協助，不以占星文章代替判斷。`,
      ],
    },
  ];
}

export const EXPANSION_50E_ASTRO_ARTICLE_RECORDS = topics.map((topic) => ({
  id: `ASTRO-EXPANSION-50E-${topic.serial.slice(-4)}`,
  serial: topic.serial,
  slug: topic.slug,
  section: "astro",
  product: "astro",
  published: DATE,
  updated: DATE,
  primaryKeyword: topic.label,
  secondaryKeywords: [topic.focus, `${topic.label}感情`, `${topic.label}工作`],
  title: `${topic.label}是什麼？${topic.focus}怎麼看`,
  description: `${topic.label}可用來整理${topic.focus}，本文用兩個生活場景說明觀察與行動；單一落點不能判定完整人格、關係或事件結果。`,
  answer: `${topic.label}提供${topic.focus}的觀察角度，仍要用完整星盤、實際行為與現實條件核對。`,
  tags: ["星盤", topic.label, topic.signLabel, topic.label.slice(0, 2), "自我理解"],
  faq: makeFaq(topic),
}));

export const EXPANSION_50E_ASTRO_ARTICLE_BODY_LIBRARY = Object.fromEntries(
  topics.map((topic) => [topic.slug, makeBody(topic)]),
);
