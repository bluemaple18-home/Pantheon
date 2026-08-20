---
id: CARD-PANTHEON-G8-MAIN-PUSH-RUNTIME-PROMOTION-STAGING-RETRY-2-20260820
chain_id: PANTHEON-FOUR-LANE-PRODUCTION-RECOVERY-20260818
parent_card_id: CARD-PANTHEON-G8-MAIN-PUSH-RUNTIME-PROMOTION-STAGING-RETRY-1-20260820
role: implementation
cycle: 11
status: ready
type: production_runtime_convergence
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: blocker已固定為 worktree Python capability，後續仍含高回退成本正式操作。
ownership:
  - .work/CARD-PANTHEON-G8-MAIN-PUSH-RUNTIME-PROMOTION-STAGING-RETRY-2-20260820/**
  - worktree-local .venv與UV cache
  - 唯一一次通過本機hook後的 origin/main fast-forward push
  - 正式 promotion transaction與 seven-service staging
forbidden_scope:
  - activation、canary、發文、Publisher transaction、tag、force push、第二次有效 push
  - source修補、繞過/停用hook、手改queue/state/plist/barrier/manifest
verification:
  - task-local UV cache建立 .venv；lockfile與tracked source零變更
  - release record/pre-push gate在零 remote mutation下先PASS
  - remote fast-forward至 exact source
  - promotion plan/apply/postcheck/finalize與 staged seven完整receipt
  - live/queue/transaction/tag/launchctl/content mutation delta為零
evidence_path: .work/CARD-PANTHEON-G8-MAIN-PUSH-RUNTIME-PROMOTION-STAGING-RETRY-2-20260820/
---

# G8 main push 與 promotion/staging retry 2

## 工作名稱 → 正在做什麼 → 現在狀態

修復 worktree Python capability → 通過本機 release gate後續做一次 fast-forward push與正式 promotion/staging → `READY / USER AUTHORIZED`

## Root Question

在不繞過 hook、不改 source、不 activation/canary的條件下，能否補齊 worktree `.venv/bin/python` 後完成已授權的唯一有效 push與 runtime convergence？

## 已知 blocker與授權

- retry 1 的普通 push invocation在任何 remote mutation前被本機 pre-push/release record gate擋下：缺 `.venv/bin/python`。
- origin/main before/after均為 `b8a34451e7a2b10a9e7ce1f11f366250cc67d87b`；promotion apply calls=0，staging/activation/canary/publish/tag皆未執行。
- 使用者 2026-08-20 的「授權」仍限一次實際 fast-forward push＋正式 promotion/staging；禁止 force、activation、canary、發文、tag。

## 執行

1. 鎖 dispatch初始 HEAD為 exact source，驗 clean、remote未漂移，讀 toolchain_paths。
2. 設定 evidence目錄下 task-local `UV_CACHE_DIR`，用 `uv sync --frozen`建立 worktree `.venv`；不得變更 lockfile或tracked files。
3. 用正式 release record/pre-push檢查入口做零 remote mutation預驗；非PASS即 `BLOCKED / NO CANARY`，不 push。
4. 重建 current promotion plan與 Gate A一次性authorization；plan/digest/remote/actor/manifest/stage任一漂移即停。
5. 緊鄰push前重讀remote並驗ancestor；只執行一次普通 fast-forward `main:main`。push後remote必須等於 exact source。
6. 正式 apply→postcheck；失敗走同transaction rollback。PASS才finalize。
7. 只走正式 installers純 staging seven；禁止load/kickstart/reload/barrier child I/O。正式 preactivation transition驗 staged coherent且old live未變。

## 停損與交付

- 同 blocker再失敗即達第三次，停止；不得再開 retry 3。
- 不刪 queue、不清使用者檔、不動其他 worktree。
- 最終只可 `STAGED / NO CANARY` 或 `BLOCKED / NO CANARY`；附remote、promotion、identity與零mutation證據。
