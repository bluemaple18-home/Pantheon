---
id: CARD-PANTHEON-OPEN2-QUOTA-SEAM-MAPPING-20260902
chain_id: PANTHEON-FOUR-LANE-RESIDENT-OPERABILITY-20260902
role: research
cycle: 1
status: ready
risk: medium
---

# OPEN-2 quota seam 與成本上限唯讀 mapping

## 目標

在不改產品碼的前提下，以 CodeGraph 加原始碼確認：

1. 既有 Publisher lock、publication/release ledger 與各 publication transaction 的共同 admission seam。
2. `new`、`rewrite`、`i18n-new`、`i18n-rewrite` 從 selection 到 publication 的 provider-call／attempt authority、重試層與持久化位置。
3. 可由既有 durable authority 表達且不新增 state store 的最小 daily cost-cap 計數單位，並提出有證據的數值候選。
4. 同一 `run_id` crash replay、跨午夜 admission date、concurrency 與 publication-success／ledger-write crash window 的最小 implementation／test seams。

## 固定政策

- Asia/Taipei daily success quota：`new=1`、`rewrite=1`、`translation=1`、`total=3`；兩條 i18n lane 共用 translation。
- admission date 於 transaction admission 固定；同一 `run_id` 跨午夜仍歸原日。
- success quota 與 daily cost cap 是兩個獨立上限；失敗不扣 success quota，但必須扣 cost cap。
- quota 判定與 publication mutation 位於既有 Publisher lock boundary；沿用既有 ledger／release identity，不新增 database、registry、ledger、FSM 或第二套 runtime。
- 尚未由 Mainline 鎖定 cost-cap 數值前，不得改產品碼或宣稱 OPEN-2 可 activation。

## Allowlist

- 只新增本卡與：
  `artifacts/fortune_council/four_lane_runtime_execution/RESULT-PANTHEON-OPEN2-QUOTA-SEAM-MAPPING-20260902.md`
- 可唯讀 `scripts/`、`tests/`、production plist/config 的 repo 版本與既有 evidence。
- 禁止修改 source、tests、config、runtime、queue、state、ledger、plist、Git refs 或外部服務。

## RESULT 必填

- graph query 與原始碼確認的 exact symbols／lines。
- 四條 lane 的 provider-call／attempt 流程與既有 retry owner；不得把 transport retries、run attempts、Publisher retries混為一談。
- cost-cap 計數單位與數值候選；列出推導、最壞情境、`why_not_less`、`why_not_more`、`do_not_absorb`。
- success quota 的共同 transaction seam，或明確 `BLOCKED_REQUIRED_OWNER_SEAM`。
- crash/replay 與日期 attribution 的最小測試矩陣。
- 結論只能是 `READY_FOR_MAINLINE_NUMERIC_DECISION` 或 `BLOCKED_REQUIRED_OWNER_SEAM`，不得實作。
- `git diff --check`、`git status --short`、production mutation/provider/launchctl：`0/NOT_RUN`。
