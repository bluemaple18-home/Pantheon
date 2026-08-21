---
id: CARD-PANTHEON-G8-RELEASE-TRANSITION-BOUNDED-IMPLEMENTATION-V1-20260821-REVIEW-RESULT
card_id: CARD-PANTHEON-G8-RELEASE-TRANSITION-BOUNDED-IMPLEMENTATION-V1-20260821-REVIEW
chain_id: PANTHEON-G8-RELEASE-CONTROL-PLANE-V1
status: REVIEW_GO
reviewed_commit: 92ffd718b3b771e25dadeaf24cb2ba0c7ca65e50
base_candidate: 3875b0e669e0450ea62a0b14b42b129bd08070c7
prior_review_commit: c7eca18254522554969f9be9518a329a72fdb535
rereview_generation: 1
base_commit: 3bf77c032f85586ddcf00b0b6dfe66bc6110a6dd
date: 2026-08-22
---

# G8 Release Transition independent Review RESULT

## Generation 1 Targeted Re-Review

`REVIEW_GO`

reviewed_commit：`92ffd718b3b771e25dadeaf24cb2ba0c7ca65e50`

Spec axis：`GO`。Repair generation 1 關閉原兩個 P1：edge/action guard 改為 explicit effector/action token exact equality；release observation duplicate evidence 在 state matching 前 fail-closed，完全一致 duplicate 可去重，conflicting normative/path/receipt drift 均不得 `CONVERGED`。

Standards axis：`GO`。未發現 Repair source/test regression；P1 清空。Repair diff 範圍包含 source/tests/Repair RESULT，另包含既有 Repair task card `CARD-PANTHEON-G8-RELEASE-TRANSITION-BOUNDED-IMPLEMENTATION-V1-20260821-REPAIR.md`；本 re-review 未建立新 thread/card，且該 artifact 不改 source/tests/canonical evidence，不列為阻擋 regression。

### Finding Closure

- `G8-REL-REV-001`：CLOSED。`TE-CAPACITY-TO-ACTIVATED + --activate` 與 `TE-CANARY-READY-TO-RUNNING + --activate` 均回 `EDGE_EFFECTOR_MISMATCH`；授權的 `--activate-only` 與 `--activate-publisher-only` 回 `PASS`。
- `G8-REL-REV-002`：CLOSED。Identical duplicate 回 `CONVERGED`；conflicting normative duplicate、path drift、receipt-path drift 均回 `RELEASE_AMBIGUOUS` / `AMBIGUOUS`，且 `matched_state=null`、`next_edge=null`。

### Repair Diff Scope

`git diff --name-status 3875b0e669e0450ea62a0b14b42b129bd08070c7 92ffd718b3b771e25dadeaf24cb2ba0c7ca65e50`：

```text
A artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-RELEASE-TRANSITION-BOUNDED-IMPLEMENTATION-V1-20260821-REPAIR-RESULT.md
A artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-RELEASE-TRANSITION-BOUNDED-IMPLEMENTATION-V1-20260821-REPAIR.md
M scripts/pantheon_g8_production_preactivation.py
M tests/test_agy_gemini_coordinator.py
M tests/test_pantheon_g8_production_preactivation.py
```

No Capacity guard, installer, canonical evidence, implementation RESULT, production artifact, registry, metadata, generated page, sitemap, feed, redirect, tag, push, merge, launchctl, deploy, or canary mutation was introduced by the Repair diff.

### Re-Review Verification

- CodeGraph readiness：ready，578 files / 6618 nodes / 14424 edges.
- Repair RESULT read from `92ffd718b3b771e25dadeaf24cb2ba0c7ca65e50`.
- Regression selector on repair tree：`<main-checkout>/.venv/bin/python -m pytest -q tests/test_pantheon_g8_production_preactivation.py tests/test_agy_gemini_coordinator.py -k "reg_g8_rel_rev or wrong_release_edge"`：`8 passed, 293 deselected in 2.53s`.
- Action replay on repair tree:
  - `TE-CAPACITY-TO-ACTIVATED + --activate`：BLOCKED / `EDGE_EFFECTOR_MISMATCH`.
  - `TE-CAPACITY-TO-ACTIVATED + --activate-only`：PASS.
  - `TE-CANARY-READY-TO-RUNNING + --activate`：BLOCKED / `EDGE_EFFECTOR_MISMATCH`.
  - `TE-CANARY-READY-TO-RUNNING + --activate-publisher-only`：PASS.
- Receipt-path drift replay：BLOCKED / `RELEASE_AMBIGUOUS`; duplicate conflict field `receipt_path`.
- Focused suite on valid git checkout of repair commit：`<main-checkout>/.venv/bin/python -m pytest -q tests/test_pantheon_g8_production_preactivation.py tests/test_pantheon_content_capacity_guard.py tests/test_agy_gemini_coordinator.py`：`353 passed in 431.71s (0:07:11)`.
- Archive-tree focused suite attempt was invalid because the archive had no `.git`; representative failures were `git rev-parse HEAD` returning `fatal: not a git repository`. It was not used for verdict.
- `bash -n scripts/install_agy_gemini_coordinator_launchd.sh` on repair tree：PASS.
- `git diff --check 3875b0e669e0450ea62a0b14b42b129bd08070c7..92ffd718b3b771e25dadeaf24cb2ba0c7ca65e50`：PASS.

## Initial Verdict

`REVIEW_NO_GO`

