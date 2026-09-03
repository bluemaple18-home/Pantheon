# RECOVER_MALFORMED_ACTIVATION_ONLY_COHORT — Fixed-Diff Re-review

> Current controlling decision（candidate `1df7f8f4b2`）：`REVIEW_GO`。
> 本文件保留下方所有先前 verdict；舊 `GO`、兩次 `NO_GO` 與 findings 均為 audit trail，不得單獨引用為目前狀態。
> 此決定只接受修補 diff，不構成 production recovery 授權。

## Reviewer role

你是本任務的 Claude Code fixed-diff Reviewer。只做唯讀 review，不得修改任何檔案。

## Review boundary

- Repository：Pantheon
- Base：`38819d03055da029c8a6261567f2fac5a97adc0f`
- Head：`23439e00bfbbb54399379ccb23de16d29ae2e27a`
- 精確 review diff：`38819d03055da029c8a6261567f2fac5a97adc0f..23439e00bfbbb54399379ccb23de16d29ae2e27a`
- 必讀契約：
  - `handoff_20260903_recover_malformed_activation_only_cohort_execution.md`
  - `handoff_20260903_recover_malformed_activation_only_cohort.md`
- 禁止 review 或吸收目前 working tree 的其他 dirty／untracked changes。

## Prohibited actions

- 禁止 Edit、Write、NotebookEdit。
- 禁止 push、merge、deploy、launchctl、activation、canary、publish、tag。
- 禁止 production、provider、network 或外部狀態 mutation。
- 不得把本 review 視為 production recovery 授權。

## Known verification evidence

- Repair-focused coordinator tests：`27 passed, 454 deselected`。
- Capacity guard suite：`69 passed`。
- `bash -n scripts/install_agy_gemini_coordinator_launchd.sh`：PASS。
- `git diff --check 38819d0305..23439e00bf`：PASS。
- Full coordinator suite：`479 passed, 2 failed`。
- 上述兩個 failure 在 base `38819d0305` 可獨立重現，且本 diff 未修改 `scripts/agy_gemini_coordinator.py`，因此屬目標分支既存紅燈，不得誤歸因於本 diff。

## Required review questions

1. 修復是否精確限制於 evidence 鎖定的 malformed seven-service activation-only cohort？
2. 所有 admission drift 是否 zero-mutation fail closed？
3. 是否重用既有 installer、plist generation 與 rollback authority，沒有建立第二套 generator？
4. 是否存在 partial state、rollback blind spot、TOCTOU 或 receipt／fingerprint 完整性問題？
5. Regression 是否證明同一 formal Capacity preflight 可由 RED 轉 GREEN？
6. 是否造成 Capacity guard、Success quota 或 Provider daily guard scope drift？
7. Mainline 最終裁決應為 `REVIEW_GO` 或 `REVIEW_NO_GO`？

## Required output

請只回傳 review，不要寫檔。輸出必須包含：

- `decision: REVIEW_GO | REVIEW_NO_GO`
- `findings`：依 P0／P1／P2／P3；沒有則寫 `none`
- 對 Required review questions 1–6 的逐項 evidence-based answers
- `residual_risks`
- `recommendation`
- 每項 finding 或關鍵判斷引用具體檔案與行號

## Claude Code reviewer response

- Review mode：Claude Code CLI，read-only plan mode；Edit／Write／NotebookEdit／WebFetch／WebSearch 禁用。
- Decision：`REVIEW_GO`
- Blocking findings：`none`（P0／P1／P2 均無）。

### P3 observations

1. Review 卡記錄的 repair-focused command 選到 `27 passed, 454 deselected`；Reviewer 以較窄的 `-k "malformed_cohort or recovers_exact"` 重跑得到 `26 passed, 455 deselected`。兩者總數同為 481，差異來自選樣 expression，不是測試失敗。
2. `scripts/install_agy_gemini_coordinator_launchd.sh` 的 `capacity_binding.before = CLASSIFIER_EMPTY_SET_PID_REQUIRED` 是由 exact before SHA admission 與獨立 classifier regression 綁定的 evidence label，不是 recovery 當下再次量測的欄位。不得在後續卡片中把它誤寫成即時 probe 結果。

