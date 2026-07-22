# External tool gate

- Tool: local Antigravity `agy` CLI, observed version `1.1.5`.
- Intended future operation: one synthetic public JSON generation canary after independent review GO.
- Authorization: user explicitly requires Gemini CLI for the three content lines and told Codex to proceed.
- Data class: `PUBLIC_SANITIZED` only; no private repository paths, credentials or unpublished article content.
- Authentication boundary: reuse existing local CLI login/config through allowlisted `HOME`; never inject, read, copy or record a credential.
- Process boundary: exactly one target process, FD 0/1/2 only, closed argv schema, closed environment allowlist.
- Cost/state boundary: current card performs fake CLI tests only. The later real canary is one call, no retry/fallback and no publishing state change.
- Stop conditions: unknown model, forbidden data, missing executable, nonzero, timeout, invalid JSON/schema, replay ambiguity or receipt mismatch.
