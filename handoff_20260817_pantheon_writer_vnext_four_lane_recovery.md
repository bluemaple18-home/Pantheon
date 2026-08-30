# Pantheon Writer vNext／四線發文恢復交接

## 新對話第一拍

先只讀本交接與 repository `AGENTS.md`。不要立即啟動服務、重跑 Publisher、清 transaction 或改 code。先回報已理解的 root question、blocker、目前 production 狀態與第一個唯讀診斷步驟。

## Root Question

如何在保留 Pantheon 單一 Control Plane 與既有 Publisher 的前提下：

1. 讓 `new`、`rewrite`、`i18n-new`、`i18n-rewrite` 四條 runtime lane 各自可靠處理自己的 queue 任務。
2. 讓 Writer vNext 的 Editorial Contract、Evidence、Blind Read、Claims、Humanizer、SEO/AEO/GEO 接回既有 Publisher。
3. 恢復 production 正常排程，避免混線、重複領取、假 active、卡死 transaction 與無界 retry。

## Current Blocker

唯一現場 blocker：Publisher 建立 `state/transaction-ond6ep49` 後，停在 `prerender_article_shells.py` 約五分鐘；CPU 0，且沒有實際 Python／Node 子程序。

根因尚未確認。不得把以下候選直接當結論：subprocess 啟動前卡住、git/worktree lock、recursive symlink、runtime `PATH`／`uv`、transaction 狀態或 prerender wrapper 等待條件。

## Candidate Fork

先做一張唯讀 forensic 診斷卡，產出單一根因與最小修法：

- 若是 transaction/worktree/lock 問題：使用既有 recovery/rollback 入口修復，不手動刪目錄。
- 若是 runtime `PATH`／`uv`／Python／Node 啟動問題：修正式入口與測試，不加環境 shim。
- 若是 prerender 程式內等待問題：只修等待點與 bounded timeout/fail-closed。
- 若證據顯示不是以上任一類：停止並回報新 fork，不在診斷卡直接改 code。

## Constraints & Preferences

- 使用者要求節省模式：短回報、單卡、禁止重武裝流程。
- 不開 Reviewer／Repair／架構卡，除非下一張卡已證明需要。
- 不刪 queue、不 force push、不手動改已發布文章。
- 不繞過 runtime SHA descendant、identity、path、capacity gate。
- 同一 blocker 第三次即停；production 異常第一次即停止 acceptance，不使用三次額度試運氣。
- 第一階段保留 Existing Publisher；Writer vNext 透過 Compatibility Contract 接回，不重構 Publisher。
- Editorial Stage 是 artifact/contract，不等於每一階段都開一個 Agent。
- 不建立固定篇幅、固定節數、固定文章模板。
- 四條 runtime lane 與三種內容來源不要混淆：runtime lane 是 `new/rewrite/i18n-new/i18n-rewrite`；Control Plane 內容來源仍是 `NEW/REPAIR/GSC Optimization`。

## Completed Actions

### Source／Runtime 基礎

- Queue preservation 已修復並 review GO；repair candidate `00ed59c52ec202c2ecb2616563cce7ce89c98852`，已整合主線。
- 可設定 Gemini model route 已修復 fallback deadlock並 review GO；review receipt commit `3811444a8e789f03ac963d80ae60815d8905b413`，已整合主線。
- launchd capacity guard 已修正排程型服務短暫無 PID 判定；目前 main commit `387d73eef8cb525efced572f5aef772ee9a135e2`，已 push。
- main、origin/main、production actor、runtime manifest 均已唯讀核對為 `387d73eef8cb525efced572f5aef772ee9a135e2`。
- Runtime manifest：`config_version=formal-runtime-v3-model-route-v1`、generation `g4-387d73eef8-20260817T131000Z`。

### Model Routing（不可再猜）

- Writer route：`gemini-3.5-flash-lite` → `gemini-3.5-flash` → `gemini-2.5-flash`。
- Reviewer route：`gemini-3.1-flash-lite` → `gemini-2.5-flash-lite`。
- 500 RPD 型號優先。
- 只有 exact model 的全部 slots 都得到 `API_QUOTA` 才降級。
- 暫時性 429／503／`API_RATE_LIMITED` 不降級。
- 每日 reset 回第一模型。
- Quota block key：`(slot, exact model)`。
- 四線共用同一 versioned config/digest；未來換模型只改 config → deterministic preflight → promotion/reload，不改 Python hardcode。

### Production 發布證據

- 新文 `tarot-1818` 已發布：commit `9d57ebf`、tag `v0.3.366`。
- 一篇 rewrite 已發布：commit `5c0f244`、tag `v0.3.367`。
- 兩筆已 push。
- 公開 sitemap 數量曾由 `624 → 625`；rewrite 不應要求 sitemap 數量增加。
- 這證明新 runtime 至 Existing Publisher 的發布路徑至少成功過，不代表四線常態排程已穩定。

