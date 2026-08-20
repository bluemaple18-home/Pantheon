# G8 Cycle 17 canonical Python contract repair

## 工作名稱

修復 Cycle 17 promotion plan 的 canonical Python 契約。

## 現況

- Cycle 17 終態：`BLOCKED / NO CANARY`。
- evidence commit：`68fdc5569e`。
- production mutation：`0`。
- deterministic plan 唯一 blocker：`python_executable must use its canonical realpath`。
- 卡片指定：`/Users/mattkuo/Documents/Pantheon/.venv/bin/python`。
- 實際 canonical realpath：`/Users/mattkuo/.local/share/uv/python/cpython-3.12.12-macos-aarch64-none/bin/python3.12`。
- 前者是 symlink；版本仍為 Python `3.12.12`。

## Root question

能否在不放寬 promotion fail-closed 驗證、不改 production runtime、零 push／零 promotion 的前提下，把 Cycle 17 的 target Python 契約改為既可攜又能在執行時鎖定 canonical realpath？

## 任務

1. CodeGraph-first；失敗才限域 `rg`。
2. 讀 Cycle 17 卡、`68fdc5569e` evidence、promotion plan public seam 與相關測試。
3. 判定是 task parameter、card contract 或 source contract 問題；不得把 canonical-realpath check 移除或弱化。
4. 優先最小修正：文件以 `<repo-root>/.venv/bin/python` 表達工具來源，正式 argv 則在 Gate 前鎖定並寫入該 executable 的 canonical realpath、版本與 digest evidence。
5. 若只需修卡，只改 Cycle 17 card 與本卡 evidence；若 source 必須修改，先交 `BLOCKED / SOURCE CHANGE REQUIRED`，不得直接改 source。
6. 跑受影響靜態／單元驗證與 `git diff --check`。
7. 不執行 Gate A、push、promotion、restaging、formal preflight、capacity install、activation 或 canary。

## 可改範圍

- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-REPAIRED-SOURCE-PROMOTION-STAGING-CYCLE-17-20260821.md`
- `.work/CARD-PANTHEON-G8-CYCLE17-CANONICAL-PYTHON-CONTRACT-REPAIR-20260821/**`

## 禁止範圍

- production runtime、actor、manifest、stage、LaunchAgents、queue。
- `origin/main`、tag、publish。
- 任何 Gate A／promotion／activation／canary 執行。
- 放寬 canonical path、identity 或 fail-closed 驗證。

## 驗收

- 明確 verdict：`CONTRACT REPAIRED`、`NO CHANGE NEEDED` 或 `SOURCE CHANGE REQUIRED`。
- exact target Python resolution 契約可執行且不依賴 symlink 作正式 identity。
- production mutation count 必須為 `0`。
- evidence 含檢查、hash、diff scope 與下一拍唯一入口。

