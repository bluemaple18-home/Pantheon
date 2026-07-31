---
card_id: CARD-PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731
chain_id: PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731
status: COMPLETE
user_hold: false
type: diagnostic-repair-mainline
ownership: mainline
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 跨四條 lane、Gemini broker、schema／品質 gate、Publisher 與 production canary，且涉及共享流程、外部 provider 與發布證據。
created_at: 2026-07-31
timezone: Asia/Taipei
required_base_ref: origin/main
required_base_sha: dde0cd214fea9b9e6567ed5ec7b7a82113cc836d
proposed_branch: codex/four-lane-production-output-recovery-20260731
thread_status: COMPLETE
observe_dispatch_card: CARD-PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731-RETRY-1
observe_dispatch_key: v1:fbc0ab99ea1425b00d27b384ce04942232a2bff7fcf705a70321c19ea6952f4a
observe_thread_id: 019fb598-204e-7cd0-b6b6-004b159365ba
active_base_ref: v0.3.189
active_base_sha: d9d1be2353bce1bc251e00f55d17523dcfeb18f9
rebase_backup_ref: backup/four-lane-pre-rebase-20260731
rebase_completed_at: 2026-07-31T10:26:09+08:00
observe_candidate: 63979fa6e7b2ea88011011f1655e269013e65662
checkpoint_a: GO
repair_dispatch_status: ALL_REPAIRS_INTEGRATED_AND_PRODUCTION_VERIFIED
production_acceptance_status: GO_ALL_FOUR_LANES
runtime_actor_alignment: EXACT_ORIGIN_MAIN_AFTER_EVIDENCE_CORRECTION
production_acceptance_missing: []
repair_cards_ready:
  - CARD-PANTHEON-FOUR-LANE-A2-NEW-CONTRACT-REPAIR-20260731
  - CARD-PANTHEON-FOUR-LANE-A3-REWRITE-ELIGIBILITY-DEADLOCK-REPAIR-20260731
  - CARD-PANTHEON-FOUR-LANE-A4-MULTILINGUAL-CONTRACT-NATIVE-QUALITY-REPAIR-20260731
active_repair_threads:
  - card_id: CARD-PANTHEON-FOUR-LANE-A2-NEW-CONTRACT-REPAIR-20260731
    thread_id: 019fb5d7-d3e0-72e1-92fe-ae1c0868bc61
  - card_id: CARD-PANTHEON-FOUR-LANE-A3-REWRITE-ELIGIBILITY-DEADLOCK-REPAIR-20260731
    thread_id: 019fb5d8-0aa3-7921-8da9-464fdd0115a6
  - card_id: CARD-PANTHEON-FOUR-LANE-A4-MULTILINGUAL-CONTRACT-NATIVE-QUALITY-REPAIR-20260731
    thread_id: 019fb5d8-3c6a-7c11-b507-a2f56c97a1ea
integrated_repairs:
  - card_id: CARD-PANTHEON-FOUR-LANE-A2-NEW-CONTRACT-REPAIR-20260731
    commit: 8d7a64490
  - card_id: CARD-PANTHEON-FOUR-LANE-A4-MULTILINGUAL-CONTRACT-NATIVE-QUALITY-REPAIR-20260731
    commit: 78329ebf5
  - card_id: CARD-PANTHEON-FOUR-LANE-A3-REWRITE-ELIGIBILITY-DEADLOCK-REPAIR-20260731
    commit: be6f05381
resolved_review_findings:
  - card_id: CARD-PANTHEON-FOUR-LANE-A3-REWRITE-ELIGIBILITY-DEADLOCK-REPAIR-20260731
    finding_id: A3-R1-MALFORMED-RETRY-SHAPE
external_provider_calls_authorized: true
production_mutation_authorized: true
production_authorization_received_at: 2026-07-31T10:26:09+08:00
production_authorization_scope:
  - push verified repair baseline to origin/main
  - align production runtime actor SHA
  - one controlled real canary for new
  - one controlled real canary for rewrite
  - one controlled real canary for i18n-new
  - one controlled real canary for i18n-rewrite
production_authorization_status: CONSUMED_GO
second_round_authorized: true
second_round_authorization_received_at: 2026-07-31T11:10:00+08:00
second_round_authorization_basis: 使用者在得知四條 lane 尚未完成、且第二輪包含必要 Gemini calls 與 gate 通過後的 production publish 後，明確要求「沒好就繼續」
second_round_authorization_scope:
  - repair i18n-new LocalePlanValidationError without weakening deterministic gates
  - execute the preserved new replacement job with bounded retry
  - execute one fresh controlled rewrite canary
  - execute one fresh controlled i18n-new canary after repair deployment
  - execute one fresh controlled i18n-rewrite canary
  - publish each lane only after candidate, review, dry-run and Publisher gates pass
