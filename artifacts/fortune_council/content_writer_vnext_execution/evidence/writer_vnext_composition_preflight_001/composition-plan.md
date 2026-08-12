# Writer vNext Composition Plan

## Verdict

`BLOCKED / WVO-FC-COMPOSITION_LINEAGE`

The fixed objects are readable and the three pinned final evidence files report
`REVIEW_GO`. The Writer and Runtime candidate deltas have no exact-path overlap.
That is not sufficient to authorize composition: the activated source contains
the Writer lineage but not the Runtime Authority lineage. The reviewed-delta
three-way analysis uses the Runtime candidate's declared parent as base. It
finds one `changed in both` path: `scripts/agy_content_publisher.py`.

The other four Runtime candidate-delta paths are unambiguous: the two Runtime
artifacts are added in remote, and `scripts/pantheon_runtime_fs_authority.py`
plus `tests/test_pantheon_runtime_fs_authority.py` apply without conflict.

No resolution ownership, resolution allowlist, or reviewed resolution exists.
This preflight therefore does not authorize merge, cherry-pick, patching, or
implementation of `WVO-SLICE-001`.

## Pinned authority

| Lineage | Candidate | Final review evidence | Verdict |
| --- | --- | --- | --- |
| Orchestration | `4cd768e353e6e349d15f57c5366a3275f7eefb8c` | `writer_vnext_orchestration_architecture_review_001/findings.json` | `REVIEW_GO` |
| Writer contract | `671fdba9bf1b5655cc9182bbf375cadae3efb0b5` | `writer_vnext_contract_review_002/findings.json` | `REVIEW_GO` |
| Runtime Authority | `e6d93fba050eac7c22e1a34bf52d8ac4c707a1b3` | `runtime_authority_activation_review_003/findings.json` | `REVIEW_GO` |

The obsolete `writer_vnext_contract_review_001` and
`runtime_authority_activation_review_001` / `_002` evidence is recorded in the
manifest and must not be selected as composition authority.

## Required next-card contract

The eventual integration card must:

- use `bcd35b090dd37b118632d3b4153308964218f0c8` as the Runtime
  candidate-delta base when applying to the activated source;
- restrict the activated-source allowlist to the five Runtime candidate-delta
  paths; only `scripts/agy_content_publisher.py` requires resolution;
- name a single Publisher conflict owner and obtain independent review for that
  explicit resolution;
- run the contract, Publisher, runtime authority, activation, manifest,
  capability, coordinator, runner, and capacity regression suites listed in
  `composition-manifest.json`;
- keep deployment, publication, canary, service start, push, and production
  state outside scope;
- define rollback as abandoning the unmerged integration candidate. It must not
  rewrite an accepted artifact or publish a prior candidate.

No follow-up card is created by this preflight.
