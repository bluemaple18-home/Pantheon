---
id: CARD-PANTHEON-AUTOMATION-ACCEPTANCE-B-TRANSLATION-PUBLIC-URL-20260826
status: ready
chain_id: PANTHEON-AUTOMATION-ACCEPTANCE-20260826
role: implementation
cycle: 2
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 規格固定但涉及 production locale identity、翻譯 publication transaction、canonical/hreflang 與公開網址驗收，採 strict/core-bounded 跑道；沒有未解架構岔，不升 Sol。
execution_mode: bounded_production_acceptance
production_mutation: single_source_single_locale_translation_publish_authorized
remote_mutation: only_existing_official_single_translation_publish_flow_authorized
---

# Pantheon 翻譯公開網址自動化驗收

工作名稱：Pantheon 翻譯公開網址自動化驗收

任務目的：由一篇已通過的中文來源走 translation Writer → Reviewer／最多三次 repair → publish locale URL，驗證來源與 locale identity 綁定、公開譯文與 canonical/hreflang。

可改範圍：本卡專屬 result/evidence、正式 runtime 既有入口擁有的單一 translation queue/state/publication transaction，以及同一來源的單一 locale 譯文；禁止修改中文來源、source/workflow、共享設定、新文鏈或既有未追蹤檔。

驗證：唯一公開 locale URL HTTP 200 且譯文可見，locale/來源 identity 綁定、canonical 與 hreflang 正確，同 locale 沒有重複文章、URL 或 transaction；中間狀態、commit、tag、push 或 exit 0 均不能單獨算完成。

停損：七服務全程保持停止；同一 blocker 第三次、內容審核／修復第三次仍失敗、來源或 locale identity 漂移、第二來源、第二 locale、第二 publication transaction、需偏離正式入口或需擴權時立即停止並保留證據。

## 來源與固定事實

- 接手：`handoff_20260826_pantheon_automation_acceptance_dispatch.md`。
- 前一卡：`CARD-PANTHEON-AUTOMATION-ACCEPTANCE-A-LEGACY-REWRITE-20260826`；先前 `REMOTE_MAIN_BEHIND_RUNTIME_ACTOR` blocker 已由 mainline promotion transaction 解除，卡 B 仍須在卡 A 重新驗收後依序執行。
- 本卡不得自行修復、push、promotion 或修改 clean-origin gate；任何正式 gate 再次擋下時，保留本卡獨立 evidence 並 `BLOCKED`。
- Source commit：建立正式 thread 時，以包含本卡且可由 `git show` 讀取的 main commit 為準。
- Runtime actor：`e5c0743fe1e0c99a66f2c0e3355591f2a353a322`。
- Runtime generation：`g48-e5c0743f-gsc-json-shape-20260826`。
- 新文完整 canary 已通過，本卡禁止重驗或修改新文鏈。
- `auto-new-v1-20260826-001-01` 已存在；本卡禁止 seed、resume 或改動該 identity。
- 七個 launchd 服務在接手時均為 `STOPPED`；本卡不得 bootstrap、kickstart、enable 或啟用常駐排程。
- 主工作區既有未追蹤檔屬使用者；禁止讀寫、加入、清理或帶入 worktree。

## 執行契約

