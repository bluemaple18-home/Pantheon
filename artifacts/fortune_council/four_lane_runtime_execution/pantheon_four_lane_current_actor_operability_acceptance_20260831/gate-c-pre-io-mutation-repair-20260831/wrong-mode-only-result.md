---
verdict: GATE_C_PRE_IO_MUTATION_REPAIR_PASS_PENDING_INDEPENDENT_REVIEW
independent_review: PENDING
---

# Wrong-mode-only pre-I/O repair

修訂後只修 wrong-mode：在 `reconcile_translation_replacement_identity` execute path 先呼叫既有 `build_plan()`，再進 lock 並保留既有 locked `build_plan()` 重驗。strict wrong-mode RED 由 lock residue 重現，修補後 wrong-mode 與 generation qualified external-drift node `2 passed`；repaired Gate C 13 nodes 加 same-generation resume／rollback impacted nodes 共 `15 passed`。

generation 沒有 source change：`generations/07` 是 external drift fixture，G1 維持 application persistence spy=0、state bytes unchanged 的 qualified contract。production queue 2000 files、ledger/registry digest 與 0/7 loaded 不變；DBG grep 無結果，`git diff --check` 通過。activation/shadow 仍未授權。
