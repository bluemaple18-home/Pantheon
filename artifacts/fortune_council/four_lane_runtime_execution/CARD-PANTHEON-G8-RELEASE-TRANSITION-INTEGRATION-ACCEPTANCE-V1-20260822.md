---
id: CARD-PANTHEON-G8-RELEASE-TRANSITION-INTEGRATION-ACCEPTANCE-V1-20260822
chain_id: PANTHEON-G8-RELEASE-CONTROL-PLANE-V1
role: acceptance
cycle: 1
status: ready
type: strict_evidence_first_acceptance
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 固定 integration candidate 的最終採納前證據閘門；不改 implementation。
base_sha: 813ec58a785cd74d91956abf9bc7ef62384cf36d
candidate_sha: b2c6ac128607345ab4ec1e24d8f3cc46e6d796da
reviewed_source_sha: 92ffd718b3b771e25dadeaf24cb2ba0c7ca65e50
review_authority_sha: 3d53455d16a05c6a3b8dd1558b6b4582035f3858
ownership:
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-RELEASE-TRANSITION-INTEGRATION-ACCEPTANCE-V1-20260822-RESULT.md
forbidden_scope:
  - 修改 implementation、tests、既有 cards/RESULT 或 canonical evidence
  - production inspection/mutation、launchctl、deploy、canary、push、tag、merge、更新 main
  - 建立 Reviewer/Repair/replacement thread 或下一張卡
verification:
  - <repo-root>/.venv/bin/python -m pytest -q tests/test_pantheon_g8_production_preactivation.py tests/test_agy_gemini_coordinator.py -k "reg_g8_rel_rev or wrong_release_edge"
  - bash -n scripts/install_agy_gemini_coordinator_launchd.sh
  - git diff --check 813ec58a785cd74d91956abf9bc7ef62384cf36d..b2c6ac128607345ab4ec1e24d8f3cc46e6d796da
evidence_path: artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-RELEASE-TRANSITION-INTEGRATION-ACCEPTANCE-V1-20260822-RESULT.md
---

# G8 Release Transition integration final acceptance

## 工作名稱 → 正在做什麼 → 現在狀態

G8 Integration final acceptance → 唯讀驗證固定 candidate 是否可交 mainline 採納 → READY

## 固定輸入

- base：`813ec58a785cd74d91956abf9bc7ef62384cf36d`
- integration candidate：`b2c6ac128607345ab4ec1e24d8f3cc46e6d796da`
- source authority：`92ffd718b3b771e25dadeaf24cb2ba0c7ca65e50`
- targeted re-review：`3d53455d16a05c6a3b8dd1558b6b4582035f3858`，verdict=`REVIEW_GO`
- 完整讀 Integration RESULT、Review RESULT 與本卡。CodeGraph 無有效結果時限域固定 Git objects。

## Acceptance contract

1. 驗證 candidate lineage 精確包含四個既定 cherry-pick mapping 與唯一 Integration RESULT；無 conflict/empty/額外 commit。
2. 驗證 `base..candidate` path surface 只含 integration ownership；canonical evidence、registry、metadata、generated page、sitemap/feed/redirect、task cards 不得修改。
3. 驗證 source/tests blobs 等同 `92ffd718...`；三份既有 RESULT 分別等同固定 authority；Integration RESULT 內容與實際 Git tree/commands 一致。
4. 重播 targeted regression；核對 focused suite `353 passed` 證據；執行 `bash -n` 與 `git diff --check`。
5. 只新增唯一 Acceptance RESULT 並做 result-only commit。不得修檔或更新 main。

## Verdict / delivery

- 證據全部一致：`ACCEPT_GO`。
- 任一 lineage、blob、allowlist、測試或證據不一致：`ACCEPT_NO_GO`；只報 finding，不修。
- 同 blocker 第三次失敗即停。
- final 附 verdict、full commit SHA、accepted candidate、驗證摘要與 RESULT path；worktree 必須 clean。
