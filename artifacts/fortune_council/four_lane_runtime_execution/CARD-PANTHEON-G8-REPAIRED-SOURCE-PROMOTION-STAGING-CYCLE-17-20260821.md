---
id: CARD-PANTHEON-G8-REPAIRED-SOURCE-PROMOTION-STAGING-CYCLE-17-20260821
status: ready
chain_id: PANTHEON-G8-PRODUCTION-READINESS-20260820
role: implementation
cycle: 17
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 固定 SHA 的 production push 與 runtime restaging；mutation authority 與停止條件必須嚴格鎖定。
---

# 推送 G8 修復版並重建 staging（Cycle 17）

## 工作名稱 → 正在做什麼 → 現在狀態

`G8 修復版 promotion staging` → 驗證 Gate A 後單次 fast-forward push 與 runtime restaging → `READY / NO CANARY`

## 已解除 blocker

- Cycle 16 capacity receipt：`.work/CARD-PANTHEON-G8-HOST-SWAP-CAPACITY-EXERCISE-CYCLE-16-20260821/capacity-receipt.json`
- receipt SHA256：`3773594ff3e3dea71902ff122b280818b91fb826659570606e45f34b6fc3f6ce`
- receipt `status=PASS`、兩輪 RSS/swap telemetry available、`production_mutation=false`。
- evidence 保存 commit：`53f5479449`。
- 本卡不得重跑 capacity exercise；只驗證上述 receipt 與 current capacity preflight 契約。

## 鎖定 authority

- source SHA：`c05929f2a7dac86e94aaeaa5ab6c5455892f5f77`
- expected actor SHA：`88c6c0a95a013d0e9e8ab84c1a0f75a58ada1ff5`
- expected remote SHA：`88c6c0a95a013d0e9e8ab84c1a0f75a58ada1ff5`
- Python：`/Users/mattkuo/Documents/Pantheon/.venv/bin/python`，必須先證明 Python 3.12.12。
- Gate A public CLI：`/Users/mattkuo/Documents/Pantheon/.venv/bin/python -m scripts.pantheon_gate_a_governance ...`
- transaction root：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/transactions/g8-repaired-source-promotion-staging-cycle-17-20260821`

## 允許

1. 唯讀 current capability、capacity receipt/preflight、remote/actor/manifest/stage/queue、release dry preflight。
2. deterministic promotion plan 與 exact apply argv。
3. 建立本卡全新的 authorization/state；只執行一次 Gate A module invocation。
4. Gate A `READY` 後執行一次普通 fast-forward push：`c059...:refs/heads/main`。
5. remote 精確成為 `c059...` 後，執行一次正式 promotion apply/postcheck/finalize 與七服務 restaging；不得 activation。
6. 寫本卡專屬 evidence。主線負責保存 commit；task 不得因 git index 權限改用 alternate index/object store。

## 禁止

- 禁止 system Python、file-path Gate A 入口、新 venv、第二次 Gate A invocation。
- 禁止重跑 capacity exercise、mock telemetry、降低安全門檻。
- 禁止 force push、第二次 push、source/tests/config/workflow 修補。
- 禁止 activation、canary、lane run、Publisher transaction、tag、publish。
- 禁止 alternate index/object store、`git commit-tree`。
- 禁止重用舊 transaction root、authorization 或 state。
- 任一 current gate、receipt hash、remote/actor identity、plan、Gate A、push postcheck 或 promotion postcheck 非 PASS：立即停止，不換入口、不重試。

## 驗收

- Cycle 16 capacity receipt hash 與 PASS 契約精確符合。
- 唯一 Gate A module invocation：exit 0、JSON `status=READY`、`apply_calls=0`、`production_mutation=0`。
- push：before=`88c6...`、after=`c059...`，一次普通 fast-forward。
- actor/manifest/private stage 轉為 target authority；七服務 staged coherent，live 保持 preactivation 狀態。
- queue 既有 run IDs 完整保留；無 activation、canary、publish、tag。
- `git diff --check`。

## 交付

- `STAGED / NO CANARY` 或 `BLOCKED / NO CANARY`。
- evidence：`.work/CARD-PANTHEON-G8-REPAIRED-SOURCE-PROMOTION-STAGING-CYCLE-17-20260821/`
- 回報 evidence manifest SHA256、remote before/after、actor/manifest/stage/generation、七服務 staged/live、Gate A/push/promotion/production mutation counts。
