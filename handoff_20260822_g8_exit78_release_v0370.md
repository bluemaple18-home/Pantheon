---
id: HANDOFF-PANTHEON-G8-EXIT78-RELEASE-V0370-20260822
date: 2026-08-22
status: ready_for_handoff
baseline_branch: main
baseline_sha: b0950d4c436cc902e17ac110b579b35b84aa53e4
release_version: 0.3.370
release_tag: v0.3.370
---

# Pantheon G8 Exit 78 Release v0.3.370 換手卡

## Root Question

如何在 G8 `TARGET_STAGED → QUIESCED_TARGET_STAGED` edge 已完成程式修復、獨立 re-review、main adoption 與 release 後，以當下 production 狀態做一次完整唯讀 reconciliation，確認 Rule 24／25 與 Cycle 29–34 evidence current，再由人工決定是否授權 bounded canary？

## Current Blocker

程式 blocker 已解除；目前唯一 blocker 是缺少修復後、針對當下 production 狀態的新鮮唯讀 reconciliation 與 current Rule 24／25 capability evidence。

在這些 evidence 完整且 verdict 為 GO 前，不得執行 reset、Capacity mutation、activation、restage 或 canary。

## Candidate Fork

目前沒有 candidate fork。

若唯讀 reconciliation 發現同一 transition edge 的新 defect，優先回到同一 bounded repair unit；不得依 error string 拆出 Cycle 35／36 symptom card。只有 blocker 已跨入另一個 authority boundary，才可提出新卡。

## Goal

以 `main@b0950d4c436cc902e17ac110b579b35b84aa53e4`／`v0.3.370` 為唯一 release baseline，完成 production read-only reconciliation；若所有 gate current 且 GO，停止並向使用者索取一次 bounded canary 的人工授權。

## Constraints & Preferences

- 文件、回報、註解與 docstring 使用繁中；程式碼維持既有語言。
- 下一手第一拍只讀本卡、列出的 evidence、HEAD／tag／worktree／CodeGraph 與 production current state。
- 不新增第二套 transition engine、daemon、database、scheduler、registry 或 content-plane semantics。
- 同一 transition edge 視為一個 bounded repair unit；禁止一個 error code 一張新卡。
- Rule 24／25、readiness 與 evidence consumer 不得自行取得 mutation authority。
- 未取得人工授權前，禁止 production reset、Capacity install、activation、restage、canary、deploy 或 steady autonomy。
- 原有未追蹤 artifacts／handoffs 是使用者資料；不得刪除、stage、覆寫或帶入派工 worktree。
- 已完成的可見 threads 保留，不封存、不刪除。

## Completed Actions

1. 修正 Publisher reset settling race，已於先前 commit `0ed5124eab` 納入 main。
2. 明文化 activation-only Publisher 在 transition moment 出現 exit 78 的 inert／quiesced 邊界。
3. 獨立 Review 找出 `G8-EXIT78-P1-001`：舊 production validator 未證明 target-newer 與 current reset provenance，判定 `REVIEW_NO_GO`。
4. 在同一 transition edge repair unit 完成 durable provenance 修復：
   - reset 開始前使舊 success receipt 失效；
   - producer 原子寫入 owner-only `publisher-reset-receipt.json`；
   - receipt 綁定 correlation、target／old-live generation、Publisher identity 與 other-six unchanged proof；
   - Capacity 僅在觀察到 exit 78 時要求完整 current provenance；absent／0 semantics 不收窄；
   - stale／missing receipt、same-generation、identity drift、PID／path drift與其他 nonzero 均 fail closed。
5. Repair candidate：`3da4caf01efbc3851f7da22670bfaa130aa9d21e`。
6. Targeted independent re-review：`RE_REVIEW_GO`；RESULT source commit `a65e9b7b213f81195ce4bdd32a69b8ee5829ebd8`，main adoption commit `9068e33d67`。
7. 版本升為 `0.3.370`，release commit：`b0950d4c436cc902e17ac110b579b35b84aa53e4`。
8. 建立 annotated tag `v0.3.370`，已與 main 一起推到 `origin`；遠端 branch 與 peeled tag 均指向 release commit。
9. 收掉本輪命名分支：
   - `review/g8-exit78-contract-clarification`
   - `repair/g8-exit78-provenance`
10. 相關 worktree 皆 clean 並已解除 branch 綁定；側邊欄 threads 保留可見。
11. 未執行 production mutation、deploy 或正式 canary。

## Active State

- Repository branch：`main`
- Release baseline：`b0950d4c436cc902e17ac110b579b35b84aa53e4`；換手卡 commit 會位於其後，下一手只要求 HEAD／`origin/main` 包含此 baseline。
- Release：`0.3.370`
- Annotated tag：`v0.3.370` → `b0950d4c436cc902e17ac110b579b35b84aa53e4`
- Main tracked worktree：換手卡建立前 clean。
- Main 有既存 unrelated untracked artifacts／handoffs；本 chain 未碰。
- 本任務未啟動 server、daemon 或 production process。
- 可見 threads：
  - Contract Clarification：`01a02844-d9e4-72c2-bd1a-0f8f844cbdd7`
  - Independent Review／targeted re-review：`01a02852-f795-7331-9b1e-9a3be1ce1403`
  - Provenance Repair：`01a0285c-bbe9-7292-b474-63db0ab0d883`

