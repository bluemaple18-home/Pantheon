# PANTHEON ACCEPTANCE B GEN06 STALE FIXTURE REPAIR

## 任務目標

修復唯一過時 production fixture assertion：
`tests/test_agy_multilingual_pipeline.py::test_exact_production_gen05_legacy_safety_hydrates_read_only`
不得再假設合法 production `generations/06` 永遠不存在。

## 固定基線

- Repo HEAD：`5704fa6077aa4187619fddc08d9c29cad2f2dabf`
- 已知 RED：正式 publisher single execute `FAILED_RECOVERED`，506 passed、1 failed。
- 唯一 failure：最後斷言 `assert not (run_dir / "generations/06").exists()`，但 production 已合法 terminal Gen06。

## 可改範圍

- `tests/test_agy_multilingual_pipeline.py`
- 本卡片
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_stale_fixture_repair_20260829/`

## 禁止範圍

- `scripts/**`
- app/public/generated content
- production runtime root
- queue/state/manifest
- provider/coordinator/publisher
- git push/tag/deploy
- 其他測試檔或 production code

## 修復契約

此測試只驗證 Gen05 legacy hydration read-only，不應要求未來 Gen06 缺席。
最小修法是將 Gen06 presence assumption 改為 shape-neutral invariance：

1. 測試開始前 snapshot `generations/06` 是否存在。
2. 若存在，snapshot 其 regular-file relative paths 與 bytes。
3. 若不存在，記錄 absent。
4. 執行既有 Gen05 hydration 後，assert Gen06 existence/tree bytes 完全不變。

不得只刪 assertion；不得固定要求 Gen06 存在；不得放寬既有 Gen05 bytes/state、coverage/topology assertions。

## RED 假說

- H1：fixture contract 過時。若原因是測試仍要求 Gen06 缺席，改為 Gen06 tree invariance 後 exact test 應轉綠，且 production bytes 不變。
- H2：production hydration 會寫入後續 generation。若原因是被測流程實際修改 Gen06，改為 snapshot invariance 後仍會 fail，並顯示 Gen06 tree/bytes 漂移。

## 驗收命令

- RED：本機重跑 exact test，必須命中同一 assertion。
- GREEN：exact test。
- GREEN：完整 `tests/test_agy_multilingual_pipeline.py`，不得 deselect/skip。
- GREEN：相關 approved-stage selector。
- `py_compile`（若適用）。
- `git diff --check`。
- `rg '\[DBG-'`。
- production root / queue / ledger / seal / Gen07 hash before == after。
- provider/coordinator/publisher/tag/push = 0。

## 停止條件

- RED 不是同一 assertion。
- 需要修改 source code。
- production bytes 漂移。
- 完整 suite 另有失敗。
- scope 超過單一測試。
