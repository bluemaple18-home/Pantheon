# Writer vNext contract handoff

Status: `DELIVERED_CONTRACT_CANDIDATE`

`scripts/agy_editorial_contracts.py` adds a pure in-process validator for a versioned `ArticleBriefV2` and declarative `EditorialManifestV1`. Optional stages are selected by the manifest and have no fixed order. The validator returns stable, sorted finding codes and never creates queues, runtime state, approval, or publication actions.

Legacy compatibility calls the existing `scripts.agy_seo_copy_pipeline.validate_candidate` boundary instead of copying Publisher schema rules. The fixture validates an existing optimize candidate and checks its canonical hash.

Risk: this worktree does not contain a local `.venv` or CodeGraph index/runtime. Tests passed through the primary worktree's existing Python virtualenv while retaining this worktree as the pytest root. Integration with Publisher remains deliberately out of scope.
