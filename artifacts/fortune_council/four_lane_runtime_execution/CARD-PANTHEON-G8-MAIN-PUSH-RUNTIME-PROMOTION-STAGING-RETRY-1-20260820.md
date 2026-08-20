---
id: CARD-PANTHEON-G8-MAIN-PUSH-RUNTIME-PROMOTION-STAGING-RETRY-1-20260820
chain_id: PANTHEON-FOUR-LANE-PRODUCTION-RECOVERY-20260818
parent_card_id: CARD-PANTHEON-G8-MAIN-PUSH-RUNTIME-PROMOTION-STAGING-20260820
supersedes:
  - CARD-PANTHEON-G8-MAIN-PUSH-RUNTIME-PROMOTION-STAGING-20260820
role: implementation
cycle: 10
status: ready
type: production_runtime_convergence
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 固定契約的高回退成本 production runtime 操作。
ownership:
  - .work/CARD-PANTHEON-G8-MAIN-PUSH-RUNTIME-PROMOTION-STAGING-RETRY-1-20260820/**
  - 唯一一次 origin/main fast-forward push
  - 唯一一次正式 promotion transaction與 seven-service staging
forbidden_scope:
  - activation、launchctl mutation、canary、發文、Publisher transaction、tag、第二次 push
  - force push、改寫歷史、手改 queue/state/plist/barrier/manifest、修改 source
verification:
  - exact source/remote/actor/manifest/stage/live基線
  - capability READY、capacity PASS、canary_created=false
  - push fast-forward且 remote精確等於 source
  - promotion plan/apply/postcheck/finalize完整 receipt
  - staged seven coherent；live、queue、transaction、tag、launchctl與內容 mutation delta為零
  - git diff --check、evidence完整、worktree clean
evidence_path: .work/CARD-PANTHEON-G8-MAIN-PUSH-RUNTIME-PROMOTION-STAGING-RETRY-1-20260820/
---

# G8 main push 與 runtime promotion/staging retry 1

## 工作名稱 → 正在做什麼 → 現在狀態

G8 runtime convergence → 一次 fast-forward push＋正式 promotion/staging → `READY / USER AUTHORIZED`

## Root Question

能否在零 activation、零 canary、零發文下，使 dispatch 初始 HEAD 成為 origin/main、actor、runtime manifest與 staged seven 的唯一 authority？

## 使用者授權

- 2026-08-20 使用者明確回覆「授權」：一次 origin/main fast-forward push與正式 runtime promotion/staging。
- 不含 activation、canary、發文、Publisher transaction、tag、第二次 push、force push或 source修補。

## 前置與失敗緣由

- 原 cycle 9 僅因 control-plane `task_intro` 超過 50 字而 `ABORTED_PRECREATE`；沒有 thread、worktree、外部寫入或 production mutation。
- dispatch 初始 HEAD鎖為 exact source；已知 reviewed base `ab6f3623b42bd57f61ed40e7d66e4e8171732d8a`，current readiness為 READY、capacity兩週期 PASS、七步 capability PASS、`canary_created=false`。
- 授權前最後成功核對 origin/main為 `b8a34451e7a2b10a9e7ce1f11f366250cc67d87b`；正式 push前必須重新讀取，漂移即停。

## 執行

1. 唯讀保存 exact source、clean state、origin URL、remote main、actor HEAD、manifest/private-stage digest、staged/live seven、queue/transaction/tag/launchctl基線。
2. 重新驗 current readiness/capacity對 exact source有效；用正式 promotion `plan` 與 canonical sorted unique preserve-run IDs。任何非 READY/PASS/READY_TO_APPLY：零 mutation停止。
3. push緊鄰前重讀 remote；驗 remote為 exact source ancestor。只執行一次普通 fast-forward `main:main`；禁止 force。結果不確定即停，不 retry。push後 remote必須精確等於 source。
4. 依 `scripts/pantheon_gate_a_governance.py` schema建立 exact apply argv、plan digest、一次性 authorization/state；只由正式 governance/aggregate入口 apply一次。
5. 保留 rollback bundle。postcheck失敗就同 transaction正式 rollback並停止；PASS才 finalize，保存 COMMITTED receipt。
6. 只用正式 installers產生 seven-service staged aggregate；禁止 load/kickstart/reload/barrier child I/O。用正式 preactivation transition/capacity入口驗 new staged seven coherent且 old live未變。
7. 驗 actor、manifest、private stage、staged seven同一 source/identity/generation/digest；live、queue、transactions、tags、launchctl與內容 mutation delta均為零。

## 停損與交付

- 每一外部 write一次；不盲 retry。同 blocker第三次停止。
- 不刪 queue、不清使用者檔案、不動其他 worktree；到 activation邊界立即停止。
- 交 remote before/after、promotion各階 receipt、identity matrix、零 mutation delta。
- 最終只能是 `STAGED / NO CANARY` 或 `BLOCKED / NO CANARY`。
