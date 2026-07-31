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
