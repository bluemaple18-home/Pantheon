# Pantheon Writer vNext Runtime Activation Plan

## Verdict

`RUNTIME_ACTIVATION_PLAN_READY_FOR_REVIEW`

本計畫只判定「下一階段非 production Runtime Activation 切片可進入獨立 Review」。它不代表 runtime 已啟用、不代表 production ready，也不授權 canary、publication、tag、push、deploy 或正式產文。正式服務維持 `0/4`，production 維持 `NO-GO`。

## Scope Boundary

| 項目 | 結論 |
|---|---|
| Source base | formal task HEAD `7af82c40439af642a9f91cb7a4c3b3146325c404`; local `main` `c758f34362b1503a41c8ff48885ede896ce26335` |
| Handoff | `.ai/handoff_20260811_pantheon_writer_vnext_integrated_runtime_activation.md` 只讀，不修改 |
| Writable output | `docs/pantheon_writer_vnext_runtime_activation_plan.md` 與 `artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/writer_vnext_runtime_activation_plan_001/` |
| Forbidden runtime actions | 未執行 push、deploy、publication、canary、tag、network write、launchctl、排程、服務啟停或正式產文 |
| CodeGraph | bounded prepare 通過，task-semantic query 已完成，另以限域 source confirmation 核對入口 |

## Official Entry And Authority Matrix

| Boundary | Official entry | Authority owner | Source confirmation | Current conclusion |
|---|---|---|---|---|
| Runtime identity manifest | `scripts/pantheon_content_runtime_manifest.py create/validate/aggregate/barrier-*` | runtime activation operator | `scripts/pantheon_content_runtime_manifest.py` | Entry exists for identity, plist receipt, readiness ack and barrier |
| Activation token | `scripts.pantheon_runtime_activation:publish_generation_token` and `validate_service_before_io` | runtime activation operator | `scripts/pantheon_runtime_activation.py` | Entry exists, but no non-production seven-service probe artifact yet |
| Create/register run | `scripts/agy_gemini_coordinator.py register` and `cycle --new-matrix-sweep` | Gemini coordinator | `scripts/agy_gemini_coordinator.py` | Entry exists, but lacks capability receipt linking create output to run input |
| Run candidate/review | `scripts/agy_gemini_coordinator.py cycle` plus `scripts/agy_gemini_runner.py process-once` | Gemini runner/coordinator | `scripts/agy_gemini_coordinator.py`, `scripts/agy_gemini_runner.py` | Entry exists, formal runtime tick is checked before queue/state I/O |
| Select/publish/transaction/tag/push preflight | `scripts.agy_content_publisher:formal_capability_preflight` | content publisher | `scripts/agy_content_publisher.py` | Bounded dry-run entry exists for select, publish, transaction, tag, push |
| Production publisher mutation | `scripts/agy_content_publisher.py --queue-root ... [--push]` | content publisher deployment actor | `scripts/agy_content_publisher.py`, `docs/pantheon_deployment_workflow.md` | Exists but not authorized in this card |

## Seven Capability Matrix

