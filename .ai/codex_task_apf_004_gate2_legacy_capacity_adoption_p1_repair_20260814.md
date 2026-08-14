# APF-004-GATE2-LEGACY-CAPACITY-ADOPTION-P1-REPAIR-001

## 正式狀態

- 工作名稱：APF-004-GATE2-LEGACY-CAPACITY-ADOPTION-P1-REPAIR-001
- 正在做什麼：修復 legacy capacity adoption 對 `launchctl print` path 的 prefix/substring 誤判
- 現在狀態：REPAIR_READY_FOR_REREVIEW / LOCAL ONLY / NO PRODUCTION MUTATION
- Current candidate：f614bea8f22663bd40dcee0f5e921d788d679a4e
- Reviewer thread：019ffb96-c9fc-7463-856f-aa37988846df
- Verdict：REVIEW_CHANGES_REQUIRED
- mutation_executed：false

## 唯一 P1

`scripts/install_agy_gemini_coordinator_launchd.sh` 的 legacy capacity adoption path 對 `launchctl print` 的 loaded path 使用 prefix/substring match。若 identity 輸出 `path=<CAPACITY_TARGET>.forged`，可能被誤判為 exact target，讓 activation-only 進入 bootout/bootstrap mutation path。

## 修復契約

- 解析 `launchctl print` 中唯一 `path` 欄位；missing 或 duplicate 直接 reject。
- `path` 欄位必須是嚴格格式：`path = /absolute/path`，不得有 extra whitespace。
- loaded path 與 capacity target 都必須 canonical / normalized absolute。
- prefix、suffix、relative、noncanonical、symlink alias、ambiguous fields 均 fail closed。
- 檢查必須在 adoption marker 與任何 `replace_live_plists` / `bootout` / `bootstrap` 前。
- 不改 normal authority。
- 不放寬 snapshot / owner / mode / running / hash。
- 不改 child I/O。

## Source decision

- CodeGraph：repair worktree 未初始化 `.codegraph`，不可用。
- fallback：限域讀 coordinator installer seam 與直接 tests。

## RED

Command:

```bash
<venv-python> -m pytest -q 'tests/test_agy_gemini_coordinator.py::test_activation_only_legacy_capacity_adoption_blocks_invalid_state_before_mutation[prefix-forged-path]'
```

Observed before fix:

- result：FAILED
- assertion：`mutation_log.exists()` was true
- interpretation：`path = <CAPACITY_TARGET>.forged` 被 prefix match 誤接受，已進入 fake launchctl mutation path。

## 修復摘要

- 新增 `canonical_existing_path()` helper。
- `prepare_legacy_capacity_adoption()` 改為：
  - 先計算 lenient path assignment count，必須剛好 1。
  - 再計算 strict path assignment count，必須剛好 1。
  - strict path 必須為 absolute、存在、非 symlink。
  - loaded path 與 capacity target 都轉 canonical physical path。
  - raw path 必須已 canonical，target 也必須 canonical。
  - canonical loaded path、canonical target path、raw loaded path、raw target path 必須完整相等。
- 保持 adoption marker 在所有上述檢查通過後才建立。

## 驗證摘要

- reviewer exact `<target>.forged` + duplicate path：PASS
- full zero-write negative matrix：PASS
- positive adoption / rollback receipts / normal isolation / existing regressions：PASS
- affected coordinator suite：PASS
- runtime manifest suite：PASS
- static gates：見 evidence。
