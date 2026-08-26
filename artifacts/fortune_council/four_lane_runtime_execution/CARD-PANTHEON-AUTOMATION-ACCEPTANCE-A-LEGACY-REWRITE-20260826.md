---
id: CARD-PANTHEON-AUTOMATION-ACCEPTANCE-A-LEGACY-REWRITE-20260826
status: ready
chain_id: PANTHEON-AUTOMATION-ACCEPTANCE-20260826
role: implementation
cycle: 1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 規格固定但涉及 production 舊文 identity、原網址 publication transaction 與公開驗收，採 strict/core-bounded 跑道；沒有未解架構岔，不升 Sol。
execution_mode: bounded_production_acceptance
production_mutation: single_legacy_article_rewrite_at_existing_canonical_url_authorized
remote_mutation: only_existing_official_single_article_publish_flow_authorized
---

# Pantheon 舊文原網址自動化驗收

工作名稱：Pantheon 舊文原網址自動化驗收

任務目的：用一篇既有舊文驗證 selector → rewrite Writer → Reviewer／最多三次 repair → publish update，沿用同一 article identity 與原 canonical URL。

可改範圍：本卡專屬 result/evidence、正式 runtime 既有入口擁有的單篇 queue/state/publication transaction，以及該舊文既有內容；禁止修改 source、workflow、共享設定、新文鏈或既有未追蹤檔。

驗證：原公開網址 HTTP 200、正文確實更新、article identity 與 canonical URL 不變，且沒有新增重複 URL、文章、ledger transaction；中間狀態、commit、tag、push 或 exit 0 均不能單獨算完成。

停損：七服務全程保持停止；同一 blocker 第三次、內容審核／修復第三次仍失敗、identity 漂移、第二篇、第二 publication transaction、需偏離正式入口或需擴權時立即停止並保留證據。

## 來源與固定事實

- 接手：`handoff_20260826_pantheon_automation_acceptance_dispatch.md`。
- Source commit：建立正式 thread 時，以包含本卡且可由 `git show` 讀取的 main commit 為準。
- Runtime actor：`6477ab815e8aecca7d1e8e1588e6e5eba0fab001`。
- Runtime generation：`g47-6477ab81-activation-only-20260826`。
- 新文完整 canary 已通過，本卡禁止重驗或修改新文鏈。
- `auto-new-v1-20260826-001-01` 已存在；本卡禁止 seed、resume 或改動該 identity。
- 七個 launchd 服務在接手時均為 `STOPPED`；本卡不得 bootstrap、kickstart、enable 或啟用常駐排程。
- 主工作區既有未追蹤檔屬使用者；禁止讀寫、加入、清理或帶入 worktree。

## 執行契約

