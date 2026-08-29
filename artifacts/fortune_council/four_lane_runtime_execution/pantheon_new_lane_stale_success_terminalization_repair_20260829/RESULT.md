---
id: PANTHEON-NEW-LANE-STALE-SUCCESS-TERMINALIZATION-REPAIR-20260829
status: RE_REVIEW_REQUESTED
type: bounded_repair
production_mutation: false
---

# RESULT：New lane stale-success terminalization Repair

## 裁決

`RE_REVIEW_REQUESTED`。

已新增唯一正式 operator seam：`terminalize-stale-succeeded-writer`。它只接受 `new` lane、唯一 `attempts/01` Writer、active registry、pending Writer operation、succeeded production attempt、完整 archive/inbox，以及 exact run/job/request/prompt/schema/result 與五個 artifact digests。任何 drift、第二 Writer attempt、candidate/review、wrong lane、缺件、symlink 或 job location ambiguity 都在寫入前 fail closed。

成功 execute 的唯一 mutation 是：先新增 immutable `PREPARED` receipt，再把 exact registry 從 `active` 轉為 terminal `failed`，最後將同一 receipt finalize 為 `TERMINALIZED`。archive、inbox、attempt、writer-operation bytes 不搬移、不刪除、不覆寫。重跑回 `already_terminalized` 且 bytes 不變；state write interruption 會留下可重播的 `PREPARED` receipt。

## RED → GREEN

- RED：`.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py::test_stale_success_rca_exact_fixture_has_plan_only_operator_seam -q`
  - 結果：`1 failed`；正式 CLI 對 `terminalize-stale-succeeded-writer` 回 invalid choice，證明現有 seam 拒絕本形狀。
- GREEN：`.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -k 'stale_success' -q`
  - 結果：`24 passed`（exact plan/execute、CLI、hash drift、second job、candidate/review、wrong lane、missing archive/inbox、symlink、receipt-first crash recovery、idempotency、scheduler frontier）。
- affected coordinator/new lifecycle：`.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -k 'stale_success or terminalize_pending or dangling_terminalization or seed_new_matrix_runs' -q`
  - 結果：`55 passed, 332 deselected`。
- `py_compile`：PASS。
- `git diff --check`：PASS。
- debug marker：`[DBG-` 無命中。
- source budget：source `+373/-0`，bounded ceiling 400，PASS。

完整 coordinator suite 另觀察到 `378 passed, 8 failed`；八項皆在既有 campaign translation fixture 的 `external locale plan coverage fields are strict`，不在本卡 seam、new lifecycle 或本次修改區域。本卡未擴 scope 修它們。

## Acceptance mapping

- exact RCA fixture：四個 production evidence snapshots 的 SHA-256 與 RCA receipt 完全一致；result canonical SHA 亦固定。
- provider/reviewer/publisher：全部 `0`。
- protected bytes：before == after。
- mutation allowlist：只允許 exact registry status transition 與單一 terminal receipt。
- crash-safe／idempotent：PASS。
- scheduler frontier：terminalization 後 synthetic official new-matrix seeding 可建立一個 fresh `new` run，未呼叫 provider。
- negatives：hash drift、second job、candidate/review、wrong lane、missing archive/inbox、symlink/regular-file boundary 全部 zero-write PASS。

## Evidence index

- `allowlist-receipt.json`
- `immutability-receipt.json`
- `source-budget-receipt.json`
- exact fixtures：`tests/fixtures/new_lane_stale_success_rca_20260829/`

## Not claimed

- 未對 production queue 或 live run 執行 terminalization。
- 未 install／activate／reload plist 或服務。
- 未呼叫 provider、Reviewer、Publisher。
- 未 promotion、commit、push、tag、deploy。
- 未修改其他 lanes、registry FSM 或 database。
