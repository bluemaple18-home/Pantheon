---
id: PANTHEON-C-C-T-OWNER-RECEIPT-PROVENANCE-REPAIR-2-RESULT
status: REPAIR_2_READY_FOR_REVIEW
repair_generation: 2
production_mutation: 0
runtime_mutation: 0
provider_calls: 0
public_publish: 0
gate_d_e: NOT_RUN
commit_push: NOT_RUN_BY_THIS_WORKER
---

# C-C/T owner receipt provenance Repair-2 result

## Verdict

`REPAIR_2_READY_FOR_REVIEW`

本 worker 已完成 Repair-2 implementation 與本地驗證；此狀態不是 `C-C_T_REVIEW_GO`。下一步仍須回同一 Reviewer conversation 做 targeted re-review。

本地獨立 read-only targeted re-review：`GO`；未發現 P0／P1／P2／P3 findings。此結果只代表 candidate 已可送外部 Reviewer，不取代外部 sequential review gate。

## Scope

已修改 allowlist 內檔案：

- `scripts/pantheon_four_lane_disposable_acceptance_cohort.py`
- `tests/test_pantheon_four_lane_disposable_acceptance_cohort.py`
- `artifacts/fortune_council/disposable_acceptance_cohort/CARD-PANTHEON-C-C-T-OWNER-RECEIPT-PROVENANCE-REPAIR-2-20260901.md`
- `artifacts/fortune_council/disposable_acceptance_cohort/REPAIR-2-RESULT.md`
- `artifacts/fortune_council/disposable_acceptance_cohort/repair-2-raw-test-output.txt`

未修改 owner modules：Coordinator、Runner、Publisher、C-B、multilingual、broker。

## Findings addressed

- `CCT-P1-WORKLOAD-OWNER-RECEIPT-PROVENANCE`
  - formal `run_once()` 移除 caller-supplied owner receipt callbacks。
  - controller 固定組 Coordinator、Runner、C-B materializer、bundle close、Publisher dry-run invocation。
  - process-style owner stdout 由 controller 包成 receipt 後，再走既有 strict owner schema validators。
  - Runner delivery 以 sealed bundle authority 加上 owner read-back ledger／anchor 驗證。
  - C-B materialization receipt 必須能從 pending receipt terminal state read back。
  - Publisher 由 private adapter 固定呼叫既有 lane-specific owner function，強制 dry-run／no-push／max-runs=1／single exact selector。
  - deterministic positive flow 執行真正 `publish_ready_*` owner functions；測試只替換更底層的 runtime、git、selector與 release-plan seam。
  - Coordinator terminal stdout 後，controller 依 exact run ids 重讀 canonical run state，並記錄 state path／digest；stdout 與 state 任一不一致即 fail closed。

- `CCT-P1-LAUNCHCTL-FINGERPRINT-RECEIPT-PROVENANCE`
  - formal path 不接受 launch／bootout／print／production fingerprint callback injection。
  - controller 固定組 `/bin/launchctl print/bootstrap/kickstart/bootout` argv。
  - 測試只 monkeypatch private raw process transport；未執行真實 launchctl。
  - bootstrap 成功後若 loaded/kickstart validation 失敗，會嘗試 bootout，並在 failure path 仍要求 final print-not-found closeout。
  - production runtime manifest identity 從固定 `~/Library/LaunchAgents` 七份 plist 推導，不接受 caller env path。
  - 七份 plist 由既有 runtime validator 驗證並綁定同一 manifest；article registry identity/count/digest 由 manifest actor root 下實際檔案重算，不接受 self-reported JSON digest。

## RED evidence

新增並先實際執行的 RED：

```text
.venv/bin/python -m pytest -q tests/test_pantheon_four_lane_disposable_acceptance_cohort.py::test_formal_run_once_rejects_caller_supplied_owner_receipts_without_readback

F                                                                        [100%]
FAILED tests/test_pantheon_four_lane_disposable_acceptance_cohort.py::test_formal_run_once_rejects_caller_supplied_owner_receipts_without_readback
E       Failed: DID NOT RAISE <class 'scripts.pantheon_four_lane_disposable_acceptance_cohort.AcceptanceBlocked'>
1 failed in 0.08s
```

該 RED 命中 provenance 症狀：舊 formal `run_once()` 可接受 caller-supplied forged owner receipt callbacks。

## GREEN evidence

```text
.venv/bin/python -m pytest -p no:cacheprovider -q tests/test_pantheon_four_lane_disposable_acceptance_cohort.py
...........................                                              [100%]
27 passed in 11.70s
```

```text
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_cycle_external_workers_only_requires_exact_selector_before_io tests/test_agy_gemini_coordinator.py::test_cycle_external_workers_only_rejects_automatic_sweep_before_io tests/test_agy_gemini_coordinator.py::test_cycle_external_workers_only_advances_exact_pending_without_process tests/test_agy_gemini_coordinator.py::test_materializer_cli_requires_exact_external_pins tests/test_agy_gemini_coordinator.py::test_materializer_external_pin_mismatch_rejects_before_translation_write
...............                                                          [100%]
15 passed in 32.37s
```

```text
.venv/bin/python -m py_compile scripts/pantheon_four_lane_disposable_acceptance_cohort.py scripts/agy_gemini_coordinator.py tests/test_pantheon_four_lane_disposable_acceptance_cohort.py tests/test_agy_gemini_coordinator.py
PASS
```

```text
git diff --check
PASS
```

## Boundary evidence

- 真實 `/bin/launchctl bootstrap`／`kickstart`／`bootout`：NOT_RUN。
- provider：NOT_RUN。
- production/public mutation：NOT_RUN。
- Gate D/E：NOT_RUN。
- commit/push：NOT_RUN_BY_THIS_WORKER。
- formal public callback injection：source seam removed; remaining callback names only exist in a negative TypeError regression fixture.

## Residual risk

- External review evidence P2 production fingerprint expansion remains explicitly deferred to Gate D/E scope and was not absorbed into Repair-2.
- 本輪只驗證固定唯讀 production state reader 的暫存 fixture；未在 host production 上執行 reader，未執行任何 launchctl mutation。
