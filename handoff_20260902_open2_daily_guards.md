# Pantheon OPEN-2 daily guards handoff

## Root question

現有四 lane 能否在不新增第二套 authority／state store／runtime 的前提下，安全進入無人值守連續
運行；其中 OPEN-2 必須同時限制每日 provider 成本與 publication success 產量。

## Goal

保留已驗收的 Provider admission cap，封存未通過 review 的 Publication success quota，並讓下一位
接手者能從固定 branch／SHA／測試與 finding 重現目前裁決。

## Constraints & preferences

- Operating Mode、Product Level、Capability Vector 未變更。
- 沿用既有 allocator lock、Publisher lock 與 ledger；禁止新增 authority ledger、registry、FSM、
  database、canonical writer 或第二套 runtime。
- provider attempt 上限固定為 Asia/Taipei 每日 `102`。
- publication success 目標為 `new=1, rewrite=1, translation=1, total=3`；Success quota production
  source 淨增硬上限為 `260 LOC`，且最多一個 generic FSM。
- 本次只 push 兩個隔離分支作 review／handoff；不 merge、deploy、launchctl、provider、publish 或
  production mutation。

## Completed actions

### Control branch

- Branch：`codex/pantheon-open2-daily-guard-20260902`。
- `59fe3fea21`：將目標縮回 resident operability，區分 per-run correctness 與連續運行證據。
- `2c8c277115`：完成 OPEN-2 quota seam mapping。
- `b42938aa94`：記錄 OPEN-1 歷史 failure-isolation evidence；該證據不等於三次失敗後 terminal
  path 已證明。
- `e18c4df46d`：鎖定 Provider／Success 兩張 implementation card。
- `4da465a5bb`：鎖定 Owner 決策：marker deletion 後同 job retry 是新 paid attempt；Success quota
  以 production net `<=260 LOC` 與單一 generic FSM 為 gate。
- `4ac3de9f1b`：整合已通過 review 的 Provider admission cap。

### Provider admission cap

- 四 lane 共用 allocator lock 與 schema v4 的 Asia/Taipei daily integer count。
- production-attempt marker 是 replay identity；marker 存在時零 provider call／零 count，明確刪除
  marker 後重試會重新計數。
- 第 103 筆在 claim／credential read／CLI／broker／provider call 前 fail closed。
- formal coordinator 也受既有 formal transport gate 與 `102` cap；未新增 coordinator lifecycle。
- 驗證：受影響 suites `199 passed`；focused repair `12 passed`；formal coordinator focused
  `2 passed`；`py_compile` 與 `git diff --check` 通過。
- 獨立 correctness re-review：GO。Provider production source 相對 implementation base 淨增
  `140 LOC`。

### Publication success quota research branch

- Branch：`codex/pantheon-open2-success-quota-repair1-20260902`。
- Implementation candidate：`811e294bee`。
- Repair-3 candidate：`4281d3a3f427fde655893e761a1c7bb55d4c43ed`。
- Final NO-GO documentation：`cb3287ec09`。
- Publisher production source 相對 `e18c4df46d` 為 `545 additions / 295 deletions`，淨增
  `250 LOC`；表面符合 LOC gate，實際未通過安全 review。
- 驗證曾達 Publisher `182 passed`、installer focused tests、`py_compile`、`bash -n`、
  `git diff --check` 通過；這些測試沒有覆蓋真正 production ordering，因此不得作 acceptance。

## Active state

- Control branch 只包含已接受的 Provider guard 與控制文件；未包含 Success quota source。
- Success quota branch 保留完整失敗候選與 `REVIEW_NO_GO` 文件，僅供重現／研究。
- 兩個 worktree 的本機絕對路徑屬 local-only 診斷資訊，不可跨機照抄；跨機接手請從上述遠端
  branch 建立各自乾淨 worktree。
- 無 server、launchd job、provider call、production queue/state、tag 或 publication mutation。

## Blocker

Publication success quota 的 generic crash-recovery FSM 在真實 production ordering 下不安全，且
已進入「再補丁會擴大架構」的停線條件。

## Blocked & errors

### P0：restart 可繞過 release gate

`COMMIT_INTENT` 在 commit/tag 前落盤，但 production 是 commit/tag 後才執行 release gate。若在
commit/tag 後、release gate 完成前 crash，restart 只用 tag／parent identity 便可升級
`PUSH_PREPARED` 並 push，未重新跑 release gate 或驗 diff allowlist。real-git test 還以任意檔案
commit 期待可 push，形成 false-green safety evidence。

### P1：intent 後、tag 前 crash 會永久 wedge

