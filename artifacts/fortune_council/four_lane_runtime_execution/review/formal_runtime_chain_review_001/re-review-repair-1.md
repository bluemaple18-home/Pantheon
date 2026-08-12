# Repair-1 follow-up re-review

- 原 Review commit／Repair base：`6c57f3d9a47a76704acf4f0cfdf5522f48a7685d`
- Reviewed Repair candidate：`12a86f91bc56a3c3566038deb0dc062f1b6a0c4d`
- Candidate parent：`6c57f3d9a47a76704acf4f0cfdf5522f48a7685d`
- Candidate ref：`codex/four-lane-formal-runtime-repair-1-candidate-20260810`
- 範圍：只重驗 `PANTHEON-FORMAL-RUNTIME-001` 與 Repair-1 直接回歸；原 P2 002／003 維持 residual risk，不移動本輪球門。
- Verdict：`REVIEW_NO_GO`
- Blocking finding：`PANTHEON-FORMAL-RUNTIME-001` 仍為 OPEN。
- Production：未授權、未執行；本 re-review 不宣稱 production ready。

## Finding first

### PANTHEON-FORMAL-RUNTIME-001 — P1 — 正式入口已命中，但 dry-run 未封住 queue／state filesystem boundary

- Category：correctness / runtime safety / evidence integrity
- Path：`scripts/agy_content_publisher.py:165`
- Related paths：`scripts/agy_content_publisher.py:174`、`scripts/agy_content_publisher.py:202`、`scripts/agy_content_publisher.py:2865`、`scripts/agy_content_publisher.py:2867`、`scripts/pantheon_content_capability_adapter.py:79`
- Trigger：讓 `PANTHEON_RUNTIME_QUEUE_ROOT` 與 `PANTHEON_RUNTIME_PUBLISHER_STATE_ROOT` 指向 sandbox 外、原先不存在的合法路徑，再呼叫 `formal_capability_preflight("publish", ...)`。adapter 的 contract loader 只驗證 `sandbox_root` 本身，沒有驗證 manifest 的 queue／publisher-state root 必須位於該 sandbox 內。
- Source evidence：`formal_capability_preflight()` 直接信任兩個 environment root，先執行 `mkdir()`，再把它們交給正式 `publish_ready_runs(..., dry_run=True)`。正式 publisher 即使在 dry-run 仍會建立 `state_root/publisher.lock`；transaction path 也會在同一 state root 建立暫存 transaction directory。函式最後固定回報 `production_mutation=False`，沒有以實際 containment／mutation assertion 支撐該欄位。
- Runtime evidence：獨立 `/tmp` harness 在呼叫前觀察到 external queue／state 均不存在；呼叫後兩個目錄與 `external-state/publisher.lock` 均存在，lock size 為 0。相同回傳卻是 `status=PASS`、`boundary_status=idle`、`production_mutation=false`。這直接違反 Repair 卡「sandbox 之外無 filesystem/git mutation」及「不得寫正式 queue/state」契約。
- Positive invocation evidence：獨立 wrapper/call recorder 證實四步確實命中正式函式，順序為 `publish_ready_runs(dry_run=True,push=False,release_gate=False)`、`_isolated_transaction_worktree()`、`_stage_commit_tag_push(push=False,release_gate=False,checked_runner=injected)`、`_stage_commit_tag_push(push=True,release_gate=False,checked_runner=injected)`。四步正式 return 均被檢查後才得到 PASS；tag／push trace 來自注入 Git runner，未寫正式 tag 或 remote。
- Test evidence：`tests/test_pantheon_content_capability_probe.py` 與 `tests/test_agy_content_publisher.py` 合計 126 passed；但現有正向測試由 probe 自己建立 sandbox manifest，沒有注入 sandbox 外 queue／state root，因此未命中此邊界。
- Risk：capability receipt 可以在 caller／manifest 指定的正式 queue 或 publisher state 上留下目錄與 lock，卻宣稱零 production mutation。原 P1 的「正式 invocation + 可證明無正式副作用」只完成前半；若以此 receipt 放行 production canary，evidence 會把真實 control-plane filesystem I/O 誤報為安全 dry-run。
- Minimal fix：在進入任何 `mkdir` 或正式 publisher boundary 前，將 queue／publisher-state（以及 transaction root）嚴格綁定到本次 `sandbox_root` 的 resolved descendants；拒絕 symlink escape、相等／父層／外部路徑。不要固定手寫 `production_mutation=False`；由建立前後 snapshot 或注入 filesystem boundary 的可驗證結果產生。若 public preflight 必須接受環境 root，則 adapter 與 preflight 兩層都要 fail closed。
- Re-review validation：以相同 production public interface 重跑 recorder；sandbox 內四步仍須命中正式 boundary。另以外部 queue、外部 state、symlink escape 各做一例，必須在首次 filesystem I/O 前 BLOCKED，且 before／after snapshot 完全相同；正常 production callers 未注入 `checked_runner` 時仍須使用既有 `_run_checked` default。
- Confidence：high

## Repair regression review

- `6c57f3d..12a86f9` inventory：5 files，515 insertions，31 deletions；production 變更限 `scripts/agy_content_publisher.py` 187-line diff，測試變更限 `tests/test_pantheon_content_capability_probe.py`。
- `git diff --check 6c57f3d..12a86f9`：PASS。
- Release boundary：`_stage_commit_tag_push()` 的 `checked_runner` 預設仍為 `None`，並以 `checked_runner or _run_checked` 保留正常 production default；本輪未發現 tag／remote 或 release SHA 驗證的直接 P0/P1 regression。
- Invocation／fail-closed：正式函式 exception 的既有 Repair 測試通過；call recorder 證明 PASS 不是原先完全自報的 entrypoint 字串。
- 阻擋範圍只限 Repair 自己引入的 sandbox containment 缺口；未建立新 finding ID。

## Verification receipt

- CodeGraph：已在 source decision 前對 formal capability、production boundary、injected Git／checked runner、environment trust 與 release SHA 做 candidate semantic query；indexed source 對齊 `12a86f9…`。
- Targeted tests：126 passed，1 warning，17.83s；JUnit：`re-review-repair-1-targeted.junit.xml`。
- Independent boundary recorder：publish／transaction／tag／push 各實際命中一次正式 boundary；transaction trace 使用 injected `worktree add/remove`，tag／push trace 使用 injected add／commit／tag／push，未執行真實 Git mutation。結構化 receipt：`re-review-repair-1-trace.json`。
- Independent mutation proof：external queue/state `false/false → true/true`，且 `publisher.lock=true`；同次正式回傳仍宣稱 `PASS`、`production_mutation=false`。結構化 receipt：`re-review-repair-1-trace.json`。
- Allowlist：Repair candidate 的 5 個 changed files均在 Repair 卡 allowlist；本 Reviewer 寫入只在原 task-owned review evidence path。
- Safety：未修改 candidate source、tests、installer 或 plist；未執行 launchctl、network、正式 queue/state、tag、push、deploy 或 canary。

## Residual risks（不移動球門）

- `PANTHEON-FORMAL-RUNTIME-002` 與 `PANTHEON-FORMAL-RUNTIME-003` 維持原 P2 residual risk；本輪未重新定級，也不以其阻擋 Repair-1。

## Verdict

`REVIEW_NO_GO`

`PANTHEON-FORMAL-RUNTIME-001` 尚未真正關閉：正式 production functions 已被實際呼叫，但 sandbox containment 缺失使 queue／state filesystem mutation 可在 PASS receipt 下發生。交回主線；本 Reviewer 不自行建立 Repair-2。
