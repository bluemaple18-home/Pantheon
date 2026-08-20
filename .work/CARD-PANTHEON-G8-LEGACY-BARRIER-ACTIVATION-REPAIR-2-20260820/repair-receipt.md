# CARD-PANTHEON-G8-LEGACY-BARRIER-ACTIVATION-REPAIR-2-20260820 Repair Receipt

## 範圍

- ownership: `scripts/install_agy_gemini_coordinator_launchd.sh`
- ownership: `tests/test_agy_gemini_coordinator.py`
- ownership: `.work/CARD-PANTHEON-G8-LEGACY-BARRIER-ACTIVATION-REPAIR-2-20260820/**`
- production mutation: 0
- push/tag/publish: 未執行

## RED

- `test_activate_only_accepts_coherent_old_live_with_promoted_manifest_path` 先在未修 installer seam 時失敗。
- failure phase: `previous_barrier_validation`
- failure stderr: `legacy prior-loaded service 缺少 valid activation barrier，拒絕 activation。`
- RCA reproduced: old live plist 保留 old digest 與 old barrier，但 manifest path 指向已 promoted 的 shared current manifest。
- reviewer retry 的 `test_activate_only_promoted_manifest_rejects_duplicate_outer_expected_digest_before_mutation` 先精確重現第二組 drifted `--expected-digest` 繞過：candidate exit `0`，未在 mutation 前 fail-closed。

## GREEN

- installer 新增 activation-only 專用 seam: 從 snapshot 後的 live plist、launchctl identity、old barrier payload 重建 previous runtime manifest。
- seam 不讀 promoted shared manifest 內容作為 old authority。
- seam 僅在完整七服務 old live tuple coherent、全部 loaded、無 PID/running、barrier identity/digest/generation matching 時採用。
- normal activation 與 invalid transition 仍 fail-closed before live replacement。
- legacy seam 只解析唯一 child separator 前的 outer argv；`--barrier`、`--expected-digest`、`--manifest`、`--service-label` 與 `--activation-only` 均須 exact once。
- duplicate same/drifted value、missing value、odd outer token、multiple separator，以及 child argv 重複 authority control 均在 live replacement、launchctl mutation 與 child I/O 前拒絕。

## Verification

- `bash -n scripts/install_agy_gemini_coordinator_launchd.sh`: PASS
- `pytest tests/test_agy_gemini_coordinator.py::test_activate_only_accepts_coherent_old_live_with_promoted_manifest_path tests/test_agy_gemini_coordinator.py::test_activate_only_promoted_manifest_legacy_barrier_blocks_invalid_transition_before_mutation -q`: 10 passed
- `pytest tests/test_agy_gemini_coordinator.py::test_activate_only_promoted_manifest_rejects_malformed_outer_authority_before_mutation -q`: 20 passed
- promoted manifest exact suite: 30 passed
- `pytest tests/test_agy_gemini_coordinator.py -k "legacy_capacity or inert_six or legacy_barrier or promoted_manifest or activation_only_adopts or normal_activate_rejects" -q`: 43 passed, 175 deselected
- `pytest tests/test_agy_gemini_coordinator.py -q`: 238 passed
- `pytest tests/test_pantheon_content_runtime_manifest.py tests/test_pantheon_content_capacity_guard.py tests/test_pantheon_writer_vnext_runtime_activation_capacity.py -q`: 102 passed
- `git diff --check`: PASS

## Residual Risk

- 唯一 residual risk: seam 仍依賴 launchctl `print` 中 canonical `path = /...` identity 輸出格式；argv authority 已由 exact-once outer parser 保護，path duplication、relative、symlink、running/PID 與 drift 也有負例。