若 crash 發生於 intent 已寫、tag 未建時，restart 無法重建 target；control 與 quota reservation
持續存在，每輪都 fail closed，沒有 terminal／release 或安全重做路徑。測試順序先建 tag 再寫
intent，與 production 相反。

### P1：strict config 不是最外層 mutation gate

phase helper 已在 collector 前讀 config，但 production `main()` 更早 truncate log、建立 state root、
建立或清理 transaction worktree。現有 helper test 沒走這段 wiring，因此不能證明 malformed／
missing config 在所有受管 mutation 前 fail closed。

### P1：generic refactor 曾遺失 translation authority semantics

第一版只驗 control self-digest 與內嵌 ledger/evidence，漏掉 sealed queue state、
`queue_state_sha256`、candidate/review/formal-job hashes、replacement manifest 與 supersession。
Repair-3 補回驗證，但同時暴露上述 P0/P1；這說明不能只抽資料形狀而省略 phase authority。

### P1：restart worktree 與 phase continuation 曾回歸

- 第一版 scheduler 先刪 stale worktree、再從 `origin/main` 建 base worktree，卻要求
  `HEAD == target_commit_sha`，因此 push 前 crash 必然無法 resume。
- 第一版 create/rewrite resume 直接 return，跳過 pending translation seeding；idle path 也無法補。
- Repair-3 局部修復兩者，但不抵消新的 release-gate bypass／pre-tag wedge。

### P2：ledger atomicity 與 dry-run 證據不足

- 第一版 `pushed=False` terminal 與 reservation release 分兩次 ledger write；中間 crash 會永久占用
  quota。Repair-3 已局部改為同次 atomic write。
- dry-run 用固定 `10_000` 取代原 limit，仍非 exhaustive；兩筆 mock test 無法證明超過上限時完整
  列出 ready runs。
- installer test 以 source parsing＋手動 `setenv` 為主，未證明 scheduler 實際載入 staged plist
  後的 end-to-end Publisher consumption。

完整 finding 與根因見 Success quota branch 的
`artifacts/fortune_council/four_lane_runtime_execution/RESULT-PANTHEON-OPEN2-PUBLICATION-SUCCESS-QUOTA-IMPLEMENTATION-20260902.md`。

## Key decisions & resolved questions

- per-run correctness 已有 production canary 證據；resident operability 尚未證明，兩者不可混稱。
- OPEN-1 只有「歷史 failed registry 未停止同 cycle seed/dispatch」證據；沒有真實三次失敗後進
  terminal/manual、釋放 slot、下一 item 被選走的完整證據。
- Provider cap 採 attempt marker boundary，不使用 job-id 去重清單，避免 state 成長與同 job retry
  漏計成本。
- Success quota 即使未超過 `260 LOC`，只要 production invariant 不成立仍是 NO-GO；LOC 是上限，
  不是 acceptance substitute。
- 不建立 Repair-4，不把 rejected candidate cherry-pick 到 control branch。

## Candidate fork

若 Owner 日後重啟 Success quota，從 `e18c4df46d` 重新設計最小 slice，不沿用 rejected candidate
逐 finding 疊補丁。先建立符合真實 production 順序的 RED tests，再決定是否能只靠既有 Publisher
transaction／ledger seam 達標；若仍需要新 transaction layer 或第二 FSM，維持
`BLOCK_SCOPE_EXPANSION`。

## In progress / remaining work

1. OPEN-2 Provider guard 已可進主線 review／PR，但本 handoff 不授權 merge 或 deploy。
2. OPEN-2 Success quota 維持 `REVIEW_NO_GO`，等待 Owner 是否另開重新設計卡。
3. OPEN-1 仍需真實 resident run 證據：同一 item 三次失敗、terminal/manual、slot release、下一 item
   被選取；讀 code 或單次 loop evidence 不算完成。
4. 啟動 resident workflow 前仍須跑封死的四項 preflight：七服務 install/load 乾淨、cap 設定存在且
   Publisher 真正讀到、一次 dry cycle、production fingerprint 無漂移。

## Next step

先由獨立 reviewer 對遠端 control branch 的 Provider diff 與本 handoff 重現證據；GO 後再由 Owner
單獨授權 merge。Success quota 不跟隨 Provider 一起整合。

## Waiting conditions

- Provider：等待遠端 branch review／Owner merge 決策。
- Success quota：等待 Owner 是否接受重新設計，而非 Repair-4。
- Resident activation：等待 OPEN-1 真實 failure-isolation evidence 與四項 preflight 全部通過。

## Limits

- 不因「測試全綠」覆蓋未測到的 production ordering P0/P1。
- 不放寬 Success quota `260 LOC`、不新增第二 FSM 或 state store。
- 未取得獨立授權前，不 merge、deploy、launchctl、publish、呼叫 provider 或改 production state。
