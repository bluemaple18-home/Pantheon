# Pantheon G8 current readiness 交接

## Goal

用正式側邊欄 task 與隔離 worktree，重建 APF-004 的 current capability／capacity receipt，確認四線正式入口是否可用；未取得 current 證據前不得宣稱四線 READY，也不得碰 production。

## Root Question

如何讓 G8 readiness 的唯一正式生成命令在受控 task 內成功執行，產出可驗收的 current receipt，而不是沿用舊 summary 或繞過正式流程？

## Current Blocker

正式 task 已執行卡片允許的唯一生成命令一次，但 `uv` 在進入 receipt generator 前，因共用 cache 權限失敗：

```text
error: failed to open file /Volumes/VibeCode/Caches/uv/sdists-v9/.git: Operation not permitted (os error 1)
```

因此本輪沒有生成 current receipt、沒有 candidate commit，也沒有 current READY 結論。

## Candidate Fork

- 建議主路徑：另開一張 retry 卡，明確把 `UV_CACHE_DIR` 指到新 worktree 內可寫的 task-local cache，再只執行一次相同 generator。
- 替代路徑：取得明確授權後，在允許讀取既有 `/Volumes/VibeCode/Caches/uv` 的外部 runtime 執行同一正式命令。
- 禁止在原卡重跑；原卡契約明定唯一命令失敗即停止。

## Constraints & Preferences

- 使用者偏好：開卡、正式側邊欄派工、監工、節省模式；不要全用 GPT-5.6 Sol。
- 本卡採 standard／Terra medium；主線負責驗收與整合。
- 不得用隱藏 sub-agent 冒充正式 task。
- 不得修改 production、publish、tag、push、deploy、schedule 或 LaunchAgent。
- 不得拿既有 tracked summary 的 READY 狀態冒充本次 current 證據。
- 同一 blocker 第三次即停；目前這張 G8 卡只嘗試一次，且依「唯一命令」契約已停止。
- 保留主工作區既有 untracked 使用者檔案，不得清除或覆寫。

## Completed Actions

1. 建立並提交正式卡：
   - `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-CURRENT-READINESS-RECEIPT-20260819.md`
   - main/card commit：`785f62325f0465a79803f82ac32a0d674cf4b98e`
2. 完成 visible-thread prepare-create、容量檢查、正式 thread 建立、worktree 驗證與 activation。
3. 正式 task：
   - title：`核對 G8 四線正式入口`
   - thread ID：`01a01dbc-7364-79b0-9d92-ed5181e6d791`
   - worktree local-only path：`/Users/mattkuo/.codex/worktrees/4c9b/Pantheon`（不可跨機照抄）
4. Control plane 的 CodeGraph index 已對齊 card HEAD；task 也完成任務語意 query。
5. task 只執行一次 generator；exit 2 後依卡片停止，未重跑、未 fallback、未修改 source。
6. 已驗證 task tracked diff 為空、`git diff --check` 通過、worktree clean。
7. 為通過容量閘門，已移除一個乾淨且已整合的舊 Repair worktree；其 candidate patch 與 main 的整合 commit patch-id 相同，歷史 commit 與測試紀錄仍可追溯。

## Active State

- 主工作區：`<repo-root>`
- main HEAD：`785f62325f0465a79803f82ac32a0d674cf4b98e`
- main 相對 `origin/main`：ahead 8。
- 正式 G8 task：已完成並回報 `BLOCKED`，目前 idle。
- Candidate SHA：無。
- Changed tracked files in task：0。
- Production mutation：0。
- 主工作區另有既存 untracked 卡片／artifact，皆視為使用者資產，本輪未動。

## Evidence

- 正式卡：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-CURRENT-READINESS-RECEIPT-20260819.md`
- task local-only log：`/Users/mattkuo/.codex/worktrees/4c9b/Pantheon/.work/CARD-PANTHEON-G8-CURRENT-READINESS-RECEIPT-20260819/generation.log`（不可跨機照抄；worktree 收掉前需另存必要證據）
- task final：thread `01a01dbc-7364-79b0-9d92-ed5181e6d791`，結論為 uv cache permission BLOCKED。
- 舊 tracked `readiness-summary.json` 雖顯示 READY，但不是本次生成，不能作 current acceptance。

## In Progress / Remaining Work

1. 不要回原 task 重跑。
2. 先開 retry 實體 `.md` 卡，唯一改變只應是可寫的 task-local `UV_CACHE_DIR` 契約；generator、輸出 ownership、停損與 production 禁區維持不變。
3. 用新的 verification identity/cycle 建立一個正式側邊欄 task，完成 bootstrap、activation 後只跑一次。
4. 若生成成功，核對 receipt 數量、digest、capability/capacity/official gates、changed file allowlist、`git diff --check`，READY 才收 candidate。
5. 主線整合 candidate 後再跑受影響驗收；在此之前不得宣稱四線已打通。

## Waiting Conditions

- 需要使用者授權建立 replacement/retry 正式卡；原卡不可自行擴張或重跑。
- 若選外部 runtime 路徑，另需明確授權該非本機／受限環境變更或權限範圍。

## Limits / Stop Conditions

- retry 卡仍只准一次 generator；非零即保存完整 log 並停止。
- 不得為解 cache 權限去改 generator、測試、config、共用規則或 production。
- 新證據未生成前，狀態只能是 BLOCKED／未驗收，不能引用舊 READY。
- 不建立同一 chain、同一 role、同一 cycle 的第二個正式 task。

## Key Decisions & Resolved Questions

- 問題不是 Publisher 四線邏輯再次失敗；命令尚未進入 generator，根因位於 `uv` 共用 cache 的 sandbox 權限邊界。
- 正規流程本身已成功走到正式 thread、隔離 worktree、activation 與唯一命令；本輪缺的是可寫 cache 契約。
- 不採「這裡直接修」或原 task 內第二次嘗試，避免重武裝與規則偷跑回圈。

## 新對話第一拍

```text
讀 handoff_20260820_g8_current_readiness_uv_cache_blocker.md 與 AGENTS.md。先只讀回報 root question、blocker、candidate fork、正式 task 狀態；不要重跑原卡、不要動 production。接著等待我授權 retry 卡。
```