second_round_authorization_status: CONSUMED_GO
second_round_external_call_budget: 40
second_round_transport_attempts_per_request: 3
second_round_semantic_repairs_per_run: 2
second_round_schema_repairs_per_semantic_generation: 2
second_round_replacement_runs_per_lane: 1
second_round_payload_scope:
  - content prompts
  - source facts
  - response schemas
second_round_external_destination: Google Gemini
canary_execution_sha: 66009a3014ee51ba8977b2cbd33462fc37c029ff
production_source_ref: origin/main
production_runtime_ref: exact final origin/main after evidence commit
production_release_commit: d9d1be2353bce1bc251e00f55d17523dcfeb18f9
production_release_tag: v0.3.189
production_publication_count: 4
production_public_article_count: 504
production_services_loaded: true
operations_followup_release_tag: v0.3.203
operations_followup_release_commit: 5e7b78bad0a8eb76727f71ec8946dc3673f25950
operations_followup_public_article_count: 510
operations_followup_translation_published_count: 62
operations_followup_publisher_schedule: ENABLED_60S
operations_followup_publisher_state_after_cycle: 45_MIB_NO_TRANSACTION
production_canary_attempts:
  - lane: new
    status: GO
    run_id: auto-new-v1-20260731-122-01
    article_id: V2-MBTI-PAIR-INTP-ISFP-WORK
    release_commit: 1b845702db2cd561a4559d7aa5a6bab7954ba4cb
    release_tag: v0.3.186
  - lane: rewrite
    status: GO
    run_id: legacy-auto-sweep-v1-astrology-0004-astro-love-01-retry-01
    article_id: ASTRO-LOVE-01
    release_commit: 2c1b5652b6b978335173c3382955166ec093de27
    release_tag: v0.3.187
  - lane: i18n-new
    status: GO
    run_id: auto-i18n-en-cfd7211d31136567123c-replacement-01
    article_id: V2-MBTI-PAIR-INTP-ISFP-WORK
    locale: en
    release_commit: 5fac6eb6626f54968de50f95eff97e3015a4e09e
    release_tag: v0.3.188
  - lane: i18n-rewrite
    status: GO
    run_id: auto-i18n-en-daf6984c146f81cb5738
    article_id: ASTRO-LOVE-01
    locale: en
    release_commit: d9d1be2353bce1bc251e00f55d17523dcfeb18f9
    release_tag: v0.3.189
---

# Pantheon 四條內容 Lane 端到端產出恢復卡

## 1. 任務目的

找出並修復 `new`、`rewrite`、`i18n-new`、`i18n-rewrite` 各自無法穩定產出的原因，恢復下列完整閉環：

`合格輸入 → Gemini／確定性處理 → schema 與品質 gate → candidate → Publisher → 可驗證發布結果`

本卡不接受「LaunchAgent 存在」、「last exit code = 0」或「目前 idle」作為完成證據。四條 lane 都必須各自交付新鮮、可追溯的端到端產出證據。

## 2. 根問題

哪些 lane-specific 或共用邊界，讓四條 lane 無法把合格輸入穩定轉成發布結果？最小修復是什麼，才能在不放寬品質契約、不製造無限重試、也不把 deterministic failure 誤判成 credential failure 的前提下恢復產出？

## 3. 已確認基線

觀察時間：2026-07-31 約 01:48（Asia/Taipei）。執行者開工後須重新取證，不得把本節當成永遠不變的 runtime 狀態。

1. 四個 LaunchAgent 均存在；最新觀察時 `new` 已回到 `last exit code = 0`，所以不能判定為整條 lane 永久死亡。
2. `new` 的近期主要失敗標籤是 `V4BrokerFailure`，但 broker 診斷顯示 transport 成功、`result_validation = SCHEMA_MISMATCH`；已見 `description minLength` 與正文段落 `maxLength` 違約。
3. 相同 schema-invalid request 曾輪替多個 Gemini account；這不能證明 credential outage，反而可能放大 deterministic failure。
4. 2026-07-31 00:00 後已有 5 篇 `new` 發布，public article count 由 491 增至 496；最後一次發布約在 00:53。這證明 `new` 是間歇性 contract failure，不是全域斷線。
5. Publisher actor 與 `origin/main` 當時皆在 `dde0cd214fea9b9e6567ed5ec7b7a82113cc836d`；近期 stdout 為：
   - `create idle published 0`
   - `rewrite idle rewritten 0`
   - `translation idle_rejects_only translated 0`
