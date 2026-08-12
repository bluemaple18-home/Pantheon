# Writer vNext Integration-003 Review 001

## Verdict

`REVIEW_NO_GO`

Candidate: `1da55d6fc6b233e008ffff5959f54801a8b927eb`

Parent: `cbed615c9c16a03b4d3ccfcf816d9901feea0ed9`

Review source: `bb0d6bc2752f157568339c590e9ef17f2d082e0e`

## Findings

### WVNI3-REVIEW-001 | P1 | Manifest opt-in boundary accepts missing or wrong orchestration mode

Axis: Spec and Standards

Category: correctness / fail-closed contract

Location: `scripts/agy_editorial_contracts.py:130`

Trigger: Any caller validates an `EditorialManifestV1` that has valid hashes but omits `orchestration_mode`, uses a wrong mode, or carries an extra free-state field.

Evidence:

- Architecture requires explicit vNext opt-in: `docs/pantheon_writer_vnext_orchestration_architecture.md:178` to `187` defines `orchestration_mode: writer_vnext_opt_in_v1` and says mixed mode without a valid manifest is `WVO-FC-SCHEMA_VERSION`.
- Architecture invariant requires the same boundary: `architecture-invariants.json` defines `WVO-INV-011` as explicit `EditorialManifestV1` mode and no shadow A/B.
- Implementation required fields omit `orchestration_mode`, and the validator uses subset acceptance instead of exact top-level schema: `scripts/agy_editorial_contracts.py:135` to `137`.
- The test helper creates a manifest without `orchestration_mode` and expects it to be valid: `tests/test_agy_editorial_contracts.py:36` to `53`.
- Reproducer output shows `missing_orchestration_mode`, `wrong_orchestration_mode` and `extra_free_state` all return `{"blocking": false, "findings": [], "valid": true}`.

Risk:

This breaks the explicit vNext opt-in boundary and schema-drift fail-closed requirement. A partial or wrongly-modeled sidecar can be accepted as a valid vNext manifest, so downstream coordinator or Publisher sidecar checks would not be able to distinguish a declared vNext run from stale, shadow, or free-state metadata. That is a core contract violation, not only a test gap.

Recommended repair boundary:

- Add `orchestration_mode` to the strict top-level manifest schema.
- Require `manifest["orchestration_mode"] == "writer_vnext_opt_in_v1"`.
- Reject extra top-level fields, or explicitly version and document any optional fields before accepting them.
- Add public negative tests for missing mode, wrong mode and extra/free-state fields.

Validation gap:

The required 10 test groups pass, but they do not exercise the explicit opt-in invariant. The candidate test suite currently encodes the fail-open behavior by treating a mode-less manifest as valid.

Confidence: high.

## Non-Blocking Evidence

The candidate composition checks passed:

- `HEAD=bb0d6bc2752f157568339c590e9ef17f2d082e0e`
- `HEAD^=1da55d6fc6b233e008ffff5959f54801a8b927eb`
- `1da55d6^=cbed615c9c16a03b4d3ccfcf816d9901feea0ed9`
- Diff inventory: 46 files, all added.
- Overlay identity: 37 paths.
- Overlay blob equality: 37/37 against `c7ad4881eabc47cbf43e5053f1ac79d7e70af546`.
- Integration-003 evidence paths: 9.
- Forbidden Publisher/runtime/coordinator/runner path diff: none.
- `git diff --check cbed615..1da55d6`: PASS.
- Required 10 test groups: 412 passed, 1 warning.

CodeGraph task-semantic query returned unrelated canonical verifier / prototype symbols, so source confirmation used bounded `rg`, `nl` and fixed Git objects.

Production remains `0/4`; production is still `NO-GO`.
