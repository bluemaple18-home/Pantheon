---
id: PANTHEON-C-C-T-SINGLE-WORKLOAD-OWNER-ARCHITECTURE-ROOT-20260901
status: CANDIDATE_READY_FOR_INDEPENDENT_REVIEW
type: architecture_root
thickness: strict
source_sha: 4e68b28ed031bddafa898905880c68982944730b
supersedes_blocked_chain: PANTHEON-C-C-T-OWNER-RECEIPT-PROVENANCE
production_authorized: false
launchctl_authorized: false
gate_d_e: NOT_AUTHORIZED
---

# C-C/T 單一 workload owner 架構根

## 工作名稱 → 正在做什麼 → 現在狀態

- 工作名稱：C-C/T 單一 workload owner 架構根
- 正在做什麼：在隔離測試內關閉 production home authority 與 launchd／Controller 雙重 workload execution authority。
- 現在狀態：`CANDIDATE_READY_FOR_INDEPENDENT_REVIEW`；已完成離線實作與 bounded 驗證，尚未取得外部 `REVIEW_GO`。

## Implementation closeout

- 結論：`CANDIDATE_READY_FOR_INDEPENDENT_REVIEW`。
- RED evidence：已新增並執行 S1 forged `HOME` subprocess test；已新增並執行 S2 public `run_once()` launchd-child single-owner test；Mainline 退件後另補 async stdout bounded wait 與 preexisting `steps` symlink fail-closed RED。
- Additional external finding：`CCT-AR-P1-PREACTIVATION-TOKEN-DEADLOCK` RED 證明 baseline plist 若在 activation ACK 前注入不存在的 activation token，真 `barrier-exec` subprocess 會回 `78` 且不寫 ACK；GREEN 改為 baseline activation-only plist 不帶 token，barrier activation 後的 step plist 才帶 token。
- Additional P2-1：舊 `_execute_schedule()` direct workload executor 已固定 fail-closed，避免日後重新接回 Controller direct schedule alternate executor。
- Second-NO_GO Repair：`CCT-AR-P1-PUBLIC-WAIT-CALLBACK-OWNER-INJECTION` RED 證明 public `run_once(..., monotonic/sleep=...)` 仍可進入 formal launch path；GREEN 移除 formal public wait callback 參數，內部等待只走 module-private `_monotonic()` / `_sleep()`。
- Second-NO_GO Repair：`CCT-AR-P1-SEVEN-SERVICE-POST-BARRIER-AUTHORITY-INCOMPLETE` RED 證明缺一份、錯 label、錯 digest、未完成 baseline activation completion 都可 PASS；GREEN 要求 post-barrier 7/7 exact activation-only `PASS` stdout 後才進入 baseline bootout。
- Second-NO_GO Repair：`CCT-AR-P1-STEP-PARENT-SYMLINK-PATH-ESCAPE` RED 證明 generation parent symlink/external、inode replacement、production symlink 會在 block 前造成 step mutation；GREEN 沿用 `TrustedSandboxDirectoryAuthority` / `path_identity`，render pin generation dir identity，step filesystem mutation 以 dirfd/no-follow relative write 完成。
- Internal zero-write Repair：A RED 證明 preseeded/prebarrier exact baseline `PASS` stdout 可越過 baseline authority；GREEN 在任何 launch 前要求 baseline stdout/stderr 不存在，且 completion stdout/stderr 必須是 canonical owner-safe regular file、strict generation descendant、ctime/mtime 晚於 barrier。
- Internal zero-write Repair：B RED 證明 caller 可同步偽造 mutable `rendered['plist_generation_identity']` 後寫 step；GREEN 移除 formal rendered identity authority，由 `run_once` 自行 capture generation identity 並以 local variable 傳入 schedule/step。
- Internal zero-write Repair：C RED 證明 step failure cleanup 會 follow generation symlink 刪除 external allowed filename；GREEN 將 step/run final cleanup 改為 pinned identity + acceptance-root/generation-root anchored `TrustedSandboxDirectoryAuthority` no-follow relative cleanup，identity drift 時不 follow，只記 residue/teardown failure。
- Follow-up Repair：RED 證明真 launchd 於 pre-barrier 建立空 `StandardErrorPath` 時，過嚴 timestamp rule 會誤擋；GREEN 改為只要求 stdout content ctime/mtime 晚於 barrier，stderr 只驗 canonical owner-safe regular + exact empty。
- Follow-up Repair：RED 證明 broken baseline output symlink 會被 `Path.exists()` 視為不存在而越過 prelaunch absence；GREEN 改為以 `fs_authority.path_identity()` / lstat 語意檢查，任何 regular/symlink/broken symlink/other prelaunch output 都 fail closed。
- GREEN summary：production LaunchAgents authority 改由 OS UID record；baseline disposable services 改 activation-only且 pre-activation 不帶 token；formal Controller 僅持有 private wait primitives；baseline 七服務 post-barrier completion 收齊且 stdout 具 barrier 後 filesystem provenance、stderr canonical empty 才 bootout；非 Publisher workload 改為 immutable schedule 派生的 acceptance-local step plist serial launch/read-back；step plist I/O 與 cleanup 由 pinned generation directory authority 保護；Publisher plan-only dry-run保留且測試證明單次 owner function呼叫。
- 驗證：focused C-C/T `50 passed`；runtime/runner affected `118 passed`；coordinator targeted `7 passed`；`py_compile` 通過；`git diff --check` 通過；DBG scan 無 debugger/debug residue，僅命中合法測試 child `print(...)` snippets 與 `production_fingerprint` 名稱。
- Internal read-only pre-freeze review：`GO`；此為 Mainline 內部唯讀 pre-freeze 判定，不等同 external `C-C_T_REVIEW_GO`。
- 未授權／未執行：真 launchctl、production、Gate D/E、provider、public mutation、commit、push 均未執行。
- Evidence files：`C-C-T-SINGLE-OWNER-RESULT.md`、`c-c-t-single-owner-raw-test-output.txt`。

