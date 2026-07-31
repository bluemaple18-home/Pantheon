# 四 lane × 八層 failure matrix

## 狀態語意

- `productive`：該層有可追溯成功輸出。
- `processing`：有 fresh eligible work，尚未終態。
- `idle_no_eligible_work`：沒有可執行輸入；不代表服務健康或有產出。
- `blocked`：上游／selector／retry gate 阻止本層執行。
- `failed`：該層有封閉、可定位的終態失敗。

Locator alias 定義見 `baseline.md`。

## Matrix

| lane | 1. input selection | 2. provider transport | 3. provider output | 4. schema validation | 5. deterministic quality | 6. candidate persistence | 7. Publisher | 8. release verification |
|---|---|---|---|---|---|---|---|---|
| new | `processing`：active-floor 尚有 active run；`<queue-root>/runs/*.json` | `productive`：job `979c6d…` 成功；fresh 52 failures 的 broker outcome 也全是 SUCCESS | `failed`：fresh output 皆有 JSON，但長度 contract 不合 | `failed`：52／52 `SCHEMA_MISMATCH`；`lanes/new/failed/*.json` | `blocked`：current failures 未越過 schema；不把 schema failure 誤歸 auth | `blocked`：current failures 無 candidate；歷史 run `…077-01` 曾 productive | `idle_no_eligible_work`：current 無 approved candidate；ledger last new publish `…077-01` | `productive`（last known）：tag `v0.3.183` → `de68b6b…`；其後無新 release |
| rewrite | `blocked`：179 unattempted，但 5 clean approve 觸發 `publish_ready_first` | `productive`：job `99e382…` 於 dedicated lane 成功 | `productive`：schema-accepted response 進 inbox | `productive`：run complete，candidate 可驗 | `productive`：五筆 reviewer clean approve | `productive`：五筆 candidate preserved | `blocked`：五筆 retry `attempts=3/max=3`，`_retry_eligible=false` | `blocked`（current）；last known productive 為 `v0.3.132`／`443dc0b…` |
| i18n-new | `idle_no_eligible_work`：v0.3.183 三筆 locale run 已 failed，queue 0 | `productive`：job `72760b…` response 成功進 inbox | `productive`：provider 回傳 plan JSON | `failed`：pipeline hydration 報 `locale plan coverage mapping differs for article-01` | `blocked`：未到 deterministic article quality gate | `blocked`：run directory 只有 brief，沒有 candidate | `failed`：ledger deferred `run failed: ValueError` | `failed`（current v0.3.183 translations）；last historical i18n-new release `v0.3.173` |
| i18n-rewrite | `idle_no_eligible_work`：last legacy translation 已終態 deferred，queue 0 | `productive`：job `5bd9ff…` 成功 | `productive`：response 進 inbox | `productive`：run complete、candidate schema 成立 | `failed`：`NON_NATIVE_SEARCH_INTENT`、`AI_TEMPLATE_STYLE` | `productive`：root candidate／review 已保存 | `blocked`：`translation reviewer did not cleanly approve` | `failed`：legacy translation published count 0 |

## Cell locators

### new

- 成功 transport／candidate／release：
  - `<queue-root>/lanes/new/inbox/979c6d34181c546116e678d06c4e4197e7c0b89e.json`
  - `<queue-root>/runs/dc4e7c7f0af901a42ea8fca0.json`
  - `<production-root>/.work/gsc-copy/auto-new-v1-20260731-077-01/{candidate.json,review.json}`
  - `<publisher-state-root>/ledger.json` → version `0.3.183`
- fresh deterministic failure：
  - `<queue-root>/lanes/new/failed/c570471f71d441ee2f983b71368ba31252c61939.json`
  - aggregate query：所有 `completed_at >= 2026-07-31T07:04:29+08:00`
  - 結果：52 `V4BrokerFailure`／52 `SCHEMA_INVALID_PAYLOAD`／52
    `SCHEMA_MISMATCH`／52 provider `SUCCESS`

### rewrite

- clean approve candidate：
  - `<queue-root>/lanes/rewrite/inbox/99e382e273c10f50e287f87df1a5f7cfe53ecd27.json`
  - `<queue-root>/runs/00ba7432253f48bc48c21fe0.json`
  - `<production-root>/.work/gsc-copy/legacy-auto-sweep-v1-interpersonal-0007-theme-interpersonal-07/{candidate.json,review.json}`
- exhausted Publisher retry：
  - `<publisher-state-root>/retry/rewrite/legacy-auto-sweep-v1-interpersonal-000{3,4,5,6,7}-theme-interpersonal-0{3,4,5,6,7}.json`
  - 每筆 `attempts=3`、`eligibility=exhausted`、`candidate_preserved=true`
- shared source seam：
  - `scripts/agy_gemini_coordinator.py::seed_legacy_rewrite_runs`
  - `scripts/agy_content_publisher.py::_retry_eligible`
  - `scripts/agy_content_publisher.py::collect_ready_rewrite_runs`

### i18n-new

- response／terminal state：
  - `<queue-root>/lanes/i18n-new/inbox/72760b166343c0582f708316ca9f695fc6454eac.json`
  - `<queue-root>/runs/ed5eff76a05354b690e9a013.json`
  - `<queue-root>/translation-runs/auto-i18n-ko-d069fa6b3a94ae07bbd8/brief.json`
- Publisher：
  - `<publisher-state-root>/ledger.json` →
    `translation_deferred_runs[run_id=auto-i18n-ko-d069fa6b3a94ae07bbd8]`
