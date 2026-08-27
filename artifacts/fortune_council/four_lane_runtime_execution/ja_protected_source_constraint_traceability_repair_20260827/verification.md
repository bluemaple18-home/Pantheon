# JA Protected Source Constraint Traceability Repair Verification

card_id: `CARD-PANTHEON-JA-PROTECTED-SOURCE-CONSTRAINT-TRACEABILITY-REPAIR`
base_commit: `d0d27cffa1a12d3029b851215f18025e97b2eb45`
run_id: `auto-i18n-ja-1414b75a404721e95e74`
source_article_id: `V2-TAROT-DEATH-MONEY`
source_sha256: `1088d4dfae649824b9691d260e1754e528295a2b877a79a1d8e665054fe6db23`

## Bootstrap

- worktree was clean before switching base
- base commit was readable
- `HEAD` was switched to `d0d27cffa1a12d3029b851215f18025e97b2eb45`
- Git reported the superseded commits `96a7fd4c90`, `78fe095f61`, and `f4f7c149aa` as left behind, not mixed into the replacement candidate
- CodeGraph was queried before source decision against canonical Pantheon

## Fixture Provenance

Repo fixtures are stored under `tests/fixtures/agy_multilingual_pipeline/ja_boundary_contract/`.

The tests read only repo fixtures. Fixture provenance labels use `<production-runtime>/...`; no host-specific absolute path is stored in the manifest.

| fixture | SHA-256 |
|---|---|
| `brief.json` | `93e09f8f637c396e35ccc28707c66734b08eb7f1c0c4cbdcb246df5b11ac8844` |
| `candidate_02.json` | `88e85070e057227836c78bf307e88d316a858bbbfaa850b2206fd7be3bd31e42` |
| `candidate_03.json` | `2a57b6bcb7fe27eeee0c57ff10d18d773643139b8a24e392b0b215be72aabda8` |
| `review_02.json` | `01e57a6360929100cd309efe029a086db665b2949dfa0dacec8adb88b91e8087` |
| `review_03.json` | `d4d4e7bb6820ff2608f4bf1016646b31dcd2d4bff7df21b5138ee879ed4db33d` |
| `corrected_test_only_candidate.json` | `667dea0e2db5da7d0ec27ce357825345d583e0ba6bade53425bf6d09f43230e8` |

## RED

Candidate 2/3 RED command:

```bash
<pantheon-venv-python> -m pytest tests/test_agy_multilingual_pipeline.py -k 'ja_boundary or protected_source_constraints'
```

Observed before implementation:

- selected: 5
- result: `2 failed, 3 passed, 187 deselected`
- candidate 2 returned no deterministic boundary finding, expected `BOUNDARY_BOILERPLATE_REPEATED`
- candidate 3 returned no deterministic boundary finding, expected `BOUNDARY_MEANING_MISSING`

Full SC RED command:

```bash
<pantheon-venv-python> -m pytest tests/test_agy_multilingual_pipeline.py -k 'ja_boundary or protected_source or unknown_boundary or ordinary_negation or corrected_fixture'
```

Observed before implementation:

- selected: 7
- result: `4 failed, 3 passed, 185 deselected`
- failures proved no `protected_source` traceability view existed and unknown/ordinary candidates had no disposition

Review-blocked P1 RED command:

```bash
<pantheon-venv-python> -m pytest tests/test_agy_multilingual_pipeline.py -k 'source_span_id or source_fact_projection or same_category or paraphrase_span'
```

Observed before P1 repair:

- selected: 4
- result: `4 failed, 192 deselected`
- failures proved same-category source claims were coarsely merged, source span IDs drifted with classifier hit order, Writer facts contained broken fragments, and paraphrased repeated boilerplate was missed

## GREEN

Protected source and JA boundary SC command:

```bash
<pantheon-venv-python> -m pytest tests/test_agy_multilingual_pipeline.py -k 'ja_boundary or protected_source or unknown_boundary or ordinary_negation or corrected_fixture'
```

Result:

- selected: 11
- result: `11 passed, 185 deselected`

Review-blocked P1 command:

```bash
<pantheon-venv-python> -m pytest tests/test_agy_multilingual_pipeline.py -k 'source_span_id or source_fact_projection or same_category or paraphrase_span'
```

Result:

- selected: 4
- result: `4 passed, 192 deselected`

Full multilingual regression:

```bash
<pantheon-venv-python> -m pytest tests/test_agy_multilingual_pipeline.py
```

Result:

- selected: 196
- result: `196 passed`

Coordinator translation regression:

```bash
<pantheon-venv-python> -m pytest tests/test_agy_gemini_coordinator.py -k translation
```

Result:

- selected: 24
- result: `24 passed, 291 deselected`

Fixture JSON and manifest digest check:

- result: `json fixtures ok 7`
- result: `manifest digests ok 6`

Whitespace:

```bash
git diff --check
```

Result:

- passed with no output

## Constraint Snapshot

Fixed brief source package after repair:

- facts: 22
- protected constraints:
  - total exact-equivalence constraints: 20
  - `outcome_not_determined`: 8 constraints
  - `contextual_or_general_interpretation`: 9 constraints
  - `professional_advice_non_substitution`: 3 constraints
- dispositions:
  - `PRESERVED`: 18
  - `MERGED_DUPLICATE`: 22
  - `NOT_A_BOUNDARY`: 2
  - `UNRESOLVED`: 0
- broken projection fragments `，。`, `，，`, `。，。`, `然而。`, `也。`, `但。`: absent from Writer fact projection
- standalone repeated source fact text `內容只提供通用理解，不能替個人下結論`: absent from Writer fact projection

Deterministic fixture findings:

- `candidate_02.json`: `BOUNDARY_BOILERPLATE_REPEATED`, `repeated_locations=["body"]`
- `candidate_03.json`: `BOUNDARY_MEANING_MISSING`, `missing_fields=["meta_description","body"]`, `missing_categories=["contextual_or_general_interpretation","professional_advice_non_substitution"]`, `present_categories=["outcome_not_determined"]`
- `corrected_test_only_candidate.json`: no deterministic boundary findings

## Allowlist

Changed paths are inside the card allowlist:

- `scripts/agy_multilingual_pipeline.py`
- `tests/test_agy_multilingual_pipeline.py`
- `tests/fixtures/agy_multilingual_pipeline/ja_boundary_contract/`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-JA-PROTECTED-SOURCE-CONSTRAINT-TRACEABILITY-REPAIR-20260827-RESULT.md`
- `artifacts/fortune_council/four_lane_runtime_execution/ja_protected_source_constraint_traceability_repair_20260827/`

## Mutation Accounting

- provider calls: 0
- production candidate calls: 0
- production queue/state mutation: 0
- services mutation: 0
- service startup: 0
- network: 0
- publication policy mutation: 0
- Publisher / Promotion / Coordinator lifecycle mutation: 0
