---
id: CARD-PANTHEON-G8-PRECANARY-REMAINING-GATES-DIAGNOSTIC-20260821
chain_id: pantheon-g8-precanary-remaining-gates-diagnostic
role: architecture-diagnostic-auditor
status: queued
model_route: gpt-5.6-sol-high
source_sha: 1d608410cc9ee9adc6fc3bc53c515e4ecd4005d1
---

# G8 PRE-CANARY REMAINING-GATES DIAGNOSTIC

## 工作名稱 → 正在做什麼 → 現在狀態

- 工作名稱：G8 pre-canary remaining-gates 完整診斷。
- 正在做什麼：從 Cycle 32 blocker 往後一次稽核 Capacity、readiness、Rule 25、Publisher activation-only 與 exact-run canary 前置鏈，辨識所有 authority／state-machine／fixture mismatch。
- 現在狀態：`BOOTSTRAP_ONLY`；未收到主線 `ACTIVATE_DIAGNOSIS` 前只允許唯讀 preflight。

## Root objective

本卡只診斷，不修。禁止把任務縮成「修 plist activation mode mismatch」。目標是避免再出現「修一關 → production 跑一次 → 下一關失敗」。若 Capacity、readiness、Rule 25 對 activation phase 定義互相矛盾，必須明確判定：

`ARCHITECTURE CONTRACT MISMATCH`

最新 evidence 起點固定為 `1d608410cc9ee9adc6fc3bc53c515e4ecd4005d1`。

## 必讀證據

1. `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-RUNTIME-PROMOTION-STAGE-CONVERGENCE-CYCLE-32-20260821-RESULT.md`
2. canonical TMPDIR repair `d9e21adc9eb6439307341080f39e6d044e0492e9` 與其 tests／review RESULT。
3. Cycle 31 current readiness card／RESULT。
4. Capacity Guard source、installer、tests、receipts。
5. preactivation transition source、schema、fixtures。
6. Rule 25 receipt／gate與 current readiness generator。
7. Publisher activation-only／normal-mode contracts。
8. coordinator、four lanes、Publisher、Capacity staged＋live plist authority。

## 已知事實

- canonical TMPDIR realpath blocker 已由 `d9e21adc...` 修復，focused Publisher terminal reset suite PASS。
- Cycle 32：source promotion、manifest postcheck、coordinator＋four lanes private stage、Publisher exact-run private stage、Capacity synthetic exercise均 PASS。
- 唯一正式 `install_pantheon_content_capacity_guard_launchd.sh --preflight` 回：`NO-GO`、`preactivation_transition=rejected`、`plist activation mode mismatch`。
- 同一 raw evidence：`rss_available=false`、`rss_error=loaded_service_pid_missing:com.pantheon.agy-gemini-coordinator`、`swap_available=true`。
- Cycle 32 已正式 rollback；Cycle 31 artifacts 不得當作 current target evidence。

## Root Questions

### A. 精確 activation-mode mismatch

列出 Capacity preactivation transition 實際比較的所有 service，包括 coordinator、四 lanes、Publisher、Capacity Guard（若有 expectation）與任何額外 runtime service。每個 service 必須輸出：

- `service_label`
- `live_present`／`live_loaded`／`live_pid`
- `live_activation_mode`
- `staged_present`／`staged_activation_mode`
- `expected_preactivation_mode`
- `actual_mode_source`
- `match / mismatch`

必須指出具體 plist、欄位、expected、actual。禁止只重述錯誤字串。

### B. Transition authority 是否錯位

追出 Capacity gate 如何組合 live plist、staged plist、runtime manifest、launchctl state、Publisher activation-only／normal receipt、coordinator／lanes readiness與 previous-generation evidence。判定是否錯把「下一階段 activation-only target」與「目前 live normal cohort」做 equality，或要求新 staged cohort 等於舊 live cohort。不得改 live plist或硬改 expected string。

### C. coordinator loaded/no-PID 是否合法

由 runtime contract、installer、tests、readiness、Capacity Guard source判定這個 release phase 正確狀態是：running PID、loaded/no-PID、absent或 only staged。若 loaded/no-PID 合法，說明 telemetry authority與 PID requirement 時點；若必須有 PID，定位其缺失原因及前六服務是否其實未 runtime converge。

