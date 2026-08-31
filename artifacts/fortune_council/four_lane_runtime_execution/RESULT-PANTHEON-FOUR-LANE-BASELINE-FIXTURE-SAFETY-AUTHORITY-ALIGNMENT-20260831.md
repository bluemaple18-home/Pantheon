---
id: RESULT-PANTHEON-FOUR-LANE-BASELINE-FIXTURE-SAFETY-AUTHORITY-ALIGNMENT
card: PANTHEON-FOUR-LANE-BASELINE-FIXTURE-SAFETY-AUTHORITY-ALIGNMENT
status: BASELINE_GREEN
runtime_actor_sha: 0f61545f8c6b561742b27792b8fef11ae8b1ccc5
acceptance_harness_sha: WORKTREE_UNCOMMITTED
provider_calls: 0
production_mutation: 0
---

# Slice 2A 結果收據

## 修改範圍

本 Slice allowlist 僅包含：

- 本派工卡：`CARD-PANTHEON-FOUR-LANE-BASELINE-FIXTURE-SAFETY-AUTHORITY-ALIGNMENT-20260831.md`
- `tests/test_agy_gemini_coordinator.py`
- 本 result receipt

Fixture 現在從傳入 schema 讀取 `coverage_mapping.items` contract，assert `additionalProperties=false`、`safety_boundary` 不在 `properties`／`required`，並從 supplied schema 的 identity enum 取得唯一 identity values；assert 型別、長度與唯一性後，依 deterministic fact 順序 zip 產生 mappings。輸出欄位僅為 identity、`planned_h2_slot`、`coverage_note`。未修改 production source、hydration、legacy contract、scripts 或 runtime-owned artifacts。

## RED before fix

原始三個 exact targeted tests 在修改前均失敗，錯誤為：

`ValueError: external locale plan coverage fields are strict for article-01`

重現命令：

```text
.venv/bin/pytest -q tests/test_agy_gemini_coordinator.py -k 'campaign_translation_runs_new_and_rewrite_through_real_vertical_chain or private_campaign_e2e_composes_four_lanes_without_publishing or private_campaign_e2e_resumes_seeded_partial_state_without_repeating_completed_work'
```

結果：`3 failed, 451 deselected`。

## Targeted verification after fix

同一命令結果：`3 passed, 451 deselected in 0.58s`。

Safety matrix：

```text
.venv/bin/pytest -q -p no:cacheprovider tests/test_agy_multilingual_pipeline.py -k 'safety or source_ref_map or planning_result'
```

結果：`15 passed, 288 deselected in 0.12s`。

## Fresh-process exact baseline

以下 38-case baseline 是依卡片規定的 exact node selectors，由主線 fresh process 執行；不是下列 broad `-k` diagnostic selector：

