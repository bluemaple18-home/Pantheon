# Root cause

1. Production caller 未傳 profile，broker 以 executable basename 推論 `antigravity_cli_v1` 或 `raw_stdin_v1`；因此 `agy-current` 可落入 synthetic profile。修復後 production runner 固定傳 `antigravity_cli_v1` 與部署時配置的 trusted SHA-256，broker 對未知 profile／digest fail closed。
2. 原流程先雜湊 pathname bytes，再由 broker 重新以同一路徑 `Popen`；驗證後替換 pathname 可改變實際 exec bytes。修復後 supervisor 只讀一次 bytes、核對 trusted digest、寫入 operation-local read/execute-only snapshot，broker 只執行該 snapshot。
3. `EXEC_CONFIRMED` append 位於 target lifecycle cleanup 範圍外；CAS exception 會直接離開且不回收 child。修復後 target、pipes 與 agy tempdir 由同一個 post-fork `finally` 收斂，所有 exception 都 kill、wait、close、cleanup。
4. Receipt 原本只綁 operation/request/model；schema-valid synthetic stdout 可與 production success 混淆。修復後 receipt 必填 profile 與 executable digest，production runner 只接受 `antigravity_cli_v1` 加 configured trusted digest 的完全相符 receipt。

可證偽假說均由 public `run_single_shot` 或 production `process_once` seam 的 regression 驗證；未加入 retry、fallback 或 debug instrumentation。
