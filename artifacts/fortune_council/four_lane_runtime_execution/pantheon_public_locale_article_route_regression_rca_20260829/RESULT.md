# RESULT：Pantheon 公開 locale 文章路由回歸 RCA

status: `GO_RCA_CLOSED`
main_decision: `NO_PUBLIC_RUNTIME_REGRESSION`
matrix_finding: `REJECTED_EVIDENCE_MODALITY_MISMATCH`
production_mutation: `false`

## 單一主裁決

`/ja/articles/tarot/tarot-1884` **沒有發生從 PASS 到 RED 的 public runtime 回歸**。形成鏈只有一條：四線矩陣把 Gen06 的 **browser-rendered DOM PASS**，拿去和稍後的 **raw HTTP response shell RED** 比較；兩者不是同一觀測層，因此把既有架構行為誤判成 runtime regression。

目前同一 URL 的證據是：

- raw HTTP contract probe 確實是 RED：HTTP 200，但 canonical `/articles`、title／H1 `最新文章`，且沒有目標日文正文 sentinel。
- 現在的 browser-rendered DOM 是 PASS：canonical、title、H1、日文正文 sentinel 全部正確，載入 `article.js?v=agy-i18n-0-3-374`，console warning／error 為 0。
- 更關鍵的是，Gen06 首次 PASS 當時保存的 raw HTTP body 本來也是同一份 generic shell。歷史 raw 與現在 raw 去除 Cloudflare email-protection 隨機 token 後 byte-identical。

所以 raw RED 是一條可重現的「更強 raw-HTML 契約」測試，不是這次 release 後才形成的回歸。四線矩陣對 `i18n-new` 的 `BLOCKED: PUBLIC_LOCALE_ARTICLE_ROUTE_RETURNS_GENERIC_ARTICLE_LIST` 不成立，應撤回；它不能阻擋後續四線 acceptance。這不等於四線全部通過，`new`／`rewrite` 的 current revision E2E 與 `i18n-rewrite` 的正式 E2E 仍按原矩陣分別處理。

## 已實跑 RED-capable command

命令位於 `http_dom_contract_probe.py`，同時驗 status、canonical、title、H1 與 unique body sentinel；列表 fallback 即使 HTTP 200 也會 exit 1。

本次實跑：

- exit code：`1`
- status：`200`（唯一通過項）
- canonical：實際 `https://www.mysticpantheon.com/articles`，預期 locale article URL
- title：實際 `最新文章 | Pantheon`
- H1：實際 `最新文章`
- sentinel `金銭における死神の意味と現状の見直し`：不存在
- verdict：`RED`

這條 RED 的正確解讀是「raw response 沒有 prerendered locale article DOM」；不能單獨推導「瀏覽器公開文章壞掉」。

## Formation timeline

| 時間（UTC） | 事件 | 證據含義 |
|---|---|---|
| 2026-08-29 03:20:59 | release commit `22d7e21b...` 與 annotated tag `v0.3.374` 形成 | parent 是 `dfcb3c77...`。 |
| 2026-08-29 03:21:26 | GitHub check `Cloudflare Pages` success | deployment `bbad7483-e5c5-4e02-b382-1e176b8b5031`。 |
| 2026-08-29 03:22:51 | Gen06 保存 raw public body | 當時已是 `最新文章`／canonical `/articles`；`cf-cache-status: DYNAMIC`。 |
| 約 03:22:51 | Gen06 保存 rendered DOM PASS | 日文 title／canonical／正文全存在；rendered DOM SHA `51b987...`。 |
| 03:46–03:47 | 四線矩陣以兩次 raw GET 重驗 | 得到同一 generic shell，跨層比較後誤判回歸。 |
| 03:53:28 | 本 RCA 重抓 raw body | 與 03:22:51 歷史 raw shell 正規化後完全相同；`cf-cache-status: DYNAMIC`。 |
| 約 03:56 | 本 RCA 重跑 browser rendered DOM | 目標 URL、一般 localized control、astrology-0003 control 全 PASS。 |

GitHub `main` 在本次 probe 時仍是 `22d7e21b...`。沒有 22d7 後的新 release／deployment 可構成回歸區間。

## Origin 22d7、Cloudflare 與 public bytes

`22d7` 的 authoritative release artifact 與現在 public assets 一致：

| asset | origin 22d7 SHA256 | public SHA256 | 結果 |
|---|---|---|---|
| `static/article.js` | `73c01ef2...` | `73c01ef2...` | exact |
| `static/article-locales.js` | `9c4ec617...` | `9c4ec617...` | exact |
| target JA locale record | `2c73125d...` | `2c73125d...` | exact |

公開 article shell 只多了 Cloudflare email obfuscation；移除該轉換後，其 SHA 與 origin `22d7` 的 `app/web/article.html` 完全一致。這證偽 hosting revision、asset cache 或 deploy drift。

release diff 也沒有生成 locale-specific SEO HTML。`22d7` 新增 target JA locale JS record、更新 locale registry，並把 article cache token 升為 `agy-i18n-0-3-374`；`_redirects` 與 parent `dfcb` 完全相同。

## 假說排序與證偽

### 1. Acceptance evidence modality mismatch — confirmed root cause

預測：若是跨 raw／rendered 觀測層誤判，歷史 raw 也應是 generic shell，而現在 rendered DOM 仍可正確呈現。