6. `rewrite` 最近一次確認發布約為 2026-07-30 03:36；目前 idle 不等於已證明可產出。
7. `i18n-new` 近期 en／ja／ko provider operation 已成功產生 inbox，但 pipeline 隨後以 `ValueError` 結束；問題較可能位於 transport 後的 locale／plan／pipeline 邊界，確切根因仍須重現。
8. `i18n-rewrite` 近期無新產出證據；必須先區分「沒有合格工作」與「選件／流程卡住」。
9. 最近一次確認的多語發布約為 2026-07-30 11:36；不能以 runner idle 取代新鮮的多語產出證據。

## 4. 需求契約

### BRS-4LANE-001

Pantheon 必須能讓四條內容 lane 自主、可觀測、可追溯地完成端到端產出。

### US-4LANE-001

作為維運者，我能從一致的證據判斷每條 lane 是：

- 沒有合格工作；
- 正在處理；
- 被 deterministic contract 擋住；
- provider／transport 失敗；
- Publisher 失敗；
- 已成功產出。

### US-4LANE-002

作為內容系統負責人，我能對四條 lane 各執行一個受控 canary，並看到它通過既有 schema、品質與發布契約。

### FR-4LANE-001 — 狀態語意

每條 lane 必須區分 `idle_no_eligible_work`、`processing`、`blocked`、`failed` 與 `productive`；不得以單一 `idle` 遮蔽沒有工作、reject-only 或流程異常。

### FR-4LANE-002 — 失敗分層

失敗 receipt 必須標示實際層級與封閉診斷：

- input selection；
- provider transport；
- provider output；
- schema validation；
- deterministic quality gate；
- candidate persistence；
- Publisher；
- release verification。

證據不得包含 secrets 或未封閉的原始 provider output。

### FR-4LANE-003 — New lane schema repair

`new` 必須能重現並修復近期的 min／max schema mismatch。修復應採用 prompt contract、deterministic normalization、bounded repair feedback 或其他可測方案；不得直接放寬既有品質門檻以換取綠燈。

### FR-4LANE-004 — i18n-new post-transport repair

`i18n-new` 必須定位 provider operation 成功後的 `ValueError` 邊界，補上可重現的 failing test、最小修復與封閉 failure receipt。

### FR-4LANE-005 — Rewrite lane liveness

`rewrite` 必須證明 eligible-input selection、writer／review／repair、candidate 與 Publisher 路徑皆可工作；若沒有真實 eligible backlog，先用 deterministic fixture 驗證，不得捏造 production 成果。

### FR-4LANE-006 — i18n-rewrite lane liveness

`i18n-rewrite` 必須證明來源選件、locale plan、翻譯／改寫、candidate 與 Publisher 路徑皆可工作；沒有 eligible backlog 時，必須明確回報 `idle_no_eligible_work`。

### FR-4LANE-007 — Retry 語意

Retry 必須有上限。相同 payload 的 deterministic schema／quality failure 不得耗盡 credential slot 後才回報，也不得被包成 auth outage。

### FR-4LANE-008 — Publisher contract

Publisher 必須正確接受四類合格 candidate，拒絕不合格 candidate，並留下 run ID、candidate ID、release commit／tag、產出類型與公開面驗證證據。

## 5. 完成定義

只有同時滿足以下條件，主線才可把本卡標記為完成：

### SC-4LANE-001 — 四條 lane 都有新鮮 candidate

四條 lane 各至少產生一份本次修復後的新鮮 candidate，且 writer／review／repair receipt、schema 結果與 deterministic gate 結果完整可追溯。

### SC-4LANE-002 — 四種發布結果都成立

取得明確 provider／production 授權後，四條 lane 各完成一次受控 production canary：

- `new`：新增一筆公開 article registry entry；
- `rewrite`：既有文章完成一筆 body override／rewrite release；
- `i18n-new`：新文章完成一筆 locale release；
- `i18n-rewrite`：改寫來源完成一筆 locale update／release。

每次 canary 必須在既有 bounded retry budget 內完成；若缺少合法 eligible input，狀態保持未完成並回報阻塞，不得以 fixture 冒充 production proof。

### SC-4LANE-003 — 錯誤分類正確

受控測試證明 schema／quality failure 不再被誤分類成 credential／auth failure，也不會觸發無意義的跨帳號重播。

### SC-4LANE-004 — Runtime 與發布一致

四次 canary 後：

- runtime 與 `origin/main`／Publisher actor SHA 一致；
- 無未處理 P0／P1 failure；
- queue／ledger／candidate 狀態一致；
- LaunchAgent 健康，但此項只算必要條件，不算充分條件。