### Required questions verdict

1. **Exact cohort：PASS。** `RECOVERY_EXPECTED_HASH_BINDINGS` 對七個 service 綁定 exact blocker-evidence SHA；任一 before SHA 不符即 reject。Fixture 亦檢查正式腳本中的七組 hash 綁定。
2. **Zero-mutation drift：PASS。** Negative matrix 涵蓋 SHA、flag count、separator、Label、plist、identity、generation、manifest、barrier、topology 與 loaded-state drift；transaction root 只會在兩次 admission probe 完全一致後建立。
3. **Existing authority reuse：PASS。** Plist generation、aggregate replace、Capacity preflight 與 `rollback_activation` 均沿用既有 seam；未修改 Capacity classifier，也未建立第二套 generator。
4. **Partial state／rollback／TOCTOU／receipt：PASS。** Snapshot 後與 shared-stage write 前皆有 revalidation；partial replacement failure 會還原 exact seven-service bytes 與 loaded state；rollback fingerprint mismatch 終止為 `ROLLBACK_FAILED`；receipt 有 canonical SHA seal。
5. **Formal Capacity RED→GREEN：PASS。** 獨立 classifier regression 證明 exact malformed fixture 為 PID-required `NO-GO`；成功 recovery regression 再由既有 formal Capacity preflight 得到 PASS。
6. **Guard isolation：PASS。** Fixed diff 只有 installer 與 coordinator tests；Capacity guard、Success quota、Provider daily guard 均未變更，capacity suite 69 tests 全綠。

### Residual risks

- Fixed diff 未包含 committed evidence 子目錄；目前 evidence 由本 review MD、commit 與可重現命令承載。
- Full coordinator suite 的兩個既存 failure 不屬本 diff，但仍應由其他 bounded task 處理，不能併入 production recovery scope。
- 尚未執行任何 live recovery、launchctl、provider 或 production mutation。

### Reviewer recommendation

接受 `23439e00bfbbb54399379ccb23de16d29ae2e27a` 為 Mainline `REVIEW_GO`。本 review 不構成 production recovery 授權。

## Mainline correction after adversarial review

- Previous decision：`ACCEPTED_FOR_PRODUCTION_RECOVERY_AUTHORIZATION_GATE`
- Current decision：`SUPERSEDED_REVIEW_NO_GO`
- Blocking finding：`P1_ROLLBACK_PRE_BOOTOUT_BLIND_SPOT`
- Current production state：`BLOCKED_REPAIR_AND_FIXED_DIFF_REREVIEW_REQUIRED`
- 禁止建立 production recovery execution 卡；必須先修復 P1 並取得新的 fixed-diff `REVIEW_GO`。

### Static evidence

- Script 全域啟用 `set -euo pipefail`：`scripts/install_agy_gemini_coordinator_launchd.sh:2`。
- `STARTED_LABELS=()`：同檔 `:1223`。
- rollback 先迭代 `"${STARTED_LABELS[@]}"`：同檔 `:1253`。
- 對每個 `previous_loaded=1` 的 label 無條件 bootstrap：同檔 `:1273-1284`；沒有綁定「本 transaction 是否真的 bootout」。
- Error trap 在 live plist replace 前生效：同檔 `:1868-1869`。
- Live plist 的 `install`／`PlistBuddy` 可能在 `:1875-1883` 失敗；首個 bootout 要到 `:1885-1897`。
- 現有 partial rollback regression 只在第七次 bootstrap 注入失敗：`tests/test_agy_gemini_coordinator.py:9055-9128`。
- Fake launchctl 的 bootstrap 只 touch loaded marker，不拒絕 already-loaded label：同檔 `:8364-8410`。

### RED reproduction