Spec axis：`NO-GO`。Candidate 大致落實 Contract v1 parser、四種 reconciliation status、SVC-CORE 展開、Capacity inert/no-PID 與 activation 後 restage 測試，但 release safety 的兩個 fail-closed 契約未滿足：edge/action 驗證會誤授權錯誤 action；observation parser 對同一 service/scope 的衝突 evidence 會覆蓋後仍 `CONVERGED`。

Standards axis：`NO-GO`。兩個問題都屬 production transition guard / evidence parser fail-open，為 P1 release safety risk。未改 source、tests 或 canonical evidence；本 Review 只新增此 RESULT。

## Findings

### G8-REL-REV-001

- severity：P1
- category：release safety / correctness
- path:line：`scripts/pantheon_g8_production_preactivation.py:347`
- evidence：`validate_effector_edge` 以 `action not in authority` 做 substring 判斷。Canonical edge map 只授權 `TE-CAPACITY-TO-ACTIVATED` 執行 `--activate-only`，但重播命令回 `PASS`：

```text
<main-checkout>/.venv/bin/python -m scripts.pantheon_g8_production_preactivation --validate-effector-edge --edge-id TE-CAPACITY-TO-ACTIVATED --action=--activate
{"action": "--activate", "edge_id": "TE-CAPACITY-TO-ACTIVATED", ... "status": "PASS"}
```

同樣地，`TE-CANARY-READY-TO-RUNNING` 只授權 `--activate-publisher-only`，但 `--action=--activate` 也回 `PASS`。
- risk：`scripts/install_agy_gemini_coordinator_launchd.sh:74` 會在 mutation 前呼叫這個 guard。若 operator 或 orchestration 傳入 `PANTHEON_RELEASE_NEXT_EDGE=TE-CAPACITY-TO-ACTIVATED` 但實際 action 是 legacy `--activate`，guard 會放行錯誤 action，破壞 `stage -> reset -> Capacity -> activation-only -> restage` 的固定 transition contract。
- minimal fix：將 authority 解析成明確 effector/action token，要求 exact action equality；不要用 substring。為 `--activate` vs `--activate-only`、`--activate` vs `--activate-publisher-only` 加負測。
- test gap：現有 `tests/test_pantheon_g8_production_preactivation.py:397` 只測正向 mapping；`tests/test_agy_gemini_coordinator.py:5047` 只測完全不同 edge/action，未覆蓋 prefix/subcommand collision。
- confidence：high；重播命令直接在 candidate 上證明錯誤 PASS。

### G8-REL-REV-002

- severity：P1
- category：parser fail-closed / evidence ambiguity
- path:line：`scripts/pantheon_g8_production_preactivation.py:290`
- evidence：`observed = {(item.get("service"), item.get("scope")): item ...}` 會讓後一筆 duplicate evidence 覆蓋前一筆。重播在 `ST-TARGET-STAGED` observation 中插入一筆衝突的 live Publisher `activation_mode=activation-only`，同一 service/scope 後面仍有原本的 `normal`；結果仍回：

```text
code=0
reconciliation_status=CONVERGED
matched_state=ST-TARGET-STAGED
divergences=[]
```

- risk：任務卡要求 parser 對 version/ID/缺失/歧義 fail closed，且 current/historical 混用或多 state match 必須 `AMBIGUOUS`。同一 service/scope 的 current evidence 互相衝突是歧義；目前會依輸入順序默默採信最後一筆，使 release reconciliation 可能在 evidence package 有衝突時仍授權 next edge。
- minimal fix：建立 observation index 前偵測 duplicate `(service, scope)`；若 duplicate 完全一致可去重，若任何 normative field/path/receipt 不一致則回 `AMBIGUOUS` 或 `OBSERVATION_INVALID`，並列出全部衝突 evidence path。
- test gap：現有 per-service mismatch 測試只修改單筆 evidence；沒有 duplicate/conflicting current evidence、duplicate path drift、或同一 scope 多來源的 fail-closed 測試。
- confidence：high；最小 fixture 重播直接證明衝突 evidence 被覆蓋並產生 `CONVERGED`。

## Verification

- 完整讀 Review 卡、handoff、五份 canonical evidence、implementation 卡與 implementation RESULT。
- CodeGraph 狀態：bootstrap 已確認 `CONTEXT_DEGRADED/codegraph_scope_unavailable`；本 review 使用 bounded fixed Git object/source confirmation。
- `git diff --check 3bf77c032f85586ddcf00b0b6dfe66bc6110a6dd..3875b0e669e0450ea62a0b14b42b129bd08070c7`：PASS。
- `bash -n scripts/install_agy_gemini_coordinator_launchd.sh`：PASS。
- `<main-checkout>/.venv/bin/python -m pytest -q tests/test_pantheon_g8_production_preactivation.py tests/test_pantheon_content_capacity_guard.py tests/test_agy_gemini_coordinator.py`：`346 passed in 437.17s (0:07:17)`。
- Negative review repros：
  - `TE-CAPACITY-TO-ACTIVATED + --activate` incorrectly returned `PASS`.
  - `TE-CANARY-READY-TO-RUNNING + --activate` incorrectly returned `PASS`.
  - duplicate conflicting service/scope observation incorrectly returned `CONVERGED`.

## Residual Notes

- No production inspection/mutation, launchctl mutation, deploy, canary, tag, push, merge, Repair, Reviewer, replacement, or next card was created.
- Focused tests passing does not offset the two fail-open release safety findings above.
