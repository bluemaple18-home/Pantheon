---
status: COMPLETE
owner: codex
task: pantheon_acceptance_b_gen06_queue_reactivation_rca_20260828
created_at: 2026-08-28T18:25:49+08:00
scope: read_only_rca
---

# RESULT — gen06 queue reactivation RCA

## Status

NO-GO for further production mutation until one bounded Repair or explicitly authorized registry reactivation path is selected.

This RCA was read-only against production/runtime state. Source, queue registry, continuation state, publisher state, tags, content, and provider were not mutated. The only files created by this task are this RCA card/result.

## Current facts

- Runtime target: `<runtime-root>/queue/translation-runs/auto-i18n-ja-1414b75a404721e95e74`.
- gen06: missing.
- gen07: missing.
- published artifact: missing.
- run-local continuation: `status=active`, `next_generation=6`, `semantic_budget=2`, `completed_generations=[5]`, `abandoned_generations=[4]`.
- `authority-transition-05.json`: exists; canonical JSON state hash matches current `continuation/state.json`.
- queue registry: `<runtime-root>/queue/runs/f46cda9eaa9ded446bf8e6c6.json`.
- queue registry status: `complete`.
- queue registry `last_job_id`: `32570d45e3dd22f0fea558c414063bd186002c0d`.
- queue registry result: `status=complete`.
- lane `i18n-new` outbox/processing after observation: `0/0`.
- provider count for the failed exact-cycle attempt: `0`.

## Why exact-run-id was not selected

`scripts/agy_gemini_coordinator.py` selects candidates from queue registry, not from run-local continuation state:

- `_active_states()` reads `<queue-root>/runs/*.json` and keeps only `state.get("status") == "active"` (`scripts/agy_gemini_coordinator.py:2289-2294`).
- exact-run-id filtering is applied only after that active registry list is built (`scripts/agy_gemini_coordinator.py:5321-5331`).
- lane selection is then applied to those already-active states (`scripts/agy_gemini_coordinator.py:5338-5358`).

Therefore the target run is known, but because its queue registry state is `complete`, it never reaches `_lane_for_state()`. The `--exact-run-id` argument cannot resurrect a complete registry entry; it only narrows already-active candidates.

## Four RCA evidence items

### 1. Last successful comparable version / behavior

No successful prior example was found for this exact lifecycle: terminal Reviewer REJECT complete state → formal next-generation authorization → queue registry reactivation from `complete` to `active` → exact coordinator selection.

Closest successful comparable behavior:

- gen04 terminalization → gen05 continuation worked while the queue registry was already `active`.
- Evidence from `pantheon_acceptance_b_gen05_production_release_23e_retry1_20260828/RESULT-PANTHEON-ACCEPTANCE-B-GEN05-PRODUCTION-RELEASE-23E-RETRY1-20260828.md`:
  - exact-run returned `status=ok`, `active=1`;
  - lane `i18n-new` queued `1`;
  - target writer job `61a83c341d39c882d5eed8ea23b7f805a89085e3` was created.

That proves coordinator can select this run when the queue registry is active. It does not prove any existing successful complete→active queue reactivation seam.

### 2. First failing commit / mechanism

First failing mechanism: `f12f24315d fix: authorize one rejected translation retry`.

Evidence:

- `f12f24315d` introduced `authorize_next_generation_after_reviewer_reject` in `scripts/agy_multilingual_pipeline.py`.
- The implementation writes:
  - `<run-dir>/continuation/authority-transition-05.json`;
  - `<run-dir>/continuation/state.json`.
- It does not update `<queue-root>/runs/<namespace>.json`.
- The tests added in that commit cover pipeline-local continuation behavior, crash replay, and fake next-generation creation, but do not cover coordinator exact-cycle selection through queue registry.

Precise mechanism:

1. gen05 terminal Reviewer REJECT caused coordinator to mark queue registry `status=complete`.
2. `authorize-next-generation-after-reviewer-reject --execute` updated run-local continuation to `active,next_generation=6`.
3. Queue registry remained `complete`.
4. coordinator `cycle --exact-run-id` filtered active registry entries first, so target run was excluded before lane selection.

### 3. Authoritative owner and durable invariant

There are two state owners:

- `scripts/agy_multilingual_pipeline.py` owns run-local continuation lifecycle under `<run-dir>/continuation/`.
- `scripts/agy_gemini_coordinator.py` owns queue registry lifecycle under `<queue-root>/runs/*.json`, and uses it as the authoritative scheduler input.

Durable invariant that was broken:

When a run-local continuation is made executable again (`status=active,next_generation=N`) and the intended next action is coordinator execution, the queue registry for the same run id must also be active or the formal scheduler must have a hash-bound way to reactivate it. Otherwise the system has an executable continuation that no formal exact cycle can select.

This is a cross-lifecycle boundary issue, not a provider/content issue.

