---
id: CARD-PANTHEON-G8-HOST-SWAP-CAPACITY-EXERCISE-CYCLE-16-20260821
status: ready
chain_id: PANTHEON-G8-PRODUCTION-READINESS-20260820
role: implementation
cycle: 16
thickness: minimal
risk: medium
model: gpt-5.6-luna
reasoning: medium
model_reason: 根因與命令均已鎖定，只需一次宿主權限 bounded exercise 與證據驗證。
---

# 驗證宿主 swap telemetry 與容量演練（Cycle 16）

## 工作名稱 → 正在做什麼 → 現在狀態

`G8 宿主 swap 容量演練` → 以正式 venv 在宿主權限下執行一次 bounded synthetic exercise → `READY / NO PRODUCTION MUTATION`

## 根因證據

- Cycle 15 receipt：兩個 cycle 均 `swap_available=false`，因此 `NO-GO`。
- sandbox minimal reproduction：`_swap_used_bytes()` 回傳 `swap_sources_failed:command:1;fallback:sysctlbyname_failed:1`。
- sandbox `/usr/sbin/sysctl vm.swapusage`：`Operation not permitted`。
- 同一宿主命令在授權後成功，能讀出 total / used / free；因此 blocker 位於 Codex sandbox 權限層，不是容量 guard parser 或主機缺少 telemetry。

## 目標

使用 `/Users/mattkuo/Documents/Pantheon/.venv/bin/python`（必須證明 Python 3.12.12）在宿主權限下執行唯一一次正式 bounded capacity exercise，產生新的 Cycle 16 receipt。只驗證容量安全閘門，不延伸到 promotion 或 production。

## 唯一允許的 mutation invocation

```text
/Users/mattkuo/Documents/Pantheon/.venv/bin/python -m scripts.pantheon_content_capacity_guard --exercise-root .work/CARD-PANTHEON-G8-HOST-SWAP-CAPACITY-EXERCISE-CYCLE-16-20260821/capacity-exercise --receipt .work/CARD-PANTHEON-G8-HOST-SWAP-CAPACITY-EXERCISE-CYCLE-16-20260821/capacity-receipt.json exercise
```

- 此 invocation 必須直接要求宿主／sandbox escalation；不得先在 sandbox 試跑。
- approval 被拒或 invocation 非 exit 0：立即 `BLOCKED / NO PRODUCTION MUTATION`，不得第二次執行。
- 允許唯讀檢查 Python 版本、Git SHA、receipt、manifest 與 `git diff --check`。
- 允許建立本卡專屬 evidence manifest；主線負責保存 commit。

## 禁止

- 禁止修改 source、tests、config、workflow 或安全門檻。
- 禁止第二次 capacity exercise、替代 swap source、mock telemetry 或手改 receipt。
- 禁止 Gate A、push、promotion、activation、canary、lane run、Publisher transaction、tag、publish。
- 禁止清除其他 task evidence、worktree 或側邊欄 thread。
- 禁止 alternate index/object store、`git commit-tree`。

## 驗收

- Python 精確為 3.12.12。
- 唯一 exercise invocation exit 0。
- receipt `status=PASS`、`production_mutation=false`。
- 兩個 cycles 的 `rss_available=true`、`swap_available=true`，swap before/after 皆為非負整數。
- reclamation 只刪本卡 allowlist 中的 synthetic file；stop-loss `status=STOPPED`、`remaining_loaded=[]`、`cross_project_deletions=[]`。
- `git diff --check` 通過。

## 交付

- `CAPACITY PASS / NO PRODUCTION MUTATION` 或 `BLOCKED / NO PRODUCTION MUTATION`。
- evidence：`.work/CARD-PANTHEON-G8-HOST-SWAP-CAPACITY-EXERCISE-CYCLE-16-20260821/`
- 回報 invocation count、exit code、receipt SHA256、兩個 cycle telemetry、reclamation、stop-loss 與 production mutation count。
