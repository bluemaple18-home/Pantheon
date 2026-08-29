# TEMP_PLIST Canonical Path Repair Result

狀態：`RE_REVIEW_REQUESTED`

## 範圍與決策

- 唯一 source 變更：`scripts/install_pantheon_content_capacity_guard_launchd.sh`。
- 唯一新增測試：`tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_canonicalizes_var_tmp_plist_for_preactivation_transition`。
- `mktemp` 產生檔案後，以既有 `/usr/bin/perl -MCwd=realpath` 模式取得 canonical path；空值、非 regular file 或 symlink 一律 fail-closed，成功時才將該 canonical path 傳入 `--capacity-plist`。
- why_not_less：只改 argument path 仍可能在 canonicalization 失敗時繼續執行，故需最小的 fail-closed guard。
- why_not_more：未變更 shared `plist_receipt`、stage copy、ownership/mode 規則、runtime manifest 或任何 control plane。
- do_not_absorb：不新增 helper、環境開關、registry、FSM、authority 或 production 流程。

## RED → GREEN

- RED（修復前）：macOS `/var` alias 的 public installer preactivation seam 回傳 1，原始拒絕為 `{"preactivation_transition": "rejected", "reasons": ["plist canonical realpath or owner mismatch"], "status": "NO-GO"}`。
- GREEN（修復後）：同一測試通過；`/var/...` 與 `/private/var/...` 以 `samefile()` 證明同 inode，installer 成功完成 preactivation staging。
- temp cleanup：GREEN 測試驗證 alias temp directory 中無 `pantheon-content-capacity-guard.*` 殘留；cleanup 以 canonical path 刪除同一 inode。

## 安全契約未放寬

- owner、0600 mode、regular、non-symlink、absolute/canonical 路徑仍由未修改的 `scripts.pantheon_content_runtime_manifest.plist_receipt` 共同 validator 強制。
- 既有 shared-validator 情境覆蓋：
  - owner/mode/symlink：`tests/test_agy_gemini_coordinator.py::test_activation_only_inert_six_adoption_blocks_invalid_state_before_mutation`（`inert-owner`、`inert-mode`、`inert-symlink` variants）。
  - relative/missing/symlink alias：`tests/test_agy_gemini_coordinator.py::test_activation_only_legacy_capacity_adoption_blocks_invalid_state_before_mutation`（`relative-path`、`legacy-plist-missing`、`symlink-path`、`symlink-alias` variants）。
  - capacity candidate payload drift：`tests/test_pantheon_content_capacity_guard.py::test_preactivation_transition_rejects_capacity_candidate_plist_drift`。
- 上述 shared-validator tests 未因 allowlist 被修改；本 repair 只新增 `/var` canonical path 與 cleanup edge。canonicalization failure 的 installer branch 明確 fail-closed，無新增環境 hook 或放寬方式。

## 驗證

- `tests/test_pantheon_content_capacity_guard.py`：69/69 passed，分段 15 + 19 + 8 + 27。
- `tests/test_pantheon_content_runtime_manifest.py`：50/50 passed。
- 合計：119/119 passed。
- `bash -n scripts/install_pantheon_content_capacity_guard_launchd.sh`：passed。
- `.venv/bin/python -m py_compile scripts/pantheon_content_capacity_guard.py scripts/pantheon_content_runtime_manifest.py`：passed。
- `git diff --check`：passed。
- normal 與 `--install-recovery-stage`：既有 capacity installer regression 包含並通過；本變更未觸及 stage copy/cleanup 以外的路徑。

## 非 production 證據邊界

未執行 production/install/activate/canary 或 live service 操作。isolated harness 的 fake launchctl mutation log 為空；無 scheduler/provider/reviewer/publisher mutation。故沒有聲稱 production bytes before==after 或 live loaded services 結果。

未 commit、push、tag 或 deploy。