### 4. RED-capable provider=0 harness

Command used on an isolated temp copy:

```text
python3 -m scripts.agy_gemini_coordinator --queue-root <tmp>/queue --repo-root <repo-root> --lane-mode cycle --exact-run-id auto-i18n-ja-1414b75a404721e95e74
```

Harness shape:

- copied target run directory into `<tmp>/queue/translation-runs/...`;
- copied queue registry entry with `status=complete`;
- rewrote only copied registry `run_dir` to the temp run path;
- copied minimal lane inbox/archive/failed artifacts;
- no provider credentials, no production state, no production queue.

Observed RED output:

```json
{
  "status": "ok",
  "active": 0,
  "complete": 0,
  "failed": 0,
  "runner": {"status": "idle"},
  "lanes": {
    "new": {"active": 0, "queued": 0, "processing": 0},
    "rewrite": {"active": 0, "queued": 0, "processing": 0},
    "i18n-new": {"active": 0, "queued": 0, "processing": 0},
    "i18n-rewrite": {"active": 0, "queued": 0, "processing": 0}
  }
}
```

Post-harness checks:

- copied registry remained `complete`;
- copied `generations/06` remained missing;
- copied i18n-new outbox remained `0`;
- provider count remained `0`.

## DATA_ONLY verdict

Not DATA_ONLY.

The data is internally explainable but not self-healing:

- run-local continuation is correctly authorized for gen06;
- queue registry remains terminal `complete`;
- the existing exact cycle only considers active queue registry states.

Without a formal registry reactivation step, repeating coordinator exact cycle will keep idling. Manually editing registry would violate the owner boundary.

## Existing formal entrypoints

Existing but too broad as-is:

- `scripts.agy_gemini_coordinator resume <run_dir>` calls `resume_run()`.
- `resume_run()` reads the queue registry state and sets `status="active"`, clears terminal result/error fields, and writes registry back.
- It does not bind `authority-transition-05.json`, terminal candidate/review hashes, or current continuation canonical hash.

Existing but not applicable:

- `replace-failed-external-job --resume-replacement` only applies to failed replacement residue and requires failed/archived replacement evidence. Current blocker is registry terminal `complete`, not failed external replacement requeue.

## Minimum-sufficient Repair frontier

One bounded Repair, no new registry/FSM/database:

- Add a narrow formal registry reactivation seam for terminal Reviewer REJECT next-generation authorization, or extend `authorize-next-generation-after-reviewer-reject --execute` to update queue registry under the same identity/lock boundary.
- It must bind:
  - run id;
  - queue registry namespace/path;
  - current registry hash/status/result;
  - run-local `authority-transition-05.json`;
  - canonical `continuation/state.json` hash;
  - terminal candidate/review/source/locale/source-ref hashes;
  - absence of gen06/gen07/publish.
- It must fail closed for:
  - missing transition;
  - state hash drift;
  - registry not `complete` with expected terminal result;
  - wrong run dir;
  - gen06 already present;
  - publish residue;
  - ambiguous/multiple registry entries.

After that mutation is formally authorized and applied, the existing coordinator exact cycle should be able to select the run normally and create gen06.

## Why not less

Less than this would be a manual registry edit or generic `resume` call. That would reactivate scheduler state without binding the terminal-authority transition that made gen06 legal.

## Why not more

No new scheduler, registry, FSM, database, provider retry policy, publisher change, or gen06 generation logic is needed. The failure is at the existing boundary between run-local continuation authorization and queue registry scheduler activation.

## Do not absorb

Do not absorb a generalized lifecycle manager or second registry. Do not change provider, reviewer, publisher, content contracts, or planning. Do not loosen exact-run selector semantics to read arbitrary run-local continuation state without a queue registry authority check.

## Commands run

- CodeGraph context/explore for `authorize_next_generation_after_reviewer_reject`, `continue_writer_reviewer`, `resume_run`, `_active_states`.
- Read-only runtime state snapshot for target run, queue registry, lane replacement receipt, and job locations.
- Read-only source line checks around `_active_states`, exact-run filtering, `resume_run`, and `authorize_next_generation_after_reviewer_reject`.
- Read-only git history checks:
  - `git log --oneline -- scripts/agy_multilingual_pipeline.py scripts/agy_gemini_coordinator.py`
  - `git log --oneline -S 'authorize_next_generation_after_reviewer_reject' -- scripts/agy_multilingual_pipeline.py scripts/agy_gemini_coordinator.py`
  - `git show f12f24315d -- scripts/agy_multilingual_pipeline.py`
- Provider=0 RED harness on isolated temp copy.

## Final classification

`FORMAL_MISSING_SEAM`: terminal next-generation authorization changed the run-local continuation owner state but did not reactivate the coordinator-owned queue registry, leaving a valid gen06 continuation invisible to the formal exact-run scheduler.
