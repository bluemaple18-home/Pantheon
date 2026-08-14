# APF-004-GATE2-ACTIVATION-ONLY-INTEGRATION-001 evidence

## 結論

- status：`INTEGRATION_READY`
- mode：`LOCAL INTEGRATION / NO LIVE MUTATION`
- base：`de13ef0de5d122cbe66831ede20b4a62cc6e37a1`
- approved candidate：`ba4afa33577ae8160057a80124dfc7887fe985d2`
- reviewer verdict：`REVIEW_APPROVED`
- branch：`codex/apf-004-gate2-activation-only-integration-4eda`
- integration worktree：`<temp-integration-worktree>`
- mutation_executed：`false`

## Integration Boundary

既有 integration worktree 含未提交卡與 evidence，且與 candidate 路徑重疊；依監工契約未刪除、覆寫或 stash。整合改在乾淨 temp worktree，從 base 建唯一 promotion branch。

Approved candidate 由兩段 commit 組成：

```text
52ef3394f62d77dcec3983011bd9cf3fb07a85ab fix: add gate2 activation-only mode
ba4afa33577ae8160057a80124dfc7887fe985d2 fix: reject activation-only staged plists in normal activate
```

兩段以 `--no-commit` 完整套入，八個 candidate allowlist 檔案與 `ba4afa3357` content-equivalent，再加入 integration card 與本 evidence，準備合成單一 integration commit。

## Changed Files

- `.ai/codex_task_apf_004_gate2_activation_only_integration_20260814.md`
- `.ai/codex_task_apf_004_gate2_activation_only_p1_repair_20260814.md`
- `.ai/codex_task_apf_004_gate2_activation_only_repair_20260814.md`
- `.ai/evidence/apf_004_gate2_activation_only_integration_001.md`
- `.ai/evidence/apf_004_gate2_activation_only_p1_repair_001.md`
- `.ai/evidence/apf_004_gate2_activation_only_repair_001.md`
- `scripts/install_agy_gemini_coordinator_launchd.sh`
- `scripts/pantheon_content_runtime_manifest.py`
- `tests/test_agy_gemini_coordinator.py`
- `tests/test_pantheon_content_runtime_manifest.py`

## Review Result

未發現阻塞問題。

- activation-only public mode：barrier 與七份 readiness acknowledgement 完成後回 PASS，不 `exec` business child。
- legacy fail-closed：prior-loaded service 缺 valid previous barrier 時，在首次 live plist replacement／bootout／bootstrap 前拒絕並寫 failure receipt。
- normal authority isolation：normal staged aggregate 明確要求 `activation-mode=normal`，拒絕 activation-only token；activation-only live post-check 明確要求 `activation-mode=activation-only`。
- normal success／rollback 路徑維持原行為。

## Tests

Direct coordinator edge matrix：

```text
P1 normal rejects activation-only staged plist before mutation
activation-only positive with zero child I/O
legacy prior-loaded negative before live replacement
normal success
normal rollback matrix
result: 6 passed in 19.02s
```

Targeted runtime expected-mode matrix：

```text
normal aggregate rejects activation-only token
activation-only aggregate requires and accepts activation-only token
barrier-exec activation-only acknowledges without child exec
result: 3 passed in 0.27s
```

Affected coordinator suite：

```text
tests/test_agy_gemini_coordinator.py -k 'installer or aggregate_activation or four_lane_activation or activation_only or legacy_loaded or normal_activate'
result: 31 passed, 113 deselected in 54.58s
```

Runtime manifest suite：

```text
tests/test_pantheon_content_runtime_manifest.py
result: 42 passed in 2.29s
```

## Static Gates

- 三個 installer `bash -n`：PASS。
- DBG scan：PASS，無 matches。
- secret scan：REVIEWED PASS；唯一 keyword match 是 repair evidence 內的掃描命令文字，無 secret value。
- added absolute path scan：REVIEWED PASS；matches 僅為 repo-owned macOS system helper 與 test fixture shell 路徑，無使用者 live path。
- binary scan：PASS；全部為 UTF-8 text 或 text executable。
- `git diff --check`：PASS。

## Safety Boundary

未執行 push、merge、deploy、live install、activate、launchctl mutation、runtime write、外部模型、create、run、select、publish、transaction、tag 或 schedule。`mutation_executed=false`。