### 最近 bounded acceptance

- 舊 `state/transaction-dr50kr8n` 已由正式 Publisher recovery 入口安全收斂。
- Capacity gate PASS；`git diff --check` PASS。
- `new`：`auto-new-v1-20260817-097-01`，complete。
- `i18n-new`：`auto-i18n-en-fcaa5bb4adcfef7aa55c`，complete。
- `i18n-rewrite`：`auto-i18n-en-614aa4dc3542ab2c5637`，complete。
- 最終 queue 無殘留 processing ownership。
- `rewrite` bounded acceptance 未完成，因 Publisher prerender 卡死。
- 本次卡遵守停止條件：未改 code、未刪 queue、未手動清新 transaction。

## Active State

### Git

- Repository HEAD：`387d73eef8cb525efced572f5aef772ee9a135e2`。
- `origin/main`：同上。
- Main working tree 有未追蹤卡片，屬本次工作；禁止清除：
  - `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-LAUNCHD-ACTIVATION-RECOVERY-20260817.md`
  - `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-FOUR-LANE-STATE-CONVERGENCE-20260817.md`
  - 本交接文件。
- 多個舊 worktree 存在；不要在接手第一拍清理 worktree/branch。

### Production Runtime

- 七個 launchd labels 已於交接前即時核對為全部 UNLOADED：Publisher、Coordinator、四條 lane、Capacity Guard。
- 因此目前沒有四線或 Publisher 在背景繼續處理。
- Production actor HEAD：`387d73eef8cb525efced572f5aef772ee9a135e2`。
- Runtime manifest digest：`1331c26c25d3e5883a4d634e91f0319d60c4fb824d6f30dadd1ff638cfa26836`。
- Runtime digest：`77bf68e9f2dbcccbd6476a55f7ecb506d429e609ddf22dd35ce2bc105b9fa62b`。

### 未完成 Transaction

- `state/transaction-ond6ep49` 仍保留，約 106 MB。
- Transaction repo HEAD：`387d73eef8cb525efced572f5aef772ee9a135e2`。
- 內有未提交網站生成變更與 `app/web/static/article-expansion-agy-auto-new-v1-20260817-071-01.js`。
- 內容未 commit／tag／push；不得把它當已發布文章。
- 前一 transaction 備份仍在 local-only 路徑 `/private/tmp/pantheon-stopped-publisher-transaction-20260817T2105`。此絕對路徑不可跨機照抄。

### Relevant Visible Tasks

- `01a00f96-a0f8-75b3-b9ca-8ab3bc86864d`：修復 launchd activation 並恢復四線發文；已完成，留下 Publisher transaction 相關現場。
- `01a00fd8-89d5-7ba1-9d46-ad63f1057b5f`：收斂四線狀態並恢復獨立處理；已完成為 BLOCKED/NO-GO，證明三線 complete 並安全卸載七服務。
- `01a00ea1-4cca-74a0-867c-45a83ddcc8e6`：新版四線 Runtime Promotion 與發文恢復；舊 Recovery 任務，已 idle。

## In Progress / Immediate Remaining Work

### P0 — 先解 Publisher prerender 卡死

1. 唯讀保存 `transaction-ond6ep49`、queue、runtime manifest 與相關 log 時間窗。
2. 查當時 parent command、process tree、open files、等待點、exit/signal、subprocess 啟動參數。
3. 查 transaction repo 的 `.git` 指向、worktree locks、git locks、recursive symlink。
4. 查 launchd plist 的 `PATH`、`UV_*`、Python、Node、pnpm 與 prerender command 實際解析。
5. 對 `prerender_article_shells.py` 的啟動前、subprocess call、timeout、cleanup 建立時間線。
6. 輸出唯一根因、最小修法、可重現 RED；診斷卡不直接修。

### P0 — 根因修復後恢復四線

1. 用正式入口收斂 `transaction-ond6ep49`；禁止手動刪除。
2. 修復後跑 affected tests、capacity gate、`git diff --check`。
3. 重新對齊 main/origin/runtime/Publisher identity。
4. 啟動七服務一次。
5. `rewrite` 先做最多一筆 bounded acceptance。
6. 再核對四線 lane ownership、queue state、Publisher exit 0、commit/tag/push。
7. 無殘留 transaction、無假 active、服務保持 loaded 後，才宣告正常排程恢復。

## Larger Writer vNext Work Still Incomplete

以下是使用者要求的完整改版，不可因四線 runtime 曾成功發文就宣稱完成。

