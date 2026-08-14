---
id: APF-004-RAW-CAPACITY-RECEIPT-PLAN-REPLAY
title: 補 raw capacity receipt 並重跑 aggregate plan
status: ready
chain_id: PANTHEON-WRITER-VNEXT-AUTO-PUBLISHING-FIRST
role: implementation
cycle: 1
thickness: strict
risk: critical
model: gpt-5.5
reasoning: high
model_reason: public CLI 與 blocker 已固定；本卡只補 bounded synthetic receipt 並重播 read-only plan
parent_candidate: 28f9d9d8c18dfb6d0918cb14e20956045c4abbe6
traces_to:
  - FR-AGG-PROMOTE-PLAN-001
  - SC-CAPACITY-RAW-RECEIPT-001
  - SC-AGG-PROMOTE-PLAN-REPLAY-001
---

# APF-004｜raw capacity receipt＋aggregate plan replay

## 任務五行卡

- 目標：用正式 capacity guard `exercise` 產生 aggregate CLI 可驗的 raw stop-loss receipt，接著唯讀重跑 aggregate `plan` 兩次。
- 可寫：`artifacts/fortune_council/content_writer_vnext_execution/apf_004_canary/aggregate_runtime_promotion_plan_replay_raw_capacity_20260815/**`；一次性 exercise root 只准位於 `/private/tmp`。
- 禁止：不得 `apply/rollback/finalize`；不得寫 production actor/manifest/plist/stage/queue/state/log；不得 launchctl、deploy/install/copy、create-run、外部模型、select/publish/transaction/tag/push/schedule；不得改 code/config/tests。
- 驗收：輸出 `PLAN_READY | BLOCKED`；raw receipt contract PASS、兩次 plan deterministic、plan digest 唯一、production roots/transaction root 零變化、production mutation=0。
- 交付：單一 evidence candidate commit，不 amend、不 push；回 SHA、verdict、capacity receipt digest、plan digest、mutation summary。

## 固定 authority

1. runtime source authority 固定 `0bf78f0b0cac6743fef4dae4aa76e21ebbaffe35`，使用既有 clean detached source worktree；`origin/main` 必須為其 descendant，且 `git diff 0bf78f0b0c..origin/main -- scripts tests` 為空。
2. capacity receipt 只能由 public CLI `python -m scripts.pantheon_content_capacity_guard --exercise-root ... --receipt ... --cycle-bytes 4096 exercise` 產生；不得手填 cycles/telemetry/stop-loss。
3. exercise root 必須在 `/private/tmp`、執行前不存在、上限 2 cycles × 4096 bytes；禁止指向 production、repo、user home 或共享 artifact root。
4. public aggregate CLI 固定 `python -m scripts.pantheon_content_runtime_promotion plan`；不得用 internal function 代替。
5. actor target source 仍是 `0bf78f0b0cac6743fef4dae4aa76e21ebbaffe35`；current actor/manifest/stage/target/correlation/authorization 等欄位全部由執行當下實際 artifacts 重算。

## Receipt 契約

1. raw temp receipt 必須為 `schema_version=1`、`regression_id=REG-PANTHEON-CAPACITY-WRITE-CYCLES-001`、`status=PASS`、`mode=bounded-synthetic-dry-run`、`production_mutation=false`。
2. 必須有至少兩個 cycles，且每個 `rss_available=true`、`swap_available=true`；reclamation `bytes_after < bytes_before`。
3. stop-loss 必須 `status=STOPPED`、`triggered=true`、`remaining_loaded=[]`、`cross_project_deletions=[]`。
4. 先保存 raw receipt SHA-256；再只正規化 `exercise_root` 與 reclamation allowlist 的本機 path 成 `<exercise-root>`，建立可攜 canonical receipt並計算新 digest。不得改任何 telemetry、status、cycle、reclamation 或 stop-loss 值。
5. canonical receipt 必須通過 aggregate CLI 的 public plan 驗證；artifact 內不得有 `/opt`、`/private/tmp`、`/Users`、使用者名稱或 `file://`。

## Plan replay 與證據

1. exercise 前後保存 temp root bytes/files、host free/RSS/swap；證明 bounded write/reclamation，production mutation=0。
2. plan 前保存 actor/manifest/private stage/queue/state/run/gsc-copy/worker/transaction root snapshot。
3. 用 canonical receipt與其實際 SHA-256執行兩次完全相同的 public `plan`；不得第三次。
4. `PLAN_READY` 必須兩次 returncode=0、`status=PLAN`、stdout/plan digest/ordered stages/write set/backup set/rollback order/postchecks 完全一致。
5. plan 後重算所有 production roots；transaction root 必須仍不存在或 byte-for-byte unchanged。
6. 任一 telemetry unavailable、receipt NO-GO、plan NO-GO/non-deterministic、或 production drift，立即 `BLOCKED`；不得修 production。
7. artifacts 保存 raw stdout/stderr hash、sanitized body、pre/post snapshots、receipt、verification、artifact digests；跨機只用 placeholder。

## 下一閘門

- 本卡不授權 production promotion。
- `PLAN_READY` 經獨立 Reviewer 核准並整合後，才可請求使用者一次明確 Gate A `apply` 授權。
- Gate B single plan-only 與任何發文仍不在範圍。
