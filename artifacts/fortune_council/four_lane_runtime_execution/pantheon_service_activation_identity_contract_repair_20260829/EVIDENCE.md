# Evidence Index

- `identity_semantic_census.py`：accepted parent、committed manifests、RCA lineage與baseline test set的唯讀deterministic collector。
- `identity-census.json`：6 producer／14 consumer call sites、5 committed manifests、3 production lineage records、7 live plists與36 regression nodes的完整semantic census。
- `DESIGN-CORRECTION.md`：actor-prefix overreach裁決、修正後durable invariant與最小Repair frontier。
- `red_exact_recovery_stage.json`：exact operation-specific identity＋`actor_head` 在正式 recovery-stage edge 的 RED。
- `green_exact_recovery_stage.json`：同一 fixture 雙跑 GREEN；兩次皆為 `1 passed`。
- `test_receipt.json`：targeted、promotion downstream、coordinator/install/aggregate、compile與 diff gates。
- `anti_expansion_receipt.json`：allowlist、LOC、禁止吸收與 production/external mutation counts。
- `baseline_comparison.py`：固定相同 interpreter、pytest selection、參數與環境的可重跑比較harness。
- `candidate_broad_pytest.stdout.txt`／`.stderr.txt`：candidate完整廣域診斷原始輸出。
- `baseline_broad_pytest.stdout.txt`／`.stderr.txt`：detached exact parent完整廣域診斷原始輸出。
- `baseline_identical.json`：final candidate與parent同selection的command SHA、exit、逐node failure set與normalized error digest exact比較。
- `BASELINE_COMPARISON.md`：第一次candidate撤回與final baseline-identical摘要。
- `RESULT.md`：DESIGN_GO最小revision後的 `RE_REVIEW_REQUESTED` 單一裁決。

所有 runtime fixture只使用 pytest temporary roots；未讀寫 live manifest、stage、plist、queue、registry或ledger。
