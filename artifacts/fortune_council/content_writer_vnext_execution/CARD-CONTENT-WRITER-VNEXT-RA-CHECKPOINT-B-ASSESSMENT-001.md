---
id: CARD-CONTENT-WRITER-VNEXT-RA-CHECKPOINT-B-ASSESSMENT-001
status: ready
chain_id: CONTENT-WRITER-VNEXT-RUNTIME-ACTIVATION
role: review
cycle: 1
role_thread_policy: reuse-existing-reviewer
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: Checkpoint B 需固定整合 SHA，交叉驗證七段 identity/digest continuity、兩週期容量、官方 thin gate 與當前主機基線；架構已固定但影響 production authorization，適用 strict/core-bounded 跑道。
traces_to:
  - RA-CHECKPOINT-B
  - SC-human-authorization
  - SC-production-canary-readiness
  - STORAGE-CAPACITY-SAFETY-GATE-3
  - STORAGE-CAPACITY-SAFETY-GATE-5
depends_on:
  - RA-SLICE-004-INTEGRATED
  - RA-SLICE-005-INTEGRATED
  - RA-SLICE-006-INTEGRATED@643d535c1b21a577ea65cf2aa3845c35419b328f
  - RA-SLICE-007-INTEGRATED@136c737316b28bc119f667591ac15a4938f04f7d
---

# Writer vNext RA Checkpoint B：唯讀授權前評估

## 目標

固定整合主線 SHA，獨立重算 RA004–RA007 的 capability、capacity、readiness 與目前 host baseline，判定是否僅剩人類 production canary 授權。此卡不得建立或執行 canary。

## Ownership

- 本卡由 chain 既有唯一 Reviewer thread 執行；禁止建立第二個 Reviewer、replacement、Repair 或其他 task。
- 主線保留 production 授權請求、canary、整合與最終判定。
- `READY_FOR_AUTHORIZATION` 只表示可向使用者請求授權，不是 production authorization、canary readiness mutation 或 publication permission。

## Fixed inputs

- Integrated base：`136c737316b28bc119f667591ac15a4938f04f7d`。
- RA004：`runtime_activation/ra_slice_004/**`。
- RA005：`runtime_activation/ra_slice_005/**`。
- RA006：`runtime_activation/ra_slice_006/**`。
- RA007：`runtime_activation/ra_slice_007_capacity_preflight/**` 與 final strict review evidence。
- Repo authority：`scripts/pantheon_content_capability_receipt.py`、`scripts/pantheon_writer_vnext_runtime_activation_readiness.py`。
- Official thin gate authority：`<ai-core-root>/scripts/production_canary_readiness_gate.py`。

## Allowlist

只可新增：

`artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_checkpoint_b_assessment/**`

至少包含：

- `findings.json`
- `authority-map.md`
- `gate-results.json`
- `capacity-composition.json`
- `checkpoint-verdict.md`
- `verification.md`

## 必驗契約

1. 固定 HEAD、main ref、card source、clean state；任何 SHA 漂移即 `BLOCKED`。
2. 先以 repo readiness packager 重建 package；必須由 repo validator 驗 RA004 七段 identity、correlation、digest continuity、evidence provenance，再允許呼叫 official thin gate。
3. RA004 正向七段必須同 execution line／actor／runtime identity，step input/output digest 連續；缺步、identity drift、digest discontinuity、來源逃逸均 fail closed。
4. RA005 必須為兩個完整 synthetic non-production cycles、capacity `PASS`、cleanup reclaim 已實測、stop-loss negative 為 `BLOCKED`、峰值推估保留正式 reserve。
5. RA006 重建 package 必須與 committed authority 相容；positive official gate 為 `READY`、missing-step 為 `BLOCKED`。adversarial thin receipt 即使 official gate 回 `READY`，repo packager必須先回 `BLOCKED`。
6. RA007 committed host samples、versioned digest contract、四項 runtime 指標與 reserve 算術必須可重算；兩次 sample deficit 都為 0。RA007 卡內 `NO-GO` 不得被偷改成 `PASS`；aggregate assessment 只能引用 RA005 完整 policy proof 加 RA007 current baseline。
7. 確認 `canary_created=false`、`production_authorized=false`、`production_mutation=false`、正式服務 `0/4`。
8. JSON parse、portable path audit、changed-file allowlist、`git diff --check`、worktree clean。

## 判定

- 全部必驗條件成立且無 P0/P1：`CHECKPOINT_B_READY_FOR_AUTHORIZATION`。
- 任一 identity/capacity/readiness/review 證據缺口：`BLOCKED`，列 P0/P1 finding 與可重現證據。
- P2/P3 只列 residual，不得阻擋。

## 禁止範圍

- 禁止修改 code、config、RA004–RA007、ai-core gate／runtime 或既有 evidence。
- 禁止 push、deploy、tag、production、canary、正式產文、publication、network write、服務啟停、cleanup、archive、worktree removal。
- 禁止以 official gate 單獨 `READY` 自證；repo validator／packager 必須先通過。
- 禁止把 `READY_FOR_AUTHORIZATION` 寫成已授權或 production `GO`。

## 驗證與交付

- 執行限域測試／packager／official gate正負 probe；保存命令、exit code、固定 SHA、digest 與輸出摘要。
- 單一 evidence commit，父為 card source commit，worktree clean。
- 只回 `CHECKPOINT_B_READY_FOR_AUTHORIZATION` + evidence SHA，或 `BLOCKED` + evidence SHA／blocker。
