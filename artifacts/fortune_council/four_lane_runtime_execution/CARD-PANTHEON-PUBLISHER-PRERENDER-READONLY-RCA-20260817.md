---
id: CARD-PANTHEON-PUBLISHER-PRERENDER-READONLY-RCA-20260817
status: ready
type: diagnosis
chain_id: PANTHEON-PUBLISHER-PRERENDER-RECOVERY-20260817
role: implementation
cycle: 1
thickness: minimal
risk: bounded-production-readonly
model: gpt-5.6-luna
reasoning: medium
model_reason: 節省模式；工作範圍已鎖定為唯讀取證、單一根因與停止點，不含修復或 production mutation。
owner: visible-thread-diagnostic
mainline_acceptor: current-main-thread
---

# Publisher prerender 唯讀根因診斷

## Root question

為何 Existing Publisher 建立 `state/transaction-ond6ep49` 後，停在 `prerender_article_shells.py`，約五分鐘 CPU 為 0，且沒有實際 Python／Node 子程序？

本卡只定位單一根因、可重現 RED 與最小修法，不執行修復。後續四線 activation、Publisher recovery、發布及 Writer vNext／SEO／AEO／GEO 都不屬本卡。

## 已知事實

- source、`origin/main`、production actor 與 runtime manifest 在交接時均對齊 `387d73eef8cb525efced572f5aef772ee9a135e2`。
- 七個 production launchd labels 在交接時均為 `UNLOADED`，目前不得啟動或 reload。
- `new`、`i18n-new`、`i18n-rewrite` bounded acceptance 已完成；`rewrite` 因本次 Publisher prerender blocker 未完成。
- 未完成 transaction 為 `state/transaction-ond6ep49`，約 106 MB，repo HEAD 為上述 SHA；內含未提交網站生成變更，尚未 commit、tag 或 push。
- 前一 transaction 已用正式 Publisher recovery 入口收斂；本卡不得手動刪除或修改任何 transaction。
- production runtime root 是同機 local-only 證據來源；若執行環境無法唯讀存取，立即以 `BLOCKED / EVIDENCE_ACCESS` 停止，不猜測、不要求 production mutation。

## 必讀

- repository `AGENTS.md`
- 本卡
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-LAUNCHD-ACTIVATION-RECOVERY-20260817.md`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-FOUR-LANE-STATE-CONVERGENCE-20260817.md`
- `root-cause-triage` skill
- `rules/19-codegraph-context-infrastructure.md`

## 允許範圍

1. 唯讀保存並比對 transaction、queue、runtime manifest、Publisher／launchd logs 與 Git metadata 的當前快照及相關時間窗。
2. 先以任務語意查 CodeGraph，確認 Publisher → prerender 的程式入口與呼叫鏈；只有無結果或能力失敗才限域使用 `rg`。
3. 唯讀檢查當時 parent command、process tree、open files、exit／signal、subprocess 啟動參數及等待點；不得啟動 Publisher 或 production services 來補證據。
4. 唯讀檢查 transaction repo 的 `.git` 指向、worktree locks、Git locks、recursive symlink。
5. 唯讀解析 launchd plist 的 `PATH`、`UV_*`、Python、Node、pnpm 與實際 prerender command；不得修改環境、安裝依賴或加 shim。
6. 建立 `prerender_article_shells.py` 啟動前、subprocess call、timeout、cleanup 的證據時間線。
7. 在不觸碰 production 的前提下，實際執行一條 red-capable command；若安全條件下無法建立 RED，列出證據缺口後停止。

## 唯一可寫範圍

- `.work/CARD-PANTHEON-PUBLISHER-PRERENDER-READONLY-RCA-20260817/`

其中至少產出：

- `result.md`：單一根因、被證偽假說、最小修法、停止判定。
- `evidence/`：限量命令輸出、時間線與 RED receipt；不得複製 106 MB transaction、binary、完整 queue 或無界 logs。

除了上述 task workspace，不得修改、建立、刪除或格式化 repository、production runtime、transaction、queue、manifest、logs、plist、Git refs 或外部狀態。診斷輸出不得 commit、push 或整合，由主線讀取驗收。

## 禁止範圍

- 不啟動、reload、kickstart 或 unload 任何服務；不部署、不 promotion、不發布。
- 不執行 Publisher recovery／rollback，不清 transaction，不刪 queue，不改 run ownership。
- 不修改 code、config、tests、workflow、runtime、launchd plist、環境變數或依賴。
- 不用 `strace`／`dtruss`／debugger attach 等會改變或干擾 production process 的手段；目前服務已停，不得為 attach 而重啟。
- 不把 PATH、uv、lock、symlink、subprocess 或 transaction 候選直接當結論。
- 不開 Reviewer／Repair／替代 thread，不擴到四線恢復或 Writer vNext。

## 診斷方法與判定

1. 先保存 failure evidence，再列少量、可證偽且排序的假說。
2. 每次只驗一個變數；`0 rows`、無 child process、無 lock 也是證據。
3. 根因必須能同時解釋：transaction 已建立、停在 prerender 邊界、CPU 0、沒有實際 Python／Node child，以及等待約五分鐘。
4. 至少明確證偽一個合理候選；只靠時間相關或單一 log 文案不得宣稱 RCA。
5. 最小修法只能描述，不得實作；若證據導向新類型，標記 `candidate fork` 並停止。

## 驗收條件

- transaction、queue、manifest 與 log 時間窗已唯讀保全，且記錄 digest／大小／mtime 等可重驗識別。
- CodeGraph query 與必要原始碼入口確認已完成，或已留下 `CONTEXT_DEGRADED` 的精確原因與限域 fallback。
- 有一條已實際執行且能命中同一症狀的 red-capable command；若無法安全建立，依規則明確 BLOCKED。
- `result.md` 只提出一個主根因，附直接證據、至少一個已證偽候選及信心等級。
- 最小修法不繞過 SHA descendant、identity、path、capacity 或 Publisher preflight。
- `git status --short` 證明唯一寫入只在允許的 `.work/`；production side-effect 檢查無變更。

## 停止條件

- 產出單一 RCA 與最小修法後立即停止，不直接修。
- 若需要啟動 production、修改 transaction／queue、安裝工具、取得新權限或進行有干擾的 attach 才能繼續，立即 `BLOCKED`。
- 同一 blocker 第三次出現即停止，不做第四次。
- 發現 production 狀態相較交接有任何異常變動，第一次即停止並回報，不使用重試額度。

## 交付格式

只回報：

1. 判定：`RCA_READY` 或 `BLOCKED`。
2. 單一根因與信心等級。
3. red-capable command 及其失敗判定。
4. 兩至四項關鍵證據與已證偽假說。
5. 最小修法描述。
6. `result.md` 與 evidence 的 repo-relative 路徑。
7. 明確聲明未改 code、未啟動服務、未清 transaction、未碰 production mutation。

