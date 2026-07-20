# Pantheon 正式部署 Workflow

## 1. 目的

本文件規範 Pantheon 從改版到公開頁驗收的正式流程。任何會影響 `mysticpantheon.com` 公開頁、API、文章內容、SEO、sitemap、redirect、靜態資產 cache 的變更，都必須依照本 workflow 執行。

核心原則：

- 不能只說「推了」，要有測試與公開頁證據。
- 不能只驗本機，公開網址也要驗。
- 不能讓舊 cache 蓋住新內容。
- 不能把未關聯的 dirty changes 混進部署。
- 不能把內部管理語言、未達門檻 topic、錯誤 tag 規則推到公開頁。

## 2. 分支與部署來源

正式公開部署以 `main` 為 production source。

開始任何部署前先確認：

```bash
git worktree list
git status --short
git branch --show-current
```

規則：

- 只有確認要上線的變更可以進入 commit。
- 若 worktree 有不屬於本次任務的 dirty files，不能順手加入。
- `outputs/` 這類未追蹤輸出資料預設不加入 commit。
- 若目前不在 `main`，只能做開發與驗收；要正式上線必須明確合併或 cherry-pick 到 `main` 後推送。

## 3. 改版前檢查

每次部署前先確認變更類型。

| 類型 | 必查檔案 |
|---|---|
| 文章內容 / SEO | `app/web/static/article-registry.js`, `app/web/static/article-meta.js`, `app/web/static/article-seo.js` |
| 文章頁 UI | `app/web/article.html`, `app/web/static/article.js`, `app/web/static/styles.css` |
| 最新文章頁 | `app/web/articles.html`, `app/web/static/articles.js`, `app/web/static/styles.css` |
| 管理頁 | `app/web/article-admin.html`, `app/web/static/article-admin.js` |
| URL / sitemap | `app/web/_redirects`, `app/web/sitemap.xml`, `app/web/robots.txt` |
| API / 算力 | `main.py`, `app/api/`, `app/calculators/`, `app/ai/` |

部署前必須先看 diff：

```bash
git diff --stat
git diff --name-only
```

## 4. Cache 版號規則

靜態頁部署時，瀏覽器與 CDN 可能吃舊檔。凡是改到被 HTML import 的 JS/CSS，都要同步升 cache query。

| 變更 | 必須同步更新 |
|---|---|
| `app/web/static/article-meta.js` | `app/web/static/article.js` import query、`app/web/article.html` script query |
| `app/web/static/article-registry.js` | `article-meta.js` import query；若 admin 用到 registry，也更新 `article-admin.js` import query |
| `app/web/static/article.js` | `app/web/article.html` script query |
| `app/web/static/styles.css` | 對應 HTML 的 stylesheet query |
| `app/web/static/article-admin.js` | `app/web/article-admin.html` script query |
| `app/web/static/articles.js` | `app/web/articles.html` script query |

命名慣例：

```text
article-content-YYYYMMDD-N
article-product-theme-YYYYMMDD-N
tag-management-YYYYMMDD-N
```

完成後公開驗收必須確認頁面實際載入新 query，例如：

```text
/static/article.js?v=article-content-20260710-22
```

## 5. 文章與 SEO Gate

文章部署前必須符合：

- URL 使用流水號：`/articles/{category}/{category}-{number}`。
- canonical、breadcrumb、sitemap、上一篇/下一篇都使用正式 URL。
- 相關文章不顯示流水號。
- 可見延伸閱讀最多 6 條，可包含上一篇 / 下一篇、分類文章入口與推薦文章；推薦文章最多 5 篇。
- FAQ 不出現內部管理語言。
- topic 連結只給已達門檻的標籤。
- 未達 10 篇文章的標籤只能顯示 chip，不能產生公開集結頁。

目前 topic 生成門檻：

```text
PUBLIC_TOPIC_MIN_ARTICLES = 10
```

標籤規則：

- 顯示短標籤：`塔羅`、`愚者`、`正位`、`逆位`、`感情`、`工作`。
- 不顯示長詞標籤：`愚者牌正位`、`愚者牌逆位`、`工作塔羅`。
- 不把「關鍵字長詞」直接當 topic。
- topic 是否產生，以管理頁「標籤集結頁管理」為準。

## 6. 必跑測試

若本次涉及 API、算力或 `services/` Node bridge，先安裝 lockfile 指定的 Node 依賴：

```bash
pnpm install --frozen-lockfile
```

`services/ziwei/iztro_chart.mjs` 需要 `iztro`；缺少依賴時會依設計回退到 `pantheon_ziwei`，這不算正式 provider 驗收通過。

