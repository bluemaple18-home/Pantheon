---
id: CARD-PANTHEON-JA-CROSS-VERSION-PLAN-AUTHORITY-REPAIR-20260827
status: ready
chain_id: PANTHEON-AUTOMATION-ACCEPTANCE-20260826
parent_card: CARD-PANTHEON-AUTOMATION-ACCEPTANCE-B-TRANSLATION-PUBLIC-URL-20260826
depends_on: CARD-PANTHEON-JA-PROTECTED-SOURCE-CONSTRAINT-TRACEABILITY-REPAIR-20260827
role: implementation
cycle: 3
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 規格已固定但涉及跨版本來源身份、continuation plan authority 與 provider 成功邊界，採 strict/core-bounded 跑道；沒有未解架構岔，不升 Sol。
execution_mode: repo_only_bounded_implementation
production_mutation: forbidden
remote_mutation: forbidden
provider_calls: forbidden
service_activation: forbidden
root_cause: CROSS_VERSION_DERIVED_IDENTITY_REUSED_WITHOUT_REBINDING_PROVENANCE
---

# Pantheon JA Cross-Version Plan Authority Repair

工作名稱：修復 JA 跨版本 Plan Authority

任務簡介：讓 current source authority 重新接管 JA continuation planning，禁止無 provenance 的 legacy derived IDs 跨版本延續。

## Root Question

如何只在既有 JA continuation planning／hydration seam 內，使 current source package 成為本次 item identity authority，讓模型只引用本機建立的 request-local refs，並在 legacy mapping 缺乏 stable provenance 且與 current IDs 不一致時明確失效，而不建立 fuzzy migration、第二套 identity system 或新的 production 嘗試？

## 已裁決根因

正式 root cause：

`CROSS_VERSION_DERIVED_IDENTITY_REUSED_WITHOUT_REBINDING_PROVENANCE`

兩項事實必須同時成立：

1. 舊 `fact_id` 是 extractor／normalization 版本內的 derived identity，卻被當成可跨版本延續的 durable authority。
2. attempt 03 的 historical locale plan 只有 `source_fact_id`、section assignment 與自然語言 coverage note，沒有 stable source-span provenance，因此無法證明 `old fact_id → old source span → current fact_id`。

本卡取代任何「直接把 attempt 03 三個舊 ID 換成三個新 ID」或 fuzzy rebind 方案。前一張 protected source constraint traceability Repair 維持為已整合的下游 regression authority，不由本卡重寫。

## 固定 production 事實

- run：`auto-i18n-ja-1414b75a404721e95e74`
- source article：`V2-TAROT-DEATH-MONEY`
- locale：`ja`
- source digest：`1088d4dfae649824b9691d260e1754e528295a2b877a79a1d8e665054fe6db23`
- current source fact count：`22`
- post-Repair generation：`04`
- planning provider calls：`1`
- article provider calls：`0`
- Reviewer provider calls：`0`
- production transaction／tag／push／deploy：`0`
- generation 04 provider response 含 `22` 個 coverage items，其中 `3` 個 stale legacy IDs、缺少 `3` 個 current IDs、duplicates `0`。
- deterministic hydration 已 fail closed；不得放寬 coverage gate，也不得重跑 provider。

Repo 內 authority：

- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-AUTOMATION-ACCEPTANCE-B-TRANSLATION-PUBLIC-URL-20260826-RESULT.md`
- `artifacts/fortune_council/four_lane_runtime_execution/automation_acceptance_b_translation_public_url_20260826/evidence.md`
- `artifacts/fortune_council/four_lane_runtime_execution/automation_acceptance_b_translation_public_url_20260826/machine-summary.json`

同機 immutable fixture source（local-only，不可寫入）：

- `<local-runtime-root>/queue/translation-runs/auto-i18n-ja-1414b75a404721e95e74/brief.json`
- `<local-runtime-root>/queue/translation-runs/auto-i18n-ja-1414b75a404721e95e74/attempts/03/locale-plan.json`
- `<local-runtime-root>/queue/translation-runs/auto-i18n-ja-1414b75a404721e95e74/generations/04/external-plan.json`

`<local-runtime-root>` 只由 dispatch prompt 提供本機映射；不得把本機絕對路徑寫入 committed card、fixture、result 或 evidence。若任一來源不可讀，回 `BLOCKED / FIXTURE_SOURCE_UNAVAILABLE`，不得自造替代 fixture。

## Authority Contract

### FR-001 — Durable 與 current authority 分離

Durable authority 只包含 source text/span、source digest 與 provenance。Current extraction package 是本次 planning 的 current item authority；`fact_id`／`constraint_id` 只在 current extraction identity domain 內有效，不具跨 extractor version 的永久 authority。

### FR-002 — Legacy mapping retention／invalidation

WHEN source digest 相同，且 legacy mapping 引用的 ID set 與 current required ID set 精確相同，系統 MAY 沿用 item-level assignment。

IF 任一 legacy ID stale、任一 current ID missing、或集合有 duplicate，且 historical artifact 沒有 stable source provenance，THEN 系統 SHALL：

- 將整份 legacy item-level mapping 標記為 `INVALIDATED`；
- 禁止部分保留或猜測 old-to-current mapping；
- 禁止把 old fact IDs、old coverage notes 或舊 item assignments 放入新 prompt；
- 最多保留 section title、order、purpose 作 non-authoritative hint；
- 以 current source package 重新建立本次 planning references。

不得用 coverage note matching、normalized text similarity、embedding、LLM、手工 old-ID → new-ID 表或 historical extractor replay 建立 migration authority。

### FR-003 — Request-local source references

本機 SHALL 依 current source package 的 canonical order 建立固定、單次 request-local 的 refs，例如 `source_ref_01` 至 `source_ref_22`，並保存 ref → current `fact_id` 的本次映射。

- ref 的合法集合與值只由本機建立。
- 模型 MAY 引用／選擇既有 ref，但不得創造集合外 ref。
- ref 不得跨 request、run、generation 或 source version 成為 durable identity。
- 模型不得輸出或抄寫 `fact_id`、`constraint_id`、digest、`source_span_id` 或 authoritative hash。
- hydration 必須由本機將合法 ref 轉回 current IDs。

### FR-004 — Prompt sanitation

新 JA continuation planning prompt SHALL 證明：

- stale／legacy fact ID occurrences = `0`；
- legacy item-level assignments = `0`，若 mapping 已 invalidated；
- current request-local ref count = current source fact count；
- optional historical hint 只含不涉及 identity 的 outline／section purpose；
- current source meaning 仍完整提供給模型。

任何 invalidated legacy ID 或 item mapping 仍進 prompt時 fail closed。

### FR-005 — Provider response success boundary

Provider HTTP／transport success 不能單獨表示 planning success。JA planning result 只有依序完成下列 gate 才能標記成功：

1. JSON／既有 schema parse；
2. request-local ref membership validation；
3. exact-once coverage validation；
4. unknown／missing／duplicate ref validation；
5. local hydration to current IDs；
6. hydrated current-ID coverage validation。

不得依賴 provider enum 保證 ref 合法；provider adapter 可能移除超過八項的 enum。不得為此修改共用 provider adapter 或全語系 schema。

若 validation 失敗，JA continuation 必須 terminalize 為 planning contract failure，article／Reviewer 不得開始。若現有 provider receipt 固定記錄 transport success，必須在既有 JA seam 內使 transport status 與 planning result 可區分；不得擴張成通用 receipt／budget／FSM 重構。

## Mandatory Offline RED

先唯讀複製並固定三份真實 evidence bytes 與 SHA-256：

1. production `brief.json`；
2. attempt 03 `locale-plan.json`，代表 historical topology input；
3. generation 04 `external-plan.json`，代表已保存的 provider response。

注意：精確 `3 stale / 3 missing` 來自 generation 04 `external-plan.json` 對 current source package 的 hydration；不得誤用 attempt 03 `external-plan.json` 代替。

修前 SHALL 以完全離線測試穩定重現：

- current facts = `22`；
- returned coverage items = `22`；
- stale legacy IDs = `3`；
- missing current IDs = `3`；
- duplicates = `0`；
- coverage = `FAIL`；
- article calls = `0`；
- Reviewer calls = `0`；
- provider calls = `0`；
- production mutation = `0`。

若失敗形狀不同，回 `BLOCKED / RED_EVIDENCE_MISMATCH`，不得進 implementation。

## Offline GREEN

不得呼叫 provider。使用同一 immutable brief／historical plan，加上一份 test-only fixed current-ref response fixture，證明：

1. legacy mapping 因 stale／missing 且無 provenance 被整體標記 `INVALIDATED`；
2. old IDs 與 old item assignments 不進新 prompt；
3. current request 建立 `source_ref_01` 至 `source_ref_22`；
4. fixed response 只能引用合法 refs；
5. local hydration 後 stale = `0`、missing = `0`、duplicate = `0`；
6. current-ID coverage = `PASS`；
7. unknown／missing／duplicate ref 各有 fail-closed negative test；
8. 不宣稱恢復 attempt 03 舊 item grouping；
9. provider／network／service／production mutation = `0`。

另外必須證明：

- source brief fixture bytes 與 digest 固定；
- 原有 protected constraint omission／duplication／unresolved fixtures 全部仍通過；
- 同 source digest 且 legacy/current ID set 完全一致的 same-domain continuation 不被誤判 invalidated；
- 非 JA observable behavior 不變；
- coverage gate 未放寬。

## Call Accounting Evidence

本卡不新增 accounting schema、ledger、budget service 或 FSM。RESULT 只從既有 operation artifacts 與檔案存在性計算並列出：

- generation attempts；
- planning provider calls；
- article provider calls；
- Reviewer provider calls；
- automatic repair calls；
- terminal stage／reason。

若現有 evidence 無法無歧義計算，回 `BLOCKED / ACCOUNTING_EVIDENCE_INSUFFICIENT`，不得在本卡順手重構 lifecycle schema。

## 可改範圍

- `scripts/agy_multilingual_pipeline.py`
- `tests/test_agy_multilingual_pipeline.py`
- `tests/fixtures/agy_multilingual_pipeline/ja_plan_authority/`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-JA-CROSS-VERSION-PLAN-AUTHORITY-REPAIR-20260827-RESULT.md`
- `artifacts/fortune_council/four_lane_runtime_execution/ja_cross_version_plan_authority_repair_20260827/`