## Authority 與 lineage

- 固定來源：`4e68b28ed031bddafa898905880c68982944730b`。
- Second-NO_GO Repair base：`b74c1099f7f50d6b620a829d23862722f3f35044`。
- Final external verdict：`C-C_T_REVIEW_NO_GO / BLOCKED_REVIEW_REPAIR_LIMIT`。
- 舊 Repair 額度：`2/2 EXHAUSTED`；本卡是 Owner 明示同意的新 architecture root，不是 Repair-3，也不得改寫舊 finding／review evidence。
- Owner 裁決：允許本卡 bounded offline implementation；不授權真 launchctl、Gate D/E、provider、production/public mutation、merge 或 push。

## Second-NO_GO RCA 四證據

1. 成功版本：C-C/T cohort 本身沒有已知 successful candidate；可作為 known-good seam 的是 shared `barrier-exec` ACK → barrier → activation-only completion invariant，以及 `scripts/pantheon_runtime_fs_authority.py` 的 dirfd／no-follow filesystem authority。
2. fault origins：public callbacks 由 `7821adb`／`b5d` formal API lineage 引入；immediate baseline bootout 與 step parent path handling 由 `97e` candidate lineage 引入。
3. durable invariant：formal Controller 只能擁有 wait primitives，不得讓 public wait callback 成為 owner workload injection seam。
4. durable invariant：Controller 必須收齊七個 baseline service post-barrier `PASS` activation-only completion 後才 bootout，且 step filesystem mutation 必須在 pinned、non-symlink acceptance authority 下，以 relative no-follow semantics 完成。

## Root question

能否在不碰 production 的前提下，使 production fingerprint authority 不受 caller `HOME` 影響，並讓每個 acceptance workload step 只有一個實際執行 owner，使 Controller 只負責 deterministic launch／等待／authoritative read-back，不再直接重跑同一 owner workload？

