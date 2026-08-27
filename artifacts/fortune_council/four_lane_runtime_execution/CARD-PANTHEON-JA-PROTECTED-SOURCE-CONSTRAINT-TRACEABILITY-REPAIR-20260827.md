---
id: CARD-PANTHEON-JA-PROTECTED-SOURCE-CONSTRAINT-TRACEABILITY-REPAIR
status: ready
chain_id: PANTHEON-AUTOMATION-ACCEPTANCE-20260826
parent_card: CARD-PANTHEON-AUTOMATION-ACCEPTANCE-B-TRANSLATION-PUBLIC-URL-20260826
supersedes: CARD-PANTHEON-JA-TRANSLATION-BOUNDARY-CONTRACT-REPAIR
role: repair
cycle: 2
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
execution_mode: repo_only_bounded_repair
production_mutation: forbidden
root_cause: TRANSLATION_BOUNDARY_CONTRACT_OSCILLATION
---

# Pantheon JA Protected Source Constraint Traceability Repair

工作名稱：JA Protected Source Constraint Traceability Repair

## Root Question

如何只在既有 JA translation seam 內，保留原始 source span 與 provenance，讓 heuristic boundary candidate 經過明確、可重算的 disposition 後形成去重 protected constraints，並在未知分類時 fail closed，而不再以刪字 normalization 或全設 `safety_boundary=false` 靜默丟失來源限制？

## 已裁決根因與前卡 NO-GO

正式 root cause 維持：`TRANSLATION_BOUNDARY_CONTRACT_OSCILLATION`。

前卡三個 candidate `96a7fd4c90`、`78fe095f61`、`f4f7c149aa` 均未整合：

- 第一版新增 boundary contract，但 planner／Writer 仍收到 14 個逐段 safety facts。
- 第二版以 regex／整句移除 normalization 產生 `但。`、`也。`、`文章。`、`然而。` 等破句，並誤刪 substantive claim。
- 第三版仍可能留下殘缺 derived fact，且把所有 JA source facts 的 `safety_boundary` 強制改成 false；未被三類 classifier 識別的「不得用於醫療診斷／不得自行停藥」會沒有 contract、沒有 disposition、沒有 fail-closed finding。

主線撤回「heuristic `safety_boundary=true` 永遠不可改成 false」的過強主張。不可變的是同一 source version／run 內的原始 source span、文字、digest 與 provenance；heuristic classification 可以重算，但不得沒有 disposition 地消失。

## 目的與範圍

### BRS-001

在 Automation Acceptance B 再產生任何 fresh JA candidate 前，修復 source constraint 的可追溯性與 fail-closed 缺口，同時保留 candidate 2／3 已證明的 omission 與 duplication 分流。

### StRS-001

JA Writer、deterministic translation validation 與 Reviewer 必須共用同一份 protected constraint view；來源 span 保持可追溯，重複語意可合併，false positive 可明確排除，未知分類不得放行。

## 最小資料契約

### FR-001 — Immutable source authority

系統 SHALL 對每個 source field 保留同一 source version／run 內不可變的：

- `source_span_id`
- `field_path`
- `source_text`
- `source_digest`
- `provenance`：`source` 或既有 `publication_policy`

`source_span_id` SHALL 由穩定來源位置與 source digest 導出，例如 `source_digest + field_path + ordinal`；不得由 normalization 後文字導出。來源改版後建立新 digest／新 authority，不宣稱跨版本永遠 immutable。

不得覆寫、截短或 regex 改寫 `source_text` 來形成 canonical authority。若需要 derived text，它只能是可丟棄 projection，且原 span 必須仍可重建。

### FR-002 — Boundary candidate disposition

每個由既有 heuristic 偵測出的 JA boundary candidate SHALL 恰有一個可重算 disposition：

- `PRESERVED`：對應一個 normalized protected constraint。
- `MERGED_DUPLICATE`：與語意等價 constraint 合併，保留全部 `source_span_ids[]`。
- `NOT_A_BOUNDARY`：附 deterministic `reason_code`；不得只存自由文字理由。
- `UNRESOLVED`：分類無可靠依據，必須 fail closed。