### SC-4LANE-005 — 發布證據完整

每條 lane 的 final evidence 至少包含：

- source run ID；
- candidate ID；
- lane／locale；
- gate 結果；
- Publisher decision；
- release commit 與 tag；
- 公開面或生成產物驗證；
- rollback 方法與結果（若有執行）。

## 6. 工作切片與依賴

### SLICE-OBSERVE-001 — 四 lane 可重現診斷

狀態：`CURRENT_FRONTIER`

目標：

1. 重新凍結四條 lane 的 baseline。
2. 對每條 lane 建立「至少一個成功路徑或 red-capable failure」。
3. 產出 failure matrix，區分 input、provider、schema、quality、candidate、Publisher 與 release。
4. 確認真實 eligible backlog；累積 queue count 不得直接當成 backlog。

限制：唯讀診斷與本機 fixture；不得呼叫真實 provider、不得寫 production。

交付：`EV-OBSERVE-001`、`EV-FAILURE-MATRIX-001`。

### CHECKPOINT-A — 根因與拆卡

主線審查 failure matrix 後才能進入 repair。若確認為多個互不重疊根因，可建立 lane-specific 修復卡與獨立 worktree；共享檔案仍由主線唯一整合。

### SLICE-NEW-001 — New schema／retry 修復

依賴：`SLICE-OBSERVE-001`

交付：

- schema mismatch 的 red test；
- 最小修復；
- bounded repair／retry 分類測試；
- `EV-NEW-GREEN-001`。

### SLICE-I18N-NEW-001 — i18n-new ValueError 修復

依賴：`SLICE-OBSERVE-001`

交付：

- transport success 後 `ValueError` 的 red test；
- 最小修復；
- locale／plan／candidate receipt 測試；
- `EV-I18N-NEW-GREEN-001`。

### SLICE-REWRITE-001 — Rewrite liveness 修復

依賴：`SLICE-OBSERVE-001`

交付：

- eligible／ineligible selection fixture；
- writer 至 candidate 的測試；
- Publisher acceptance fixture；
- `EV-REWRITE-GREEN-001`。

### SLICE-I18N-REWRITE-001 — i18n-rewrite liveness 修復

依賴：`SLICE-OBSERVE-001`

交付：

- source／locale eligibility fixture；
- translation／rewrite 至 candidate 的測試；
- Publisher acceptance fixture；
- `EV-I18N-REWRITE-GREEN-001`。

### CHECKPOINT-B — 主線整合

依賴：四個 lane repair slice

主線須確認：

- 共享 schema／coordinator／Publisher 沒有互相回歸；
- failure taxonomy 一致；
- 所有受影響測試、生成器與 `git diff --check` 通過；
- runtime 安裝／reload 變更若非必要，不得混入。

### SLICE-REVIEW-001 — 獨立 strict review

依賴：`CHECKPOINT-B`

只做審查，不直接實作。P0／P1 必須先回 repair；P2 必須有明確 disposition。

### SLICE-CANARY-001 — 四 lane production canary

依賴：

- `SLICE-REVIEW-001 = GO`
- 使用者另行明確授權 provider calls 與 production mutation

執行順序：一次一條 lane、一次一個 canary；每次先核對 eligibility、rollback 與 bounded retry，再進下一條。

交付：

- `EV-CANARY-NEW-001`
- `EV-CANARY-REWRITE-001`
- `EV-CANARY-I18N-NEW-001`
- `EV-CANARY-I18N-REWRITE-001`

### SLICE-ACCEPT-001 — 主線最終驗收

依賴：四份 production canary evidence

核對 requirements traceability、release evidence、公開面結果與 rollback readiness，才可標記 `COMPLETE`。

## 7. 預期可改範圍

根因尚未凍結前，不把本節視為全部都要修改。只允許在證據指向時改動：

- `scripts/agy_gemini_runner.py`
- `scripts/agy_gemini_v4_broker.py`
- `scripts/agy_gemini_outbox.py`
- `scripts/agy_gemini_coordinator.py`
- `scripts/agy_seo_copy_pipeline.py`
- `scripts/agy_multilingual_pipeline.py`
- `scripts/agy_content_publisher.py`
- 對應的 `tests/`
- 必要的 fixture、schema 與封閉 evidence
- LaunchAgent template／installer 僅限證據確認 runtime contract 有問題

任何 lane-specific worktree 都必須再鎖定最小 allowlist；共享檔案不得由多個 worktree 同時修改。

## 8. 明確禁止