## 固定 findings

### `CCT-AR-P1-HOME-AUTHORITY`

`PRODUCTION_LAUNCH_PLIST_ROOT = Path.home() / "Library/LaunchAgents"` 可在 import 前由 caller `HOME` 重新導向。Production user home 必須由 OS 帳號資料取得，不得信任環境變數或 caller 參數。

### `CCT-AR-P1-DUAL-WORKLOAD-OWNER`

現況先 bootstrap／kickstart 非 Publisher launchd jobs，barrier 後又由 `_execute_schedule()` 直接 subprocess Coordinator／Runner／C-B／bundle-close；真 launchd child 與 Controller direct process 會競爭同一 queue authority。每個 schedule step 必須只有一個 invocation owner，且 evidence 能歸因到該 invocation。

### `CCT-AR-P2-ONE-SECOND-BARRIER`

七服務 sequential bootstrap 下固定一秒 readiness/barrier timeout 不足以證明 deterministic operability。本卡只做最小 bounded timeout 修正與測試，不建立可配置 timeout subsystem。

### `CCT-AR-P1-PREACTIVATION-TOKEN-DEADLOCK`

candidate `97e871` 的 baseline plist env 在 activation ACK 前帶入尚不存在的 `PANTHEON_RUNTIME_ACTIVATION_TOKEN`。`barrier-exec` 即使以 `require_activation_token=False` 啟動，仍會因非空 token 指向 missing barrier 而回 `78`，導致 activation-only ACK 永遠不出現。Shared runtime 既有 invariant 是 pre-activation env 不帶 token，ACK 後才由 activated step 使用 token。

### `CCT-AR-P2-DIRECT-SCHEDULE-ALTERNATE-EXECUTOR`

舊 `_execute_schedule()` 仍保留 Controller direct workload executor 入口；即使 public `run_once()` 已改 launchd step ownership，該 alternate executor 仍可能被重新接回。此入口必須 fail closed。

## Allowlist

- `scripts/pantheon_four_lane_disposable_acceptance_cohort.py`
- `tests/test_pantheon_four_lane_disposable_acceptance_cohort.py`
- 本卡
- `artifacts/fortune_council/disposable_acceptance_cohort/C-C-T-SINGLE-OWNER-RESULT.md`
- `artifacts/fortune_council/disposable_acceptance_cohort/c-c-t-single-owner-raw-test-output.txt`

若需要修改 Coordinator、Runner、Publisher、runtime manifest、shared installer、plist template或其他 production/test 檔，立即回 `BLOCKED / CONTRACT_EXPANSION_REQUIRED`。

## Forbidden scope

- 真 `/bin/launchctl print/bootstrap/kickstart/bootout`。
- Gate D/E、provider、network、production queue/state/registry/content、public publish、tag、deploy。
- shared manifest／readiness ACK／barrier schema、shared installer或 production plist。
- 新 scheduler、ledger、registry、FSM、database、通用 runtime或第二套 production control plane。
- Controller 直接執行與已啟動 launchd child 相同的 owner workload。
- merge、push、Repair-3或改寫舊 review/evidence。

## Architecture invariants

1. Production home 只能由 `pwd.getpwuid(os.getuid()).pw_dir` 等 OS UID record 推導；resolved home、owner與 canonical path必須一致，`HOME` 不得影響結果。
2. 每個 immutable schedule step 只有一個 workload invocation owner。
3. Controller 可以組固定 launchctl argv、等待、解析 raw process result並重讀 authoritative state；不得用 direct Python/subprocess invocation重跑已由 launchd job擁有的 workload。
4. 若使用 acceptance-local step gating或 step-specific disposable plist，它必須完全由 immutable session plan導出、只存在 acceptance root、可逐步驗證與 teardown；不得成為 shared/production subsystem。
5. Publisher 保持 activation-only與 plan-only零發布契約；若其 direct dry-run owner function沒有平行 launchd child，必須以測試證明仍只有單一 invocation owner。
6. 測試 transport只能回 raw `CompletedProcess` 並模擬 launchd child在barrier後的真實行為；不得只寫 readiness ACK後假裝 child 不會執行。
7. 任一 step無法將 mutation歸因到唯一 invocation時 fail closed，不得產生 PASS receipt。

