---
id: CARD-SEO-MULTILINGUAL-001
status: implemented_browser_no_go
type: implementation
---

# Pantheon 多語文章與國際 SEO

## Root question

如何沿用現有文章產製、Reviewer、approval 與 publisher gate，讓同一篇文章安全發布繁中、英文、日文與韓文版本，並由搜尋引擎辨識為互為翻譯的頁面？

## Scope

- 保留既有繁中 URL，不做搬遷。
- 語系 URL 使用 `/en/articles/...`、`/ja/articles/...`、`/ko/articles/...`。
- 同一文章以既有 `article_id` 對應各語系；語言切換停留在同一篇文章。
- 每個語系頁自我 canonical，並輸出雙向 `hreflang` 與 `x-default`。
- Sitemap 只收錄通過 Reviewer 與人工 approval、且已發布的翻譯。
- 母語重寫沿用現有 Writer／native editor → deterministic gate → Reviewer → approval → publisher 邊界。
- 第一階段只發布少量 canary，不批量索引全站機翻。

## Out of scope

- 國家、幣別、時區或地區版內容。
- IP、GeoIP 或瀏覽器語言強制跳轉。
- 子網域、國別網域或既有繁中 URL 搬遷。
- 未經 approval 的自動發布。

## Requirements

- `FR-I18N-001`：系統 SHALL 以 locale-prefixed URL 提供已核准的翻譯頁。
- `FR-I18N-002`：每個已發布語系頁 SHALL 使用自身 URL 作 canonical。
- `FR-I18N-003`：WHEN 同一文章有多個已發布語系，系統 SHALL 在每個版本輸出包含自身的雙向 `hreflang`。
- `FR-I18N-004`：語言切換器 SHALL 只連到同一文章已發布的語系版本，繁中原文永遠可用。
- `FR-I18N-005`：翻譯 candidate SHALL 綁定原文內容 SHA-256；原文漂移時 publisher SHALL fail closed。
- `FR-I18N-006`：母語重寫 SHALL 經過 schema、語系 editorial contract、結構去鏡射、語言、Reviewer hash 與人工 approval gate。
- `FR-I18N-007`：Sitemap SHALL 只包含已發布語系，並為同一文章輸出一致的 alternate 集合。

## Slices

### `SL-I18N-CONTRACT`

- traces_to：`FR-I18N-005`、`FR-I18N-006`
- 產出：語系常數、母語重寫資料 schema、來源 hash 與 deterministic validator。
- 驗證：unit tests；錯誤 locale、欄位漂移、來源 hash 漂移必須退件。
- blocker：無。

### `SL-I18N-RUNTIME`

- traces_to：`FR-I18N-001`、`FR-I18N-002`、`FR-I18N-004`
- 產出：locale route 解析、翻譯 lookup、語言切換器與 locale-aware metadata。
- 驗證：Node/runtime tests 與 prerender HTML assertions。
- blocker：`SL-I18N-CONTRACT`。

### `SL-I18N-SEO`

- traces_to：`FR-I18N-002`、`FR-I18N-003`、`FR-I18N-007`
- 產出：canonical、HTML `lang`、Open Graph locale、JSON-LD `inLanguage`、`hreflang`、sitemap alternates。
- 驗證：generated HTML/sitemap tests。
- blocker：`SL-I18N-RUNTIME`。

### `SL-I18N-WORKFLOW`

- traces_to：`FR-I18N-005`、`FR-I18N-006`
- 產出：現有 Writer/Reviewer transport 的 native editorial mode、approval apply 與 per-run locale module。
- 驗證：pipeline/publisher unit tests；dry-run canary artifacts。
- blocker：`SL-I18N-CONTRACT`。

### `SL-I18N-CANARY`

- traces_to：全部 `FR-I18N-*`
- 產出：至少一篇文章的 en/ja/ko candidate、review、approval 或明確 pending 證據。
- 驗證：生成器、focused tests、`git diff --check`、瀏覽器 user path。
- blocker：前四個 slices。

## Acceptance

- 原繁中 URL 與內容不變。
- 已發布翻譯 URL 可直接開啟，不依 cookie 或 `Accept-Language`。
- 切換器能在同一篇文章的繁中／英／日／韓版本間移動。
- canonical、`hreflang`、JSON-LD 與 sitemap 相互一致。
- 未核准或來源已漂移的翻譯不會發布。
- 所有受影響測試、生成器、`git diff --check` 與瀏覽器驗收有可重跑證據。

## 2026-07-24 implementation evidence

- Branch：`codex/multilingual-seo`
- Canary source：`TAROT-BASE-01`（`/articles/tarot/tarot-0001`）
- Published locale routes：`/en/articles/tarot/tarot-0001`、`/ja/articles/tarot/tarot-0001`、`/ko/articles/tarot/tarot-0001`
- 真實工作流：既有 Antigravity CLI Writer → deterministic gate → 獨立 Reviewer → approval → apply。
- Native editorial canary：英文 `i18n-native-tarot-en-0006`、日文 `i18n-native-tarot-ja-0002`、韓文 `i18n-native-tarot-ko-0002` 均由獨立 Reviewer 核准。
- 舊 `i18n-canary-tarot-0002` 直譯式版本已移除；相同中文 H2／段落骨架現在會以 `structural_mirroring` hard finding 退件。
- Regression：`144 passed`；`git diff --check` 通過。
- Static evidence：三語 `html lang`、self-canonical、Open Graph locale、JSON-LD `inLanguage`、reciprocal `hreflang`、`x-default` 與 sitemap URL 均已生成。
- Browser：`NO-GO`。Playwright 在首次導頁前因本機缺少對應 Chromium binary 而無法啟動；未宣稱 UI browser acceptance 通過。
