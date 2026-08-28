---
schema_version: 1
title: Pantheon Acceptance B gen05 production entrypoint INVALID_RECEIPT repair result
date: 2026-08-28
status: RE_REVIEW_REQUESTED
mode: BOUNDED_REPAIR
target_run: auto-i18n-ja-1414b75a404721e95e74
source_job_id: 61a83c341d39c882d5eed8ea23b7f805a89085e3
base_commit: 23eab63ea31031094aa084faee0e5ff65d326533
production_mutation: false
provider_calls: 0
push: false
commit: false
---

# 結論

本輪 bounded Repair 已完成至 `RE_REVIEW_REQUESTED`，未觸碰 production、未呼叫 provider、未 push、未 promotion、未 deploy、未 commit。Reviewer 前次 verdict 為 NO-GO，本結果不自稱 GO，需交原 Reviewer re-review。

修復內容：

- `scripts/agy_gemini_runner.py`
  - 新增 formal production Gemini lane transport guard。
  - 當正式 service label 缺 `AGY_GEMINI_CREDENTIAL_POOL_FILE`、`AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE`、model route digest、writer/reviewer model 等必要 env 時，在 claim queue 前回 `blocked`。
  - 新增薄的 `operator-exact-process-once` / `operator_exact_process_once`，由 current manifest + barrier + plist `EnvironmentVariables` 組合正式 exact one-shot runner command。
  - 明確忽略 plist `ProgramArguments`，避免 stale ProgramArguments 變成 operator entrypoint。
  - operator result 不回傳原始 stdout/stderr；只回 bytes/digest/empty receipt。
  - operator env receipt 不輸出任何 env 原值；檔案類 env 只記 presence/absolute/size/sha256，非檔案 env 只記 presence/sha256。
  - child JSON stdout 只保留安全摘要欄位，不帶 credential/env 原值。

- `scripts/agy_gemini_coordinator.py`
  - 沿用既有 `replace_failed_external_job` seam。
  - 極窄支援 `provider-attempt=0`、`ValueError`、`INVALID_RECEIPT`、無 `error_code`、無 `credential_pool`、且 state 為 legacy null correlation 的 residue。
  - 持久 receipt / decision 的 `correlation_id` 保持原 durable identity：legacy null 就寫 `null`；operator synthetic token 只作為非持久 authority result，不污染 state identity。
  - 若存在 production-attempt marker，或不是 legacy null correlation，或不是 no-error-code INVALID_RECEIPT，仍 fail-closed。

# RED 證據

命令：

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_agy_gemini_runner.py::test_formal_production_lane_missing_transport_env_blocks_before_claim tests/test_agy_gemini_runner.py::test_operator_exact_process_uses_current_manifest_and_plist_env_without_stale_program tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_plan_only_accepts_provider_zero_invalid_receipt_legacy_null_correlation tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_rejects_invalid_receipt_when_provider_attempt_exists -q`

結果：

- 4 failed。
- 舊 runner 會進入 `generate_json`，被測試以 `provider must not run` 攔下，證明缺 transport env 時未在 claim/provider 前 fail-closed。
- 舊 runner 沒有 `operator_exact_process_once` 正式 one-shot operator 入口。
- 舊 coordinator 對 legacy null correlation 直接報 `failed external replacement state identity mismatch`，無法 plan-only recovery。

# GREEN 證據

命令：

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_agy_gemini_runner.py::test_formal_production_lane_missing_transport_env_blocks_before_claim tests/test_agy_gemini_runner.py::test_operator_exact_process_uses_current_manifest_and_plist_env_without_stale_program tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_plan_only_accepts_provider_zero_invalid_receipt_legacy_null_correlation tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_legacy_null_correlation_result_recovers_without_actor_run_dir tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_rejects_invalid_receipt_when_provider_attempt_exists -q`

結果：

- 5 passed。
- 包含主線提醒後新增的 end-to-end recovery regression：legacy null correlation replacement execute 後，刪除 actor run dir，`cycle_once(... exact_run_ids=...)` 能從 replacement inbox 完成 run；state 與 replacement receipt 的 `correlation_id` 均維持 `null`。

命令：

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_agy_gemini_runner.py tests/test_agy_gemini_coordinator.py -k 'failed_external_job_replacement' -q`

結果：

- 28 passed, 306 deselected。

命令：

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_agy_gemini_runner.py -q`

結果：

- 5 passed。

命令：

`.venv/bin/python -m py_compile scripts/agy_gemini_runner.py scripts/agy_gemini_coordinator.py tests/test_agy_gemini_runner.py tests/test_agy_gemini_coordinator.py`

結果：

- PASS，無輸出。

命令：

`git diff --check`

結果：

- PASS，無輸出。

# coordinator 全檔分類

