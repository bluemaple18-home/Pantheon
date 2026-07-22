# V4 Architecture Repair 1 Independent Re-review｜NO_GO

## Verdict

- Spec axis：`NO_GO`
- Standards axis：`NO_GO`
- Architecture verdict：`NO_GO`
- Reviewed Repair 1 candidate：`ef6d6f3a26e6d44c3586cdb4beee37918d58c9ee`
- Provisioning parent：`16e71276ee2c5da32dde2ea2665b37d6204c5a4b`
- Original candidate：`735d2850bd89bf3e4b29748f310981ba4d855709`
- Decision：方案 B 尚不可進入 production implementation。兩個 P1 仍未關閉，且 runtime-derived matrix 沒有捕捉這些真實反例。

## Findings

### [P1] EXEC_CONFIRMED 後缺 terminal 被改判 INVALID/UNKNOWN

- severity：`P1`
- category：`correctness / process_accounting / crash_replay`
- path:line：`scripts/agy_gemini_v4_architecture_probe.py:187`
- evidence：fresh probe 依文件合法前綴寫入 `OPERATION_CREATED → BROKER_ATTEMPTED → FORK_ATTEMPTED → EXEC_CONFIRMED`，沒有 terminal。`_fsm_result` 先產生文件要求的 `BLOCKED/1`，同時加入 `PROCESS_TERMINAL_MISSING`；`replay` 隨後把任何非-AMBIGUOUS error改成 `INVALID/UNKNOWN`。`fresh_results.json` 的 `replay_contract.exec_confirmed_without_terminal` 顯示 documented expected `BLOCKED/1`，actual `INVALID/UNKNOWN`。
- risk：已 durable 證明成功 exec 的 process 在 broker crash／terminal 遺失時失去已知 count 1，違反 Repair 文件的合法狀態表與 crash accounting；recovery無法區分「ledger非法」與「已啟動但 terminal 缺失」。雖然 `automatic_resend_allowed=false` 仍 fail closed，process accounting 仍不正確。
- suggested_fix：將 `PROCESS_TERMINAL_MISSING` 視為 `BLOCKED/1` 的 reason，而非 schema/FSM validation error；只有真正非法的 schema、binding、ordering、framing或chain error才轉成 `INVALID/UNKNOWN`。加入新-schema `EXEC_CONFIRMED` 無 terminal regression。
- validation_gap：focused tests只覆蓋 `FORK_ATTEMPTED` 前後的 0／UNKNOWN crash windows，未鎖定文件明列的 `BLOCKED/1` terminal-loss case。
- confidence：`high`

### [P1] current schema 仍接受舊 aliases 為 COMPLETE

- severity：`P1`
- category：`correctness / replay_schema / migration_boundary`
- path:line：`scripts/agy_gemini_v4_architecture_probe.py:24`
- evidence：文件的 closed schema只列 `PREFLIGHT_REJECTED/FORK_ATTEMPTED/EXEC_FAILURE/EXEC_CONFIRMED`，但 `EVENT_TYPES`、`EVENT_FIELDS`與 `_fsm_result` 仍把 `PROCESS_NOT_STARTED`、`PROCESS_STARTED` 當 schema v2 合法事件。fresh probe 的 `legacy_process_not_started` 回 `COMPLETE/0`，`legacy_process_started` 回 `COMPLETE/1`；另 `EXEC_CONFIRMED(pid=0)` 也回 `COMPLETE/1`。
- risk：舊 ledger 可繞過 Repair 1 新增的 fork/exec分帳，重新把 preflight與 post-fork exec failure壓成同一個 complete-zero型態；這正是 P1-05 要消除的 attribution 缺口。current schema宣稱 closed、strict，但實際接受未列入文件的遷移 aliases及非正 PID。
- suggested_fix：從 schema v2 的 event allowlist/FSM移除 legacy aliases；若歷史 evidence確實要讀，使用明確的 legacy decoder/version並輸出 legacy/unsupported狀態，不得轉成 current `COMPLETE`。對 `EXEC_CONFIRMED.pid` 加入正整數限制。
- validation_gap：focused strict replay tests只驗 illegal order、duplicate、unknown field與bad ordinal/outcome，沒有斷言 documented event set之外的 legacy aliases與 nonpositive PID必須拒絕。
- confidence：`high`

