# Repair 1 preflight

- card: `CARD-PANTHEON-PRODUCTION-GEMINI-STRICT-ROUND-ROBIN-REPAIR-1-20260726`
- chain: `PANTHEON-PRODUCTION-GEMINI-STRICT-ROUND-ROBIN-20260726`
- source_candidate_sha: `611839c3aef8bb27755595dd6220816054cbd106`
- base_sha: `5ee733697727512e9c7bddb0572eedff4dd691c1`
- locked_head_match: `true`
- working_tree_clean_before_first_edit: `true`
- index_lock_present: `false`
- worktree_registered: `true`
- required_local_only_interpreter_executable: `true`
- capability_command: `worktree_capability_preflight.sh --check --root <repo-root>`
- capability_exit: `0`
- capability_python_tests: `needs_prepare`
- capability_node_tests: `needs_prepare`
- capability_codegraph: `degraded:fallback_rg`
- forbidden_prepare_or_download_used: `false`
- result: `PASS`

本 evidence 所在的唯一 commit 即 repaired candidate；其精確 full SHA 由
commit 後的 delivery receipt 提供，並可用 `git rev-parse HEAD` 驗證。
