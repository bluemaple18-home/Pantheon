---
id: CARD-PANTHEON-G8-V0378-CURRENT-AUTHORITY-READONLY-PROBE-20260824
chain_id: PANTHEON-G8-RULE24-SIGNED-EVIDENCE
role: authority-probe
cycle: 2
status: ready
type: strict_readonly_external_probe
thickness: strict
risk: critical
model: gpt-5.5
reasoning: high
model_reason: current Git/production authority 是 adoption/reset 前硬閘門；操作已限縮為一次只讀 probe。
required_base_ref: main
required_base_sha: 93cd8061a22c9aa78acea36850b88c1c97f4cdb9
production_read_authorized: true
production_mutation_authorized: false
remote_git_read_authorized: true
remote_git_write_authorized: false
canary_authorized: false
ownership:
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0378-CURRENT-AUTHORITY-READONLY-PROBE-20260824-RESULT.md
  - artifacts/fortune_council/four_lane_runtime_execution/g8_v0378_current_authority_readonly_probe_20260824/**
forbidden_scope:
  - 修改 source/tests/config/registry/metadata/既有 evidence/handoff/未追蹤檔
  - fetch/pull/push/tag/branch/ref/credential mutation；remote query 最多一次且只限 origin main
  - production actor/manifest/queue/state/transaction/plist/stage/barrier/launchctl mutation
  - adoption/reset/activation/deploy/canary/schedule/Publisher child
  - 輸出 token、credential、private key、完整環境變數或無關 production data
verification:
  - before/after protected digests相同；remote invocation count=1；JSON parse；git diff --check
  - verdict 僅 AUTHORITY_CURRENT、BLOCKED、UNKNOWN
result_path: artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0378-CURRENT-AUTHORITY-READONLY-PROBE-20260824-RESULT.md
---

# V0378 current authority read-only probe

## 工作名稱 → 正在做什麼 → 現在狀態

V0378 authority probe → 取得 current remote Git 與 production observation → READY / READ-ONLY AUTHORIZED

## Authorized reads

1. Remote Git：只執行一次 `git ls-remote --heads origin main`；禁止 retry、fetch、pull、credential 變更。保存 invocation count、exit、stdout SHA 或遮蔽後錯誤。
2. Canonical locator：唯讀確認 `<repo-root>`、production actor root、runtime manifest、stage root、LaunchAgents root 是否存在且 canonical；不得建立或修補。
3. Production identity：唯讀取得 actor HEAD/clean、manifest actor/source/generation/digest、stage generation/manifest digest/run controls。
4. Runtime status：只用 `launchctl print`/`list` 讀指定 Pantheon labels 的 loaded/PID/last-exit，不 load/unload/kickstart/enable/disable。
5. Reset/phase evidence：唯讀定位現存 reset receipt、phase/parent-run/promotion receipt；不存在即明列 missing。
6. Before/after：對 actor refs/status、manifest、stage、queue/state/transaction tree、live plist與 barriers 做同集合 digest；任一變更固定 `BLOCKED / MUTATION_DETECTED`。

## Formal evaluation

- 沿用既有 collector/reconciler contracts：`scripts.pantheon_g8_production_preactivation` 與 V0370 canonical observation schema；不得新造第二套 truth。
- 新 observation 必須含 contract/edge map/evidence scopes/services、identity、correlation、timestamp與來源 locator。
- remote main、local main、actor HEAD、manifest source/actor與 canonical checkout 必須逐項列出；不以 patch-id 取代 authority。
- Rule24/Rule25 只做 currentness 判斷，不執行 canary或 production workflow。

## Verdict

- `AUTHORITY_CURRENT`：current remote、production identity、canonical locator與 protected tripwire均唯一且可重現。
- `BLOCKED`：明確 drift、缺 current identity、缺 locator、phase/reset receipt不足或 mutation detected。
- `UNKNOWN`：唯一一次 remote query失敗或必要 read不可用；不得 retry。

## Delivery

- 只新增 RESULT＋task-owned machine-readable evidence；單一 commit。
- RESULT：remote SHA、local SHA、actor/manifest/stage identity、phase/reset、tripwire、Rule24/25 currentness、verdict、唯一下一步。
- 不 push、不 production write、不派工、不開下一張卡。
