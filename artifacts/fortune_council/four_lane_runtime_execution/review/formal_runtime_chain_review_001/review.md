# 4lan 正式 Runtime 候選獨立審查

- Reviewed base：`f31ef017170c69543528708fd1314dc87ff7528a`
- Reviewed candidate：`c61491e748acad43e44e73f7eabbc320dcbaa532`
- Candidate parent：`f31ef017170c69543528708fd1314dc87ff7528a`
- Diff：87 files，4,646 insertions，201 deletions
- Verdict：`REVIEW_NO_GO`
- Blocking findings：`PANTHEON-FORMAL-RUNTIME-001`
- Production：未授權、未執行；本審查不宣稱 production ready。

## Findings

### PANTHEON-FORMAL-RUNTIME-001 — P1 — Publisher capability 鏈以手寫 PASS 取代正式執行入口

- Category：correctness / evidence integrity / test gap
- Path：`scripts/pantheon_content_capability_adapter.py:215`
- Related path：`scripts/agy_content_publisher.py:110`
- Trigger：執行正向 capability probe 的 `select → publish → transaction → tag → push`。
- Source evidence：adapter 的 publisher 五步全部只呼叫 `formal_capability_preflight()`。該函式只驗證 run ID、填入 `status=PASS`、`validation_mode`／`transaction_mode`，tag／push 只組裝 `release_git_plan()`；未呼叫正式 `publish_ready_runs()`、`_isolated_transaction_worktree()` 或 `_stage_commit_tag_push()`。
- Runtime evidence：將上述三個正式函式替換為 call recorder 後，五個 capability 仍全數回 `PASS`，而 `actual_calls=[]`。已提交的正向 receipt 也只列 `formal_capability_preflight`、normalizer、capacity preflight 或 release plan。
- Test evidence：`tests/test_pantheon_content_capability_probe.py:28` 只要求 `production_entrypoints` 非空、subprocess return code 為 0；`tests/test_pantheon_content_capability_probe.py:124` 只驗 transition failure 會向外傳遞，沒有證明正式 publisher／transaction／release 函式被呼叫。
- Risk：FR-001／SC-001 的核心證據可在完全未進正式 publisher transaction path 時成功；coordinator 到 publisher、transaction、tag、push 的「正式鏈」因此仍是模擬 receipt。這會把未驗證的 production release boundary 誤標為已關閉。
- Suggested fix：讓薄 adapter 進入可注入 runner、確保無正式副作用的 production 公開入口；publish 至少實際呼叫 `publish_ready_runs(..., dry_run=True, exact_run_ids=...)`，transaction／tag／push 必須進正式 isolated-worktree／release boundary，而不是只回 command plan。trace 應由實際 invocation 產生，不能由函式手寫 `called_entrypoints`。
- Re-review validation：對 production 公開入口加 wrapper/call recorder，斷言正式函式的實際 call count、參數、return code 與無 filesystem/git mutation；正負例均須命中相同 production interface。
- Confidence：high

### PANTHEON-FORMAL-RUNTIME-002 — P2 — Actor-recovery full-suite 分類無法證明候選行為

- Category：evidence integrity / test gap
- Path：`artifacts/fortune_council/four_lane_runtime_execution/evidence/formal_runtime_chain_001/evidence-index.md:9`
- Related path：`tests/test_pantheon_content_actor_recovery.py:41`
- Trigger：把 full-suite 的三個 actor-recovery failure 分類為「與本卡無關」。
- Source evidence：候選實際修改 `scripts/pantheon_content_actor_recovery.py`，因此 evidence 中「所涉 production 檔均未被本卡修改」不正確。
- Runtime evidence：原 worktree 的三個測試先在 helper 的 local `git push` 被缺少 `.venv/bin/python` 的 pre-push hook 擋下。將 base 與 candidate 分別放入 clean isolated repository、提供相同 `.venv` 並移除該 hook 影響後，兩邊皆在 helper 的 `git commit -qm 'repair-2 fixture'` 以 `nothing to commit` 失敗，仍未進 actor-recovery production path。
- Risk：目前可判定這三個 failure 不是 candidate production path 的可重現 regression，但也沒有驗證 candidate 對 `_provision_and_preflight()` 新增的 runtime identity 參數；full-suite receipt 不能作為該修改已通過的證據。
- Suggested fix：讓 fixture 從固定舊 snapshot 建 source repo，再套入 candidate repair paths，或在測試內建立 deterministic commit 差異；base/candidate 使用相同 hermetic hook／dependency 條件重跑。
- Re-review validation：clean candidate 上三個 actor-recovery scenario 必須真正走到 `recover_actor()`，並與 base 以同一 harness 比較。
- Confidence：high

