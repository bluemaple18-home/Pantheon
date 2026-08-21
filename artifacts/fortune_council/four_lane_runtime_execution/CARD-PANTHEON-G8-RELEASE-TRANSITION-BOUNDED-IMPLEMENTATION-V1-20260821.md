---
id: CARD-PANTHEON-G8-RELEASE-TRANSITION-BOUNDED-IMPLEMENTATION-V1-20260821
chain_id: PANTHEON-G8-RELEASE-CONTROL-PLANE-V1
role: implementation
cycle: 2
status: ready
type: bounded_implementation
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: Release state/edge contract 已固定；需跨 reconciler、Capacity 與 installer tests 落實核心 fail-closed contract，屬 strict/core-bounded。
ownership:
  - scripts/pantheon_g8_production_preactivation.py
  - scripts/pantheon_content_capacity_guard.py
  - scripts/install_agy_gemini_coordinator_launchd.sh
  - tests/test_pantheon_g8_production_preactivation.py
  - tests/test_pantheon_content_capacity_guard.py
  - tests/test_agy_gemini_coordinator.py
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-RELEASE-TRANSITION-BOUNDED-IMPLEMENTATION-V1-20260821-RESULT.md
forbidden_scope:
  - 修改 Publisher、coordinator、four lanes 的 business/content logic 或 lineage
  - 新增 daemon、database、scheduler、通用 workflow/state-machine engine 或第二套 state authority
  - 修改 canonical Contract v1、Transition Edge Map v1、Cycle 29-32 replay
  - 放寬 identity、digest、generation、Capacity、Rule 24 或 Rule 25 fail-closed policy
  - production inspection、reset、install、activation、restage、canary、launchctl/live plist mutation、deploy、tag、push
  - 修改 registry、共用 metadata、生成頁、sitemap、feed、redirects 或 unrelated untracked files
  - 建立 Reviewer、Repair、replacement thread 或下一張卡
verification:
  - .venv/bin/python -m pytest -q tests/test_pantheon_g8_production_preactivation.py tests/test_pantheon_content_capacity_guard.py tests/test_agy_gemini_coordinator.py
  - git diff --check
evidence_path: artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-RELEASE-TRANSITION-BOUNDED-IMPLEMENTATION-V1-20260821-RESULT.md
---

# G8 Release Transition bounded implementation v1

## 工作名稱 → 正在做什麼 → 現在狀態

G8 Release Transition bounded implementation v1 → 落實 read-only reconciliation、Capacity inert/no-PID 與合法 edge ordering → READY

## Root Question

能否在不新增 mutation authority、不碰 production、不改 content plane 的前提下，讓現有 G8 read-only preactivation reconciliation 直接遵守 Contract v1，對 current live/target evidence 唯一判定 state、divergence、next legal edge 與 invalidation，並讓 Capacity 與 installer seam 對 activation-only loaded/no-PID 及 stage→reset→Capacity→activation→restage 使用同一 fail-closed 語意？

## Source 與必讀 evidence

- provisioning source：包含本卡的 exact commit；執行前以 `git rev-parse HEAD` 與 `git cat-file` 驗證。
- handoff：`handoff_20260821_g8_release_transition_contract_v1.md`。
- canonical evidence：
  1. `PANTHEON-G8-RELEASE-STATE-CONTRACT-V1-20260821.md`
  2. `PANTHEON-G8-TRANSITION-EDGE-MAP-V1-20260821.md`
  3. `PANTHEON-G8-CYCLE-29-32-SHADOW-REPLAY-20260821.md`
  4. `CARD-PANTHEON-G8-PRECANARY-REMAINING-GATES-DIAGNOSTIC-20260821-RESULT.md`
  5. `CARD-PANTHEON-G8-RELEASE-TRANSITION-CONTRACT-V1-20260821.md`
- Cycle 31 readiness 只能作 historical evidence，禁止作 current target authority。
- 先執行 CodeGraph task-semantic context；無結果才限域讀 ownership source/tests。

## Implementation contract

