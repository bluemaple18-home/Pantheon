---
schema_version: 1
title: Pantheon four-lane activation TEMP plist canonical path repair
date: 2026-08-29
owner: codex-repair-worker
status: RE_REVIEW_REQUESTED
mode: BOUNDED_REPAIR
finding: TEMP_PLIST_CANONICAL_PATH_CONTRACT_GAP
reviewer_decision: GO
target_scope: four-lane activation acceptance preactivation seam
source_allowlist:
  - scripts/install_pantheon_content_capacity_guard_launchd.sh
test_allowlist:
  - tests/test_pantheon_content_capacity_guard.py
result_dir: artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_activation_temp_plist_canonical_path_repair_20260829
---

# 目標

修復四線 activation acceptance 在 capacity guard installer → validator
preactivation seam 的 TEMP plist canonical path contract gap。修復後只能讓
validator 收到 canonical TEMP plist path；不得宣稱四線已啟用、運行或驗收，
production 維持零變更。

# 根因與邊界

- RCA 主因：`TEMP_PLIST_CANONICAL_PATH_CONTRACT_GAP`。
- Reviewer decision：`GO`，僅限本卡 bounded repair。
- 唯一可修改 source：`scripts/install_pantheon_content_capacity_guard_launchd.sh`。
- 優先測試：`tests/test_pantheon_content_capacity_guard.py`；只有測試證據證明
  必要時，才可加入既有 installer 直接測試，且仍不得超出本卡 allowlist。
- Repair 只能在 capacity installer → validator seam 將 TEMP plist
  canonicalize 後傳入 preactivation，或採更窄的 canonical TEMP creation。

# 禁止

- 不得放寬 `shared plist_receipt` 契約。
- 不得修改 Python validator、runtime manifest、publisher、coordinator、lane
  runner 或 aggregate。
- 不得 chmod、chown、symlink production。
- 不得 install、activate、production canary、commit、push、promotion、deploy、
  release、tag 或公開發文。
- 不得建立第二套 registry、FSM、database、canonical writer 或替代 runtime。
- 不得把人工 operator 的成功或既有舊 actor 版本當作四線 activation acceptance。

# TDD 驗收

1. 先建立可穩定重現的 RED-capable RCA harness：exact `/var` alias path 必須
   fail；canonical path 指向同一 inode 時必須可通過。
2. GREEN：installer 在 seam canonicalize TEMP plist，傳入 preactivation 的
   path 必須是 canonical path；canonical 與 alias 必須保持同一 inode 語意。
3. Negative regression 必須維持 RED：uid 不符、mode 不符、symlink path，及
   非 canonical／非預期 path 不得被放行或被 receipt 掩蓋。
4. 跑 normal stage 與 recovery stage 的受影響既有測試；不得以單一狀態文案、
   projection receipt 或舊 production evidence 取代 runtime 證據。
5. 執行 RCA harness、受影響測試、`py_compile`、`bash -n` 與 `git diff --check`。
6. 以明確檢查證明 production bytes written = `0`；任何 production mutation
   均為 NO-GO。

# 交付格式

- 結果檔：
  `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_activation_temp_plist_canonical_path_repair_20260829/RESULT.md`
- RESULT 狀態固定為：`RE_REVIEW_REQUESTED`。
- RESULT 必須記錄 RCA、RED/GREEN、negative regressions、normal/recovery
  stage、靜態檢查、`git diff --check`、production bytes=0，以及未執行
  production/install/activate/canary/commit/push 的證據。

# 吸收界線

- `why_not_less`：只修 canonicalization seam 不足以讓 validator 接收正確
  identity；不修則 exact `/var` alias 仍會阻斷 preactivation。
- `why_not_more`：validator、manifest、publisher、coordinator、runner、
  aggregate 與 shared receipt 均非根因；擴大修改會改變未驗證的 activation
  contract，超出 Reviewer GO。
- `do_not_absorb`：不吸收任何 production activation、四線 canary、provider
  呼叫、權限／所有權變更、symlink workaround、替代 canonical writer 或新
  governance／runtime subsystem。

