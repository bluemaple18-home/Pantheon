# APF-004-GATE2-LEGACY-CAPACITY-ADOPTION-INTEGRATION-001

## 目標

把 Reviewer-approved legacy capacity adoption repair chain
`f614bea8f22663bd40dcee0f5e921d788d679a4e`、
`b7a7470834ecab4dfc9d998955781e636fa5ce7d`，以
`e83ca791d0b86287e8e3a33c29f12f9cb2b7c6d0` 為 parent，整合成單一 local
promotion commit。

## Allowlist

- `scripts/install_agy_gemini_coordinator_launchd.sh`
- `tests/test_agy_gemini_coordinator.py`
- `.ai/codex_task_apf_004_gate2_legacy_capacity_adoption_repair_20260814.md`
- `.ai/codex_task_apf_004_gate2_legacy_capacity_adoption_p1_repair_20260814.md`
- `.ai/evidence/apf_004_gate2_legacy_capacity_adoption_repair_001.md`
- `.ai/evidence/apf_004_gate2_legacy_capacity_adoption_p1_repair_001.md`
- `.ai/codex_task_apf_004_gate2_legacy_capacity_adoption_integration_20260814.md`
- `.ai/evidence/apf_004_gate2_legacy_capacity_adoption_integration_001.md`

## 禁止範圍

- 不 push、merge、deploy 或改 origin/main。
- 不讀寫 production runtime、manifest、plist、stage、queue、state 或 barrier。
- 不執行 launchctl mutation、external model、create、run、select、publish、transaction、tag、schedule 或發文。
- 不刪除、覆寫或 stash 其他 worktree 的 card／evidence。
- 不改變 approved repair 語意。

## 驗證計畫

1. 以 `--no-commit` 套入兩個 approved commits，驗證 source、test、repair cards、repair evidence 與 repair tip content-equivalent。
2. 重跑 reviewer exact edge、targeted 23、affected coordinator 48（113 deselected）、runtime 42。
3. 跑三 installer `bash -n`、DBG／secret／跨機 path／binary gates、`git diff --check` 與 `git show --check`。
4. 比對 normal authority 與 activation-only child I/O 邊界未改變。

## 交付

結果只回 `INTEGRATION_READY` 或 `BLOCKED`，附 exact SHA、parent、worktree、changed files、測試數與 `mutation_executed=false`。