### D. Remaining Gate Dry Reconciliation

依序唯讀／synthetic／fixture-backed 稽核：

1. Capacity public preflight
2. Capacity staged coherence
3. current synthetic readiness
4. seven-service capability receipt
5. Rule 25 official gate
6. negative fixture
7. Publisher activation-only readiness
8. exact-run canary prerequisites

每關輸出 `Gate / Expected inputs / Current evidence / Missing evidence / Known mismatch / Would PASS|BLOCKED|UNKNOWN / Reason`。不能完全唯讀驗證時標：`UNKNOWN — requires bounded production-shaped diagnostic`，並定義最小 diagnostic；不得真的執行 production gate碰運氣。

### E. Transition State Machine

以文字 state table涵蓋 `CURRENT LIVE / PRIVATE STAGED / PREACTIVATION / ACTIVATION-ONLY / CANARY / POST-CANARY / ROLLBACK`。對 coordinator、four lanes、Publisher、Capacity Guard分別列：plist 存在、activation mode、RunAtLoad、StartInterval、KeepAlive、loaded、PID expected、child allowed、receipt authority、mutation authority。標出不同 gate 對同 phase 的定義衝突。

### F. Production vs fixture semantic gaps

稽核 fake launchctl、`tmp_path`、symlink／canonical path、loaded-service、PID、activation-mode、staged/live transition fixtures。指出未覆蓋的真實 macOS／production semantics與哪些 tests 可能只測 fake production。

## 允許範圍

- 讀 source、cards、RESULT、receipts、manifest、plist與 launchctl 的唯讀輸出。
- CodeGraph、限域 `rg`、targeted source inspection。
- 唯讀或 synthetic／fixture-backed tests。
- 必要時建立未追蹤 diagnostic script，但不得先提交；最終需刪除或保持 ignored，worktree 必須 clean。
- 只新增唯一診斷 RESULT，並以單一 commit 交付。

## 禁止範圍

- production reset、Capacity install、Publisher activation、canary。
- live／staged plist mutation、launchctl mutation、actor／manifest promotion。
- queue mutation、state reset、evidence deletion。
- tag、push、deploy、schedule。
- 修改 source、tests、config、gate、expected string或 fail-closed行為。
- 建立第三套 activation-mode truth。
- 沒查完整 chain就提出或執行第一個局部修補。
- 建立、啟動或執行下一張 repair card。

## 診斷方法與證據標準

1. CodeGraph先定位 public boundaries、callers與 state-machine seams；再讀原始碼確認。
2. 優先重播既有 Cycle 32 receipt／fixtures，建立不變更 production 的 red-capable diagnostic。
3. 每個結論附 repo-relative檔案／symbol／行號或 artifact digest；找不到即 `UNKNOWN`。
4. 分開標記 observed fact、contract interpretation、inference與 proposed scope。
5. 不以 README、註解、單一狀態字串或 Cycle 31 artifact宣稱 current target PASS。

## 唯一交付

`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-PRECANARY-REMAINING-GATES-DIAGNOSTIC-20260821-RESULT.md`

RESULT 必須包含：

1. Cycle 32 Capacity blocker精確 root cause。
2. 哪個 service／plist／欄位 activation mode mismatch。
3. coordinator loaded/no-PID是否合法。
4. Capacity transition authority是否合理。
5. remaining gate matrix。
6. transition state table。
7. production vs fixture semantic gaps。
8. 後續 blocker預測。
9. 建議修復範圍。
10. 組合判定：`FIX LOCAL CONTRACT / FIX TRANSITION MODEL / FIX TEST FIXTURE / FIX PRODUCTION RUNTIME STATE`。
11. 是否為 `ARCHITECTURE CONTRACT MISMATCH`。
12. 只給一張下一步 repair card 的建議範圍；不得建立或執行。
13. 診斷命令、測試、未執行項、唯一 commit full SHA與 clean status。

## 終局狀態

- `DIAGNOSIS_COMPLETE`：A–F與全部輸出契約均有 evidence-backed答案。
- `DIAGNOSIS_PARTIAL`：明確列出只能由 bounded production-shaped diagnostic補足的 UNKNOWN；仍不得 mutation或修復。
