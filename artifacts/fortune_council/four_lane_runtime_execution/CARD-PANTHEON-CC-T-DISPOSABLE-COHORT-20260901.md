---
id: PANTHEON-CC-T-DISPOSABLE-COHORT-IMPLEMENTATION-20260901
project: bluemaple18-home/Pantheon
type: domain-local-bounded-implementation
status: READY_FOR_IMPLEMENTATION
canonical_main_sha: 0f61545f8c6b561742b27792b8fef11ae8b1ccc5
accepted_parent_sha: 836d5f0d1d62b58ad886aa37863c15ce41d233ec
branch: codex/pantheon-cc-t-disposable-cohort-20260901
launchctl_authorization: NOT_AUTHORIZED
gate_d_e: NOT_RUN
provider_calls: 0
public_publish: 0
production_mutation: 0
---

# Pantheon C-C/T disposable cohort implementation card

## 1. Goal

Deliver the minimum Pantheon-local implementation required for a later, separately authorized Gate D/E runtime acceptance:

- one immutable fresh acceptance session;
- one disposable seven-service launchd cohort;
- four exact lane runs (`new`, `rewrite`, `i18n-new`, `i18n-rewrite`);
- real Coordinator → lane outbox → lane-specific Runner → sealed transport → normal inbox → Coordinator terminal flow;
- exact Publisher plan-only verification;
- successful seven-service teardown;
- zero production fingerprint drift.

This implementation does **not** grant `GO_FOUR_LANE_RUNTIME_CURRENT`. It only produces a reviewable C-C/T code candidate. Bootstrap, activation, shadow workload execution, and launchctl mutation remain forbidden until an independent `C-C_T_REVIEW_GO` and explicit Owner acceptance-launchctl authorization.

## 2. Accepted upstream authority

The implementation branch is rooted directly at:

`836d5f0d1d62b58ad886aa37863c15ce41d233ec`

Accepted code chain:

`b13bc765e9f694b3d9eeefc65335a5410cf5d898`
→ `c4db5bead4c3744022f9c7ff7450487a0d8e36c9`
→ `2a38090ba12ba6c6732f485af96a39e841077ede`
→ `836d5f0d1d62b58ad886aa37863c15ce41d233ec`

Independent review receipts are external evidence only:

- R2: `6897bb5d54a647b005b1422b207039f856ef232c` / `R2_REVIEW_GO`
- C-A: `1ea615ad4096077a2b82af86a2effb0c487c582d` / `CA_REVIEW_GO`
- C-B: `fa2e6cb65d5f57209fd3aebb3020246549ce2bc6` / `CB_REVIEW_GO`

They must not become candidate parents and must not be cherry-picked into this branch.

The old WIP snapshot `b46224ed6adbda6e344e050b5654617db9eaae41` is explicitly excluded. It diverges before accepted C-A/C-B, touches the shared installer, and is neither an implementation base nor a patch source.

## 3. Fresh-session architecture ruling

The accepted design is **fresh generation**, not a shared manifest schema change.

Authority graph:

`fresh random session nonce`
→ `fresh acceptance generation`
→ `runtime_identity_digest`
→ `manifest_digest`
→ `7 readiness acknowledgements`
→ `7 ack digests`
→ `activation barrier`
→ `activation_token_digest`

No `acceptance_session_token` is added to the shared manifest, readiness acknowledgement, barrier, or activation-token schemas.

The acceptance generation is the pre-activation session authority. The activation-token digest is the post-readiness cohort authority. Readiness acknowledgements cannot depend on the future activation token.

### Freshness implementation contract

1. Generate at least 128 random bits for every attempt.
2. Derive `generation = acceptance-<sha256(nonce)>`; use a collision-resistant prefix accepted by the existing generation grammar.
3. Store only `session_nonce_digest` in the immutable plan and receipts, not the raw nonce.
4. Derive one canonical acceptance root from a fixed acceptance base plus the generation. The caller may select the base, but may not redirect one generation to a second root.
5. Atomically create the generation root with `exist_ok=False` before any plist, readiness acknowledgement, or barrier can exist.
6. Never erase a failed generation root to retry it. A failed or interrupted attempt requires a new session ID, nonce, generation, manifest, roots, bundles, and plan authority.
7. Preserve final or failed session evidence under the generation root. Teardown removes disposable runtime artifacts but not the terminal evidence proving that the generation was consumed.
8. Reject production, legacy, fixed-test, or previously existing generations before launchctl mutation.
9. Reject a pre-existing ready root, barrier, session plan, terminal receipt, teardown receipt, plist root, or runtime residue before launchctl mutation.
10. First version has no cross-session resume.

This deterministic generation-root namespace is the reuse guard. It is not a second ledger, registry, FSM, or database.

## 4. Confirmed minimum Coordinator seam

