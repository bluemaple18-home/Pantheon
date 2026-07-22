# V4 Architecture Repair 2 Final Independent Re-review｜GO

## Verdict

- Spec axis：`GO`
- Standards axis：`GO`
- Architecture verdict：`GO`
- Reviewed candidate：`e34d5da658979bf22884772cc7ff4913e9ede2f7`
- Candidate parent：`404e0687c67ad9fa6d07cfd46864ce451309b589`
- Prior independent re-review evidence：`393f8469f07840ddbb056c9c38123ea2ef338f99`
- Decision：方案 B 已可進入另一張、受 allowlist 約束的 production implementation 卡；本 verdict 本身不授權 implementation、Gemini 呼叫、merge、push、deploy、publish 或 content recovery。

## Findings

沒有 P0、P1、P2 或 P3 finding。

## 上輪三項 finding closure

| 上輪 finding | 最終狀態 | Reviewer-owned fresh evidence |
|---|---|---|
| P1：`EXEC_CONFIRMED` 缺 terminal 被誤判 `INVALID/UNKNOWN` | `CLOSED` | 合法 prefix 精確回 `BLOCKED`、count `1`、`complete=false`、`automatic_resend_allowed=false`、唯一 reason `PROCESS_TERMINAL_MISSING`。 |
| P1：schema v2 接受 legacy aliases 與非正 PID | `CLOSED` | `PROCESS_NOT_STARTED`、`PROCESS_STARTED` 均為 `INVALID/UNKNOWN`；PID 缺值、0、負數、bool、字串均為 `INVALID/UNKNOWN`，正整數為 `COMPLETE/1`。 |
| P2：`strict_replay` matrix 未由完整反例推導 | `CLOSED` | baseline 為 `strict_replay=true`／`DETECTED`；terminal loss、legacy、PID、illegal order、partial frame、wrong binding、chain mismatch 七項各自反轉，都自動降為 `false`／`UNSUPPORTED`。 |

## Independent evidence

- `fresh_probes.py` 是 Reviewer-owned probe，未引用 candidate tests 的 assertion，也未修改 candidate。
- fresh probe 連跑兩次 byte-identical；結果 SHA-256 為 `6891ad06383df7ef154eec81528cf1eedfc6cba27bd5352a2f03c497f0420295`。
- 完整合法 replay table 實測：complete-zero=`COMPLETE/0`、blocked-zero-abort=`BLOCKED/0`、blocked-zero-exec=`BLOCKED/0`、ambiguous-broker=`AMBIGUOUS/UNKNOWN`、ambiguous-fork=`AMBIGUOUS/UNKNOWN`、blocked-one=`BLOCKED/1`、complete-one=`COMPLETE/1`；所有狀態的 automatic resend 都是 false。
- Crash regression：durable before-fork evidence=`BLOCKED/0`；before-exec 與 after-exec-before-event 都是 `AMBIGUOUS/UNKNOWN`，未猜 process count。
- FD regression：正確 target table 為 `[0,1,2]` 且無 ledger FD；wrong `close_fds`、wrong `pass_fds` 與 foreign inherited FD 都讓 allowlist 失敗。
- Same-UID raw filesystem replacement 的邊界仍是 `OUT_OF_SCOPE`；external anchor 未由 ledger 自證。方案 C 因無 kernel implementation 仍全部 `UNSUPPORTED`。

## Scope and architecture readiness

- Repair 2 candidate 僅變更卡片 allowlist 內的 architecture doc、隔離 POC/tests 與 Repair 2 evidence，共 9 個路徑；沒有 production、app、articles、registry、metadata 或 publishing 變更。
- 文件保留 bounded future caller、feature flag、no-fallback、migration、implementation allowlist 與 rollback 契約，可直接另開 bounded implementation 卡。
- POC 仍為 synthetic subprocess/fake executable；沒有 production import、framework dependency、automatic retry、Gemini/HTTP/external-model invocation。

## Final decision

`GO`。Repair 1 re-review 的兩個 P1 與一個 P2 均已關閉。此結論只批准方案 B 的 architecture 進入後續受限 implementation review flow；production implementation 仍未授權，且本次沒有執行 merge、push、deploy、publish 或 content recovery。
