# Repair 2 root cause

狀態：`READY_FOR_REVIEW`，不自審 `GO`。

## 已重現症狀

以未修改的 Repair 1 re-review `fresh_adversarial_probes.py` 重跑，輸出與既有 `fresh_results.json` byte-identical：

- 合法 `EXEC_CONFIRMED` prefix 缺 terminal 被回成 `INVALID/UNKNOWN`。
- schema v2 接受 `PROCESS_NOT_STARTED` 為 `COMPLETE/0`、`PROCESS_STARTED` 為 `COMPLETE/1`，並接受 `pid=0` 為 `COMPLETE/1`。
- 上述錯誤存在時，`strict_replay` 仍為 true，matrix cell 仍為 `DETECTED`。

## 根因與假說

1. 若通用 error 映射誤把合法 blocked reason 當 validation error，將兩類 error 分流後 terminal-loss 應保留 `BLOCKED/1`。結果成立。
2. 若 current schema allowlist/FSM 直接納入 legacy alias，且 PID 只驗型別或允許缺值，移除 alias 並收緊 exact positive-int domain 後應全部 `INVALID/UNKNOWN`。結果成立。
3. 若 matrix 只抽樣少數正向布林值，改由完整合法狀態表與真實 negative controls 共同推導後，任一關鍵 replay 結果被反轉時 cell 應降級。結果成立。

另排除「Reviewer fixture 本身錯誤」：原 probe 可重現文件明列的合法 terminal-loss prefix，且其 expected value 與任務卡一致。

## 修正接縫

- `LEGAL_REPLAY_STATES` 成為 FSM 與完整合法狀態驗證的共同契約。
- `replay` 分離 validation errors 與合法未終結 reasons；只有 schema、binding、order、frame、chain 等 validation errors 強制 `INVALID/UNKNOWN`。
- schema v2 的 `EVENT_TYPES/EVENT_FIELDS` 不含 legacy aliases；PID 必填、exact `int` 且大於零。
- `_integrity_probe` 實跑完整合法狀態表，以及 terminal-loss、legacy alias、PID、order、partial frame、binding、chain controls；`strict_replay` 是它們的 conjunction。

POC 的 `Ledger` 是隔離 fixture builder，可刻意編碼不合法 frame 供 adversarial replay；current schema 的唯一接受邊界是 replay decoder。
