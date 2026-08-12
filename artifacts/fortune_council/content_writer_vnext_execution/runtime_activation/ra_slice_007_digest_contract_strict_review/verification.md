# RA007 Digest Contract Strict Successor Verification

## Commands

- `pwd`
- `git status --short`
- `git rev-parse HEAD`
- `git rev-parse def554580ced5af1399a1edfe8a9debc90a4b83b^`
- `git diff --name-status dd6dac202edef2bde3f060c09078295ed31691ba..def554580ced5af1399a1edfe8a9debc90a4b83b`
- `git diff --check dd6dac202edef2bde3f060c09078295ed31691ba..def554580ced5af1399a1edfe8a9debc90a4b83b`
- `python3 -m json.tool artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_007_capacity_preflight/resource-snapshot.json`
- bounded JSON recomputation script over committed `resource-snapshot.json`
- bounded inventory and cleanup JSON consistency script
- portable path token scan over `artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_007_capacity_preflight`

## Results

- Worktree started at candidate `def554580ced5af1399a1edfe8a9debc90a4b83b` and was clean.
- Candidate parent check passed: parent is `dd6dac202edef2bde3f060c09078295ed31691ba`.
- Allowlist passed: only `resource-snapshot.json` and `verification.txt` changed.
- `git diff --check` passed with no output.
- JSON parse passed.
- Digest contract check passed:
  - domain: `pantheon.writer_vnext.ra_slice_007.capacity_preflight.measurement_digest`
  - version: `1`
  - algorithm: `sha256`
  - serialization: UTF-8 JSON, sorted keys, separators `(',', ':')`, `ensure_ascii=false`, no whitespace
  - digest exclusions: `samples[].measurement_digest` and `digest_inputs[].expected_digest`
- Canonical projection check passed for both samples: each `digest_inputs[].canonical_projection` exactly matches `{domain, version, sample}` derived from committed sample fields.
- Digest recomputation passed:
  - sample 0 actual: `sha256:e7b2aa52c8070fc95a7f791d8941a4dee40bb53ab0cfd4b8582a307d84d8d79f`
  - sample 1 actual: `sha256:b7332c4dcc88b64b35634803450f9eb05513d1a955afb551792a35de33fda224`
- Original measurements did not regress against the parent for the listed sample fields.
- Interval check passed: `3` seconds.
- Arithmetic check passed:
  - formal reserve is `max(20 GiB, ceil(10% host total)) = 24510719591`
  - both reserve deficits are `0`
  - host free delta is `1085440`
  - Codex RSS delta is `-87883776`
  - swap delta is `0`
- Four runtime indicators remain non-empty in both samples.
- Capacity verdict remains `NO-GO`.
- Candidate evidence path audit passed with no matches.
- Inventory and cleanup plan regression checks passed.

## Verification Verdict

All delegated adversarial and regression checks passed.