結果完全符合：歷史與現在 raw shell 正規化後相同；現在 rendered DOM 全部正確。單一故障 layer 是 **acceptance aggregation／public probe classifier**，authoritative owner 是四線 current acceptance 的證據收集與裁決，不是 Cloudflare、Publisher 或 client runtime。

### 2. Cloudflare deploy／asset cache version drift — falsified

- Cloudflare Pages 對 `22d7` 的 check completed / success。
- public 三個關鍵 JS asset 與 origin `22d7` SHA 精確相同。
- shell 載入正確 cache token `agy-i18n-0-3-374`。
- current HTTP 是 `cf-cache-status: DYNAMIC`。
- current rendered DOM 正確。

### 3. Client router locale lookup fallback — falsified

若 target record lookup 失敗，JS 執行後仍會停在 generic metadata 或 fail-closed redirect；實際 rendered target 的 canonical／title／H1／正文 sentinel 全正確。一般 JA localized route與 `astrology-0003` 控制路徑也正確渲染日文正文。

### 4. Generated localized SEO route missing／wrong content — confirmed as pre-existing gap, not regression

這個假說能解釋 raw RED，但不能解釋「從 PASS 回歸」：

- dynamic locale article routing 由 commit `396266bd277608d7122b29ee8ee3daa19ae155ef`（2026-07-27，`Publish multilingual article routes (#11)`）引入，將 `/ja/articles/*` rewrite 至 client-rendered article shell。
- commit `93edf8cfe5f95555d30b65fe1e5c898ed8770430` 只把 Cloudflare rewrite target 從 `/article.html` 修成 `/article`。
- `22d7` 沒改 `_redirects`，也沒有生成 locale-specific prerendered HTML。

若 Owner 現在要求「不執行 JS 的 crawler 也必須從 raw HTML 取得 locale canonical／正文」，這是一個真實的 SEO architecture gap，其 authoritative owner 才是 `scripts/prerender_article_shells.py` ＋ `app/web/_redirects`／build output contract；但它不是 Gen06 後的 regression，也不應偷渡進本次 acceptance repair。

## Durable invariant

目前架構的 durable invariant 必須分層：

1. raw transport invariant：locale path HTTP 200、回傳可載入且版本正確的 article shell，關鍵 JS assets 可取得且 release identity 正確。
2. rendered public invariant：JS 完成後 canonical、title、H1、locale、unique body sentinel 都必須對應 exact article；generic list fallback 必須 RED。
3. evidence comparison invariant：current 與 baseline 必須在同一觀測層比較；raw 不得和 rendered 互相比較後宣稱 regression。

最後一次成功 deploy／public bytes 就是目前的 `22d7`／Cloudflare deployment `bbad7483...`；沒有「最後成功後被另一版覆蓋」的證據。raw shell 自首次 PASS 至今未變，rendered target 至今仍 PASS。

## 影響面

- `i18n-new`：本次 public route blocker 應撤回；current rendered target PASS。
- `i18n-rewrite`：沒有共享 locale route outage。`/ja/articles/astrology/astrology-0003` 的 current rendered route PASS；但這只證偽路由故障，不補足該 lane 所缺的 current Writer→Reviewer→publish E2E。
- 一般 localized routes：抽查 `/ja/articles/astrology/astrology-0181` rendered PASS。所有 `/en|ja|ko/articles/*` raw response 共享 generic shell 是既有設計，不是目前 runtime outage。

## 單一最小 Repair frontier

`REPAIR_CURRENT_ACCEPTANCE_EVIDENCE_MODALITY`

只修 current acceptance 的 probe／classifier：保存 raw 與 rendered 兩份 evidence，各自套對應 invariant；route/body acceptance 以同一個 JS-enabled rendered DOM command 做 baseline/current 比較，並讓 rendered generic list fallback fail closed。然後更正四線矩陣中 `i18n-new` 的 route blocker 狀態。

- `why_not_less`：只手動改矩陣文字、沒有固化同層 probe，下一次仍會把 raw shell 誤判為 rendered regression。
- `why_not_more`：public assets、deployment 與 client locale lookup 都已通過，沒有 measured gap 支持 publisher retry、cache purge、redirect 修改或 deploy。
- `do_not_absorb`：不在這張 Repair 生成全語系 prerender tree、不改 Cloudflare architecture、不重發文章、不重跑 provider／Reviewer／Publisher、不建立第二套 deployment/version authority。

若 Owner 要新增 raw localized SEO invariant，應另立產品／SEO task，先量測 crawler/indexing gap與 storage/build 成本；不得把它稱為本次 regression repair。

## Evidence index

- `raw-http-red-probe.json`
- `http_dom_contract_probe.py`
- `browser-rendered-probes.json`
- `release-public-byte-comparison.json`
- `formation-timeline.json`
- `hypothesis-verdicts.json`
- Gen06 historical raw：`../pantheon_acceptance_b_gen06_final_publish_acceptance_20260829/resume-dfcb-public-ja.body.html`
- Gen06 historical rendered DOM：`../pantheon_acceptance_b_gen06_final_publish_acceptance_20260829/resume-dfcb-public-ja-rendered-dom.html`
- Gen06 rendered validation：`../pantheon_acceptance_b_gen06_final_publish_acceptance_20260829/resume-dfcb-public-ja-rendered-validation.json`

## Not claimed

- 未宣稱四線全通。
- 未改 source、tests、build、public、Cloudflare config／remote、queue／state／runtime。
- 未 commit、push、deploy、publisher、provider 或 reviewer。
- 未把 raw SEO gap 自動升格為本次產品需求。
