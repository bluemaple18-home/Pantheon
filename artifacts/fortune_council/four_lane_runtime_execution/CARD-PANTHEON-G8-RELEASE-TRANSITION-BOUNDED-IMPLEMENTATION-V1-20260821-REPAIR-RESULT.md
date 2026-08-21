---
id: CARD-PANTHEON-G8-RELEASE-TRANSITION-BOUNDED-IMPLEMENTATION-V1-20260821-REPAIR-RESULT
card_id: CARD-PANTHEON-G8-RELEASE-TRANSITION-BOUNDED-IMPLEMENTATION-V1-20260821-REPAIR
chain_id: PANTHEON-G8-RELEASE-CONTROL-PLANE-V1
status: REPAIR_READY_FOR_REREVIEW
parent_candidate: 3875b0e669e0450ea62a0b14b42b129bd08070c7
review_commit: c7eca18254522554969f9be9518a329a72fdb535
date: 2026-08-22
---

# G8 Release Transition Repair RESULT

## Verdict

`REPAIR_READY_FOR_REREVIEW`

本修復只處理 `G8-REL-REV-001` 與 `G8-REL-REV-002`，未修改 Capacity guard、installer、canonical evidence、implementation RESULT 或 Review RESULT，未執行 production、launchctl、deploy、canary、tag、push 或 merge。

## Regression IDs

- `REG-G8-REL-REV-001-ACTION-PREFIX-COLLISION`
  - `tests/test_pantheon_g8_production_preactivation.py::test_reg_g8_rel_rev_001_edge_action_prefix_collision_blocks`
  - `tests/test_agy_gemini_coordinator.py::test_installer_rejects_wrong_release_edge_before_mutation`
  - 修復：`validate_effector_edge` 將 edge authority 解析為 explicit effector/action token，要求 action exact equality；`--activate` 不再匹配 `--activate-only` 或 `--activate-publisher-only`。
- `REG-G8-REL-REV-002-DUPLICATE-EVIDENCE-FAIL-CLOSED`
  - `tests/test_pantheon_g8_production_preactivation.py::test_reg_g8_rel_rev_002_conflicting_duplicate_service_scope_is_ambiguous`
  - `tests/test_pantheon_g8_production_preactivation.py::test_reg_g8_rel_rev_002_identical_duplicate_service_scope_is_deduped`
  - `tests/test_pantheon_g8_production_preactivation.py::test_reg_g8_rel_rev_002_duplicate_service_scope_path_drift_is_ambiguous`
  - 修復：release observation 在建 index 前檢查 duplicate `(service, scope)`；完全一致 duplicate 去重；normative field、path 或 receipt 欄位衝突回 `AMBIGUOUS`，列出 service、scope、fields 與 evidence paths，禁止 `CONVERGED`。

## RED Evidence

使用主 checkout 既有 Python 執行精確新增 tests：

```text
/Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest -q tests/test_pantheon_g8_production_preactivation.py tests/test_agy_gemini_coordinator.py -k "reg_g8_rel_rev or wrong_release_edge"
```

結果：`6 failed, 2 passed, 293 deselected`。

- `G8-REL-REV-001`：兩個 prefix collision case 未 raise `EDGE_EFFECTOR_MISMATCH`。
- `G8-REL-REV-002`：conflicting duplicate 與 path-drift duplicate 仍回 `code=0` / `CONVERGED`。

前置環境失敗不列為 RED：本 worktree 原本缺 `.venv/bin/python`，依監工修正改用 `/Users/mattkuo/Documents/Pantheon/.venv/bin/python` 後才記錄 assertion RED。

## GREEN Evidence

修復後重跑同一組精確 regression：

```text
/Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest -q tests/test_pantheon_g8_production_preactivation.py tests/test_agy_gemini_coordinator.py -k "reg_g8_rel_rev or wrong_release_edge"
```

結果：`8 passed, 293 deselected in 2.04s`。

## Final Verification

- focused suite：

```text
/Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest -q tests/test_pantheon_g8_production_preactivation.py tests/test_pantheon_content_capacity_guard.py tests/test_agy_gemini_coordinator.py
```

結果：`353 passed in 435.81s (0:07:15)`。

- installer syntax：`bash -n scripts/install_agy_gemini_coordinator_launchd.sh` PASS。
- whitespace：`git diff --check` PASS。
- allowlist：只修改本 Repair 卡列出的 source/tests/RESULT。
