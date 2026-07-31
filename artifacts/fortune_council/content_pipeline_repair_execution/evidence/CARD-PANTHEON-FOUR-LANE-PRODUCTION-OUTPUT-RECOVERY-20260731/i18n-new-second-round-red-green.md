# EV-I18N-NEW-SECOND-ROUND-RED-GREEN-001

## Scope

```text
lane: i18n-new
failure_type: LocalePlanValidationError
provider_payload_disclosed: false
production_mutation_during_repair: false
```

## RED

The preserved production response was replayed locally through
`_hydrate_locale_plan`. The command exited `1` at the same deterministic seam:

```text
ValueError: locale plan coverage heading differs for article-01
```

Closed structural diagnostics, without printing provider text:

- outline count: `5`
- coverage mapping count: `17`
- exact heading matches: `15`
- normalized heading matches: `15`
- mismatched mappings: indices `15` and `16`
- both mismatches referenced the same sixth heading
- the sixth heading was not a source-structure blacklist entry

## Falsifiable hypotheses

1. Punctuation or casing drift caused the mismatch.
   - Falsified: normalized matching remained `15/17`.
2. The model copied a forbidden source H2.
   - Falsified: neither mismatch matched the source blacklist.
3. The external schema duplicated a free-form H2 string in
   `coverage_mapping`, but JSON Schema could not enforce membership in the
   sibling outline.
   - Supported: the response passed the provider schema envelope and failed
   only at the deterministic cross-field check.

## First repair

- External coverage now uses `planned_h2_index`, an enum of `0..3`.
- The external outline is fixed at exactly four H2s, which remains inside the
  existing accepted four-to-five H2 content contract.
- Hydration resolves each index to the canonical outline string before the
  existing internal validator runs.
- Fact identity, order, safety boundary, target-language, prior-topology and
  candidate-outline gates remain unchanged.
- The provider prompt explicitly forbids writing or paraphrasing a separate H2
  inside coverage mappings.

## GREEN

```text
.venv/bin/pytest -q \
  tests/test_agy_multilingual_pipeline.py \
  tests/test_agy_gemini_outbox.py

308 passed in 2.14s
```

The regression tests prove:

- coverage indices hydrate to exact canonical H2 strings;
- the external index is not persisted in the internal plan;
- `4`, `5` and boolean indices fail closed for a four-item outline;
- the response schema locks the index enum and exact outline cardinality;
- multilingual pipeline and outbox behavior remain green.

## External tool gate

```text
tool/service: installed Gemini CLI through the production credential allocator
operation_level: write_action
connection_status: configured; credential values not inspected or recorded
schema_checked: true
confirmation_required: true
confirmation_status: received for bounded second-round canaries and gated publish
execution_status: pending repair deployment
remaining_risk: provider quota or availability can still produce a typed NO-GO
```

## Live schema compatibility follow-up

部署 first repair 後，同一個 `i18n-new` writer request 由兩個不同 production
credential slot 呼叫；兩次都在 1 秒內回 `API_HTTP_ERROR`，且
`request_sha256` 完全相同。相同模型剛完成 `rewrite` Writer，排除模型整體
不可用；未浪費第 3 次 transport attempt 重送同一 schema。

根據 Gemini structured-output 契約，string enum 是穩定的分類約束；為避開
live endpoint 對 nested multi-value numeric enum 的接受差異，second repair
把 external 欄位改為：

```text
planned_h2_slot: h2-1 | h2-2 | h2-3 | h2-4
```

本地 hydration 將 slot 解析為 outline index，再寫回既有 internal
`planned_h2` canonical string。模型仍不能複製、改寫或發明 coverage H2；
錯誤型別、未知 slot 與超界 slot 全部 fail closed。

RED：

```text
KeyError: planned_h2_slot
```

GREEN：

```text
tests/test_agy_multilingual_pipeline.py: 163 passed
git diff --check: PASS
```

兩個舊 schema 外呼已計入授權額度；second repair 尚未呼叫 provider。

### Second repair live result

string slot request 使用新 hash 呼叫後仍在 1 秒內回 `API_HTTP_ERROR`，因此
numeric enum 不是唯一撞點。結構統計顯示：

