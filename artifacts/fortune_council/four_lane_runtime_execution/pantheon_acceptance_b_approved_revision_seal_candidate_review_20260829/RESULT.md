# Approved Revision Seal Candidate Re-Review Result

## Verdict

`GO`

理由：前一輪 4 個 P1 與 1 個 P2 finding 已由同一 Repair candidate 收斂；本輪沒有發現新的 P0/P1，核心 acceptance 與指定驗證完成。

## Re-Review Evidence

- Base：`831c536043d85a6cafe813c08a4f06921f0dd0e2`
- Current scope diff：4 files
- Source budget：`scripts/agy_multilingual_pipeline.py +468/-0`，`scripts/agy_content_publisher.py +74/-20`，source insertions total `542 <= 550`，publisher insertions `74 <= 100`
- No registry/FSM/database/universal expansion：diff scan no matches
- Release transaction semantics：publisher still calls existing `_stage_commit_tag_push`; diff only adds approved-stage selection and optional `staging_receipt_sha256` ledger field
- CodeGraph：index ready，650 files / 8290 nodes；context still partially degraded for exact symbols, so final verdict relies on direct diff and tests

## Resolved Findings

### [RESOLVED] P1 formal identity fixture/contract mismatch

- Evidence：`tests/test_agy_multilingual_pipeline.py -k approved_edited_stage` now selects 20 tests and passes.
- Code：`scripts/agy_multilingual_pipeline.py:2799-2826` validates schema version, run id, reviewer role, lane, 40-hex job id, 64-hex request sha, result verdict/findings, review binding, and candidate sha binding.
- Test：`test_approved_edited_stage_rejects_formal_job_identity_tamper` covers missing run id, wrong lane, and request/job mismatch.

### [RESOLVED] P1 crash-before-current idempotent recovery

- Evidence：`test_approved_edited_stage_recovers_verified_operation_before_current` passes.
- Code：`scripts/agy_multilingual_pipeline.py:3058-3061` now loads a verified operation record with `require_current=False`, atomically writes `current.json`, and returns `recovered_current_pointer=True`.

### [RESOLVED] P1 publisher writes into sealed operation_dir

- Evidence：publisher diff no longer writes `operation_dir / "approval.json"`; `test_approved_stage_publish_binds_receipt_and_preserves_terminal_audit` snapshots stage bytes and verifies unchanged after publish path.
- Code：`scripts/agy_content_publisher.py:4220-4244` builds approval in memory and calls `apply_approved_translations`; only ledger receives `staging_receipt_sha256`.

### [RESOLVED] P1 missing publisher acceptance coverage

- Evidence：`tests/test_agy_content_publisher.py -k approved_stage...` selects 7 tests and passes.
- Coverage：valid seal selection, missing/tampered stage rejection, deferred/published lifecycle rejection, dry-run zero runtime mutation, receipt binding, terminal audit preservation.

### [RESOLVED] P2 path symlink/regular-file/descendant protections

- Evidence：`test_approved_edited_stage_rejects_symlinked_authority_path` and `test_approved_edited_stage_rollback_rejects_symlinked_operation_dir` pass.
- Code：`scripts/agy_multilingual_pipeline.py:2829-2861` centralizes approved stage path validation with strict descendant, non-symlink, regular-file/directory checks.

## Commands

- `.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py -k approved_edited_stage` → `20 passed`
- `.venv/bin/python -m pytest tests/test_agy_content_publisher.py -k "approved_stage or collect_ready_translation_runs_selects_valid_approved_stage or collect_ready_translation_runs_rejects_missing_or_tampered_stage or collect_ready_translation_runs_does_not_bypass_ledger_lifecycle"` → `7 passed`
- `.venv/bin/python artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_approved_edit_staging_rca_20260828/red_harness_missing_approved_edit_stage.py` → `GREEN`, return code `0`, production/public/queue/ledger/run-dir hashes unchanged, provider/coordinator/publish/tag/push all `0`
- `.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py::test_approved_edited_stage_recovers_verified_operation_before_current tests/test_agy_multilingual_pipeline.py::test_approved_edited_stage_rejects_formal_job_identity_tamper tests/test_agy_multilingual_pipeline.py::test_approved_edited_stage_rejects_symlinked_authority_path tests/test_agy_multilingual_pipeline.py::test_approved_edited_stage_rollback_rejects_symlinked_operation_dir` → `7 passed`
- `.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py tests/test_agy_content_publisher.py -k "approved_edited_stage or approved_stage"` → `23 passed`
- `.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py tests/test_agy_content_publisher.py -k "not exact_production_gen05_legacy_safety_hydrates_read_only"` → `407 passed, 1 deselected, 1 warning`
- `.venv/bin/python -m py_compile scripts/agy_multilingual_pipeline.py scripts/agy_content_publisher.py tests/test_agy_multilingual_pipeline.py tests/test_agy_content_publisher.py` → PASS
- `git diff --check -- scripts/agy_multilingual_pipeline.py scripts/agy_content_publisher.py tests/test_agy_multilingual_pipeline.py tests/test_agy_content_publisher.py` → PASS

## Remaining Risk

- One broader affected-suite assertion remains excluded as stale fixture policy: `test_exact_production_gen05_legacy_safety_hydrates_read_only` still expects Gen06 absence while mounted production fixture now includes terminal Gen06. This was not introduced by this Repair and is outside the approved revision seal acceptance.
- This review did not execute commit, push, tag, deploy, or production publish.

## Final Decision

`GO`
