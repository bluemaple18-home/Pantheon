---
id: CARD-PANTHEON-G8-RELEASE-TRANSITION-BOUNDED-IMPLEMENTATION-V1-20260821-REPAIR
chain_id: PANTHEON-G8-RELEASE-CONTROL-PLANE-V1
role: repair
cycle: 1
status: ready
type: strict_bounded_repair
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 固定 candidate 有兩個 P1 release-safety fail-open；修復範圍與負測已明確。
parent_candidate_sha: 3875b0e669e0450ea62a0b14b42b129bd08070c7
review_commit_sha: c7eca18254522554969f9be9518a329a72fdb535
blocking_findings:
  - G8-REL-REV-001
  - G8-REL-REV-002
ownership:
  - scripts/pantheon_g8_production_preactivation.py
  - tests/test_pantheon_g8_production_preactivation.py
  - tests/test_agy_gemini_coordinator.py
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-RELEASE-TRANSITION-BOUNDED-IMPLEMENTATION-V1-20260821-REPAIR-RESULT.md
forbidden_scope:
  - 修改 Capacity guard、installer、canonical evidence、implementation/Review RESULT
  - 額外重構、改 state/edge contract、放寬 fail-closed
  - production inspection/mutation、launchctl、deploy、canary、tag、push、merge
  - 建立 Reviewer、Repair、replacement thread 或下一張卡
verification:
  - .venv/bin/python -m pytest -q tests/test_pantheon_g8_production_preactivation.py tests/test_pantheon_content_capacity_guard.py tests/test_agy_gemini_coordinator.py
  - bash -n scripts/install_agy_gemini_coordinator_launchd.sh
  - git diff --check
evidence_path: artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-RELEASE-TRANSITION-BOUNDED-IMPLEMENTATION-V1-20260821-REPAIR-RESULT.md
---

# G8 Release Transition bounded Repair

## 工作名稱 → 正在做什麼 → 現在狀態

G8 Release Transition Repair → 修復兩個 P1 fail-open → READY

## 固定輸入

- parent candidate：`3875b0e669e0450ea62a0b14b42b129bd08070c7`
- Review commit：`c7eca18254522554969f9be9518a329a72fdb535`
- 完整讀 Review RESULT；只處理 `G8-REL-REV-001`、`G8-REL-REV-002`。
- CodeGraph 無有效結果時，限域固定 Git objects 與 ownership source/tests。

## Repair contract

### G8-REL-REV-001

- 把 edge authority 解析為明確 effector/action token，要求 exact equality。
- `--activate` 不得匹配 `--activate-only` 或 `--activate-publisher-only`。
- 保留既有合法 edge/action PASS；錯誤 action 必須在 mutation 前 fail closed。
- 補 prefix/subcommand collision 負測；至少覆蓋 Review RESULT 的兩個重播。

### G8-REL-REV-002

- 建 observation index 前檢查 duplicate `(service, scope)`。
- 完全一致 duplicate 可安全去重；normative field、path 或 receipt 任一衝突必須 fail closed。
- 衝突不得回 `CONVERGED`；回 `AMBIGUOUS` 或明確 invalid，並列出衝突 service/scope/evidence paths。
- 補 conflicting duplicate、identical duplicate 與 path drift 測試。

## Acceptance

- 先用 Review 最小重播/新增負測證明 RED，再修至 GREEN；RESULT 記錄 RED→GREEN。
- 兩個 finding 的 regression IDs 與測試名稱可追溯。
- focused suite、`bash -n`、`git diff --check`、allowlist、candidate commit 後 clean 全 PASS。
- 不更改 installer/Capacity/canonical evidence；不改 production。

## Stop / Delivery

- 需要擴大 source scope、改 contract、碰 production 或放寬 fail-closed：`REPAIR_BLOCKED`。
- 同 blocker 第三次失敗即停。
- ownership + 唯一 RESULT 做單一 atomic repair commit；禁止 push/merge/deploy/tag。
- final：`REPAIR_COMPLETE|REPAIR_BLOCKED`、full SHA、parent candidate、finding regression 摘要、RESULT path。