```text
tests/test_agy_gemini_coordinator.py::test_campaign_translation_runs_new_and_rewrite_through_real_vertical_chain
tests/test_agy_gemini_coordinator.py::test_private_campaign_e2e_composes_four_lanes_without_publishing
tests/test_agy_gemini_coordinator.py::test_private_campaign_e2e_rejects_capacity_and_rolls_back_translation_failure
tests/test_agy_gemini_coordinator.py::test_private_campaign_e2e_resumes_seeded_partial_state_without_repeating_completed_work
tests/test_agy_gemini_coordinator.py::test_apf_004_create_run_adapter_plan_only_is_deterministic_and_zero_write
tests/test_agy_gemini_coordinator.py::test_apf_004_create_run_adapter_apply_is_idempotent_and_resume_safe
tests/test_agy_gemini_coordinator.py::test_apf_004_create_run_adapter_negative_matrix_fails_before_write[missing_lane-exactly four lanes]
tests/test_agy_gemini_coordinator.py::test_apf_004_create_run_adapter_negative_matrix_fails_before_write[duplicate_lane-lane is duplicated]
tests/test_agy_gemini_coordinator.py::test_apf_004_create_run_adapter_negative_matrix_fails_before_write[fifth_lane-exactly four lanes]
tests/test_agy_gemini_coordinator.py::test_apf_004_create_run_adapter_negative_matrix_fails_before_write[work_id-work identity differs]
tests/test_agy_gemini_coordinator.py::test_apf_004_create_run_adapter_negative_matrix_fails_before_write[campaign_version-campaign version drift]
tests/test_agy_gemini_coordinator.py::test_apf_004_create_run_adapter_negative_matrix_fails_before_write[source_pairing-translation source pairing]
tests/test_agy_gemini_coordinator.py::test_apf_004_create_run_adapter_negative_matrix_fails_before_write[caller_run_id-caller-supplied run identity]
tests/test_agy_gemini_coordinator.py::test_apf_004_create_run_adapter_negative_matrix_fails_before_write[runtime_digest-runtime identity digest]
tests/test_agy_gemini_coordinator.py::test_apf_004_create_run_adapter_negative_matrix_fails_before_write[max_runs-max_runs=1]
tests/test_agy_gemini_coordinator.py::test_register_and_exact_activation_persist_immutable_identity_envelope
tests/test_pantheon_runtime_activation.py::test_activation_token_requires_complete_seven_service_acknowledgements
tests/test_pantheon_runtime_activation.py::test_activation_token_allows_seven_matching_services_before_io
tests/test_pantheon_runtime_activation.py::test_stale_activation_token_fails_before_queue_state_io
tests/test_pantheon_writer_vnext_runtime_activation_e2e.py::test_runtime_activation_e2e_links_official_boundaries_and_writes_artifacts
tests/test_pantheon_writer_vnext_runtime_activation_e2e.py::test_runtime_activation_e2e_saves_fail_closed_matrix_and_blocked_receipt
tests/test_pantheon_writer_vnext_runtime_activation_e2e.py::test_runtime_activation_e2e_rejects_untrusted_or_overlapping_roots
tests/test_pantheon_writer_vnext_runtime_activation_e2e.py::test_runtime_activation_e2e_stops_when_publisher_boundary_blocks
tests/test_agy_content_publisher.py::test_collect_ready_runs_exact_selector_excludes_unlisted_ready_run
tests/test_agy_content_publisher.py::test_collect_ready_translation_runs_does_not_bypass_ledger_lifecycle[deferred]
tests/test_agy_content_publisher.py::test_collect_ready_translation_runs_does_not_bypass_ledger_lifecycle[published]
tests/test_agy_content_publisher.py::test_approved_stage_publisher_dry_run_has_zero_runtime_mutation
tests/test_agy_multilingual_pipeline.py::test_ja_continuation_schema_uses_request_local_refs_not_fact_ids
tests/test_agy_multilingual_pipeline.py::test_ja_continuation_current_ref_response_hydrates_to_current_ids
tests/test_agy_multilingual_pipeline.py::test_ja_continuation_fresh_response_rejects_provider_safety
tests/test_agy_multilingual_pipeline.py::test_ja_legacy_provider_safety_read_requires_receipt
tests/test_agy_multilingual_pipeline.py::test_ja_legacy_provider_safety_read_rejects_schema_receipt_drift
tests/test_agy_multilingual_pipeline.py::test_ja_legacy_provider_safety_read_ignores_only_safety_assertion
tests/test_agy_multilingual_pipeline.py::test_ja_legacy_provider_safety_read_ref_drift_fails_closed[unknown]
tests/test_agy_multilingual_pipeline.py::test_ja_legacy_provider_safety_read_ref_drift_fails_closed[missing]
tests/test_agy_multilingual_pipeline.py::test_ja_legacy_provider_safety_read_ref_drift_fails_closed[duplicate]
tests/test_agy_multilingual_pipeline.py::test_exact_production_gen05_legacy_safety_hydrates_read_only
tests/test_agy_multilingual_pipeline.py::test_locale_plan_rejects_fresh_provider_safety_assertion
```

上述 38 IDs 是 collect-only frozen manifest；正式 execution 使用同一組 selectors。

主線 fresh-process 執行結果：

```text
38 passed in 91.00s
0 failed/skip/xfail
```

上述結果僅支持 `BASELINE_GREEN`；umbrella activation/shadow 仍未授權。

## Integrity gates

- `provider_calls=0`：fixture-only tests，未配置 provider transport。
- `production_mutation=0`：所有測試使用 temporary roots；未執行 production／activation／shadow。
- `scripts/**` diff：0。
- `runtime_actor_sha`：`0f61545f8c6b561742b27792b8fef11ae8b1ccc5`。
- `acceptance_harness_sha`：`WORKTREE_UNCOMMITTED`。
- `git diff --check`：通過。
- allowlist：本派工卡、`tests/test_agy_gemini_coordinator.py`、本 RESULT；scripts diff=0。
- independent review：`RE_REVIEW_GO`；原 Reviewer 已確認 38 IDs inline、`38 passed in 91.00s`、allowlist、scripts diff=0 與 `git diff --check`，且無新 P0/P1。

## Stop / handoff

Slice 2A 已閉合為 `BASELINE_GREEN`。未進行 commit、push、deploy、activation、shadow、network 或 external write；umbrella production activation/shadow 仍未授權，不得宣告 `GO_FOUR_LANE_RUNTIME_CURRENT`。下一 frontier 只能是 fresh Authority Snapshot／Gate C offline negative preparation。
