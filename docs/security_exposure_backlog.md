# Pantheon Security / Exposure Backlog

更新：2026-09-09
狀態：`ACTIVE / SECURITY HARDENING`
定位：本檔為 Pantheon 目前最新的 cross-cutting security backlog；不取代 `docs/content_expansion_backlog.md` 的內容產品主線，也不改寫既有 publishing priority。
用途：記錄公開 repo 與 production-facing surface 的防護缺口。此檔只保存修補目標與驗收條件，不保存 exploit payload、真實 secret、production credential、攻擊步驟或可直接重現的濫用細節。

## P0 — Network trust boundary hardening

### SEC-P0-01 — SEO audit outbound fetch / redirect boundary

**狀態：MISSING / BLOCKING**

目標：`/api/v1/seo/audit` 的每個 outbound network hop 都必須重新通過 public-destination admission；不得只驗證初始 URL 後交由 client 自動跟隨 redirect。

最低要求：

- redirect 逐跳處理並限制 hop 數。
- 每個 hop 重新驗證 scheme、host、port 與 global-address policy。
- resolution / connect identity 不可在驗證後無界漂移。
- local / private / loopback / link-local / non-global destination fail closed。
- 驗證失敗不得留下 partial audit result。

驗收：加入 redirect、resolution drift、non-global destination、正常 public redirect 的 regression tests；現有公開網站 audit 不回歸。

### SEC-P0-02 — Default branch governance

**狀態：MISSING**

目標：`main` 不再依賴單一帳號／單一 automation token 的直接寫入安全。

最低要求：

- require PR。
- required CI / review gate。
- 禁止 force push / branch deletion。
- automation 必須走可追蹤 mutation path。

驗收：branch rule/ruleset 生效且正常 release path 可運作。

## P1 — Resource / abuse boundaries

### SEC-P1-01 — SEO crawler response budget

**狀態：MISSING**

目標：所有 HTML/XML/text fetch 都有明確 byte / decompressed-size budget，不使用 unbounded `read()`。

最低要求：per-response hard cap、total-request budget、timeout、過大 body 明確失敗。

### SEC-P1-02 — Public SEO audit rate / concurrency budget

**狀態：MISSING**

目標：公開 server-side crawler 必須有 per-client rate limit、concurrency cap、total fetch budget 與 domain cooldown；若此能力只供內部使用，則改為 authenticated/internal-only surface。

### SEC-P1-03 — CORS scope narrowing

**狀態：PARTIAL**

目標：CORS 僅允許 Pantheon own production / bounded preview origins；不得信任整個共享 hosting namespace。

驗收：own production + approved preview 通過，其他 unrelated origins 被拒絕；CORS 不被當作 authentication。

## P1 — Public repository exposure hygiene

### SEC-P1-04 — Tracked `.work` exposure review

**狀態：MISSING**

目標：盤點目前已追蹤的 `.work/`、recovery、canary、activation、diagnostic evidence；分類成 `PUBLIC_REPRO_EVIDENCE / INTERNAL_DEFENSIVE_INTELLIGENCE / REMOVE_FROM_PUBLIC_HISTORY_GOING_FORWARD`。

規則：

- `.gitignore` 只保護未追蹤檔案；已 commit 的 `.work` 必須另行處理。
- public repo 不新增 production failure intelligence、secret、credential、internal path 或攻擊細節。
- 必要 remediation evidence 放 private workspace；public commit 只保留乾淨 patch 與 bounded rationale。

## Current checks

- `.env.example` 目前只含空 API-key placeholder：`PASS`。
- `main` branch protection：`MISSING`。
- historical secret absence 尚未完成 full-history object scan；目前只能標 `NOT_FOUND_IN_BOUNDED_CHECK`，不得宣稱 `VERIFIED_ABSENT`。

## 後續驗證

完整歷史 secret audit 應在可取得完整 Git history 的隔離環境使用 gitleaks / trufflehog 類工具執行；若命中真 secret，只記錄位置與 rotate requirement，不把 secret 值複製進公開 issue、backlog 或 PR。