### PANTHEON-FORMAL-RUNTIME-003 — P2 — Rollback 動態測試未製造 control-plane identity mismatch

- Category：test gap / operations
- Path：`tests/test_agy_gemini_coordinator.py:2829`
- Related path：`scripts/install_agy_gemini_coordinator_launchd.sh:316`
- Trigger：執行 `test_four_lane_activation_failure_restores_previous_plists_and_loaded_state` 的 rollback 正負例。
- Source evidence：fake `launchctl print` 只輸出 `pid = 4242`，但 production installer 的 `normalize_control_identity()` 明確移除 pid；正規化後 expected／actual identity 都是空內容。`rollback_fail_at=4` 的 `ROLLBACK_FAILED` 來自 bootstrap failure，不是 control identity mismatch。`validate_rollback_identities()` 的 Python 測試則只比較 synthetic dict，shell rollback 不呼叫該函式。
- Risk：SC-004 的 shell production path 雖有 byte comparison，測試沒有證明「重新載入成功但實際 identity 漂移」會 fail closed。
- Suggested fix：fake `launchctl print` 應輸出不會被 normalize 移除的穩定 ProgramArguments／EnvironmentVariables identity，並在 rollback 後對一個 label 製造漂移；另保留完整一致的成功案例。
- Re-review validation：相同 shell installer path 下，一致 identity 必須 `ROLLBACK_COMPLETE`，任一 label 穩定 identity 漂移必須 `ROLLBACK_FAILED`。
- Confidence：high

## Spec axis

- FR-001：FAIL。Publisher／transaction／tag／push 未進正式 production public interface；`PANTHEON-FORMAL-RUNTIME-001` 阻擋。
- FR-002：PASS（source + targeted tests）。七個 label 的 runtime environment、manifest digest、runtime identity digest、generation 與 root 在 tick 前驗證；coordinator、lane runner、publisher、guard 均在主要 queue/state mutation 前呼叫驗證。
- FR-003：PARTIAL。7/7 ACK/barrier 與 early-start fail-closed 有實作及測試；rollback source 有 loaded identity byte comparison，但動態 mismatch 測試缺口見 `PANTHEON-FORMAL-RUNTIME-003`。
- SC-001：FAIL，隨 FR-001 阻擋。
- SC-002：PASS，七服務 mismatch matrix 通過。
- SC-003：PASS，6/7、stale barrier、early-start 均 fail closed。
- SC-004：PARTIAL，implementation 存在但 production shell mismatch scenario 未被驗證。

## Standards axis

- Candidate lineage、parent、required base ref 一致。
- `git diff --check` 通過；87-file exact inventory 已保存於 `changed-files.txt`。
- 三個 installer `bash -n` 通過；四個 plist template `plutil -lint` 通過。
- 受影響 targeted suite 241 passed；actor-recovery fail-closed unit 1 passed，合計 242 passed。
- Repository full-suite 不能視為綠色：環境缺 Playwright；排除此 collection blocker 的既有 receipt 仍有 5 failures，其中 actor-recovery 三例的「unrelated」分類不成立為完整候選證據。

## Testing gaps

- Publisher capability tests 沒有 invocation assertion，無法分辨正式呼叫與手寫 entrypoint 字串。
- Actor-recovery 的三個主要 scenario 在 clean candidate 上未進 production path。
- Rollback shell test 未注入可存續 normalization 的 control-plane identity drift。

## Residual risks

- 本審查未執行 launchctl、正式 queue、network、tag、push、deploy 或 production canary；只能接受隔離 source/test evidence。
- `review-orchestrator` 在 materialized Review 卡之後執行，只看見當時 working-tree 的兩個 reviewer 檔案；其 schema/routing 有採用，但 candidate 規模以固定 commit range 重新盤點為 87 files。

## Verdict

`REVIEW_NO_GO`

存在一個可重現 P1：`PANTHEON-FORMAL-RUNTIME-001`。交回主線建立唯一 Repair-1；本 Reviewer 不自行開 Repair。
