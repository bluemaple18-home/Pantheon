# APF-004-GATE2-ACTIVATION-ONLY-REPAIR-001

## 正式狀態

- 工作名稱：APF-004-GATE2-ACTIVATION-ONLY-REPAIR-001
- 正在做什麼：修復 Gate 2 無法只啟動、會直接執行內容 I/O 的正式入口缺口
- 現在狀態：REPAIR_READY_FOR_REVIEW
- Base / production candidate：de13ef0de5d122cbe66831ede20b4a62cc6e37a1
- mutation_executed：false

## 契約邊界

- 沿用既有唯一 Repair task，不建立新 Repair。
- 新增 repo-owned activation-only public mode。
- activation-only 必須完成七服務 identity acknowledgement、loaded/post-check 與 rollback 證據。
- activation-only 下 coordinator/lane/publisher/provider/queue/state/business child I/O counters 必須為 0。
- activation-only authority 不得成為正式 child I/O token；正常 production mode 契約不得削弱。
- legacy prior-loaded service 無 valid barrier 時，需在首次 live mutation 前拒絕，且不可隱藏 rollback failure。
- live actor/manifest realignment 維持獨立正式 stage/install 與 exact receipt，不得在 activate 偷偷 checkout/覆寫。

## 可改檔案

- scripts/pantheon_content_runtime_manifest.py
- scripts/install_agy_gemini_coordinator_launchd.sh
- tests/test_agy_gemini_coordinator.py
- tests/test_pantheon_content_runtime_manifest.py
- .ai/codex_task_apf_004_gate2_activation_only_repair_20260814.md
- .ai/evidence/apf_004_gate2_activation_only_repair_001.md

## 禁止範圍

- live install / activate / launchctl mutation
- live manifest / plist / runtime write
- push / merge / deploy
- external model
- create / run / select / publish / transaction / tag / schedule

## Source decision

- CodeGraph 查詢結果：repo 未初始化 CodeGraph，回報需先 `codegraph init`。
- 依契約 fallback：限域 `rg` 檢查 runtime manifest helper、coordinator installer、直接 tests。

## RED

1. `tests/test_agy_gemini_coordinator.py::test_gate2_activation_only_bootstraps_barrier_without_child_io`
   - RED 現象：`--activate-only` 不是公開 action，installer usage exit 2。
2. `tests/test_agy_gemini_coordinator.py::test_activation_rejects_legacy_loaded_without_valid_barrier_before_live_replacement`
   - RED 現象：legacy prior-loaded service 缺 valid barrier 時，fixture live plist 已先被替換。

## 修復摘要

- `barrier-exec` 新增 `--activation-only`。
- activation-only 在 barrier 與 python identity 驗證後寫 readiness ack 並回 JSON PASS，不 exec child command。
- plist identity receipt 允許 `--activation-only` 位於 barrier-exec 與 child `--` separator 之間，且仍驗證 child python identity。
- coordinator installer 新增 `--activate-only` public mode。
- `--activate-only` replacement 階段只對 target plist 注入 barrier-exec `--activation-only`，不傳遞給 child command。
- legacy prior-loaded service 缺 previous valid barrier 時，在 replace live plist 前 fail-closed 並產 failure receipt。
- normal `--activate` 訊息與 child execution path 保持不變。

## GREEN / Gates

- `tests/test_agy_gemini_coordinator.py::test_gate2_activation_only_bootstraps_barrier_without_child_io`：PASS
- `tests/test_agy_gemini_coordinator.py::test_activation_rejects_legacy_loaded_without_valid_barrier_before_live_replacement`：PASS
- `tests/test_pantheon_content_runtime_manifest.py::test_barrier_exec_activation_only_acknowledges_without_child_exec`：PASS
- affected coordinator suite：30 passed, 113 deselected
- normal-mode regression：3 passed
- runtime manifest suite：40 passed
- bash-n：PASS
- DBG / secret / path / binary / diff gates：見 `.ai/evidence/apf_004_gate2_activation_only_repair_001.md`

## 剩餘 live migration step

本修復未執行 live mutation。後續需在 review / integration 後，另走獨立正式 realignment stage/install gate，再由人工單獨確認 Gate 2 activation-only。realignment 與 activation-only 仍是兩個獨立 confirmation gates。
