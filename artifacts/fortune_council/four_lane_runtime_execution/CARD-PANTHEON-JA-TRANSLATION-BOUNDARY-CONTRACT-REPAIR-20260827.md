---
id: CARD-PANTHEON-JA-TRANSLATION-BOUNDARY-CONTRACT-REPAIR
status: superseded_no_go
chain_id: PANTHEON-AUTOMATION-ACCEPTANCE-20260826
parent_card: CARD-PANTHEON-AUTOMATION-ACCEPTANCE-B-TRANSLATION-PUBLIC-URL-20260826
role: repair
cycle: 1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 規格已固定，涉及 JA translation safety boundary、Writer／Repair／Reviewer 共用契約與 production 前 fail-closed gate，屬 strict/core-bounded；沒有未解架構岔，不升 Sol。
execution_mode: repo_only_bounded_repair
production_mutation: forbidden
root_cause: TRANSLATION_BOUNDARY_CONTRACT_OSCILLATION
superseded_by: CARD-PANTHEON-JA-PROTECTED-SOURCE-CONSTRAINT-TRACEABILITY-REPAIR
---

# Pantheon JA Translation Boundary Contract Repair

> 2026-08-27 主線 re-review：本卡三個 candidate 均未閉合 source authority normalization；最後版本仍可能靜默解除未識別的 JA safety candidate。依三次停損契約停止，改由 `CARD-PANTHEON-JA-PROTECTED-SOURCE-CONSTRAINT-TRACEABILITY-REPAIR` 以 source-span provenance 與明確 disposition 取代；本卡不得再續作。

工作名稱：JA Translation Boundary Contract — Writer / Reviewer Alignment

## Root Question

如何只在既有 JA translation quality seam 內，讓 Source fact extractor、Writer／Repair 與 Reviewer／deterministic validation 共用同一份可程式化 boundary contract，使必要安全語意完整保留，同時拒絕跨段重複的免責 boilerplate？

## 已裁決根因

`TRANSLATION_BOUNDARY_CONTRACT_OSCILLATION`

- Source fact extractor 把多段近似免責文字分別視為 safety facts，沒有先正規化、分類與去重。
- Writer／Repair 第一輪可能重複承載安全語意；後續 repair 只依最新 finding 大幅刪除，沒有保存尚未滿足的結構化 boundary constraints。
- Reviewer 只有自然語言的「限制保留／文體自然」判斷，沒有欄位級、語意類別級的共同契約與精確 finding code。
- candidate 2 與 candidate 3 不構成 Reviewer 自相矛盾：前者有安全語意但以重複套語呈現；後者仍有部分反例，但缺少 meta description 限制與完整的適用／非專業替代語意。

## 目的與成功條件

### BRS-001

修復阻擋 Automation Acceptance B 的最後一個 JA 內容契約缺口，不重開 A、C、Promotion 或 G8，也不以額外 production 嘗試代替修復證據。

### StRS-001

Pantheon 內容治理需要一份 JA Writer、bounded Repair 與 Reviewer／translation quality validation 共同使用的 boundary contract，能區分「必要安全語意」與「重複 boilerplate 文案」。

### FR-001 — Fixture authority

系統 SHALL 以既有 production 失敗證據唯讀抽取固定 fixtures，不得重新呼叫 provider 產生 fixture：

1. candidate 2 與 reviewer finding 2。
2. candidate 3 與 reviewer finding 3。
3. original source article、brief 與 extracted source facts。

抽取後的測試只使用 repo 內 immutable fixture；驗 fixture 不得依賴 production queue/state。

### FR-002 — Structured JA boundary contract

系統 SHALL 將 source／既有 policy 的 boundary 要求正規化為去重後的結構化 constraints，至少能表達：

- required fields：`meta_description`、`body`。
- required semantic categories：
  - `outcome_not_determined`
  - `contextual_or_general_interpretation`
  - `professional_advice_non_substitution`，僅在 source 或既有 policy 要求時成立。
