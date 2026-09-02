# Pantheon C-C/T Continuous Authority Root｜Architecture Card

## 任務與基線

- 工作：從 accepted base `4e68b28ed031bddafa898905880c68982944730b` 建立全新 C-C/T architecture root。
- 只改 cohort Controller、其 focused tests，以及本 root 的 CARD／RESULT／raw evidence。
- rejected candidates 僅作 forensic evidence；不套用、cherry-pick 或複製其 diff。
- 不執行真 launchctl、provider、Gate D/E，不修改 shared runtime／manifest／Coordinator／Runner／Publisher。

## Measured gap 與 durable invariant

最後 accepted base 只用普通 `Path` 重開 production plist、baseline plist 與 step output；bootstrap side effect 也只有在完整 launch receipt 返回後才進入外層 `launched`。因此 ancestor／generation／leaf replacement 可把後續驗證重新綁到新 inode，而 bootstrap 後的局部失敗可讓 teardown ownership 消失。

本 root 的 durable invariant 是：單一 Controller aggregate 從 capture 到 terminal 持續持有每個 authority fd 與首次 identity；所有 path-visible entry 只能用來證明它仍指向已持有的 inode，不得成為新的 authority source。bootstrap return 0 當下，job 立即加入同一 aggregate 的 teardown ownership set；只有 bounded bootout 後 `print == not_found` 才能移除。

## Architecture decision

### Authority owner

`ContinuousAuthority`（實際名稱可依程式碼風格調整）是 `run_once` 唯一 authority owner；不是 DB、registry、ledger、FSM 或第二套 control plane。它持有：

1. OS UID home、`Library`、`LaunchAgents` 三層 directory fd＋device/inode，production plist 只可由 pinned LaunchAgents fd 以 direct-child name、`O_NOFOLLOW` 讀取。
2. acceptance root、`plists`、generation directory fd＋identity，以及七份 baseline plist retained fd＋digest；baseline readiness output 在首次出現時由 pinned parent capture，之後重驗同一 inode。
3. 一個 pinned `steps` directory fd；每個 step 的 plist、stdout、stderr retained fd＋identity＋digest。建立、validate、stdout capture 與 teardown 全部使用這組 fd；capture 前禁止 path reopen。
4. bootstrap 成功的 baseline／step loaded identity 與 teardown attempts。entry 只有在 bootout 成功且後續 print 明確 not_found 時移除。

### Side-effect transition 與 terminal

- preflight 前先驗 ancestor/generation/baseline authority。
- bootstrap return 0 的同一 control point立即 `claim_loaded`，再做 loaded print、kickstart或任何 read-back。
- bootout return 0 不是 terminal；若 print仍 loaded就繼續 bounded retry。
- retry exhaustion 保留 owner entry、loaded identity與逐次錯誤；cleanup 不執行，也不得追蹤 rebound generation／steps。
- terminal proof完成後才允許清理原 pinned generation tree；path entry若已 rebound，fail closed並保留外部／rebound內容。

## Minimum sufficient

- why_not_less：單點 `resolve()`／digest重算會重新授權 replacement；一次 suppress bootout無法證明 side effect terminal。
- why_not_more：不新增跨執行持久化狀態、通用 authority framework、shared runtime seam或 production workflow。
- do_not_absorb：rejected lineage 的 schema擴張、額外 receipt callback、production control plane、Gate D/E 行為。

## 驗證計畫

1. 新增 production ancestor alias／regular-directory replacement RED → production plist bytes讀取前 fail，external／production sentinel不變。
2. 新增 generation rename＋rebind、baseline bootstrap/kickstart前 replacement RED → launch side effect不發生。
3. 新增 step creation→capture same-content new inode、readback→bootout replacement RED → replacement不得被採納；local teardown失敗由 outer owner reclaim。
4. 新增 bootout return 0但 print仍loaded與 exhaustion RED → retry到 not_found；exhaustion evidence保留 loaded identity／attempt errors。
5. 跑 focused cohort、manifest＋runner affected、`py_compile`、`git diff --check` 與 status；freeze source/test/evidence SHA256。

## Rollback

本 root 只在 allowlist 檔案內；回退可移除本 CARD／RESULT／raw evidence，並回復 cohort source/test diff，不影響 shared runtime 或 production。

## Candidate implementation receipt

狀態：`CANDIDATE_READY_FOR_REREVIEW`（Repair-2，2/2；不是 `C-C_T_REVIEW_GO`）。

- `ContinuousAuthority` 是單次 `run_once` 唯一 aggregate；以 retained directory/file fd、首次 device/inode 與 pinned digest 持有 production、baseline、step authority。
- production authority 由 OS account database 的 UID home 起始，逐層以 `O_NOFOLLOW` 開啟 `Library`、`LaunchAgents`，plist 只由 pinned LaunchAgents fd 讀 direct-child bytes。
- baseline generation、七份 plist 與預先建立的 stdout/stderr retained 到 final print；七份 baseline 全為 activation-only，barrier 後須 7/7 stdout PASS 且 stderr 空白。
- step plist/stdout/stderr 全由單一 pinned steps fd 建立與讀回；stdout 同內容換 inode 仍 fail closed。
- bootstrap return 0 後立即 `claim_loaded`；bootout 0 後仍須 print 113，否則 bounded retry。局部 step teardown exhaustion 不移除 ownership，外層統一 reclaim；最終 exhaustion 保留 dev/inode 與逐次錯誤。
- cleanup 只在 terminal proof、無 loaded entry 且 visible generation identity 未漂移時進行；不追蹤或清除 rebound path。

## Bounded Repair-1 decision（1/2）

Closure reviewer 的 zero-write verdict有三項 P1：bootstrap ownership transition仍可能先被 verify中斷、immutable plist只有 inode continuity而無 retained-fd digest continuity、teardown drift可被 terminal bootout吞掉。另提示 create→close→path reopen與 cleanup verify→rmdir window。

最小修復：

- `claim_loaded` 只做不可失敗的 loaded map assignment；bootstrap 0 後先 claim，所有 post-bootstrap verify／print／kickstart在後。
- `RetainedFile` 區分 immutable plist與mutable output。immutable每次 verify都由 retained fd重算 captured digest；stdout/stderr只驗 inode，完成後另算內容 digest。
- create fd由 `RetainedFile.adopt`直接接管；baseline/step stdout/stderr與step plist不再 close後path reopen。
- teardown前後都驗 artifact；drift仍安全執行bootout＋print 113，但持久留在單次 aggregate的structured evidence並令整體 NO_GO。
- cleanup先把owned generation原子移到隨機 quarantine，確認quarantine就是pinned inode後只清除quarantine；同名rebound entry不會成為cleanup target，且使整體NO_GO。

## Bounded Repair-2 decision（2/2）

Re-review 唯一 P1 是 bootout 後 terminal print 呼叫期間仍有 artifact replacement window。最小修復是在 print 返回後、處理 return 113 與移除 loaded ownership前，再由 retained fd 重驗 step plist identity與immutable digest。terminal not-found仍可完成安全 teardown並釋放 ownership，但任何此時捕捉的 drift都保留 structured evidence、令整體 run NO_GO，且禁止正常 cleanup replacement。
