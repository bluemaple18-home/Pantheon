# APF-004 macOS swap telemetry fallback repair

## 任務狀態

- 工作名稱：APF-004 macOS swap telemetry fallback repair
- 基線：`9c4c19c80c8bd535b4482fe08693c338e3c8d986`
- 模式：code/test only
- production mutation：0

## Root question

當 macOS 上的 `sysctl -n vm.swapusage` 命令失敗時，capacity guard 是否能由可信、本機、bounded 的原生介面取得 swap used bytes，同時讓未知或格式異常維持 fail-closed？

## 已知證據

- 已核准的單次 live capacity 結果為 `NO-GO`。
- 唯一 reason 是 `swap_telemetry_unknown`，底層錯誤是 `swap_command_failed:1`。
- 本任務不得重跑 live capacity preflight。

## 可證偽假說

1. 主命令的 delivery/權限失敗，但 Darwin `sysctlbyname` 原生介面仍可提供同一 `vm.swapusage` telemetry。
2. 問題來自主來源輸出格式漂移；此時不得以 fallback 掩蓋解析異常，必須維持 unknown/NO-GO。

## Allowlist

- `.ai/codex_task_apf_004_macos_swap_telemetry_fallback_repair_20260815.md`
- `scripts/pantheon_content_capacity_guard.py`
- `tests/test_pantheon_content_capacity_guard.py`

## 實作契約

- 主命令成功且輸出可解析時，沿用主來源。
- 主命令非零時，才嘗試 Darwin 原生 `sysctlbyname` fallback。
- fallback 必須驗證回傳碼、完整結構大小及 `used <= total`。
- 主來源成功但解析錯誤、fallback 失敗或 fallback 資料異常，一律回 telemetry unknown；不可將 unknown 當 0。
- 不修改容量門檻、runtime identity、manifest 或 LaunchAgent。

## RED / GREEN 驗收

- 主來源成功：回傳解析後 used bytes，不呼叫 fallback。
- 主來源失敗、fallback 成功：回傳 fallback used bytes。
- 主來源與 fallback 皆失敗：回 unknown，preflight 為 `NO-GO`。
- 主來源解析錯誤：fail-closed，不呼叫 fallback。
- fallback 結構異常：fail-closed。
- targeted tests 與 affected capacity suite PASS。
- `git diff --check` PASS，debug residue scan 零命中。

## 禁止範圍

- live capacity preflight、launchctl、reload、Gate B、publication、production mutation 或 retry。
- production runtime identity、manifest、LaunchAgent、capacity thresholds 的任何變更。
- push 或 amend。

## History

- 2026-08-15：完成 startup/coding protocol 與 CodeGraph 查詢；CodeGraph 未直接定位 swap helper，依規則限域讀取 capacity guard 與測試。
- 2026-08-15：RED 為 4 個目標案例因缺少 `fallback` seam 而失敗；不是 import 或 fixture failure。
- 2026-08-15：根因為 swap telemetry 只有外部 `sysctl` 命令主來源；該命令非零時，macOS 沒有同資料契約的原生 fallback，因而回 unknown。
- 2026-08-15：新增 Darwin `sysctlbyname` bounded fallback；只有主命令非零才使用，驗證 syscall、結構大小與 usage bounds。
- 2026-08-15：targeted 7 tests PASS；capacity/runtime affected suite 87 tests PASS；live preflight 與 production mutation 均為 0。
