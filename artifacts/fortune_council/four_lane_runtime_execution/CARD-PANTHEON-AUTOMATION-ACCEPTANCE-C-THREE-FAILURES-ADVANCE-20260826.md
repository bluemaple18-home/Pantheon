---
id: CARD-PANTHEON-AUTOMATION-ACCEPTANCE-C-THREE-FAILURES-ADVANCE-20260826
status: ready
chain_id: PANTHEON-AUTOMATION-ACCEPTANCE-20260826
role: implementation
cycle: 3
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 規格固定但驗證 production actor 的 retry/terminal/manual/slot-release 狀態機與跨 item 前進 invariant，採 strict/core-bounded 跑道；使用隔離、可回復、不公開的正式 seam，不需 Sol 裁決架構岔。
execution_mode: bounded_isolated_runtime_acceptance
production_mutation: forbidden
remote_mutation: forbidden
---

# Pantheon 三次失敗後前進自動化驗收

工作名稱：Pantheon 三次失敗後前進自動化驗收

任務目的：用 bounded、可回復且不污染公開內容的正式隔離失敗情境，證明同一 item 第三次失敗後進 terminal/manual、釋放槽位，下一個不同 identity 的 eligible item 會進入執行。

可改範圍：本卡專屬 result/evidence、task-owned `/private/tmp` 隔離 queue/state/workspace，以及正式 actor 明示支援的 isolated/synthetic acceptance seam；禁止修改 production queue/registry/ledger、source/workflow、公開內容、credential、共享設定或既有未追蹤檔。

驗證：失敗 item 沒有 publish transaction/公開 URL，attempt 精確等於三且不再重試；下一 item identity 不同並由正式 selector 進入執行；全域 loop 沒有因單篇失敗停死，所有測試狀態可完整清除而不碰 production。

停損：七服務全程保持停止；同一 blocker 第三次、隔離邊界不明、需要手改 registry 狀態、需要破壞 API credential、任何 production/public/remote mutation、attempt 超過三、原 item 被第四次選取或下一 item identity 相同時立即停止並保留證據。

## 來源與固定事實

- 接手：`handoff_20260826_pantheon_automation_acceptance_dispatch.md`。
- 前一卡 A：`NO-GO / REMOTE_MAIN_BEHIND_RUNTIME_ACTOR`；前一卡 B：同一 `NO-GO`。兩者 blocker 不授權本卡修復、push、promotion、publication 或修改 clean-origin gate。
- Source commit：建立正式 thread 時，以包含本卡且可由 `git show` 讀取的 main commit 為準。
- Runtime actor：`6477ab815e8aecca7d1e8e1588e6e5eba0fab001`。
- Runtime generation：`g47-6477ab81-activation-only-20260826`。
- 本卡只驗 retry/terminal/advance contract，不進 Publisher、不驗公開網址，不重驗新文。
- `auto-new-v1-20260826-001-01` 已存在；本卡禁止 seed、resume 或改動該 identity。
- 七個 launchd 服務在接手時均為 `STOPPED`；本卡不得 bootstrap、kickstart、enable 或啟用常駐排程。
- 主工作區既有未追蹤檔屬使用者；禁止讀寫、加入、清理或帶入 worktree。

## 執行契約

