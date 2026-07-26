# Repair 1 verification

- status: `DELIVERED_REPAIRED_CANDIDATE`
- source_candidate_sha: `611839c3aef8bb27755595dd6220816054cbd106`
- repaired_candidate_sha: 本 evidence 所在的唯一 commit；精確 full SHA 見
  commit 後 delivery receipt。
- prepare_or_download: none
- PR/push/merge/deploy/launchd/live/acceptance: none
- real_credential_value_read: none（測試中的 value 僅為 synthetic fixtures）

## Test totals

- focused runner/outbox/coordinator: `141 passed`
- publisher + multilingual: `59 passed`
- full suite:
  `504 passed, 2 deselected, 2 warnings in 111.33s`
- exact deselections（未執行）:
  - `tests/test_api.py::test_predict_route_returns_charts_and_ai`
  - `tests/test_calculators.py::test_ziwei_returns_palace_payload`
- 4-process stress: `1 passed`; test 內斷言 300 ordinals 精確為 `1..300`，
  無 gap/duplicate，account-1/account-2/account-3 各 100。
- final affected regression after validator TOCTOU tightening: `19 passed`

## Command summary

```text
<local-only-python> -m pytest tests/test_agy_gemini_outbox.py tests/test_agy_gemini_coordinator.py -q
<local-only-python> -m pytest tests/test_agy_content_publisher.py tests/test_agy_multilingual_pipeline.py -q
<local-only-python> -m pytest -q \
  --deselect tests/test_api.py::test_predict_route_returns_charts_and_ai \
  --deselect tests/test_calculators.py::test_ziwei_returns_palace_payload
<local-only-python> -m pytest \
  tests/test_agy_gemini_outbox.py::test_production_pool_four_process_stress_has_no_ordinal_gap_or_duplicate -q
<local-only-python> -m py_compile \
  scripts/agy_gemini_allocator.py scripts/agy_gemini_runner.py scripts/agy_gemini_coordinator.py
bash -n scripts/install_agy_gemini_coordinator_launchd.sh
plutil -lint ops/launchd/com.pantheon.agy-gemini-coordinator.plist.example \
  ops/launchd/com.pantheon.agy-gemini-lane.plist.example
git diff --check
```

## Static and boundary gates

- Python compile: pass
- installer `bash -n`: pass
- coordinator/lane plist lint: pass
- `git diff --check`: pass
- changed-line secret pattern scan: pass
- `[DBG-` scan: pass
- V4 code/test/plist/docs diff relative to source candidate: empty
- `scripts/agy_gemini_outbox.py` diff relative to source candidate: empty

## Remaining risk

- 未執行 live credential、provider、launchd install/restart、deploy 或 production
  acceptance；主線保留 re-review、PR、Merge、Deploy 與 acceptance。
- State schema 新增 lock device/inode；不符合新 closed schema 的舊 state 會
  fail closed，需由主線依正式 migration/rollout 決策處理，不得在本卡清除 ledger
  或手動重送 job。
- 兩個既有 Ziwei baseline mismatch 依三次停損契約保持未處理，本輪未執行。
