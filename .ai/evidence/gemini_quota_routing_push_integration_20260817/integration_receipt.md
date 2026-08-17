# Gemini quota routing push / integration receipt

- card_id: `CARD-PANTHEON-GEMINI-QUOTA-ROUTING-PUSH-INTEGRATION-20260817`
- dispatch_key: `v1:d37e80e123e7cc7700150f371f7cd9503996bb8aa346eed0113c47e4500cb233`
- activation_token: `act-v1:94a2c5aeeb1e969f5e671bc0293befdb6024a7226e4fce88f5be5468809a8128`
- formal_thread_id: `01a00e40-6d18-77a2-b288-99016ccec373`
- worktree: `<repo-root>` detached HEAD worktree
- origin: `git@github.com:bluemaple18-home/Pantheon.git`
- base_sha: `2d8d8cb27e872f21c445d863bd7e15dbd1c0a7f7`
- verified_code_candidate_sha: `5996989fe81debed844737fe8d274f6edf434546`
- remote_feature_ref: `refs/heads/codex/gemini-model-quota-fallback-20260817`
- remote_feature_ref_sha_before_evidence_commit: `5996989fe81debed844737fe8d274f6edf434546`
- origin_main_drift: `0`
- force_push: `0`
- direct_main_push: `0`
- tag_push: `0`
- production_activation: `0`
- production_canary: `0`
- provider_call: `0`
- publish: `0`
- transaction: `0`
- deploy: `0`

## Changed paths

- `.ai/codex_task_gemini_model_quota_fallback_20260817.md`
- `.ai/codex_task_gemini_quota_routing_push_integration_20260817.md`
- `.ai/handoff_20260817_gemini_quota_routing_ready_for_integration.md`
- `scripts/agy_gemini_allocator.py`
- `scripts/agy_gemini_outbox.py`
- `scripts/agy_gemini_runner.py`
- `scripts/agy_seo_copy_pipeline.py`
- `scripts/install_agy_gemini_coordinator_launchd.sh`
- `tests/test_agy_gemini_allocator.py`
- `tests/test_agy_gemini_coordinator.py`
- `tests/test_agy_gemini_outbox.py`
- `tests/test_agy_seo_copy_pipeline.py`

## Verification

- `git fetch origin --prune`: PASS
- `git push origin codex/gemini-model-quota-fallback-20260817:codex/gemini-model-quota-fallback-20260817`: PASS after local `.venv` gate setup; pre-push release record gate PASS
- `git ls-remote origin refs/heads/codex/gemini-model-quota-fallback-20260817`: PASS, exact verified code candidate SHA before this evidence commit
- `bash -n scripts/install_agy_gemini_coordinator_launchd.sh`: PASS
- `git diff --check origin/main...HEAD`: PASS
- `.venv/bin/python -m pytest tests/test_agy_gemini_allocator.py tests/test_agy_gemini_outbox.py tests/test_agy_seo_copy_pipeline.py`: PASS, `312 passed`
- `.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py::test_launchd_template_runs_coordinator_and_installer_is_valid_shell tests/test_agy_gemini_coordinator.py::test_installer_injects_one_shared_allocator_contract_into_coordinator_and_all_lanes`: PASS, `3 passed`

## Full coordinator residual

Full `tests/test_agy_gemini_coordinator.py` was also run as part of the four-file command and returned `455 passed, 41 failed`.
Observed failures are outside the Gemini quota-routing path:

- Existing APF fixture baseline: `ASTRO-SCENARIO-BIG-THREE` missing from matrix backlog.
- APF-004 activation / rollback receipt expectations returning `ACTIVATION_REJECTED` or `aggregate_preflight` where older tests expect rollback or previous-barrier phases.

No code change was made for those residual failures because they are outside this card's Gemini quota-routing integration scope.

## Final state

- Integration candidate is the feature branch HEAD because latest `origin/main` did not drift from the card base and remains an ancestor of the candidate.
- Final delivery SHA is reported in the task handoff after this receipt commit is created and pushed.