禁止把 heuristic hit 直接升格為 canonical safety truth；也禁止將它改成 false 後無 disposition 消失。

### FR-003 — Normalized protected constraints

每個 protected constraint SHALL 至少包含：

- `constraint_id`
- `category`
- `source_span_ids[]`
- `required_fields[]`
- source／policy provenance

既有 JA categories 維持：

- `outcome_not_determined`
- `contextual_or_general_interpretation`
- `professional_advice_non_substitution`，只在 source 或既有 policy 要求時成立。

同 category 不代表同一 constraint。「不得作醫療診斷」與「不得自行停藥」不得只因同屬 medical／professional context 而合併；只有語意等價的重複 span 才能 `MERGED_DUPLICATE`。

### FR-004 — Writer／Reviewer authority

Writer／locale planner SHALL 以 normalized protected constraints 承擔 boundary coverage，不得再把每個重複 boilerplate span 當成獨立 safety requirement。

原始 `source_text` 仍供 provenance／claim trace；若 prompt 中保留原始段落，必須明示 boundary spans 只透過 normalized constraints 實現，不得逐段複製。不得以破壞 source claim 的字串刪除來製造 Writer authority。

同一份 constraint view SHALL 提供給：

- JA locale planner／Writer
- deterministic translation validation
- 既有 JA Reviewer prompt

History 只供 trace／診斷；不得成為 mutable authority，也不得串接歷輪自然語言 findings。

### FR-005 — Existing quality seam only

沿用既有 `brief → source fact package → deterministic findings → Reviewer` 流程與既有檔案 owner。不得新增 ledger、registry、database、通用 constraint runtime、第二套 Reviewer 或全語系 framework。

Finding 維持最小集合：

- target 沒有 required meaning，或否定／條件／非專業替代語意失真：`BOUNDARY_MEANING_MISSING`，以 structured reason 區分 omission／mistranslation，不新增另一套 MQM engine。
- 等價 boundary boilerplate 非必要重複：`BOUNDARY_BOILERPLATE_REPEATED`。
- boundary candidate 沒有可靠 disposition：`UNRESOLVED_BOUNDARY_CANDIDATE`；這是 Pantheon pipeline integrity finding，不宣稱為 MQM 官方 code。

上述 structured findings 必須保存在既有 deterministic findings artifact；既有 Reviewer schema 若只容許 `code/message`，不得為此擴張成第二套 review schema。

## RED → GREEN 驗收

### SC-001 — Candidate 2 duplication

Given immutable candidate 2 fixture，When 執行既有 JA deterministic validation，Then：

- `BOUNDARY_BOILERPLATE_REPEATED`
- 指出重複欄位／位置
- 不得錯判為 meaning 全失

### SC-002 — Candidate 3 omission

Given immutable candidate 3 fixture，When 執行相同 validation，Then：

- `BOUNDARY_MEANING_MISSING`
- `missing_fields[]` 至少包含 `meta_description`
- `missing_categories[]` 依 source／policy authority 列出
- 保留「仍有部分 outcome counterexample」的診斷事實

### SC-003 — Equivalent duplicate merge

Given 固定 source brief 中多個語意等價 boilerplate spans，When 建立 protected constraints，Then：

- 原始 spans、文字與 digest bytes 不變
- 每個 candidate 都有 disposition
- 只產生一個對應 normalized constraint
- `source_span_ids[]` 包含所有 merged spans
- Writer／plan authority 不要求逐段重現這些 boilerplate

### SC-004 — Unknown safety candidate fail closed

Given test-only source span「本內容不得用於醫療診斷，也不得自行停藥」，When 現有 classifier 無法可靠分類，Then：

- 原始 span／文字／digest 保留
- disposition = `UNRESOLVED`
- deterministic finding = `UNRESOLVED_BOUNDARY_CANDIDATE`
- 不得以 `safety_boundary=false` 或空 contract 放行