## Slices、blocking edges 與驗證

### `CCT-AR-S1-OS-HOME-RED-GREEN`

- traces_to：`CCT-AR-P1-HOME-AUTHORITY`。
- frontier：可立即開始。
- RED：在 import 前設定 forged `HOME`，production LaunchAgents authority不得隨之改變；現況必須先失敗。
- GREEN：改由 OS UID record推導並驗證 exact LaunchAgents descendant。
- verification：focused subprocess/import test。

### `CCT-AR-S2-SINGLE-OWNER-RED`

- traces_to：`CCT-AR-P1-DUAL-WORKLOAD-OWNER`。
- frontier：可與 S1 依序執行，但 source GREEN 前只新增一個 behavioral RED。
- RED：transport模擬 readiness後真 launchd child執行；現況因 Controller direct schedule造成相同 step第二次執行或歸因不唯一而失敗。
- verification：public `run_once()` behavioral test，不能只 assert private function名稱。

### `CCT-AR-S3-LAUNCHD-OWNED-SCHEDULE`

- depends_on：`CCT-AR-S2-SINGLE-OWNER-RED`。
- traces_to：`CCT-AR-P1-DUAL-WORKLOAD-OWNER`、`CCT-AR-P2-ONE-SECOND-BARRIER`。
- GREEN：Controller依 immutable schedule只啟動指定 disposable service step、等待並重讀 owner evidence；不得 direct subprocess同一 workload。Timeout採單一 bounded constant並由測試覆蓋 early/late readiness。
- verification：正向四 lane固定順序、duplicate invocation fail-closed、missing/stale read-back fail-closed、teardown完整。

### `CCT-AR-S4-CLOSEOUT`

- depends_on：S1、S3。
- traces_to：全部 findings。
- verification：focused suite、受影響 Coordinator seam、`py_compile`、`git diff --check`、allowlist inventory與 zero-mutation evidence。

## Checkpoint

S1與S2 RED完成後先停下核對：兩個測試必須分別命中 `HOME` authority及雙重 owner症狀，不接受 import／fixture／mock schema錯誤。確認後才能進 S3。

## Minimum sufficient

- why_not_less：只改 `Path.home()`不能關閉雙重 owner；只移除 Controller direct schedule又沒有 launchd step attribution，會失去正式 service consumption evidence。
- why_not_less：只改 `_env()`不夠，因為舊 `_execute_schedule()` 仍會保留可重新接回的 direct workload schedule；只改測試也無法證明真 `barrier-exec` pre-activation ACK 行為。
- why_not_more：不修改 shared runtime、manifest、owner modules、production installer或新增 capacity workload step；新 root只處理兩個原 P1、直接相依 timeout P2、preactivation token deadlock與 direct schedule alternate executor。
- do_not_absorb：production fingerprint欄位擴張、release identity、Cloudflare preview、Gate D/E activation unlock；C-C/T 四-lane single workload owner scope只要求 Capacity Guard readiness operability，完整七服務 runtime acceptance child operability另待 Owner/Gate D/E 決策。

## Acceptance 與交付

- 必須先保存可重現 RED，再做最小 GREEN。
- focused與受影響測試全綠；`py_compile`、`git diff --check`通過。
- worktree只包含 allowlist內變更，無 production/public side effect。
- 結論只能是 `CANDIDATE_READY_FOR_INDEPENDENT_REVIEW` 或 `BLOCKED`；不得自行宣告 `C-C_T_REVIEW_GO`。
- 不 commit／push，除非 Mainline另有明確授權與 freeze裁決。

## Rollback

整體移除本卡 delta即可回到 `4e68b28…`；不修改 shared owner modules、production runtime或外部狀態。