Command：

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider /private/tmp/test_p1_rollback_pre_bootout.py
```

注入條件：第一份 live plist 已由 `install` 替換後，`PlistBuddy Add :ProgramArguments:16` 失敗；fake launchctl 明確拒絕 bootstrap already-loaded label。

Observed result：

- Test：`FAILED`。
- stderr：`STARTED_LABELS[@]: unbound variable`。
- launchctl mutation log 不存在，因此 `bootout=0`、`bootstrap=0`；七個 loaded marker 仍全部存在。
- 第一份 live coordinator plist 未被還原：before SHA `4fc2626a...`，actual SHA `9f6406d7...`。
- `failure-receipt.json`：缺失。
- `malformed-cohort-rollback-receipt.json`：缺失。
- transaction root：仍存在。

### Root-cause decision

此 P1 成立，而且有兩層：

1. **Immediate failure**：首個 bootout 前 `STARTED_LABELS` 為空，macOS Bash 在 nounset 下展開空陣列使 rollback 本身中止，留下已替換的 live plist、無 rollback receipt。
2. **Latent failure**：即使先修掉空陣列 crash，現有 rollback 仍會對所有 `previous_loaded=1` labels bootstrap，沒有判斷它們是否曾被本 transaction bootout，會產生不必要 mutation 並可能把 rollback 誤標為失敗。

### Required minimal repair

1. 空的 transaction-started／booted-out label collection 在 rollback 中必須安全處理。
2. Durable transaction state 必須明確記錄每個成功 bootout 的 label。
3. Rollback 只對本 transaction 實際 bootout 且原先 loaded 的 labels 執行 bootstrap。
4. 未被 bootout 的原 loaded labels 只 restore exact bytes，並驗證原 loaded identity／topology；不得 bootstrap。
5. 新增首個 bootout 前 live plist replacement failure regression，要求 exact seven plist bytes restored、`bootout=0`、`bootstrap=0`、loaded topology 不變、receipt=`ROLLBACK_COMPLETE`。
6. Fake launchctl 必須拒絕 bootstrap already-loaded label，讓錯誤 mutation 可被測試抓到。

## Claude Code adversarial re-review of P1

- Decision：`CONFIRM_P1`
- Mainline `SUPERSEDED_REVIEW_NO_GO`：確認正確。
- P1 layers：`immediate empty-array crash = YES`；`latent already-loaded bootstrap = YES`。
- 反證結果：無法推翻。

CC 額外確認：

- 本機 `/bin/bash` 為 GNU Bash 3.2.57；`set +e` 不會關閉 nounset。
- `STARTED_LABELS=()` 在 Bash 3.2 下仍會於 `"${STARTED_LABELS[@]}"` 報 `unbound variable`。
- `STARTED_LABELS` 全腳本只有宣告、rollback 迭代、以及 bootstrap 前 append 三處；因此任何 `replace_live_plists` 或 `bootout_previous_services` failure 都可能以空陣列進 rollback。
- Layer 1 會阻止 plist／barrier restore、rollback receipt、failure receipt 與 transaction cleanup。
- Layer 2 沒有任何 `BOOTED_OUT_LABELS` 或 per-label marker；現有 `RECOVERY_BOOTOUT_COUNT` 只有 aggregate count，不能決定每個 label 是否應 re-bootstrap。
- 只修安全空陣列展開不夠；仍必須加入 per-label successful-bootout state，並據此限制 rollback bootstrap。

CC 建議再補一條中段 bootout failure regression：例如第 4 次 bootout 失敗時，只 re-bootstrap 已成功 bootout 的 labels；未 bootout labels 只 restore bytes 與驗證 identity／topology。

## Final failure-state repair and independent re-review

### Fixed candidate

- Base：`23439e00bfbbb54399379ccb23de16d29ae2e27a`
- Head：`1df7f8f4b2`
- Review range：`23439e00bfbbb54399379ccb23de16d29ae2e27a..1df7f8f4b2`
- Repair commits：
  - `b7d20eef80` — `fix rollback before launchd bootout`
  - `96086b033a` — `arm recovery cleanup after transaction creation`
  - `1df7f8f4b2` — `track observed launchd side effects`

### Findings closed during re-review

1. `P1_ROLLBACK_PRE_BOOTOUT_BLIND_SPOT`：以 `BOOTED_OUT_LABELS` 與 per-label durable marker 限制 rollback bootstrap；未被本 transaction bootout 的原 loaded label 只 restore bytes，並以 `launchctl print` 正向驗證仍載入。
2. `P2_TRANSACTION_INITIALIZATION_TRAP_GAP`：transaction root 建立後立即武裝 cleanup handler；`booted-out` 目錄或 admission receipt 初始化失敗會清除 root、寫正確 phase receipt，且可安全重跑。
3. `P1_BOOTOUT_MUTATED_THEN_FAILED`：不以 command return code 推測 topology。bootout 後先 `launchctl print`；若服務確實已卸載，先寫 in-memory／durable state，再傳播原始 return code。
4. 對稱的 bootstrap post-mutation failure：bootstrap 後先觀察實際 loaded state；實際已啟動的 label 先加入 `STARTED_LABELS`，再傳播原錯誤，讓 rollback 能先移除新服務。

### Regression evidence

- Failure-state 核心案例：`7 passed, 479 deselected`。
- 最終 malformed recovery focused selector：`32 passed, 454 deselected`。
- Capacity guard suite：`69 passed`。
- Full coordinator suite（`b7d20eef80`）：`481 passed, 2 failed`；兩個 failure 均已在 base `38819d0305` 重現，且最終兩個追加 commits 只修改 installer failure handling 與對應 regressions。
- Final native reviewer 另跑 8 個聚焦案例：`8 passed in 31.08s`。
- `bash -n scripts/install_agy_gemini_coordinator_launchd.sh`：PASS。
- `git diff --check 23439e00bf..1df7f8f4b2`：PASS。

### Failure-state acceptance matrix

| Failure point | Accepted terminal state |
|---|---|
| Transaction initialization | 原七服務仍 loaded、live bytes 不變、launchctl mutation=0、transaction root 清除、`ACTIVATION_REJECTED`、retry 成功。 |
| Replacement before first bootout | exact seven plist bytes 與 barrier restored、bootout=0、bootstrap=0、七服務逐一 `launchctl print` 成功、`ROLLBACK_COMPLETE`。 |
| Bootout fails before mutation | 只 re-bootstrap 先前三個確實 bootout 的 labels；未 bootout labels 不 bootstrap；最終七服務 loaded。 |
| Bootout mutates then returns nonzero | topology observation 先確認第四個已 unloaded，再記 marker 並傳播原 code；rollback 恰好 bootstrap 四個，transaction 清除，retry 成功。 |
| Bootstrap fails before mutation | failed label 不加入 `STARTED_LABELS`；rollback 移除先前確實 started labels，再依七個 bootout markers 恢復原服務。 |
| Bootstrap mutates then returns nonzero | topology observation 先確認第四個已 loaded，再加入 `STARTED_LABELS` 並傳播原 code；rollback 移除四個新服務後恢復七個原服務，retry 成功。 |

### Independent verdicts

- Reviewer A：native subagent；未讀本文件與其他 reviewer verdict；decision=`REVIEW_GO`；無 P0／P1，列出三項非阻塞 residual risks。
- Reviewer B：Claude Code CLI；禁止 Bash／Edit／Write／Web，未讀本文件與其他 reviewer verdict；decision=`REVIEW_GO`；逐 trap 與逐副作用核對全部六個 failure states，未提出 P0／P1／P2。
- Independence policy：兩份 verdict 均在提交前隔離；沒有用多數決。先前兩次 `REVIEW_NO_GO` 促成新的 RED regressions 與修補，完整保留於本文件。

### Residual risks

- `SIGKILL`／斷電不會執行 ERR trap；殘留 transaction root 會 fail closed，需要人工檢查，不屬本次 bounded recovery 的自動 crash-resume 契約。
- `launchctl print` 非零同時可能代表 absent 或觀察命令故障；現有 rollback verification 會 fail closed，但診斷粒度有限。
- Receipt operation counters 代表已確認的 forward side effects，不代表 invocation 次數或 rollback mutation 總數；消費端不得混用語意。
- Production recovery execution 仍須 Owner 重新明示授權，且執行前須再跑完整 suite／容量 gate；本 review 沒有授權 push、merge、deploy 或 production mutation。

### Final decision

`REVIEW_GO` — 接受 `23439e00bf..1df7f8f4b2` 進入 production recovery authorization gate；目前仍停在 gate 前，未取得 execution authorization。
