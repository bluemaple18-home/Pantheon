---
card_id: CARD-PANTHEON-I18N-OUTBOX-OPERATOR-TERMINALIZATION-20260801
status: COMPLETE
owner: current-thread
type: strict-production-repair
risk: high
created_at: 2026-08-01
timezone: Asia/Taipei
base_ref: origin/main
base_sha: fcc4a6a0f6b62b1b773bedfb44b43d16647f23f9
proposed_branch: codex/i18n-outbox-terminalization-20260801
implementation_commit: cd00b007bbdeac6da39a9ebb5a5da119992e3357
user_hold: false
external_provider_calls_authorized: false
production_terminalization_authorized: true
local_verification_status: PASS
production_terminalization_status: PASS
production_terminalized_at: 2026-08-01T09:49:04+08:00
mainline_status: PUSHED
production_actor_alignment: EXACT_ORIGIN_MAIN_AFTER_FINAL_RECEIPT_COMMIT
launchagents_status: SIX_RELATED_SERVICES_UNLOADED
production_authorization_basis: 使用者在得知將建立可追溯的單筆 pending retry 終止能力後明確要求「開卡做吧」。
production_authorization_scope:
  - dry-run exact pending retry identity
  - terminalize exactly one named i18n-rewrite pending retry without provider call
  - preserve request and prior failure evidence
  - keep all six related LaunchAgents unloaded
---

# Pantheon i18n outbox 單筆 operator terminalization

## 1. 目標與根問題

`i18n-rewrite` 有一筆已知不應再次送出的 `gemini-3.5-flash` transport retry。
現有 outbox 只有「runner 執行」或「保持 pending」兩條路，沒有能同時滿足
exact identity、dry-run、證據保留、run terminal state 與 idempotency 的 operator
終止介面。人工刪檔或偽造 provider failure receipt 都會破壞證據契約。

本卡只補上這個缺口，不改 provider transport、credential allocator、內容品質
gate、Publisher 或排程策略。

## 2. 已確認可沿用的經驗

1. `build_external_request`／`validate_external_request` 已鎖定 `job_id`、
   `request_sha256`、model、role 與 `transport_attempt`，直接沿用，不另建 identity。
2. `atomic_write_json` 與同一 filesystem 的 `os.replace` 已是 outbox／runner 的
   既有持久化與 claim 原語。
3. Runner 只 claim `outbox/*.json`；既有 `archive/` 保存已處理 request，適合作為
   不可執行且可追溯的 request 保存位置。
4. Coordinator `runs/*.json` 已是 active／failed／complete 的唯一 run state；
   terminalization 必須更新這份 state，不另建第二套 scheduler state。
5. Closed taxonomy、bounded retry 與 replacement lineage 保持不變；operator
   終止不是 provider response，也不得寫進 `failed/` 冒充 provider receipt。

## 3. 鎖定的 production target

- lane：`i18n-rewrite`
- run ID：`auto-i18n-ko-aff5c67c15dbae615544-replacement-01`
- job ID：`542e316fd596eb10e2b6501fb285c644fab640d7`
- logical request SHA-256：
  `85bdb1195547608e50131faa6af239ca7484fe2c63a7d0b48a4c8be342f3afb9`
- model：`gemini-3.5-flash`
- role：`writer`
- transport attempt：`1`
- closed reason：`UNSUPPORTED_MODEL_CANARY_ABORT`

執行前必須重新取證；任一欄位或路徑狀態漂移即 fail closed，不得改成「挑目前
第一筆」或批次終止。

## 4. 需求與追蹤

### US-001 — 安全終止單一 pending retry

作為維運者，我能先預覽、再以完整 identity 終止一筆仍在 outbox 的 retry，
保留原 request 與既有 provider failure evidence，並讓所屬 run 進入可稽核的
terminal state，且不發生 provider call。

- **FR-001**：預設 dry-run；只有明確 execute 才能寫入。 <!-- traces_to: US-001 -->
- **FR-002**：run ID、job ID、request SHA、model、role、attempt 全部 exact match。 <!-- traces_to: US-001 -->
- **FR-003**：只允許仍在 `outbox` 的單一 job；若已被 claim 到 `processing`，拒絕。 <!-- traces_to: US-001 -->
- **FR-004**：request 原始 bytes 移入既有 `archive/`，不得刪除或重建。 <!-- traces_to: US-001 -->
- **FR-005**：另寫 closed operator decision；不得建立 `failed/` provider receipt。 <!-- traces_to: US-001 -->
- **FR-006**：所屬 coordinator state 只可由 `active` 轉為 operator terminal failed。 <!-- traces_to: US-001 -->
- **FR-007**：相同 exact command 重跑回報 already terminalized，bytes 與 state 不再變動。 <!-- traces_to: US-001 -->
- **FR-008**：任一 identity／位置／state 衝突皆 fail closed，不得 mass cancel。 <!-- traces_to: US-001 -->

## 5. 驗收情境

1. **AS-US001-01**：dry-run 回傳完整 target／proposed action，所有檔案 bytes 不變。 <!-- traces_to: FR-001, FR-002 -->
2. **AS-US001-02**：execute 原子移出 outbox、保留 request bytes、寫 operator decision、將 run 標為 failed。 <!-- traces_to: FR-003, FR-004, FR-005, FR-006 -->
3. **AS-US001-03**：同一 exact execute 重跑為 idempotent；不改 timestamp／evidence。 <!-- traces_to: FR-007 -->
4. **AS-US001-04**：錯 run／job／SHA／model／role／attempt、processing race、非 active state 全部拒絕且零寫入。 <!-- traces_to: FR-002, FR-003, FR-008 -->
5. **AS-US001-05**：production 指定 job 終止後，outbox 為 0、archive request hash 不變、prior failed receipt hash 不變、run terminal、六個服務仍 unloaded。 <!-- traces_to: FR-004, FR-005, FR-006, FR-008 -->

