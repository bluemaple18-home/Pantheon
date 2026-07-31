# A2 mainline acceptance

- status: `GO`
- candidate: `aac2d3bd180bb5b82dd41f98596a0cdc62d2866f`
- parent: `de68b6b283493a3e9ca5f80286c682cb7846735e`
- integration: `46322d1e4`
- risk_tier: `full`
- spec_axis: `GO`
- standards_axis: `GO`
- blocking_findings: `none`
- changed_files_allowlisted: `true`
- candidate_worktree_clean: `true`
- mainline_test: `309 passed in 69.97s`
- candidate_diff_check: `pass`
- provider_called: `false`
- production_mutated: `false`

Mainline inspected the runner, broker, normalization contract and deterministic
tests. The repair revalidates normalized data against the unchanged schema,
does not resend the provider request, and preserves fail-closed handling for
all other mismatches.

Production canary and real end-to-end output remain outside this acceptance.
