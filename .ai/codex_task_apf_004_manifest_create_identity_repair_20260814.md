# APF-004-MANIFEST-CREATE-IDENTITY-REPAIR-001

- 目標：最小補齊 `scripts.pantheon_content_runtime_manifest create` 的 hardened identity 輸入，使 exact realignment manifest 可帶入並驗證 `actor_head`、`python_executable`；`traces_to: US-004, FR-012, FR-014, SC-001, SC-003, SC-008`。
- 輸入：integration `8fea7a47a86a97e0dd1eb6af94df1ba6056e7a17`；preflight `396dd65c84`；blocked plan `6698857b9e`。唯一 source gap：create CLI 缺 `--actor-head`／`--python-executable`，但 validate/install/receipts 已依賴兩欄。
- 可改：`scripts/pantheon_content_runtime_manifest.py`、其直接 tests/fixtures、本卡與 `.ai/evidence/apf_004_manifest_create_identity_repair_001.md`。採 RED→GREEN；不得順手重構其他 runtime/installer。
- 必驗：create 明確要求／接收兩參數並傳入既有 `build_manifest()`；輸出 manifest 可由 validate 接受；錯誤 actor head、python executable、缺欄位均 fail-closed；三 installer 對同一 manifest identity 的既有 propagation tests 不退化。
- 禁止：不得 live manifest/stage/runtime/plist write、install/activate/launchctl mutation、merge/push/deploy、external model、publish/transaction/tag/schedule；不得讀寫 secrets、不得產跨機絕對路徑或 binary artifacts。
- 驗收：受影響 tests PASS、`bash -n`（若 shell touched）、DBG/secret/path/binary scan、`git diff --check`；commit allowlist；回 `REPAIR_READY_FOR_REVIEW | REPAIR_BLOCKED`，附 RED/GREEN、exact commit、`mutation_executed=false`。

## Repair Log

- CodeGraph：本 worktree 未初始化，fallback 至限域 `rg`。
- RED：`.venv/bin/python -m pytest -q tests/test_pantheon_content_runtime_manifest.py::test_manifest_create_cli_requires_and_validates_hardened_identity` 失敗；缺 `--actor-head`／`--python-executable` 時 `create` 仍 returncode `0`。
- Root cause：`build_manifest()` 已支援 `actor_head`／`python_executable`，但 `create` parser/main 未要求也未傳入兩欄。
- Fix：`create` 子命令新增 required `--actor-head` 與 `--python-executable`，並直接傳入既有 `build_manifest()`；未改 installer 或其他 runtime flow。
- GREEN：
  - `.venv/bin/python -m pytest -q tests/test_pantheon_content_runtime_manifest.py::test_manifest_create_cli_requires_and_validates_hardened_identity` → `1 passed`
  - `.venv/bin/python -m pytest -q tests/test_pantheon_content_runtime_manifest.py::test_manifest_create_cli_hardened_identity_negative_matrix_fails_closed` → `3 passed`
  - `.venv/bin/python -m pytest -q tests/test_pantheon_content_runtime_manifest.py` → `39 passed`
  - `.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py -k 'installer or aggregate_activation or four_lane_activation'` → `28 passed, 113 deselected`
  - `.venv/bin/python -m pytest -q tests/test_agy_content_publisher.py -k 'installer or runtime_manifest'` → `5 passed, 107 deselected`
  - `.venv/bin/python -m pytest -q tests/test_pantheon_content_capacity_guard.py -k 'installer or runtime'` → `4 passed, 12 deselected`
- Live mutation：未執行 install、activate、launchctl、manifest/stage/runtime/plist write、merge/push/deploy、external model、publish/transaction/tag/schedule；`mutation_executed=false`。
