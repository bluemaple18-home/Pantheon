# Fresh verification

## Finding-specific

```text
.venv/bin/pytest -q \
  tests/test_agy_gemini_outbox.py::test_production_pool_commit_failure_precedes_credential_and_provider \
  tests/test_agy_gemini_coordinator.py::test_installer_injects_one_shared_allocator_contract_into_coordinator_and_all_lanes \
  tests/test_agy_gemini_coordinator.py::test_installer_pool_opt_out_preserves_compatibility_without_pool_requirements \
  tests/test_agy_gemini_coordinator.py::test_launchd_template_runs_coordinator_and_installer_is_valid_shell
```

結果：`5 passed`。

修復前 red-capable probe：

- commit-failure regression 觀察 `credential_opens=1`
- coordinator installed plist 缺 pool/state/cooldown
- coordinator template 與 opt-out installed plist 缺 cooldown

修復後 commit-failure probe：

- credential open/read：0
- state ordinal durable：false
- provider construction/call：0
- `failed/` 恰好一個 closed terminal failure
- production attempt 恰好一個且 status=`failed`
- raw exception、credential path/value 未進入 terminal artifacts

## Focused

```text
.venv/bin/pytest -q \
  tests/test_agy_gemini_allocator.py \
  tests/test_agy_gemini_outbox.py \
  tests/test_agy_gemini_coordinator.py
```

結果：`171 passed in 17.39s`。

## 64 denied multiprocess 與 300 allocation stress

```text
.venv/bin/pytest -q \
  tests/test_agy_gemini_outbox.py::test_cooling_admission_64_process_competition_has_zero_side_effects \
  tests/test_agy_gemini_outbox.py::test_production_pool_four_process_stress_has_no_ordinal_gap_or_duplicate
```

結果：`2 passed in 0.30s`。

## Publisher、SEO lifecycle、V4

```text
.venv/bin/pytest -q \
  tests/test_agy_content_publisher.py \
  tests/test_agy_seo_copy_pipeline.py \
  tests/test_agy_gemini_v4_broker.py \
  tests/test_agy_gemini_v4_architecture_probe.py
```

結果：`181 passed in 93.32s`。

## Multilingual baseline

Candidate 與 required parent 都執行：

```text
.venv/bin/pytest -q tests/test_agy_multilingual_pipeline.py
```

兩者結果相同：`16 passed, 2 failed`。失敗皆為：

- `test_apply_approved_translation_writes_run_module_and_manifest`
- `test_apply_translation_fails_closed_when_source_changed`

共同 failure code：`missing_policy_contract`。

判定：`PRE_EXISTING_BASELINE`；本 Repair 未新增 Multilingual 失敗。

## Static

- production Python `py_compile`：PASS
- installer `bash -n`：PASS
- coordinator plist `plutil -lint`：PASS
- lane plist `plutil -lint`：PASS
- `git diff --check`：PASS

## 禁止操作

未執行真實 Gemini/HTTP、真 credential、production queue/state、LaunchAgent、
installer control-plane mutation、deploy、canary、Publisher、publish、push、PR
或 merge。
