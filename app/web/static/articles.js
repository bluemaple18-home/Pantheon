import { getArticlePath, getProductThemeRecord, listArticleRecords } from "./article-registry.js?v=articles-hub-20260710-logo-2";
import { initPantheonAnimatedLogos } from "./pantheon-logo.js?v=articles-hub-20260710-logo-2";

const articleGrid = document.querySelector("[data-home-articles]");
const SEARCH_SNIPPETS = {
  "mbti-meaning": "MBTI 用四組偏好組成 16 型人格，常用來理解自我、溝通和工作模式，但不能當心理診斷。",
  "16-personalities": "16 型人格整理每一型常見特質、感情、人際和工作傾向，適合先建立快速對照。",
  "mbti-test": "做 MBTI 測驗前，先知道題目會受狀態和情境影響，結果適合參考，不適合直接貼標籤。",
  "mbti-accuracy": "MBTI 讓人覺得準，多半因為它描述偏好；但偏好不是固定人格，也不是科學診斷。",
  "intj-meaning": "INTJ 常見關鍵字是策略、長期規劃和系統思考；感情與工作仍要看實際情境。",
  "infp-meaning": "INFP 常重視價值感、真實關係與內在一致，不等於脆弱，也不等於不切實際。",
  "infj-meaning": "INFJ 常被連到洞察、理想和深層關係；稀有不代表優越，也不能決定人生結果。",
  "enfp-meaning": "ENFP 常擅長看見可能性和建立連結；熱情不等於三分鐘熱度，也不代表沒有方向。",
  "tarot-card-meanings": "塔羅牌意思先看 78 張牌的象徵、正位與逆位，再放回問題和牌陣一起判讀。",
  "upright-reversed": "塔羅正位逆位不是單純好壞，而是看能量順不順、是否過度、阻塞或需要調整。",
  "birth-chart-meaning": "命盤是把出生資料轉成命理系統的分析語言；八字、紫微和星盤看的角度不同。",
  "birth-chart-astrology": "星盤用行星、宮位和星座看性格與生命主題，不能只看太陽星座就下結論。",
};

renderLatestArticles();
initPantheonAnimatedLogos();

function renderLatestArticles() {
  if (!articleGrid) return;
  articleGrid.replaceChildren(...pickLatestArticles(listArticleRecords()).map((article) => {
    const productTheme = getProductThemeRecord(article.product);
    const card = document.createElement("a");
    card.className = "home-article-card";
    card.href = getArticlePath(article);
    card.dataset.productTheme = article.product;
    card.dataset.themeGlyph = productTheme.glyph;

    const meta = document.createElement("div");
    meta.className = "home-article-meta";

    const serial = document.createElement("span");
    serial.className = "home-article-serial";
    serial.textContent = article.serial;

    const product = document.createElement("span");
    product.className = "home-article-product";
    product.textContent = productTheme.label;

    const keyword = document.createElement("span");
    keyword.className = "home-article-keyword";
    keyword.textContent = article.primaryKeyword;

    const title = document.createElement("strong");
    title.textContent = article.title;

    const description = document.createElement("p");
    description.textContent = SEARCH_SNIPPETS[article.slug] || article.description;

    meta.append(serial, product, keyword);
    card.append(meta, title, description);
    return card;
  }));
}

function pickLatestArticles(articles) {
  return articles.slice(0, 12);
}
