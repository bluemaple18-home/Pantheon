import { getProductThemeRecord, listArticleRecords } from "./article-registry.js";

const articleGrid = document.querySelector("[data-home-articles]");

renderLatestArticles();

function renderLatestArticles() {
  if (!articleGrid) return;
  articleGrid.replaceChildren(...pickLatestArticles(listArticleRecords()).map((article) => {
    const productTheme = getProductThemeRecord(article.product);
    const card = document.createElement("a");
    card.className = "home-article-card";
    card.href = `/articles/${article.product}/${article.slug}`;
    card.dataset.productTheme = article.product;
    card.dataset.themeGlyph = productTheme.glyph;

    const meta = document.createElement("div");
    meta.className = "home-article-meta";

    const product = document.createElement("span");
    product.className = "home-article-product";
    product.textContent = productTheme.label;

    const keyword = document.createElement("span");
    keyword.className = "home-article-keyword";
    keyword.textContent = article.primaryKeyword;

    const title = document.createElement("strong");
    title.textContent = article.title;

    const description = document.createElement("p");
    description.textContent = article.description;

    meta.append(product, keyword);
    card.append(meta, title, description);
    return card;
  }));
}

function pickLatestArticles(articles) {
  return articles.slice(0, 12);
}
