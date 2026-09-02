---
id: PANTHEON-FOUR-LANE-RESIDENT-OPERABILITY-OPEN-ITEMS-20260902
chain_id: PANTHEON-FOUR-LANE-RESIDENT-OPERABILITY-20260902
role: canonical_open_items
date: 2026-09-02
status: open
---

# Pantheon 四線 resident operability 剩餘缺口

## 已結案與未結案邊界

- `PER_RUN_CORRECTNESS = CLOSED`
- `RESIDENT_OPERABILITY = UNPROVEN`
- `ACTIVE_BEHAVIORAL_GAPS = OPEN-1 + OPEN-2`
- `C_C_T_ACCEPTANCE_PROGRAM = TERMINATED`

本清單不得重新加入 C-C/T 模擬器問題，也不得以 code inference、fixture 或單次
有人監督的 canary 宣稱 resident operability 已結案。

## OPEN-1 — 真實 failure isolation

### 問題

既有正式 retry authority 是否能在無人值守下終止失敗 item、釋放槽位，並讓
既有 selector 選到下一個不同 item。

### 先行工作

先唯讀映射 transport、run/article 與 Publisher 各自擁有的 retry／terminal
authority，並查詢 registry／ledger 的既有歷史紀錄。不得新增 retry counter，
不得先改 production state 製造證據。

### 唯一結案門檻

同一個真實 item 必須完整觀察到下列連續事件：

1. 實際失敗三次，或達到映射後確認的既有正式上限。
2. 實際進入既有 terminal/manual 狀態。
3. 實際釋放其占用槽位。
4. 下一個不同 item 由既有 selector 選出並開始執行。

四項必須屬於同一條可追溯 evidence chain。讀 code 認為「應該如此」、fixture、
Controller 手動指定下一篇，都不能代替真實觀察。

2026-08-26 的相近案例只證明：coordinator 看到歷史 registry `failed: 2` 回
exit 1 時，同一 cycle 仍能 seed/dispatch，亦即單篇失敗沒有停止全域 loop。
該案例沒有觀察到第三次失敗、terminal/manual 與槽位釋放，故不能結案
`OPEN-1`。

### 目前狀態

`OPEN-1_UNPROVEN`。若唯讀歷史 mapping 找不到完整鏈，只能維持此狀態；不得用
推論補足。

## OPEN-2 — 每日 publication 與成本硬上限

### Success quota

以 Asia/Taipei calendar date 為 key：

| Publication class | Daily success quota | Lane mapping |
|---|---:|---|
| `new` | 1 | `new` |
| `rewrite` | 1 | `rewrite` |
| `translation` | 1 | `i18n-new`、`i18n-rewrite` 共用 |
| `total` | 3 | 三個 publication class 合計 |

quota check、admission／reservation 與 publication mutation 必須在既有
Publisher lock 下形成同一個 transaction boundary；以既有 ledger／release
identity 持久化，不新增 state store。transaction admission 時固定
Asia/Taipei 日期；同一 `run_id` 跨午夜仍歸原 admission date。成功只計一次，
失敗釋放 success reservation。

### Crash／replay invariant

- 同一 `run_id` 重放不得重複計數。
- publication 已成功但 ledger 尚未完成的 crash window，不得讓重啟後多放一篇。
- replay 必須先由既有 publication／release identity 辨認已完成 mutation，再原子
  補齊或確認同一筆 quota accounting。
- concurrent workers 不得同時看見相同剩餘額度並各自發布。

### Cost quota

success quota 不限制失敗重試的 provider 成本。`OPEN-2` 另須 daily
admitted-attempt 或 provider-call hard cap；失敗也必須計入。實作前先從既有
call/retry authority 推導最小安全數值並交 Mainline 鎖定。

目前沒有 Owner 核准的數字，因此狀態為
`OPEN-2_COST_CAP_NUMERIC_POLICY_REQUIRED`。在數值、既有持久化 authority 與
fail-closed 測試閉合以前：

- `OPEN-2` 不得標為完成；
- 不得 activation；
- 不得把成本無上限記成 Owner 已接受的 known risk。

### 最小驗證矩陣

後續實作至少須以 RED→GREEN 覆蓋 quota exhaustion、translation shared cap、
total cap、Asia/Taipei 跨日、同 `run_id` replay、publication-success／ledger-write
crash window、concurrency、restart/manual 與成本 cap fail-closed。這是 OPEN-2
驗證，不得擴張固定 go-live preflight。

## 執行順序與 activation 邊界

預設先完成 `OPEN-2` 煞車，再執行固定 preflight；之後是否 bounded activation、
並在真實運行中觀察 `OPEN-1`，由 Owner 另行明示決定。S0 文件化不授權
activation、provider call 或 production mutation。

固定 go-live preflight 只引用 Owner decision 中已鎖定的四項，不在本清單新增或
派生任何第五項：
`artifacts/fortune_council/four_lane_runtime_execution/OWNER-RESCOPE-DECISION-PANTHEON-FOUR-LANE-GO-LIVE-20260902.md`。

