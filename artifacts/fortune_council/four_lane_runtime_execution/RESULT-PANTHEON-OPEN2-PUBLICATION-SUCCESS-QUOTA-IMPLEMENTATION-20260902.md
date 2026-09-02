---
id: RESULT-PANTHEON-OPEN2-PUBLICATION-SUCCESS-QUOTA-IMPLEMENTATION-20260902
card_id: CARD-PANTHEON-OPEN2-PUBLICATION-SUCCESS-QUOTA-IMPLEMENTATION-20260902
status: REVIEW_NO_GO
production_mutation: 0
---

# OPEN-2 publication success quota 實作結果（REVIEW NO-GO）

## 最終裁決

`REVIEW_NO_GO`。候選實作雖符合單一 generic FSM 與 production source 淨增不超過
260 LOC 的表面界線，但獨立 re-review 發現一個可繞過 release gate 的 P0，以及數個 crash
recovery／fail-closed／dry-run 契約缺口。此分支只保留作研究與重現證據，不得整合、push 到
main、deploy 或啟動 production。

## 交付

- 僅延伸既有 `ledger.json`，以單一 create／rewrite／translation 通用
  prepared/reconcile FSM 處理 remote 收斂、phase ledger terminal entry 與 quota
  success status 的同次 atomic write。
- quota 固定為 Asia/Taipei 的 `new=1`、`rewrite=1`、`translation=1`、`total=3`；
  同 run replay 保留首次 admission date，未發佈可證明時才 release reservation。
- dry-run 保留完整 ready 清單；non-dry 在 journal selection、reservation 與任何 mutation
  前 deterministic 僅放行各 phase 的第一筆 ready run。
- scheduler 無 `--exact-run-id` 時會先 resume `PUSH_PREPARED`；installer 固定投影
  `PANTHEON_PUBLICATION_SUCCESS_QUOTA`，Publisher 的每次 non-dry mutation 都會 strict read。
- translation-only prepared helper／reconcile FSM 已移除；保留並改接 crash、config、concurrency
  測試到通用 FSM。
- 第一個 git mutation 前會原子寫入 `COMMIT_INTENT`，保存 phase、run、base、proposed tag
  與可重建的 ledger/evidence identity；commit/tag 已生成但尚未轉換時，scheduler 會以 local
  annotated tag、peeled commit 與 parent base 驗證後原子升級為 `PUSH_PREPARED`，否則 fail-closed。
- translation 的 sealed/staged resume 會重驗 queue state、candidate/review/formal hashes，以及
  replacement manifest／supersession lineage；未發佈 terminal entry 與 reservation release 同次
  ledger atomic write。

## 驗證

- `.venv/bin/python -m pytest tests/test_agy_content_publisher.py -q`：182 passed（1 個既有 SyntaxWarning）。
- installer config focused：1 passed。
- `python3 -m py_compile scripts/agy_content_publisher.py tests/test_agy_content_publisher.py`：通過。
- `bash -n scripts/install_agy_content_publisher_launchd.sh`：通過。
- `git diff --check`：通過。
- 對 base `e18c4df46d`，Publisher 為 545 additions／295 deletions，淨增 250 LOC（≤260）。

未執行 push、deploy、launchctl、provider 或 production mutation。

## 獨立 review 發現

### P0：`COMMIT_INTENT` recovery 可繞過 release gate

- production 順序是 commit/tag 後才執行 release gate；若在 commit/tag 完成後、release gate
  完成前硬 crash，restart 會只用 tag／parent identity 將 `COMMIT_INTENT` 升級為
  `PUSH_PREPARED`，接著 push。
- recovery 沒有重新執行 release gate，也沒有重新驗證實際 diff allowlist，因此可能發布從未
  通過 release gate 的 commit。
- 新增的 real-git lifecycle test 反而以任意 `owned.txt` commit 期待可 push，將錯誤行為寫成
  GREEN；測試通過不能作為安全證據。

### P1：intent 後、tag 前 crash 會永久卡住 Publisher

- `COMMIT_INTENT` 在 `git add/commit/tag` 前寫入；若 crash 發生在 tag 建立前，restart 無法從
  proposed tag 重建 target。
