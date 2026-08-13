# APF-004 create-run adapter verification receipt

- Entrypoint: `scripts.agy_gemini_coordinator:create_campaign_run_adapter`
- Signature: keyword-only `repo_root`, `workset`, `exact_tuples`, `run_root`, `queue_root`, `state_root`, `campaign_version`, `workset_sha256`, `confirmed_payload_digest`, `activation_authorization_digest`, `runtime_identity_digest`, `actor_identity`, `correlation_id`, `plan_only`, `max_runs=1`
- Exact IDs: see `exact-run-plan.json`
- Negative matrix: see `negative-matrix.json`
- Plan-only contract: targeted tests run `plan_only=True` twice and assert identical output plus zero file writes
- Apply contract: targeted tests run apply twice, delete one pending dependency receipt, rerun, and assert no duplicate run plus resume-only refill
- Not performed: external model, production runtime, publish, transaction, tag, push, deploy, schedule, production canary