| Step | Formal production entry | Input | Output | Identity/correlation | Current status |
|---|---|---|---|---|---|
| `create` | `scripts/agy_gemini_coordinator.py cycle --new-matrix-sweep` or `register <run_dir>` | content matrix or prepared `brief.json`; formal runtime env; queue root | registered run state with `run_id`, `run_dir`, `correlation_id` | `register_run` records `correlation_id`; service label `com.pantheon.agy-gemini-coordinator` | `ENTRY_EXISTS / EVIDENCE_GAP` |
| `run` | `scripts/agy_gemini_coordinator.py cycle`; `scripts/agy_gemini_runner.py process-once` | active run state, outbox job, lane queue | `candidate.json`, `review.json`, `run-evidence.json`, state transition | runner/coordinator formal runtime tick; run_id and job_id | `ENTRY_EXISTS / EVIDENCE_GAP` |
| `select` | `scripts.agy_content_publisher:formal_capability_preflight(capability="select")`; production selector also via `--exact-run-id` | completed run IDs | normalized selected run IDs | `correlation_id`, runtime identity digest, exact run ID validation | `ENTRY_EXISTS / NEEDS_PROBE_ARTIFACT` |
| `publish` | `formal_capability_preflight(capability="publish")`; production via publisher CLI dry-run/non-dry-run | selected run IDs, queue root, state root | dry-run or published evidence; no production mutation in probe | same `correlation_id`, publisher runtime identity digest | `ENTRY_EXISTS / NEEDS_POSITIVE_AND_FAIL_CLOSED_PROBES` |
| `transaction` | `formal_capability_preflight(capability="transaction")`; production via `_isolated_transaction_worktree` | publisher state root and actor repo | sandbox transaction operation trace; production transaction worktree when authorized | transaction name derives from `correlation_id:transaction:<actor_sha>` | `ENTRY_EXISTS / NEEDS_PROBE_ARTIFACT` |
| `tag` | `formal_capability_preflight(capability="tag")`; production via `_stage_commit_tag_push(push=False)` | release version, staged content changes | annotated release tag in transaction boundary | release plan `v<version>`; commit SHA | `ENTRY_EXISTS / NEEDS_PROBE_ARTIFACT` |
| `push` | `formal_capability_preflight(capability="push")`; production via `_stage_commit_tag_push(push=True)` | release commit and tag | atomic push plan/result or unresolved push control record | atomic `git push --atomic origin HEAD:main v<version>` | `ENTRY_EXISTS / PRODUCTION_MUTATION_NOT_AUTHORIZED` |

## Evidence Gap Matrix

| Gap | Affected steps | Why it matters | Required non-production evidence |
|---|---|---|---|
| No single execution-line receipt | all seven | Similar run IDs and successful helpers do not prove one chain | One synthetic `execution_line_id` and `correlation_id` carried through create, run, select, publish, transaction, tag, push probes |
| Positive and fail-closed artifacts not paired | all seven | Production canary gate requires independent `PASS` and `BLOCKED` artifacts | Separate artifact files per step: positive probe plus missing input, wrong identity/correlation, no selector, and mutation refusal probes |
| Create/run not exposed through the same capability preflight surface as publisher | create, run | Publisher has bounded preflight; coordinator/runner need equivalent receipt shape | Add or document a coordinator non-production preflight that creates a synthetic brief, advances one run, and writes a receipt without production write |
| Push readiness cannot be proven by real remote mutation in this card | push | User forbids push and production mutation | Use sandbox dry-run trace for pre-review; production push remains `NO-GO` until separately authorized |
| Capacity evidence not measured for two cycles | create, run, publish, transaction | Capacity rule requires two representative cycles and cleanup/stop-loss proof | Synthetic two-cycle run measuring queue, runner, publisher state, logs, transaction temp roots, RSS/swap, file counts |

## Non-Production E2E Flow

1. Build a synthetic runtime manifest in a private sandbox root with canonical actor, queue, publisher state and log directories.
2. Start with `PANTHEON_FORMAL_RUNTIME=1` and a test-only generation identity; do not use production plist or production launchd.
3. Create a synthetic run from a fixed local source record with at most one article and record `execution_line_id` plus `correlation_id`.
4. Advance the run via the coordinator/runner formal boundary using local/sandbox transport only. Network-backed model execution is not part of this card and must be separately authorized.
5. Select exactly that synthetic run ID.
6. Invoke publisher bounded capability preflight for `select`, `publish`, `transaction`, `tag`, and `push` in one sandbox, preserving the same `correlation_id`.
7. Write separate `PASS` and `BLOCKED` artifacts for every step; blocked probes must use the same official boundary and refuse mutation.

## Storage Capacity And Stop-Loss Plan