1. 第一拍只讀：確認卡片、source SHA、獨立 clean worktree、actor/generation、七服務停止、正式 entrypoint、capacity/readiness receipt 與目前 queue/registry。coding／review／debug 的第一次 source decision 前查 CodeGraph；無結果或 prepare 失敗才限域 `rg`，並留下 degraded reason。
2. capability receipt 必須在 mutation 前證明正式 `create → run → select → publish → transaction → tag → push` 的入口、I/O、identity/correlation、正向與 fail-closed 負向證據；receipt 或 production/capacity gate 不成立即 `BLOCKED`，不得以本次真實舊文 mutation 補證 readiness。
3. 從既有正式 selector 選取唯一一篇 eligible 舊文；在任何寫入前鎖定 article identity、原 canonical URL、內容基線 hash／可見摘要、run ID、correlation ID，以及 mutation 前 URL/ledger/article 唯一性基線。禁止手選成新文章或建立新 identity。
4. 只使用既有正式 one-shot／exact-run 入口執行 rewrite Writer → Reviewer；Writer 固定 `gemini-3.5-flash-lite`，Reviewer 固定 `gemini-3.1-flash-lite`。同一 item 的審核／修復合計最多三次；第三次仍失敗就 terminal/manual，不得為內容偏好繼續重寫。
5. 只有 Reviewer 與 deterministic gates 通過才能進既有正式單篇 Publisher 流程。全程不得啟動七個常駐服務；若正式流程無法在七服務保持停止下 bounded 執行，停止並回報 blocker，不得自行 bootstrap 或改 plist。
6. 本卡授權的外部 write 僅為同一 article identity 在既有官方單篇 publish flow 內必要的一次更新 transaction，以及該流程內不可分割且已有正式 gate 的 tag/push/deploy 步驟。任何第二 transaction、手動 push/tag、替代 deploy、非目標檔案或超出單篇更新的遠端 mutation 都立即停止。
7. publication 後以 HTTP 與 browser 驗證原網址 200、canonical 不變、更新後正文 identity 可見；對照前後 hash／可見摘要，並核對 sitemap、registry、ledger、route 與文章數量沒有重複或新增 identity。
8. 終態再唯讀確認七服務仍全為 `STOPPED`、沒有殘留 child／排程、主工作區未追蹤檔未碰；只提交本卡 allowlist 內 result/evidence，不提交 public content 或 runtime 擁有的既有文章變更副本。

## 唯一可寫範圍

- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-AUTOMATION-ACCEPTANCE-A-LEGACY-REWRITE-20260826-RESULT.md`
- `artifacts/fortune_council/four_lane_runtime_execution/automation_acceptance_a_legacy_rewrite_20260826/`
- 正式 runtime 既有入口明示擁有的單篇舊文 queue/state/publication transaction 與同 identity 內容更新。
- task-owned `/private/tmp/pantheon-automation-acceptance-a-*`。

## 禁止範圍

- 禁止修改 repo source、tests、workflow、registry 手工檔、shared metadata、生成頁、sitemap、feed、redirects、既有 evidence 與未追蹤檔。
- 禁止修改新文鏈、建立新文章 identity、第二篇、全批舊文、平行 production run、第二 child 或無上限 retry。
- 禁止直接手改 registry/ledger 狀態、手造 receipt、替代 script、promotion、capacity exercise、常駐服務重啟或自動排程啟用。
- 禁止建立 B、C、第四張卡、Reviewer、Repair 或 replacement thread；發現真正 P0/P1 code defect 時只回主線，由主線依唯一 Reviewer/Repair 規則決定。
- 禁止 archive thread、清理主工作區、刪除 queue/plist/ledger 或自行宣稱主線 GO。

## 證據契約

- dispatch：正式 thread ID、獨立 worktree path/cwd、source SHA、clean state、activation receipt、model/reasoning runtime evidence。
- pre-mutation：actor/generation、七服務 `STOPPED`、capacity/readiness gate、正式入口、選定 article identity、原 URL、內容與唯一性基線、run/correlation identity。
- runtime：selector、Writer/Reviewer/repair attempt、deterministic gate、Publisher child、publication transaction 的逐步 correlation；attempt 計數不得靠文案推定。
- public：原網址 HTTP 200、browser 正文與 canonical、前後可見內容差異；sitemap/registry/ledger/route/article count 的前後唯一性。
- terminal：七服務仍 `STOPPED`、無殘留 child、未追蹤檔未碰、所有 mutation 與 cleanup accounting。

## 驗證與交付

- `GO`：上述證據完整，只有一篇、同 identity、同 URL、一次 transaction、正文已更新、無重複，七服務仍停止。
- `BLOCKED`：單一根因、同 blocker 已嘗試次數、最後安全狀態、是否有 partial mutation、七服務狀態，以及下一個需要的明確授權。
- 交付 `RESULT.md`、evidence 目錄與完整 candidate commit SHA；只能標記 `DELIVERED_CANDIDATE`，不得宣稱 `ACCEPTED`、`INTEGRATED` 或最終 GO。