### SC-005 — Deterministic false-positive disposition

Given 一個只表達普通內容對比、不是 safety requirement 的否定句 fixture，When classifier 重算，Then：

- 原始 source span 保留
- disposition = `NOT_A_BOUNDARY`
- 附穩定 `reason_code`
- 不產生 protected constraint
- 不得靠 Reviewer 自由裁量才排除

### SC-006 — Corrected fixture GREEN

Given test-only corrected JA candidate，When 執行相同 deterministic validation，Then：

- 所有 required constraints 均有 target evidence
- 無 omission／mistranslation finding
- 無重複 boilerplate finding
- 無 unresolved candidate

### SC-007 — Regression boundary

必須證明：

- source brief bytes、source digest、candidate identity 不變。
- 原有 deterministic gates 未放寬。
- 非 JA observable behavior 不變。
- unrelated JA negation 不會全部被強制標 false 或全部升格為 protected constraint。
- publication policy 未修改、未繞過。
- fixture tests 不讀 production runtime、不呼叫 provider。

## 實作邊界

### 可改

- `scripts/agy_multilingual_pipeline.py`
- `tests/test_agy_multilingual_pipeline.py`
- `tests/fixtures/agy_multilingual_pipeline/ja_boundary_contract/`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-JA-PROTECTED-SOURCE-CONSTRAINT-TRACEABILITY-REPAIR-20260827-RESULT.md`
- `artifacts/fortune_council/four_lane_runtime_execution/ja_protected_source_constraint_traceability_repair_20260827/`

若既有 schema owner 證明 allowlist 不足，立即回 `BLOCKED / ALLOWLIST_INSUFFICIENT`；不得自行擴大。

### 禁止

- 禁止 cherry-pick 或續改前卡三個未接受 candidate；必須從本卡 base 重新實作最小 replacement。
- 禁止修改 `app/core/article_publication_policy_v2.json`、Publisher、Promotion、Coordinator lifecycle、A／C、G8、production queue/state 或已發布文章。
- 禁止呼叫 Writer／Reviewer provider、生成 production candidate、啟動七個服務、push、deploy 或 publication mutation。
- 禁止新增全語系 policy、通用 MQM engine、完整 provenance subsystem、第二套 quality engine、database／ledger／registry。
- 禁止用硬編 article ID、固定 candidate 文句或把所有 JA safety flags 設為同一值來通過 fixture。

## 停損

任一條成立立即停止：

- 需要可靠語意分類但只能靠新增 provider call。
- `NOT_A_BOUNDARY` 無法以 deterministic reason 重算。
- `MERGED_DUPLICATE` 只能依 category、關鍵字或整段相似度合併，無法證明語意等價。
- 需要修改全語系或 publication policy 才能通過。
- 需要再做 destructive source-text normalization。
- corrected fixture 仍無法同時通過 meaning、repetition 與 unresolved gate。

## 驗證與交付

必須交付：

1. 每項 SC 對應的先 RED、後 GREEN 證據。
2. 完整 `tests/test_agy_multilingual_pipeline.py`。
3. coordinator translation regression。
4. fixture JSON 與 immutable source fixture digest 驗證。
5. `git diff --check` 與 changed-file allowlist。
6. provider／production／service／network mutation 全為 0。
7. `RESULT.md`、evidence 與單一 candidate commit SHA。

執行線只能交付 `DELIVERED_CANDIDATE`。主線保留獨立 review、整合與最終 GO；本卡通過前不得回 B。

## 後續 production 契約（本卡不執行）

只有本卡獨立 review 通過、整合，且 local main／origin main／runtime actor 收斂後，才可回 Automation Acceptance B：恰好一次 fresh JA semantic generation、Writer provider attempt = 1、automatic repair = 0、Reviewer 判定 = 1；REJECT 即停，transaction／tag／push／deploy 全為 0。