- presentation constraints：
  - required meaning 必須存在。
  - 同一安全語意不得以近似完整套語跨多段重複。
  - 消除重複時，不得刪除尚未滿足的 required category。

同一份 contract 必須同時提供給 JA Writer、bounded Repair 與 JA Reviewer／translation quality validation。History 只供 trace／診斷；不得成為 mutable authority，也不得把歷輪 Reviewer 自然語言 findings 直接串接進 prompt。

### FR-003 — Finding codes

沿用既有 translation quality seam，只新增或收斂：

1. `BOUNDARY_BOILERPLATE_REPEATED`
   - 必須指出重複位置或欄位。
   - 不得只輸出「免責太多」之類的模糊文案。
2. `BOUNDARY_MEANING_MISSING`
   - 必須附 `missing_fields[]`。
   - 必須附 `missing_categories[]`。
   - 除非實際全部缺失，不得宣稱所有 boundary 消失。

不得建立第二套 Reviewer／quality engine；本輪行為只啟用於 JA translation。這兩個 code 不得默示觸發全篇 outline rebuild。

### FR-004 — Cumulative constraint preservation

Repair SHALL 保留尚未滿足的結構化 boundary constraints，不得只修最新一條而把上一條修壞；不得把所有歷史 Reviewer prose 原樣累積。若需要保存歷史，只保存 immutable trace 與由 current candidate 重新計算的 active constraint state。

### SC-001 — RED fixture 1

Given 固定 candidate 2 fixture，When 執行 JA boundary validation，Then：

- 必須回 `BOUNDARY_BOILERPLATE_REPEATED`。
- finding 必須指出重複位置／欄位。
- 不得錯判為 `BOUNDARY_MEANING_MISSING`。

### SC-002 — RED fixture 2

Given 固定 candidate 3 fixture，When 執行 JA boundary validation，Then：

- 必須回 `BOUNDARY_MEANING_MISSING`。
- `missing_fields[]` 至少包含 `meta_description`。
- `missing_categories[]` 依 source／policy 實際要求列出。
- finding 必須承認候選仍保留部分反例，不得宣稱全部 boundary 消失。

### SC-003 — GREEN fixture

Given 一份明確標記為 test-only 的 corrected JA fixture，When 執行相同 validation，Then：

- 必要安全語意完整。
- 沒有跨段重複 boilerplate。
- 上述兩個 finding 均不存在。

### SC-004 — Regression boundary

驗證必須同時證明：

- 原有 deterministic gates 未放寬。
- candidate identity 與 source digest 不變。
- publication policy 沒有被繞過。
- 非 JA translation observable behavior 不變。
- invalid schema／source drift／既有 native-quality rejection 仍 fail closed。

## Fixture 來源與保存方式

- production run identity：`auto-i18n-ja-1414b75a404721e95e74`。
- source article identity：`V2-TAROT-DEATH-MONEY`。
- local-only fixture source：`<production-runtime>/queue/translation-runs/auto-i18n-ja-1414b75a404721e95e74/`。
- repo 內 canonical fixture destination：`tests/fixtures/agy_multilingual_pipeline/ja_boundary_contract/`。
- 必須保存抽取來源檔的 SHA-256 與 repo fixture SHA-256；fixture extraction 後，RED／GREEN 測試不得再讀 production runtime。
- candidate 2／3、review 2／3 與 original brief 只能唯讀；禁止修改或覆寫 production artifacts。

## 執行切片與依賴

### JA-BOUNDARY-SLICE-FIXTURES

- traces_to：`FR-001`、`SC-001`、`SC-002`。
- frontier：可立即開始。
- 工作：唯讀抽取、最小化並鎖定 fixtures；先建立一條能重現兩個錯誤分類的 red-capable test command。
- 驗收：fixture hash 可重算；沒有 provider call；production bytes 不變。

### JA-BOUNDARY-SLICE-CONTRACT

