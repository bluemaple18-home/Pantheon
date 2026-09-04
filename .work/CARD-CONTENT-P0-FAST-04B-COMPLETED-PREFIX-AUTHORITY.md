# CONTENT-P0-FAST-04B — Completed Prefix Authority

## Objective

關閉 `943463319a` 的 completed-prefix admission 缺口：Checkpoint B 跳過前四槽前，必須由既有 topic reservation authority 證明四槽皆為同一 frozen plan owner 的 `PUBLISHED`。

## Failure evidence

- 最後成功基線：`54050d87d8` 已驗收 frozen plan SHA、10-slot identity 與完整 preflight。
- 失敗起點：`943463319a` 新增 `completed_count=4`，目前只驗證四份 brief bytes；四筆 reservation 即使仍是 `RESERVED`，也會跳過並回報 Checkpoint B `READY`。
- Durable invariant：只有 authority 的 exact owner `PUBLISHED` 狀態可證明槽位已完成；本機 brief 存在不等於已發文。
- RED：前四槽僅 prepare、未 publish 時，以 `completed_count=4` 執行 Checkpoint B，必須在 slots 5–10 claim 前拒絕。

## Scope

- `scripts/pantheon_topic_reservation.py`：新增最小 read-only exact-owner published verifier。
- `scripts/pantheon_content_batch.py`：completed prefix 逐槽呼叫 verifier。
- `tests/test_pantheon_topic_reservation.py`
- `tests/test_pantheon_content_batch.py`

## Constraints

- 不新增 ledger、lock、transaction、scheduler 或第二套狀態。
- 不修改 reservation transition 語義。
- 不呼叫 provider、publish、push、merge、deploy 或 production。
- 驗證必須先於 slots 5–10 的任何 claim/output mutation。

## Acceptance

1. `RESERVED`、缺失、foreign owner、malformed state 均 fail closed。
2. exact owner `PUBLISHED` 通過，Checkpoint B 只準備 slots 5–10。
3. batch、topic identity、topic reservation regression 全綠。
4. `py_compile` 與 `git diff --check` 通過。

## Mainline evidence

- RED：`test_checkpoint_ten_rejects_unpublished_completed_prefix_before_new_claim` 在 `943463319a` 上未拋錯，證明 `RESERVED` 前綴會被誤跳過。
- Repair：authority 新增 read-only exact-owner published verifier；batch 在 completed-prefix brief bytes 驗證後逐槽查核，任一槽不符即停止，尚未進入 slots 5–10 claim。
- Targeted GREEN：published 正路徑、unpublished fail-closed、brief drift fail-closed、authority exact/read-only 共 `4 passed`。
- Full regression：batch + topic identity + topic reservation 共 `69 passed`；`py_compile`、`git diff --check` 通過。
- 邊界：只接受本機 Checkpoint B preparation admission；Writer／Reviewer／Publisher／production 仍未執行。
