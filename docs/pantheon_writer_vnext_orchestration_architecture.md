# Pantheon Writer vNext Orchestration Architecture

## 狀態

本文件回答 `CARD-CONTENT-WRITER-VNEXT-ORCHESTRATION-ARCHITECTURE-001`。它只定義架構契約與後續實作切片，不實作 Agent、prompt、queue、retry loop、Publisher mutation、deployment 或 production canary。

Verdict target: `ARCHITECTURE_READY_FOR_REVIEW`

## Root Answer

Writer vNext 不建立第二套 queue、approval、publication 或 deployment control plane。vNext 的 orchestration source of truth 是 run 目錄內可重建的 versioned artifacts：

- `<run-dir>/brief.json` 保持既有 coordinator registration input。
- `<run-dir>/vnext/manifest.json` 是 `EditorialManifestV1`，宣告 opt-in、selected stages、artifact hashes、final candidate hash 與 handoff identity。
- `<run-dir>/vnext/ledger.jsonl` 是 append-only artifact ledger，記錄每個 stage 的 request identity、response identity、input SHA、output SHA 與 deterministic gate result。
- `<run-dir>/vnext/artifacts/*.json` 保存 stage output 與 validator output。
- `<run-dir>/candidate.json`、`<run-dir>/review.json`、`<run-dir>/review.md` 保持 legacy Publisher handoff identity。

Coordinator 每個 tick 只從 artifacts、manifest、request/response SHA 與既有 outbox state 推導唯一 next action。任何 collision、tamper、missing dependency、unknown stage、schema drift 或 ambiguous next action 都 fail loud，不補值、不重送、不發布。

## Owner And Authority Matrix

| Authority | Existing owner | vNext contract |
|---|---|---|
| Lane selection and active-run lock | `scripts/agy_gemini_coordinator.py` | Coordinator 仍是 tick owner；vNext 只增加 run-local projection，不新增 daemon 或 queue。 |
| External model transport | `scripts/agy_gemini_outbox.py` and `scripts/agy_gemini_runner.py` | 只使用既有 sanitized request envelope、outbox/inbox/failed/archive folders、bounded retry authority。 |
| Model role | Existing `writer` and `reviewer` roles | 不新增 role。Stage intent 由 stage manifest、prompt、schema、artifact kind 表達。 |
| Deterministic validation | `scripts/agy_editorial_contracts.py`, `scripts/agy_seo_copy_pipeline.py`, later slice tests | vNext manifest validation and legacy candidate/review validation must both pass before state becomes complete. |
| Publication | `scripts/agy_content_publisher.py` | Publisher remains the only publication owner. It may revalidate a present vNext manifest, but manifest never grants approval/apply/Git/push authority. |
| Deployment and runtime activation | Existing deployment/runtime authority commits | Runtime activation receipt is an input identity for Publisher capability gates, not a Writer orchestration permission. |

## Stable Decisions

### WVO-ARCH-001: Transport Mapping

`ArticleBriefV2`, `EditorialManifestV1` and selected stages map onto the existing request envelope without new roles.

The envelope remains:

```json
{
  "schema_version": 1,
  "namespace": "<opaque run namespace, optionally stage-qualified>",
  "role": "writer|reviewer",
  "model": "<existing writer or reviewer model>",
  "thinking_level": "LOW",
  "operation_level": "external_generation",
  "prompt": "<public sanitized stage task>",
  "response_schema": "<closed JSON schema>",
  "prompt_sha256": "<sha256>",
  "schema_sha256": "<sha256>",
  "job_id": "<request_sha256 first 40 chars>",
  "request_sha256": "<sha256>"
}
```

Stage mapping:

| Stage kind | Transport role | Input artifact | Output artifact | Schema/version | Deterministic gate |
|---|---|---|---|---|---|
| `content_plan_v1` | `writer` | `ArticleBriefV2` + prior approved artifacts declared in `required_inputs` | `content_plan` | `ContentPlanV1` | `validate_manifest` plus stage output hash match |
| `claim_classification_v1` | `writer` | `ArticleBriefV2`, `content_plan` if declared, candidate draft if declared | `claim_classification` | `ClaimClassificationV1` | claim type allowlist and high-risk evidence rules |
| `blind_read_v1` | `reviewer` | final candidate blinded input and declared prior artifacts | `blind_read` | `BlindReadResultV1` | final candidate SHA match and thesis match |
| `legacy_candidate_adapter_v1` | local deterministic code | vNext final draft, brief, manifest | `candidate.json` | legacy candidate schema version 1 | `pipeline.validate_candidate` |
| `legacy_review_adapter_v1` | `reviewer` or existing review path | legacy candidate | `review.json`, `review.md` | legacy review schema version 1 | `pipeline.validate_review` and clean approval rules |