若既有檔案 owner 證明 allowlist 不足，回 `BLOCKED / ALLOWLIST_INSUFFICIENT`；不得自行擴大。

## 禁止範圍

- 禁止修改共用 provider adapter、`scripts/agy_seo_copy_pipeline.py`、Publisher、Promotion、Coordinator lifecycle、A／C、G8、publication policy、production queue/state 或已發布文章。
- 禁止修改 retry cap、model routing、全語系 translation framework 或非 JA observable behavior。
- 禁止 migration database、identity registry、historical extractor runtime、fuzzy matching engine、手工 ID mapping或第二套 planning／quality engine。
- 禁止 Writer／Reviewer provider call、生成新 JA candidate、重跑 B、啟動七個服務、network、push、tag、deploy、publication transaction或任何 remote write。
- 禁止直接修改 local-only runtime evidence；只能唯讀複製必要 bytes 成 test fixture並保存 digest／來源角色，不得在 committed artifact 寫入本機絕對路徑。
- 禁止宣稱 transport HTTP 200 等於 planning success；也禁止把共用 transport receipt 語意整體改寫。

## 停損條件

任一情況立即停止：

- RED 無法穩定重現 `3 stale / 3 missing / 0 duplicate`；
- 需要猜測 old-to-current mapping；
- 需要把 coverage note 當 identity evidence；
- 需要 historical extractor replay 才能前進；
- invalidated old ID 仍進新 prompt；
- 模型可創造集合外 source refs；
- provider／network／service／production mutation 發生；
- coverage gate 被放寬；
- 開始保存無 provenance 的 legacy item topology；
- 開始擴成全語系 migration、通用 receipt 或 accounting subsystem。

## 驗證與交付

必須交付：

1. 真實 evidence fixture 的 byte digest 與 RED reproduction。
2. RED → GREEN focused tests與各 negative ref validation test。
3. 完整 `tests/test_agy_multilingual_pipeline.py`。
4. 前一張 JA protected source constraint traceability regression。
5. coordinator translation regression。
6. fixture JSON validation、`git diff --check` 與 changed-file allowlist。
7. provider／network／service／production／remote mutation 全為 `0`。
8. RESULT、evidence與單一 candidate commit SHA。

執行線只能交付 `DELIVERED_CANDIDATE`。不得自行整合、push、回 B、建立 Reviewer／Repair／replacement thread或宣稱最終 GO。主線保留獨立 review、整合與最終驗收。

## 後續順序（本卡不執行）

```text
本卡 DELIVERED_CANDIDATE
→ 獨立 Reviewer GO
→ 主線驗收並整合
→ local main／origin main／runtime actor 收斂
→ 由 Owner 另行授權是否恢復 B
```

本卡不保證 B 最終發布成功，也不新增 production generation 授權。
