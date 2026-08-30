# Pantheon Acceptance B：Rule24 容量阻擋分診結果

status: `RULE24_EVIDENCE_GAP`

## 裁決

這不是實際 host reserve 不足。`dfcb` receipt 的 `NO-GO` 是兩個 cycle 都拿不到 swap telemetry；在受限執行環境中，`sysctl` 與程式內 `sysctlbyname` 均回傳 permission denied。相同主機以唯讀 host 權限讀取 `vm.swapusage` 成功，證明 telemetry 存在。

主機在事故 receipt 與本次量測時都高於 Rule24 保留線；容量 shortfall 是 `0 GiB`。因此不需要靠刪檔才能回到 PASS。

## Host reserve 證據

- filesystem total：`245,107,195,904` bytes（`228.274 GiB`）。
- Rule24 10%：`24,510,719,590` bytes。
- 20 GiB：`21,474,836,480` bytes。
- required reserve：`24,510,719,590` bytes（10% 較高）。
- dfcb receipt 最後一個 cycle 的 host free：`27,302,150,144` bytes；高於 reserve `2,791,430,554` bytes（約 `2.600 GiB`）。
- 本次唯讀量測 host free：`27,286,179,840` bytes；高於 reserve `2,775,460,250` bytes（約 `2.585 GiB`）。
- 既有 normalized capacity proof 的 retention peak：`1,610,645,859` bytes。即使由本次 free 扣除該峰值，仍高於 reserve `1,164,814,391` bytes（約 `1.085 GiB`）。
- 到 host reserve PASS 至少需釋放：`0 GiB`。

## 為何 receipt 是 NO-GO

形成鏈已定位：

1. `run_bounded_exercise()` 只要任一 cycle 的 `rss_available` 或 `swap_available` 不是 `true`，便直接輸出 `NO-GO`。
2. dfcb receipt 兩個 cycle 都是 `rss_available=true`、`swap_available=false`。
3. 受限環境實測：`sysctl` 回傳 `Operation not permitted`；fallback `sysctlbyname` 回傳 errno 1。
4. 相同主機的唯讀 host telemetry 成功回傳 swap total／used／free。

因此 receipt 的直接 NO-GO 原因是 swap sensor 權限，不是 host reserve。

該 synthetic receipt 本身也不含 Rule24 要求的 `max_bytes`、`max_file_count`、正常增長率、尖峰視窗、保留期與 projection 欄位；但這些欄位缺失並未參與 `run_bounded_exercise()` 的 status 計算。完整欄位已存在於既有 `resume-1e46-rule25-readiness/package/capacity-proof-normalized.json`，狀態為 PASS。要讓 dfcb gate 的證據契約自足，仍應把 fresh host telemetry 與該 normalized policy/projection 明確綁定，而不是用清理檔案繞過。

## Pantheon 範圍容量盤點

- main repo：`1,257,783,296` bytes（`1.171 GiB`）。主要為 `.git` `583,139,328`、`.work` `339,361,792`、`artifacts` `90,673,152` bytes。
- Documents 內全部 Pantheon runtime roots：`1,597,382,656` bytes（`1.488 GiB`）；其中 v8 為 `1,595,658,240` bytes。
- `/private/tmp` 內名稱明確屬 Pantheon 的 192 個 root：`14,099,693,568` bytes（`13.132 GiB`）。
- Git 已登記的 12 個 Pantheon worktree：`1,595,539,456` bytes；其中 Codex worktree 六個、`832,073,728` bytes 位於上述 tmp 統計之外。
- 去除已知重疊後，本次盤點的 Pantheon scope 合計約 `17,786,933,248` bytes（`16.565 GiB`）。

## 分類

### authoritative / non-rebuildable

- main `.git`、`artifacts`。
- live v8 `actor`、`queue`、`state`、`gsc-copy`、`evidence`、`quarantine`、`transactions`、`logs`。
- 以上不得為本次容量事件清除。

### rebuildable / cache / temp

- main `.venv`、`.pytest_cache`、`.codegraph`：可重建，但總量小，且沒有容量 shortfall。
- live v8 `dependencies`：來源可重建，但目前是 live runtime dependency，不列入安全清理。
- dfcb bounded exercise 遺留的單一 `cycle-2.bin`：`1,048,576` bytes，receipt 已證明為 synthetic temp。
- 六個較早、未登記為 worktree、tracked clean、origin 為 Pantheon 且 HEAD 可由 `origin/main` 到達的 standalone source clone，合計 `4,129,411,072` bytes（`3.846 GiB`）。僅在 Owner 明確授權且再次確認未被當前程序引用後可回收。

### unknown / retain

- live v8 `backups`：`726,896,640` bytes，含 rollback bundle；未完成 retained-reference audit，保留。
- main `.work/archive/capacity-20260813`：`311,373,824` bytes；ownership 雖屬 Pantheon，但是否仍為 acceptance evidence 未證明，保留。
- 其餘 non-git tmp roots與所有已登記 worktree：可能含未提交證據／handoff／unique lineage，保留。
- 當前 `dfcb`、`1e46`、`5704` final-publish source clone：即使 clean，仍在本輪正式發文續接鏈上，不列入清理候選。

## Owner 授權後的最小操作

回到 Rule24 PASS 的必要操作不是清空檔案，而是：

1. 在可讀 host telemetry 的執行邊界重新產生一次 bounded exercise receipt，使兩個 cycle 的 swap telemetry 都為可用。
2. 將 fresh receipt 與既有完整 policy／projection proof 的 digest 明確綁定；若契約要求同 SHA freshness，則重新產生 normalized proof。
3. 重新驗證 projected free 仍高於 `24,510,719,590` bytes。

若 Owner 額外希望增加空間緩衝，可先審批 machine receipt 內的明確 allowlist 候選；本卡沒有執行任何清理。

## 邊界確認

- production mutation：`0`
- promotion／publisher：`0`
- push／tag：`0`
- launch agent stop／start：`0`
- 刪除／移動／壓縮：`0`

