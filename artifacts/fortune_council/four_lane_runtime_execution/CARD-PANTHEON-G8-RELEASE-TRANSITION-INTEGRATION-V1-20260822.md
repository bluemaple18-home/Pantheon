---
id: CARD-PANTHEON-G8-RELEASE-TRANSITION-INTEGRATION-V1-20260822
chain_id: PANTHEON-G8-RELEASE-CONTROL-PLANE-V1
role: integration
cycle: 1
status: ready
type: strict_bounded_mainline_integration
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 固定 REVIEW_GO candidate 的主線整合；commit lineage、allowlist 與 release-safety 驗收已鎖定。
mainline_base_sha: 520fecb7b1a1adb62a1b472dbb994215a51b567f
implementation_commit_sha: 3875b0e669e0450ea62a0b14b42b129bd08070c7
repair_commit_sha: 92ffd718b3b771e25dadeaf24cb2ba0c7ca65e50
initial_review_commit_sha: c7eca18254522554969f9be9518a329a72fdb535
rereview_commit_sha: 3d53455d16a05c6a3b8dd1558b6b4582035f3858
review_verdict: REVIEW_GO
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
forbidden_scope:
  - 修改 source、tests、canonical evidence、既有 task card 或既有 RESULT 內容
  - production inspection/mutation、launchctl、deploy、canary、tag、push
  - merge 非固定 lineage、建立 Reviewer/Repair/replacement thread 或下一張卡
verification:
  - .venv/bin/python -m pytest -q tests/test_pantheon_g8_production_preactivation.py tests/test_pantheon_content_capacity_guard.py tests/test_agy_gemini_coordinator.py
  - bash -n scripts/install_agy_gemini_coordinator_launchd.sh
  - git diff --check
evidence_path: artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-RELEASE-TRANSITION-INTEGRATION-V1-20260822-RESULT.md
---

# G8 Release Transition 主線整合與驗收

## 工作名稱 → 正在做什麼 → 現在狀態

G8 Release Transition 主線整合 → 將固定 `REVIEW_GO` lineage 整合至 mainline worktree → READY

## 固定輸入與順序

- mainline base：`520fecb7b1a1adb62a1b472dbb994215a51b567f`；本卡 bootstrap commit 只新增本卡。
- implementation：`3875b0e669e0450ea62a0b14b42b129bd08070c7`。
- repair：`92ffd718b3b771e25dadeaf24cb2ba0c7ca65e50`。
- initial Review RESULT：`c7eca18254522554969f9be9518a329a72fdb535`。
- targeted re-review：`3d53455d16a05c6a3b8dd1558b6b4582035f3858`，verdict=`REVIEW_GO`，reviewed_commit=`92ffd718b3b771e25dadeaf24cb2ba0c7ca65e50`。
- 先 CodeGraph task-semantic query；無有效結果才限域固定 Git objects、ownership 與 canonical evidence。

## Integration contract

1. 驗證本 worktree 起點只比 `mainline_base_sha` 多本卡，且無其他 tracked diff。
2. 驗證四個 fixed commits 存在；re-review RESULT 的 verdict、reviewed commit 與兩個 P1 closure 精確吻合。
3. 依序只 cherry-pick direct commits：`3875b0e...` → `92ffd718...` → `c7eca182...` → `3d53455d...`。禁止 cherry-pick Repair bootstrap `8b9f728...`，因主線已有同一 Repair 卡。
4. 若 conflict、空 commit、非 allowlist path、既有卡/RESULT 被非預期改寫，立即停止；禁止人工改 source/tests 解 conflict。
5. 新增唯一 Integration RESULT，記錄：起點、實際 cherry-pick mapping/new SHAs、tree/allowlist、Review authority、測試與 clean status。
6. commit Integration RESULT；最終 worktree 必須 clean。不得 push、merge 至其他 branch、deploy、tag 或碰 production。

## Acceptance

- `git diff --name-status <bootstrap>..HEAD` 僅含 ownership；不含 canonical evidence、registry、metadata、generated page、sitemap、feed、redirect 或既有 task card 修改。
- source/tests 的 final blob 必須分別等同 repair candidate `92ffd718...`；implementation/Repair/Review RESULT final blob 等同各自固定 authority commit。
- focused suite 全 PASS；`bash -n` PASS；`git diff --check <bootstrap>..HEAD` PASS。
- targeted regression 至少覆蓋 `reg_g8_rel_rev` / `wrong_release_edge` 並 PASS。
- 不觸碰原有未追蹤檔案；final 回 `INTEGRATION_COMPLETE` 或 `INTEGRATION_BLOCKED`，附 full SHA、驗證摘要與 RESULT path。

## Stop

- fixed object 不可讀、Review authority 不一致、需擴 scope、需改 source/tests 或任何 production 權限：`INTEGRATION_BLOCKED`。
- 同一 blocker 第三次失敗即停；不得另開下一張卡或自行派工。
