# Quota sharding decision

Date: 2026-07-25

Decision: `READY_FOR_REVIEW`

- Keep single-key configuration backward compatible.
- Allow a strict owner-only pool only through explicit
  `AGY_GEMINI_V4_CREDENTIAL_POOL_FILE`.
- Select one slot deterministically before a new operation forks.
- Bind non-secret pool identity to receipt and durable ledger.
- Never switch slots within an operation.
- Treat 429, timeout, transport failure and nonzero as terminal.
- Do not activate, publish or promote by this candidate.

The local three-slot pool is prepared and passed a no-network dry-run. Project
separation remains operator-provided information until control-plane evidence
is available.
