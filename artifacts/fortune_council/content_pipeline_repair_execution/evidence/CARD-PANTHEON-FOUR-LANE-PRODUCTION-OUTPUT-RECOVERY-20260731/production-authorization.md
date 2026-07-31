# Production authorization receipt

## Authorization

- received_at: `2026-07-31T10:26:09+08:00`
- status: `AUTHORIZED`
- authorized_by: repository owner in the active Codex thread
- scope:
  - rebase the verified repair commits onto current `origin/main`
  - push the verified repair baseline to `origin/main`
  - align the production Publisher／Gemini actor runtime SHA
  - execute one controlled real end-to-end production canary for each of
    `new`, `rewrite`, `i18n-new`, and `i18n-rewrite`
  - call the configured Gemini provider and publish the resulting canary when
    all existing gates pass

## Boundaries

- Execute one lane and one canary at a time.
- Do not reset or delete queue、ledger、candidate、archive or existing production
  artifacts.
- Do not loosen schema、quality、reviewer、retry or release gates.
- Stop the affected lane on an unresolved blocker; do not substitute fixtures、
  `idle`、service health or exit code for production output.
- Evidence must redact credentials、tokens and raw provider output.

## Pre-mutation receipt

- source base: `origin/main` at `49df25b7bcb060942e6de5ebf27f9636dd7b8738`
  (`v0.3.185`)
- verified repair commits after rebase:
  - `8d7a64490` — new contract repair
  - `78329ebf5` — multilingual contract repair
  - `be6f05381` — rewrite scheduler repair
  - `c541b1214` — dispatch／review evidence
- accepted observation evidence: `1de30d56f`
- regression result: `595 passed, 1 warning in 86.93s`
- whitespace gate: `git diff --check origin/main..HEAD` passed
- production services were allowed to finish their current Publisher process,
  then all six relevant LaunchAgents were stopped before synchronization.
