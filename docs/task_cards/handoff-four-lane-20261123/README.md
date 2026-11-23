# Pantheon 四線恢復：換手入口（2026-11-23）

本次整理已驗收成果與原始草稿，換手分支以正式發布 v0.3.1241（`e61fb62bfc7e9fd25134f387bb16d521c1b283f0`）為基底。應從這個正式基準繼續，不把 v1205 上的舊草稿整包覆蓋回去。

## 主線狀態

- 翻譯交接卡：已驗收、CC 放行、已結案。正常週期既有鎖內補呼叫 seed 的修補已在 main，純修補 commit `45a5dd8f9feb5fab8cb4b8129bbc585ed5e63871`，現役 actor 為 `123ee9a682578ea37b8f4581f494e57479d8bcc1`。
- 原訂 7 來源／21 個 EN、JA、KO 任務，另含等待期間自然發布 v1238 的 3 個，共 8 來源／24 個，均有正式 queue state、brief、正確來源／語言／線別。原排程已接收，保存真實 Writer 回覆。
- 翻譯交接兩個 P2 延後，不另開修復、測試或 review。已結案的程式路徑到此停止修改。
- FORTUNE-0030 英文逾時卡：已驗收、CC ACCEPT、無程式變更結案。同篇原版重測於 2026-11-23T18:45:24+08:00 發布 v0.3.1241，commit `e61fb62bfc7e9fd25134f387bb16d521c1b283f0`。
- 真實 Chrome DOM：英文標題可見、12/12 段正文等於原 APPROVE 候選；公開模組與發布 commit blob 的 SHA 相同。HTTP 200 另由 CC 獨立確認；CC 沒有自行重驗 Chrome，不得改寫成 CC 已獨立驗證全部正文。

[公開 FORTUNE-0030 英文](https://www.mysticpantheon.com/en/articles/fortune/fortune-0030)

## 逾時結案與殘留風險

歷史 13:47 發布在 300.11 秒 `PrerenderTimeout`；213 秒安裝與該輪的關聯來自當時觀測，共用 stderr 該行本身沒有 transaction ID。

本次**未改程式、未預熱 actor `.venv`**，安裝 1.17 秒、預渲染約 53 秒（2 秒取樣），沿原 300 秒限制成功；原 3 項前置與 777 項回歸檢查全過。依派工卡「修前重測已能發出就收工」條件結案。`root_cause_proven=false`，不能宣稱已完成預熱修復或已證明 213 秒是唯一真因。

重開門檻：下次出現「已過審、候選 hash 一致、純逾時」且可重現的同類個案，再評估預熱前／後控制對照。不得提高 timeout、改 JS 邏輯或拿品質退稿當工程故障。

## 已推送但未驗收的原始草稿

- 分支：`codex/fix-article-resource-fanout-20261118`。
- 原封不動 checkpoint：`a248538ad108388c5629a06fbf1c1527530abbc2`。
- 草稿基底：v0.3.1205，`6aa7eb0764f2d845ba0a3ece90cb3af18a17c653`。
- 17 個檔案，逐檔 SHA-256 與大小見 [draft-inventory.json](draft-inventory.json)。包括資源減載及過程留下的服務／控制程式草稿；checkpoint 只保存既有內容，未做新的程式修改。
- [GitHub 草稿差異](https://github.com/bluemaple18-home/Pantheon/compare/6aa7eb0764f2d845ba0a3ece90cb3af18a17c653...a248538ad108388c5629a06fbf1c1527530abbc2)。
- 此分支**不是發布候選**。裡面部分服務草稿早於已上線修復，不能因為看見未合併檔案，就全部再修或合併。若 Owner 後續選資源減載題目，只從當前 main 擷取相關最小變更，先證明現在仍有使用者症狀。

## 下一步與禁止擴張

兩張卡已結案。目前等待 Owner 選下一個產品問題；沒有自動排入以下工作：

1. 15 筆舊文失敗：先逐筆判斷是否影響使用者可見更新、是否值得處理，品質退稿不得重置或繞過。
2. 資源載入／HTTPS與導覽標記差異：先查現在的單篇實際載入量及 Google 抓取／報表差異，再決定是否修。不沿用「只是抽樣」當已證實原因。

四條服務接線與這兩張卡的證據，不等於已另外證明四條線長期穩定、每條都完成當日新產稿→審稿→上線；不得把庫存發布當作新產稿證據。後續稿件按既有排程與 Reviewer 規則前進，不為清空清單而催發、重試或改規則。

CC 僅做唯讀 review，不接實作、清理或部署。此文件只交接事實與邊界，不自行把 Mainline 責任交給 CC 或開新對話。

## 現役與本機資料定位

跨機使用以下相對位置；完整原始證據仍在原機，倉庫只保存摘要與檔案雜湊，沒有金鑰、credential pool、launchd 私有環境或大型 `.work` 內容。

- `<recovery-operations>`：原主工作區 `.work/continuous-recovery-20261123`。
- `<translation-operations>`：原主工作區 `.work/translation-handoff-20261123`。
- 現役 actor：`<translation-operations>/work/source`，HEAD `123ee9a682578ea37b8f4581f494e57479d8bcc1`。它與本換手工作樹分離，**不要把本分支 checkout 到現役 actor**。
- manifest generation：`translation-handoff-123ee9a68257-20261123`；digest：`e98f338645d96f2a87b96d3ea29ddfbd453bba2bf2632edab9d9f9c4a36d70d5`。
- runtime：原主工作區的同層目錄 `Pantheon-canary-runtime-v8`，正式 ledger 在 `state/ledger.json`。
- 原主工作區 `main` 另有 5 個本地未合併 commit 與其他任務未提交資料，本輪保留；不得 `reset --hard`、`clean` 或整包提交這些其他資料。
- 舊 `handoff-phase-one.py`／`handoff-phase-two.py` 及既有停止收據是已執行過的一次性歷史操作，**不得直接重跑**；保存的 d6 控制備份也不是可直接點擊的退版入口。

## 證據入口

見 [evidence-summary.json](evidence-summary.json)，包含發布 SHA、實際測試／DOM結果、CC 獨立驗證範圍及原始證據 SHA-256。

先核對 live，再做判斷。原始證據與本機絕對路徑對照另存 `<recovery-operations>/HANDOFF-FOUR-LANE-20261123.md`。