Existing `cycle_once(..., exact_run_ids=...)` restricts run selection but still invokes inline `process(...)` after `_advance(...)` creates a pending job. That cannot prove consumption by the four independently launched lane Runner services.

A minimal production-default-preserving seam is therefore authorized:

- Python API: `external_workers_only: bool = False`
- CLI: `--external-workers-only`
- behavior when false: byte-for-byte existing production behavior
- behavior when true:
  - Coordinator still validates the formal runtime and exact-run selection;
  - Coordinator still calls `_advance(...)` to create normal lane outbox work;
  - Coordinator does **not** invoke inline Runner `process(...)`;
  - a later Coordinator tick still consumes normal inbox responses and advances terminal state;
  - no queue scan, scheduling, response writing, candidate writing, review writing, or terminal-state writing is transferred to the acceptance controller.

The implementation result must record:

- `why_needed`: independent lane-service consumption evidence is otherwise impossible;
- `exact_changed_contract`: only suppression of inline `process(...)` in explicitly requested mode;
- `default_production_behavior_unchanged`: flag absent/false preserves current behavior;
- `rollback`: remove flag and the single guarded branch.

No wider Coordinator refactor is allowed.

## 5. Implementation allowlist

Initially allowed:

- `scripts/pantheon_four_lane_acceptance_controller.py`
- `scripts/agy_gemini_coordinator.py` only for the bounded `external-workers-only` seam
- `tests/test_pantheon_four_lane_acceptance_controller.py`
- `tests/test_agy_gemini_coordinator.py` only for the bounded seam
- this card, one C-C/T result, and raw evidence under the existing four-lane acceptance artifact tree

The controller file already owns C-A compilation helpers. C-C/T may extend that same Pantheon-local controller rather than introduce another runtime owner.

Not allowed without a new exact blocker and Owner architecture ruling:

- `scripts/pantheon_content_runtime_manifest.py`
- shared production launchd installer scripts
- Runner transport or R2 authority
- Publisher implementation
- multilingual pipeline
- production plist files
- scheduler, queue, registry, FSM, database, session ledger, or second barrier

## 6. Immutable session plan

The controller must build and atomically publish one strict plan after the final candidate actor is frozen and all four C-A bundles have been compiled on that exact clean actor.

Required fields:

- `schema_version`
- `session_id`
- `session_nonce_digest`
- `generation`
- `accepted_parent_sha`
- `actor_sha`
- `manifest_path`
- `manifest_digest`
- `runtime_identity_digest`
- `service_labels`
- `acceptance_root`
- `queue_root`
- `publisher_state_root`
- `log_root`
- `evidence_root`
- `plist_root`
- `ready_root`
- `barrier_path`
- four exact run IDs
- four exact lane identities
- four sealed bundle paths
- four sealed bundle raw digests
- four sealed bundle semantic digests
- immutable translation dependency graph
- C-B expected target run IDs
- C-B expected pending digests
- C-B expected plan digest
- `provider_call_budget = 0`
- `public_publish_budget = 0`
- `production_mutation_budget = 0`
- teardown policy
- production-before fingerprint
- `plan_digest`

`accepted_parent_sha` remains `836d5f0d...`; `actor_sha` is the eventual exact C-C/T candidate SHA. The two must not be conflated.

Plan publication requirements:

- owner-only regular file;
- canonical non-symlink path;
- temp file, fsync, atomic rename, parent fsync;
- strict schema and exact-key validation;
- digest reconstructed from all fields except `plan_digest`;
- published plan immutable for the session;
- no post-publication bundle, run, root, dependency, budget, or actor rebinding.

## 7. Disposable seven-plist cohort

Render exactly these labels under the acceptance-only plist root:

- `com.pantheon.agy-content-publisher`
- `com.pantheon.agy-gemini-coordinator`
- `com.pantheon.agy-gemini-new`
- `com.pantheon.agy-gemini-rewrite`
- `com.pantheon.agy-gemini-i18n-new`
- `com.pantheon.agy-gemini-i18n-rewrite`
- `com.pantheon.content-capacity-guard`

Requirements:

- use existing manifest schema, barrier-exec, service entrypoints, and labels;
- every plist binds the same exact actor, manifest, generation, isolated roots, and barrier path;
- mode `0600`, canonical owner-only regular file, atomic publication;
- no writes to `~/Library/LaunchAgents`;
- no shared installer invocation or modification;
- no root overlap with production;
- preflight requires all seven production labels unloaded before any bootstrap;
- Publisher is rendered activation-only from first bootstrap;
- Coordinator uses exact run IDs and `--external-workers-only`;
- each lane Runner is lane-specific and bound to its exact sealed bundle authority;
- static aggregate validation must pass before launchctl is even eligible.

## 8. Controller authority boundary

The controller may:

