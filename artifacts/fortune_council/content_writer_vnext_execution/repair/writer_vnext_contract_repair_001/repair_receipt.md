# Writer vNext Contract Repair-1 receipt

Status: `REPAIR_READY_FOR_REREVIEW`

## Scope

- Finding: `WVN-REVIEW-001 P1`
- Source change: `scripts/agy_editorial_contracts.py`
- Regression: `tests/test_agy_editorial_contracts.py`
- Evidence: this directory only

## CodeGraph context

CodeGraph index was current. A task-semantic query did not return the editorial-contract validation symbol, so the repair used the permitted bounded fallback: `scripts/agy_editorial_contracts.py` and `tests/test_agy_editorial_contracts.py`.

## RED

Before the repair, the new `True`/`False` regression failed because a boolean sequence was accepted and validation instead reached `selected_stage_artifact_missing`. Full output: `red.txt`.

## GREEN

The selected-stage sequence check now requires `type(value) is int`, rejecting Python booleans while preserving normal integer uniqueness and ordering. Full summary: `green.md`.
