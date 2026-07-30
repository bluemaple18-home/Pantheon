# Publisher hub fixture contract repair — candidate evidence

Status: `LOCAL_CANDIDATE_READY_FOR_INDEPENDENT_REVIEW`

## Scope and baseline

- User continuation instruction: integrate the current project first, then continue.
- Integrated baseline commit:
  `f7d6fab4c32a38da36a86ed96bb0cfc9af14f421`
- Candidate branch:
  `codex/pantheon-integrated-publisher-fixture-repair-20260730`
- Production Publisher, queue, ledger, retry state, push, tag, deployment, and live
  URLs were not touched.

The original card named `origin/main@0e9870764` as its base. The user subsequently
asked to integrate the current project before continuing, so this candidate is based
on the already accepted local i18n/runtime mainline descendant `f7d6fab4`.

## Root cause and repair

`_sync_web_test_release_fixture` owned two stable release inputs in
`tests/test_web.py`: the article cache token and `DAILY_PUBLIC_ARTICLE_PATHS`.
It also parsed and rewrote a separate runtime acceptance test by matching the old
fixed `data["records"]` assertion text. Commit `9a64bf0e4` changed that test to
runtime-derived `baseline` and `rewritten` assertions, making the source regex
fail closed with:

```text
test_web hub display fixture marker not found
```

The repair removes this cross-test source rewrite and its now-unused helpers.
The Publisher still updates the cache token and de-duplicated public paths.
The existing hub test continues to calculate and validate display order, category
balance, and rewrite behavior from runtime data.

## Changed files

- `scripts/agy_content_publisher.py`
- `tests/test_agy_content_publisher.py`
- this evidence file

`tests/test_web.py` was intentionally not changed or weakened.

## RED

Command:

```bash
<shared-python> -m pytest \
  tests/test_agy_content_publisher.py::test_sync_web_test_release_fixture_preserves_runtime_hub_assertions \
  -q
```

Result before the production change: `1 failed`; failure was
`PublishBlocked: test_web hub display fixture marker not found`.

## GREEN

- Focused fixture contract tests: `3 passed`
- `tests/test_agy_content_publisher.py`: `75 passed`
- `tests/test_web.py`: `72 passed`
- Combined Publisher and Web suites: `147 passed`
- Python compile check: passed
- `git diff --check`: passed

The full repository suite produced `784 passed, 2 failed`. Both failures assert
that the Node Ziwei provider is `iztro`; the clean baseline produces the same
two failures in this environment because the package is absent and the calculator
uses its documented `pantheon_ziwei` fallback. An offline `pnpm install` could not
provision the missing transitive package because its tarball was not cached.
These failures are baseline-equivalent and outside this candidate's changed paths.

## Local review gate

The strict review plan covered correctness, regression, test gaps,
maintainability, performance, and agent-instruction drift. The local multi-view
review found no P0/P1 issue or production safety regression in this diff.
This is not a substitute for the card's independent reviewer gate.

## Residual risk and next gate

- The candidate deliberately keeps the runtime hub assertions independent of the
  Publisher's source mutation contract.
- Transaction recovery paths remain covered by the full Publisher test module.
- The four exhausted production runs still require separately authorized,
  supported retry recovery after this candidate is independently reviewed and
  accepted.