- reserve and initialize the deterministic acceptance root;
- create immutable session artifacts;
- render and statically validate disposable plists;
- call existing CLI entrypoints with externally pinned exact arguments;
- bootstrap and bootout only after later authorization;
- wait for exact receipts and validate digests;
- invoke C-B with exact plan selectors;
- collect evidence, compare fingerprints, and write closeout receipts;
- own successful teardown.

The controller may not:

- select queue work dynamically;
- decide Writer/Reviewer ordering;
- add or swap R2 bundle entries;
- consume Runner work;
- write outbox responses or normal inbox;
- write candidates, reviews, translation state, or run terminal state;
- call internal Python functions to impersonate service consumption;
- execute Publisher publish/tag/push/deploy;
- change production runtime, labels, plists, queue, state, ledger, or content.

## 9. Required local/static test matrix

### Session freshness

- fresh current generation, pristine root → PASS
- prior-generation one ACK copied into current ready root → RED
- prior-generation 7/7 ACKs copied into current ready root → RED
- ACK generation edited without digest reconstruction → RED
- ACK digest reconstructed while manifest/runtime identity remain prior-generation → RED
- wrong manifest digest → RED
- wrong runtime identity digest → RED
- wrong service label → RED
- missing 1/7 ACK → RED
- foreign or duplicate ACK → RED
- pre-existing ready root → RED before launchctl mutation
- pre-existing barrier → RED before launchctl mutation
- same generation second session → RED
- teardown followed by same-generation reuse → RED
- wrong barrier/token at service entry → RED before queue/state I/O
- fresh 7/7 current-generation ACKs → barrier PASS

### Coordinator seam

- default call still invokes inline `process(...)`
- `external_workers_only=True` never invokes inline `process(...)`
- external mode still creates the expected pending lane outbox through `_advance(...)`
- external mode preserves exact-run restrictions and rejects missing/foreign run IDs
- after a real-format inbox response exists, a later external-mode Coordinator tick consumes it and advances normally
- CLI flag maps exactly to the Python argument
- automatic sweeps remain incompatible with exact-run mode

### Disposable plist and lifecycle

- exactly seven expected labels, no duplicates or foreign labels
- all plists share actor/manifest/generation/root identity
- Publisher activation-only at initial bootstrap
- Coordinator exact-run plus external-worker-only arguments
- lane-specific Runner mapping and sealed authority pins
- unsafe path, owner, mode, symlink, actor, manifest, generation, label, or root drift → RED
- production label loaded snapshot → RED before bootstrap
- root overlap → RED before bootstrap
- bootout success and failure classification are deterministic
- teardown is idempotent only for already-absent services in the same terminal session; it never authorizes generation reuse

Tests must use mocks/fakes for launchctl. No implementation test may load services, touch production, invoke providers, publish, deploy, tag, or push.

## 10. Candidate and review sequence

1. Implement only the allowlisted local/static capability.
2. Run focused unit tests, affected regressions, Python compile, and `git diff --check`.
3. Freeze one exact clean C-C/T candidate commit.
4. Obtain a fresh independent zero-write code review of `836d5f0d.....<candidate>`.
5. Only `C-C_T_REVIEW_GO` permits exact-actor C-A bundle compilation and immutable session-plan preparation.
6. Conduct a separate read-only plan review.
7. Obtain explicit Owner acceptance-launchctl authorization.
8. Only then may Gate D/E bootstrap, activation, four-lane execution, Publisher plan-only, teardown, and final closeout occur.

A Reviewer who edits code, tests, or candidate receipts becomes Repair Author and cannot issue the same-round independent review verdict.

## 11. Stop conditions

Stop with `BLOCKED_<EXACT_REASON>` if any of the following becomes necessary or occurs:

- shared manifest or shared installer modification;
- a new session ledger, registry, FSM, database, queue, runtime, or barrier;
- controller direct queue/response/candidate/review/terminal writes;
- Coordinator cannot run exact external-worker mode without production-default behavior change;
- lane Runner cannot independently claim its lane outbox;
- generation/root reuse or non-pristine runtime artifacts;
- actor, manifest, generation, bundle, barrier, or token mismatch;
- live provider or credential allocator access;
- production label loaded before acceptance;
- Publisher selector cardinality differs from one or any execute/tag/push/deploy path becomes reachable;
- teardown cannot prove seven services absent and no pending/processing residue;
- production fingerprint drift;
- only synthetic function composition exists without later real-service evidence.

## 12. Current state after card freeze

- main mutation: `0`
- production mutation: `0`
- runtime activation: `0`
- launchctl: `NOT_AUTHORIZED / NOT_RUN`
- provider calls: `0`
- public publish: `0`
- Gate D/E: `NOT_RUN`
- final verdict: not yet eligible

Next code action: implement the bounded `external-workers-only` seam and the local/static C-C/T session/plist/teardown controller contracts on this branch.