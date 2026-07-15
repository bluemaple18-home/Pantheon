import {
  enforceArticlePolicy,
  getArticlePath,
  getArticleRecord,
  getArticleSectionRecord,
  getLifeIntentRecord,
  getProductThemeRecord,
  getTopicForLabel,
  getTopicRecord,
  listArticleRecords,
  listArticlesForTopic,
  listPublicTagLabelsForArticle,
} from "./article-registry.js?v=article-content-20260711-25";
import { SECOND_BATCH_ARTICLE_BODY_LIBRARY } from "./article-bodies-second-batch.js?v=article-content-20260711-25";
import { NEXT_30_ARTICLE_BODY_LIBRARY } from "./article-bodies-next-30.js?v=article-content-20260711-25";
import { SCALE_44_ARTICLE_BODY_LIBRARY } from "./article-bodies-scale-44.js?v=article-content-20260711-25";

const DEFAULT_ARTICLE_PUBLISHED_DATE = "2026-07-10";
const DEFAULT_ARTICLE_UPDATED_DATE = "2026-07-12";

const INTERNAL_DISPLAY_TAGS = new Set([
  "Pantheon",
  "繁體中文",
  "公開文章",
  "通用知識",
  "SEO",
  "AEO",
  "GEO",
  "公開文章邊界",
]);

