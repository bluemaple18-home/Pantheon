---
id: CARD-PANTHEON-G8-LEGACY-BARRIER-ACTIVATION-REVIEW-2-20260820
chain_id: PANTHEON-FOUR-LANE-PRODUCTION-RECOVERY-20260818
parent_card_id: CARD-PANTHEON-G8-LEGACY-BARRIER-ACTIVATION-REPAIR-2-20260820
role: reviewer
cycle: 2
status: ready
type: source_review
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: Production activation barrier seam 需獨立檢查 fail-closed、identity coherence 與零 mutation，沿用原 Reviewer。
base_sha: f0b1783cb7499267d4ef64ac6b2c7435abd3ba44
candidate_sha: 9343f9035e18e3bec2556ee228f61406c9862665
ownership:
  - .work/CARD-PANTHEON-G8-LEGACY-BARRIER-ACTIVATION-REVIEW-2-20260820/**
forbidden_scope:
  - 修改任何 source、test、production、queue/state/transaction、manifest、plist、barrier 或 git refs
  - production activation、promotion、publisher、launchctl、push、tag
verification:
  - 獨立審查 ancestry、三路徑 allowlist 與 installer seam
  - 重跑新增正向/負向、legacy targeted、coordinator full、runtime/capacity affected tests
  - 所有拒絕路徑在 replace_live_plists、launchctl、child I/O 前 fail-closed
  - git diff --check、candidate tree 不變、production mutation=0
evidence_path: .work/CARD-PANTHEON-G8-LEGACY-BARRIER-ACTIVATION-REVIEW-2-20260820/
---

# G8 legacy barrier activation Review 2

## 工作名稱 → 正在做什麼 → 現在狀態

獨立複審 legacy barrier activation repair → 驗證 candidate `9343f9035e18e3bec2556ee228f61406c9862665` → `READY TO DISPATCH TO ORIGINAL REVIEWER`

## Root Question

Candidate 是否只在 old live 七服務、old barrier、new staged 七服務與 accepted preactivation transition 全部 coherent 時，允許 shared manifest 已 promoted 的 `--activate-only`，並對其他狀態在任何 mutation 前 fail-closed？

## Review Contract

1. 比對 base `f0b1783c...` 到 candidate `9343f903...`；只允許 installer、coordinator test、Repair `.work` receipt 三路徑。
2. Source review 必須確認 old authority 只由 live backup plists、old barrier payload、launchctl identity 重建；不得信任已覆寫的 current manifest 作 old authority。
3. 檢查 mixed old live、PID/running、barrier digest/generation mismatch、missing/malformed barrier、new-stage drift、normal activation 全部在 live replacement、launchctl mutation與 child I/O 前拒絕。
4. 檢查 shell/Python seam 的引數、service set、plist filename/label mapping、canonical path、錯誤輸出與 TOCTOU 風險。
5. 重跑 exact positive/negative、legacy targeted、coordinator full 及 runtime/capacity affected suites；測試前後不得改 production artifact。
6. Reviewer 只可新增本卡 `.work` evidence，不得修改 candidate source/tests。Verdict 只可 `GO` 或 `NO-GO`；P0/P1 或契約缺口即 `NO-GO`。

## Required Verification

```text
/Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest -q \
  tests/test_agy_gemini_coordinator.py::test_activate_only_accepts_coherent_old_live_with_promoted_manifest_path \
  tests/test_agy_gemini_coordinator.py::test_activate_only_promoted_manifest_legacy_barrier_blocks_invalid_transition_before_mutation
/Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py
/Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest -q \
  tests/test_pantheon_content_runtime_manifest.py \
  tests/test_pantheon_content_capacity_guard.py \
  tests/test_pantheon_writer_vnext_runtime_activation_capacity.py
bash -n scripts/install_agy_gemini_coordinator_launchd.sh
git diff --check f0b1783cb7499267d4ef64ac6b2c7435abd3ba44..9343f9035e18e3bec2556ee228f61406c9862665
```

## Stop

- 找到 source/test 問題：輸出 `NO-GO` finding，回原 Repair task；Reviewer 不修。
- 即使 `GO` 也不得 push、promotion、activation、canary、publish、transaction 或 tag。
