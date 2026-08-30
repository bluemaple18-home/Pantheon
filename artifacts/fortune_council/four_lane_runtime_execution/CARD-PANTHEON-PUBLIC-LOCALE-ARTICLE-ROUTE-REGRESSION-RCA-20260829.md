# PANTHEON 公開 locale 文章路由回歸 RCA

- 工作名稱：公開日文文章路由回歸唯讀 RCA
- 日期：2026-08-29
- 模式：standard／continue
- 角色：唯讀 RCA Worker

## 目的

針對 `https://www.mysticpantheon.com/ja/articles/tarot/tarot-1884` 在 HTTP 200 下回傳錯誤文章／列表 canonical 的 concrete RED，重建 formation timeline、定位單一故障 layer 與 authoritative owner，提出一個最小 Repair frontier；不得以換 URL 或中間 gate 代替公開網址驗收。

## 可寫範圍

- 本卡。
- `pantheon_public_locale_article_route_regression_rca_20260829/RESULT.md`。
- 同一結果目錄內的 machine evidence。

## 禁止範圍

- 不改 source、tests、build、public files。
- 不改 Cloudflare config／remote、queue／state／runtime。
- 不 commit、push、deploy、publisher、provider、reviewer。
- 不先做 Repair，不以替代 URL 假裝通過。

## 必要證據與驗收

1. 實跑一條 red-capable HTTP／DOM command，同時驗證 status、canonical、title／H1 與目標正文 unique sentinel；HTTP 200 列表 fallback 必須判 RED。
2. 讀四線矩陣 RESULT／machine receipt、Gen06 Final RESULT、release commit `22d7` diff／manifest／deployment evidence。
3. 還原 release push／tag、Cloudflare deploy、首次 PASS 與目前 RED 的時間、cache、host，並比較 `origin/main` 的 `22d7` build artifact 與 public bytes。
4. 排序並證偽至少兩個假說：generated localized SEO route、redirect／SPA fallback、Cloudflare deploy／asset cache drift、client router locale lookup fallback。
5. 精準定位單一 layer 與 authoritative owner，回答 durable invariant、最後成功 public bytes／deploy、引入 commit／機制、影響面是否包含 i18n-rewrite／一般 localized routes。
6. 交付單一主裁決與最小 Repair frontier，包含 `why_not_less`、`why_not_more`、`do_not_absorb`。

## 完成條件

- `RESULT.md` 清楚標示 `NO-GO`／`PARTIAL`／`BLOCKED` 之一，不在證據不足時宣稱完成。
- 所有主要判斷可由同目錄 machine evidence 或既有 artifact 路徑重現。
- `git diff --check` 通過；除允許輸出外沒有新增修改。
