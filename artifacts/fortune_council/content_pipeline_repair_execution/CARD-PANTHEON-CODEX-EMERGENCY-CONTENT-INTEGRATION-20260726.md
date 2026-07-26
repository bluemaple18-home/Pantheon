# CARD-PANTHEON-CODEX-EMERGENCY-CONTENT-INTEGRATION-20260726

目的：把 A/B/C 三個 emergency content source commits 整合為正式網站內容 candidate，但不 push、不 merge、不 deploy。

Base lock：
- `origin/main` / `FETCH_HEAD`: `5ee733697727512e9c7bddb0572eedff4dd691c1`

輸入 commits：
- A: `9c4821794bc7476a320a579d756d8cf19a4053bc`
- B: `e97d609e098d94e542c939e527d303335852bac7`
- C: `472dae1513156d77d40ff0c06dfcc24b290b70ee`

整合範圍：
- 新文 4 篇：A 2、B 2。
- Rewrite 2 篇：固定 source `ASTRO-BASE-02`、`ASTRO-BASE-03`，保留既有 identity/canonical，不算新文。
- 多語 18 篇：`en` / `ja` / `ko` 各 6，其中 new 4、rewrite 2。

Allowlist：
- 三個 source artifact/card。
- 本卡。
- 必要 `app/web/static/article-*.js`。
- 共享 registry / locale manifest。
- generator 產生的 `app/web/seo/**`、`app/web/sitemap.xml`、`app/web/feed.xml`、`app/web/_redirects`。
- 直接相關 tests/evidence。

禁止範圍：
- queue / ledger / publisher state / launchd / credential。
- Gemini / V4 / failed / rejected / quarantined / deferred 狀態檔。
- production pipeline / publisher code。
- push / merge / deploy。
- 偽造 Gemini approval 或 receipt。

驗證契約：
- provenance 與 allowlist。
- 數量與來源分流：new 4、rewrite 2、en/ja/ko 各 6。
- ID / serial / slug / canonical / locale path 唯一。
- publication standard：answer、meta、fixed tags、FAQ 3-5、必要 H2、延伸閱讀。
- humanizer 禁詞、重複句、translation source、rewrite drift。
- prerender、sitemap、feed、redirect。
- 受影響 pytest、`git diff --check`、worktree preflight。
