# V0387 fresh Rule24 bundle CLI verification

- `python3 scripts/pantheon_writer_vnext_runtime_activation_capacity.py bundle --help`：PASS；顯示 `--task-root`、`--evidence-root` 與 `--capacity-sandbox-root`。
- public `bundle` smoke：PASS；實際呼叫既有 `run_capacity_proof_evidence_bundle`，產生兩週期 unsigned exact-byte bundle，exit `0`。
- root allow-boundary：task root 必須是 existing canonical `/private/tmp` strict descendant；evidence/sandbox 必須是 task root 的互不重疊 strict descendants。
- production/outside-root、symlink escape、missing input、invalid/unbounded policy：入口 fail closed，exit `2`，且測試確認不呼叫 bundle API。
- smoke summary：`signed=false`、`production_mutation=false`、`canary_created=false`，artifacts 為 capacity receipt 與兩個 cycle measurements。
- `<repo-root>/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pantheon_writer_vnext_runtime_activation_capacity.py`：PASS，`25 passed`。
- `<repo-root>/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pantheon_content_runtime_promotion.py`：PASS，`27 passed`。
- `<repo-root>/.venv/bin/python -m py_compile scripts/pantheon_writer_vnext_runtime_activation_capacity.py tests/test_pantheon_writer_vnext_runtime_activation_capacity.py`：PASS
- JSON parse：PASS。
- `git diff --check`：PASS

此 receipt 未執行 production runtime、remote、LaunchAgents、promotion、DSSE signing、push 或 tag。