一般部署：

```bash
uv run pytest
git diff --check
```

如果本機 `uv run pytest` 因環境問題不可用，可用已建立的 `.venv`：

```bash
.venv/bin/python -m pytest
git diff --check
```

只改文章與前台時，至少先跑：

```bash
.venv/bin/python -m pytest tests/test_web.py
git diff --check
```

但收工前仍以全套測試為準。

## 7. 本機瀏覽器驗收

涉及 UI、文章、SEO、tag、cache、管理頁時，必須開本機 server 做瀏覽器驗收。

```bash
.venv/bin/uvicorn main:app --host 127.0.0.1 --port 9878
```

驗收頁面依變更選擇：

| 變更 | 至少驗收 |
|---|---|
| 單篇文章 | 對應文章 URL |
| 產品線頁 | `/articles/{product}` |
| 最新文章頁 | `/articles` |
| topic | `/topics/{topic}` 與未達標 topic redirect |
| 管理頁 | `/article-admin` |
| redirect | 舊 URL 與目標 URL |

瀏覽器驗收要確認：

- 文字實際出現在 DOM，不只看 source。
- 靜態資產 query 是新版本。
- mobile 版文字不溢出、不重疊。
- chip href 符合規則。
- FAQ、延伸閱讀、上下篇位置符合規範。

## 8. Commit 與 Push

### 8.1 文章發布版本與記錄

凡 push 範圍包含文章來源或預渲染文章頁，必須在同一個 release commit 完成：

1. 同步提升 `pyproject.toml` 與 `package.json` 的 SemVer 版本。
2. 在 `CHANGELOG.md` 最上方新增同版本記錄，至少包含日期、release tag、公開文章總數、發布範圍、驗證與證據路徑。
3. 建立指向 release commit 的 annotated tag：`v<version>`。
4. 執行 release gate，並在同一次 push 推送 `main` 與 tag。

```bash
.venv/bin/python scripts/check_release_record.py --base-ref origin/main --require-head-tag
git push origin main v<version>
```

啟用 repository hook 後，文章 push 若缺少升版、記錄、annotated tag，或 tag 未與 `main` 同次推送，pre-push 會拒絕操作：

```bash
git config core.hooksPath .githooks
```

一般文件或不涉及文章內容的修正不強制升版。

提交前檢查：

```bash
git diff --stat
git status --short
```

只加入本次變更檔案：

```bash
git add <file>
git commit -m "<短句說明>"
```

正式部署推送；非文章發布可只推 `main`：

```bash
git push origin main
```

禁止：

- 把不相關 dirty files 一起 commit。
- 用 `git reset --hard` 清工作區。
- 沒跑測試就推。
- 沒做公開頁驗收就宣稱完成。

## 9. 公開頁驗收

push 後等待部署完成，再驗公開網址。

必驗：

- 受影響公開 URL。
- 至少一個 mobile viewport。
- 靜態資產 query 是否更新。
- 這次修正的問題是否真的不存在。

範例驗收項：

```text
URL: https://www.mysticpantheon.com/articles/tarot/tarot-0003?codex_public_acceptance=<commit>
Script: /static/article.js?v=article-content-20260710-22
Expected tags: 塔羅 / 愚者 / 正位 / 逆位 / 感情 / 工作
Forbidden tags: 愚者牌正位 / 愚者牌逆位 / 工作塔羅
```

若公開頁仍載入舊 cache：

1. 不回報完成。
2. 等 20 到 60 秒再驗。
3. 若仍舊版，檢查 HTML 是否有升 query。
4. 若 HTML 已升但 JS 舊，檢查 import query。

## 10. 回退流程

若已推送但公開頁錯誤：

1. 先確認錯誤 URL、錯誤畫面、錯誤 commit。
2. 用 revert，不用 reset。

```bash
git revert <bad-commit>
git push origin main
```

3. 驗公開頁載入 revert 後的新 commit。
4. 回報回退 commit、公開驗收 URL、剩餘風險。

## 11. 回報格式

部署完成回報必須包含：

```text
Commit:
推送分支:
變更摘要:
測試:
本機瀏覽器驗收:
公開頁驗收:
公開頁載入的 cache query:
截圖或證據路徑:
未處理事項:
```

不得只回「已推」或「改好了」。

## 12. 最低完成標準

一次部署要算完成，必須同時滿足：

- 變更已 commit。
- 已推到 production source。
- 測試通過。
- `git diff --check` 通過。
- 公開頁載入新 cache。
- 公開頁驗到指定修正。
- 工作區沒有本次遺留修改。
- 若有未追蹤檔案，明確說明未加入原因。