1. 第一拍只讀：確認卡片、source SHA、獨立 clean worktree 且不得等於 A/B worktree、actor/generation、七服務停止、production queue/registry/ledger 路徑與 hash、正式 retry/selector/terminal isolated seam、capacity/readiness receipt。coding／review／debug 的第一次 source decision 前查 CodeGraph；無結果或 prepare 失敗才限域 `rg`，並留下 degraded reason。
2. 在任何寫入前證明正式 actor 的 entrypoint 可接受 task-owned absolute queue/state/workspace，且不會 fallback 到 production roots、Publisher、Git remote、launchd 或公開網站。無法 fail-closed 證明隔離時直接 `BLOCKED`；不得以實際 production mutation 試探。
3. 只可透過正式 create/seed/runner/selector 或 repo 既有 deterministic acceptance harness 建立兩個 bounded synthetic items；禁止直接手寫或修改 registry 狀態。item F 為可預期、可重現且不涉及 credential 的 deterministic failure；item N 為不同 identity 的 eligible next item。
4. item F 的每次執行必須由同一正式 runner/selector 產生 attempt evidence，固定 max attempts=`3`。每次只允許 one-shot／max-runs=`1`，三次 correlation 必須連續且同 identity；不得一次批次偽造 attempt count。
5. 第三次失敗後必須由正式狀態機自動將 item F 轉為 terminal/manual、移出 active/retry eligibility 並釋放槽位。再跑一次 selector 的 read-only/dry-run probe，必須證明 item F 不會第四次被選取。
6. 只再執行一個 bounded selector/runner step，證明下一個被選取的 item N identity 與 F 不同且已進入執行。若避免外部模型或副作用所需，可在「identity 已鎖定且進入正式執行狀態」後使用既有安全 stop/cancel seam 收斂；禁止直接手改狀態。
7. 全程核對 item F/N、global loop 與 slot accounting：F attempt=`3`、terminal/manual、不再 eligible；N identity different/進入執行；global loop 未全域停止；publication transaction、tag、push、public URL、production registry/ledger/queue diff 全為 `0`。
8. 使用正式 cleanup/rollback seam 清除 task-owned synthetic state；只可清理本卡 `/private/tmp/pantheon-automation-acceptance-c-*` allowlist。終態再唯讀確認七服務全為 `STOPPED`、production hashes 不變、沒有殘留 child／排程、主工作區未追蹤檔未碰。

## 唯一可寫範圍

- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-AUTOMATION-ACCEPTANCE-C-THREE-FAILURES-ADVANCE-20260826-RESULT.md`
- `artifacts/fortune_council/four_lane_runtime_execution/automation_acceptance_c_three_failures_advance_20260826/`
- task-owned `/private/tmp/pantheon-automation-acceptance-c-*`。
- 正式 actor 明示支援、且已證明不會 fallback 到 production 的 isolated/synthetic acceptance root。

## 禁止範圍

- 禁止修改 production queue/state/registry/ledger、公開內容、repo source、tests、workflow、shared metadata、生成頁、sitemap、feed、redirects、既有 evidence 與未追蹤檔。
- 禁止破壞或替換正式 API credential、呼叫付費 Writer/Reviewer 來製造失敗、發布測試字樣、Git remote write、push、tag、deploy、promotion 或 publication。
- 禁止直接手改 registry/ledger/item 狀態、手工把 attempt 設成三、手造 selector output、替代流程、無上限 failure loop、第四次 retry 或第二組失敗 item。
- 禁止修 A/B blocker、啟動七服務、建立第四張卡、Reviewer、Repair 或 replacement thread；發現真正 P0/P1 code defect 時只回主線。
- 禁止 archive thread、清理主工作區、刪除 production queue/plist/ledger 或自行宣稱主線 GO。

## 證據契約

- dispatch：正式 thread ID、獨立且不同於 A/B 的 worktree path/cwd、source SHA、clean state、activation receipt、model/reasoning runtime evidence。
- isolation：actor/generation、七服務 `STOPPED`、production root hashes、task-owned roots、正式 entrypoint argv/contract、no-fallback/dry-run 負向證據。
- attempts：item F identity/correlation、三次正式 runner/selector evidence、每次 attempt transition、第三次 terminal/manual、第四次 selector 不再選 F。
- advance：slot before/after、item N identity、與 F 不同、正式 selector 選中並進入執行、global loop 仍可前進。
- zero-mutation：production queue/registry/ledger/publication/tag/push/public URL 前後均無變化；未呼叫 Writer/Reviewer API。
- cleanup：只清 task-owned roots、七服務仍 `STOPPED`、無殘留 child、production hashes 不變、未追蹤檔未碰。

## 驗證與交付

- `GO`：F 精確三次後 terminal/manual 且不再 retry，槽位釋放，N 以不同 identity 進入執行，global loop 未停死，production/public/remote mutation 全為零且隔離狀態已清除。
- `BLOCKED`：單一根因、同 blocker 已嘗試次數、最後安全狀態、是否有 partial mutation、七服務狀態，以及下一個需要的明確授權。
- 交付 `RESULT.md`、evidence 目錄與完整 candidate commit SHA；只能標記 `DELIVERED_CANDIDATE`，不得宣稱 `ACCEPTED`、`INTEGRATED` 或最終 GO。