No new Gemini role is required. If a future stage cannot be safely expressed as writer or reviewer, that stage must be rejected with `WVO-FC-UNKNOWN_STAGE` until a separate migration card adds a versioned role and runner compatibility tests.

Identity rules:

- `run_id` remains private/local and is not exposed directly to external prompt text.
- Outbox `namespace` remains opaque. For vNext, the deterministic namespace seed is `sha256(run_id)[:24]`; stage identity is bound by prompt/schema/request SHA and ledger `stage_id`, not by a new queue.
- `request_sha256` is the transport identity.
- `response_sha256` is `sha256(canonical_json(response.result))` computed by the vNext validator before writing the stage artifact.
- `artifact_sha256` is the stable JSON hash used by `scripts/agy_editorial_contracts.py`.

### WVO-ARCH-002: Artifact Ledger And Next-Action Reconstruction

The vNext coordinator projection is rebuilt from:

1. `brief.json`
2. `vnext/manifest.json`
3. `vnext/ledger.jsonl`
4. stage artifacts named by manifest `artifacts`
5. existing outbox/inbox/failed/archive files for pending transport jobs
6. legacy `candidate.json`, `review.json`, `review.md`

The ledger is append-only. Each event contains:

```json
{
  "schema_version": "WriterVNextLedgerV1",
  "sequence": 1,
  "parent_sha256": null,
  "run_id_sha256": "<sha256(run_id)>",
  "manifest_sha256": "<sha256(manifest without volatile projection)>",
  "stage_id": "content_plan_v1#001",
  "stage_type": "content_plan_v1",
  "action": "REQUEST_CREATED|RESPONSE_ACCEPTED|ARTIFACT_ACCEPTED|LEGACY_ADAPTER_ACCEPTED|HANDOFF_BLOCKED",
  "input_sha256": {"brief": "..."},
  "request_sha256": "...",
  "response_sha256": "...",
  "output_artifact": "content_plan",
  "output_sha256": "...",
  "gate": "PASS|FAIL_CLOSED",
  "finding_codes": []
}
```

The projection is not a free state file. A cache such as `vnext/projection.json` may be generated for observability, but tests and recovery must be able to delete it and reconstruct the same next action from immutable inputs.

### WVO-ARCH-003: Dedupe, Collision And Tamper Fail-Closed

A completed stage is never resent when all of the following match:

- manifest schema and `selected_stages` entry match exactly
- all declared input artifact SHA values match ledger
- request envelope rebuilds to the same `request_sha256`
- response artifact exists, validates against expected schema, and hashes to ledger `output_sha256`
- ledger parent hash chain is intact

Failure behavior:

| Code | Trigger | Behavior |
|---|---|---|
| `WVO-FC-SCHEMA_VERSION` | unsupported manifest, ledger, stage or legacy artifact schema | fail closed, no new request |
| `WVO-FC-UNKNOWN_STAGE` | stage type not in manifest allowlist | fail closed, no new request |
| `WVO-FC-MISSING_DEPENDENCY` | required input artifact absent | fail closed, no new request |
| `WVO-FC-REQUEST_COLLISION` | same job ID maps to different request bytes | fail closed using existing outbox collision semantics |
| `WVO-FC-ARTIFACT_TAMPER` | artifact hash differs from manifest or ledger | fail closed, no handoff |
| `WVO-FC-AMBIGUOUS_NEXT_ACTION` | projection finds more than one eligible next action | fail closed, no request |
| `WVO-FC-TRANSPORT_RETRY_EXHAUSTED` | existing bounded transport retry limit reached | fail closed through existing transport failure path |
| `WVO-FC-PUBLISHER_INCOMPATIBLE` | legacy candidate/review or vNext manifest cannot be revalidated | block handoff or quarantine, no publication |
| `WVO-FC-RUNTIME_IDENTITY` | runtime activation receipt missing or digest mismatch | block Publisher capability gate |
| `WVO-FC-COMPOSITION_LINEAGE` | reviewed commits are absent, unmerged, or cannot be proven in one lineage | block integration card |

### WVO-ARCH-004: Publisher Compatibility Adapter

The compatibility adapter is the only vNext-to-legacy handoff surface.

It produces legacy artifacts only after all selected vNext stages are terminal and valid:

```text
vnext manifest + stage artifacts
→ deterministic compatibility adapter
→ candidate.json + review.json + review.md
→ coordinator state.result points at candidate/review
→ Publisher collect_ready_* revalidates legacy identity and optional vNext manifest
```

