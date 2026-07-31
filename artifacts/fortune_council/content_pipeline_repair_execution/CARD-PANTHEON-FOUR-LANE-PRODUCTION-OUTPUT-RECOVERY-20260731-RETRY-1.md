---
card_id: CARD-PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731-RETRY-1
chain_id: PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731
parent_card_id: CARD-PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731
role: implementation
cycle: 0
status: DELIVERED_CANDIDATE
user_hold: false
type: diagnostic-observe-successor
ownership: SLICE-OBSERVE-001 only; mainline retains Checkpoint A, repair slicing, integration, review, canary authorization, and acceptance
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 四條 lane 共用 Gemini broker、schema／品質 gate 與 Publisher；本輪只凍結根因與 failure matrix，避免未確診前平行修改共享流程。
project_id: c2xpbmdzaG90OmVudl9lXzZhMTdiMzc4MTg1ODgzMmRhZWU4Njk3YzMwZmM3ZTdjCi9Vc2Vycy9tYXR0a3VvL0RvY3VtZW50cy9QYW50aGVvbg==
repo_identity: github.com/bluemaple18-home/Pantheon
required_base_ref: v0.3.183
required_base_sha: de68b6b283493a3e9ca5f80286c682cb7846735e
source_origin_main_at_freeze: de68b6b283493a3e9ca5f80286c682cb7846735e
proposed_branch: codex/four-lane-production-output-recovery-20260731-retry-1
thread_status: RUNNING
dispatch_key: v1:fbc0ab99ea1425b00d27b384ce04942232a2bff7fcf705a70321c19ea6952f4a
formal_thread_id: 019fb598-204e-7cd0-b6b6-004b159365ba
activation_state: BOUND
worktree: <codex-home>/worktrees/739b54d6-2661-4e6a-9bf1-a7505f013595/Pantheon
candidate_commit: 63979fa6e7b2ea88011011f1655e269013e65662
candidate_parent: de68b6b283493a3e9ca5f80286c682cb7846735e
supersedes_dispatch_key: v1:3dc5b577b0a24987083ade7b817d666018e78da7190ba28d742616c00ffc8be1
supersedes_thread_id: 019fb593-406b-7212-8b17-25daa2f63c8e
supersession_reason: BASE_SHA_MISMATCH
external_provider_calls_authorized: false
production_mutation_authorized: false
created_at: 2026-07-31
timezone: Asia/Taipei
---

# Pantheon 四條內容 Lane 診斷恢復卡 — RETRY-1

## 五行派工契約

1. 目標：只完成根卡的 `SLICE-OBSERVE-001`，重新凍結 `new`、`rewrite`、`i18n-new`、`i18n-rewrite` 基線並產出封閉 failure matrix。
2. 可改：本卡專屬診斷 evidence；production code、共享 schema、coordinator 與 Publisher 只讀。
3. 禁止：真實 Gemini/provider call、production mutation、push、deploy、reload、publish、queue／ledger 重置，以及以 `idle`、服務綠燈或 fixture 冒充產出。
4. 驗證：四 lane 各有成功路徑證據或 red-capable failure；失敗分層到 input、transport、provider output、schema、quality、candidate、Publisher、release。
5. 交付：只交 evidence candidate commit 與 Checkpoint A 拆卡建議；不得宣稱 repair、canary 或整張根卡完成。

## Root question

哪些 lane-specific 或共用邊界，讓四條 lane 無法把合格輸入穩定轉成發布結果？在不放寬品質契約、不製造無限重試、也不把 deterministic failure 誤判成 credential failure的前提下，後續最小修復應如何切卡？

## 已知基線與重取證義務

- 原始根卡凍結於 `dde0cd214fea9b9e6567ed5ec7b7a82113cc836d`。
- 第一次正式 thread 建立時，`origin/main` 已前進到 `de68b6b283493a3e9ca5f80286c682cb7846735e`，因此未 activation、未開始實作。
- `dde0cd2..de68b6b` 為五筆內容發布 commit，tag 為 `v0.3.179` 至 `v0.3.183`。
- 本 successor 以不可移動 tag `v0.3.183` 鎖定 `de68b6b283493a3e9ca5f80286c682cb7846735e`。
- 執行者仍須以帶時間戳的新證據重新觀察 runtime；本節不得當成永遠不變的 production truth。

## 本輪唯一責任

1. 驗證 formal worktree 的 HEAD 精確等於 `de68b6b283493a3e9ca5f80286c682cb7846735e` 且 clean。
2. 執行 worktree capability preflight；source exploration 前依專案規範查 CodeGraph。
3. 以唯讀 runtime／artifact／log 檢查重新凍結四 lane 基線。
4. 對每條 lane 建立至少一個已驗證成功路徑，或一個可被後續 red test 重現的封閉 failure。
5. 區分真實 eligible backlog 與累積 queue count。
6. 產出 lane-by-layer failure matrix 與 Checkpoint A 拆卡建議。
7. 只提交本輪 evidence candidate；主線決定後續 lane-specific 或 shared repair ownership。

