# Source Inventory

## CodeGraph

- `worktree_capability_preflight.sh --prepare --with-codegraph` returned `provisioning=ready`, `codegraph=ready`, `codegraph_indexed_sha=7af82c40439af642a9f91cb7a4c3b3146325c404`, `prepare_required=false`.
- `codegraph_status` after prepare: 553 files, 5502 nodes, 11140 edges, backend `native (better-sqlite3)`.
- Task-semantic query: `Writer vNext Runtime Activation capability chain: find production official entrypoints for create run select publish transaction tag push...`
- CodeGraph surfaced `scripts/pantheon_content_runtime_manifest.py`, `scripts/pantheon_runtime_activation.py`, `scripts/agy_gemini_allocator.py`; bounded source confirmation expanded to coordinator, runner and publisher files.

## Confirmed Source Files

| Path | Relevant evidence |
|---|---|
| `scripts/pantheon_content_runtime_manifest.py` | Runtime manifest create/validate/aggregate/barrier CLI, formal tick validation, readiness ack and activation barrier |
| `scripts/pantheon_runtime_activation.py` | Thin activation token publication and validation before queue/state I/O |
| `scripts/agy_gemini_coordinator.py` | `register`, `cycle`, `--new-matrix-sweep`, exact run selection, formal runtime tick before queue/state work |
| `scripts/agy_gemini_runner.py` | `process-once`, lane processing, formal runtime tick before queue/state I/O |
| `scripts/agy_content_publisher.py` | `formal_capability_preflight` for `select/publish/transaction/tag/push`; deployment preflight; isolated transaction worktree; commit/tag/push helper |
| `docs/pantheon_deployment_workflow.md` | Production publisher deployment contract and release push requirements |
| `docs/pantheon_article_publication_standard.md` | Publication policy v2 boundary and fail-closed apply/publish constraints |

## Source Conclusions

- Formal runtime identity and activation token boundaries exist.
- Coordinator/runner create and run entrypoints exist, but their proof surface is not yet normalized into the production canary seven-step capability receipt.
- Publisher has a bounded public dry-run/preflight entry for select, publish, transaction, tag and push.
- The current card did not execute production publisher, tag or push. Remote mutation remains unauthorized.
