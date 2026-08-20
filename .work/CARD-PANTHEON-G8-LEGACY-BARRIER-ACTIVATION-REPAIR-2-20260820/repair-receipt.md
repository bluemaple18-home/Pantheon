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

## GREEN

- installer 新增 activation-only 專用 seam: 從 snapshot 後的 live plist、launchctl identity、old barrier payload 重建 previous runtime manifest。
- seam 不讀 promoted shared manifest 內容作為 old authority。
- seam 僅在完整七服務 old live tuple coherent、全部 loaded、無 PID/running、barrier identity/digest/generation matching 時採用。
- normal activation 與 invalid transition 仍 fail-closed before live replacement。

## Verification

- `bash -n scripts/install_agy_gemini_coordinator_launchd.sh`: PASS
- `pytest tests/test_agy_gemini_coordinator.py::test_activate_only_accepts_coherent_old_live_with_promoted_manifest_path tests/test_agy_gemini_coordinator.py::test_activate_only_promoted_manifest_legacy_barrier_blocks_invalid_transition_before_mutation -q`: 10 passed
- `pytest tests/test_agy_gemini_coordinator.py -k "legacy_capacity or inert_six or legacy_barrier or promoted_manifest or activation_only_adopts or normal_activate_rejects" -q`: 43 passed, 175 deselected
- `pytest tests/test_agy_gemini_coordinator.py -q`: 218 passed
- `pytest tests/test_pantheon_content_runtime_manifest.py tests/test_pantheon_content_capacity_guard.py tests/test_pantheon_writer_vnext_runtime_activation_capacity.py -q`: 102 passed
- `git diff --check`: PASS

## Residual Risk

- 唯一 residual risk: seam 依賴 launchctl `print` 中 canonical `path = /...` identity 輸出格式；已有 path duplication、relative、symlink、running/PID 與 drift 負例保護。
