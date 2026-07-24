---
id: CARD-PANTHEON-PUBLISHER-DEADLOCK-REPAIR-20260724-root-cause
status: DELIVERED_CANDIDATE
type: implementation-evidence
---

# Root cause

## 已確認事實

1. `publish_ready_runs`、`publish_ready_rewrite_runs`、`publish_ready_translation_runs` 都在正式 actor worktree 直接套用候選、改版本、產生頁面、跑測試、commit、tag、release gate 與 push；原流程沒有涵蓋整段的失敗回復邊界。
2. translation release 只把 `tests/test_web.py` 的 `ARTICLE_CACHE_TOKEN` 改成 `agy-i18n-<version>`，沒有像 create/rewrite release 一樣呼叫 `_bump_article_cache_queries()`。因此測試期望已更新，`app/web/article.html` 與 `app/web/articles.html` runtime query 仍可停在舊 token。
3. gate 在 commit 前失敗時，版本、locale registry、generated locale module、測試 fixture 與 changelog 會留在 worktree；下一輪的 clean-origin gate 因此固定回報 `repo worktree is not clean`。
4. commit/tag 後的 release gate 或 push 若失敗，舊流程也沒有本地回復；而非 atomic push 另有 commit/tag 遠端半成功風險。
5. Gemini runner 的一般 generation 例外已會寫入 `failed/<job_id>.json`。未隔離的接縫是 coordinator 呼叫 runner 時，runner 邊界若直接拋 `JSONDecodeError`，例外會逸出 `cycle_once()`，中止整輪。

## 修復

- 三種 publisher phase 共用 recoverable transaction wrapper。
- transaction 只在初始 clean repo 啟動；失敗先保存 patch、untracked 檔案、錯誤型別、HEAD/tag 與 status，再把本輪 repo 變更回復到明確 base SHA。
- run directory、queue、ledger 與 transaction evidence 不在 repo rollback 集合；候選保留為 retryable。
- translation release 由同一個 `cache_token` 同步更新 runtime queries 與 `tests/test_web.py`。
- release commit 與 tag 改為 `git push --atomic`。
- coordinator 將 runner 邊界的 `JSONDecodeError` 回報為具 `job_id` 與 `error_type` 的 failed runner result，run state 維持 active，可由既有 transport retry 邊界接手。

## 被否證假說

- 「queue/ledger 被截短造成 deadlock」：沒有證據；deadlock 的直接 blocker 是 publisher worktree dirty。
- 「所有 malformed JSON 都被 runner 靜默吞掉」：不成立；runner 已保存一般失敗記錄。缺口只在 coordinator 對 runner 直接例外的隔離。
- 「只需手動清除 v0.3.59」：不成立；不修 transaction 與 token 契約，下一次 gate fail 仍會重現。
- 「V4 rollout 是本次必要修復面」：不成立；本修復未改 V4 預設或 rollout 設定。
