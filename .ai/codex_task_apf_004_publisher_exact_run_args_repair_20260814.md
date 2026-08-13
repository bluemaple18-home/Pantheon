# APF-004-PUBLISHER-EXACT-RUN-ARGS-REPAIR-001

## 工作

- 目標：修復 Publisher installer 在 optional exact selector 未設定時，於 macOS Bash 3.2／`set -u` 展開空 `EXACT_RUN_ARGS[@]` 而失敗。
- 狀態：REPAIR / NO_LIVE_MUTATION。
- traces_to：APF-004 Gate 1 realignment；failure evidence `apf-004-realign-retry-2-20260813T180314Z`。
- frontier：唯一 blocker 已定位為 `scripts/install_agy_content_publisher_launchd.sh` 空陣列展開。

## 可改

- `scripts/install_agy_content_publisher_launchd.sh`
- `tests/test_agy_content_publisher.py`
- 本卡與對應 sanitized evidence receipt。

## 禁止

- 不改 Writer／Publisher business logic、runtime manifest schema、其他 installer、registry/shared generated files。
- 不執行 live install/activate、launchctl mutation、publish/transaction/tag/schedule、push/deploy、external model。
- 不重跑 Gate 1；修復交付後由主線 review／整合／另行執行。

## 驗收

1. RED：在 Bash `set -u` 且 exact selector 未設定時重現同一 failure。
2. GREEN：未設定 selector 時 installer preflight/install fixture 不因空陣列失敗；設定 selector 時仍精確傳遞一次。
3. 保持 fail-closed identity／manifest／actor checks。
4. 跑直接測試、`bash -n scripts/install_agy_content_publisher_launchd.sh`、`git diff --check`。
5. 只提交 allowlist；回 `REPAIR_READY_FOR_REVIEW | REPAIR_BLOCKED`，附 commit、RED/GREEN、測試結果；`live_mutation_executed=false`。

## 交付順序

- RED → 最小修復 → GREEN → 直接回歸 → gates → commit。

## Repair Log

- CodeGraph：本 worktree 未初始化，fallback 至限域 `rg`。
- Branch：`codex/apf-004-publisher-exact-run-args-repair` from fixed source `7ae57fbd21bff0ffa887debf989424626734119d`。
- RED：`.venv/bin/python -m pytest -q tests/test_agy_content_publisher.py::test_content_publisher_installer_omits_unset_exact_run_args_under_bash32_set_u` → 2 failures；stderr reproduces `scripts/install_agy_content_publisher_launchd.sh: line 207: EXACT_RUN_ARGS[@]: unbound variable` for `--preflight` and tmp `--install` fixtures.
- Root cause：macOS Bash 3.2 with `set -u` treats an empty local array expansion as unbound in `"${EXACT_RUN_ARGS[@]}"`.
- Fix：guard the optional expansion as `${EXACT_RUN_ARGS[@]+"${EXACT_RUN_ARGS[@]}"}` so unset selector emits no argv entry; exact selector still emits `--exact-run-id <id>` once.
- GREEN：
  - `.venv/bin/python -m pytest -q tests/test_agy_content_publisher.py::test_content_publisher_installer_omits_unset_exact_run_args_under_bash32_set_u` → `2 passed`
  - `.venv/bin/python -m pytest -q tests/test_agy_content_publisher.py::test_content_publisher_installer_accepts_python_symlink_and_uses_realpath` → `1 passed`
  - `.venv/bin/python -m pytest -q tests/test_agy_content_publisher.py -k 'installer or runtime_manifest'` → `7 passed, 107 deselected`
  - `.venv/bin/python -m pytest -q tests/test_agy_content_publisher.py::test_content_publisher_installer_accepts_python_symlink_and_uses_realpath tests/test_agy_content_publisher.py::test_content_publisher_installer_omits_unset_exact_run_args_under_bash32_set_u tests/test_agy_content_publisher.py::test_content_publisher_installer_rejects_python_symlink_to_non_executable tests/test_agy_content_publisher.py::test_four_lane_recovery_publisher_rejects_new_only_before_mutation` → `5 passed`
  - `bash -n scripts/install_agy_content_publisher_launchd.sh` → pass
- Live mutation：未執行 live install/activate、launchctl mutation、Gate 1 retry、publish/transaction/tag/schedule、push/deploy/external model；`live_mutation_executed=false`。