Blocking findings that prohibit handoff:

- Any `validate_manifest()` blocking finding.
- Any selected stage missing or SHA-mismatched.
- Any `blind_read_v1` `thesis_match=false`.
- Any legacy candidate validation failure.
- Any legacy review validation failure.
- Any legacy review item with `REJECT`, `hard_failure=true`, or non-empty findings.
- Any Publisher deterministic quality/rewrite/translation finding.

Publisher revalidation contract:

- It always revalidates `candidate.json` and `review.json` using existing functions.
- If `<run-dir>/vnext/manifest.json` exists, it must re-run `validate_manifest()`.
- It must confirm `manifest.final_candidate_sha256 == artifact_sha256(candidate)` and `manifest.legacy_candidate_sha256 == artifact_sha256(candidate)` when `legacy_candidate` is present.
- It must reject manifest mutation, schema drift, run ID drift and article identity drift before collect-ready returns a run.

The manifest never grants approval, apply, commit, tag, push or publication authority. It is evidence beside the legacy candidate, not a replacement for Publisher gates.

### WVO-ARCH-005: Legacy Compatibility And Rollback Identity

Legacy runs remain valid when no vNext artifacts exist:

- `brief.json` with legacy `schema_version: 1` and no `vnext/manifest.json` follows existing `run_pipeline_tick()`.
- Existing coordinator state `active`, `complete` and `failed` semantics stay unchanged.
- Existing Publisher logic can publish legacy completed runs after current validation.

vNext opt-in is explicit:

```json
{
  "version": "EditorialManifestV1",
  "orchestration_mode": "writer_vnext_opt_in_v1"
}
```

There is no shadow A/B. A run is either legacy or vNext opt-in. Mixed mode without a valid manifest is `WVO-FC-SCHEMA_VERSION`.

Rollback identity:

| Artifact | Rollback identity | Fail-closed condition |
|---|---|---|
| Candidate | `artifact_sha256(candidate.json)` plus legacy article identity fields | candidate hash drift, article ID/path drift, invalid legacy schema |
| Review | per-article `candidate_sha256` and reviewer verdict set | review hash mismatch, missing article, reject/hard failure |
| Manifest | `artifact_sha256(manifest)` plus `brief_sha256`, `final_candidate_sha256`, stage artifact hashes | any manifest or artifact SHA mismatch |
| Runtime activation receipt | `runtime_identity_digest` and reviewed runtime commit lineage | missing digest, unreviewed runtime, actor/runtime mismatch |

Rollback means disabling vNext opt-in for future runs or quarantining a specific vNext run. It never rewrites an already accepted artifact in place and never auto-publishes a prior candidate.

### WVO-ARCH-006: Reviewed-Commit Composition Gate

This card does not merge reviewed commits. A later integration card may compose:

- Writer contract candidate `671fdba9bf1b5655cc9182bbf375cadae3efb0b5`, reviewed by `038cf4d2979bf2a1a8ceaf4d44964c3fde5816c6`.
- Runtime Authority candidate `e6d93fba050eac7c22e1a34bf52d8ac4c707a1b3`, reviewed by `38774ddf1bccc77a0b40917322bb100d238469d7`.

Composition gate:

1. Both candidate commits and review commits are readable Git objects.
2. Review evidence has `REVIEW_GO`.
3. Integration base is declared and clean.
4. Changed-file inventory is exactly the union of the two reviewed lineages plus explicit integration glue.
5. Public behavior tests for contract validation, outbox/coordinator ticks, runtime authority and Publisher dry-run pass.
6. Any conflict resolution is separately reviewed, with source references to both lineages.

If any part is missing, the integration card verdict is `BLOCKED / WVO-FC-COMPOSITION_LINEAGE`.

## Forward-Only State Transition Table

| Projection state | Required evidence | Unique next action | Terminal or failure |
|---|---|---|---|
| `LEGACY_ACTIVE` | no vNext manifest; coordinator state active | existing `run_pipeline_tick` | existing complete/failed |
| `VNEXT_MANIFEST_READY` | valid manifest, empty or initialized ledger | first selected stage request | fail on invalid manifest |
| `STAGE_REQUEST_PENDING` | request ledger entry exists; no valid response or failure | wait for existing outbox/inbox/failed | fail on invalid failure receipt |
| `STAGE_RESPONSE_READY` | inbox response matches request SHA | validate response, write stage artifact, append accepted ledger event | fail on schema/hash mismatch |
| `STAGE_ACCEPTED` | stage artifact validates and hashes match | next manifest-declared stage by `sequence` | fail on ambiguous sequence |
| `VNEXT_ARTIFACTS_COMPLETE` | all selected stages accepted | run compatibility adapter | fail on blocking findings |
| `LEGACY_HANDOFF_READY` | candidate/review/review.md valid, manifest sidecar valid | mark coordinator state complete | Publisher later owns publication |
| `PUBLISHER_COLLECTED` | Publisher revalidated legacy payload and sidecar | existing publication transaction | quarantine/block through Publisher |

