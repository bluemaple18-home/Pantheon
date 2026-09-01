---
id: PANTHEON-C-C-T-OWNER-RECEIPT-PROVENANCE-REPAIR-2
status: REPAIR_2_READY_FOR_REVIEW
type: repair
repair_generation: 2
thickness: strict
---

# C-C/T owner receipt provenance Repair-2

## Objective

在不執行真實 launchctl、Gate D/E、provider或 production/public mutation的前提下，讓 C-C/T formal path 結構上無法接受 caller-supplied owner receipts；controller 必須固定組合 owner command、由 private process transport取得原始執行結果、自己建構 receipt，並從 cross-owner authoritative artifacts重新驗證 workload結果。

## Authority

- accepted base：`836d5f0d1d62b58ad886aa37863c15ce41d233ec`
- rejected candidate：`7821adb901d6c23059fecfd33e7b3de03fce8024`
- Repair-1 candidate／本卡 parent：`b5d934dda7d32343fbf62ceff7f35869d9a20745`
- external review evidence：`747536077338818de0b9eb4b0525a54dc5c851bb`，僅為 review evidence child，不是 code branch parent。
- Reviewer conversation：`6a965345-e49c-83e8-9623-1b5f11a19667`
- Owner authorization：本次對話明示授權推 evidence 並開始 Repair-2。
- launchctl／Gate D/E／provider／production/public mutation：未授權。
- commit／push Repair-2 candidate：未授權；完成實作與驗證後停在 dirty pre-freeze。

## Blocking findings

- `CCT-P1-WORKLOAD-OWNER-RECEIPT-PROVENANCE`
- `CCT-P1-LAUNCHCTL-FINGERPRINT-RECEIPT-PROVENANCE`

兩項共享 invariant：formal PASS 的 receipt 必須由 controller-owned invocation 與 authoritative read-back推導，caller mapping不得成為 authority。

## Allowed scope

- `scripts/pantheon_four_lane_disposable_acceptance_cohort.py`
- `tests/test_pantheon_four_lane_disposable_acceptance_cohort.py`
- 本卡
- `artifacts/fortune_council/disposable_acceptance_cohort/REPAIR-2-RESULT.md`
- `artifacts/fortune_council/disposable_acceptance_cohort/repair-2-raw-test-output.txt`

## Forbidden scope

- shared runtime manifest／schema、readiness ACK、activation barrier、installer
- Coordinator、Runner、Publisher、C-B、multilingual或 broker owner implementation
- production fingerprint欄位擴張；external review 的 P2 deferred 到 Gate D/E另卡
- public argparse／main／`run_once()` receipt callback injection
- 真實 `/bin/launchctl bootstrap`、`kickstart`、`bootout`
- provider、production/public queue、ledger、registry、content、release、tag、deploy
- Gate D/E、merge、main mutation
- 新 scheduler、runtime、ledger、registry、FSM、database或第二套 barrier

## Repair slices and blocking edges

### `CCT-R2-S1-FORMAL-INJECTION-RED`

- traces_to：兩個 blocking finding。
- frontier：可立即開始。
- RED：public `run_once()`／formal CLI 不再接受 workload、launchctl、fingerprint receipt callbacks；caller即使準備完整 owner-shaped mappings也無法送入 formal path。
- verification：focused test必須先因現行 callback signature或可偽造 PASS而 RED。

### `CCT-R2-S2-CONTROLLER-OWNED-TRANSPORT`

- depends_on：`CCT-R2-S1-FORMAL-INJECTION-RED`。
- traces_to：`CCT-P1-LAUNCHCTL-FINGERPRINT-RECEIPT-PROVENANCE`。
- controller 固定組 `/bin/launchctl print/bootstrap/kickstart/bootout` argv；receipt 只能由 process returncode/stdout/stderr與 controller後續 observation建構。
- 測試只可 monkeypatch private process transport，回傳 `subprocess.CompletedProcess` 等原始結果；不得回 owner receipt mapping。
- formal argparse／main／`run_once()` 不得暴露 transport override。implementation test期間不得執行真 launchctl。