## 6. 切片與驗證

### SLICE-TERM-001 — 現有 public operator seam 的 RED

- dependency：none
- traces_to：`US-001`, `FR-001`, `FR-002`, `AS-US001-01`
- verification：由 coordinator CLI 呼叫 `terminalize-pending`；現況因沒有該
  public command 而 RED，且 production fixture bytes 不動。

### SLICE-TERM-002 — 最小 exact-identity terminalization

- dependency：`SLICE-TERM-001`
- traces_to：`FR-002` 至 `FR-008`, `AS-US001-02` 至 `AS-US001-04`
- likely files：`scripts/agy_gemini_coordinator.py`、
  `tests/test_agy_gemini_coordinator.py`
- verification：focused tests 證明 dry-run、execute、identity mismatch、
  processing race、非 active state、request-byte preservation 與 idempotency。

### CHECKPOINT-A — 本機契約驗收

- focused RED→GREEN；
- `tests/test_agy_gemini_coordinator.py`；
- `tests/test_agy_gemini_outbox.py`；
- debug marker scan；
- `git diff --check`。

### SLICE-TERM-003 — 部署與 production dry-run

- dependency：`CHECKPOINT-A`
- traces_to：`FR-001`, `FR-002`, `AS-US001-05`
- verification：runtime source 與已驗證 commit／digest 對齊；六個服務 unloaded；
  dry-run exact match 且 queue／state／evidence hashes 全部不變。

### CHECKPOINT-B — 單筆 production mutation

- dependency：`SLICE-TERM-003`
- 只執行第 3 節鎖定的 target；不呼叫 Gemini、不啟動 runner／coordinator／Publisher。
- verification：outbox 0、archive 1、operator decision 1、run terminal；request 與
  prior failure evidence hash 保持；重跑 execute 為 already terminalized；六個
  LaunchAgents 仍 unloaded。

## 7. 可改與禁止範圍

可改：

- `scripts/agy_gemini_coordinator.py`
- `scripts/agy_gemini_outbox.py`（只讓既有 request identity 認得 atomic
  `.terminalizing` claim，避免中斷時重建 runnable duplicate）
- `tests/test_agy_gemini_coordinator.py`
- `tests/test_agy_gemini_outbox.py`
- 本卡與專屬 evidence receipt

禁止：

- 修改 provider／broker／credential pool／Publisher／品質 gate；
- 放寬 retry taxonomy 或增加 provider call；
- 人工刪除 outbox、state、archive、failed、inbox 或 production-attempt evidence；
- 偽造 provider receipt；
- 終止任一未在第 3 節列名的 job／run；
- 載入排程、發布文章或推送遠端，除非另有明確必要與授權。

## 8. Readiness report

- spec：`PASS`；單一 operator capability，邊界明確。
- traceability：`PASS`；US／FR／AS／slice 已互相追蹤。
- dependencies：`PASS`；沿用既有 validator、archive、atomic write、run state。
- slices：`PASS`；每片可獨立驗證，先 RED、再本機 gate、最後單筆 mutation。
- execution boundary：`PASS`；不需新 thread、不需 sub-agent、不需 provider call。

## 9. 本機驗證 receipt

- public CLI RED：`terminalize-pending` 原先為 argparse invalid choice，證明沒有
  operator seam；修復後同一 subprocess dry-run 為 GREEN。
- focused operator contract：`18 passed`（含 public CLI、split-root dry-run／
  execute、idempotency 與 fail-closed 邊界）。
- coordinator＋outbox affected suite：`221 passed`。
- repo-wide：`pytest -qq` exit `0`，只有既有 deprecation warnings。
- `git diff --check`：`PASS`。
- review 已修：symlink request 必須拒絕；operator decision `schema_version`
  必須為 `1`。
- production topology review 已修：global coordinator state root 與 lane job queue
  root 分離，decision path 以 state-root-relative lane path 記錄。
- production exact dry-run：`PASS`；request SHA、model、role、attempt、run state
  與 lane 全部相符，目標仍只在 outbox。
- pre-execute hashes：request file `5180e7ef...e8de4`；prior failed receipt
  `188bcdde...a650`；run state `269c0d7c...e61`。
- review verdict：未發現阻塞問題；production mutation 已依本卡 exact target 完成。

## 10. Production 結果

- exact execute：`terminalized`。
- lane outbox：`0` 個 runnable JSON。
- request 已原 bytes 移至 `archive/`，SHA-256 仍為
  `5180e7ef1fb0c8b7d1e9532e5fb43b29499bcdebe1ac6d4314338e828c8e8de4`。
- operator decision：`terminalized`，request file hash 與 archive 完全相同。
- global run state：`failed / OperatorTerminalized`，並記錄 lane、job、logical
  request、model、role、attempt、closed reason 與 state-root-relative decision。
- 原始 provider failure receipt SHA-256 仍為
  `188bcdde8df33f3b2ea35c5fdfe4266acc38ad9d1931568337c5b73aafdda650`。
- 相同 execute 重跑：`already_terminalized`；archive、decision、state、prior
  failure receipt 四份 hashes 均未變。
- 六個相關 LaunchAgents：全部 unloaded；Gemini calls：`0`；發布文章：`0`。
- 容量：228 GiB total、159 GiB used、20 GiB available、89%；queue 133 MiB、
  repair worktrees 193 MiB、Publisher state 51 MiB。

詳細 receipt：
`evidence/CARD-PANTHEON-I18N-OUTBOX-OPERATOR-TERMINALIZATION-20260801/production-terminalization.md`。