## Evidence Authority

下一手必須先讀：

1. `artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-G8-RELEASE-STATE-CONTRACT-V1-20260821.md`
2. `artifacts/fortune_council/four_lane_runtime_execution/PANTHEON-G8-TRANSITION-EDGE-MAP-V1-20260821.md`
3. `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-PUBLISHER-RESET-BOOTSTRAP-RCA-REPAIR-CYCLE-34-20260822-RESULT.md`
4. `artifacts/fortune_council/four_lane_runtime_execution/REPAIR-PANTHEON-G8-ACTIVATION-ONLY-EXIT-78-PROVENANCE-20260822-RESULT.md`
5. `artifacts/fortune_council/four_lane_runtime_execution/REVIEW-PANTHEON-G8-ACTIVATION-ONLY-EXIT-78-CONTRACT-CLARIFICATION-20260822-RE-REVIEW-RESULT.md`
6. `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-TRANSITION-TO-CANARY-READY-CYCLE-33-20260822-RESULT.md`

禁止把舊 Cycle 31 readiness 或 Cycle 33 failure 文案當成 current production evidence；它們只證明歷史狀態與 root cause。

## Verification Evidence

- Capacity focused suite：`59 passed`
- Publisher reset focused suite：`20 passed, 244 deselected`
- G8 preactivation suite：`41 passed`
- Release record tests：`7 passed`
- 兩個 installer `bash -n`：PASS
- `git diff --check`：PASS
- Release record gate：PASS
- Pre-push release gate：PASS
- Release push 當下的 remote verification：`origin/main` 與 `v0.3.370^{}` 均為 `b0950d4c436cc902e17ac110b579b35b84aa53e4`；換手卡後續 commit 不移動 release tag。

## Key Decisions & Resolved Questions

- `QUIESCED_TARGET_STAGED` 允許 activation-only Publisher child 因 old expected digest 面對 promoted manifest 而 terminal exit 78；合法性來自 loaded／no-PID／exact path／identity 與 current reset provenance，不要求 child 在該 moment 成功執行 workload。
- exit 78 不是單靠 launchctl last-exit-code 即可接受；必須同時證明 target generation newer、current correlation、Publisher post-state與 other-six unchanged proof。
- absent／0 繼續依原 semantics；新 provenance gate 只處理 observed exit 78。
- settling repair 只做 bounded read-only observation retry；bootstrap mutation仍只允許一次。
- 同一 transition edge 的 reset、bootstrap、settling、postcheck、rollback與 evidence 必須留在同一 bounded unit。
- 本次 release 只改 control-plane contract／producer／consumer與測試，未建立第二套 transition authority。

## In Progress / Remaining Work

1. 新手第一拍唯讀驗證本卡、六份 evidence、`main`／`origin/main`／`v0.3.370`、worktree與 CodeGraph readiness。
2. 只開一張 current production read-only reconciliation 卡；不得先開 canary implementation 或 symptom repair 卡。
3. 收集當下 Cycle 29–34／Rule 24／Rule 25 所需 evidence，確認 runtime phase、Publisher activation-only identity、loaded／no-PID、receipt freshness、generation與 other-six unchanged proof。
4. 產出唯一 gate matrix：`GO`、`NO-GO` 或 `UNKNOWN`；任何 contradiction 必須 fail closed。
5. 若 verdict 為 GO，停止並向使用者索取一次 bounded canary 人工授權。
6. Canary 成功後，steady autonomy 仍是獨立授權，不得自動延伸。

## Waiting Conditions

- HEAD 必須等於 `origin/main` 並包含 release baseline；peeled `v0.3.370` 必須精確指向 `b0950d4c436cc902e17ac110b579b35b84aa53e4`。
- CodeGraph 先查；不可用才限域使用 `rg`。
- production reconciliation 必須是 read-only，且 evidence timestamp／generation／correlation current。
- Rule 24 容量增長實測、監控與自動停損缺一即 `NO-GO`。
- Rule 25 必須具備 create→run→select→publish→transaction→tag→push 全鏈路 capability receipt，以及正式入口、I/O、identity／correlation、正向與 fail-closed 負向證據。
- 未取得新人工授權前，所有 production mutation維持禁止。

## Blocked & Errors

- 目前無 code／test／release blocker。
- CodeGraph 在本輪 Review worktree 未初始化；Reviewer 已依契約改用 candidate snapshot 的限域 source review。下一手仍須重新檢查 main 的 CodeGraph readiness，不得沿用舊失敗結果。
- 唯一未完成項是 current production reconciliation 與 canary authorization boundary。

## Limits

- 不重寫 Publisher、coordinator、four content lanes 或內容 business logic。
- 不新增 daemon、database、scheduler、registry、event family或 Pantheon-specific Core semantics。
- 不因新 error string 自動衍生 Cycle 35／36。
- 不碰原未追蹤檔。
- 不自行 push 新改動、deploy、production mutation或 steady autonomy。

## Acceptance for the Next Hand

下一手第一次回報只能確認：已讀本卡與六份 evidence、HEAD／remote／tag、worktree／未追蹤檔、CodeGraph readiness，以及理解下一張卡只能是 current production read-only reconciliation。

完成上述 bootstrap 前，不得修改 source、建立 production stage、執行 reset／Capacity／activation／restage／canary，或把歷史 GO 文案當成 current evidence。
