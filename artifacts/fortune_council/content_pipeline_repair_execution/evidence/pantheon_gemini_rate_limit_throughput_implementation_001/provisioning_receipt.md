# Provisioning receipt

status: `PASS`

Local-only values were reported in the formal thread before code edit. Persisted paths are
redacted here so the evidence artifact remains portable:

- thread_id: `019fa8f2-814d-75d2-9332-6a3d740aa595`
- title: `CARD-PANTHEON-GEMINI-RATE-LIMIT-THROUGHPUT-IMPLEMENTATION-001`
- sidebar/list status: `active`
- cwd/worktree: `<repo-root>`
- main checkout differs from cwd: `true`
- HEAD: `e21d9f7f11ef0fbfd78224afb5027b57c6b07f61`
- branch: `detached`
- initial clean status: `true`
- unrelated_dirty_paths: `[]`
- gitdir: `<git-common-dir>/worktrees/Pantheon4`
- common gitdir: `<git-common-dir>`
- git metadata writable: `true`
- index.lock: `absent`
- card contract: prompt complete; physical card created at the allowlisted path

Capability preflight:

- command: `worktree_capability_preflight.sh --check --root <repo-root>`
- worktree_registered: `true`
- initial python_tests: `needs_prepare`
- initial node_tests: `needs_prepare`
- codegraph: `degraded:fallback_rg`
- isolated prepare: `worktree_capability_preflight.sh --prepare --require-python-tests --root <repo-root>`
- prepared python_tests: `ready`
- prepared node_tests: `ready`
- optional CodeGraph was not initialized; source inspection uses `rg` and bounded reads.

Provisioning conclusion:

- Formal visible thread, independent clean worktree, exact source SHA, Git metadata,
  index lock, card contract and test capability gates passed before the first code edit.
- No production queue, credential, provider, launchd state, deployment or external model was accessed.
