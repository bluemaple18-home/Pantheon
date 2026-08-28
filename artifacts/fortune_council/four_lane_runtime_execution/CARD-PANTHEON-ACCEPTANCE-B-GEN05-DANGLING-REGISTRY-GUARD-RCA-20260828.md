---
schema_version: 1
title: Pantheon Acceptance B gen05 dangling registry guard RCA
date: 2026-08-28
owner: codex-rca-worker
status: complete
handoff: HANDOFF-PANTHEON-ACCEPTANCE-B-GEN05-DANGLING-REGISTRY-GUARD-20260828.md
root_question: >-
  如何讓已具合法 current identity_envelope 與 matching registry lane 的 legacy
  translate_existing run，在 brief 缺少 lane 時仍可由正式 coordinator exact-run
  安全續跑，而不放寬 identity、建立 gen06、重叫 planning provider 或手改 production state？
---

# RCA Scope

## Allowed files

- `scripts/agy_gemini_coordinator.py` read-only during RCA.
- `tests/test_agy_gemini_coordinator.py` for test-only RED / fail-closed fixture.
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-ACCEPTANCE-B-GEN05-DANGLING-REGISTRY-GUARD-RCA-20260828.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_dangling_registry_guard_rca_20260828/`

## Forbidden

- No production registry, brief, queue, continuation, publisher, promotion, tag, push, commit, merge, deploy, resume, planning provider, gen06, or publication mutation.
- No production code Repair until four RCA evidence items close.
- No modification or deletion of existing untracked artifacts.

## Required Evidence

1. Current production-shaped provider=0 RED:
   legacy `translate_existing`, missing brief `lane`, valid current `identity_envelope`, matching state `lane=i18n-new`, exact-run `cycle_once`, blocked before tick/process.
2. Historical good behavior:
   run the same fixture against `ef934239c3^` / `75466a1bab5c0cd278ccbe44730bb9b058d79244`; do not infer solely from diff.
3. Formation:
   prove `ef934239c3` formed the dangling behavior by introducing identity-envelope active guard validation while the helper still raised before the `expected_lane` fallback. The handoff `e720f2ab41` formation claim is corrected: `e720f2ab41` only removed an already-dead fallback surface.
4. Durable invariant:
   when current envelope validates and state lane exactly matches it, missing legacy brief lane must not invalidate current identity; state lane missing, invalid, mismatched, or explicit brief lane mismatch must fail closed.

## Exit Gate

- RED-capable command names the target symptom and shows tick/process/provider invocation stays zero on current HEAD.
- Historical command proves whether `ef934239c3` actually passes the same fixture.
- Negative cases are covered.
- `git diff --check` passes.
- RCA may return `GO / RCA_CLOSED_REPAIR_NOT_STARTED` only after historical good, first failing mechanism, durable invariant, and RED-capable command all close.
