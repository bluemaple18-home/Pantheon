# Pantheon Acceptance B: Gen06 Production Retry Acceptance

👉 [假設與目標確認] 目標是只對 production run `auto-i18n-ja-1414b75a404721e95e74` / generation `6` / current main `831c536043d85a6cafe813c08a4f06921f0dd0e2` 做一次 fail-closed 正式重試驗收；邊界是不新增 Repair、不碰 Gen07、不 publish/tag/push；驗收以現場 snapshot、Rule24/Rule25、正式 runner/coordinator receipt 與 final registry/artifact 證據為準。

## Scope

- Run: `auto-i18n-ja-1414b75a404721e95e74`
- Generation: `6`
- Current source authority: `831c536043d85a6cafe813c08a4f06921f0dd0e2`
- Expected current lane state: `i18n-new`
- Expected current reviewer job: `735ffd07d47e4b25d49f85f137d9dd238d8e9967`
- Evidence output directory: `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_production_retry_20260828/`

## Allowed Actions

- Create immutable before/after snapshots and hashes for the production registry, Gen06 root, lane archive/inbox/attempt, quarantine, and output artifacts.
- Run fresh storage capacity and production canary readiness gates before production mutation.
- Run the existing formal `i18n-new` runner exactly once for the expected reviewer job, if and only if all preflight gates pass.
- Run the existing formal coordinator entrypoint exactly once for the same run after the expected reviewer job is consumed.
- Write evidence receipts and a final `RESULT.md` only under the evidence output directory.

## Forbidden Actions

- No source/code/config modification.
- No manual registry JSON edit.
- No delete of production residue; quarantine must be receipt-first and produced only by the existing runtime.
- No retry/recovery replay, no second planning/provider job, no guessed job selection, no scanning other jobs to choose a replacement.
- No Gen07 creation.
- No candidate/reviewer boundary bypass.
- No publisher, tag, push, Cloudflare action, PR #22 work, or P1 architecture/CI work.

## Stop Conditions

- Any digest, request, prompt, schema, run, generation, or lane identity mismatch.
- More than one plausible current job or any unowned lane ambiguity.
- Prior quarantine does not belong to the same run/generation/job.
- Gen07 exists or is created.
- Candidate/reviewer artifacts already violate the expected boundary.
- Registry loses `last_job_id` again, points at another job, or returns to an unexplained failed state.
- Expected fresh outbox is not consumed, or runner/coordinator attempts to read stale inbox.
- Rule24 capacity or Rule25 readiness is not GO/READY for this exact source authority.

## Required Result

The result must state `GREEN`, `AMBER`, or `RED`; count provider/coordinator/publish mutations; record Gen07 status; identify the next legal edge; and include command receipts, before/after hashes, capacity/readiness receipts, and final production snapshots. Public publication is not complete unless a later authorized publisher step reaches HTTP 200 with visible body.