1. 不得放寬 min／max、品質 gate 或 reviewer 契約，只為讓結果通過。
2. 不得把 schema-invalid 或 deterministic quality failure 當成 credential outage。
3. 不得加入無上限 retry、無上限 repair loop 或無條件跨帳號輪替。
4. 未取得另行授權前，不得呼叫真實 Gemini provider、reload production runtime、push、deploy 或發布 canary。
5. 不得刪除／重置 queue、ledger、`.work`、archive 或既有 production artifacts 來製造乾淨結果。
6. 不得在 evidence 留下 secrets、cookie、token 或未封閉的原始 provider output。
7. 不得修改視覺稿、截圖或與內容 pipeline 無關的 dirty changes。
8. 不得以 synthetic fixture、process exit 0、LaunchAgent running 或 `idle` 冒充 production 產出完成。

## 9. 驗證要求

至少執行：

1. 四條 lane 的 red → green 測試。
2. 共用 coordinator／schema／Publisher 的受影響回歸測試。
3. failure classification 與 bounded retry 測試。
4. candidate persistence／idempotency／replay 測試。
5. `git diff --check`。
6. production canary 前後的 runtime SHA、queue／ledger 與 Publisher actor 檢查。
7. 四種發布結果的公開面或生成產物驗證。

若 repo 內已有更嚴格 gate，以既有 gate 為準，不得降級。

## 10. Evidence 契約

統一收斂到：

`artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731/`

必要檔案：

- `baseline.md`
- `failure-matrix.md`
- `new-red-green.md`
- `rewrite-red-green.md`
- `i18n-new-red-green.md`
- `i18n-rewrite-red-green.md`
- `integration-verification.md`
- `strict-review.md`
- `canary-new.md`
- `canary-rewrite.md`
- `canary-i18n-new.md`
- `canary-i18n-rewrite.md`
- `final-acceptance.md`

所有 runtime 數字必須帶時間戳；累積 count 不得單獨證明本次產出。

## 11. Traceability

| 需求 | Slice | 驗收證據 |
|---|---|---|
| BRS-4LANE-001 | 全部 slices | `final-acceptance.md` |
| US-4LANE-001、FR-4LANE-001、FR-4LANE-002 | SLICE-OBSERVE-001 | `baseline.md`、`failure-matrix.md` |
| FR-4LANE-003、FR-4LANE-007 | SLICE-NEW-001 | `new-red-green.md` |
| FR-4LANE-004 | SLICE-I18N-NEW-001 | `i18n-new-red-green.md` |
| FR-4LANE-005 | SLICE-REWRITE-001 | `rewrite-red-green.md` |
| FR-4LANE-006 | SLICE-I18N-REWRITE-001 | `i18n-rewrite-red-green.md` |
| FR-4LANE-008 | CHECKPOINT-B、SLICE-CANARY-001 | `integration-verification.md`、四份 canary evidence |
| US-4LANE-002、SC-4LANE-001～005 | SLICE-CANARY-001、SLICE-ACCEPT-001 | 四份 canary evidence、`final-acceptance.md` |

## 12. 停止條件

1. 同一 blocker 連續三次仍無法前進，停止並回報，不做第四次。
2. 某 lane 無法建立 red-capable reproduction，停止該 lane 修復，不可憑猜測改 code。
3. 需要真實 provider 或 production mutation 時，若未取得明確授權，停在 canary 前。
4. 發現 worktree 共享檔案重疊時，停止平行修改，交由主線整合。
5. 發現 source SHA、Publisher actor SHA 或 deployment SHA 不一致時，先修正基線，不得發布。
6. 缺少合法 eligible production input 時，該 lane 保持 `BLOCKED_INPUT`，不得用 fixture 宣稱完成。

## 13. 交付格式

最終回報必須逐 lane 分列：

- 根因；
- 修復；
- 測試；
- candidate 證據；
- production canary 證據；
- release commit／tag；
- 剩餘風險。

狀態必須明確區分：

`READY_TO_DISPATCH → DIAGNOSING → REPAIRING → INTEGRATED → REVIEW_GO → CANARY_AUTHORIZED → CANARY_VERIFIED → COMPLETE`

本卡已完成 repair、整合、strict review、四條受控 production canary 與主線
驗收。`new`、`rewrite`、`i18n-new`、`i18n-rewrite` 分別發布為
`v0.3.186`、`v0.3.187`、`v0.3.188`、`v0.3.189`；四條均有真實 candidate、
Reviewer／deterministic gate、Publisher evidence、release commit／tag 與
公開生成產物證據。六個相關 LaunchAgent 維持停止，未用 idle、服務綠燈或
fixture 取代任何 production 產出。最終判定與逐條映射見
`evidence/CARD-PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731/final-acceptance.md`。
