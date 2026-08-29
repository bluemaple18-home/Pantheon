# Pantheon Four-Lane Legacy Brief Compatibility Repair Result

Status: `RE_REVIEW_REQUESTED`

Base:

- `origin/main`: `73180233275840b0ab0e101f246e495ee6815fc9`
- `HEAD` at start: `73180233275840b0ab0e101f246e495ee6815fc9`

## Summary

Implemented a narrow legacy compatibility seam in `scripts/agy_multilingual_pipeline.py` for historical translation briefs that are otherwise canonical four-field briefs plus the exact extra key `lane`.

The global `validate_translation_brief()` contract remains canonical four-field strict. Legacy `lane` is accepted only by the run-dir loader after it is bound to a trusted registered translation state with:

- matching `run_id`
- matching canonical `run_dir`
- state `lane == "i18n-rewrite"`
- brief `lane == "i18n-rewrite"` and string typed
- matching `translation_identity_envelope(source_article_id, "i18n-rewrite")`

After that check, the in-memory brief is normalized back to canonical four fields and passed through the existing strict validator.

## Files Changed

- `scripts/agy_multilingual_pipeline.py`
- `tests/test_agy_multilingual_pipeline.py`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-FOUR-LANE-LEGACY-BRIEF-COMPATIBILITY-REPAIR-20260830.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_legacy_brief_compatibility_repair_20260830/RESULT.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_four_lane_legacy_brief_compatibility_repair_20260830/EVIDENCE.md`

No commit, push, tag, deploy, production retry, LaunchAgent change, promotion, coordinator edit, runner edit, publisher edit, manifest edit, or guard edit was performed.

## Verification

See `EVIDENCE.md` in this directory for command receipts.

Result:

- RED captured before source repair.
- Target repair tests pass.
- Full multilingual pipeline test file passes.
- Coordinator legacy translation/lane boundary slice passes.
- Python compile passes.
- `git diff --check` passes.
- Production-sensitive tracked paths `app`, `data`, `config`, and `.work` show no diff.

## Production Preservation Note

This isolated worker worktree contains no `.work/**/brief.json` production brief files, so exact production brief/registry/queue/content byte hashes were not available to compare here. The preservation evidence is therefore limited to no production-sensitive tracked path diff, no production mutation commands, and temp-root-only outbox tests with no provider/reviewer/publisher processing.