const ARTICLE_BODY_LIBRARY = {
  ...SECOND_BATCH_ARTICLE_BODY_LIBRARY,
  ...NEXT_30_ARTICLE_BODY_LIBRARY,
  ...SCALE_44_ARTICLE_BODY_LIBRARY,
  "mbti-meaning": [
    {
      heading: "MBTI 是什麼？",
      paragraphs: [
        "MBTI 是一套描述人格偏好的分類工具，常用四組傾向來理解一個人比較習慣怎麼取得能量、接收資訊、做決定和安排生活。它可以整理偏好，不能取代專業評估，也不能用來判定一個人的好壞。",
        "例如你在會議裡總是先聽完再發言，或下班後需要獨處才恢復力氣，MBTI 可以幫你把這些反應說清楚。它不能替你決定職涯、感情或人生結果，真正有用的是回到具體互動裡觀察。",
      ],
    },
    {
      heading: "16 型人格怎麼看？",
      paragraphs: [
        "16 型人格來自 E/I、S/N、T/F、J/P 四組偏好組合。例如有人偏外向互動，有人需要獨處充電；有人重視具體經驗，有人習慣先看可能性。這些差異可以幫你理解自己為什麼在某些合作、約會或家庭溝通裡特別順或特別卡。",
        "比較健康的用法，是用 MBTI 找出你常見的反應模式，再回頭檢查現實情境。不要只看四個字母就認定自己只能做某種工作、只能愛某種人，或會有固定命運。",
      ],
    },
    {
      heading: "MBTI 適合拿來做什麼？",
      paragraphs: [
        "MBTI 適合用在自我理解、團隊溝通、關係磨合和職涯偏好討論。它能提供一套比較容易開口的語言，讓你說清楚自己需要什麼、容易被什麼消耗、做決定時會卡在哪裡。",
        "MBTI 不適合拿來當專業評估、不適合替別人貼永久標籤，也不適合拿來預測感情成敗。真正有用的不是類型名稱，而是你能不能把偏好放回具體情境裡觀察。",
      ],
    },
  ],
  "16-personalities": [
    {
      heading: "16 型人格是什麼？",
      paragraphs: [
        "16 型人格是把 MBTI 的四組偏好組合成 16 種常見類型，用來整理一個人在思考、感受、工作和人際裡的傾向。它比較像偏好索引，不是人格的完整說明書。",
        "同一型的人仍然可能差很多。兩個同樣是 INFP 的人，可能一個在關係裡很會表達，另一個遇到衝突就沉默；差異來自經驗、壓力、價值觀和環境。類型可以當起點，不能當結論。",
      ],
    },
    {
      heading: "每一型可以看哪些面向？",
      paragraphs: [
        "看 16 型人格時，可以先看四個面向：怎麼補充能量、怎麼吸收資訊、怎麼做判斷、怎麼安排生活。這比只背類型綽號更實用，也比較不容易變成刻板印象。",
        "放到感情、人際和工作裡，可以觀察一個人比較需要空間還是互動、偏好明確規則還是彈性探索、遇到衝突時先解決問題還是先安撫感受。這些都是可觀察的行為，不是固定命運。",
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
        "MBTI 測驗可以幫你整理人格偏好，尤其是你在做決定、接收資訊、與人互動和安排生活時，通常會靠近哪一種模式。它適合作為自我理解的起點，不適合直接當成專業評估。",
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
        "合理用法是把結果當成討論工具：它可以幫你描述工作偏好、溝通方式、壓力來源和關係需求。比如你發現自己開會後需要時間整理，就可以先說「我想一下再回覆」，而不是硬逼自己立刻表態。",
        "如果你想用 MBTI 做自我整理，建議搭配實際例子：最近一次衝突、一次工作決策、一次感情卡住的經驗。能對照現實的結果，才有參考價值。",
      ],
    },
  ],
  "mbti-accuracy": [
    {
      heading: "MBTI 準嗎？",
      paragraphs: [
        "MBTI 會讓人覺得準，通常是因為它描述的是常見偏好：有人習慣先想清楚再說，有人邊說邊整理；有人看重邏輯一致，有人更在意關係感受。這些描述很容易對上生活經驗。",
        "但 MBTI 不應被當成絕對準確的人格判定。它不是臨床工具，也不能預測一個人的感情、工作和人生結果。它比較適合拿來整理問題，例如你為什麼在衝突時想退開，而不是直接替你下結論。",
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
        "如果 MBTI 幫你說清楚自己的需求、改善溝通、看見壓力反應，它就是有用的。例如你能說出自己需要明確分工、需要安靜整理，或需要先談情緒再談解法。若它讓你逃避改變、否定別人，或把自己困在標籤裡，就被用錯了。",
        "真正值得留下的不是測驗結果本身，而是你從結果延伸出的觀察：我在哪些情境會這樣？哪些描述不符合我？我可以怎麼和別人說得更清楚？",
      ],
    },
  ],
  "intj-meaning": [
    {
      heading: "INTJ 是什麼？",
      paragraphs: [
        "INTJ 通常被描述為重視策略、結構和長期目標的人格類型。他們習慣先理解系統怎麼運作，再思考怎麼改進，比起臨場反應，更在意方向是否合理。",
        "如果 INTJ 在討論裡先問目標、限制和風險，未必是不近人情，而是想知道事情能不能走得下去。這不代表冷漠，也不代表每個 INTJ 都適合當領導者；INTJ 只是偏好模式，不是一個人的全部。",
      ],
    },
    {
      heading: "INTJ 在感情和人際裡常見什麼模式？",
      paragraphs: [
        "在感情裡，INTJ 常常需要時間確認關係是否有長期價值。他們未必擅長即時表達情緒，但通常會用規劃、承諾和解決問題來表示在意。",
        "在人際裡，INTJ 可能不喜歡過多寒暄，更在意對話是否有內容。你可以觀察他是否願意持續回應、是否把承諾做完，而不是只看他當下熱不熱情。",
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
        "例如工作條件看起來很好，但內容和價值感衝突，INFP 可能會反覆猶豫。這不等於脆弱，也不等於不切實際；很多 INFP 對細節和現實很敏感，只是不想把自己放進完全違背價值的框架裡。",
      ],
    },
    {
      heading: "INFP 在感情裡常見什麼模式？",
      paragraphs: [
        "在感情裡，INFP 往往重視真誠、理解和情緒安全感。他們可能需要比別人更多時間確認自己是否真的被看見，也可能因為太在意關係的意義而反覆思考。",
        "這種細膩是優點，但也可能讓 INFP 容易把沒說出口的期待放在心裡。關係要穩，不只需要感受，也需要把需求講清楚，例如想被怎麼回應、哪些玩笑會受傷、需要多少獨處時間。",
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
        "例如朋友只說「沒事」，INFJ 可能已經察覺氣氛變了，卻未必知道該不該追問。INFJ 稀有不代表比較優越，也不代表神秘；它只是指出一種從整體脈絡、關係感受和內在價值理解世界的偏好。",
      ],
    },
    {
      heading: "INFJ 在關係裡容易卡在哪裡？",
      paragraphs: [
        "INFJ 在關係裡常常很在意真誠和深度，如果只停留在表面互動，容易覺得消耗。可是他們也可能太早替別人理解、太慢替自己表達需求。",
        "健康的 INFJ 關係不是永遠理解別人，而是知道什麼時候要說清楚界線。可以觀察自己是否常替對方找理由，卻很少說出不舒服；敏銳不代表要負責消化所有人的情緒。",
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
        "例如一個新專案剛開始時，ENFP 可能很快提出很多點子，也會主動把人串起來。這不等於三分鐘熱度；很多時候，他們不是沒有方向，而是需要找到足夠有生命力、能和人產生連結的方向。",
      ],
    },
    {
      heading: "ENFP 在關係裡常見什麼模式？",
      paragraphs: [
        "ENFP 在關係裡通常很重視互動感和真實交流。他們喜歡被理解，也喜歡看見對方更多可能性，因此常能帶動氣氛和對話。",
        "但 ENFP 也需要留意，熱情不等於承諾，理解別人不等於要替對方解決人生。關係要穩，仍然需要清楚的界線和節奏，例如什麼算承諾、多久需要確認一次彼此狀態。",
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
  "birth-chart-meaning": [
    {
      heading: "命盤是什麼？",
      paragraphs: [
        "命盤是把出生資料轉成命理系統可以閱讀的結構。八字、紫微斗數和星盤都會談出生時間，但使用的語言不同，不能把三套系統直接混成同一個結論。",
        "例如你想知道工作方向，八字可能先看節奏與五行結構，紫微可能看事業宮與相關宮位，星盤則會看行星與宮位落點。它們能提供觀察層次，不能把出生資料直接翻成固定命運。",
      ],
    },
    {
      heading: "命盤可以幫你整理哪一層問題？",
      paragraphs: [
        "命盤比較適合整理長期傾向、反覆出現的課題和選擇節奏。當你在感情裡反覆遇到同一種互動、在工作裡常卡在同一種位置，命盤語言可以幫你把問題放到更長的時間線上看。",
        "但命盤不能替你判斷某個人會不會留下、某份工作會不會成功，或某個年份會不會賺錢。要放回生活裡，還要看完整資料、現實條件、當下問題和你真正能選擇的範圍。",
      ],
    },
    {
      heading: "看命盤時最容易誤會什麼？",
      paragraphs: [
        "最常見的誤會，是只抓一個詞就下結論。看到某個宮位、星曜或五行訊號，就直接推成感情、收入或人生結果，通常會漏掉整體結構和時間條件。",
        "比較穩的讀法，是先問：我現在要看的是感情互動、事業位置、資源節奏，還是人生方向？問題越清楚，命盤才越容易變成觀察工具，而不是壓在身上的標籤。",
      ],
    },
  ],
  "bazi-meaning": [
    {
      heading: "八字是什麼？",
      paragraphs: [
        "八字是把出生年月日時轉成干支組合的命理系統，常用來討論節奏、傾向、資源和關係互動。它不是把一個人的人生寫成固定劇本。",
        "例如同樣是想看事業，有人會在意適合穩定累積還是變動探索，有人是在問目前資源能不能承擔轉換。八字可以提供觀察語言，但不能替你看市場、履歷、合約或實際收入條件。",
      ],
    },
    {
      heading: "出生年月日時為什麼重要？",
      paragraphs: [
        "八字會把年、月、日、時轉成不同柱位，所以時間資料越完整，討論越不容易只停在模糊印象。缺少出生時辰時，有些細節就不適合說得太滿。",
        "放到生活裡，八字常被用來理解一個人面對壓力、資源、關係和變動時的節奏。例如你遇到選擇時是先保守觀察，還是需要看到機會才會行動，這些都比一句好壞判斷更有用。",
      ],
    },
    {
      heading: "八字不能直接代表什麼？",
      paragraphs: [
        "八字不能直接判定你適合哪個職業、會不會結婚，或某年會不會有財富結果。這些問題都需要回到能力、關係互動、資源條件和現實選擇。",
        "如果你只是查八字是什麼，先理解資料如何被整理就夠了；如果要放回個人問題，就要先說清楚自己在問感情、工作、財富還是方向，不能只靠單一干支或一句命格下定論。",
      ],
    },
  ],
  "ziwei-doushu-meaning": [
    {
      heading: "紫微斗數是什麼？",
      paragraphs: [
        "紫微斗數是用命盤十二宮、星曜配置和時間線索來整理人生主題的命理系統。它可以幫你看不同生活領域的觀察點，但不是把一張盤直接翻成完整人生答案。",
        "例如感情問題可能會看夫妻宮，也會牽涉命宮、福德宮、遷移或流年；工作問題可能看事業宮，也要回到能力、組織位置和市場條件。單一宮位或星曜不能離開整體脈絡。",
      ],
    },
    {
      heading: "十二宮和主星要怎麼理解？",
      paragraphs: [
        "十二宮比較像把問題分到不同生活領域：自我、關係、財富、工作、家庭、內在狀態等。主星和其他配置則提供語氣和傾向，幫你觀察這個領域可能怎麼運作。",
        "但宮位不是單獨的結論。例如夫妻宮不是婚姻判決書，財帛宮不是投資判斷，事業宮也不是職業清單。它們比較像提醒你先觀察哪一層條件。",
      ],
    },
    {
      heading: "紫微斗數最需要保留的限制",
      paragraphs: [
        "紫微斗數可以整理觀察層次，不能承諾感情、升遷、收入或人生結果。只看一顆星、單一宮位或一句格局，都很容易把複雜問題說得太滿。",
        "比較有用的讀法，是把問題縮小：我是在問關係互動、工作舞台、資源節奏，還是內在安全感？問題清楚後，再看命盤能補哪一層，而不是讓命盤替你做決定。",
      ],
    },
  ],
  "ming-gong-meaning": [
    {
      heading: "命宮是什麼？",
      paragraphs: [
        "命宮是紫微斗數裡常用來觀察自我感、基本反應和人生主題的宮位。它可以幫你理解一個人怎麼面對世界，但不能單獨決定命運。",
        "例如命宮描述一個人遇到壓力時比較想掌控、退後、協調或先觀察，這些都還只是傾向。真正放回生活裡，還要看其他宮位、星曜配置、時間條件和現實選擇。",
      ],
    },
    {
      heading: "命宮可以放到哪些生活情境？",
      paragraphs: [
        "在工作裡，命宮可以幫你觀察自己比較習慣站到前台、穩定累積，還是透過專業和節奏建立安全感。在人際裡，它可能提醒你如何被看見，以及遇到壓力時會怎麼保護自己。",
        "如果你查命宮是什麼，是因為想知道自己適合什麼方向，先不要急著把命宮當答案。可以先觀察最近一次重要選擇：你是在追求被看見、避免失控，還是想維持內在一致？",
      ],
    },
    {
      heading: "命宮不能替你判斷什麼？",
      paragraphs: [
        "命宮不能單獨判斷性格好壞、職業成敗、感情結果或完整人生。它只是紫微命盤中的一個觀察位置，需要和整張盤與問題脈絡一起看。",
        "若只看命宮就說一個人只能如何，會忽略後天選擇、環境、資源和關係互動。命宮比較適合幫你提出問題，而不是替你蓋章。",
      ],
    },
  ],
  "spouse-palace-meaning": [
    {
      heading: "夫妻宮是什麼？",
      paragraphs: [
        "夫妻宮是紫微斗數裡常用來觀察感情互動、伴侶模式和關係期待的宮位。它可以提供關係觀察角度，但不能承諾婚姻、復合或特定對象結果。",
        "例如你在關係裡常等對方表態、害怕承諾不對等，或容易把照顧和責任混在一起，夫妻宮可以作為其中一個觀察點。但感情仍要看實際互動和雙方選擇。",
      ],
    },
    {
      heading: "夫妻宮可以看哪些關係問題？",
      paragraphs: [
        "夫妻宮比較適合看關係裡常見的期待、互動節奏和安全感需求。它可以提醒你：自己在感情裡比較在意承諾、自由、穩定陪伴，還是被理解的深度。",
        "放到生活裡，可以觀察兩件事：對方是否有穩定行動，以及你是否能說清楚自己的需求。宮位語言若不能回到這些行為，就很容易變成抽象標籤。",
      ],
    },
    {
      heading: "夫妻宮不能直接下哪些結論？",
      paragraphs: [
        "夫妻宮不能直接判斷對方愛不愛你、會不會結婚、能不能復合，也不能把單一星曜寫成感情結果。關係需要看溝通、界線、責任和現實安排。",
        "如果你正在處理曖昧、分手或婚姻壓力，夫妻宮只能補一層長期模式。真正要決定下一步，仍要回到對方做了什麼、你說了什麼，以及雙方是否願意承擔。",
      ],
    },
  ],
  "wealth-palace-meaning": [
    {
      heading: "財帛宮是什麼？",
      paragraphs: [
        "財帛宮是紫微斗數裡常用來觀察資源、金錢觀、收入方式和安全感節奏的宮位。它不是投資判斷，也不能承諾一個人會不會賺錢。",
        "例如有人面對錢會先想穩定現金流，有人會被機會和流動感吸引，有人則容易把金錢和安全感綁在一起。財帛宮可以幫你觀察這些傾向，但不能取代財務規劃。",
      ],
    },
    {
      heading: "財帛宮可以放到哪些現實條件裡看？",
      paragraphs: [
        "看財帛宮時，最好同時看收入結構、支出習慣、風險承擔和資源來源。命盤語言可以提醒你傾向，但不能替你判斷投資標的、合約風險或市場變化。",
        "如果你正在擔心存不住錢，可以先觀察花錢前的情境：是壓力補償、收入不穩、固定支出太高，還是對未來風險太敏感？這些條件比單看宮位更接近答案。",
      ],
    },
    {
      heading: "財帛宮不能代表完整財富結果",
      paragraphs: [
        "財帛宮不能單獨判斷財運好壞，也不能替任何人做投資、借貸或理財決策。財富問題牽涉收入、風險、法律、家庭責任和現實市場。",
        "比較穩的讀法，是把財帛宮當成資源節奏的觀察點。它能幫你分清自己對錢的反應模式，但不能把單一宮位寫成完整人生或資產結論。",
      ],
    },
  ],
  "tarot-card-meanings": [
    {
      heading: "塔羅牌意思怎麼看？",
      paragraphs: [
        "塔羅牌意思不是要你背完每張牌，而是先幫你把煩惱換成比較清楚的語言。你可以先看它在提醒情緒、行動、資源、溝通，還是選擇卡住。",
        "如果你是因為感情、工作或人生方向來查，重點不是這張牌本身多複雜，而是它能不能讓你看見現在的問題：誰沒有說清楚、哪個條件還不足、下一步能不能更具體。",
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
        "看塔羅牌義時，要把牌、問題問法和當下狀態放在一起看。單張牌可以給提醒，但不能取代完整脈絡。",
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
  const topic = route.topic ? getTopicRecord(route.topic) : null;
  if (route.topic) {
    if (!topic) return { redirectTo: "/articles" };
    return buildTopicContent(route, topic, origin, defaults);
  }
  const isLatestHub = !route.product && !route.slug && !route.intent;
  const intent = route.intent ? getLifeIntentRecord(route.intent) : null;
  const article = route.product && route.slug ? getArticleRecord(route.product, route.slug) : null;
  const section = article ? getArticleSectionRecord(article.section) : getArticleSectionRecord(route.product);
  if (route.slug && !article) {
    return {
      redirectTo: section?.product ? `/articles/${section.product}` : "/articles",
    };
  }
  if (route.slug && article && route.slug !== article.urlSlug) {
    return {
      redirectTo: getArticlePath(article),
    };
  }
  const productThemeRecord = getProductThemeRecord(article?.product || route.product || section?.product);
  const canonicalPath = route.intent
    ? `/articles/intents/${route.intent}`
    : article
      ? getArticlePath(article)
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
  const updated = defaults.updated || DEFAULT_ARTICLE_UPDATED_DATE;
  const author = defaults.author || "Pantheon 編輯部";
  const managedArticle = enforceArticlePolicy({
    id: article?.id,
    section: article?.section || route.product,
    slug: route.slug,
    serial: article?.serial,
    urlSlug: article?.urlSlug,
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
      description: "Pantheon 最新文章，整理命盤、人格、塔羅、星座與人生方向主題。",
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
    contentType: route.slug ? "Article" : "CollectionPage",
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
    slug: article?.urlSlug || route.slug,
    serial: managedArticle.serial || "",
    author,
    updated,
    published: defaults.published || DEFAULT_ARTICLE_PUBLISHED_DATE,
    sectionDescription: buildSectionDescription(route, section, intent, productTheme),
    productTheme: isLatestHub ? "latest" : managedArticle.productTheme,
    productThemeLabel: productTheme.label,
    productThemeGlyph: productTheme.glyph,
    productThemeDescription: productTheme.description,
    intent: route.intent || managedArticle.intent,
    keywords: managedArticle.keywords,
    tags: managedArticle.tags,
    displayTags: buildDisplayTags(article, managedArticle, productTheme),
    displayTagLinks: buildDisplayTagLinks(article, managedArticle, productTheme),
    answer: article?.answer || buildAnswer(route),
    bodySections: buildBodySections(route, article, section, intent, productTheme, managedArticle),
    faq: buildArticleFaq(route, article, productTheme),
    navigationLinks: buildArticleNavigationLinks(article),
    relatedLinks: buildRelatedLinks(article, managedArticle, productTheme, route),
    cta: buildArticleCta(article, productTheme, route),
  };
}

function buildDisplayTags(article, managedArticle, productTheme) {
  const source = article
    ? listPublicTagLabelsForArticle(article)
    : [
      productTheme.label,
      managedArticle.primaryKeyword,
      ...(managedArticle.originalTags || []),
    ];
  return uniqueList(source)
    .filter((tag) => tag && !INTERNAL_DISPLAY_TAGS.has(tag))
    .slice(0, 8);
}

function buildDisplayTagLinks(article, managedArticle, productTheme) {
  return buildDisplayTags(article, managedArticle, productTheme).map((label) => {
    const topic = getTopicForLabel(label);
    return {
      label,
      href: topic ? topic.href : "",
    };
  });
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
  const [scope = "", first = "", second = ""] = segments;
  if (scope === "topics") {
    return {
      product: "",
      productLabel: "最新文章",
      requestedSection: "",
      slug: "",
      intent: "",
      topic: first,
      intentLabel: "",
      title: humanizeSlug(first) || "標籤",
    };
  }
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
    topic: "",
    intentLabel: intent ? getLifeIntentRecord(intent)?.label || humanizeSlug(intent) : "",
    title: humanizeSlug(slug) || "文章",
  };
}

function buildDescription(route, article, section, intent, productTheme) {
  if (route.slug && article?.description) return article.description;
  if (route.slug) return `${route.title}：Pantheon 以繁體中文整理${productTheme.label}主題，提供清楚摘要、背景脈絡與延伸閱讀。`;
  if (route.intent) return `Pantheon ${intent?.label || route.intentLabel}文章主題，整理相關問題、文章脈絡與延伸閱讀。`;
  if (route.product) return section?.seoDescription || `Pantheon ${productTheme.label}文章列表，整理基礎概念、常見問題與延伸閱讀。`;
  return "Pantheon 最新文章，整理命盤、人格、塔羅、星座與人生方向主題。";
}

function buildTopicContent(route, topic, origin, defaults = {}) {
  const safeTopic = topic || {
    slug: route.topic,
    label: humanizeSlug(route.topic),
    aliases: [],
    href: `/topics/${route.topic}`,
  };
  const articles = listArticlesForTopic(safeTopic.slug);
  const updated = defaults.updated || DEFAULT_ARTICLE_UPDATED_DATE;
  return {
    title: buildTopicTitle(safeTopic.label),
    contentType: "CollectionPage",
    pageTitle: `${buildTopicTitle(safeTopic.label)} | Pantheon`,
    description: `整理 Pantheon 中提到 ${safeTopic.label} 的公開文章，方便直接找到相關內容。`,
    canonicalPath: `/topics/${safeTopic.slug}`,
    canonicalUrl: `${origin}/topics/${safeTopic.slug}`,
    product: "topics",
    productLabel: "主題",
    productHref: "/articles",
    section: "topics",
    productCrumb: "topics",
    productCrumbLabel: "主題",
    slug: safeTopic.slug,
    serial: safeTopic.id || "",
    author: defaults.author || "Pantheon 編輯部",
    updated,
    published: defaults.published || DEFAULT_ARTICLE_PUBLISHED_DATE,
    sectionDescription: `整理所有提到「${safeTopic.label}」的公開文章。`,
    productTheme: "latest",
    productThemeLabel: "主題",
    productThemeGlyph: "#",
    productThemeDescription: "同一主題的文章列表。",
    intent: "",
    keywords: uniqueList([safeTopic.label, ...(safeTopic.aliases || []), "Pantheon", "公開文章"]),
    tags: uniqueList([safeTopic.label, ...(safeTopic.aliases || [])]),
    displayTags: uniqueList([safeTopic.label, ...(safeTopic.aliases || [])]).slice(0, 8),
    displayTagLinks: uniqueList([safeTopic.label, ...(safeTopic.aliases || [])]).slice(0, 8).map((label) => ({
      label,
      href: `/topics/${safeTopic.slug}`,
    })),
    answer: `這裡整理所有提到「${safeTopic.label}」的公開文章，直接選一篇進去讀。`,
    bodySections: buildTopicBodySections(safeTopic, articles),
    faq: [],
    relatedLinks: [],
    cta: null,
  };
}

function buildTopicBodySections(topic, articles) {
  const articleLinks = articles.slice(0, 24).map((article) => ({
    label: article.title,
    href: getArticlePath(article),
    kind: article.serial,
  }));
  return [
    {
      heading: `${topic.label} 相關文章`,
      paragraphs: [
        articleLinks.length ? `目前收錄 ${articleLinks.length} 篇文章。` : "目前還沒有收錄文章。",
      ],
      links: articleLinks,
    },
  ];
}

function buildTopicTitle(label) {
  return `${label} 相關文章`;
}

function buildTopicRelatedLinks(topic, articles) {
  const articleLinks = articles.slice(0, 8).map((article) => ({
    label: article.title,
    href: getArticlePath(article),
    kind: "相關文章",
  }));
  return uniqueLinks(articleLinks).filter((item) => item.href !== `/topics/${topic.slug}`).slice(0, 8);
}

function buildSectionDescription(route, section, intent, productTheme) {
  if (route.intent) return `${intent?.label || route.intentLabel}文章會整理搜尋者真正想解決的問題，再連回對應產品線文章與主題文章。`;
  if (route.product && section?.description) return section.description;
  if (route.product) return `${productTheme.label}文章列表，整理基礎概念、常見問題與延伸閱讀。`;
  return "最新文章集中整理命盤、人格、塔羅、星座與人生方向主題。";
}

function buildAnswer(route) {
  if (route.slug) return `${route.title} 的重點會先用短摘要回答，再補充適用情境、限制與下一步閱讀。`;
  if (route.intent) return `${route.intentLabel}文章會先整理搜尋者真正想解決的問題，再連到相關主題文章。`;
  if (route.product) return `${route.productLabel}文章會先整理核心概念，再連到相關主題與延伸閱讀。`;
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
          `${label}相關搜尋通常不是只想看一個名詞，而是想知道現在遇到的問題可以從哪些角度理解。這裡會整理人格、塔羅、命盤與星盤中和${label}有關的文章。`,
          "公開文章適合先建立概念、看常見問題與限制；如果要做個人化判斷，仍需要回到具體資料與情境。",
        ],
      },
    ];
  }
  if (route.product) {
    return buildProductHubSections(route, section, productTheme);
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

function buildProductHubSections(route, section, productTheme) {
  const articles = getRelatedArticleLinks(route.product);
  const articleNames = articles.map((item) => item.label).join("、");
  return [
    {
      heading: `${productTheme.label}文章會先整理什麼？`,
      paragraphs: [
        section?.description || `${productTheme.label}文章會先整理常見概念，再補充使用限制與延伸閱讀。`,
        `${productTheme.label}文章會把同一產品線的公開內容集中在一起。讀者可以先從「${section?.primaryKeyword || productTheme.label}」建立基本語言，再依照自己真正想問的情境往下讀。`,
        "文章編號會維持固定，方便之後擴充到更多內容。讀者不需要記編號，只要看標題和情境，選最接近自己問題的文章就好。",
      ],
    },
    {
      heading: `這裡先讀哪幾篇${productTheme.label}文章？`,
      paragraphs: [
        articleNames
          ? `目前收錄：${articleNames}。每篇都會先回答搜尋問題，再說明適用情境、常見誤解和不能代表什麼。`
          : `目前會收錄${productTheme.label}基礎概念、常見問題與延伸閱讀。`,
        `如果你只是想查定義，先讀第一篇基礎文就好；如果你已經卡在感情、事業、人際、財富或人生方向，就選最接近當下煩惱的主題文章。`,
        "不要從列表直接跳到個人結論。這裡的價值，是讓你知道有哪些文章、每篇負責哪一層問題，以及下一篇該怎麼選。",
      ],
    },
    {
      heading: `${productTheme.label}文章和個人判讀的邊界`,
      paragraphs: [
        getProductBoundarySentence(productTheme.label),
        "公開文章只能整理共通知識、名詞差異和閱讀順序，不會把單一宮位、人格類型、牌義或星座落點寫成你的個人結論。真正套用到自己身上時，仍然要回到資料、問題和當下情境。",
        "如果你是從搜尋進來，先確認自己要的是概念、比較、使用限制，還是想找下一篇文章。這四種需求會導向不同閱讀路徑，也會影響你要不要改讀更接近情境的文章。",
      ],
    },
    {
      heading: "下一步怎麼選文章？",
      paragraphs: [
        "如果你不知道從哪裡開始，先選一篇最接近你搜尋字的文章；如果讀完還是不確定，再回到同分類延伸閱讀或更接近情境的主題文章。這樣可以避免在不同工具之間跳來跳去，卻沒有真正釐清問題。",
        "比較好的順序是：先讀產品線基礎文章，再看單一概念文章，最後才進到感情、事業、人際、財富或人生方向主題。重點不是多讀，而是知道下一篇要補哪一層。",
        "如果你看到文章標籤，也可以直接點進主題列表。主題列表會把跨分類文章串起來，例如 MBTI 可以連到人格、人際和自我理解；塔羅也可以連到牌義、正逆位和感情提問。",
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
    ...buildExpansionSections(article),
    buildScenarioSection(article, productTheme),
    buildRelatedReadingSection(article, productTheme),
    buildReaderDecisionSection(article, productTheme),
    buildNextStepSection(article, productTheme, managedArticle),
  ];
}

function buildExpansionSections(article) {
  if (article.slug === "16-personalities") {
    return [
      {
        heading: "16 型人格總覽怎麼讀，才不會越讀越亂？",
        paragraphs: [
          "讀 16 型人格時，先不要從哪一型最稀有、哪一型最聰明開始。比較穩的順序，是先看四組偏好：外向或內向、實感或直覺、思考或情感、判斷或知覺。這四組偏好會影響一個人怎麼接收資訊、怎麼做決定，也會影響他在關係裡需要什麼節奏。",
          "接著再看 16 種組合。每一型都可以寫出常見特質，但那些特質不是身分證，也不是命運說明。兩個同樣是 INFP 的人，可能因為家庭、工作壓力、情感經驗和自我要求不同，表現出完全不同的樣子。總整理頁的作用，是讓你快速建立地圖，而不是替每個人蓋章。",
          "如果你想把 16 型人格用得更準，可以把每一型當成一組問題：我在補充能量時偏向哪裡？我做決定時最怕失去什麼？我在壓力下會變得更封閉、急躁、逃避，還是更想控制？能回答這些問題，比背類型綽號更有用。",
          "也可以把自己和身邊人的互動分成平常狀態與壓力狀態。很多類型描述看起來不準，是因為讀者把壓力下的防衛反應誤當成日常人格；分開看，才知道哪些是長期偏好，哪些只是某段時間的負荷。",
        ],
      },
      {
        heading: "感情、工作與人際，不要只看類型名稱",
        paragraphs: [
          "在感情裡，16 型人格可以幫你整理相處偏好，例如有人需要大量對話，有人需要先安靜想清楚；有人重視被理解，有人重視問題能不能被解決。但它不能直接判定兩個人合不合，也不能說某型只能和某型在一起。",
          "在工作裡，16 型人格比較適合拿來討論合作方式。有人適合明確流程，有人需要彈性探索；有人先看全局，有人先處理細節。這些差異可以改善溝通，但不應被用來限制職涯。任何類型都可能做出好成果，差別在於環境、訓練和支持條件是否合適。",
          "在人際裡，類型描述可以幫你看見互動消耗點。你可能不是不合群，只是需要不同的社交節奏；你也可能不是太敏感，而是對關係裡沒說出口的期待很快有反應。把這些說清楚，才是 16 型人格比較健康的用途。",
          "所以讀總整理頁時，最好一邊讀一邊做排除。哪些描述只是你羨慕的樣子？哪些描述讓你想到實際事件？哪些描述一放到感情、工作或家庭就不太成立？這些差異，比單純找最像自己的類型更重要。",
          "如果你是替團隊、伴侶或朋友查 16 型人格，也要把它當成溝通提示，而不是評分表。你可以用它開啟對話，例如彼此怎麼補充能量、怎麼面對衝突、怎麼做決定；但不要拿類型替對方決定應該怎麼想。",
        ],
      },
    ];
  }
  if (article.slug === "tarot-card-meanings") {
    return [
      {
        heading: "先看你正在問什麼，不要只背牌義",
        paragraphs: [
          "查塔羅牌意思時，先不要急著問這張牌是好是壞。你真正要處理的通常是關係停住、工作選擇不明、情緒太滿，或下一步不知道怎麼走。",
          "牌組分類可以幫你理解語氣，但不用把它當成課程。比較實用的方式，是看這張牌把你的問題推向哪一層：行動、關係、想法、資源，還是現實條件。",
          "很多人卡住，是因為看到牌就想立刻翻成結果。比較好的讀法，是先問：這張牌在提醒狀態、阻力、資源，還是下一步？同一張牌放在不同問題裡，答案會不一樣；牌義提供語言，不替問題本身下結論。",
          "如果你想看得更清楚，可以用情境分類，而不是只背關鍵字。先把牌義放進感情、工作、人際或人生方向裡想一次，看看它提醒的是關係、行動、資源、想法，還是階段轉換。",
        ],
      },
      {
        heading: "正位逆位、牌陣位置和問題問法要一起看",
        paragraphs: [
          "一張牌的意思會被三件事影響：它是正位還是逆位、它落在牌陣哪個位置，以及你一開始問的是什麼。沒有問題的牌義很容易變成泛泛而談；問題越清楚，牌義越容易落到具體情境。",
          "例如同一張牌放在感情裡，可能是在提醒溝通、界線或期待；放在工作裡，可能是在提醒資源、節奏或準備程度。這也是為什麼 Pantheon 的塔羅文章不把單張牌寫成預言，而是把牌義拆成可理解的提醒。",
          "如果你讀到比較緊繃的牌，也不要急著把它當成壞結果。先回到問題：現在需要看見的是風險、延遲、過度投入，還是某個沒有說清楚的需求？這樣讀牌比較能幫助行動，也比較不會被牌面嚇到。",
          "總覽文章適合幫你先看懂提醒，不適合當最後判讀。真正有用的閱讀，還要回到問題問法、當事人的現實限制和可行選項。這些都看見後，牌義才會從抽象象徵變成能被討論的提醒。",
          "也可以把塔羅牌意思總覽當成整理工具：先看這張牌提醒什麼，再放回感情、工作或人生方向裡的語氣。不要從單一句關鍵字直接跳到結論，否則很容易忽略問題本身的條件。",
          "如果同一張牌反覆出現在你的問題裡，先不要急著把它想成命運提示。比較穩的做法，是回頭看你問的問題是否太相似、是否一直卡在同一個行動選項，或是否忽略了現實裡已經很清楚的限制。",
        ],
      },
    ];
  }
  return [];
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
      `閱讀 ${primary} 時，先把它當成整理問題的起點，而不是最後答案。`,
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
      `讀「${primary}」時，可以先把問題分成三層：名詞本身是什麼、它能看哪些生活情境、它不能直接替你判斷什麼。這樣比較不會把一個詞誤讀成完整答案。`,
      `如果你是從「${related}」這類關鍵字進來，建議先不要急著把結果套到自己身上。先確認你要找的是自我理解、關係互動、工作節奏，還是只是想知道某個詞在網路上常被怎麼使用。`,
      `比較穩的讀法，是先把通用意思說清楚，再把限制講出來。這樣讀起來會比較清楚，也不會被推向沒有根據的個人結論。`,
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
      heading: "先看你現在卡在哪一種煩惱",
      paragraphs: [
        "如果你是為了感情來查，真正想問的通常不是牌本身，而是對方態度不明、關係停住、自己不知道要不要再靠近。先把這件事說清楚，比急著找一個好壞答案更重要。",
        "如果你是為了工作或選擇來查，問題多半卡在資源、時機、溝通或下一步行動。牌義只能幫你把卡點命名，不能替你判定要不要離職、合作或投入一個計畫。",
        "如果你現在很焦慮，先不要把任何一張牌當成結論。比較有用的讀法，是看它提醒你先確認哪件事：話有沒有說清楚、條件夠不夠、界線在哪裡，或自己是不是只是在等一個確定答案。",
      ],
    };
  }
  if (article.product === "fortune") {
    return {
      heading: "感情、事業與財富題，命盤各自看哪一層？",
      paragraphs: [
        "放到感情裡，命盤文章適合整理長期關係課題、互動模式和安全感來源，但不能只用單一宮位或星曜判定一段關係。",
        "放到事業與財富裡，命盤可以協助讀者理解資源節奏、工作傾向和選擇壓力。它不是投資判斷，也不能承諾收入、升遷或創業結果。",
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
  if (article.product === "tarot") {
    return {
      heading: "什麼時候需要再往下整理？",
      paragraphs: [
        "如果你只是想知道一張牌大概在提醒什麼，讀到這裡就可以停。真正需要再往下整理，是你已經有一個具體煩惱，而且想看清楚自己能做什麼。",
        "感情題可以先問：我是在等對方表態，還是在逃避自己要不要繼續？工作題可以先問：我缺的是資源、時機，還是決心？人生方向題可以先問：我現在最怕承擔哪個選擇的後果？",
        "如果你一直想換一個答案，通常代表你要的不是提醒，而是確定答案。這時候先回到現實線索：對方做了什麼、你說了什麼、條件允不允許、你能不能接受最壞情況。先把這些線索列出來，答案才不會只停在情緒裡。",
        "能幫你看清下一個行動，才值得繼續讀；只讓你更想找確定答案的內容，就先停下來。讀完後至少留下告白、等待、溝通、準備或放手其中一個可檢查的方向，而不是只留下更強的不安。這樣塔羅才是在幫你整理狀況，不是在放大原本的煩惱，或讓你反覆繞回同一個問題。",
        "如果你讀完仍然很想立刻再找一個答案，可以先停在一個小動作：寫下目前已知事實、仍未確認的猜測、以及今天能做的一個確認。這能把牌義拉回生活，不讓問題只停在等待裡。",
      ],
    };
  }
  if (article.product === "personality") {
    return {
      heading: "什麼時候需要回到自己的互動經驗？",
      paragraphs: [
        "如果你只是想知道一個人格詞是什麼，讀到定義就夠了。真正需要回到自己身上時，要看具體事件：最近一次衝突、一次合作不順、一次你明明很累卻說不出口的需求。",
        "把文章裡的描述拿去對照事件，而不是拿去套人。你可以問：我在哪個情境真的像這段描述？哪裡其實不像？哪些反應只是壓力下的防衛？",
        "人格類型有用的地方，是幫你把習慣說清楚。它不該變成一句「我就是這樣」，也不該拿來替別人下判斷。能讓溝通變清楚，才算真的讀進去。",
        "如果讀完後想拿去處理關係或工作問題，先挑一個最小情境練習就好。比如下一次開會怎麼表達需求、下一次衝突前怎麼提醒自己暫停，而不是把整個人生都交給類型描述。",
        "也可以把最有感的一句描述改寫成可說出口的需求，例如我需要時間整理、我需要明確分工、我需要先知道對方期待。能被拿去溝通的內容，才是真的有用。",
      ],
    };
  }
  if (article.product === "fortune") {
    return {
      heading: "什麼時候需要完整資料，而不是只看單點？",
      paragraphs: [
        "如果你只是查一個宮位、星曜或命盤名詞，先理解概念就好。要放回個人狀況時，不能只抓單一詞下結論，還要看完整資料、時間節奏和你真正想問的問題。",
        "遇到感情、事業或財富題時，先把問題寫清楚：你是在看長期模式、當下選擇，還是某個反覆出現的壓力？問題不同，同一個命盤訊號的用法也不同。",
        "命盤適合整理長期課題，不適合替你承諾結果。能讓你分清資料不足、時機未明或問題問錯，才是比較有用的讀法。",
        "如果讀完後仍然想知道自己該怎麼辦，先回到現實限制：時間夠不夠、資料完整嗎、你真正要比較的是哪兩個選項。命盤語言要能幫你分清問題，而不是讓問題變得更重。",
        "也可以先把問題寫成一句具體描述，例如我卡在轉職風險、我害怕關係重複、我不知道資源夠不夠。命盤訊號放進這種句子裡，才比較容易變成可檢查的線索，也比較不會把名詞誤讀成最後答案。必要時先補資料。",
      ],
    };
  }
  if (article.product === "astro") {
    return {
      heading: "什麼時候需要看整張星盤？",
      paragraphs: [
        "如果你只是查一個太陽星座、月亮星座或上升星座，單篇文章可以先幫你抓住基本語氣。要判斷感情、人際或人生方向時，就不能只看一個落點。",
        "把太陽、月亮、上升分開看，再放回同一個情境。太陽像你怎麼表達自己，月亮像情緒和安全感，上升像你被看見的方式。三者一起看，才比較接近真實互動。",
        "星盤語言要能回到生活觀察：你怎麼溝通、怎麼感到安全、怎麼做選擇。若只留下某個星座標籤，就還沒有真正讀懂。",
        "如果讀完後想用在感情或人際裡，先對照一個真實互動。你是在意被理解、需要安全感，還是害怕被看穿？這些問題比單一星座名稱更接近你正在處理的煩惱，也更容易帶回下一次對話。能落到互動，星盤語言才有用。",
        "如果你正在比較兩個落點，不要急著選哪個比較準。先看哪個落點最能說明你最近的反應，再看另一個落點是否只是補充。這樣比較不會把星座詞直接變成關係判決，也比較能回到真實互動。必要時先放慢，再看證據。",
      ],
    };
  }
  return {
    heading: `什麼時候需要把${productTheme.label}放回個人情境？`,
    paragraphs: [
      `如果你只是想理解「${article.primaryKeyword}」這個概念，先停在定義和限制就好。要放回自己的狀況時，先把問題寫清楚，再看這個概念能不能解釋你遇到的具體情境。`,
      "不要把任何一篇文章、單一名詞或單一工具直接當成最後判斷。比較可靠的讀法，是看它能不能幫你提出更好的問題，或幫你排除一個明顯的誤解。",
      "如果讀完仍然模糊，先把疑問改寫得更小。從「我該怎麼辦」改成「我現在缺哪個條件」、「哪個限制最明顯」或「哪件事需要先確認」。問題變小，答案才會變清楚。",
      "能被帶回生活的文章，至少會讓你多一個可檢查的問題：我要先談清楚、先補資料、先觀察行動，還是先承認自己其實還沒準備好選擇。",
      "如果這篇文章讓你想到某個人或某個選擇，先不要直接套答案。把情境、證據、限制分開寫下來，再看哪一段真的能解釋你的狀況。",
    ],
  };
}

function buildReaderDecisionSection(article, productTheme) {
  if (article.product === "personality") {
    return {
      heading: "讀完人格文章後，可以怎麼整理自己的問題？",
      paragraphs: [
        "讀完人格文章後，先不要急著問自己是不是完全符合某一型。比較有用的做法，是寫下三個具體情境：最近一次關係卡住、最近一次工作消耗、最近一次你覺得自己不像平常的時候。再回頭看文章裡的描述，哪些真的對得上，哪些其實只是你當時壓力太大。",
        "如果文章讓你更能說清楚需求，它就有價值；如果它讓你開始用類型替自己或別人找藉口，就要暫停。人格文章的目的，是幫你把反應模式說清楚，不是讓你把自己鎖在某個標籤裡。",
        "也可以把文章裡最有感的描述改寫成自己的語句，例如「我需要比較多時間整理情緒」或「我在壓力下會急著找答案」。能被你用來溝通的句子，才是真正留下來的內容。",
        "最後再檢查一件事：這篇文章有沒有幫你提出更好的問題。如果讀完只剩下「我就是這樣」，那還不夠；如果讀完能讓你知道下一次要怎麼說、怎麼觀察、怎麼調整互動，文章才真的被用上。",
      ],
    };
  }
  if (article.product === "tarot") {
    return {
      heading: "把問題改成現在能處理的事",
      paragraphs: [
        "把「他會不會回來」改成「這段關係目前卡在哪裡」。把「會不會成功」改成「我現在缺哪個條件」。問題一變具體，答案才不會只剩好或壞。",
        "如果你在感情裡反覆不安，先看能不能確認三件事：對方有沒有實際行動、你有沒有把需求說出口、這段關係是不是只靠你一個人在撐。",
        "如果你在工作或選擇上卡住，先看哪個條件最不穩：時間、能力、資源、溝通，還是你其實不想承擔後果。這些比一句抽象牌義更能幫你往前走。",
        "讀到任何提醒，都要落回現實。提醒你溝通，就想清楚要談哪件事；提醒你等待，就分清是在準備還是在拖延；提醒你行動，就先找一個今天能做的小步驟。",
      ],
    };
  }
  if (article.product === "fortune") {
    return {
      heading: "讀完命盤文章後，先把觀察點放回完整情境",
      paragraphs: [
        "讀完命盤文章後，最重要的是不要只抓一個詞下結論。命宮、夫妻宮、財帛宮、八字、紫微斗數都只是不同觀察點；它們要放回完整資料、時間節奏和讀者當下真正想問的問題裡，才比較不會被誤讀。",
        "如果你正在查感情、事業或財富，先把問題寫成一句具體描述，再看文章能不能幫你分清層次。公開文章可以建立共同語言，但不會替你判定一段關係、一次轉職或一個財務選擇的最後結果。",
        "也可以把讀到的命盤詞分成三類：系統名詞、觀察位置、生活問題。系統名詞幫你知道資料從哪裡來，觀察位置幫你知道它看哪一層，生活問題則提醒你不要離開現實條件。",
        "最後再問：這個觀察點能不能回到一個具體行動或判斷邊界？如果只能讓你更焦慮，就先停在背景知識；如果能幫你分清資料不足、時機未明或問題問錯，才適合繼續往下讀。能對上現實條件，命盤語言才有用，也比較不會把壓力誤讀成答案或結果。",
      ],
    };
  }
  if (article.product === "astro") {
    return {
      heading: "讀完星盤文章後，不要只留下單一星座印象",
      paragraphs: [
        "讀完星盤文章後，可以先把太陽、月亮、上升各自寫成一句話：太陽比較像你如何表達自己，月亮比較像情緒和安全感，上升比較像你被看見的方式。這三句話放在一起，會比只看一個星座更接近實際情境。",
        "如果你是為了感情或人生方向而查星盤，記得單一落點不能直接說明完整關係。它能提供語言和提醒，但仍要搭配互動經驗、現實條件和你真正想處理的問題。",
        "星盤文章最適合拿來做對照，而不是拿來貼標籤。你可以先看哪個落點最能解釋目前的情緒，再看哪個落點其實只是補充角度。把主次分清楚，才不會被星座語言牽著走。",
        "最後把星盤語言翻成生活觀察。你可以問：這個落點在我平常的安全感、溝通方式或選擇節奏裡是否看得見？如果看不見，就先把它當成參考，不要硬套成完整答案。能說出一個可觀察情境，才算真的讀懂，也才知道下一步要確認哪個條件。",
      ],
    };
  }
  return {
    heading: "讀完文章後，先把問題寫成一句話",
    paragraphs: [
      `讀完${productTheme.label}文章後，先把你真正想問的問題寫成一句話，再回頭看文章提供的是定義、背景、限制，還是下一步閱讀方向。`,
      "公開文章最適合幫你建立語言和分類，不適合直接替你做人生判斷。能把問題說清楚，才是決定下一篇要補哪一層前最重要的事。",
      "如果一篇文章讓你更想追問，可以把追問拆成事實、感受、限制和可行動選項。這四層分開後，後續閱讀才不會一直繞回同一個焦慮。",
      "最後確認這篇文章留下的是判斷方法，而不是情緒答案。方法可以被帶到下一個問題裡重複使用；情緒答案通常只會讓人短暫安心，卻沒有真正釐清問題。能落到一個可觀察行為，才適合繼續延伸。",
    ],
  };
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
      heading: "不要只問這張牌好不好",
      paragraphs: [
        "同一張牌放在不同煩惱裡，重點會不一樣。感情裡可能是在提醒界線，工作裡可能是在提醒準備不足，人生方向裡可能是在提醒你還沒真正開始。",
        "例如愚者不必直接當成好事，也不必直接當成壞事。它可能像新的開始，也可能像太快跳下去。魔術師也一樣，可能是資源到位，也可能是話很多但行動還沒跟上。",
        "所以不要只問這張牌好不好。先問：它對我現在這個問題，提醒的是溝通、資源、時機、界線，還是我需要換一種問法？",
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
      `讀${productTheme.label}文章時，可以先看同分類基礎文章，再回到單篇文章補概念，最後用感情、事業、人際、財富或人生方向整理自己的問題。`,
      "延伸閱讀不是為了堆連結，而是讓讀者知道下一篇要解決哪一層問題：定義、情境、限制，還是自己的具體狀況。",
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
      answer: article?.answer || `${primary} 適合先看定義、適用情境與限制，再決定要不要放回自己的問題裡。`,
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
      question: `想看自己的狀況，應該先整理什麼？`,
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
  if (article?.product === "tarot") return "最容易問成「會不會真的發生」。比較好的問法，是問目前卡在哪裡、自己能看見什麼、下一步如何更清楚。";
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
  if (article?.product === "personality") return `${formatFaqTopicPrefix(topic)}只能整理常見偏好，不能取代專業評估，也不能單獨判定感情、工作或人生結果。`;
  if (article?.product === "tarot") return `${formatFaqTopicPrefix(topic)}只能提供牌義和情境提醒，不能替對方下結論，也不能承諾復合、成功或最終結果。`;
  return `${formatFaqTopicPrefix(topic)}只能幫你理解${productTheme.label}的通用概念，不能替代個人資料、具體問題與專業判斷。`;
}

function buildEntryAnswer(article, productTheme) {
  if (article?.product === "personality") return "先整理最近一次真的卡住的互動：誰、什麼情境、你怎麼反應、哪裡讓你不舒服，再回頭看人格描述是否能幫你說清楚需求。";
  if (article?.product === "tarot") return "先把煩惱寫成一句具體問題：關係卡在哪裡、工作缺哪個條件、現在能做哪一步。牌義只用來輔助整理，不用來替你拿確定答案。";
  return `先把問題寫成一句具體描述，再看${productTheme.label}文章能不能幫你分清定義、限制和下一步要確認的條件。`;
}

function buildRelatedLinks(article, managedArticle, productTheme, route = {}) {
  if (!article && route.product) {
    return getRelatedArticleLinks(route.product).slice(0, 8);
  }
  if (!article) return [];
  return buildArticleRecommendationLinks(article);
}

function getRelatedArticleLinks(product) {
  const articles = listArticleRecords()
    .filter((item) => item.product === product || item.articleCategory === product)
    .sort(compareArticleSerial);
  if (!articles.length) return [];
  return articles.map((item) => ({
    label: item.title,
    href: getArticlePath(item),
    kind: "同分類",
  }));
}

function buildArticleNavigationLinks(article) {
  if (!article) return [];
  const siblings = listArticleRecords()
    .filter((item) => item.articleCategory === article.articleCategory)
    .sort(compareArticleSerial);
  const index = siblings.findIndex((item) => item.serial === article.serial);
  if (index === -1) return [];
  return [
    siblings[index - 1]
      ? { label: siblings[index - 1].title, href: getArticlePath(siblings[index - 1]), kind: "上一篇" }
      : null,
    siblings[index + 1]
      ? { label: siblings[index + 1].title, href: getArticlePath(siblings[index + 1]), kind: "下一篇" }
      : null,
  ].filter(Boolean);
}

function buildArticleRecommendationLinks(article) {
  const candidates = getRecommendedArticleCandidates(article);
  const currentCategory = article.articleCategory || article.product;
  const sameCategoryRecommendations = candidates
    .filter(({ article: candidate }) => (candidate.articleCategory || candidate.product) === currentCategory)
    .slice(0, 2);
  const usedCategories = new Set([currentCategory]);
  const crossCategoryRecommendations = [];
  candidates.forEach((candidate) => {
    if (crossCategoryRecommendations.length >= 3) return;
    const candidateCategory = candidate.article.articleCategory || candidate.article.product;
    if (!candidateCategory || usedCategories.has(candidateCategory)) return;
    usedCategories.add(candidateCategory);
    crossCategoryRecommendations.push(candidate);
  });
  return [...sameCategoryRecommendations, ...crossCategoryRecommendations]
    .slice(0, 5)
    .map(({ article: candidate }) => ({
      label: candidate.title,
      href: getArticlePath(candidate),
      kind: "相關文章",
    }));
}

function getRecommendedArticleLinks(article) {
  return buildArticleRecommendationLinks(article);
}

function getRecommendedArticleCandidates(article) {
  if (!article) return [];
  const currentPath = getArticlePath(article);
  return listArticleRecords()
    .filter((candidate) => getArticlePath(candidate) !== currentPath)
    .map((candidate) => ({
      article: candidate,
      score: scoreRelatedArticle(article, candidate),
    }))
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score || compareArticleSerial(a.article, b.article));
}

function scoreRelatedArticle(article, candidate) {
  const sourceTopics = new Set(getArticleTopicSlugs(article));
  const candidateTopics = new Set(getArticleTopicSlugs(candidate));
  const sharedTopicCount = [...sourceTopics].filter((topic) => candidateTopics.has(topic)).length;
  const sourceTerms = new Set(getArticleSearchTerms(article));
  const candidateTerms = new Set(getArticleSearchTerms(candidate));
  const sharedTermCount = [...sourceTerms].filter((term) => candidateTerms.has(term)).length;
  let score = 0;
  score += sharedTopicCount * 8;
  score += sharedTermCount * 2;
  if (article.articleCategory === candidate.articleCategory) score += 4;
  if (article.product === candidate.product) score += 3;
  if (article.intent && article.intent === candidate.intent) score += 3;
  if (article.section === candidate.section) score += 2;
  return score;
}

function getArticleTopicSlugs(article) {
  return getArticleSearchTerms(article)
    .map((term) => getTopicForLabel(term)?.slug)
    .filter(Boolean);
}

function getArticleSearchTerms(article) {
  return uniqueList([
    article.primaryKeyword,
    ...(article.secondaryKeywords || []),
    ...(article.originalTags || []),
    ...(article.tags || []),
  ]);
}

function compareArticleSerial(a, b) {
  return String(a.serial || "").localeCompare(String(b.serial || ""), "en", { numeric: true });
}

function uniqueLinks(items = []) {
  const seen = new Set();
  return items.filter((item) => {
    if (!item?.href || seen.has(item.href)) return false;
    seen.add(item.href);
    return true;
  });
}

function buildArticleCta(article, productTheme, route = {}) {
  if (!article && route.product) {
    const productLinks = getProductHubCtaLinks(route.product);
    return {
      title: "從哪篇開始？",
      body: `${productTheme.label}文章會先把同分類內容放在一起。先讀基礎概念，再依照感情、事業、人際、財富或人生方向補充情境文章。`,
      links: productLinks,
    };
  }
  if (!article) return null;
  return null;
}

function getProductHubCtaLinks(product) {
  if (product === "fortune") return [
    { label: "fortune-0001 命盤是什麼", href: "/articles/fortune/fortune-0001" },
    { label: "fortune-0002 八字是什麼", href: "/articles/fortune/fortune-0002" },
    { label: "fortune-0003 紫微斗數是什麼", href: "/articles/fortune/fortune-0003" },
  ];
  if (product === "personality") return [
    { label: "personality-0001 MBTI 是什麼", href: "/articles/personality/personality-0001" },
    { label: "personality-0002 16 型人格完整整理", href: "/articles/personality/personality-0002" },
    { label: "interpersonal-0001 人際關係卡住怎麼辦", href: "/articles/interpersonal/interpersonal-0001" },
  ];
  if (product === "tarot") return [
    { label: "tarot-0001 塔羅牌意思總覽", href: "/articles/tarot/tarot-0001" },
    { label: "tarot-0002 塔羅牌正位逆位", href: "/articles/tarot/tarot-0002" },
    { label: "love-0001 感情塔羅怎麼問", href: "/articles/love/love-0001" },
  ];
  return [
    { label: "astrology-0001 星盤是什麼", href: "/articles/astrology/astrology-0001" },
    { label: "astrology-0002 上升星座是什麼", href: "/articles/astrology/astrology-0002" },
    { label: "astrology-0003 月亮星座是什麼", href: "/articles/astrology/astrology-0003" },
  ];
}

function getProductEntry(label) {
  if (label === "人格") return "看人格文章，整理你的反應模式";
  if (label === "塔羅") return "看塔羅文章，整理當下問題";
  if (label === "命盤") return "看命盤簡介，了解長期底色";
  if (label === "星座") return "看星盤或星座落點，整理情緒和安全感";
  return "先選一篇最接近你問題的 Pantheon 文章";
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
  if (article.product === "personality") return "人格類型適合描述偏好與互動模式，不適合拿來替一個人貼永久標籤，也不能取代專業評估。";
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
