---
id: CARD-PANTHEON-G8-MAIN-PUSH-RUNTIME-PROMOTION-STAGING-20260820
chain_id: PANTHEON-FOUR-LANE-PRODUCTION-RECOVERY-20260818
parent_card_id: CARD-PANTHEON-G8-CURRENT-READINESS-NO-SYNC-CYCLE-4-20260820
role: implementation
cycle: 9
status: ready
type: production_runtime_convergence
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 契約已固定，但 fast-forward push 與正式 runtime promotion/staging 是高回退成本操作。
ownership:
  - .work/CARD-PANTHEON-G8-MAIN-PUSH-RUNTIME-PROMOTION-STAGING-20260820/**
  - 本卡唯一一次 origin/main fast-forward push
  - 本卡唯一一次正式 runtime promotion transaction 與 rollback bundle
  - 本卡正式 seven-service staging receipts
forbidden_scope:
  - production activation、launchctl load/kickstart/reload、建立或消耗 canary run
  - 發文、Publisher transaction、commit、tag、第二次 push
  - force push、改寫歷史、手改 queue/state/plist/barrier/manifest
  - 修改 source、tests、rules 或為通過 gate 現場修補程式
verification:
  - dispatch 初始 HEAD 鎖為 exact source SHA，worktree clean
  - origin/main 基線未漂移且只允許 fast-forward
  - current capability READY、capacity PASS、canary_created=false
  - 正式 promotion plan READY，apply 只消耗一次授權，postcheck PASS後才 finalize
  - actor、manifest、private stage、staged seven 同一 source/identity/generation/digest
  - live seven、queue、transactions、tags、launchctl 狀態與內容 mutation 前後不變
  - git diff --check、完整 evidence、worktree clean
evidence_path: .work/CARD-PANTHEON-G8-MAIN-PUSH-RUNTIME-PROMOTION-STAGING-20260820/
---

# G8 main push 與 runtime promotion/staging

## 工作名稱 → 正在做什麼 → 現在狀態

G8 main push 與 runtime promotion/staging → 將 current reviewed source fast-forward 推到 origin/main，完成正式 actor/manifest/private-stage convergence 與 seven-service 純 staging → `READY / USER AUTHORIZED`

## Root Question

能否在完全不 activation、不建立 canary、不發文的邊界內，將本卡 dispatch 初始 HEAD 以正式、可回滾且 fail-closed 的方式收斂為 origin/main、actor、runtime manifest 與 staged seven 的唯一 authority？

## 使用者授權

- 使用者於 2026-08-20 明確回覆「授權」，授權本卡執行一次 origin/main fast-forward push，以及正式 runtime promotion/staging。
- 授權不包含 production activation、canary、發文、Publisher transaction、tag、第二次 push、force push或 source 現場修補。

## 鎖定事實

- dispatch 初始 HEAD 即本卡 exact source authority；啟動後立即保存 40-char SHA，後續不得漂移。
- 授權前已知 local main base 為 `ab6f3623b42bd57f61ed40e7d66e4e8171732d8a`；current readiness cycle 4 為 `READY`，100 份 evidence、兩週期 capacity PASS、capability 七步 PASS、`canary_created=false`。
- 授權前最後成功核對的 origin/main 為 `b8a34451e7a2b10a9e7ce1f11f366250cc67d87b`；正式 push 前必須重新讀取，若不同即停止，不准猜測或 merge。
- production actor 曾回報不同 HEAD；必須以正式 promotion plan 重新量測 current actor/manifest/stage/live tuple，不得依賴舊狀態文案。

## 執行順序

### 1. 零 mutation preflight

1. 保存 dispatch 初始 HEAD、worktree clean、origin URL、remote main、actor HEAD、manifest digest、private-stage digest、staged/live seven、queue/transaction/tag 與 launchctl 基線。
2. 重新驗證 current readiness/capacity artifacts 對 exact source 有效；任何 source/correlation/evidence 漂移即 `BLOCKED`。
3. 用 `scripts/pantheon_content_runtime_promotion.py plan` 建立 deterministic plan；preserve-run IDs 必須 canonical sorted unique，禁止改 queue。
4. plan 非 `READY_TO_APPLY`、remote main 非已知 ancestor、actor/manifest/stage identity 不可證明、容量非 PASS：零 production mutation停止。

### 2. 唯一 fast-forward push

1. 緊鄰 push 前再次 `git ls-remote --heads origin main`；必須等於 preflight remote SHA。
2. 驗證 remote SHA 是 exact source 的 ancestor；只允許一般 fast-forward `main:main`，禁止 force、lease force、merge或 rebase。
3. push 後重新讀 remote；必須精確等於 exact source SHA。失敗或結果不確定即停止，不 retry。

### 3. 正式 promotion transaction

1. 依正式 Gate A schema產生 exact apply argv artifact、plan digest、一次性 authorization/state；所有 immutable tuple 綁 exact source與本卡 evidence root。
2. 只透過正式 governance/aggregate promotion 入口執行一次 `apply`；保留 rollback bundle。
3. postcheck 必須證明 actor、manifest、private stage、queue preservation、runtime/config/generation/digest與 plan完全一致。
4. postcheck失敗：走同一 transaction正式 rollback並停止；不得 finalize失敗狀態。
5. postcheck PASS才執行正式 `finalize`，保存 COMMITTED receipt。

### 4. 純 staging

1. 只走既有正式 installers 產生 seven-service staged aggregate；不得 load、kickstart、reload或執行 barrier child I/O。
2. 使用正式 preactivation transition/capacity 入口驗證：new staged seven coherent、old live seven仍維持原狀且 loaded/no-PID契約可判讀。
3. staged destination、identity、generation、manifest digest、actor/config/runtime path或 Publisher marker任一漂移即停止；若 promotion rollback bundle尚在，依正式狀態決定 rollback，不猜測清理。

## 停損

- 任一外部 write只執行一次；輸出不確定即停止，不盲重試。
- 同一 blocker第三次失敗停止；本卡不得另開 Repair/Reviewer/canary。
- 不刪 queue、不清使用者檔案、不移除其他 worktree、不封存其他進行中 task。
- 到達 activation邊界立即停止；不得因 staging成功順手 activation。

## 交付

- exact source、remote before/after、push結果。
- promotion plan/apply/postcheck/finalize/rollback狀態與 digest。
- actor、manifest、private stage、staged seven、live seven before/after identity matrix。
- queue/transaction/tag/launchctl/content mutation delta 必須為零。
- 最終只能是 `STAGED / NO CANARY` 或附唯一 blocker 的 `BLOCKED / NO CANARY`。
