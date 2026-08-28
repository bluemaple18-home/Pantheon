---
schema_version: 1
title: Pantheon Acceptance B gen06 terminal continuation and capacity RCA result
date: 2026-08-28
status: COMPLETE
mode: RCA_ONLY
target_run: auto-i18n-ja-1414b75a404721e95e74
target_generation: 6
source_commit: 99507c67e27d9e6f3af4e33c3ab0727682ed82bd
primary_verdict: FORMAL_MISSING_SEAM
secondary_verdict: SWAP_TELEMETRY_BOUNDARY_UNAVAILABLE
data_only: false
bounded_repair_allowed: true
---

# 結論

本 RCA 判定有兩個獨立 NO-GO：

1. Primary：`FORMAL_MISSING_SEAM`。目前正式 continuation API 只支援
   active continuation 與 gen04 partial planning terminalization 的
   authority transition；不支援從 `status=complete` 且 Reviewer `REJECT`
   的 terminal run 建立下一代 gen06。
2. Secondary：`SWAP_TELEMETRY_BOUNDARY_UNAVAILABLE`。final Rule24 的 swap null
   不是容量耗盡證據，但 repeated read-only measurement 連續 5 次同樣失敗，
   因此也不是單次 transient；依 Rule24 必須 fail-closed。

這不是 DATA_ONLY。不能靠手改 state、刪改 root candidate/review 或直接建立
`generations/06` 來恢復。需要唯一 bounded Repair：新增正式、受 authority
receipt 約束的 terminal-rejected next-generation continuation seam；另對 swap
telemetry 做正式 host-boundary 修補或 operator contract clarification。

# Evidence artifacts

- `terminal-rejected-gen06-reproduction.json`
- `terminal_rejected_gen06_harness.py`
- `swap-telemetry-repeated-readonly.json`
- prior production attempt:
  `pantheon_acceptance_b_gen06_production_attempt_995_20260828/RESULT-PANTHEON-ACCEPTANCE-B-GEN06-PRODUCTION-ATTEMPT-995-20260828.md`

# 四項證據

## 1. Last successful comparable continuation from rejected terminal state

沒有找到「terminal complete + Reviewer REJECT → explicit next generation」的
成功先例、正式函式或 CLI。

最近可比成功 continuation 是 rejected deferred lineage：

- test：
  `test_deferred_lineage_continuation_is_incremental_immutable_and_replayable`
- source seam：
  `continue_writer_reviewer(...)`
- state type：
  active continuation created from legacy attempts/root rejected review
- result：
  creates `generations/04`, updates active continuation state, then reaches
  Reviewer APPROVE。

但它不是 terminal complete/rejected 的 next-generation seam；它依賴
`state.status == "active"`。目前 live run 是 `status="complete"`，
`completed_generations=[5]`，`next_generation=6`，Reviewer `REJECT`。

## 2. First failing commit / mechanism

Commit history：

- terminal replay boundary introduced by
  `f0b70b4bba feat: add native locale planning continuation`
- partial planning authority transition introduced by
  `662942386c Fix gen04 semantic budget accounting`
- current repair/promotion target：
  `99507c67e2 fix: tighten JA boundary field coverage`
- swap fallback introduced by
  `a6b2334a2b fix capacity swap telemetry fallback`

First failing mechanism for gen06 is not the 995 content repair itself. It is
the existing terminal replay boundary:

```text
continue_writer_reviewer(...)
  → _load_or_create_continuation_state(...)
  → if state["status"] == "complete": return root_candidate, root_review
```

Because of that early return, formal API cannot consume
`next_generation=6` once state is terminal complete, even if the terminal review
is `REJECT` and no publish happened.

## 3. Durable invariant / authoritative owner

Generation authority invariant：

- `continuation/state.json` is the durable owner of:
  - `status`
  - `started_after_generation`
  - `semantic_budget`
  - `next_generation`
  - `completed_generations`
  - `abandoned_generations`
  - terminal candidate/review hashes
- `continuation/generation-lifecycle.json` and
  `continuation/authority-transition-XX.json` are authority receipts for
  explicit lifecycle transitions.
- Generation dirs under `generations/NN` must match state contiguity.

Authoritative code owner：

- `scripts/agy_multilingual_pipeline.py`
  - `continue_writer_reviewer`
  - `_load_or_create_continuation_state`
  - `_consume_partial_generation_terminalization`
  - `_authority_transition_path`
  - `_run_locale_generation`
