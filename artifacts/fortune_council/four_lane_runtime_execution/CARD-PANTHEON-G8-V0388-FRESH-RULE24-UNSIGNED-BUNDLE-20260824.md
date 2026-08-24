---
id: CARD-PANTHEON-G8-V0388-FRESH-RULE24-UNSIGNED-BUNDLE-20260824
status: ready
execution_mode: local_task_owned_only
production_mutation: forbidden
remote_access: forbidden
---

# PANTHEON G8 V0388 fresh Rule24 unsigned bundle

## 工作名稱 → 正在做什麼 → 現在狀態

V0388 fresh Rule24 unsigned bundle → 以 V0387 正式 CLI 在 task-owned `/private/tmp` 跑 fresh two-cycle capacity harness → ready；禁止 production、remote、signing、promotion。

## 目的與依賴

- 依賴 main `6868151310` 的 V0387 accepted CLI。
- 只補 V0386 phase 1：fresh unsigned `capacity-receipt.json`、兩份 exact-byte cycle measurements、digest 與可重現 argv。
- 不沿用 V0383/V0385 舊 capacity artifacts；不得把舊 plan、argv 或 authorization 當本卡授權。

## 執行契約

1. 先查 CodeGraph；失敗才限域 `rg`。
2. 建立唯一 task root：`/private/tmp/pantheon-v0388-<correlation>`；所有 input、evidence、sandbox 都是其 canonical strict descendants。
3. input schema 只能取自 V0387 CLI、既有 function signature、tests 與 `DEFAULT_POLICY`；不得猜 schema。
4. bounded policy 至少鎖：`max_bytes=67108864`、`max_file_count=1024`、`sampling_interval_seconds<=300`，並保留既有 retention、RSS/swap、host reserve、reclaim、stop-loss 欄位。
5. 執行正式入口：`<repo-root>/.venv/bin/python -m scripts.pantheon_writer_vnext_runtime_activation_capacity bundle ...`。
6. happy path 必須實跑兩週期；任何 host reserve、project bytes/files、RSS/swap、retention projection、reclaim、cleanup 或 artifact drift 失敗即 `BLOCKED`。
7. 將成功 bundle exact bytes 複製到本卡唯一 evidence 目錄；重算 SHA-256，確認與 CLI summary 一致。保留 machine-readable argv、inputs、summary、digests、capacity receipt、兩份 measurements。
8. 任一輸出缺失、非 fresh、digest mismatch、cycle count 非 2、`production_mutation!=false`、`canary_created!=false` 或 `signed!=false` 即 `BLOCKED`。

## 唯一可寫範圍

- task-owned `/private/tmp/pantheon-v0388-<correlation>/`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0388-FRESH-RULE24-UNSIGNED-BUNDLE-20260824-RESULT.md`
- `artifacts/fortune_council/four_lane_runtime_execution/g8_v0388_fresh_rule24_unsigned_bundle_20260824/`

## 禁止範圍

- production actor、manifest、private-stage、readiness、barrier、queue、state、transaction、LaunchAgents。
- DSSE/key/signing、promotion plan/apply/postcheck、deploy、canary、activation。
- remote/network、push/tag、整條 merge、改 source/tests/workflow/shared metadata、派下一卡。
- 不刪除或清理任何非本卡 task root；本卡 task root cleanup 也必須先保留 exact-byte evidence。

## 驗收

- CLI exit `0`；summary 可 JSON parse，`status=PASS`、`cycle_count=2`、`signed=false`、`production_mutation=false`、`canary_created=false`。
- 三個 bundle artifacts 存在且 SHA-256/byte length 與 summary 完全一致。
- capacity receipt 與兩 cycle measurements 通過既有 schema/semantic verifier；兩 cycle correlation/policy/producer inputs一致且時間新鮮。
- Rule24 回收、停損、host reserve、projection 全 PASS。
- `<repo-root>/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pantheon_writer_vnext_runtime_activation_capacity.py` PASS。
- evidence JSON parse、digest manifest、`git diff --check` PASS。
- 單一 commit、worktree clean、不 push。

## 交付

- Verdict 只能 `DELIVERED_CANDIDATE` 或 `BLOCKED`。
- 回報 commit SHA、fresh correlation、task root lifecycle、artifact digests、測試結果、production mutation count（必須 0）。
- 不得宣稱已簽署、已可 apply 或已取得新 production authorization。