## Tick Reconstruction And Dedupe Pseudocode

```python
def reconstruct_next_action(run_dir, queue_root):
    brief = read_json(run_dir / "brief.json")
    manifest_path = run_dir / "vnext" / "manifest.json"
    if not manifest_path.exists():
        return legacy_tick(run_dir, queue_root)

    manifest = read_json(manifest_path)
    manifest_gate = validate_manifest_shape_without_side_effects(manifest)
    if manifest_gate.blocking:
        return fail_closed("WVO-FC-SCHEMA_VERSION", manifest_gate.findings)

    ledger = replay_hash_chain(run_dir / "vnext" / "ledger.jsonl")
    accepted = accepted_stage_projection(ledger, manifest)
    pending = pending_transport_projection(ledger, queue_root)
    if pending.count > 1:
        return fail_closed("WVO-FC-AMBIGUOUS_NEXT_ACTION")
    if pending.count == 1:
        return consume_or_wait_for_existing_request(pending.only)

    for stage in manifest["selected_stages"].sorted_by_sequence():
        if stage.stage_type in accepted:
            require_matching_artifact_sha(stage, accepted[stage.stage_type])
            continue
        inputs = collect_declared_inputs(stage, brief, manifest, accepted)
        if inputs.missing:
            return fail_closed("WVO-FC-MISSING_DEPENDENCY", inputs.missing)
        request = build_existing_outbox_request(
            role=role_for(stage.stage_type),
            prompt=render_public_stage_prompt(stage, inputs),
            response_schema=schema_for(stage.stage_type),
        )
        if existing_matching_request_or_artifact(request, stage, ledger):
            return wait_or_accept_existing(request, stage)
        if existing_conflicting_job_id(request, queue_root):
            return fail_closed("WVO-FC-REQUEST_COLLISION")
        append_request_event(ledger, stage, request, inputs)
        create_existing_external_request(queue_root, request)
        return pending(request.job_id)

    if not legacy_candidate_and_review_exist(run_dir):
        return run_compatibility_adapter_or_fail(run_dir, manifest, accepted)
    return complete_state_if_publisher_handoff_valid(run_dir, manifest)
```

## Failure Taxonomy

| Stable code | Owner | Recoverability |
|---|---|---|
| `WVO-FC-SCHEMA_VERSION` | Validator | Fix artifact/schema in a new run or repair card; do not mutate accepted ledger. |
| `WVO-FC-UNKNOWN_STAGE` | Orchestration | Requires a versioned stage migration card. |
| `WVO-FC-MISSING_DEPENDENCY` | Orchestration | Requires producing missing predecessor artifact or quarantining run. |
| `WVO-FC-REQUEST_COLLISION` | Transport | Requires manual investigation; no resend. |
| `WVO-FC-ARTIFACT_TAMPER` | Validator | Quarantine run; accepted artifact cannot be rewritten in place. |
| `WVO-FC-AMBIGUOUS_NEXT_ACTION` | Coordinator | Fix ledger/projection logic before resuming. |
| `WVO-FC-TRANSPORT_RETRY_EXHAUSTED` | Transport | Existing bounded retry exhausted; surface failed run. |
| `WVO-FC-PUBLISHER_INCOMPATIBLE` | Publisher | Quarantine or defer through existing Publisher state. |
| `WVO-FC-RUNTIME_IDENTITY` | Deployment/runtime authority | Refresh activation receipt through runtime authority card. |
| `WVO-FC-COMPOSITION_LINEAGE` | Integration gate | Stop until reviewed commits form one verifiable lineage. |

## Compatibility Matrix

| Run shape | vNext artifacts | Coordinator behavior | Publisher behavior |
|---|---|---|---|
| Legacy create/optimize/rewrite | absent | existing tick path | existing collect-ready and validation |
| Legacy translation | absent | existing multilingual path | existing translation collect-ready |
| vNext opt-in with valid manifest | present | vNext reconstruction path | legacy candidate/review plus sidecar validation |
| vNext partial stage | present with pending ledger | wait or consume existing request | not eligible |
| vNext invalid/tampered sidecar | present but invalid | fail closed | collect-ready blocks/quarantines if reached |
| Unknown future manifest | unsupported version | fail closed | fail closed |

