---
id: CARD-PANTHEON-OPEN2-PROVIDER-ADMISSION-CAP-IMPLEMENTATION-20260902
chain_id: PANTHEON-FOUR-LANE-RESIDENT-OPERABILITY-20260902
role: implementation
cycle: 1
model: gpt-5.6-terra
reasoning: high
model_reason: strict core-bounded schema change；native subagent 無 GPT-5.5 跑道，採最近的 Terra high
status: ready
risk: high
---

# OPEN-2 provider admission cap 實作

## 一行契約

在四 lane 共用的既有 production allocator admission transaction 內，建立 Asia/Taipei
每日最多 `102` 次 provider admission 的 durable hard cap；不碰 publication success quota。

## Strict fact gate

- Authority：`scripts/agy_gemini_allocator.py` 的共用 state／lock 與
  `ProductionSlotAdmission.commit()`；Runner 在真實 provider call 前 commit admission。
- 固定 config：production service 必須取得值為 `102` 的 cap；缺失、非整數、非 102、
  state schema/date/count/job identity 損壞均在 provider call 前 fail closed。
- Accounting：以 exact `job_id` 冪等；同 job crash/replay 不重扣，新的第 103 筆拒絕；
  admission 已 commit 即計數，provider 後續失敗不退還。
- 日期：以 allocator admission instant 的 Asia/Taipei 日期計；不得用 host locale、UTC 或
  既有 America/Los_Angeles provider quota reset 冒充。

## Allowlist 與停線

- 可改：`scripts/agy_gemini_allocator.py`、`scripts/agy_gemini_runner.py`、
  `scripts/install_agy_gemini_coordinator_launchd.sh`，及其直接對應 tests。
- 可新增唯一 RESULT：
  `artifacts/fortune_council/four_lane_runtime_execution/RESULT-PANTHEON-OPEN2-PROVIDER-ADMISSION-CAP-IMPLEMENTATION-20260902.md`。
- 若必須修改 manifest、Publisher、Coordinator lifecycle 或新增 state store，停止回
  `BLOCKED_REQUIRED_OWNER_SEAM`。
- 禁止 provider、production runtime／queue／state mutation、真 `launchctl`、publish、
  push、merge、deploy。

## RED → GREEN

1. 先建立 RED：第 102 筆原子成功、第 103 筆在 provider call 前拒絕；同 job replay
   不重扣；跨 Asia/Taipei 午夜重設；malformed／future schema fail closed。
2. 最小 GREEN：延伸既有 allocator state schema／lock transaction，不新增另一份 counter。
3. 覆蓋 Runner crash-after-admission、四 lane 共用 state 與 installer cap projection。
4. 跑 focused allocator/runner/installer tests、受影響 suites、py_compile／bash -n、
   `git diff --check`；RESULT 記錄實際數量與 production mutation 0。
