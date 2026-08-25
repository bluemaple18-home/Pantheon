# V0396 promotion run state durability review

## Verdict

`REVIEW_NO_GO`

審查對象：

- Base：`345d9c3184856718254615b58b92655743a8d64a`
- Candidate：`178f4504c9e4add4ecb5f35cfff9f92bd115383b`
- Activation：`act-v1:95e27f7f099ab1d6f7fa9ea36ff50ea1761e4a86bc00a58edd1f89cef48a7a91`

## Findings

### P1 - failed replacement active state 仍會跳過 dangling gate 並先執行 automatic sweeps

位置：`scripts/agy_gemini_coordinator.py:1970`

觸發條件：

1. promotion 後 queue registry 仍有 `status=active` 的 run。
2. 該 state 帶有 `failed_external_job_replacement` metadata。
3. registry 的 `run_dir` 已消失、缺 `brief.json`，或 identity 已 drift。
4. coordinator 以 `new_matrix_sweep=True` 或 `legacy_sweep=True` 執行一般 cycle，而不是只用 `exact_run_ids` resume 該 replacement。

證據：

- Candidate 的 `_active_run_integrity_block()` 在 `scripts/agy_gemini_coordinator.py:1969-1971` 對任何 `failed_external_job_replacement` dict 直接 `continue`，沒有驗證 `run_id`、`run_dir`、`brief.json` 或 replacement receipt 是否足以安全 recovery。
- `cycle_once()` 在同一輪只要 integrity block 回 `None`，就先執行 `seed_new_matrix_runs()` 與 `seed_legacy_rewrite_runs()`；呼叫點分別在 `scripts/agy_gemini_coordinator.py:4617-4626` 與 `scripts/agy_gemini_coordinator.py:4628-4643`。
- Candidate 的 dangling sweep regression 只覆蓋「沒有 failed replacement metadata」的 normal active state：`tests/test_agy_gemini_coordinator.py:4890-4941`。
- Candidate 的 failed replacement recovery 測試只覆蓋 `exact_run_ids=("v0393-synthetic-run",)`，且沒有開 automatic sweeps：`tests/test_agy_gemini_coordinator.py:3252-3285`。

風險：

這保留了卡片明列的漏洞：promotion 刪掉 actor-local run_dir 後，只要 dangling active registry 帶 failed replacement metadata，coordinator 不會 fail closed，反而可先做 new/legacy sweep，建立新的 run identity。這會讓原本應由 durable replacement recovery 關閉的 run 與新 auto-seed identity 並存，造成發文狀態持久化與 identity continuity drift。

最小修法：

把 failed replacement 豁免改成受限 recovery gate，而不是無條件跳過：

- 只有 `exact_run_ids` 指定該 run，或 replacement receipt 已完整證明 source archive、replacement job、lane queue 與 inbox result 可消費時，才允許缺 actor run_dir 的 recovery path。
- automatic sweep 前仍必須對 failed replacement active state fail closed，或至少在 replacement state 未進終態前禁止 `seed_new_matrix_runs()` / `seed_legacy_rewrite_runs()`。
- 補一個 regression：active state 含 `failed_external_job_replacement`、`run_dir` missing、`new_matrix_sweep=True`、`legacy_sweep=True` 時，summary 必須是 `blocked` 且 sweep call count 為 0。

Validation gap：

目前 test suite 沒有打到「failed_external_job_replacement + dangling registry + automatic sweeps」的組合；既有 GREEN 不能證明卡片指定的 identity drift 已關閉。

## Non-Blocking Checks

- Promotion preserved-run closure 有明確強化：`_queue_identity_snapshot()` 要求 preserved `run_dir` 是 queue-owned `gsc-copy` canonical descendant，存在 `brief.json`，且 brief run identity 一致；plan 也保存 `run_tree_digest`。
- Installer 將 `GSC_COPY_ROOT` 固定為 `${QUEUE_ROOT}/gsc-copy`，並拒絕不一致的 `PANTHEON_GSC_COPY_ROOT` override；未看到 actor-local default 回退。
- Empty/preserved/completed/failed run、symlink、digest drift 與 zero-mutation 負向路徑在 candidate tests 中有合成 fixture 覆蓋。

## Verification

本輪只做 reviewer 允許範圍內的唯讀驗證與 review artifact 寫入，未修改產品 source/tests，未操作 production、launchctl、真實 queue/state、publish、tag、push 或另開任務。

已執行：

```text
codegraph_status: ready, 582 files, 6993 nodes, 15620 edges
codegraph_context: promotion/run-state/failure replacement 語意查詢完成
git diff --stat 345d9c3184856718254615b58b92655743a8d64a..178f4504c9e4add4ecb5f35cfff9f92bd115383b
git diff --name-only 345d9c3184856718254615b58b92655743a8d64a..178f4504c9e4add4ecb5f35cfff9f92bd115383b
git diff --check 345d9c3184856718254615b58b92655743a8d64a..178f4504c9e4add4ecb5f35cfff9f92bd115383b
git cat-file -t 178f4504c9e4add4ecb5f35cfff9f92bd115383b
git cat-file -t 345d9c3184856718254615b58b92655743a8d64a
```

結果：

```text
git diff --check: PASS
base object: commit
candidate object: commit
worktree before review artifact edit: clean
```

未重跑 candidate pytest：目前 activated worktree HEAD 綁定 `5e5c93200cc6372bb6d6fc9b0c36abaf50363f9c`，而 candidate 是獨立 commit；在「產品 source/tests 唯讀」與「只可寫 RESULT / review.md」限制下，本輪未 checkout candidate 或建立額外 worktree。

## Residual Risk

- 未執行 production promotion 或新 canary。
- Candidate evidence 宣稱完整 pytest 通過，但本 review 發現的 P1 path 不在既有 regression coverage 內。
