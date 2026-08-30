# Pantheon 工作區事故現場封存

## 狀態

`DO_NOT_MERGE / FORENSIC_REVIEW_ONLY`

此文件封存 2026-08-30 主工作區累積變更，供其他 Reviewer 判斷 scope 膨脹、證據重複、未整合成果與錯誤控制流程。它不是 release candidate，也不得直接合併到 `main`。

## Git 基線

- 本機 branch：`main`
- 本機 HEAD：`9d6915660124e3a5b41a0878b2c80ab4aecbe6aa`
- 當時 `origin/main`：`54ad8654675dbf729367a25a5093a52b379b2538`
- 本機 main 明顯落後 remote；此 snapshot 只保留事故現場，不代表可 rebase／merge。

## 變更盤點

- tracked 修改：3 files，約 `+481/-24`。
- untracked：1,730 files，約 16,968 KiB。
- untracked `wc -l` 合計：約 198,356 lines。
- Codex UI 顯示：約 `+195,107/-24`；與 shell 計數差異來自 UI 的 binary／directory／line counting 方式。
- 主要內容：cards、RCA／review RESULT、promotion snapshots、protected-byte manifests、stdout／stderr receipts、測試 harness、少量 screenshots。

## 安全檢查

- Dirty-only 常見 private key、Bearer token、OpenAI key 與 Google API key pattern：0 hits。
- 最大 dirty file 約 1 MiB；未發現 GitHub 100 MiB 單檔 blocker。
- `git diff --cached --check`：38 lines；主要是既存 raw HTTP headers 的 CRLF／trailing whitespace，以及 8 份 Markdown EOF blank-line 警告。為保留事故現場，forensic branch 不機械改寫這些 bytes。
- 此 snapshot 不授權 production、deploy、publish、service activation 或 registry mutation。

## 已知問題

1. 主線累積大量未整合 evidence，違反 bounded task 與 workspace hygiene。
2. 多輪 gate failure 被逐一轉成 Repair，沒有及時停止並縮回最後成功 publication path。
3. 主工作區與隔離 candidate 的 scope 被分開量測，導致主線低估整體膨脹。
4. 部分 evidence 是同一流程不同重跑的完整 snapshot，資訊價值遠低於其 review 成本。
5. 未接受的 replacement identity candidate 必須保存在獨立 forensic ref，不得混入此 snapshot 後宣稱 accepted。

## Reviewer 問題

Reviewer 只需回答：

1. 哪些檔案是 canonical evidence，哪些只是重複或可重建輸出？
2. 哪些 tracked source/test 修改具有獨立 measured gap 與 acceptance？
3. 哪些成果已在 `origin/main`，此處只是 stale duplicate？
4. 恢復單篇發文所需的最小既有正式入口為何？
5. 四線 automation 應保留、縮減、拆案或回退到哪個 accepted boundary？

## 禁止事項

- 不得直接 merge 此 branch。
- 不得以 snapshot 的存在證明任何 Repair 已接受。
- 不得用此 branch promotion、deploy 或 production publish。
- 不得在 review 前將 1,730 個 untracked files 一次性搬進 canonical main。