## Publisher Handoff Boundary

Publisher sees the same legacy handoff artifacts it already trusts:

```text
state.schema_version == 1
state.status == "complete"
state.result.candidate == "<run-dir>/candidate.json"
<run-dir>/review.json
<run-dir>/review.md
optional <run-dir>/vnext/manifest.json
```

The vNext sidecar is not a publication input by itself. It is an additional integrity condition for opt-in runs. If the sidecar exists, Publisher revalidates it before candidate selection. If it is absent, Publisher treats the run as legacy.

FAQ, article shape changes, metadata, Schema policy, sitemap, feed and redirects are out of scope for this card.

## Implementation Slices

Current frontier: `WVO-SLICE-001`.

| Slice | Name | Blocking edges | Traces to | Likely files | Verification |
|---|---|---|---|---|---|
| `WVO-SLICE-001` | Compose reviewed contract and runtime authority lineage | none | `WVO-ARCH-006`, `FR-001`, `FR-014` | integration card allowlist, reviewed source files | `git show`, changed-file inventory, relevant tests |
| `WVO-SLICE-002` | Add vNext ledger replay and manifest projection | `WVO-SLICE-001` | `WVO-ARCH-002`, `WVO-ARCH-003`, `FR-005`, `FR-009` | orchestration helper module, tests | RED/GREEN replay tests for dedupe/tamper |
| `WVO-SLICE-003` | Render stage requests through existing writer/reviewer outbox | `WVO-SLICE-002` | `WVO-ARCH-001`, `FR-006`, `FR-010` | outbox/coordinator integration seam, tests | request SHA stability and no new role tests |
| `CHECKPOINT-001` | Contract and transport checkpoint | `WVO-SLICE-001..003` | `US-002`, `US-003` | evidence only | rerun contract/outbox/coordinator targeted tests |
| `WVO-SLICE-004` | Implement forward-only vNext coordinator tick | `WVO-SLICE-003` | `WVO-ARCH-002`, `WVO-ARCH-003`, `FR-008`, `FR-011` | coordinator, tests | pending/complete/failed reconstruction tests |
| `WVO-SLICE-005` | Add compatibility adapter to legacy candidate/review | `WVO-SLICE-004` | `WVO-ARCH-004`, `FR-012`, `FR-013` | pipeline helper, tests | legacy validation passes; blocking findings stop handoff |
| `WVO-SLICE-006` | Add Publisher optional sidecar revalidation | `WVO-SLICE-005` | `WVO-ARCH-004`, `FR-014`, `FR-017` | Publisher, tests | collect-ready blocks invalid sidecar and accepts legacy absent sidecar |
| `CHECKPOINT-002` | Handoff checkpoint | `WVO-SLICE-004..006` | `US-004` | evidence only | Publisher dry-run, no publication mutation |
| `WVO-SLICE-007` | Add rollback identity and runtime activation receipt checks | `WVO-SLICE-006` | `WVO-ARCH-005`, `WVO-ARCH-006`, `FR-001`, `FR-002` | runtime authority/Pub gate integration, tests | digest mismatch fail-closed |
| `WVO-SLICE-008` | End-to-end vNext public behavior tests | `WVO-SLICE-007` | all card FRs | tests and evidence | full targeted suite, `git diff --check` |

Each implementation slice must be one focused card with its own allowlist, public-behavior RED/GREEN, evidence path, and candidate commit. No slice may introduce a fixed Research to Outline to Blind Reader to Fact Checker template; stages remain manifest-declared.

## Rejected Alternatives

| Alternative | Decision |
|---|---|
| Second queue for vNext stages | Rejected. Existing outbox already supplies strict request/response SHA, archive, failed receipts and bounded retry. |
| New Gemini roles for every editorial stage | Rejected. Stage semantics fit in prompt/schema/artifact identity while preserving `writer`/`reviewer` runner compatibility. |
| Mega-agent that performs plan, claims, blind read, candidate and review in one prompt | Rejected. It cannot provide per-stage dedupe, artifact hashes or deterministic recovery. |
| Fixed Research to Outline to Blind Reader to Fact Checker pipeline | Rejected. The contract says selected stages are optional and manifest-declared. |
| Manifest publication authority | Rejected. Publisher remains sole publication owner; manifest is integrity evidence only. |
| Shadow A/B migration | Rejected. vNext uses explicit versioned opt-in boundary; legacy absence remains legacy. |
