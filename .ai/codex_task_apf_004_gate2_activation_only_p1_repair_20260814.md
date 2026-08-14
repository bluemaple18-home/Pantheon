# APF-004-GATE2-ACTIVATION-ONLY-P1-REPAIR-001

## 正式狀態

- 工作名稱：APF-004-GATE2-ACTIVATION-ONLY-P1-REPAIR-001
- 正在做什麼：修復 normal activate 接受 activation-only authority
- 現在狀態：REPAIR_READY_FOR_REREVIEW / NO LIVE MUTATION
- Reviewer：019ffb96-c9fc-7463-856f-aa37988846df
- Verdict：REVIEW_CHANGES_REQUIRED
- Base：de13ef0de5d122cbe66831ede20b4a62cc6e37a1
- Candidate：52ef3394f62d77dcec3983011bd9cf3fb07a85ab
- mutation_executed：false

## 唯一 P1

normal `--activate` 若 staged plist `ProgramArguments` 含 `--activation-only`，既有 `plist_receipt` / aggregate preflight 會接受，可能造成 normal activation 不跑 business child 卻回 activation completed。

## 契約邊界

- 只修此 P1，不擴 scope。
- 先加 RED：normal `--activate` + activation-only staged plist，必須在首次 live replacement / bootout / bootstrap 前 fail-closed，零 fake launchctl mutation。
- aggregate / plist validation 明確接收 expected activation mode。
- normal staged preflight 預設拒絕 activation-only token。
- 只有 activation-only 路徑注入後的 live post-check 可允許 activation-only token。
- activation-only positive、legacy negative、normal success / rollback 均不得退化。
- 禁止 live install / activate / launchctl、runtime write、push / deploy、external model、create / run / select / publish / transaction / tag / schedule。

## Source decision

- CodeGraph：此 worktree 未初始化 `.codegraph`，查詢失敗。
- fallback：限域 `rg` 只查 runtime manifest helper、coordinator installer、直接 tests。

## 可證偽假說

- 假說：P1 root cause 是 aggregate / plist preflight 沒有 expected activation mode；若 normal mode preflight 拒絕 `--activation-only`，reviewer edge 應在 `aggregate_preflight` fail-closed，且不產生 fake launchctl mutation。

## RED

Command:

```bash
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py::test_normal_activate_rejects_activation_only_staged_plist_before_mutation
```

Observed before fix:

- result：FAILED
- assertion：`mutation_log.exists()` was true
- interpretation：normal `--activate` 未在 aggregate preflight 擋下 staged activation-only token，已進入 fake launchctl mutation path。

## 修復摘要

- `plist_receipt()` 新增 `expected_activation_mode`。
- `aggregate_plist_preflight()` 新增 `expected_activation_mode` 並傳入每個 plist receipt。
- aggregate CLI 新增 `--activation-mode normal|activation-only`，預設 `normal`。
- coordinator staged aggregate preflight 明確使用 `--activation-mode normal`。
- coordinator live aggregate post-check 依 `--activate-only` / normal action 傳入對應 mode。
- normal mode 拒絕 barrier side `--activation-only`；activation-only live post-check 要求該 token 存在。

## GREEN / Regression

- P1 edge GREEN：`1 passed`
- activation-only positive + normal P1 edge targeted：`2 passed`
- runtime activation-mode targeted：`2 passed`
- prior activation-only / legacy / normal regression：已跑，結果見 evidence。
- affected coordinator suite：已跑，結果見 evidence。
- runtime manifest suite：已跑，結果見 evidence。

## Final gates

- 三 installer `bash -n`
- DBG / secret / path / binary scan
- `git diff --check`
- 單一 allowlist commit

結果：PASS / REVIEWED PASS。詳見 `.ai/evidence/apf_004_gate2_activation_only_p1_repair_001.md`。