## Allowlist

只允許新增或修改：

- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731/baseline.md`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731/failure-matrix.md`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-FOUR-LANE-PRODUCTION-OUTPUT-RECOVERY-20260731/observe-verification.md`

可唯讀檢查：

- `scripts/agy_gemini_runner.py`
- `scripts/agy_gemini_v4_broker.py`
- `scripts/agy_gemini_outbox.py`
- `scripts/agy_gemini_coordinator.py`
- `scripts/agy_seo_copy_pipeline.py`
- `scripts/agy_multilingual_pipeline.py`
- `scripts/agy_content_publisher.py`
- 對應 `tests/`、fixture、schema、封閉 runtime evidence

## Forbidden scope

- 不得修改 production code、tests、fixture、schema、LaunchAgent template／installer。
- 不得呼叫真實 Gemini 或其他 provider。
- 不得 push、deploy、reload production runtime 或發布 canary。
- 不得刪除、重置或手改 queue、ledger、`.work`、archive、candidate 或 production artifact。
- 不得讀出或保存 secret、cookie、token 或未封閉的原始 provider output。
- 不得放寬 min／max、品質 gate、reviewer 契約或 retry budget。
- 不得把 schema／quality failure分類為 credential／auth outage。
- 不得自行建立 Repair、Review、replacement 或其他 thread。

## Failure matrix contract

每條 lane 都必須逐層標示 evidence-backed 狀態：

1. input selection；
2. provider transport；
3. provider output；
4. schema validation；
5. deterministic quality gate；
6. candidate persistence；
7. Publisher；
8. release verification。

狀態只能使用明確語意，例如：

- `idle_no_eligible_work`
- `processing`
- `blocked`
- `failed`
- `productive`

`idle`、process exit 0、LaunchAgent running 或累積 count 不能單獨證明 productive。

## Evidence contract

`baseline.md` 至少包含：

- 觀察時間與 timezone；
- worktree／source SHA；
- runtime／Publisher actor SHA；
- 各 lane eligible input 判定；
- queue／ledger／candidate 摘要；
- 最近一筆可追溯成功或失敗；
- secrets redaction 說明。

`failure-matrix.md` 至少包含：

- 四 lane × 八層 failure matrix；
- 每格 evidence locator；
- shared root cause 與 lane-specific root cause 分離；
- deterministic、provider、Publisher 與 release failure 分類；
- Checkpoint A 建議卡片、ownership 與互斥 allowlist。

`observe-verification.md` 至少包含：

- 實際執行的唯讀命令／查詢；
- CodeGraph query 與原始碼確認摘要；
- 未執行 provider／production mutation 的證據；
- `git diff --check`；
- changed files；
- candidate commit SHA。

## Acceptance

只有同時滿足以下條件才可交付 `DELIVERED_CANDIDATE`：

1. 四條 lane 都有新鮮、帶時間戳且可追溯的 baseline。
2. 四條 lane 都有一條已證明的成功路徑或 red-capable failure；若沒有 eligible work，明確標記 `idle_no_eligible_work`。
3. failure matrix 能把 input、provider、schema、quality、candidate、Publisher、release 分開。
4. 無真實 provider call、production mutation、push、deploy、reload 或 publish。
5. changed files 僅限三份 allowlist evidence。
6. `git diff --check` 通過。
7. 以單一 candidate commit 交回主線；不得宣稱 repair、integration、review、canary 或 root card complete。

## Stop conditions

- 同一 blocker 連續三次仍無法前進，停止，不做第四次。
- 任一 lane 無法形成 evidence-backed success 或 red-capable failure，標記 blocker，不憑猜測改 code。
- 需要真實 provider 或 production mutation時立即停止，等待使用者另行授權。
- source、runtime、Publisher actor SHA 不一致時先記錄基線阻塞，不發布。
- 發現應由多張卡修改同一共享檔時，交回主線決定唯一 owner。

## Supersession handoff

- Previous dispatch：`v1:3dc5b577b0a24987083ade7b817d666018e78da7190ba28d742616c00ffc8be1`
- Previous thread：`019fb593-406b-7212-8b17-25daa2f63c8e`
- Previous result：bootstrap-only；clean worktree；無 activation token；無修改、測試、commit、provider call 或 production mutation。
- Previous unique work：none。
- Previous thread/worktree 不得重用，不得由本 task 清理或封存。
- 本卡僅建立新的 dispatch identity；不自證 previous resource cleanup。
