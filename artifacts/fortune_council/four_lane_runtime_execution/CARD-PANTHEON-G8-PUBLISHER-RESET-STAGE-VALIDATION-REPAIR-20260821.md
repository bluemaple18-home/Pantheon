# G8 Publisher reset stage-validation 限域修復卡

## 工作名稱／狀態

- 工作名稱：修復 Publisher reset stage-validation 靜默失敗
- 正在做什麼：以既有 production failure receipt 與相同輸入契約，定位 `--reset-publisher-activation-only` 在 `publisher_reset_stage_validation` 內唯一失敗 primitive，補齊可觀測 fail-closed 邊界與回歸測試。
- 現在狀態：READY FOR REUSED FORMAL THREAD

## Root question

為何 stage plist、live normal receipt、live identity 與 activation-only 診斷副本各自 PASS，但正式 reset 入口仍在 `publisher_reset_stage_validation` 無 stdout/stderr exit `1`？如何用最小修復讓同一輸入成功，或至少讓 receipt 精確指出失敗 primitive，且 mutation 前仍 fail-closed？

## 已鎖定證據

- source／origin／runtime actor：`7b2f9b546bdac7c162c7ade2271eca6922020070`，actor clean。
- 唯一一次正式 reset：exit `1`；receipt status `ACTIVATION_REJECTED`；phase `publisher_reset_stage_validation`；stdout/stderr 空白。
- reset 後 live 未變：Publisher absent，其他六服務 loaded/no-PID；無 activation、child、transaction、tag 或 canary push。
- 個別只讀診斷 PASS：stage Publisher formal validation、live Publisher canonical normal receipt、live identity/service label、診斷副本 one-shot/activation-only transform 與 receipt。
- terminal evidence：`CARD-PANTHEON-G8-PUBLISHER-CANARY-FINAL-SHIP-20260821-RESULT.md`。

## 任務邊界

### 可修改

- `scripts/install_agy_gemini_coordinator_launchd.sh`
- `tests/test_agy_gemini_coordinator.py`
- 本卡對應單一 RESULT：`CARD-PANTHEON-G8-PUBLISHER-RESET-STAGE-VALIDATION-REPAIR-20260821-RESULT.md`

### 禁止修改／禁止動作

- 不改 Publisher 業務邏輯、四 lane routing、manifest schema、capacity/Rule24/Rule25 契約。
- 不碰 production queue、runtime actor、LaunchAgents、launchctl、remote、tag、push、activation。
- 不建立新 thread、Reviewer 或 Repair identity；只重用正式 thread `01a0228a-9c2c-7e01-9f3c-06808720a9ff`。
- 不重跑 production reset，不做 release 全套，不廣掃 repository，不用 sleep/retry 掩蓋 race。
- 不降低任何 identity、path、argv、schedule 或 pre-mutation fail-closed gate。

## 實作要求

1. 先把 `publisher_reset_stage_validation` 拆成可識別 primitive，建立一次完整 failure matrix；禁止「測一個、改一個」。
2. 用測試 fixture 重現 production 差異；優先檢查真實 shell／macOS primitive 與測試 shim 的語義差異、temp path、plist argv 操作、redirect/ERR trap。
3. 每個會無訊息失敗的 primitive 必須有穩定 stderr 或 receipt subphase/check id；不得把錯誤吞掉。
4. 修復必須維持 mutation 前 fail-closed；失敗時 live plist、launchctl 狀態、其他六服務與 child I/O 皆為零變更。
5. 同一 blocker 最多兩輪實作；仍無法重現或證明就交付 BLOCKED RESULT，不擴大範圍。

## 驗收

- 新測試可在修復前精確重現錯誤，修復後 PASS。
- `publisher_terminal_reset` focused tests 全部 PASS。
- 新增至少一個 primitive failure 負向測試，驗 stderr/receipt 能精確定位且 mutation log 為空。
- `bash -n scripts/install_agy_gemini_coordinator_launchd.sh` PASS。
- `git diff --check` PASS。
- 僅一個 source commit；RESULT 必須列出 root cause、修改、完整測試數量、未做項與 full SHA。

## 停止條件

- production runtime 一律不動。
- scope 需要超出兩個允許 source/test 檔時立即 BLOCKED。
- 同一 blocker 第二次修復仍失敗時立即停止，不進第三輪。
