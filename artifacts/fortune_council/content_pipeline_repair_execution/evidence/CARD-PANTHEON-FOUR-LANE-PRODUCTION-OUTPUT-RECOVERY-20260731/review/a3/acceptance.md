# A3 mainline acceptance

- status: `GO`
- candidate: `d0fdb136d3142eb5d3687b2fa4ca8e2eea8a229c`
- superseded_candidate: `1a4e3c8e0349d18baff1a8bc783141e29b364a1b`
- parent: `de68b6b283493a3e9ca5f80286c682cb7846735e`
- integration: `921353cb6`
- risk_tier: `full`
- spec_axis: `GO`
- standards_axis: `GO`
- mainline_test: `128 passed in 16.45s`
- candidate_diff_check: `pass`
- resolved_finding: `A3-R1-MALFORMED-RETRY-SHAPE`
- repair_thread: `019fb5d8-0aa3-7921-8da9-464fdd0115a6`
- provider_called: `false`
- production_mutated: `false`

The primary exhausted-retry deadlock repair and malformed retry-state boundary
are both supported by deterministic tests. Exhausted candidates remain
terminal without replay or retry reset; malformed states produce an explicit
non-idle blocker without modifying retry bytes.

Production Publisher execution and canary remain outside this acceptance.