命令：

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -q`

結果：

- 320 passed。
- 8 failed。
- 8 個 failure 均為既有 LocalePlanValidationError：`external locale plan coverage fields are strict for article-01`。
- 分類：`PRE_EXISTING_NON_SCOPE`。前序 baseline 已將這 8 個 exact nodeids 分類為 parent 8a 與 current Repair tree 同型失敗；本輪 allowlist 禁止修改 `scripts/agy_multilingual_pipeline.py` 與 locale plan scope，因此未修。

# Mutation accounting

- source files changed: 2
  - `scripts/agy_gemini_runner.py`
  - `scripts/agy_gemini_coordinator.py`
- test files changed: 2
  - `tests/test_agy_gemini_runner.py`
  - `tests/test_agy_gemini_coordinator.py`
- artifact files changed: 2
  - `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-ACCEPTANCE-B-GEN05-PRODUCTION-ENTRYPOINT-INVALID-RECEIPT-REPAIR-20260828.md`
  - `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_production_entrypoint_invalid_receipt_repair_20260828/RESULT-PANTHEON-ACCEPTANCE-B-GEN05-PRODUCTION-ENTRYPOINT-INVALID-RECEIPT-REPAIR-20260828.md`
- production queue/state/archive/failed/registry changed: no
- provider calls: 0
- push/promotion/deploy/publish/tag: no

# 風險

- `operator-exact-process-once` 是新 CLI entrypoint，仍需獨立 re-review 確認正式 operator 指令排列與現場 LaunchAgent plist path 選擇。
- recovery seam 只解 `provider-attempt=0 INVALID_RECEIPT + legacy null correlation + no error_code`。若現場 failed receipt 帶有不同 failure shape，應 NO-GO 並重新 RCA，不應在 production 手改 queue。
- coordinator 全檔仍有 locale plan 8 fail，已分類為本輪外既有問題；不得在本 repair 吸收。

# 建議 commit message

`fix: guard formal gemini operator transport`

# Reviewer NO-GO response 2026-08-28

Reviewer finding:

- P1：`operator-exact-process-once` 記錄 child/barrier `returncode`，但外層 CLI 仍可能 exit `0`，會讓 runbook / automation 把 failed exact recovery 誤判為成功。
- P2：stdout 多行時，`child_result_summary` 可能消失；需安全解析最後 JSON line 或明確 parse status，仍不可回 raw stdout/stderr。

本輪 follow-up 修復：

- P1 fixed：`main()` 在 `operator-exact-process-once` result `status == "executed"` 且 `returncode != 0` 時，外層 CLI 回傳該 nonzero code；若 code 不在 shell 1..255 範圍則回 `1`。
- P2 minimal fixed：`operator_exact_process_once` 只掃 stdout 最後一個 non-empty JSON object line，寫入 `child_result_summary_parse`；只保留 allowlist child summary fields，不回 raw stdout/stderr。
- Secret hygiene preserved：env receipt 無原值；stdout/stderr 僅 bytes/sha256/empty；child summary 不含 `secret` 或任意非 allowlist 欄位。

RED command:

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_agy_gemini_runner.py::test_operator_exact_process_cli_propagates_child_nonzero_without_raw_streams tests/test_agy_gemini_runner.py::test_operator_exact_process_summarizes_last_json_line_without_raw_output -q`

RED result:

- 2 failed。
- `test_operator_exact_process_cli_propagates_child_nonzero_without_raw_streams`：舊外層 CLI 回 `0`，expected `42`。
- `test_operator_exact_process_summarizes_last_json_line_without_raw_output`：舊 result 缺 `child_result_summary_parse`。

GREEN commands:

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_agy_gemini_runner.py::test_operator_exact_process_cli_propagates_child_nonzero_without_raw_streams tests/test_agy_gemini_runner.py::test_operator_exact_process_summarizes_last_json_line_without_raw_output -q`

Result: `2 passed`。

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_agy_gemini_runner.py::test_formal_production_lane_missing_transport_env_blocks_before_claim tests/test_agy_gemini_runner.py::test_operator_exact_process_uses_current_manifest_and_plist_env_without_stale_program tests/test_agy_gemini_runner.py::test_operator_exact_process_cli_propagates_child_nonzero_without_raw_streams tests/test_agy_gemini_runner.py::test_operator_exact_process_summarizes_last_json_line_without_raw_output tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_plan_only_accepts_provider_zero_invalid_receipt_legacy_null_correlation tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_legacy_null_correlation_result_recovers_without_actor_run_dir tests/test_agy_gemini_coordinator.py::test_failed_external_job_replacement_rejects_invalid_receipt_when_provider_attempt_exists -q`

Result: `7 passed`。

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_agy_gemini_runner.py -q`

Result: `7 passed`。

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_agy_gemini_runner.py tests/test_agy_gemini_coordinator.py -k 'failed_external_job_replacement' -q`

Result: `28 passed, 308 deselected`。

`.venv/bin/python -m py_compile scripts/agy_gemini_runner.py scripts/agy_gemini_coordinator.py tests/test_agy_gemini_runner.py tests/test_agy_gemini_coordinator.py`

Result: PASS，無輸出。

`git diff --check`

Result: PASS，無輸出。