- `scripts/agy_gemini_coordinator.py`
  - selects exact run and calls multilingual continuation; no separate terminal
    rejected generation creator was found.

Existing gen04 seam：

- `generations/04/partial-generation-decision.json`
- `continuation/authority-transition-04.json`
- action：`advance_after_terminalized_partial`
- only legal for PLANNING partial-generation terminalization.

The string `explicit_next_generation_after_authority_update` exists only as an
allowed next-action value in the partial generation decision payload; no native
function/CLI implementing that action was found.

## 4. RED-capable test / harness

Command：

```text
.venv/bin/python artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_terminal_continuation_and_capacity_rca_20260828/terminal_rejected_gen06_harness.py
```

Result：

- status：`REPRODUCED_NO_FORMAL_GEN06_SEAM`
- red_capable：true
- provider_called：false
- gen06_exists_after：false
- file_list_changed：false
- returned existing root review verdict：`REJECT`

This harness copies the live run to `/private/tmp`, calls the formal
`continue_writer_reviewer(...)` seam with a fail-if-called client, and proves
that complete+REJECT+next_generation=6 cannot create gen06 under current formal
API.

# Capacity RCA

## Earlier PASS

In the 995 production attempt:

- pre-promotion Rule24:
  - `rule24-capacity-pre-995.json`
  - status `PASS`
  - swap_available true
  - swap value around `7,498,429,890`
- post-apply Rule24:
  - `rule24-capacity-after-apply-995.json`
  - status `PASS`
  - swap_available true
  - swap value around `7,498,429,890`

## Final NO-GO

Final stop Rule24:

- `rule24-capacity-final-stop-995.json`
- status `NO-GO`
- swap_available false
- swap_before / swap_after null

Repeated read-only measurement:

- artifact：`swap-telemetry-repeated-readonly.json`
- 5/5 samples:
  - primary command `sysctl -n vm.swapusage` failed
  - native fallback `_local_swap_used_bytes()` failed
  - combined error:
    `swap_sources_failed:command:1;fallback:sysctlbyname_failed:1`

Verdict：

- Not storage exhaustion: disk free remained around 37.6GB and Rule24 write
  growth was bounded.
- Not proven one-shot transient: repeated samples failed identically.
- Current issue is telemetry boundary unavailable from this execution context.
- Code behavior is intentionally fail-closed and already tested:
  `test_swap_telemetry_is_no_go_when_primary_and_fallback_fail`。

# why_not_less

Less would mean:

- hand-editing `continuation/state.json` from complete to active;
- creating `generations/06` by filesystem write without authority receipt;
- publishing a gen05 rejected candidate;
- ignoring final Rule24 swap telemetry unknown.

All violate production safety and lifecycle invariants.

# why_not_more

More is unnecessary because:

- actor promotion worked and is not implicated.
- queue/registry identity was preserved.
- services stayed stopped.
- gen04 partial transition seam works for its original scope.
- capacity evidence points to telemetry boundary, not unbounded disk growth.

No new registry/FSM/database, broad continuation rewrite, or replacement of
Rule24 is justified.

# do_not_absorb

Do not absorb:

- a second generation lifecycle ledger;
- manual state surgery;
- generic “rerun any rejected article” command;
- bypass of Reviewer rejection;
- relaxed Rule24 that treats unknown swap as PASS;
- browser/publish acceptance without public URL;
- gen07 or multiple retry loop.

# Bounded Repair frontier

One bounded Repair may proceed with two narrow surfaces:

1. Terminal rejected continuation seam:
   - Add a formal, explicit, idempotent next-generation authority transition for
     terminal complete + Reviewer REJECT + no publish + `next_generation=N`.
   - Must verify root candidate/review hashes, completed/abandoned generation
     contiguity, no existing `generations/N`, no publish URL, and exact run
     identity.
   - Must write an authority-transition receipt before creating generation N.
   - Must call existing `_run_locale_generation(...)` once and preserve prior
     generations/attempts immutable.
   - Must expose a formal CLI or coordinator command; no manual state edits.

2. Swap telemetry boundary:
   - Either provide a formal host-side measurement entrypoint that has permission
     to read `vm.swapusage`, or update Rule24 contract to distinguish
     sandbox-unavailable telemetry from host production telemetry without
     treating unknown as PASS.
   - Must keep fail-closed production behavior unless host-boundary evidence is
     present.

# Final status

RCA complete。`DATA_ONLY=false`。可進唯一 bounded Repair；不可直接 retry
production 或手改 state。