### Phase 1 — Contracts／Traceability／Publisher Compatibility

- Editorial Contract：`reader_question`、`thesis`、彈性 `content_plan.sections[].purpose/supports_thesis`。
- Evidence Contract 與每階段 SHA/provenance/traceability。
- 新 Editorial Contract → Existing Article Contract 的 Compatibility Contract/Test。
- 完整現況需要先 audit；目前沒有「整個 Phase 1 已驗收」證據。
- Publisher 第一階段不重構；Compatibility 是邊界，不是另一個新 Publisher。

### Phase 2 — Gemini Transport／Resume

- Queue contract 支援 editorial stage、artifact、status、retry、resume。
- 現有四 lane、queue preservation、model routing 已完成重要 runtime 基礎；但 Editorial artifact 的完整 transport/resume 尚未整體驗收。
- 禁止把 stage 寫死成固定 Writer Agent／Reviewer Agent 拓樸。

### Phase 3 — Writer vNext Editorial Pipeline

- Planner 一次產 Reader Question／Thesis／Content Plan。
- Writer 只負責把已確認契約寫成人可理解的 draft。
- Blind Reader：`summary_one_sentence`、`thesis_match`、`confusing_sections[]`、`low_information_sections[]`、`reader_questions[]`。
- Claims 分類；只有 verifiable/high-risk claim 強制 source/evidence。
- Humanizer 分層：template/banned phrase → filler → AI pattern → coherence → human comprehension。
- Reviewer 讀 Editorial Evidence Package，輸出 PASS／REWRITE／BLOCK。
- 完整改版尚未完成 production acceptance。

### Phase 4 — SEO／AEO／GEO

- SEO：intent、title、description、internal link、entity、canonical、indexability、content gap。
- AEO：question clarity、direct answer、answer extraction、passage structure、entity clarity。
- GEO：passage citability、entity signals、citation readiness、AI crawler accessibility、AI visibility。
- 三者共用同一篇文章與 Evidence；不是各寫一篇，也不是全部塞回 Writer prompt。
- 這一整套仍是大項未完成，不得遺漏。

### Phase 5 — Feedback Loop

- GSC／SERP／CrUX／competitor／AI search → Evidence Layer。
- SEO drift／search performance／AI visibility → Opportunity。
- Opportunity 回到 NEW／REPAIR／GSC Optimization。
- Drift、監控、回饋閉環尚未完成。

## Key Decisions & Resolved Questions

- Pantheon 只保留一套 Control Plane。
- Existing Publisher 第一階段保留；不與 Writer vNext 同時重構。
- Compatibility Adapter 的意思只是資料契約轉換邊界；若目前已由既有 schema 直接相容，不要為名稱硬新增 adapter 層。
- 四線成功過三線 bounded run，表示 lane/queue 基礎不是全部壞掉；當前阻斷在 Publisher prerender。
- Sitemap `+1` 只適用新增 URL；rewrite 更新既有 URL 不應強求數量增加。
- launchd 排程服務可 loaded-but-idle 且無 PID；不能只用即時 PID 判定健康。
- 先前錯誤做法：把 activation、四線驗收、Publisher recovery、發布與新 bug 修復塞同一卡並在成功後繼續探索。後續每卡只允許一個明確停止點。

## Waiting Conditions

只有滿足以下條件才可從唯讀診斷進入修復：

- `transaction-ond6ep49` 已保全。
- 卡死時間線可重現或有足夠 process/log/lock 證據。
- 已選定唯一根因，不再逐個 launchd state 猜測。
- 最小修法不需要繞過 identity/path/capacity/Publisher preflight。

只有滿足以下條件才可恢復正常排程：

- Publisher prerender bounded run exit 0。
- `rewrite` 完成一筆且 ownership 正確。
- 四線 queue 無假 active、無跨 lane、無重複領取。
- 無未完成 Publisher transaction。
- 七服務 loaded，Capacity Guard PASS。

## Evidence Paths

- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-LAUNCHD-ACTIVATION-RECOVERY-20260817.md`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-FOUR-LANE-STATE-CONVERGENCE-20260817.md`
- `artifacts/fortune_council/four_lane_runtime_execution/runtime_queue_preservation_review_20260817/final-review-receipt-5.6.md`
- `artifacts/fortune_council/four_lane_runtime_execution/runtime_queue_preservation_review_20260817/repair-1-final-re-review-receipt.md`
- `artifacts/fortune_council/content_writer_vnext_execution/`
- Production runtime local-only root：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8`，不可跨機照抄。

## Next Step

新對話只做：建立一張「Publisher prerender 唯讀根因診斷卡」，讀本交接後取證。診斷結束即停；不要直接接 activation、四線、Publisher 發布或 SEO 改版。
