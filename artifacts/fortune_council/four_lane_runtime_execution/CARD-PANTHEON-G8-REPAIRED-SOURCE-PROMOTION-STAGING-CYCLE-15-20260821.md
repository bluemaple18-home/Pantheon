---
id: CARD-PANTHEON-G8-REPAIRED-SOURCE-PROMOTION-STAGING-CYCLE-15-20260821
status: ready
chain_id: PANTHEON-G8-PRODUCTION-READINESS-20260820
role: implementation
cycle: 15
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 固定 SHA 的 production push 與 runtime restaging；規格已鎖定但回退成本高。
---

# 推送 G8 修復版並重建 staging（Cycle 15）

## 目標

以正式 Gate A module 入口驗證一次性 mutation authority；通過後，將 production authority `c05929f2a7dac86e94aaeaa5ab6c5455892f5f77` 普通 fast-forward push 至 `origin/main`，再執行一次正式 runtime promotion/restaging。停在 activation 前。

## 鎖定 authority

- source SHA：`c05929f2a7dac86e94aaeaa5ab6c5455892f5f77`
- expected actor SHA：`88c6c0a95a013d0e9e8ab84c1a0f75a58ada1ff5`
- expected remote SHA：`88c6c0a95a013d0e9e8ab84c1a0f75a58ada1ff5`
- Python：`/Users/mattkuo/Documents/Pantheon/.venv/bin/python`，必須先證明 Python 3.12.12 且可執行。
- Gate A public CLI：`/Users/mattkuo/Documents/Pantheon/.venv/bin/python -m scripts.pantheon_gate_a_governance ...`
- transaction root：`/Users/mattkuo/Documents/Pantheon-canary-runtime-v8/transactions/g8-repaired-source-promotion-staging-cycle-15-20260821`

## 允許

1. current capability、capacity、remote/actor/manifest/stage/queue 與 release dry preflight。
2. deterministic promotion plan。
3. 建立 exact apply argv、一次性 authorization/state；只執行一次 Gate A module invocation。
4. Gate A `READY` 後執行一次普通 fast-forward push：`c059...:refs/heads/main`。
5. remote 精確成為 `c059...` 後，執行一次正式 promotion apply/postcheck/finalize 與七服務 restaging；不得 activation。
6. 寫本卡專屬 evidence。主線負責保存 commit；task 不得因 git index 權限改用 alternate index/object store。

## 禁止

- 禁止 system Python、file-path Gate A 入口、新建 venv、第二次 Gate A invocation。
- 禁止 force push、第二次 push、source/tests/config/workflow 修補。
- 禁止 activation、canary、lane run、Publisher transaction、tag、publish。
- 禁止 alternate index、alternate object store、`git commit-tree`。
- 禁止重用舊 transaction root 或舊 authorization。
- 任一 current gate、remote/actor identity、plan、Gate A、push postcheck 或 promotion postcheck 非 PASS：立即停止，不換入口、不重試。

## 驗收

- 唯一 Gate A module invocation：exit 0、JSON `status=READY`、`apply_calls=0`、`production_mutation=0`。
- push：before=`88c6...`、after=`c059...`，一次普通 fast-forward。
- actor/manifest/private stage 轉為 target authority；七服務 staged coherent，live 保持 preactivation 狀態。
- queue 既有 run IDs 完整保留；無 canary、publish、tag。
- `git diff --check`。

## 交付

- `STAGED / NO CANARY` 或 `BLOCKED / NO CANARY`。
- evidence：`.work/CARD-PANTHEON-G8-REPAIRED-SOURCE-PROMOTION-STAGING-CYCLE-15-20260821/`
- 回報 evidence manifest SHA256、remote before/after、actor/manifest/stage/generation、七服務 staged/live、mutation counts。
