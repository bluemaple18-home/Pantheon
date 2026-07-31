---
card_id: CARD-PANTHEON-I18N-BOUNDED-REPLACEMENT-RECOVERY-20260731
status: DEPLOYED_CANARY_BLOCKED_PROVIDER
owner: current-thread
base_ref: origin/main
base_sha_at_triage: 6ba4692b7
initial_implementation_base_sha: 523ad3e4c
verified_mainline_sha: 2066de2c2
implementation_branch: codex/i18n-bounded-replacement-20260731
implementation_commit: 7002e135f
deployed_main_sha: 7002e135f
deployed_actor_sha: 7002e135f
user_hold: false
production_canary_hold: true
jira: not-applicable
jira_reason: 本卡在既有本機內容管線內修復，不建立外部 Jira。
---

# Pantheon i18n bounded replacement recovery

## 1. 目標與根問題

`i18n-new`、`i18n-rewrite` 排程仍活著，但 terminal translation run 不會再次
eligible，導致 locale release 長時間沒有前進。修復必須沿用既有 bounded
transport retry、credential pool、lane state 與 Publisher gate，不建立第二套
runner，也不放寬 locale-plan、fact、語言或 Reviewer 驗證。

## 2. 已確認可沿用的經驗

1. `OUTBOX_MAX_TRANSPORT_RETRIES = 2` 已存在；同一 logical request 使用相同
   `request_sha256`，`transport_attempt` 已在 production 觀察到 `0 → 1 → 2`。
2. `NETWORK` 已在既有 closed taxonomy 的 retry allowlist；`AUTH`、`QUOTA`、
   `MODEL_UNAVAILABLE`、`CLI_UNAVAILABLE` 保持 terminal。
3. 先前 `i18n-new` 以單一 `-replacement-01` 完成 v0.3.188，證明 replacement
   lineage 可行；本卡把該人工做法收斂成 deterministic、最多一次的 scheduler
   行為。
4. 先前 locale-plan 修復的原則保持不變：exact fact set、唯一性、safety、
   target language、source SHA 與 outline authority 全部 fail closed；缺 fact 或
   語言不符不得 canonicalize 成通過。
5. rewrite 已有 bounded retry lineage 與 terminal-state inventory，可重用其
   「新 run ID、不覆寫舊 evidence、不產生無上限 loop」模式。

## 3. 現況證據

- Translation ledger 最新 release 仍為 v0.3.189；new／rewrite 已持續前進。
- 保存 response 的 deterministic replay 已重現：
  - `auto-i18n-ja-51825f8b2fad8aa574dd`：
    `locale plan native locale language differs`；
  - `auto-i18n-en-082928fb9b16d6dbb2fc`：
    `external locale plan source fact coverage differs`。
- Production archive 已出現 transport attempts 0、1、2，否證「NETWORK 完全
  沒有 retry」。
- terminal state 目前不會由 `enqueue_article_translations` 重新啟用；同一
  deterministic run identity 永遠維持 terminal。

## 4. 需求

### Canonical trace markers

#### i18n terminal run 有限恢復 <!-- US-001 -->

- **FR-001**: 保留既有 transport retry。 <!-- FR-001 traces_to: US-001 -->
- **FR-002**: 使用封閉 replacement eligibility。 <!-- FR-002 traces_to: US-001 -->
- **FR-003**: 每個 base run 最多一個 replacement。 <!-- FR-003 traces_to: US-001 -->
- **FR-004**: 保留 source identity 與原 evidence。 <!-- FR-004 traces_to: US-001 -->
- **FR-005**: 每 lane／cycle 有固定上限。 <!-- FR-005 traces_to: US-001 -->
- **FR-006**: 不放寬 deterministic、Reviewer 或 Publisher gate。 <!-- FR-006 traces_to: US-001 -->

1. **Given** eligible i18n-new terminal run，建立且只建立一個 replacement。 <!-- AS-US001-01 traces_to: FR-001, FR-002, FR-003, FR-004, FR-005 -->
2. **Given** eligible i18n-rewrite terminal run，建立且只建立一個 replacement。 <!-- AS-US001-02 traces_to: FR-001, FR-002, FR-003, FR-004, FR-005 -->
3. **Given** terminal category 不在 allowlist，不建立 replacement、不放寬 gate。 <!-- AS-US001-03 traces_to: FR-002, FR-006 -->
4. **Given** source SHA drift，不建立 replacement、不覆寫 evidence。 <!-- AS-US001-04 traces_to: FR-004 -->

- **SC-001**: 先 RED、同一 public behavior 再 GREEN。 <!-- SC-001 traces_to: US-001 -->
- **SC-002**: i18n-new／i18n-rewrite fixture 均證明 bounded replacement。 <!-- SC-002 traces_to: US-001, FR-003, FR-004 -->
- **SC-003**: 受影響回歸、diff check 與 debug marker scan 通過。 <!-- SC-003 traces_to: US-001, FR-006 -->
- **SC-004**: Production canary 保持另行授權。 <!-- SC-004 traces_to: US-001, FR-006 -->

### US-001 — i18n terminal run 有限恢復

作為內容排程，我需要對已用盡既有 transport／plan 嘗試且符合封閉條件的
translation run 建立一次 replacement，讓偶發 provider／plan 失敗不會永久
封死該 locale，同時不增加無上限外呼。

### FR-001 — 保留既有 transport retry

不得改寫 credential allocator、provider 呼叫或 `0 → 1 → 2` logical-request
retry。Replacement 發生在原 run 進入 terminal 後，不得與 transport retry
混成同一層。

### FR-002 — 封閉 replacement eligibility

只允許下列 terminal 狀態建立 replacement：

