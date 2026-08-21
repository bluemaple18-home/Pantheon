---
id: CARD-PANTHEON-G8-RELEASE-TRANSITION-BOUNDED-IMPLEMENTATION-V1-20260821-RETRY-1
chain_id: PANTHEON-G8-RELEASE-CONTROL-PLANE-V1
role: implementation
cycle: 2
status: ready
type: bounded_implementation
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: Release state/edge contract 已固定；跨 reconciler、Capacity 與 installer tests 落實核心 fail-closed contract，屬 strict/core-bounded。
supersedes: CARD-PANTHEON-G8-RELEASE-TRANSITION-BOUNDED-IMPLEMENTATION-V1-20260821
retry_reason: 原 identity 在 create 前因 task_intro 超過 50 字而 ABORTED_PRECREATE；未形成 thread、create request 或 role slot。
ownership:
  - scripts/pantheon_g8_production_preactivation.py
  - scripts/pantheon_content_capacity_guard.py
  - scripts/install_agy_gemini_coordinator_launchd.sh
  - tests/test_pantheon_g8_production_preactivation.py
  - tests/test_pantheon_content_capacity_guard.py
  - tests/test_agy_gemini_coordinator.py
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-RELEASE-TRANSITION-BOUNDED-IMPLEMENTATION-V1-20260821-RETRY-1-RESULT.md
forbidden_scope:
  - 修改 Publisher、coordinator、four lanes business/content logic 或 lineage
  - 新增 daemon、database、scheduler、通用 workflow/state-machine engine 或第二套 state authority
  - 修改 Contract v1、Edge Map v1、Cycle 29-32 replay
  - 放寬 identity、digest、generation、Capacity、Rule 24/25 fail-closed policy
  - production inspection/mutation、reset、install、activation、restage、canary、launchctl、deploy、tag、push
  - ownership 外檔案、unrelated untracked files、Reviewer/Repair/replacement thread/下一張卡
verification:
  - .venv/bin/python -m pytest -q tests/test_pantheon_g8_production_preactivation.py tests/test_pantheon_content_capacity_guard.py tests/test_agy_gemini_coordinator.py
  - git diff --check
evidence_path: artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-RELEASE-TRANSITION-BOUNDED-IMPLEMENTATION-V1-20260821-RETRY-1-RESULT.md
---

# G8 Release Transition bounded implementation v1 RETRY-1

## 工作名稱 → 正在做什麼 → 現在狀態

G8 Release Transition bounded implementation → 唯讀 reconciliation、Capacity inert/no-PID、合法 edge ordering → READY

## Root Question

不新增 mutation authority、不碰 production、不改 content plane，讓現有 G8 read-only preactivation reconciliation 遵守 Contract v1；唯一判定 state、divergence、next edge、invalidation，並使 Capacity/installer 對 inert no-PID 與 stage→reset→Capacity→activation→restage 使用同一 fail-closed 語意。

## 必讀與 authority

- 完整讀 `handoff_20260821_g8_release_transition_contract_v1.md` 與其中五份 canonical evidence。
- state/edge 唯一 authority：Release State Contract v1、Transition Edge Map v1、Cycle 29-32 Shadow Replay。
- Cycle 31 readiness 僅 historical；禁止作 current target authority。
- 先 CodeGraph task-semantic query；無結果才限域讀 ownership source/tests。

## Implementation contract

1. 延伸 `pantheon_g8_production_preactivation.py`；全程 read-only、保留 mutation tripwire，禁止另建 engine。
2. 不複製 state/edge enum truth；若解析 artifact，須 fail closed 驗 version/IDs。
3. JSON 至少輸出：`reconciliation_status`（只允許 `CONVERGED/DIVERGED/UNKNOWN/AMBIGUOUS`）、matched state、逐欄 divergences/missing、唯一 next edge、effector mapping、invalidations、`production_mutation=false`。
4. 無 explicit execution artifact 禁止 `TRANSITIONING`；多 state/current-historical 混用=`AMBIGUOUS`；缺 current evidence=`UNKNOWN`；已知 mismatch=`DIVERGED`。
5. `SVC-CORE` 展開五 labels；錯誤/receipt含 service/path/expected/actual。
6. activation-only loaded/no-PID 不綁 config version：`INERT_LOADED`、`pid_required=false`、`measurement_required=false`、`expected_process_count=0`、`resource_usage=NOT_APPLICABLE`；PID 固定 violation；真正需 RSS phase仍 fail closed。
7. 移除 `preflight_pid_gap` 成功捷徑；可信 inert no-PID 直接形成 known-zero RSS語意，不得先 unknown 再放行。
8. 唯一 ordering：stage→formal Publisher reset→Capacity preflight/install→aggregate activation-only→Publisher exact-run restage。reconciler/installer preflight只驗 next edge；錯序在 mutation 前拒絕，不自動執行 effector。
9. aggregate activation 刪 stage後，pre-activation staged evidence全 invalid；`ST-CANARY-READY` 前要求 post-activation restage/current receipts。
10. content topology固定 `new→i18n-new`、`rewrite→i18n-rewrite`。

## Acceptance

- RED→GREEN：八 states、四 statuses、五-label expansion、per-service mismatch、missing/stale/ambiguous、禁止 `TRANSITIONING`。
- Capacity：config-v3 AO loaded/no-PID→known inert zero；PID→violation；需 RSS 但缺 telemetry→NO-GO；無 `preflight_pid_gap`。
- Ordering：Cycle 32 mixed cohort next edge只能 reset；跳 Capacity mutation 前拒絕；activation invalidation後必須 restage。
- Cycle 29–32 committed evidence shadow replay；production-shaped dry reconciliation只用 fixture/temp roots。
- focused suite、`git diff --check`、allowlist diff、candidate commit後 clean 全 PASS。

## Stop / Delivery

- scope expansion、第二套 authority、production/launchctl需求、放寬 fail-closed → `SCOPE_VIOLATION / ARCHITECTURE_CONTRADICTION`。
- 同 blocker 第三次失敗即停；dry gates PASS後仍停，等待 production canary另行授權。
- ownership + 唯一 RESULT 做單一 atomic candidate commit；禁止 push/merge/deploy/tag。
- final：`IMPLEMENTATION_COMPLETE|IMPLEMENTATION_BLOCKED`、full SHA、驗證摘要、RESULT path。
