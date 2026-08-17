# CARD-PANTHEON-NEW-FLOW-PRODUCTION-PUBLISH-RECOVERY-20260817

## 任務目的

使用目前 `main` 上的新版四線流程，正式恢復 production 產文與 Publisher 推送；不可只替舊 runtime 更新 remote ref，也不可用舊流程繞過 promotion。最終至少讓一篇「新文章」完成 create → run → select → publish → commit → tag → push，並證明 sitemap 文章數增加。

## 已知事實

- 主線與遠端基準：`main@1bdd7d9322204fb74d9b47aa9a15b908f8ab10f6`。
- production runtime：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8`。
- production actor 目前仍為 `2d8d8cb27e872f21c445d863bd7e15dbd1c0a7f7`。
- runtime manifest digest：`49f8a6e22c8f2ad7717d55035d9e0621eff8ebd09476e9f66f21c56205db78bb`。
- Publisher 目前 fail-closed：`PublishBlocked: origin/main is not a descendant of publisher runtime SHA`。
- 2026-08-17 15:28（Asia/Taipei）正式 capacity guard 執行成功，last exit code `0`、state `PASS`；mutation 尚未發生。
- queue 內已有 complete／active／failed run；不得為了 promotion 直接刪除、搬移或竄改 failed run registry。
- 既有成功發布基準：`v0.3.365`、commit `425cec152dcb383ac7c44ffdfb2972d0295f9382`、run `apf-create-run-new-7d0e46d9ec617526f77f8213`，當時 sitemap 文章數為 620。

## 需求追溯

- `US-PUBLISH-RECOVERY-001`：站方可使用新版四線流程持續產文並推送，不需人工補 Git 操作。
- `FR-PUBLISH-RECOVERY-001`：正式 runtime 必須 promotion 至已授權的新版 main SHA，七個 launchd 服務使用同一 manifest identity。
- `FR-PUBLISH-RECOVERY-002`：保留現有 queue 與 run identity，禁止以刪除 failed state 換取 promotion 成功。
- `FR-PUBLISH-RECOVERY-003`：Publisher 必須以正式入口完成 commit、annotated tag 與 push。
- `SC-PUBLISH-RECOVERY-001`：遠端 main、release/tag、文章檔、registry 與 sitemap 對同一發布 run 有一致證據。
- `SC-PUBLISH-RECOVERY-002`：新文章發布後 sitemap URL 數由基準增加至少 1；rewrite 不得冒充文章數增加。
- `SC-PUBLISH-RECOVERY-003`：恢復後 coordinator、四個 lane runner、Publisher、capacity guard 均有健康／exit 證據。

## 執行切片與 blocking edges

### `SLICE-PUBLISH-RECOVERY-A`：新版 promotion preflight

- `traces_to`：`FR-PUBLISH-RECOVERY-001`、`FR-PUBLISH-RECOVERY-002`
- Frontier：可立即執行。
- 讀取並遵守 storage capacity 與 production canary readiness 規則。
- 收集 current actor／manifest／stage／queue snapshot digest、正式 origin/main、容量 exercise receipt。
- 先跑 plan-only；不得 mutation。
- 若 promotion 契約因 failed run registry 阻擋，先證明 root cause；不得手工清 queue。
- 驗證：plan digest 可重現、target SHA 正確、preserved run identity 完整、capacity receipt PASS。

### `SLICE-PUBLISH-RECOVERY-B`：正式 runtime promotion 與七服務重載

- `traces_to`：`FR-PUBLISH-RECOVERY-001`、`FR-PUBLISH-RECOVERY-002`、`SC-PUBLISH-RECOVERY-003`
- Blocked by：`SLICE-PUBLISH-RECOVERY-A` PASS。
- 只能走正式 aggregate promotion transaction（plan → apply → postcheck → finalize）與正式 installer／activation 入口。
- 禁止用「只 fetch 舊 actor 的 origin/main」作為完成方案。
- promotion 前後都要保留 rollback receipt；任一步失敗即 fail-closed。
- 驗證：runtime actor SHA、manifest actor_head、generation、readiness ack、activation barrier、七個 plist identity 全部一致。

### `SLICE-PUBLISH-RECOVERY-C`：新文章端到端發布

- `traces_to`：`US-PUBLISH-RECOVERY-001`、`FR-PUBLISH-RECOVERY-003`、`SC-PUBLISH-RECOVERY-001`、`SC-PUBLISH-RECOVERY-002`
- Blocked by：`SLICE-PUBLISH-RECOVERY-B` PASS。
- 使用新版 coordinator／new lane／Publisher 正式入口；不得人工拼文章或手改 registry／sitemap。
- 必須選「新文章」run；rewrite／i18n 成功不能替代 sitemap 數增加驗收。
- 驗證：run receipt → article path → registry → sitemap → commit → annotated tag → remote push 的 correlation 完整，公開 sitemap 數增加至少 1。

### `CHECKPOINT-PUBLISH-RECOVERY-001`：持續運作檢查

- `traces_to`：全部 `SC-*`。
- Blocked by：`SLICE-PUBLISH-RECOVERY-C` PASS。
- 再觀察至少一個排程週期，確認 Publisher 不再重複出現原本的 `PublishBlocked`，容量 guard 未觸發 stop-loss，queue 沒有 identity 遺失。

## 可修改範圍

- 專案內與正式 runtime promotion、manifest、queue preservation、launchd installer、Publisher／coordinator 直接相關的程式、測試、文件與 evidence。
- production runtime、`~/Library/LaunchAgents` 與 GitHub origin 僅限上述正式流程所需的 mutation。
- 若 source code 必須修復：先 RED 測試、最小 GREEN、受影響測試與 `git diff --check`；清楚回報 branch／commit。未進入 main 的修復不得宣稱已部署。

## 禁止範圍

- 不得刪除或手動改寫 production queue／run state。
- 不得繞過 capacity、manifest identity、activation barrier、Publisher transaction、tag 或 push gate。
- 不得用舊 runtime 的單純 `git fetch` 當作新版恢復完成。
- 不得把 rewrite 或單次本機生成當作 sitemap 新文章增加。
- 不得自行封存 task。

## 使用者授權

使用者已明確授權：以新版正式流程執行 production runtime promotion、必要的 launchd reload／kickstart，以及 Publisher 對 Pantheon GitHub origin 的正式 commit／annotated tag／push。授權不包含刪除 queue、繞過 gate、強推或改寫歷史。

## 交付格式

回報必須逐項區分：已建立、執行中、已 promotion、已發布、已推送、已驗收。附上：

1. source／runtime／remote SHA 與 manifest digest。
2. promotion plan／apply／finalize receipt。
3. 七服務狀態與 Publisher 原錯誤消失證據。
4. 發布 run ID、文章 slug／title、commit、tag、遠端 main。
5. sitemap 發布前後數量與公開 URL。
6. 尚存風險與 backlog；不得用模糊的「完成」代替分階段狀態。
