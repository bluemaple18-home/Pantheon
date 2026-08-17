---
id: CARD-PANTHEON-COORDINATOR-PUBLISHER-CAUSAL-RCA-20260818
status: ready
type: diagnosis
chain_id: PANTHEON-COORDINATOR-PUBLISHER-RECOVERY-20260818
role: diagnosis
cycle: 1
thickness: standard
risk: bounded-production-readonly
model: gpt-5.6-terra
reasoning: medium
model_reason: 節省模式；跨 Publisher、Coordinator 與 fail-closed guard 的唯讀因果診斷，先鎖根因與 RED，不授權修復。
owner: visible-thread-diagnostic
mainline_acceptor: current-main-thread
---

# Coordinator–Publisher 三層失敗因果 RCA

## 工作名稱 → 正在做什麼 → 現在狀態

Coordinator–Publisher 因果 RCA → 分離效能、ownership crash、timeout recovery 三層，找出第四線失敗的必要且充分因果鏈 → `READY / READ-ONLY`

## Root question

為何前三條 lane 可完成，第四條 rewrite 進入 Publisher 後失敗？三個已觀察症狀究竟是同一根因的連鎖，還是三個獨立缺陷：

1. Publisher 對 article registry／corpus 的 Node 全站掃描單次約 50 秒且重複執行；
2. Coordinator 在 Publisher 擁有 active transaction 時，於 `_migrate_pending_jobs → _lane_for_state` 丟出 `ValueError("active run brief is unavailable")` 並退出；
3. 歷史 prerender 300 秒 timeout 後，Publisher recovery 執行 `git diff --binary <base_sha>`，因 transaction repo 不含該 base object 而 exit 128。

本卡只建立可重驗的因果圖、重現 RED、鎖定第一個應修契約。不修 code，不重跑 production，不把 capacity guard 的 fail-closed 停止誤判為根因。

## 已知 evidence（不得改寫成假設）

- production 已回滾；正式七個 launchd labels 均為 `UNLOADED`，不得 load／kickstart／reload。
- 最近 canary 中 Publisher 確實反覆執行完整 Node corpus／inventory scan，每次約 50 秒；尚不足以單獨證明 deadlock。
- Coordinator trace：`cycle_once → _migrate_pending_jobs (約 4031) → _lane_for_state (約 1446) → ValueError("active run brief is unavailable")`。
- capacity guard 看到 Coordinator registered 但無 PID，依既有 stop-loss 停止六項服務；此行為目前視為正確 fail-closed，不得繞過或放寬。
- 歷史 transaction 曾先命中 prerender 300 秒 timeout，再於 recovery 的 `git diff --binary` 以 exit 128 失敗。
- 最近 canary 沒有 publish、tag 或 push；既有 transaction evidence 必須保留。

## 必讀與先後順序

1. repository `AGENTS.md` 與本卡。
2. `handoff_20260817_pantheon_writer_vnext_four_lane_recovery.md`。
3. `root-cause-triage` skill。
4. source decision 前先查 CodeGraph；失敗／無結果才限域 `rg`。
5. 只讀相關 source、tests、既有 repo 內 evidence；不得用啟動 production 補證據。

## 允許讀取

- `scripts/agy_content_publisher.py`
- `scripts/agy_gemini_coordinator.py`
- `scripts/agy_seo_copy_pipeline.py`
- `scripts/pantheon_content_capacity_guard.py`
- `scripts/prerender_article_shells.py`
- 對應的 `tests/test_agy_*.py`、`tests/test_web.py` 與既有 recovery／transaction 測試
- repo 內既有 handoff、cards、receipts、有限範圍 logs／trace 摘要

## 唯一可寫範圍

- `.work/CARD-PANTHEON-COORDINATOR-PUBLISHER-CAUSAL-RCA-20260818/`

至少產出：

- `result.md`：因果時間線、三層分類、第一修復契約、信心與停止判定。
- `evidence/`：限量 CodeGraph receipt、測試／暫存重現輸出；不得複製大型 transaction 或無界 logs。

診斷輸出不得 commit、push 或整合；主線驗收後才另開修復卡。

## 禁止範圍

- 不執行 launchctl、Publisher、Coordinator、capacity guard 或 production canary。
- 不部署、不 promotion、不 publish、不 tag、不 push。
- 不修改 code、tests、config、workflow、runtime、transaction、queue、manifest、logs 或 Git refs。
- 不清理、刪除、回收或搬動既有 transaction。
- 不安裝依賴，不用 debugger attach，不增加 timeout 掩蓋問題。
- 不弱化 capacity guard、SHA descendant、identity、ownership、transaction isolation 或 fail-closed 契約。
- 不開 Repair／Reviewer thread；診斷完立即交回主線。

## 診斷要求

1. 先建立事件時間線，再畫出三層之間的必要／非必要邊。
2. 分別判定：
   - repeated Node scan 是正常成本、效能缺陷，或觸發 300 秒 timeout 的充分條件；
   - Coordinator 是否錯把 Publisher-owned active transaction 當成必須存在 active run brief 的 Coordinator-owned state；
   - recovery 為何在 transaction repo 解析不到 base SHA，以及該錯誤是否只遮蔽原始 timeout。
3. 至少實際執行一條不碰 production 的 red-capable test／暫存重現 command；RED 必須命中契約，不接受只讀 code 後推測。
4. 至少證偽一個合理候選；若三層是獨立缺陷，明確排序第一個應修契約，不硬湊單一根因。
5. 說明「前三線可過、第四線不過」的資料／狀態差異；不得以「流程都一樣」作結論。

## 驗收條件

- `result.md` 明確回答 root question，含信心等級。
- 有可重驗時間線與函式／測試定位。
- 有實際 RED command、expected failure 與 actual failure。
- 三層各被分類為 root cause、trigger、amplifier、recovery defect 或 unrelated。
- 第一修復契約足夠小，可供下一張 GPT-5.5 implementation 卡直接執行。
- `git status --short` 證明唯一寫入只在本卡 `.work/`；明確聲明 production side effects 為零。

## 停止條件

- 需要 production mutation、啟動服務、新權限或修改 transaction 才能繼續時立即 `BLOCKED`。
- 同一 blocker 第三次出現即停止，不做第四次。
- 取得可重驗 RCA 與第一修復契約即停止，不順手修。

## 交付格式

只回報：

1. `RCA_READY` 或 `BLOCKED`。
2. 為何第四線不同。
3. 三層分類與因果鏈。
4. RED command 與結果。
5. 第一修復契約及禁止繞過項。
6. `result.md`／evidence repo-relative 路徑。
7. 未改 code、未啟動服務、未碰 production 的聲明。
