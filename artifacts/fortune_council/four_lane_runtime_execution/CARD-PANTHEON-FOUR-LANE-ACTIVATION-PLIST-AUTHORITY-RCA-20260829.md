# 👉 [假設與目標確認]

本卡只調查四線 activation 未載入的 plist authority／canonical path 根因；不修改程式、測試、權限、symlink、stage 或 production，也不執行 install、activate、scheduler、publish、commit、push 或建立 Repair。驗收是產出唯一 RCA 結果檔，且能以可重現 evidence 說明最後成功 activation cohort、first-bad commit／機制、實際不符約束的 plist、authority owner、跨版本生命週期與 production-shaped RED double-run。

# CARD-PANTHEON-FOUR-LANE-ACTIVATION-PLIST-AUTHORITY-RCA-20260829

## 任務目的

釐清「程式與 manifest 存在，但四線自動化未載入」的單一根因。RCA 只回答 plist canonical path／realpath／ownership authority 與 activation lifecycle，不把控制面狀態文案當作 runtime evidence。

## 已知背景與固定 evidence

- accepted/live actor：`6541693e929a20cbcffe8b070085b5f1caec7a92`（g72）。
- promotion：`COMMITTED/PASS`。
- Rule24：`PASS`。
- Rule25：`READY`。
- 七服務尚未 loaded；四條 lane 為 `new`、`rewrite`、`i18n-new`、`i18n-rewrite`。
- Phase2 第一次 capacity 因 publisher `max-runs=3` 被擋；已用正式 publisher installer 與 `PANTHEON_PUBLISH_MAX_RUNS=1` 修正。
- selector 雙側缺席驗證：`PASS`。
- 第二次 edge capacity `--install-recovery-stage` 被正式擋，錯誤為：`plist canonical realpath or owner mismatch`。
- 目前仍是 services 未 loaded、registry=`136`、new canary=`0`；production content 未變。

## 調查範圍

必須以唯讀 evidence 確認：

1. 最後成功的七服務 activation cohort 及其可驗收 runtime/session evidence。
2. first-bad commit 或 first-bad mechanism：指出從哪個版本、installer、stage 或 activation transition 開始破壞 durable invariant。
3. 精確辨識實際不符 expected 的 plist，分類為 capacity temp、staged publisher、lane 或 live；記錄 `path`、`realpath`、`uid`、`gid`、`mode` 與 expected 值。
4. canonical／ownership authority owner：說明哪個 installer、manifest、stage 或 runtime owner 是唯一權威，以及其他副本為何不能取代它。
5. 跨版本、installer、stage、activation lifecycle：說明 artifact 形成、搬移／安裝、載入、重啟與 recovery boundary 的因果鏈。
6. exact production-shaped RED double-run：同一 production-shaped activation／capacity 檢查連續執行兩次，兩次都應在相同不變的 immutable production bytes 上 fail closed，並保存命令、輸出、exit status、時間與 correlation identity。

## 明確禁止

- 不改 code、test、manifest 或任何既有 artifact。
- 不 `chmod`、`chown`、改 owner、改 symlink 或手動編輯／替換 stage／plist。
- 不 install、activate、load／reload scheduler、publish、promotion、deploy、tag、push 或改 production。
- 不建立 Repair、不建立第二套 authority／registry／FSM／canonical writer。
- 不以 projection receipt、registry 數字、狀態文案或既有 `831` 驗收代表目前四線 runtime。

## 唯讀證據與結果契約

結果固定寫入：

`artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_activation_plist_authority_rca_20260829/RESULT.md`

`RESULT.md` 必須包含：

- `Verdict`：single root cause、是否 `BLOCKED`，以及仍缺的 evidence（若有）。
- `Last-successful-activation-cohort`。
- `First-bad-commit-or-mechanism`。
- `Plist-authority-matrix`：每一候選 plist 的實際 path／realpath／uid／gid／mode、expected、判定與 evidence source。
- `Canonical-owner-and-lifecycle`。
- `RED-double-run`：兩次 exact run 的 command、inputs／identity、exit status、關鍵輸出與 fail-closed 判定。
- `Production-immutability`：執行前後 production bytes／digest 一致的 evidence；若無法證明，判定 `BLOCKED`。
- `Repair-frontier`：最多只提出一個最小 bounded Repair seam；不得實作或建立 Repair。若不需要，明寫 `none`。
- `why_not_less`：為何只查一個 plist／單一 snapshot 不足以閉合 authority 根因。
- `why_not_more`：為何不擴張到 code rewrite、全量 activation 或其他 subsystem。
- `do_not_absorb`：明列不吸收的額外機制／治理／registry／review 層。

## Acceptance criteria

- 所有結論都有可重現唯讀 evidence，並區分檔案 projection 與 runtime/session fact。
- 明確指出最後成功 cohort、first-bad 邊界及一個唯一 root cause；若證據衝突，保持 `BLOCKED`，不得猜測。
- 實際 plist 與 expected 的差異可由 exact path／realpath／uid／gid／mode 重現。
- RED double-run 具 production shape，兩次結果一致且 fail closed。
- production bytes 在整個調查前後 immutable；無任何 production mutation。
- 僅產生本卡與鎖定的 `RESULT.md`（結果檔須在本任務允許範圍內建立），不產生其他 Repair／stage／plist 變更。
- 完成前執行 `git diff --check`；不得執行 commit／push。

## Stop conditions

立即停止並在 `RESULT.md` 標記 `BLOCKED`：

- 無法取得 authoritative owner 或 canonical realpath evidence。
- 任何檢查需要修改 plist、owner、mode、symlink、stage、service state 或 production。
- RED double-run 不是 production-shaped、無法第二次重現，或兩次 failure boundary 不一致。
- 無法證明 production bytes immutable。
- 發現第二個相關故障而需逐症狀修補；改回 root-cause analysis，不新增 Repair。
- 同一 blocker 第三次失敗；不做第四次嘗試。

## 唯一主裁決與 Repair frontier

主裁決只在本 RCA `RESULT.md` 形成後由主線判定：四線 activation 是否仍 `BLOCKED`，以及是否允許另開一個 bounded Repair。若需要 Repair，只能針對已證明的 canonical plist authority／installer lifecycle seam，並保留 removal／rollback path；本卡不建立、不執行、不授權該 Repair。

