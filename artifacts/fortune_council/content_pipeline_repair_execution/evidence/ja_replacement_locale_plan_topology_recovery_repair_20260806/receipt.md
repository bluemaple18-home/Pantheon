# JA replacement locale-plan topology recovery evidence

## Root cause

第三代 rebuild 已由 pipeline 正確判定為 `rebuild_outline=true`，且 hydration 仍維持 deterministic authority；bounded replacement lineage 也依序進入 generation 1、2、3。失敗點在 prompt 只提供 hydrated prior plan：前代 coverage 使用 H2 文字，模型必須自行反推 `planned_h2_slot`，因此可能只替換 H2 文案而重用相同 fact-to-H2 topology，最後被 deterministic validator 以 `LocalePlanValidationError` 拒絕。

修復只在 locale-plan prompt seam 加入機器可讀的前代 fact-to-H2 slot mapping 與 forbidden topology signature，不修改 validator、不自動搬移 fact、不放寬 Reviewer，也不改 replacement lineage。

## RED / GREEN

- RED：`test_replacement_third_generation_gets_explicit_prior_topology_contract` 在 prompt 缺少 `rebuild topology constraints` 時，第三代同症狀路徑失敗。
- GREEN：同一測試通過；fixture 以 `-replacement-01` run identity 經過兩代相同 `MIRRORED_STRUCTURE` finding，第三代讀取明確 contract 後改變 topology。

## Verification

- `tests/test_agy_multilingual_pipeline.py`：177 passed。
- topology/rebuild targeted regression：9 passed。
- `tests/test_agy_gemini_coordinator.py -k exact_run_ids`：4 passed，76 deselected。
- Python compile check：passed。
- `git diff --check`：passed。
- `[DBG-...]` instrumentation：none。

## Scope and residual risk

- Changed implementation：`scripts/agy_multilingual_pipeline.py`。
- Changed regression：`tests/test_agy_multilingual_pipeline.py`。
- Production queue、credential、LaunchAgent、Gemini、發布、push、第二代 replacement：均未接觸。
- 尚未執行 production exact canary；主線在獨立 review、整合與 actor 對齊後另行驗證真實模型遵循度。
