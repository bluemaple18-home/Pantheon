# Gemini 配額感知路由：待推送、整合與正式啟用

## Root Question

如何把已完成的 Gemini Writer／Reviewer 配額感知路由安全整合到 `main`，重產正式 runtime identity，完成 preflight／canary 後啟用內容流程？

## Goal

正式內容流程採以下固定契約：

- Writer：`gemini-3.5-flash`
- Reviewer：`gemini-3.1-flash-lite`
- Writer 日配額耗盡後：Writer 降為 `gemini-3.5-flash-lite`
- Reviewer 日配額耗盡後：Reviewer 降為 `gemini-3.5-flash-lite`
- Writer／Reviewer 不得同時使用相同模型；沒有合法不同模型配對時，停止領取新工作並保留 queue。
- RPM 429 與 503 只做既有 bounded retry／cooldown，不觸發模型降級。

## Constraints & Preferences

- 使用者已確認三把 API key 來自不同帳號、不同 Google project；可視為三個獨立 project slot。
- production 仍須先輪完同一模型的三個 project slot；只有三個安全 slot identity 都回報每日 quota exhausted 才可降級。
- 不保存 provider message、原始 response、API key、quota metadata value 或私密 project identity。
- production mutation、launchd 安裝／啟用、canary 與發文都尚未執行。
- 主工作區很髒；不得把主工作區既有修改混入本分支。整合須使用乾淨 worktree／integration branch。
- 共享文件與命令一律使用 `<repo-root>` 或 repo-relative path。

## Completed Actions

- 任務卡：`.ai/codex_task_gemini_model_quota_fallback_20260817.md`
- 功能分支：`codex/gemini-model-quota-fallback-20260817`
- 功能 commit：`802133cc99f8f329e8d46b1ca3756db103d95980`
- 基底：`origin/main` 的 `2d8d8cb27e872f21c445d863bd7e15dbd1c0a7f7`
- 已完成封閉 429 classifier：
  - GenerateContent 真實 `QuotaFailure.quotaId` 含 `PerDay` → `API_QUOTA`
  - 只有 `PerMinute` → `API_RATE_LIMITED`
  - 未辨識格式預設視為 transient，不降級。
- 已用現有 key 做遮罩後的唯讀 probe：
  - `gemini-3.5-flash` 真實 429 只列 `GenerateRequestsPerDayPerProjectPerModel-FreeTier`。
  - `gemini-3.1-pro-preview` 0 quota 回應同時列每日與每分鐘 quota；每日命中仍封閉分類為 `API_QUOTA`。
- allocator state 已升為 schema v3，保存 per-model／per-slot quota block，期限為下一個 Pacific midnight。
- Outbox 只有收到三個不同安全 slot 的 `API_QUOTA` receipt 才切 fallback；routing receipt 保存 role、primary／selected model、reason 與 exhausted slot IDs。
- installer 鎖定正式 primary pair，拒絕 model route drift。
- operation receipt 會記錄實際選中的 fallback model，不再誤寫 primary model。
- 本地 commit 已建立；先前 push 因當時缺少對該 GitHub origin 的明確授權而被安全閘門拒絕，沒有任何 remote mutation。

## Verification Evidence

- `tests/test_agy_gemini_allocator.py`
- `tests/test_agy_gemini_outbox.py`
- `tests/test_agy_seo_copy_pipeline.py`
- 上述受影響 suites：`312 passed`
- `tests/test_agy_gemini_coordinator.py` installer／launchd 精準集合：`4 passed`
- `bash -n scripts/install_agy_gemini_coordinator_launchd.sh`：PASS
- `git diff --check`：PASS
- `code-review-gate`：未發現阻塞問題。
- 曾嘗試更大的 coordinator suite；在 319 tests 通過後，遇到與本卡無關的既有 fixture 問題：`ASTRO-SCENARIO-BIG-THREE` 不在 matrix backlog。不得把該基線問題誤判成本卡 regression。

