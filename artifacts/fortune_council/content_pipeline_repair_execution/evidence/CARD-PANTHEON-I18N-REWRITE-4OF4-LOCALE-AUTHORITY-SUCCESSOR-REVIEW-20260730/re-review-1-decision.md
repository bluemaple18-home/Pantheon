# Repair-1 re-review decision

## Verdict

`RE_REVIEW_GO`

## Finding disposition

### `LAS-REV-001` — CLOSED

At `scripts/agy_multilingual_pipeline.py:589`, the Repair replaces extracting
tokenization with an anchored whole-value grammar. The original four
punctuation/junk/separator triggers now reject at both the direct helper and
ja/ko x five semantic-field hydration boundary.

Fresh evidence: `44 passed, 128 deselected`.

### `LAS-REV-002` — CLOSED

At `scripts/agy_multilingual_pipeline.py:596`, alphabetic standalone authority
is restricted to the explicitly contracted `OpenAI` and `API` literals.
Generic capitalization and short-uppercase shape no longer establish
authority; `Strategy`, `SOURCE`, and `Zorple` reject across ja/ko x five
semantic fields.

Fresh evidence: `30 passed, 142 deselected`.

## Spec axis

`PASS`

- Whole-value grammar consumes the entire ASCII-only value.
- Standalone alphabetic authority no longer depends only on capitalization.
- Natural Japanese/Korean, `実践方法`, localized text containing
  `OpenAI`／`API`／`GPT-5`／`2026`, standalone contracted literals,
  `OpenAI GPT-5 2026`, and en behavior remain accepted as required.

## Standards axis

`PASS`

No Repair-direct P0/P1 correctness, regression, security, or test gap was
reproduced. Complete independent probes, direct tests, existing Review probes,
the seven-file affected suite, compile, debug scan, allowlist, and diff checks
all passed fresh.

## Residual risks

- The alphabetic literal authority set is intentionally narrow. A new
  unlisted brand or acronym fails closed until a future explicit requirement
  adds it.
- The affected suite retains one pre-existing invalid escape sequence
  DeprecationWarning.
- This re-review only adjudicates the two original findings and Repair-direct
  P0/P1 regressions; it does not certify provider output or production state.

## Limits

No provider call, production `.work` access, merge, push, deploy, publish, code
repair, replacement, other Review, or agent creation was performed.