- red-capable seam：
  - `scripts/agy_multilingual_pipeline.py::_hydrate_locale_plan`
  - `scripts/agy_multilingual_pipeline.py::validate_locale_plan`

### i18n-rewrite

- response／candidate：
  - `<queue-root>/lanes/i18n-rewrite/inbox/5bd9ff383544c14b11baae65e586643cdcfd350e.json`
  - `<queue-root>/runs/39e90f7ee2affaaa94eff5b6.json`
  - `<queue-root>/translation-runs/auto-i18n-ko-149a513358e0e81cadcd/{candidate.json,review.json}`
- Publisher：
  - `<publisher-state-root>/ledger.json` →
    `translation_deferred_runs[run_id=auto-i18n-ko-149a513358e0e81cadcd]`
- quality seam：
  - `scripts/agy_multilingual_pipeline.py::translation_findings`
  - `scripts/agy_content_publisher.py::collect_ready_translation_runs`

## Root cause 分層

### Shared／cross-lane

1. **Runtime identity blocker**
   - source／local origin：`de68b6b…`
   - installed actor／expected actor：`dde0cd2…`
   - runtime digest 本身相符，但 exact SHA 不符合本卡 stop condition。
   - 影響：任何 repair/canary 前必須先由唯一 ops owner 對齊 actor contract。

2. **Coordinator 與 Publisher 的 eligibility 語意不一致**
   - coordinator 把 `clean_approve > 0` 視為必須先 publish。
   - Publisher 把 exhausted retry 排除於 ready selection。
   - 結果：rewrite 有 candidate、也有 179 unattempted inventory，兩端都不前進。

3. **Liveness 訊號不可當 productivity**
   - coordinator／三個 idle lane／Publisher 最近可 exit 0；
   - new lane exit 1；
   - 真實 productive 狀態必須由 run、candidate、ledger 與 release SHA 證明。

### Lane-specific

1. **new：provider output 長度 contract**
   - fresh 52 筆 provider process 都 SUCCESS，payload 全部 schema mismatch。
   - error 是 `maxLength`／`minLength`，不得分類為 credential outage。
   - active-floor 持續補不同新 run，讓 deterministic failure 擴散到更多 input；
     job-level沒有保存 raw output或允許 automatic resend，不代表 orchestration 已止血。

2. **rewrite：release-gate retry exhausted**
   - candidate 與 reviewer 已 clean approve。
   - 三次 pytest release gate exit 1 後被永久跳過。
   - 本 slice 未取得足以安全重設 retry 的授權，也未重跑會套用 candidate 的
     production transaction；維持封閉 blocker。

3. **i18n-new：locale-plan coverage contract**
   - transport 與 broker response schema 已成功。
   - application hydration 要求每個 source fact 有唯一 coverage mapping；
     fresh ko response 未滿足，ValueError 在 candidate 前發生。

4. **i18n-rewrite：母語品質拒絕**
   - candidate persistence 成功。
   - reviewer 命中 `NON_NATIVE_SEARCH_INTENT` 與 `AI_TEMPLATE_STYLE`。
   - 這是品質 gate 正確拒絕，不應放寬 gate 或假裝 productive。

## Checkpoint A 拆卡建議

以下為建議，不代表已建立 thread。每張卡的 code allowlist 互斥：

| 建議卡 | 唯一 owner | 建議 code allowlist | 驗收重點 |
|---|---|---|---|
| A1 — runtime actor identity alignment | ops/runtime owner | `scripts/install_agy_gemini_coordinator_launchd.sh`、`scripts/install_agy_content_publisher_launchd.sh`、`ops/launchd/com.pantheon.agy-*.plist.example` | source／actor／expected SHA exact；需另取 deploy/reload 授權 |
| A2 — new output contract fail-closed repair | new contract owner | `scripts/agy_seo_copy_pipeline.py`、`scripts/agy_gemini_runner.py`、`tests/test_agy_seo_copy_pipeline.py`、`tests/test_agy_gemini_outbox.py` | 不放寬 min/max；fixture 重現 paragraph length mismatch；相同 deterministic class 不擴散新 run |
| A3 — rewrite eligibility deadlock repair | shared scheduler owner | `scripts/agy_gemini_coordinator.py`、`scripts/agy_content_publisher.py`、`tests/test_agy_gemini_coordinator.py`、`tests/test_agy_content_publisher.py` | coordinator／Publisher 對 exhausted clean-approve 有單一終態；不重置 retry、不自動無限重試 |
| A4 — multilingual contract／native quality repair | multilingual owner | `scripts/agy_multilingual_pipeline.py`、`tests/test_agy_multilingual_pipeline.py` | i18n-new coverage mapping 可 red→green；i18n-rewrite 保留母語 gate，4-of-4 不降級 |

A2 不擁有 coordinator；A3 不擁有 runner／SEO contract；A4 是
`agy_multilingual_pipeline.py` 的唯一 owner，避免 i18n-new 與
i18n-rewrite 兩卡同改共享檔。

## Checkpoint A 建議結論

建議順序：

1. A1 先對齊 runtime identity。
2. A2、A3、A4 再從同一 verified actor/source 基線各自建立 candidate。
3. mainline 做獨立 review 與整合。
4. 只有另行授權後才做 provider canary、deploy、reload 或 publish。

本 task 不建立上述卡片、不執行 repair、不宣稱 Checkpoint A 已接受。
