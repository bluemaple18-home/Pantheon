# RESULT: Pantheon Acceptance B Gen06 Stale Fixture Repair

status: `READY_FOR_REVIEW`

## Scope

- Repo HEAD baseline：`5704fa6077aa4187619fddc08d9c29cad2f2dabf`
- 修改檔案：`tests/test_agy_multilingual_pipeline.py`
- 新增卡片：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-ACCEPTANCE-B-GEN06-STALE-FIXTURE-REPAIR-20260829.md`
- Evidence dir：`artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_stale_fixture_repair_20260829/`
- 禁止範圍遵守：未修改 `scripts/**`、production code、production runtime root、queue/state/manifest、provider/coordinator/publisher。
- Commit / push / tag / deploy：`0`

## RED Evidence

既有 publisher failure evidence：

- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_final_publish_acceptance_20260829/publisher-execute-failure-excerpt.txt`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_final_publish_acceptance_20260829/publisher-failed-recovered-summary.json`

本機 RED command：

```bash
.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py::test_exact_production_gen05_legacy_safety_hydrates_read_only --tb=short
```

Return code：`1`

Failure excerpt：

```text
FAILED tests/test_agy_multilingual_pipeline.py::test_exact_production_gen05_legacy_safety_hydrates_read_only
tests/test_agy_multilingual_pipeline.py:2040
assert not (run_dir / "generations/06").exists()
E   AssertionError: assert not True
```

這是合格 RED：同一 nodeid、同一 assertion、不是 import/environment failure。

## Hypothesis Decision

- H1：fixture contract 過時。若測試仍要求 Gen06 缺席，改為 Gen06 tree invariance 後 exact test 應轉綠，且 production bytes 不變。
- H2：被測 Gen05 hydration 實際寫入或改動 Gen06。若如此，改為 snapshot invariance 後仍會 fail，並暴露 Gen06 tree/bytes drift。

裁決：`fault_layer = test_fixture_contract`。修後 exact test 轉綠，production immutability compare 無差異，H1 成立、H2 被否定。

## Repair

最小修改：

- 在 `test_exact_production_gen05_legacy_safety_hydrates_read_only` 內新增 `gen06_file_snapshot()`。
- 測試開始前記錄 `generations/06` 是否 absent；若存在，記錄 regular-file relative paths 與 bytes。
- 將舊 assertion `generations/06` absent 改為 hydration 後 `gen06_file_snapshot() == before_gen06`。
- 既有 Gen05 legacy bytes/state、coverage、topology assertions 保持不變。

Diff stat：`tests/test_agy_multilingual_pipeline.py` = `14 insertions, 1 deletion`。

## GREEN Evidence

```bash
.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py::test_exact_production_gen05_legacy_safety_hydrates_read_only --tb=short
```

Return code：`0`；result：`1 passed in 0.14s`

```bash
.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py --tb=short
```

Return code：`0`；result：`262 passed in 0.80s`

```bash
.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py -k approved_edited_stage --tb=short
```

Return code：`0`；result：`20 passed, 242 deselected in 0.28s`

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m py_compile tests/test_agy_multilingual_pipeline.py
```

Return code：`0`

```bash
git diff --check
```

Return code：`0`

```bash
rg '\[DBG-' scripts tests
```

Return code：`1`；result：no matches in source/test scope。

## Production Immutability

Snapshots：

- before：`before-fix-production-snapshot.json`
- after：`after-verification-production-snapshot.json`
- comparison：`production-immutability-compare.json`

Comparison status：`PASS`

Compared keys：

- actor head/status
- runtime manifest SHA
- queue root tree SHA
- target run dir tree SHA
- Gen06 existence/tree/files
- Gen07 existence/tree
- ledger SHA
- approved-edit seal/current SHA
- queue state SHA
- provider/coordinator/publisher/tag-push counts

Differences：none。

Mutation counts:

- provider calls：`0`
- coordinator calls：`0`
- publisher calls：`0`
- tag pushes：`0`
- production writes observed：`0`

## Final Decision

`READY_FOR_REVIEW`

本 repair 僅更新過時 fixture assertion，將 Gen06 absence policy 改為 shape-neutral read-only invariance。所有要求的 RED/GREEN、同檔完整測試、approved-stage selector、syntax/diff/debug-marker checks 與 production immutability evidence 均已完成。
