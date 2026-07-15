# CARD-SEO-GEO-INFRA-003｜Live deploy audit

## 任務目的

部署後驗證 production `https://mysticpantheon.com` 的 SEO / GEO 基礎工程是否真正生效。

## 目前狀態

`BLOCKED (deploy scope mixed)`

已完成 live predeploy baseline，但尚未部署。原因是目前 worktree 同時包含：

- 基礎工程：`llms.txt`、`ai.txt`、RSS feed、raw article shell、audit tool 修正。
- 先前 content gap / keyword 對標相關變更。
- schema/entity/E-E-A-T 前台模板修正。
- 多組 evidence / task card 未追蹤檔。

使用者已明確指示「關鍵字先不用對標，先把基礎工程打理好」，因此不能把整包 dirty changes 直接 commit / push 到 production。

## 請讀

- `docs/pantheon_deployment_workflow.md`
- `artifacts/fortune_council/seo_geo_fix_execution/result.md`
- `artifacts/fortune_council/seo_geo_fix_execution/evidence/live_predeploy/live_own_site_seo_audit.md`

## 部署前 live baseline

- `llms.txt`：`fallback_html`
- `ai.txt`：`fallback_html`
- `feed`：present，但 body bytes 與 fallback HTML 相同
- Schema depth：20
- E-E-A-T：0
- Citability：60
- Entity：50

## 接受標準

部署後 production audit 必須達成：

- `/llms.txt`：present / valid text endpoint
- `/ai.txt`：present / valid text endpoint
- `/feed/`：present / RSS XML
- `/articles/tarot/tarot-0001` raw HTML：Article + BreadcrumbList + FAQPage JSON-LD，無 parse error
- Schema depth >= 80
- E-E-A-T >= 80
- Entity >= 80
- `git diff --check` 通過
- production audit evidence 已歸檔

## 下一步

先切乾淨部署 scope，再 commit / push：

1. 建立只包含基礎工程的 deployment slice。
2. 不納入 keyword/content-gap 對標區塊，除非 PM 重新批准。
3. 跑全套測試與 `git diff --check`。
4. commit + push `main`。
5. 等部署完成後重跑 production audit。

## 證據路徑

`artifacts/fortune_council/seo_geo_fix_execution/evidence/live_predeploy/`
