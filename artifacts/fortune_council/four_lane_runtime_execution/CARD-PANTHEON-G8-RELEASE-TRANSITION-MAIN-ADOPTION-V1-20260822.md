---
id: CARD-PANTHEON-G8-RELEASE-TRANSITION-MAIN-ADOPTION-V1-20260822
chain_id: PANTHEON-G8-RELEASE-CONTROL-PLANE-V1
role: mainline_adoption
cycle: 1
status: ready
type: strict_bounded_mainline_adoption
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: ACCEPT_GO lineage 的固定機械採納；需產生可由主線 fast-forward 的 clean commit chain。
main_base_sha: 3848f7e03f6228039b0322efeff777aea74eb59e
accepted_candidate_sha: b2c6ac128607345ab4ec1e24d8f3cc46e6d796da
acceptance_commit_sha: c1f8eebcbcccaa7d57429289fc802b0a70795c08
ownership:
  - scripts/install_agy_gemini_coordinator_launchd.sh
  - scripts/pantheon_content_capacity_guard.py
  - scripts/pantheon_g8_production_preactivation.py
  - tests/test_agy_gemini_coordinator.py
  - tests/test_pantheon_content_capacity_guard.py
  - tests/test_pantheon_g8_production_preactivation.py
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-RELEASE-TRANSITION-BOUNDED-IMPLEMENTATION-V1-20260821-RETRY-1-RESULT.md
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-RELEASE-TRANSITION-BOUNDED-IMPLEMENTATION-V1-20260821-REPAIR-RESULT.md
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-RELEASE-TRANSITION-BOUNDED-IMPLEMENTATION-V1-20260821-REVIEW-RESULT.md
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-RELEASE-TRANSITION-INTEGRATION-V1-20260822-RESULT.md
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-RELEASE-TRANSITION-INTEGRATION-ACCEPTANCE-V1-20260822-RESULT.md
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-RELEASE-TRANSITION-MAIN-ADOPTION-V1-20260822-RESULT.md
forbidden_scope:
  - 修改 source、tests、既有 cards/RESULT 或 canonical evidence
  - production inspection/mutation、launchctl、deploy、canary、push、tag
  - 建立 Reviewer/Repair/replacement thread 或下一張卡
verification:
  - <repo-root>/.venv/bin/python -m pytest -q tests/test_pantheon_g8_production_preactivation.py tests/test_agy_gemini_coordinator.py -k "reg_g8_rel_rev or wrong_release_edge"
  - bash -n scripts/install_agy_gemini_coordinator_launchd.sh
  - git diff --check
evidence_path: artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-RELEASE-TRANSITION-MAIN-ADOPTION-V1-20260822-RESULT.md
---

# G8 Release Transition main adoption

## 工作名稱 → 正在做什麼 → 現在狀態

G8 main adoption → 將 ACCEPT_GO 固定 lineage 套到 main bootstrap，產生可 fast-forward chain → READY

## 固定輸入

- main base：`3848f7e03f6228039b0322efeff777aea74eb59e`
- accepted integration candidate：`b2c6ac128607345ab4ec1e24d8f3cc46e6d796da`
- acceptance result commit：`c1f8eebcbcccaa7d57429289fc802b0a70795c08`，verdict=`ACCEPT_GO`
- formal thread bootstrap 必須只比 `main_base_sha` 多本卡，且 clean。
- CodeGraph 無有效結果時限域固定 Git objects 與 ownership。

## Adoption contract

1. 驗證 Acceptance RESULT：`ACCEPT_GO`、accepted candidate=`b2c6ac128...`、result-only、無本機絕對路徑。
2. 依序只 cherry-pick direct commits：
   - `ccc315fae6639cde3936947cb7c75b936cbd23ab`
   - `8c57f3557212873e95257b0b025213928f13f427`
   - `39d853dd87498de727ca195e493473b429b449cc`
   - `66ef09a2d1969a30d2a83d202e426a62dd4a80c8`
   - `b2c6ac128607345ab4ec1e24d8f3cc46e6d796da`
   - `c1f8eebcbcccaa7d57429289fc802b0a70795c08`
3. 任一 conflict、empty commit、非 allowlist path：`ADOPTION_BLOCKED`；禁止人工改 source/tests 解衝突。
4. 驗證 final source/tests blobs 等同 `92ffd718...`；既有 RESULT blobs 等同固定 authority。
5. 重播 targeted regression；核對兩次 `353 passed` evidence；跑 `bash -n`、`git diff --check`、allowlist。
6. 新增唯一 Main Adoption RESULT，記錄 source→new SHA mapping、驗證與 fast-forward readiness；做 result-only commit，final clean。

## Delivery

- 全部通過：`ADOPTION_READY`；final HEAD 必須為 `main_base + 本卡 + 6 fixed patches + Adoption RESULT` 的線性後代。
- 主線只可在獨立驗證後以 `git merge --ff-only <final HEAD>` 採納；派工 thread 不得更新 main、push、deploy、tag 或碰 production。
- final 回 verdict、full SHA、mapping、tests、RESULT path。