### `CCT-R2-S3-WORKLOAD-OWNER-INVOKE-READBACK`

- depends_on：`CCT-R2-S1-FORMAL-INJECTION-RED`。
- traces_to：`CCT-P1-WORKLOAD-OWNER-RECEIPT-PROVENANCE`。
- controller 依 immutable fixed schedule固定組 Coordinator、Runner、C-B、bundle close、Publisher dry-run commands；原始 stdout／receipt由 controller解析。
- Publisher 不必新增 CLI：controller 可在 private、不可由 formal caller 替換的 adapter 中固定呼叫既有 `publish_ready_runs`、`publish_ready_rewrite_runs`、`publish_ready_translation_runs`，強制 `dry_run=True`、`push=False`、`max_runs=1` 與單一 `exact_run_ids`；formal path 不得注入 function或 final receipt。
- 每一步後重新讀 owner authority；Runner delivery至少以 broker-owned V4 ledger＋anchor交叉驗證，不只相信 Runner inbox／archive；Coordinator terminal、C-B pending＋registration、Publisher dry-run與 queue drain均由 controller讀 filesystem authority重算。
- 任一 command成功但 authoritative state缺失／漂移，必須 fail closed且不得寫 PASS。

### `CCT-R2-S4-REGRESSION-CLOSEOUT`

- depends_on：`CCT-R2-S2-CONTROLLER-OWNED-TRANSPORT`、`CCT-R2-S3-WORKLOAD-OWNER-INVOKE-READBACK`。
- forged receipt、no owner execution、owner execution無 read-back、no-op launchctl transport、fingerprint caller injection全部 RED。
- 執行 focused C-C/T、Coordinator affected seam、runtime manifest／sealed Runner regressions、`py_compile`、`git diff --check`。
- 更新獨立 Repair-2 result／raw evidence；不覆寫 Repair-1 歷史 evidence。

## Falsifiable hypotheses

1. 若根因是 public formal callback authority，移除 `run_once()` callbacks並讓測試只能替換 private raw transport後，預組 receipt無法再進入 PASS path。
2. 若 schema validation本身仍可被繞過，owner command成功但 cross-owner artifact缺失的測試仍會錯誤 PASS；加入 read-back後必須轉 RED。
3. 若 launchctl provenance仍由 caller控制，傳入任意 loaded／absent mapping仍能影響結果；移除 public injection後應在呼叫 formal path前即不可達。
4. 若 production service-state 不能由既有 repo／home／env convention穩定 derive並由 private raw readers重算，則本卡必須停在 `BLOCKED_REQUIRED_OWNER_SEAM`，不得以 hardcoded manifest／plist／registry mapping替代。

## Acceptance

- 先跑一個命中 `CCT-R2-S1` 的 red-capable focused test，確認因 provenance症狀失敗，不接受 import／fixture錯誤。
- formal `run_once()`、argparse與main沒有 owner receipt callback或 public transport injection。
- private transport只輸出原始 process result；controller自己建構、normalize與重讀 evidence。
- formal positive flow不可只靠預組 receipts完成。
- 修復不執行真 launchctl、不擴張 production fingerprint、不修改 owner implementations。
- 完整驗證與 `git diff --check`通過後，只能標記 `REPAIR_2_READY_FOR_REVIEW`；不得自稱 `C-C_T_REVIEW_GO`。
- Repair-2 targeted re-review必須回同一 Reviewer conversation；若仍有 P0/P1，停止為 `BLOCKED / REVIEW_REPAIR_LIMIT`。

## Rollback

Repair-2只修改 C-C/T controller、focused tests與本輪 evidence；可整體移除 Repair-2 delta回到 `b5d934d…`，不影響 R2、C-A、C-B或 production default behavior。