- `LocalePlanValidationError`；
- 已由既有 transport budget 用盡後才上浮的 `NETWORK`；
- 已由既有 transport budget 用盡後才上浮的
  `SCHEMA_INVALID_PAYLOAD`／`PROVIDER_UNAVAILABLE`。

`AUTH`、`QUOTA`、`MODEL_UNAVAILABLE`、`CLI_UNAVAILABLE`、
`INVALID_RECEIPT`、source drift、candidate／Reviewer quality rejection 不得
建立 replacement。

### FR-003 — 一次上限與 lineage

每個 base translation run 最多建立一個 `-replacement-01`。重複 cycle 必須
idempotent；replacement 自己失敗後不得建立 `replacement-02`。

### FR-004 — Identity 與 evidence 不可變

Replacement 必須保留 locale、source article ID、source path、source SHA 與
完整 source snapshot；原 brief、state、attempts、failure receipts 不得覆寫。
新 state 必須記錄 `replacement_of` 與 closed recovery reason。

### FR-005 — Lane 公平與限速

每個 coordinator cycle 每條 i18n lane 最多補一個 replacement；不得影響
`new`、`rewrite` 推進，也不得一次掃出無界工作量。

### FR-006 — Gate 不放寬

不得降低 locale plan、coverage、native language、source fact、safety、
candidate、Reviewer、Publisher 或 release gate。Fixture、`idle`、服務綠燈
不能冒充 production release。

## 5. 驗收情境

### AS-US001-01 — i18n-new 建立一次 replacement

給定 terminal `i18n-new` run 為 eligible failure，cycle 建立一個 active
`replacement-01`；再次 cycle 不新增第二個，原 evidence bytes 不變。

### AS-US001-02 — i18n-rewrite 建立一次 replacement

同上，且 lane 由 source lineage 正確歸為 `i18n-rewrite`。

### AS-US001-03 — terminal 類別保持封閉

AUTH／QUOTA／source drift／quality rejection fixture 不建立 replacement，
且回報 closed skip reason。

### AS-US001-04 — source identity fail closed

若 current source 與 terminal brief 的 source SHA 不一致，不建立 replacement、
不覆寫 source snapshot。

## 6. 成功準則

### SC-001 — RED／GREEN

先執行一條可重現「eligible terminal run 目前不會產生 replacement」的失敗
測試；最小修補後同一測試 GREEN。

### SC-002 — 雙 Lane fixture

`i18n-new`、`i18n-rewrite` 各有一個 deterministic replacement lifecycle
測試，包含 idempotency、lineage、source SHA 與原 evidence 不變。

### SC-003 — 邊界回歸

既有 transport retry、terminal taxonomy、locale plan、coordinator lane fairness
測試全數通過；`git diff --check` 通過，且無 `[DBG-` 殘留。

### SC-004 — Production 證據另鎖

本地修復完成不等於 production 完成。只有另行取得外部 Gemini／部署授權後，
`i18n-new`、`i18n-rewrite` 各一筆真實 locale release 才能解除
`production_canary_hold`。

## 7. 切片與依賴

### SLICE-I18N-REPL-001 — terminal inventory 與 RED

- `traces_to`: `US-001`, `FR-002`, `FR-003`, `SC-001`
- dependency: none
- verification: 單一 coordinator／enqueue public behavior test 必須因沒有
  replacement 而 RED。
- likely files: `tests/test_agy_multilingual_pipeline.py`、
  `tests/test_agy_gemini_coordinator.py`

### SLICE-I18N-REPL-002 — 最小 replacement helper

- `traces_to`: `US-001`, `FR-003`, `FR-004`, `AS-US001-04`, `SC-002`
- dependency: `SLICE-I18N-REPL-001`
- verification: helper 對兩類 lane 建立同一契約的單一 replacement，重跑
  idempotent。
- likely file: `scripts/agy_multilingual_pipeline.py`

### SLICE-I18N-REPL-003 — coordinator bounded scheduling

- `traces_to`: `US-001`, `FR-002`, `FR-005`, `AS-US001-01`,
  `AS-US001-02`, `AS-US001-03`
- dependency: `SLICE-I18N-REPL-002`
- verification: 每 lane／cycle 上限、其他 lane 不受阻塞、closed skip reasons。
- likely files: `scripts/agy_gemini_coordinator.py`、
  `tests/test_agy_gemini_coordinator.py`

### SLICE-I18N-REPL-004 — 回歸與證據

- `traces_to`: `SC-003`, `SC-004`
- dependency: `SLICE-I18N-REPL-003`
- verification: focused tests、受影響 suites、`git diff --check`、debug marker
  scan；只記錄本地 evidence，不呼叫 Gemini、不部署。

完成狀態：`SLICE-I18N-REPL-001` 至 `SLICE-I18N-REPL-004` 均已完成；修復已
無衝突重放到 `v0.3.221`、推送並部署為 `7002e135f`。Production canary 因
provider unavailable 尚未產生 candidate 或 release，仍由 `SC-004` 鎖定。

## 8. 可改與禁止範圍

可改：

- `scripts/agy_multilingual_pipeline.py`
- `scripts/agy_gemini_coordinator.py`
- 對應測試
- 本卡 evidence receipt

禁止：

- 重寫 `agy_gemini_runner.py`、credential pool 或 Publisher；
- 增加無上限 retry／跨帳號無條件輪替；
- 放寬任何 deterministic／Reviewer／Publisher gate；
- 修改 production queue、既有 run／receipt、launchd 或遠端 `main`；
- 呼叫 Gemini、部署、publish 或 canary，除非另有明確授權。

## 9. 交付格式

- 根因與被否證假說；
- 沿用的既有機制；
- RED command／failure；
- GREEN command／result；
- changed files／diff scope；
- production canary hold 與剩餘風險。
