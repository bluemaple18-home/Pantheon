# CARD-PANTHEON-G8-LEGACY-SCHEDULE-RESET-CONTRACT-20260821 RESULT

## 狀態

- status: CANDIDATE_READY
- base: `45a86c066b857ac0bf03ad1d91544e9fb2f149f4`
- source ancestor checked: `1f81d4c1886c9e029384fd8d91791fff15ea77ca`
- production mutation: none
- launchctl production mutation: none
- tag / push / deploy: none

## 變更檔案

- `scripts/install_agy_gemini_coordinator_launchd.sh`
- `tests/test_agy_gemini_coordinator.py`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-LEGACY-SCHEDULE-RESET-CONTRACT-20260821-RESULT.md`

## 修復摘要

- `--reset-publisher-activation-only` 保留正式 `publisher-plist-receipt --activation-mode normal` 作為 live Publisher canonical argv、identity、child module 與 service label 驗證。
- reset pre-mutation 現在接受合法 normal scheduled Publisher：`RunAtLoad=true`、`StartInterval=60`、無 `KeepAlive`、無 `--activation-only`。
- reset 仍拒絕非預期 `StartInterval`、`KeepAlive`、running PID、launchctl path drift、identity drift、outer argv drift、child argv drift，且都在 mutation 前 fail closed。
- 成功 reset 仍只替換 Publisher plist，轉為 activation-only terminal one-shot，移除 `StartInterval` / `KeepAlive`，Publisher child invocation 維持 `0`。
- rollback 覆蓋 bootstrap failure 與 postcheck failure，恢復原 scheduled Publisher bytes 與原 loaded/absent 狀態，其他六服務 byte-identical。

## Focused Test Matrix

- scheduled live Publisher absent -> reset PASS，僅 bootstrap Publisher。
- scheduled live Publisher loaded/no-PID -> reset PASS，僅 bootout/bootstrap Publisher。
- terminal one-shot normal live Publisher -> reset PASS，保留既有合法輸入。
- wrong `StartInterval` -> pre-mutation fail closed。
- `KeepAlive` present -> pre-mutation fail closed。
- Publisher launchctl path drift -> pre-mutation fail closed。
- Publisher identity drift -> pre-mutation fail closed。
- Publisher child argv drift -> pre-mutation fail closed。
- Publisher outer argv drift -> pre-mutation fail closed。
- other-service launchctl path drift -> pre-mutation fail closed。
- Publisher running PID / other-service PID -> pre-mutation fail closed。
- bootstrap failure -> rollback scheduled bytes and previous absent state。
- postcheck failure -> rollback scheduled bytes and previous loaded state。
- Publisher-only bounded activation regression set -> PASS。

## 驗證

- `pwd` -> `/Users/mattkuo/.codex/worktrees/f6a7/Pantheon`
- `git rev-parse HEAD` -> `45a86c066b857ac0bf03ad1d91544e9fb2f149f4`
- `git status --short` before repair -> clean
- `git show HEAD:artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-LEGACY-SCHEDULE-RESET-CONTRACT-20260821.md` -> readable
- `git rev-parse 1f81d4c1886c9e029384fd8d91791fff15ea77ca^{commit}` -> readable
- `git merge-base --is-ancestor 1f81d4c1886c9e029384fd8d91791fff15ea77ca HEAD` -> PASS
- `/Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -k 'publisher_terminal_reset'` -> `14 passed, 240 deselected`
- `/Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -k 'publisher_only_bounded_activation'` -> `10 passed, 244 deselected`
- `bash -n scripts/install_agy_gemini_coordinator_launchd.sh` -> PASS
- `git diff --check` -> PASS

## 工具旁路

- `.venv/bin/python -m pytest ...` initially failed because this worktree had no `.venv`.
- `UV_CACHE_DIR=/Volumes/VibeCode/Caches/uv uv run --frozen ...` and `uv pip install ...` both panicked in uv `system-configuration` dynamic store before tests ran.
- Per operator instruction, dependency installation attempts stopped and validation used `/Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest` with cwd kept at this f6a7 worktree. This is recorded as a tool bypass, not a product blocker.

## 未做

- 未執行 production reset / activation / canary。
- 未執行 launchctl mutation against real user LaunchAgents。
- 未修改 Publisher business logic、四 lane routing、manifest schema、Capacity Guard 或 readiness gate。
- 未 tag、push、deploy。
- 未執行 release full suite。

## 未驗

- 未在真實 production LaunchAgents 上執行 reset。
- 未驗證後續 Capacity / Rule25 / exact-run activation。
- 未用 uv runtime 完成 pytest，因 uv 在此環境 panic；已改用既有主工作區 `.venv`。

## 殘餘風險

- 正式機上若 legacy Publisher 的 normal schedule 不是 `StartInterval=60`，reset 會依本卡契約 fail closed。
- 正式 launchctl 輸出的 path 格式若與 bounded fake launchctl 不同，既有 path drift guard 仍可能 fail closed。
- 本修復只覆蓋 repo 內 bounded Repair；production sequence 仍需下一步正式授權後重新執行。

## Candidate Commit

- candidate full SHA: reported after commit in final handoff; embedding this commit's own SHA in a tracked file would change the commit identity.