1. 延伸現有 `pantheon_g8_production_preactivation.py`，不得另建 daemon/engine；reconciler 全程 read-only，保留 mutation tripwire。
2. Canonical state/edge vocabulary 以三份 Contract v1 artifact 為 authority；不得手寫另一份獨立 enum truth。若需 parser/adapter，必須在現有 ownership 檔內 bounded 實作並 fail closed 驗證 contract version/IDs。
3. JSON output 至少穩定提供：`reconciliation_status`（只允許 `CONVERGED/DIVERGED/UNKNOWN/AMBIGUOUS`）、matched state、逐欄 divergences/missing evidence、唯一 next legal edge、effectors mapping、evidence invalidations、`production_mutation=false`。
4. 沒有 explicit transition execution artifact 時禁止輸出或推論 `TRANSITIONING`；多 state match 或 current/historical 混用固定 `AMBIGUOUS`；缺 current evidence 固定 `UNKNOWN`；已知 mismatch 固定 `DIVERGED`。
5. `SVC-CORE` 必須展開五 label 比對；任一 mismatch 不得被 aggregate 掩蓋。錯誤/receipt 要含 service、path、expected、actual，避免只回泛化 activation-mode mismatch。
6. Capacity activation-only loaded/no-PID 必須 config-version-independent 映射為 `INERT_LOADED`：`pid_required=false`、`measurement_required=false`、`expected_process_count=0`、`resource_usage=NOT_APPLICABLE`；PID 出現固定 violation。真正需 RSS phase 仍 fail closed。
7. 移除 `preflight_pid_gap` 下游例外作為成功捷徑；raw Capacity receipt 必須直接對可信 inert no-PID topology 產生已知零 RSS/可驗證語意，不得先 `rss_telemetry_unknown` 再放行。
8. ordering 只能為 `stage → formal Publisher reset → Capacity preflight/install → aggregate activation-only → Publisher exact-run restage`。不得自動執行 effectors；reconciler/installer preflight 只輸出或驗證合法 next edge，錯序在任何 mutation 前 fail closed。
9. aggregate activation 刪除 private stage後，所有 pre-activation staged evidence（含 Publisher exact-run/max-runs/exact-run-id）必須列為 invalidated；進 `ST-CANARY-READY` 前要求 post-activation restage/current receipts。
10. 保留 content topology：`new → i18n-new`、`rewrite → i18n-rewrite`。不得改 Publisher/coordinator/four-lane business logic。

## Tests 與 shadow acceptance

- RED→GREEN focused tests覆蓋：八 state matching、四 reconciliation statuses、五-label expansion、per-service mismatch、缺/舊 evidence、ambiguous match、禁止 `TRANSITIONING`。
- Capacity tests覆蓋：config-v3 activation-only loaded/no-PID → known inert zero；PID → violation；真正需 RSS telemetry missing → NO-GO；不得再靠 `preflight_pid_gap`。
- installer/order tests覆蓋：Cycle 32 mixed cohort只能 next `TE-TARGET-STAGED-TO-QUIESCED`；跳到 Capacity在 mutation 前拒絕；activation invalidation後必須 restage。
- Cycle 29–32 committed evidence shadow replay：至少重現 Cycle 29 legal inert window、Cycle 32 Publisher mode mismatch與 activation stage invalidation預測。
- production-shaped dry reconciliation只能使用 fixture/temp roots；不得讀或改 host production roots。
- 完整 focused suite、`git diff --check`、allowlist diff、worktree clean（candidate commit後）全部 PASS。

## Stop conditions

- 需要新增 daemon/database/scheduler/general engine、第二套 authority、改 content plane、放寬 fail-closed、修改 ownership 外檔案 → `SCOPE_VIOLATION / ARCHITECTURE_CONTRADICTION`，停止。
- 任一測試需要 production root、launchctl mutation、正式 reset/install/activation/canary → 停止。
- 同一 blocker 第三次失敗 → 停止，不做第四次。
- production canary 未授權；所有 dry gates PASS 後仍須停止並回主線。

## Delivery

- ownership source/tests + 唯一 RESULT 組成單一 atomic candidate commit；禁止 push/merge/deploy/tag。
- RESULT 記錄：candidate SHA、files changed、RED/GREEN、focused suite、Cycle 29–32 replay、dry reconciliation gate matrix、mutation tripwire、residual risks。
- final 只回 `IMPLEMENTATION_COMPLETE` 或 `IMPLEMENTATION_BLOCKED`、完整 candidate SHA、驗證摘要、RESULT path。
