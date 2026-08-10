# Writer vNext Contract Independent Review

Verdict: `REVIEW_NO_GO`

## Findings

- [P1] stage sequence accepts JSON boolean and fails open - `scripts/agy_editorial_contracts.py:79`
  - Public input: `selected_stages=[{"stage_type":"content_plan_v1","sequence":true,...}]` with a valid `content_plan` artifact.
  - Expected: fail closed with `schema_version_unsupported`.
  - Actual: `{"blocking":false,"findings":[],"valid":true}`.
  - Why it matters: the task contract explicitly requires stage declaration ambiguity to fail closed. Python `bool` is an `int` subclass, so `isinstance(item.get("sequence"), int)` accepts JSON booleans.

## Passing Coverage

- `selected_stages=[]` passes without unselected artifacts.
- Reordered optional stages pass without fixed Research -> Outline -> Blind Reader -> Fact Checker order.
- Content plan selected with 0, 3, and 7 sections passes; FAQ, fixed word count, and fixed section count are not enforced.
- Claim types are closed to the five allowed types; `verifiable_fact` and high-risk claims without evidence block; non-fact claim types do not require citations.
- Blind read binds candidate and blind-input SHA; `thesis_match=false` blocks; confusing, low-information, and reader-question evidence does not block by itself.
- Missing core, unsupported manifest version, artifact hash mismatch, article identity mismatch, selected artifact missing, free action fields, duplicate stage ID, duplicate sequence, artifact mapping collision, and publication policy fail closed in the public reproducer.
- Legacy compatibility calls `scripts.agy_seo_copy_pipeline.validate_candidate`; legacy candidate hash tamper and schema invalidity fail closed; vNext validation did not mutate the legacy candidate object/hash.

## Source Inspection

- `scripts/agy_editorial_contracts.py` imports hashing/JSON utilities and the legacy `validate_candidate` boundary only.
- Limited source scan found no external client, queue, prompt, retry loop, publication path, Git mutation, launchctl, subprocess, network request, or runtime orchestration in `scripts/agy_editorial_contracts.py`.
- Candidate changed files are limited to `scripts/agy_editorial_contracts.py`, `tests/test_agy_editorial_contracts.py`, and review/evidence artifacts; no Publisher, transport, frontend, metadata, registry, or production files were changed by the candidate diff.

## Repair-1

Make the sequence type check exact in `_validate_selected`: use `type(item.get("sequence")) is int` rather than `isinstance(..., int)`. Add a regression test for `sequence=true` and `sequence=false`. Keep the repair bounded to `scripts/agy_editorial_contracts.py` and `tests/test_agy_editorial_contracts.py`.

Contract is still not merged, wired to orchestration, or authorized for production.
