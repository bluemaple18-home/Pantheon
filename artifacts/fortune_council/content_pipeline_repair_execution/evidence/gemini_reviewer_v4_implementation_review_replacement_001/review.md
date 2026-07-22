# V4 Implementation Replacement Review

Verdict：`NO_GO`。

本證據為 interrupted Reviewer recovery：替代 Reviewer 在第三次 Codex `systemError` 前已獨立完成 `fresh_probes.py`，但未能執行、撰寫 verdict 或 commit。主線未修改該 probe，只在 candidate worktree 以既有專案 Python 離線執行兩次，結果 byte-identical，並保存其中一次輸出。

## P1｜真實 pre-fork failure 沒有 durable aborted event

Reviewer-owned probe 走 production `run_single_shot`，在 `OPERATION_CREATED` durable 後、target fork 前讓 fake executable 與 precheck digest 不一致。

實際結果：

- ledger 只有 `OPERATION_CREATED`
- target launch count 為 `0`
- anchor 存在
- run result 與 fresh replay 均為 `INVALID / UNKNOWN`
- error 為 `ILLEGAL_EVENT_ORDER`

卡片與已核准架構要求：此已知 pre-fork failure 必須留下 durable `BROKER_ABORTED(CRASH_BEFORE_FORK)`，並 replay 為 `BLOCKED / 0`。目前 production path 與手工 ledger fixture 不一致，因此 candidate 不得整合或進真實 CLI canary。

## Bounded Repair

只允許修 `scripts/agy_gemini_v4_broker.py`、`tests/test_agy_gemini_v4_broker.py` 與獨立 Repair evidence。必須在 real `run_single_shot` path 對 OPERATION_CREATED 後、FORK_ATTEMPTED 前的可判定 failure 寫入合法 `BROKER_ATTEMPTED` 與 `BROKER_ABORTED(CRASH_BEFORE_FORK)`，維持 target count 0、`BLOCKED/0`、complete false、resend false；並補 production-path regression，不能只建立手工 ledger。