- control 與 success reservation 都保留，後續每次 scheduler restart 都重複 fail-closed，沒有
  terminal／release 或安全重做路徑。
- lifecycle test 的操作順序是先建立 commit/tag、再寫 intent，與 production 真實順序相反，
  因而漏掉此 crash window。

### P1：strict quota config 仍晚於 production entry 的部分 mutation

- phase decorator 已在 collector 前讀取 config，但 `main()` 在進入 decorator 前仍會 truncate
  log、建立 state root、建立或清理 transaction worktree。
- missing／malformed config 因此不是在「每次 non-dry mutation 前」fail closed；現有測試直接
  呼叫 phase helper，沒有經過 production `main()` wiring。

### P1：舊候選曾移除 translation sealed/staged authority 驗證

- 第一版 generic resume 只信任 control 內嵌 ledger/evidence 與 self-digest，沒有重新驗證 sealed
  queue state、`queue_state_sha256`、approved candidate/review/formal-job hashes、replacement
  manifest 與 supersession。
- Repair-3 已補回這些驗證，但因上述 P0/P1，整體候選仍不可接受。此 finding 必須保留，避免
  下次重構再次只抽資料形狀而遺失 authority semantics。

### P1：第一版 restart wiring 無法從真正 transaction worktree 恢復

- scheduler 會清掉 stale transaction worktree，再從 `origin/main` 建新 worktree；push 前 crash
  時 origin 仍指向 base，而第一版 resume 強制 `HEAD == target_commit_sha`，必然失敗。
- Repair-3 已加入 verified target checkout，但新 `COMMIT_INTENT` 路徑又產生 release-gate bypass
  與 pre-tag wedge，故不能視為整體關閉。

### P1：第一版 create/rewrite recovery 遺失 translation seeding 後續語義

- resume 後直接 return，跳過 `_seed_pending_translations()`；idle create 也在補 seed 前 return，
  使 `translation_seed_status=pending` 永久無法補回。
- Repair-3 已恢復 resume 與 idle seeding；仍保留本 finding 作 regression invariant。

### P2：unpublished terminal 與 reservation release 曾非原子

- 第一版先寫 `pushed=False` terminal，再另一次讀寫 ledger release reservation；兩次寫入間 crash
  會留下 terminal run 與永久 reserved quota。
- Repair-3 已改為同一 ledger atomic write；仍需作為下次設計的硬 invariant。

### P2：dry-run 並未真正列出全部 ready runs

- Repair-3 將 collector limit 改為固定 `10_000`，仍是未記錄的上限，不等於 exhaustive。
- 測試只有兩筆 mocked records，且 mock 在 `limit > 1` 時回傳全部，沒有證明 production collector
  對超過上限的資料仍完整列出。

### 測試與證據缺口

- Publisher suite `182 passed`、installer focused tests、`py_compile`、`bash -n` 與
  `git diff --check` 均通過，但未覆蓋上述真實 production ordering。
- installer test 主要解析 source 並手動 `setenv`；它能證明固定值出現在 installer 與 Publisher
  helper 可讀取環境值，不能完整證明 scheduler 載入 staged plist 後的 end-to-end consumption。

## 根因與停線

- 最後可接受基準：`e18c4df46d`（只鎖定 OPEN-2 契約，未包含 Success quota 實作）。
- 回歸起點：`811e294bee`；Repair-3 candidate：`4281d3a3f427fde655893e761a1c7bb55d4c43ed`。
- 根因：把 translation-specific recovery 抽成 generic FSM 時，只統一資料形狀，沒有完整保存
  mutation ordering、release-gate authority、跨 worktree lifecycle、phase continuation 與
  fail-closed boundary。
- 停線：不建立 Repair-4；不放寬 260 LOC gate；不把此候選 cherry-pick 到控制分支。

## 下一步 fork

若 Owner 日後要重啟 OPEN-2 Success quota，應從 `e18c4df46d` 重新做最小設計，不在本候選上
逐 finding 疊補丁。新設計必須先用 production-order RED tests 同時證明：release gate 不可繞過、
intent 前／後每個 crash window 可 terminal 或安全重做、strict config 先於所有受管 publication
mutation、dry-run 無隱藏上限，以及 translation authority／seeding semantics 不退步。
