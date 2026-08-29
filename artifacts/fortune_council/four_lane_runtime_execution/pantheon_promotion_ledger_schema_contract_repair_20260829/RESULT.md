# Pantheon Promotion Ledger Schema Contract Repair Result

Status: `RE_REVIEW_REQUESTED`

## Summary

Promotion preserved-run ledger validation now honors collection-specific durable identity schema:

- `published_runs`, `rewrite_released_runs`, and `superseded_runs` require canonical sorted unique `article_ids`.
- `translation_published_runs` requires singular `article_id`, matching publisher durable output from v0.3.369/v0.3.374.
- A shared `_canonical_ledger_article_ids` canonicalizer returns the exact canonical `article_ids` tuple for downstream comparison.

## Changed Files

- `scripts/pantheon_content_runtime_promotion.py`
- `tests/test_pantheon_content_runtime_promotion.py`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-PROMOTION-LEDGER-SCHEMA-CONTRACT-REPAIR-20260829.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_promotion_ledger_schema_contract_repair_20260829/`

## RED/GREEN

- RED saved: `red-v0374-singular-translation-published-ledger.txt`
  - Command: `uv run python -m pytest tests/test_pantheon_content_runtime_promotion.py::test_plan_accepts_v0374_singular_translation_published_ledger_without_runtime_mutation`
  - Expected failure: old validator looked for `article_ids` on a v0.3.374-shaped translation ledger record and raised `publisher ledger identity mismatch`.
- Targeted GREEN saved: `green-targeted-schema-tests.txt`
  - Command: `.venv/bin/python -m pytest` over the v0.3.374 singular acceptance test, existing history matrix, invalid lifecycle ledger tests, and malformed translation ledger matrix.
  - Result: `11 passed`.

## Full Verification

- Full promotion suite saved: `full-promotion-suite.txt`
  - Command: `.venv/bin/python -m pytest tests/test_pantheon_content_runtime_promotion.py`
  - Result: `65 passed in 17.04s`.
- Compile saved: `py-compile.txt`
  - Command: `.venv/bin/python -m py_compile scripts/pantheon_content_runtime_promotion.py tests/test_pantheon_content_runtime_promotion.py`
  - Result: pass.
- Diff hygiene saved: `git-diff-check.txt`
  - Command: `git diff --check`
  - Result: pass.
- Source/test budget saved: `source-test-numstat.txt`
  - `scripts/pantheon_content_runtime_promotion.py`: 48 additions, 19 deletions.
  - `tests/test_pantheon_content_runtime_promotion.py`: 111 additions, 1 deletion.
  - Source+test changed LOC: 179, within <=200.

## Compatibility And Fail-Closed Coverage

- Exact v0.3.374 translation-shaped record with singular `article_id` turns GREEN.
- Existing create/rewrite/superseded list-shaped history remains GREEN.
- `article_id` and `article_ids` are mutually exclusive per descriptor.
- Missing, wrong type, duplicate list identity, translation `article_ids` list, both fields, and drift still fail closed.
- Plan-only idempotence is asserted by running `plan_promotion` twice and comparing exact output.
- Transaction root remains absent in plan-only tests.

## Immutability Receipt

- No publisher/coordinator/registry/live ledger files were changed.
- No provider command, publisher command, production command, commit, push, tag, deploy, or promotion apply/finalize was executed.
- Production bytes/provider/publisher mutation count: 0 by command scope and plan-only test assertions.
- Allowlist diff saved: `allowlist-diff-files.txt`; only source and test files appear in tracked diff.

## Scope Decision

- why_not_less: A single translation exception would preserve the bug class; descriptors are the minimum durable contract representation needed to prevent future collection schema confusion.
- why_not_more: No migration, publisher rewrite, runtime ledger rewrite, FSM, database, or lane workflow change is needed; the producer schema is already authoritative and proven.
- do_not_absorb: Do not absorb publisher lifecycle logic, coordinator routing, live state repair, or generic identity-field unions into promotion.
- anti-expansion receipt: repair is bounded to promotion ledger validation and tests; all live/runtime mutation surfaces stayed untouched.

## Residual Risk

Low. The change is private to promotion plan-time ledger evidence validation and is covered by exact acceptance, malformed negative cases, preserved matching, idempotence, compile, and full promotion suite.

## Reviewer NO_GO Evidence-Only Repair

Status remains: `RE_REVIEW_REQUESTED`

Reviewer finding closed: missing reproducible 136-shape census/equivalent matrix.

Evidence added under this directory only:

- `promotion_ledger_census_harness.py`: deterministic read-only harness.
- `census-run-1.json` and `census-run-2.json`: full 136 preserved-run matrix.
- `census-summary.json`: compact source/count summary.
- `census-unique-transition.json`: sole measured RED-to-GREEN transition.
- `malformed-matrix.tsv`: sanitized malformed fail-closed fixture results.
- `EVIDENCE_INDEX.md`: evidence map and acceptance summary.

Current production input fingerprints:

- Runtime manifest snapshot source id: `artifact:raw-current/runtime/runtime-manifest.json`; SHA256 `5a43c7ad9e2576cb6e54b268b609133ad99e089dcdca16348eeee6d7943fdf23`.
- Queue registry source id: `runtime_manifest.queue_root/runs`; file count `136`; tree digest `5c224ee2ab5374099339a930c33a062b324e4c40d77ee547278cc500458ac942`.
- Publisher ledger source id: `runtime_manifest.publisher_state_root/ledger.json`; SHA256 `4fa27434bfbff2a5344671278697bff6b94521d979083bf1227aff779e453f37`.

136-shape matrix result:

- `unchanged_pass`: 131
- `measured_mismatch_red_to_green`: 1
- `malformed_fail_closed`: 4

The sole measured transition is `auto-i18n-ja-1414b75a404721e95e74`: registry mode `translate_existing`, lane `i18n-new`, article identity `V2-TAROT-DEATH-MONEY`; ledger collection `translation_published_runs`, identity field `article_id`, cardinality `one`, version `0.3.374`. Baseline expectation is RED because the old promotion validator required `article_ids`; candidate canonicalizer is GREEN with canonical `article_ids=["V2-TAROT-DEATH-MONEY"]`.

The 4 malformed production rows remain fail-closed because failed registry states have missing brief identity and no ledger match. Sanitized malformed fixture coverage also passed: translation list, both fields, missing, wrong type, blank identity, list duplicate, and list both-fields cases all fail closed while valid singular/list cases pass.

Determinism and immutability:

- Double run SHA256: both census outputs are `4425553c5904824f9a0a442bb17b9aa2fe183b3a6d62f5a60750728be4eb8b65`.
- Double run diff: empty.
- Census pre/post live fingerprints: identical.
- Transaction/provider/publisher/live mutation calls: 0.
- Source/test numstat diff against pre-evidence state: empty, so this evidence-only round changed source/test LOC = 0.

Evidence-only verification:

- JSON parse of `census-run-1.json`: pass.
- `py_compile` for `promotion_ledger_census_harness.py`: pass.
- `git diff --check`: pass.