## Active State

- 分支目前只含本卡相關功能 commit 與本交接文件。
- 功能分支尚未 push。
- 尚未 merge／cherry-pick 到 `main`。
- production launchd 仍是舊設定：Writer／Reviewer 都是 `gemini-3.5-flash`。
- production mutation：`0`。
- 已啟動 server：無。

## Blocker

- 沒有程式 blocker。
- 外部狀態 blocker：功能分支尚未推到可信的 `origin`，也尚未進入乾淨 integration branch。
- 啟用 blocker：程式碼改動會改變 runtime code digest；必須重產並綁定正式 manifest／receipt，不能直接重裝舊 plist。

## Candidate Fork

- 已選主線：推送功能分支 → 乾淨整合到最新 `origin/main` → 重跑受影響 gate → 重產正式 runtime promotion artifacts → capacity preflight → no-mutation canary → 取得 production activation 授權後啟用。
- 不採用：直接在髒主工作區 merge、直接修改現有 plist、跳過 runtime identity 重產、直接發文測試。

## In Progress / Remaining Work

1. 只讀確認 `origin` 目的地與最新 `origin/main`。
2. 取得明確 push 授權後，把 `codex/gemini-model-quota-fallback-20260817` 推到可信 `origin`。
3. 在乾淨 integration worktree 將功能 commit 整合到最新 `origin/main`；若基底已前進，處理衝突後重跑測試。
4. 進行獨立 code review；任何 finding 回原分支修正，不另開第二個同角色 repair chain。
5. 重產 runtime manifest／promotion plan／receipts，使新 code digest、Python、UV、actor identity 與 plist 完整綁定。
6. 執行 storage capacity gate 與 production capability no-mutation canary；缺任一正式證據即 `NO-GO`。
7. 在使用者明確授權 production activation 後，才安裝／啟用 launchd。
8. 啟用後先驗證 queue admission、三 slot rotation、Writer／Reviewer model separation、RPM 不降級與 quota fallback；發文仍需獨立授權。

## Waiting Conditions

- Push：需要使用者明確授權推送此分支到已核對的 `origin`。
- Production activation：需要完成整合、review、promotion、capacity 與 canary 後的明確授權。
- 發文：本交接不授權任何文章 publish。

## Limits

- 不可把「三把 key 不同」當成可省略 slot receipt 的理由；仍要收齊三個不同 slot 的每日 quota 證據。
- 不可把普通 429、503 或單一 slot 的 quota error 當成 model fallback 條件。
- 不可讓 Writer／Reviewer 因雙重 fallback 變成同一模型。
- 不可把測試環境的 provider body、credential path 或 API key 寫入 receipt／log／handoff。
- 不可直接覆蓋 dirty 主工作區的使用者修改。

## Key Decisions & Resolved Questions

- Google AI Pro UI 訂閱與 Gemini API quota 是不同系統；本流程只依 API response 與 project slot receipt 判定。
- GenerateContent API 的真實 429 不能只看 `RESOURCE_EXHAUSTED`；必須檢查封閉 `QuotaFailure.quotaId` 的 `PerDay／PerMinute`。
- 三把 API key 已由使用者確認屬於不同帳號／project，先前「可能共用 project quota」疑問已解除。
- Writer 與 Reviewer 維持不同模型是硬限制；額度不足時寧可停 queue，也不降低獨立 review 邊界。

## 新對話第一句

```text
請套用 ~/ai-core/compiled_lite.md。
先只讀交接卡：.ai/handoff_20260817_gemini_quota_routing_ready_for_integration.md
確認 commit 802133cc99 與目前 origin/main；先回報接手狀態，不要先做 production mutation。
下一步是取得 push 授權後推功能分支，再用乾淨 worktree 整合、review、重產 runtime promotion 與跑 capacity/canary。
本卡不授權 launchd activation 或發文。
```