```text
i18n schema: 1817 bytes / depth 10 / enum choices 29
successful rewrite schema: 1724 bytes / depth 14 / enum choices 5
```

兩者大小接近，i18n 反而較淺；差異集中在 enum state count。依 Gemini
structured-output 的 schema complexity 限制，`gemini-3.5-flash-lite`
provider payload 現在只移除超過 8 個值的大型 enum，保留 `h2-1..4` 等小型
enum。原始 outbox schema 不變；provider response 回來後仍以完整 enum、
hash、fact identity 與 deterministic validators 驗證，沒有放寬 acceptance。

RED：

```text
AssertionError: large source_fact_id enum remained in provider schema
```

GREEN：

```text
provider schema + multilingual + outbox focused tests: 312 passed
git diff --check: PASS
```

此變更是本 run 的 schema repair 2/2；尚未執行修補後外呼。

### Second repair production response and deterministic hydration

部署 `ffb0a384d03a886e0b6fd72f7be5c105cb6841a9` 後，官方 Publisher
preflight 回報 actor、queue、state、runtime SHA、runtime digest 與 push mode
全部 matched。指定 job
`27c1b68c63d42928cedbac3d57656030560f4d63` 經 production allocator 呼叫
成功，成為本輪第 14/40 次外部呼叫；原先的 `API_HTTP_ERROR` 不再出現。

provider transport 成功後，本地 deterministic gate 以同一份 response 穩定
重現：

```text
ValueError: locale plan source structure blacklist differs for article-01
```

排序假說與結果：

1. 大型 fact enum 移除後造成 fact identity 漂移：已否證，22 個 fact identity、
   order 與 safety boundary 均通過。
2. `source_structure_not_copied` 的 prompt/schema 語意不清：證實。模型回傳
   `source_h2_order`、`source_section_count`、`source_paragraph_counts` 三個
   輸入欄位名，而 validator 要求來源 H2 的精確集合。

這個欄位不是創作內容，而是 brief 已知的 deterministic audit blacklist。
hydration 現在直接由 brief 寫入來源 H2；模型產生的 intent、query、angle、
outline、coverage、fact identity、語言與安全邊界仍由原 gate 驗證。既有
production response 不需重送即可由 RED 轉 GREEN：

```text
run_id: auto-i18n-en-cfd7211d31136567123c
articles: 1
outline_count: 4
coverage_count: 22
status: PASS
```

回歸與全套驗證：

```text
affected tests: 432 passed
full suite: 823 passed, 2 warnings
git diff --check: PASS
```

### Reviewer exhaustion and replacement-run outline repair

original run 在兩次 semantic repair 後仍被 reviewer 以
`SOURCE_SYNTAX_TRANSFER`、`AI_TEMPLATE_STYLE` 拒絕；
`approved_by_reviewer=0`，因此沒有進 Publisher。依卡片限定只建立一個
replacement：

```text
auto-i18n-en-cfd7211d31136567123c-replacement-01
```

replacement 的第一份 locale plan 把 `h2-1` 到 `h2-4` 誤當實際 H2，
article 又沿用來源中文 H2。舊路徑在 provider transport 成功後以
`ValueError: article outline differs from locale plan` hard fail，無法使用
既有 semantic repair 額度。

新增 deterministic findings：

```text
LOCALE_PLAN_HEADING_PLACEHOLDER
LOCALE_PLAN_OUTLINE_MISMATCH
```

兩者會合併進 reviewer 結果並強制 `REJECT`；只有下一代 plan 使用目標語言
自然 H2，且 candidate 的 section count、order、heading 逐字對齊，才會清除
findings。prompt 同時明確區分 mapping slot 與實際 H2，不放寬任何既有
reviewer 契約。

同一份 production response 的離線 RED/GREEN：

```text
RED: ValueError: article outline differs from locale plan for article-01
GREEN: 2 deterministic findings persisted for semantic repair
affected tests: 433 passed
full suite: 824 passed, 2 warnings
git diff --check: PASS
```

截至此點 production Gemini 外呼為 24/40；replacement 尚未使用任何
semantic repair。