1. 第一拍只讀：確認卡片、source SHA、獨立 clean worktree 且不得等於卡 A worktree、actor/generation、七服務停止、正式 translation entrypoint、capacity/readiness receipt、目前 queue/registry 與卡 A 已知 blocker。coding／review／debug 的第一次 source decision 前查 CodeGraph；無結果或 prepare 失敗才限域 `rg`，並留下 degraded reason。
2. capability receipt 必須在 mutation 前證明正式 `create → run → select → publish → transaction → tag → push` 的入口、I/O、identity/correlation、正向與 fail-closed 負向證據；receipt 或 production/capacity gate 不成立即 `BLOCKED`，不得以本次真實翻譯 mutation 補證 readiness。
3. 只用既有正式 selector 選取一篇已通過且可翻譯的中文來源與唯一一個 eligible locale；在任何寫入前鎖定 source article identity、中文 canonical URL、target locale、預期 locale URL、來源內容基線 hash、run ID、correlation ID，以及 locale URL/registry/ledger 唯一性基線。
4. 只使用既有正式 one-shot／exact-run 入口執行 translation Writer → Reviewer；Writer 固定 `gemini-3.5-flash-lite`，Reviewer 固定 `gemini-3.1-flash-lite`。同一 item 的審核／修復合計最多三次；第三次仍失敗就 terminal/manual，不得為內容偏好繼續翻譯。
5. 只有 Reviewer 與 deterministic gates 通過才能進既有正式單篇 Publisher 流程。全程不得啟動七個常駐服務；若正式流程無法在七服務保持停止下 bounded 執行，停止並回報 blocker，不得自行 bootstrap 或改 plist。
6. 本卡授權的外部 write 僅為同一 source identity 與同一 locale 在既有官方單篇 publish flow 內必要的一次 translation transaction，以及該流程內不可分割且已有正式 gate 的 tag/push/deploy 步驟。任何第二 transaction、手動 push/tag、替代 deploy、非目標檔案或超出單篇單 locale 的遠端 mutation 都立即停止。
7. publication 後以 HTTP 與 browser 驗證 locale URL 200、譯文正文 identity 可見、canonical 指向正確 locale URL、hreflang 與中文來源互相對應；核對 registry、ledger、route 與同 locale 文章數量沒有重複。
8. 終態再唯讀確認七服務仍全為 `STOPPED`、沒有殘留 child／排程、中文來源未改、主工作區未追蹤檔未碰；只提交本卡 allowlist 內 result/evidence，不提交 public content 或 runtime 擁有的譯文變更副本。

## 唯一可寫範圍

- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-AUTOMATION-ACCEPTANCE-B-TRANSLATION-PUBLIC-URL-20260826-RESULT.md`
- `artifacts/fortune_council/four_lane_runtime_execution/automation_acceptance_b_translation_public_url_20260826/`
- 正式 runtime 既有入口明示擁有的單一 translation queue/state/publication transaction 與同 source/locale identity 譯文。
- task-owned `/private/tmp/pantheon-automation-acceptance-b-*`。

## 禁止範圍

- 禁止修改中文來源、repo source、tests、workflow、registry 手工檔、shared metadata、生成頁、sitemap、feed、redirects、既有 evidence 與未追蹤檔。
- 禁止修改新文鏈、全語系批次、多篇來源、第二 locale、第二 child、平行 production run 或無上限 retry。
- 禁止直接手改 registry/ledger 狀態、手造 receipt、替代 script、修 A blocker、手動 push、promotion、capacity exercise、常駐服務重啟或自動排程啟用。
- 禁止建立 C、第四張卡、Reviewer、Repair 或 replacement thread；發現真正 P0/P1 code defect 時只回主線，由主線依唯一 Reviewer/Repair 規則決定。
- 禁止 archive thread、清理主工作區、刪除 queue/plist/ledger 或自行宣稱主線 GO。

## 證據契約

- dispatch：正式 thread ID、獨立且不同於 A 的 worktree path/cwd、source SHA、clean state、activation receipt、model/reasoning runtime evidence。
- pre-mutation：actor/generation、七服務 `STOPPED`、capacity/readiness gate、正式入口、中文 source identity/URL/hash、target locale/URL、唯一性基線、run/correlation identity。
- runtime：selector、Writer/Reviewer/repair attempt、deterministic gate、Publisher child、translation transaction 的逐步 correlation；attempt 計數不得靠文案推定。
- public：locale URL HTTP 200、browser 譯文正文、canonical/hreflang 與中文來源對應；registry/ledger/route/same-locale count 的前後唯一性。
- terminal：七服務仍 `STOPPED`、無殘留 child、中文來源未改、未追蹤檔未碰、所有 mutation 與 cleanup accounting。

## 驗證與交付

- `GO`：上述證據完整，只有一篇來源、一個 locale、一個 locale URL、一次 transaction、譯文已公開、canonical/hreflang 正確且無重複，七服務仍停止。
- `BLOCKED`：單一根因、同 blocker 已嘗試次數、最後安全狀態、是否有 partial mutation、七服務狀態，以及下一個需要的明確授權。
- 交付 `RESULT.md`、evidence 目錄與完整 candidate commit SHA；只能標記 `DELIVERED_CANDIDATE`，不得宣稱 `ACCEPTED`、`INTEGRATED` 或最終 GO。
