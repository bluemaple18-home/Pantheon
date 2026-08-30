---
schema_version: 1
title: Pantheon four-lane legacy brief compatibility repair
date: 2026-08-30
owner: codex-repair-worker
status: RE_REVIEW_REQUESTED
mode: BOUNDED_REPAIR
finding: LEGACY_BRIEF_CROSS_VERSION_CONTRACT_GAP
reviewer_decision: GO
source_allowlist:
  - scripts/agy_multilingual_pipeline.py
test_allowlist:
  - tests/test_agy_multilingual_pipeline.py
evidence_root: artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_legacy_brief_compatibility_repair_20260830
---

# 目標

修復 legacy brief 跨版本相容性的 deterministic contract gap，讓既有
`i18n-rewrite` brief 能安全進入 canonical 四欄 validator；不得修改
production brief，且 production bytes 必須維持不變。

# RCA 與唯一邊界

- 根因：`LEGACY_BRIEF_CROSS_VERSION_CONTRACT_GAP`。
- Reviewer：`GO`，僅限本張 bounded Repair。
- 唯一 source allowlist：`scripts/agy_multilingual_pipeline.py`。
- 唯一 test allowlist：`tests/test_agy_multilingual_pipeline.py`。
- 唯一 evidence root：
  `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_legacy_brief_compatibility_repair_20260830/`。
- 若無法在上述 1 source + 1 test 內建立可信 lane binding，結果必須為
  `BLOCKED`，不得擴大範圍或採取猜測性相容。

# 最小 deterministic compatibility

1. 只接受 exact historic extra key `lane`。
2. `lane` 必須等於 caller／brief contract 已授權的 expected lane
   `i18n-rewrite`；不得接受任意 lane。
3. 若現有 function 沒有 lane context，必須選用更窄、既有且 trusted 的
   context seam 取得 expected lane；禁止忽略 lane、以輸入 lane 自我授權，或
   以 generic fallback 綁定。
4. 通過 binding 後，normalize 成 canonical 四欄，並沿用既有 validator。
5. unknown extra key、lane mismatch、lane type drift，以及 missing canonical
   fields 必須繼續 RED／fail-closed。

# 禁止

- 不手改 production brief、queue、state、registry 或任何 runtime artifact。
- 不新增 generic allowed extras、union schema、migration、registry 或 FSM。
- 不修改 coordinator、runner、publisher 或其他 source/test。
- 不呼叫 provider，不 install、activate、canary、promotion、deploy、publish、
  release、tag、commit 或 push。
- 不以既有成功狀態、projection receipt、狀態文案或舊版本驗收取代 runtime
  lane-binding evidence。

# TDD 驗收

- 建立 exact 3-fixture isolated harness，先取得 RED，再取得 GREEN：
  1. historic brief：只含 exact extra `lane=i18n-rewrite`，應 normalize 並
     通過既有 validator；
  2. canonical brief：四欄完整、無 extra，行為維持既有成功路徑；
  3. equivalent legacy/canonical fixture：證明 normalize 後 canonical 四欄
     語意一致，不新增任意欄位。
- Negative cases 必須維持 RED：unknown extra key、lane mismatch、lane 非字串
  或其他 type drift、任一 canonical field missing。
- 若無可信 lane context，isolated harness 必須明確輸出 `BLOCKED`，不得將
  「忽略 lane」當成 GREEN。
- 執行 `tests/test_agy_multilingual_pipeline.py` 既有 suite、必要的
  `py_compile`，以及 `git diff --check`。
- 收集 normal 與 compatibility/recovery stage 證據至唯一 evidence root；
  production bytes written 必須為 `0`。

# 交付契約

- 只允許產生本 Repair 卡及唯一 evidence root 下的結果證據；不得產生其他
  source、test 或 production 變更。
- 結果須明確標示 `RE_REVIEW_REQUESTED` 或因 lane binding 不可信而標示
  `BLOCKED`，並列出 RED→GREEN、negative regression、既有 suite、靜態檢查、
  production bytes=0 與禁止動作證據。

# 吸收界線

- `why_not_less`：只保留 exact `lane=i18n-rewrite` 並沿既有 validator，才能
  修復歷史 brief 的跨版本欄位差異，同時證明 lane identity 未被放寬。
- `why_not_more`：coordinator、runner、publisher 與 schema migration 並非
  已證明根因；擴大會改變 runtime contract，超出 Reviewer GO。
- `do_not_absorb`：不吸收任意 lane compatibility、generic extras、union／
  migration、registry／FSM、production brief 修補或新的 canonical writer。

