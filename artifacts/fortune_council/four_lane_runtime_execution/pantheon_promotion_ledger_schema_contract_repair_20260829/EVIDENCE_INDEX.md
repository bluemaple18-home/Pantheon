# Promotion Ledger Schema Contract Repair Evidence Index

Status: `RE_REVIEW_REQUESTED`

## Reviewer NO_GO Closure

Finding closed: missing reproducible 136-shape census/equivalent matrix.

## Read-Only Current Production Inputs

- Runtime manifest source id: `artifact:raw-current/runtime/runtime-manifest.json`
- Runtime manifest SHA256: `5a43c7ad9e2576cb6e54b268b609133ad99e089dcdca16348eeee6d7943fdf23`
- Queue registry source id: `runtime_manifest.queue_root/runs`
- Queue registry file count: `136`
- Queue registry tree digest: `5c224ee2ab5374099339a930c33a062b324e4c40d77ee547278cc500458ac942`
- Publisher ledger source id: `runtime_manifest.publisher_state_root/ledger.json`
- Publisher ledger SHA256: `4fa27434bfbff2a5344671278697bff6b94521d979083bf1227aff779e453f37`

No raw production snapshots are copied here; evidence files contain schema, identity, hashes, counts, and source ids only.

## Census Outputs

- `promotion_ledger_census_harness.py`: deterministic read-only harness.
- `census-run-1.json`: full 136-row matrix.
- `census-run-2.json`: second full 136-row matrix.
- `census-summary.json`: compact pass/count/source summary.
- `census-unique-transition.json`: the sole RED-to-GREEN measured mismatch.
- `malformed-matrix.tsv`: sanitized malformed fixture results.

## Matrix Counts

- `unchanged_pass`: 131
- `measured_mismatch_red_to_green`: 1
- `malformed_fail_closed`: 4

The sole measured transition is:

- run_id: `auto-i18n-ja-1414b75a404721e95e74`
- registry: `translate_existing`, lane `i18n-new`, article identity `V2-TAROT-DEATH-MONEY`
- ledger: `translation_published_runs`, identity field `article_id`, cardinality `one`, version `0.3.374`
- before baseline: RED because no `article_ids` list exists
- after candidate canonicalizer: GREEN with canonical `article_ids=["V2-TAROT-DEATH-MONEY"]`

The 4 malformed production rows remain fail-closed because failed registry states have missing brief identity and no ledger match. They are not converted to GREEN.

## Determinism And Immutability

- `census-double-run-sha256.txt`: both census outputs have SHA256 `4425553c5904824f9a0a442bb17b9aa2fe183b3a6d62f5a60750728be4eb8b65`.
- `census-double-run-diff.txt`: empty byte diff.
- Census pre/post read fingerprints are identical.
- Transaction calls: 0
- Provider calls: 0
- Publisher calls: 0
- Live mutation calls: 0

## Evidence-Only Verification

- `json-parse-census-run-1.txt`: JSON parse succeeded.
- `py-compile-census-harness.txt`: harness compile succeeded.
- `git-diff-check-evidence-only.txt`: diff hygiene succeeded.
- `source-test-numstat-after-evidence-only.txt`: source/test diff after evidence-only repair.
- `source-test-numstat-evidence-only-diff.txt`: empty diff against pre-evidence source/test numstat, proving this round changed source/test LOC = 0.
