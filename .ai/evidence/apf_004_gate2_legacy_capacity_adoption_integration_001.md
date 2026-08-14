# APF-004-GATE2-LEGACY-CAPACITY-ADOPTION-INTEGRATION-001 evidence

## Verdict

- status: `INTEGRATION_READY`
- base: `e83ca791d0b86287e8e3a33c29f12f9cb2b7c6d0`
- approved_repair_1: `f614bea8f22663bd40dcee0f5e921d788d679a4e`
- approved_repair_2: `b7a7470834ecab4dfc9d998955781e636fa5ce7d`
- mutation_executed: `false`
- push_executed: `false`
- live_access_executed: `false`

## Integration method and equivalence

The clean local integration branch was created from the exact base. Both
approved commits were applied in order with `git cherry-pick --no-commit` and
without conflicts. The six approved repair files are content-equivalent to the
repair tip; `git diff --exit-code <repair-tip> -- <six-approved-files>` was
empty.

The approved repair chain is linear:

```text
e83ca791d0b86287e8e3a33c29f12f9cb2b7c6d0
  -> f614bea8f22663bd40dcee0f5e921d788d679a4e
  -> b7a7470834ecab4dfc9d998955781e636fa5ce7d
```

## Changed files

```text
.ai/codex_task_apf_004_gate2_legacy_capacity_adoption_repair_20260814.md
.ai/codex_task_apf_004_gate2_legacy_capacity_adoption_p1_repair_20260814.md
.ai/evidence/apf_004_gate2_legacy_capacity_adoption_repair_001.md
.ai/evidence/apf_004_gate2_legacy_capacity_adoption_p1_repair_001.md
scripts/install_agy_gemini_coordinator_launchd.sh
tests/test_agy_gemini_coordinator.py
.ai/codex_task_apf_004_gate2_legacy_capacity_adoption_integration_20260814.md
.ai/evidence/apf_004_gate2_legacy_capacity_adoption_integration_001.md
```

No file outside the integration allowlist changed.

## Behavior review

The repair adds a narrowly gated adoption path for activation-only when the
only prior-loaded service is the exact legacy capacity guard and no valid prior
barrier exists. Adoption requires a unique strict absolute loaded path, exact
canonical target equality, regular non-symlink files, current-user ownership,
mode `0600`, and byte-identical backup/target plists. Forged prefixes,
duplicates, relative/noncanonical paths, symlink aliases/targets, running
state, multiple loaded labels, business plists, and invalid snapshots fail
closed before live replacement.

Normal authority remains isolated because adoption requires
`ACTIVATION_ONLY=1`. The source after `replace_live_plists` and all child
execution behavior remain unchanged. The explicit normal-isolation and
activation-only zero-child-I/O tests passed.

No blocking correctness, regression, security, or test-gap finding was found
within the approved diff.

## Test evidence

```text
reviewer exact forged+duplicate: 2 passed in 6.07s
full invalid-state zero-write matrix: 13 passed in 35.64s
targeted adoption/regression: 23 passed, 138 deselected in 63.91s
affected coordinator: 48 passed, 113 deselected in 104.43s
runtime manifest: 42 passed in 2.22s
positive adoption + normal isolation + activation-only zero child I/O: 3 passed in 9.37s
```

The 13-case invalid-state matrix includes forged prefix, duplicate,
noncanonical, symlink alias, and symlink target cases. The targeted set includes
positive adoption, rollback receipts, prior legacy rejection, normal success
and rollback, normal authority isolation, and activation-only child-I/O zero.

## Static gates

```text
bash -n scripts/install_agy_gemini_coordinator_launchd.sh: PASS
bash -n scripts/install_agy_content_publisher_launchd.sh: PASS
bash -n scripts/install_pantheon_content_capacity_guard_launchd.sh: PASS
approved content equivalence: PASS
allowlist: PASS
DBG scan: PASS
secret scan: PASS
cross-machine absolute-path scan: PASS
binary/generated-artifact scan: PASS
git diff --check: PASS
```

The promotion commit is local-only. No push, deploy, production filesystem,
launchctl, external model, content, publish, transaction, tag, or schedule
operation was executed.
