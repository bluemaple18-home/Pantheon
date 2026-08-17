# Publisher prerender 有界等待修復結果

狀態：`DELIVERED_CANDIDATE`

- prerender 子程序現在有 300 秒固定 timeout，逾時會 fail-closed。
- `PrerenderTimeout.diagnostic` 提供 command、cwd、elapsed_seconds、timeout_seconds 與 `timed_out` outcome；不收集環境變數。
- 保留既有 policy failure JSON 到 `PolicyRejected` 的轉換。
- 沒有執行 production、launchd、transaction recovery、deploy、publish 或 push。

候選 commit 由本卡工作線建立；未宣稱已整合或 production 已修復。
