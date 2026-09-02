# Pantheon C-C/T Continuous Authority Root｜Candidate Result

## Status

`CANDIDATE_READY_FOR_REREVIEW`

本結果只代表新 architecture root candidate 已形成並完成本機驗證；不宣告 `C-C_T_REVIEW_GO`。

目前為 bounded Repair-2（計數 `2/2`）。

## Lineage 與 scope

- accepted base：`4e68b28ed031bddafa898905880c68982944730b`
- branch：`codex/pantheon-cct-continuous-authority-root-20260902`
- rejected lineage：只作 forensic read-only；未 copy、cherry-pick 或套用 candidate diff。
- shared runtime／manifest／Coordinator／Runner／Publisher：未修改。
- 真 launchctl、provider、Gate D/E、production/public mutation、deploy、merge、commit、push：`NOT_RUN`。

## Finding closure candidate

1. production：UID home → Library → LaunchAgents 三層 retained directory fd/identity；七份 production plist 只由 pinned LaunchAgents fd 以 direct child＋`O_NOFOLLOW` 讀取，任何 ancestor regular-directory replacement 或 symlink alias 在 plist read 前／期間 fail closed。
2. baseline：acceptance plists generation fd 與七份 plist/stdout/stderr identity 持有到 final print；preflight、bootstrap、post-bootstrap、kickstart、readiness、barrier completion、bootout 均重驗，不採納 generation rename/rebind 或 hardlinked replacement。
3. step：單一 pinned steps fd 建立 plist/stdout/stderr，capture 讀 retained fd；same-content new inode 不會被採納。readback 後 plist replacement 即使令局部 teardown耗盡，外層仍保留 loaded ownership 並 reclaim。
4. lifecycle：bootstrap return 0 同一控制點立即 claim；bootout return 0 仍須後續 print 113。loaded print 仍存在會重試；最終耗盡保留 label、device/inode與逐次錯誤且不 cleanup。

## RED → GREEN

pre-green source SHA256：`105f89d2e274ec1e3bd34652027b219aaedcb07df434fc31414703df3806f458`

test SHA256：`2888c6267067d242ca75cac89c78d235c31b40f043179a79fd215c9748a278ac`

green source SHA256：`0acff65380d2a0ba5b2a0cd825677838a556610ee4e09dfbfc092c88e2f922bf`

實際 RED/GREEN commands、完整 pytest output 與 pre-green→green unified diff 收於同資料夾 raw evidence。

GREEN mandatory targeted：8 cases passed（generation directory/symlink pre-bootstrap、generation post-bootstrap/pre-kickstart、bootout-0-still-loaded、step same-content inode、production regular-directory replacement、production Library symlink、step local exhaustion→outer reclaim）。

## Validation

- focused cohort（Repair-2 final freeze run）：`46 passed in 16.93s`
- manifest＋runner affected（Repair-2 final freeze run）：`118 passed in 17.64s`
- `py_compile`：PASS
- `git diff --check`：PASS
- production/public mutation：`0`

## Remaining risk

- 此 root 只有 offline/fake-launchctl evidence；實機 launchd timing 仍留 Gate D/E plan review。
- Capacity Guard完整 child operability與 raw step artifact長期封存維持既有 P2 residual，不在本 root 擴張。
- candidate 尚待原 reviewer finding closure 與 fresh independent review。

## Repair-1 closure candidate

Closure reviewer authoritative findings摘要：

1. bootstrap 0 後 `claim_loaded` 仍先 verify，post-bootstrap rebind可讓外層沒有teardown ownership。
2. immutable production/baseline/step plist只驗 inode，same-inode content mutation不會被拒絕。
3. teardown artifact drift可在bootout 0＋print 113後被吞掉，錯誤地允許整體PASS／cleanup。

Repair-1已改為：unconditional claim-first、retained-fd immutable digest continuity、mutable output完成後content digest、pre/post bootout drift capture、terminal drift仍NO_GO，以及create-fd直接adopt與generation quarantine cleanup。

Repair-1 pre-fix source SHA256：`0acff65380d2a0ba5b2a0cd825677838a556610ee4e09dfbfc092c88e2f922bf`

Repair-1 test SHA256：`ba1a6f0c0e38abf95fee68f90b259572b0101a2f2e9f680b76e998c6af07213c`

Repair-1 green source SHA256：`1c9cf3bf209f22d227cd60caab39a1cf86d87108863e0eadf60a295861e15a2d`

Repair-1 targeted GREEN：`10 passed, 35 deselected in 4.27s`。

## Repair-2 closure candidate

Re-review 唯一 P1：`release()` 在 bootout後的 terminal print執行期間若 step plist被同內容新inode替換，既有pre/post-bootout驗證都已結束，print 113會直接移除 ownership並吞掉 drift。

Repair-2在 terminal print返回後、判定113與刪除 loaded ownership前，再重驗 retained artifact identity與immutable digest。若發生 drift，安全 teardown仍以not-found完成並可移除 ownership，但structured evidence必須保留、整體run NO_GO且不進正常cleanup。

Repair-2 pre-fix source SHA256：`1c9cf3bf209f22d227cd60caab39a1cf86d87108863e0eadf60a295861e15a2d`

Repair-2 pre-fix test SHA256：`ba1a6f0c0e38abf95fee68f90b259572b0101a2f2e9f680b76e998c6af07213c`

Repair-2 green source SHA256：`51fef38e8a91a3b81223a850428239b0f7fd7f95fb19401bd4cd51cff0886951`

Repair-2 green test SHA256：`97730e399a964e8e7dd47139b99254207a13ad8344ed3a2106d8efb4637d68fa`

Repair-2 targeted RED：`1 failed, 45 deselected in 2.51s`（`DID NOT RAISE`，命中錯誤PASS）。

Repair-2 targeted GREEN：`1 passed, 45 deselected in 0.07s`。
