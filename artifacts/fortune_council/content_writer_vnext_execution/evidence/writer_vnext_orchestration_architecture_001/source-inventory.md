# Source Inventory

## Fixed Inputs

| Input | Commit | Status |
|---|---|---|
| Source base | `476091289206b5cfdcb0d1ee90ba34d09823f5f7` | readable; current HEAD matched during bootstrap |
| Writer contract candidate | `671fdba9bf1b5655cc9182bbf375cadae3efb0b5` | readable |
| Writer contract review | `038cf4d2979bf2a1a8ceaf4d44964c3fde5816c6` | readable |
| Runtime Authority candidate | `e6d93fba050eac7c22e1a34bf52d8ac4c707a1b3` | readable |
| Runtime Authority review | `38774ddf1bccc77a0b40917322bb100d238469d7` | readable |

## CodeGraph Query

Task-semantic query:

```text
Writer vNext orchestration transport mapping ArticleBriefV2 EditorialManifestV1 selected editorial stages Gemini outbox runner coordinator Publisher handoff forward-only recovery artifact ledger dedupe identity schema sha
```

Result summary:

- Entry point: `OutboxGeminiClient` in `scripts/agy_gemini_outbox.py`.
- Related transport symbols: `build_external_request`, `create_external_request`, `consume_external_response`, `run_pipeline_tick`.
- Related tests: `tests/test_agy_gemini_outbox.py`, including cross-tick writer/reviewer progression and retry identity.
- Related architecture POC: `scripts/agy_gemini_v4_architecture_probe.py::Ledger`.

Follow-up CodeGraph explore confirmed source seams in:

- `scripts/agy_editorial_contracts.py`
- `scripts/agy_gemini_outbox.py`
- `scripts/agy_gemini_runner.py`
- `scripts/agy_gemini_coordinator.py`
- `scripts/agy_content_publisher.py`
- `tests/test_agy_gemini_outbox.py`
- `tests/test_agy_gemini_coordinator.py`

## Source Seams Confirmed

### Writer vNext contracts

`scripts/agy_editorial_contracts.py`

- Lines 11-15: allowed stage artifact mapping: `content_plan_v1`, `claim_classification_v1`, `blind_read_v1`.
- Lines 17-22: stable finding codes include missing artifact, schema, SHA, identity, high-risk claim and publisher compatibility failures.
- Lines 50-65: `ArticleBriefV2` strict required fields.
- Lines 68-87: selected stage validation requires object stages, unique integer sequence, expected output and blocking policy.
- Lines 130-173: `EditorialManifestV1` validation binds `run_id`, `article_identity`, `brief_sha256`, artifact hashes, final candidate SHA and optional legacy candidate compatibility.

### Legacy candidate and review validation

`scripts/agy_seo_copy_pipeline.py`

- `validate_candidate()` requires `schema_version`, `run_id`, `mode`, strict top-level fields, 1-5 articles and duplicate ID rejection.
- `validate_review()` binds each review item to candidate article identity and candidate SHA, restricts verdict to `APPROVE` or `REJECT`, and rejects missing articles.
- `public_model_brief()` strips private repo metadata from model inputs.
- `run_writer_reviewer()` writes public brief, requests writer output, hydrates candidate, runs bounded schema repair and then independent review.

### Outbox transport

`scripts/agy_gemini_outbox.py`

- Lines 20-23: transport schema version and bounded retry constants.
- Lines 142-151: prompt/schema public payload guard rejects private paths and secrets.
- Lines 154-180: strict request core allows only `writer` and `reviewer` roles and records prompt/schema hashes.
- Lines 183-199: `request_sha256` and `job_id` are deterministic from canonical request bytes.
- Lines 230-260: create request dedupes existing identical jobs and fails on collision.
- Lines 356-387: response/failure consumption validates schema, job ID, request SHA and model.
- Lines 397-449: `OutboxGeminiClient.generate_json()` uses existing writer/reviewer models and bounded retry for retryable JSON decode failures.
- Lines 452-470: `run_pipeline_tick()` maps a registered run to existing pipeline runner and returns complete state with candidate/review paths.

### Runner and runtime authority

`scripts/agy_gemini_runner.py`

- Lines 69-72: closed role instructions currently define only `writer` and `reviewer`.
- Lines 81-100: V4 effective prompt deterministically combines role instruction, JSON schema and sanitized task.
- Lines 246-345: `process_once()` claims one job, validates request, optionally runs V4 broker, writes SHA-bound inbox or failed record, and archives request.

Runtime Authority candidate `e6d93fba050eac7c22e1a34bf52d8ac4c707a1b3` adds:

- `scripts/pantheon_runtime_fs_authority.py`: trusted sandbox directory authority, operation trace recorder, trace digest and fail-closed sandbox drift detection.
- `scripts/agy_content_publisher.py::formal_capability_preflight()`: bounded `select`, `publish`, `transaction`, `tag`, `push` dry-run capability preflight under sandbox authority and runtime identity digest.
- Runtime manifest digest and exact run ID selector plumbing for Publisher capability gates.

### Coordinator

`scripts/agy_gemini_coordinator.py`

- Lines 28-35: active run and lane constants; `Tick` and `Process` injection points.
- Lines 43-56: brief validation enforces `run_id` and article count.
- Lines 64-84: `register_run()` stores active state without external request.
- Lines 100-136: `_advance()` maps pending/failed/complete transport outcomes into run state.
- Lines 538-645: `cycle_once()` holds coordinator lock, selects active states, advances ticks, invokes runner once, and summarizes state.
- Lines 648-655: `resume_run()` can reactivate an existing run.

### Publisher

`scripts/agy_content_publisher.py`

- Lines 27-61: Publisher constants include schema version, Publisher ID, success statuses, retry delay and retry attempts.
- Lines 693-716: Publisher ledger stores published/quarantined/rewrite/translation states and rejects invalid ledger schema.
- Lines 746-767: `_load_completed_run()` revalidates complete state, candidate path, review path, run ID, candidate schema and review schema.
- Lines 770-778: `_review_is_clean_approve()` rejects non-approve, hard failure and findings.
- Lines 784-840: collect-ready rejects published/quarantined runs, unsupported modes, unclean review, deterministic findings and duplicate article/path content.
- Lines 1620-1690 and 1692-1833: Publisher owns publication transaction, tests, commit/tag/push and ledger evidence.

## Architecture Implications

1. Existing transport can carry vNext stages if stage identity is represented by manifest, prompt, schema and artifact hashes rather than new roles.
2. Existing coordinator can remain the tick owner if vNext projection is run-local and reconstructable.
3. Existing Publisher must remain the publication owner; vNext sidecar may only add validation and blocking evidence.
4. Runtime Authority composition belongs to a later integration card because reviewed commits are not yet in one lineage.
