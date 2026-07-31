# CHECKPOINT-B integration verification

## Status

```text
status: GO_FOR_RUNTIME_ALIGNMENT
verified_at: 2026-07-31T10:26:09+08:00
base: 49df25b7bcb060942e6de5ebf27f9636dd7b8738
base_tag: v0.3.185
```

## Integrated repair commits

- new: `8d7a64490`
- i18n-new／i18n-rewrite: `78329ebf5`
- rewrite: `be6f05381`
- dispatch／strict-review evidence: `c541b1214`
- observation evidence: `1de30d56f`

The pre-rebase state remains reachable at
`backup/four-lane-pre-rebase-20260731`.

## Verification

Executed after rebasing onto the fetched `origin/main`:

```text
.venv/bin/pytest -q \
  tests/test_agy_seo_copy_pipeline.py \
  tests/test_agy_gemini_outbox.py \
  tests/test_agy_gemini_v4_broker.py \
  tests/test_agy_gemini_coordinator.py \
  tests/test_agy_content_publisher.py \
  tests/test_agy_multilingual_pipeline.py
```

Result:

```text
595 passed, 1 warning in 86.93s
```

The warning is the existing invalid escape sequence warning in
`tests/test_agy_content_publisher.py`; no test failed.

Additional gates:

- `git diff --check origin/main..HEAD`: PASS
- fetched `origin/main`: still `49df25b7b...` after the prior Publisher process
  naturally completed
- queue／ledger freeze: six relevant LaunchAgents stopped before push／deploy
- runtime actor alignment: pending
- provider calls in this phase: `0`
- production canaries in this phase: `0`

## Acceptance mapping

- shared coordinator／schema／Publisher regression: PASS
- failure taxonomy and bounded retry regression: PASS
- candidate persistence／idempotency regression: PASS
- runtime SHA alignment: PENDING
- four real production outputs: PENDING

Therefore CHECKPOINT-B is accepted for runtime alignment only. This evidence
does not claim any production canary has completed.