### [P2] strict_replay matrix observable 對真實反例仍維持綠燈

- severity：`P2`
- category：`testing / evidence_honesty / matrix_derivation`
- path:line：`scripts/agy_gemini_v4_architecture_probe.py:465`
- evidence：`strict_replay` observable只合併 valid-complete、partial-detected與wrong-binding-detected。即使 fresh probes已重現 terminal-missing錯誤與兩個 legacy aliases被接受，baseline `strict_replay_observable_value`仍為 true，`illegal_or_partial_replay` cell仍為 `DETECTED`。手工 override `strict_replay=false`確實會降為 `UNSUPPORTED`，證明降級 wiring存在，但實際 predicate覆蓋不足。
- risk：matrix形式上是 observable-derived，卻能在核心 replay P1存在時保持 supported綠燈；兩次 deterministic輸出不能補足錯誤 predicate。
- suggested_fix：讓 `strict_replay` observable直接涵蓋完整合法狀態／count組合、documented event allowlist、terminal-loss、legacy alias、PID domain與所有 strict negative controls；任一失敗時自動降級。
- validation_gap：negative-control test只人工覆寫 boolean，沒有以實際 failing replay result驅動 observable變 false。
- confidence：`high`

## 原 5P1／2P2 逐項狀態

| Original finding | Re-review status | Evidence |
|---|---|---|
| P1-01 crash window/process accounting | `UNRESOLVED` | durable 0與AMBIGUOUS/UNKNOWN已修；但 documented `EXEC_CONFIRMED` missing terminal仍錯成INVALID/UNKNOWN，而非BLOCKED/1。 |
| P1-02 strict typed FSM | `UNRESOLVED` | illegal order等已拒絕；但 schema v2仍接受 legacy start/not-started aliases為COMPLETE，pid=0亦可complete。 |
| P1-03 real broker→target FD isolation | `RESOLVED` | correct target FD table `[0,1,2]`；wrong close/pass與foreign extra FD均被觀察並使allowlist失敗。 |
| P1-04 external anchor/trust boundary | `RESOLVED` | same-UID replacement可發生，文件與matrix均固定標 `OUT_OF_SCOPE`；舊anchor mismatch可偵測，未宣稱immutability。 |
| P1-05 preflight vs exec failure | `RESOLVED` | 真實 broker unlink race產生 `FORK_ATTEMPTED + EXEC_FAILURE(EXEC_RACE)`，與preflight ledger bytes不同。舊 Reviewer手工 fixture仍相同不否定此新實測。 |
| P2-01 observable-derived matrix | `UNRESOLVED` | override可降級，但實際 strict replay反例未使 observable/cell降級。 |
| P2-02 bounded caller/migration contract | `RESOLVED` | 文件鎖定單一 runner `process_once` callsite、flag、entrypoint、FD/wire/anchor、legacy no-fallback、allowlist、tests與rollback。 |

## 已確認關閉的核心證據

- Durable crash-before-fork：`BLOCKED/0`。
- Fork/exec confirmation前 crash：`AMBIGUOUS/UNKNOWN`；automatic resend false。
- Orphan target marker存在但無 durable exec event：仍誠實回 `AMBIGUOUS/UNKNOWN`。
- Success/nonzero/timeout：`COMPLETE/1`。
- 真實 broker→target FD table：correct `[0,1,2]`；wrong close/pass與extra FD均失敗。
- Actual preflight-to-exec unlink race：`BLOCKED/0 + EXEC_FAILURE(EXEC_RACE)`，與 preflight bytes不同。此補證充分關閉原 P1-05，即使舊手工 fixture仍 byte-identical by construction。
- Same trust-domain full replacement：明確 `OUT_OF_SCOPE`；provider internal calls維持 `UNKNOWN`；C全部 `UNSUPPORTED`。

## Final decision

`NO_GO`。不得開始 production implementation、merge、push、deploy、publish或 content recovery。本 re-review只新增獨立 evidence，未修改 candidate、Repair tests/docs/POC、Repair evidence、原 Review evidence或任何 production檔案。