- traces_to：`FR-002`、`FR-003`、`FR-004`。
- blocked_by：`JA-BOUNDARY-SLICE-FIXTURES`。
- 工作：在既有 translation seam 實作最小 JA boundary contract，讓 Writer／Repair／Reviewer validation 共用。
- 驗收：兩個 RED fixtures 精確分類，corrected fixture 兩項均 PASS。

### JA-BOUNDARY-SLICE-REGRESSION

- traces_to：`SC-003`、`SC-004`。
- blocked_by：`JA-BOUNDARY-SLICE-CONTRACT`。
- 工作：跑受影響 JA 與非 JA regression、JSON/schema validation、`git diff --check`；產出 result/evidence。
- 驗收：測試結果、fixture digest、changed-file allowlist 與 provider／production mutation accounting 完整。

只有上一 slice GREEN 後才能進下一 slice；不得平行展開或跳過 RED。

## 唯一可改範圍

- `scripts/agy_multilingual_pipeline.py`
- `tests/test_agy_multilingual_pipeline.py`
- `tests/fixtures/agy_multilingual_pipeline/ja_boundary_contract/`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-JA-TRANSLATION-BOUNDARY-CONTRACT-REPAIR-20260827-RESULT.md`
- `artifacts/fortune_council/four_lane_runtime_execution/ja_translation_boundary_contract_repair_20260827/`

若現有 schema owner 證明上述範圍不足，立即 `BLOCKED / ALLOWLIST_INSUFFICIENT` 回主線；不得自行修改其他檔案。

## 禁止範圍

- 禁止修改 `app/core/article_publication_policy_v2.json`。
- 禁止修改 Publisher、Promotion、Coordinator lifecycle、A／C acceptance 或 G8。
- 禁止修改 production queue/state、已發布文章或中文 source article。
- 禁止直接跑第 4 次 production candidate、呼叫 Writer／Reviewer provider、換 Reviewer、降低標準、人工 override publish 或啟動七個服務。
- 禁止改全語系翻譯 policy、重寫通用 Reviewer framework、新增第二套 quality engine，或將 prompt 變成跨語系 mega-contract。
- 禁止為 fixture 或測試存取網路。

## Production Acceptance 契約（本卡只鎖定，不執行）

本卡與獨立 review 通過、整合且 local main／origin main／正式 runtime actor 收斂後，Automation Acceptance B 才能另行續跑，而且只允許：

- 恰好 1 次新的 JA Writer semantic generation。
- Writer provider attempt count = 1。
- automatic Writer repair count = 0。
- 恰好 1 次 Reviewer 判定。
- 不得沿用 candidate 2 或 candidate 3 直接發布。

只有 Reviewer `APPROVE` 才可進既有正式 publication flow。若 Reviewer `REJECT`，立即停止，且 publication transaction、tag、push、deploy 均必須為 0；不得自動開始下一次 repair 或第 5 次重跑。

## 停損條件

任一情況立即停止並交付單一 blocker：

- 開始改全語系 translation policy。
- 開始重寫通用 Reviewer framework。
- 需要人工 override Reviewer。
- 需要第 2 次 production semantic generation。
- 需要啟動七個服務。
- 需要 mutation production queue/state 才能驗 fixture。
- corrected fixture 無法同時通過 meaning 與 repetition contract。
- 需要超出 allowlist 的檔案才能完成且主線未重新授權。

## 驗證與交付

必須提供：

- 實際執行且因目標症狀失敗的 RED command 與輸出摘要。
- minimal fix 後相同 command GREEN。
- 受影響 tests 與必要 regression 測試結果。
- fixture source／destination SHA-256 對照。
- `git diff --check`。
- changed files 必須完全落在 allowlist。
- provider calls = 0、production mutation = 0、service mutation = 0。
- `RESULT.md`、evidence 目錄與完整 candidate commit SHA。

執行線只能交付 `DELIVERED_CANDIDATE`，不得宣稱 `ACCEPTED`、`INTEGRATED`、可 production 或 B 已完成；主線保留獨立 review、整合與最終 GO 判定。