| Write path | Type | Budget field | Initial budget |
|---|---|---|---|
| `.work/gemini-runner/runs` | run state | `max_file_count`, `max_bytes` | 64 files, 2 MiB per synthetic execution line |
| `.work/gemini-runner/outbox`, `processing`, `inbox`, `archive`, `failed` | queue transport | `max_file_count`, hourly growth | 128 files, 8 MiB, max 2 cycles |
| `.work/gsc-copy/<run_id>` | brief/candidate/review/evidence | per-run bytes | 20 MiB per run |
| `.work/content-publisher` | ledger, evidence, lock, push control | state bytes and file count | 64 MiB, 256 files |
| publisher transaction temp roots | isolated worktree | peak bytes and cleanup | max 1 transaction root, must be removed before PASS |
| configured publisher logs | stdout/stderr | rotation | 32 MiB max, retain 4 MiB per stream |
| `.codegraph/` | local index | out-of-band worktree-local state | ignored, not part of production runtime capacity |

Before any runtime activation canary, run two representative non-production cycles and record: project bytes, file count, host free space, process RSS, swap, hourly growth, peak temp transaction size, cleanup result, and stop command result. Any missing metric keeps production `NO-GO`.

Stop-loss triggers:

| Trigger | Action |
|---|---|
| Project bytes or file count exceeds approved budget | Stop only the runtime activation process; do not delete unrelated data |
| Host free space below `max(20 GiB, 10%)` | Stop writes and disable auto-restart for this feature |
| Growth rate exceeds 2x estimate for two samples | Stop writes before next cycle |
| Transaction temp root remains after cleanup | Block next cycle and preserve evidence |
| Unregistered write path appears | Stop, classify path, update inventory before retry |

## Vertical Slice Plan

| Slice | Goal | Blocking edges | Verification | Likely files |
|---|---|---|---|---|
| `RA-SLICE-001` | Define shared capability receipt schema for seven steps | none | schema lint; sample invalid receipt fails closed | docs/evidence only or later `templates/production_canary_capability_receipt.json` if authorized |
| `RA-SLICE-002` | Add coordinator create/run non-production preflight receipt | `RA-SLICE-001` | missing brief, bad correlation, wrong lane fail closed | `scripts/agy_gemini_coordinator.py`, tests |
| `RA-SLICE-003` | Normalize publisher `formal_capability_preflight` output to same receipt schema | `RA-SLICE-001` | select/publish/transaction/tag/push positive and blocked probes | `scripts/agy_content_publisher.py`, tests |
| Checkpoint A | Review end-to-end schema and entry parity | `RA-SLICE-001..003` | independent strict Review on receipt artifacts | review card |
| `RA-SLICE-004` | Build synthetic non-production E2E harness with one correlation | Checkpoint A | create->run->select->publish->transaction->tag->push dry-run artifact chain | scripts/tests only in later card |
| `RA-SLICE-005` | Add capacity two-cycle measurement and cleanup verification | `RA-SLICE-004` | capacity receipt `PASS`; stop-loss negative probe | capacity guard/harness files |
| `RA-SLICE-006` | Add production-canary readiness receipt gate invocation | `RA-SLICE-004`, `RA-SLICE-005` | readiness gate returns `READY` only with all artifacts and `canary_created=false` | receipt templates/gate wiring |
| Checkpoint B | Production canary authorization decision point | `RA-SLICE-004..006` | independent Review + capacity `PASS` + readiness `READY` | mainline authorization |

Current frontier: `RA-SLICE-001`, then `RA-SLICE-002` and `RA-SLICE-003`. Production canary is not in the frontier.

## Review Contract

Future strict independent Review must pin:

| Field | Required value |
|---|---|
| Base | Current candidate commit of the slice under review |
| Candidate | Full SHA of the slice candidate |
| Evidence | One unique evidence directory per slice |
| Required checks | receipt schema validation, positive/negative probe replay where non-mutating, capacity receipt review when applicable, `git diff --check`, allowlist audit |
| Prohibited inference | no claim of production readiness from dry-run, status text, HTTP 200, tag existence or push exit alone |

## Rejected Alternatives

| Alternative | Rejection reason |
|---|---|
| Manual single article success | Does not prove formal seven-step chain or fail-closed behavior |
| Temporary shell scripts as proof | Not production official entrypoints |
| Create canary first then backfill receipt | Violates readiness gate and user authorization |
| Split selector, canary and entry repair into parallel lines | Breaks execution-line identity and makes correlation unprovable |
| Use real remote tag/push in this card | Explicitly forbidden; production remains `NO-GO` |
