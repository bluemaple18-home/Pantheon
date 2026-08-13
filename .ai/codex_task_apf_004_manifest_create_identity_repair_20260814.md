# APF-004-MANIFEST-CREATE-IDENTITY-REPAIR-001

- 目標：最小補齊 `scripts.pantheon_content_runtime_manifest create` 的 hardened identity 輸入，使 exact realignment manifest 可帶入並驗證 `actor_head`、`python_executable`；`traces_to: US-004, FR-012, FR-014, SC-001, SC-003, SC-008`。
- 輸入：integration `8fea7a47a86a97e0dd1eb6af94df1ba6056e7a17`；preflight `396dd65c84`；blocked plan `6698857b9e`。唯一 source gap：create CLI 缺 `--actor-head`／`--python-executable`，但 validate/install/receipts 已依賴兩欄。
- 可改：`scripts/pantheon_content_runtime_manifest.py`、其直接 tests/fixtures、本卡與 `.ai/evidence/apf_004_manifest_create_identity_repair_001.md`。採 RED→GREEN；不得順手重構其他 runtime/installer。
- 必驗：create 明確要求／接收兩參數並傳入既有 `build_manifest()`；輸出 manifest 可由 validate 接受；錯誤 actor head、python executable、缺欄位均 fail-closed；三 installer 對同一 manifest identity 的既有 propagation tests 不退化。
- 禁止：不得 live manifest/stage/runtime/plist write、install/activate/launchctl mutation、merge/push/deploy、external model、publish/transaction/tag/schedule；不得讀寫 secrets、不得產跨機絕對路徑或 binary artifacts。
- 驗收：受影響 tests PASS、`bash -n`（若 shell touched）、DBG/secret/path/binary scan、`git diff --check`；commit allowlist；回 `REPAIR_READY_FOR_REVIEW | REPAIR_BLOCKED`，附 RED/GREEN、exact commit、`mutation_executed=false`。
