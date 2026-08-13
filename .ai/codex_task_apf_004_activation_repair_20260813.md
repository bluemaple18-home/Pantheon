# APF-004-ACTIVATION-REPAIR-001

## 工作名稱

修復 APF-004 aggregate activation `exit=1` 與缺失 failure receipt。

## 現況證據

- `origin/main`、runtime actor：`79bdc809b0b7e17005c5420236dfb71e2bf794c2`。
- corrected manifest 與三個 installer `--preflight`、`--install` 均曾 PASS。
- 唯一一次 coordinator `--activate` 回 `exit=1`。
- activation 自動 rollback live plists；live manifest 已由保留 backup 回復。
- 六個服務 unloaded；capacity guard 留在舊 actor；queue/state `0 KiB`。
- stage 保留：`<runtime-root>/private-home/Library/LaunchAgents/.pantheon-four-lane-stage`。
- 本次 failure receipt 缺失；不得把舊 evidence 當本次結果。

## 目標

建立可重現、無 live mutation 的 RED harness，定位 activation fail layer；最小修復 installer，使失敗必留 receipt、成功路徑可在隔離 fixture GREEN。

## 可改範圍

- `scripts/install_agy_gemini_coordinator_launchd.sh`
- 與 aggregate activation／barrier／rollback 直接相關的 helper。
- 對應 tests、fixtures、sanitized evidence、此任務卡。

## 禁止範圍

- 不改文章、writer、publisher business logic、registry、共享生成檔。
- 不執行 live `--install`／`--activate`、`launchctl` mutation。
- 不 external model、publish、transaction、tag、schedule、push、deploy。
- 不刪 stage；不重跑已失敗的 production activation。
- 不讀寫 secrets；evidence 必須 sanitized。

## Root-cause 流程

1. 保存現有 failure shape；先查 CodeGraph，無結果才限域 `rg`。
2. 建立單一 red-capable command，在 temp/private fixture 重現 `exit=1`＋failure receipt 缺失。
3. 列少量可證偽假說；一次只驗一個變數。
4. RED 後做最小修復；不得先廣泛重構。
5. GREEN：成功與 fail-closed rollback path 均驗；失敗 receipt 必須有當次 correlation／stage identity／exit reason。

## 驗收

- 原症狀 RED 可重現，且不是 fixture/import/env 無關失敗。
- root cause 有證據；至少一個假說被證偽或確認。
- 最小測試 suite PASS。
- 既有 installer/preflight 受影響測試 PASS。
- `rg '\[DBG-'` 無殘留。
- `git diff --check` PASS。
- commit 僅含 allowlist 檔案。
- 回 `REPAIR_READY_FOR_REVIEW` 或 `REPAIR_BLOCKED`；不得自行進 live activation。

## 下一 frontier

本卡唯一 frontier：`APF-004-ACTIVATION-REPAIR-001`。Repair 合格後回主線 review，再另產 exact live reactivation payload。

## Repair history

### 2026-08-13 fact gate

- CodeGraph：此 worktree 尚未初始化，查詢明確失敗；依契約改採限域 `rg` 與指定原始碼區段。
- 受影響檔案：`scripts/install_agy_gemini_coordinator_launchd.sh`、`tests/test_agy_gemini_coordinator.py`、本卡與 sanitized evidence。
- Public command：`scripts/install_agy_gemini_coordinator_launchd.sh --activate`。
- Failure boundary：matching stage 檢查後，aggregate preflight 位於 `ERR` trap 安裝之前；此處 `exit=1` 不會留下 failure receipt。rollback receipt 目前也缺 correlation、stage generation 與 closed exit reason。
- 使用者邊界：只允許 temp/private fixture；禁止 live `launchctl` mutation、install/activate、stage 刪除與外部動作。

### 可證偽假說

1. 若 failure receipt 缺失是因 activation failure handler 安裝過晚，讓隔離 fixture 的 aggregate preflight 在 mutation 前失敗，應得到 `exit=1` 且 stage 內沒有 receipt；把 handler 提前到 matching stage 驗證後，症狀應消失且 mutation log 仍為空。
2. 若缺失是 rollback 本身中止造成，提前 handler 不會讓 pre-mutation fixture 轉綠；必須另在 rollback 邊界找到 shell abort 證據。此假說先由第一個 RED 結果區分，不同時改第二個變數。

### 驗證計畫

1. 擴充現有 mixed-manifest private fixture 成單一 RED → `pytest -q tests/test_agy_gemini_coordinator.py::test_aggregate_activation_rejects_mixed_installer_manifest_before_mutation` 必須因 receipt 缺失失敗，且 activation `exit!=0`、mutation log 為空。
2. 最小修復 activation failure handler 與 receipt 欄位 → 同一 command GREEN；再驗既有 rollback 成功／失敗矩陣與新增成功 activation fixture。
3. 跑 installer/preflight 受影響 suite、`rg '\[DBG-'`、`git diff --check`，保存 sanitized command receipt。

### RED → GREEN 結果

- RED：單一 fixture command 因 `failure-receipt.json` 不存在而失敗；activation `exit=1`、fake launchctl mutation log 不存在，確認不是 fixture/import/env 失敗。
- Root cause：matching stage 之後的 aggregate preflight 位於 `ERR` handler 安裝之前；因此 fail-closed rejection 直接退出，沒有 receipt。假說 1 已確認；同一 failure seam 不需要假說 2 的 rollback instrumentation。
- 最小修復：matching stage 後立即建立 correlation／stage identity／closed phase handler；pre-mutation failure 寫 `ACTIVATION_REJECTED`，live mutation failure 沿用 rollback 並寫相同 receipt schema。
- GREEN：原單一 command PASS；成功 activation fixture、`ROLLBACK_COMPLETE`、`ROLLBACK_FAILED` 共四個 case PASS，均只使用 temp/private fake launchctl。
- Sanitized evidence：`.ai/evidence/apf_004_activation_repair_001.md`。

### P1 re-review follow-up

- Reviewer edge：matching stage 後，無效 external correlation 於 handler/trap 安裝前 `exit=1`，因此零 control mutation但沒有 failure receipt。
- Handler 前 exit audit：activation 專屬區段只有 matching-stage rejection 與 correlation validation；前者因 stage identity 不可信，沒有安全 receipt destination／identity，與本 P1 不同型。本 follow-up 只移動 correlation validation。
- RED command：原 mixed-manifest fixture 加 invalid-correlation 參數 case；預期 receipt 使用 generated correlation、`phase=correlation_validation`，目前因 receipt 不存在而 RED。
- RED observed：`FileNotFoundError: .../.pantheon-four-lane-stage/failure-receipt.json`；在此之前已斷言 `returncode != 0`、錯誤為 correlation validation、fake mutation log 不存在。
- 最小修復：先建立 `activation-<generation>-<pid>` 安全 correlation 與 handler/trap，再驗 external correlation；合法值才覆寫 generated correlation，無效值以 `false` 進 handler，未寫入 receipt。
- GREEN：新增 edge 與原 matrix 共 `5 passed`；受影響 suite `31 passed, 151 deselected`。
