# Bounded i18n replacement production canary｜2026-08-01

## Decision

```text
status: NO_GO_CONTENT_QUALITY
repair_deployed: true
production_output_count_this_card: 0
i18n_new_release: none
i18n_rewrite_release: none
production_canary_hold: true
services: unloaded
verified_at: 2026-08-01T02:07:13+08:00
```

本卡不能宣稱 production canary 完成。bounded replacement、deterministic
authority 與逐欄 target-locale 契約已推送及部署，flash-lite provider 也已真實
回應；但新候選未通過 Reviewer，因此沒有 Publisher release、tag 或新增公開
文章。原四線驗收的 v0.3.186–v0.3.189 歷史成功紀錄不受本卡影響。

## 更正先前 provider outage 結論

首輪六個 `API_HTTP_ERROR` 不是三個帳號同時故障。手動 canary 呼叫 `_advance`
時漏帶 production `AGY_WRITER_MODEL`，request 因而使用程式預設
`gemini-3.5-flash`；installed production profile 實際為
`gemini-3.5-flash-lite`。後者才會套用既有 provider enum complexity handling。

改用正式 model 後，locale-plan request 立即成功，證明 Google Gemini 與
credential pool 並未全面中斷。先前 `NO_GO_PROVIDER_UNAVAILABLE` 結論撤回。

## 已修的契約撞點

1. 保存 response 重播先穩定得到：
   `locale plan rebuild authority differs for article-01`。
2. `rebuild_outline` 本來由 pipeline 決定，卻同時要求 Gemini 回填，再以本機值
   比對；這與已修過的 fact 排序衝突同型。
3. `5386447c1` 現在只驗證 provider 欄位仍為 boolean，實際值由 pipeline
   authority canonicalize；fact、safety、語言、outline 與 Reviewer gate 不變。
4. 日文、韓文樣本其後又一致出現來源繁中殘留；`f00298681` 明確要求
   `title`、`description`、`answer`、`tags`、FAQ、H2、paragraphs 全部依
   `article input.locale` 重寫。

保存 production response 在 authority 修補前為 RED，修補後以同一份 bytes
通過 hydration，`coverage_count=17`；沒有重送或改寫舊 evidence。

## Production canary outcomes

| Lane | Run | 實際終點 | 發布 |
|---|---|---|---:|
| `i18n-new` | `manual-i18n-new-canary-v1-20260731-en-v2-mbti-pair-intp-esfj-work-replacement-01` | 正式 lite plan 成功；保存 response 重現 deterministic authority RED | 0 |
| `i18n-new` | `auto-i18n-ja-f5be5f2761b6489f44e8-replacement-01` | 三代完成；最終 Reviewer 因非日文、直譯與來源句法 `REJECT` | 0 |
| `i18n-rewrite` | `auto-i18n-ja-0c3530c8d30b3d2c38d7-replacement-01` | 第二代 deterministic findings 為 0；Reviewer 抓到中文殘留，第三代因重用被要求重建的 topology fail-closed | 0 |
| `i18n-new` | `auto-i18n-ko-d67f8ead32e1901409e9-replacement-01` | 第二代 deterministic findings 為 0；最終仍有繁中、直譯與來源句法，Reviewer `REJECT` | 0 |
| `i18n-new` | `auto-i18n-en-9811045f897b531ea0bd-replacement-01` | 新逐欄語言契約下三代 deterministic findings 均為 0；Reviewer 仍以來源句法與非母語搜尋意圖 `REJECT` | 0 |

每個 base 仍只有一個 `replacement-01`，沒有 `replacement-02`；source drift
仍保存 closed decision receipt，candidate quality rejection 不會被錯誤轉成新
replacement。

## Full Flash strict canary

為判斷 lite 是否為品質瓶頸，曾在不切排程的前提下，讓一個隔離
`i18n-rewrite` plan request 使用程式既有預設 `gemini-3.5-flash`。provider
payload 的大型 enum 已移除，實際 enum max 為 4，但 request 仍立即回
`API_HTTP_ERROR`。因此：

- full Flash 不能宣告支援目前 direct production API path；
- 不切換 production Writer model；
- capability 試驗 commit `362e3e474` 已由 `51d6cbb5c` 安全撤回；
- installed coordinator Writer 保持 `gemini-3.5-flash-lite`。

該 canary run `auto-i18n-ko-aff5c67c15dbae615544-replacement-01` 目前仍為
`active`，lane outbox 保存一個未呼叫的 transport attempt 1：
`542e316fd596eb10e2b6501fb285c644fab640d7`。它的 immutable model 是
`gemini-3.5-flash`。不得啟動 i18n-rewrite runner 讓它自動消耗；後續須另做
明確的 queue cancellation／terminalization 決策，不能偽造 provider receipt。

## Push and runtime alignment

- bounded replacement implementation: `7002e135f`
- deterministic rebuild authority repair: `5386447c1`
- target-locale prompt repair: `f00298681`
- final `origin/main` / production actor: `51d6cbb5ce45944863d50efe2d93fea795068a52`
- final runtime digest:
  `878b0a2c3a039dc0522ac69627926963b1bdad7f113b4c7a037b2354227b2814`
- Publisher deployment preflight: `status=ready`；actor、queue、state、SHA、digest
  與 push mode 全部 matched
- Publisher installed expected SHA/digest：與上述值一致

六個相關 LaunchAgent 均未載入：Publisher、coordinator、new、rewrite、
i18n-new、i18n-rewrite。

## Verification

- deterministic authority focused tests: `4 passed`
- multilingual + coordinator affected suites: `231 passed`
- final provider-schema + multilingual + coordinator suites: `353 passed`
- repository-wide regression after each retained code repair: exit `0`
- `git diff --check`: PASS
- production actor worktree: clean
- release-record pre-push hook: PASS

## Capacity snapshot

- filesystem: `228 GiB` total、`155 GiB` used、`26 GiB` available、`86%`
- Gemini queue root: `133 MiB`
- Publisher state root: `51 MiB`
- isolated repair worktrees: `97 MiB`

磁碟空間不是本次 deterministic 或 Reviewer failure 的根因；本卡沒有刪除
queue、ledger、archive、receipt、candidate 或既有 production evidence。

## Current production facts

- latest release tag reachable from runtime: `v0.3.221`
- public article count: `521`
- translation ledger historical published runs: `63`
- latest historical translation release: `v0.3.213`，run
  `auto-i18n-en-640c4d719e54c3f03bba`
- 本卡新發布：`0`

## Acceptance mapping

- bounded replacement、lineage、idempotency：PASS
- source drift fail-closed：PASS
- fact order canonicalization、rebuild authority：PASS
- flash-lite provider／credential pool 可用：PASS
- Writer 逐欄 target-locale 契約：PASS（production prompt 已取證）
- 真實 `i18n-new` 新 release：FAIL — Reviewer quality rejection
- 真實 `i18n-rewrite` 新 release：FAIL — quality／topology rejection，另有一筆
  unsupported-model canary pending operator decision
- fixture、idle、run complete 或服務綠燈冒充 release：NO

同一 `i18n-new` 品質 blocker 已在 ja、ko、en 三個獨立 bounded canary 重現，
因此依停損規則不再開第四個盲重試。下一步應先決定可受 production API 支援的
較高品質 Writer path，或設計獨立母語 editorial repair；在此之前保持
`production_canary_hold=true` 與六服務卸載。
