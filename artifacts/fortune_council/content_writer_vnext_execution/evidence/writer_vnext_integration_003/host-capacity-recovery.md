# Writer vNext Integration 003 Host Capacity Recovery

## Historical Failure

- The initial full 10-group run recorded `410 passed, 2 failed, 1 warning in 160.70s` in `pytest-output.txt`.
- A clean-source targeted reproduction at `cbed615c9c16a03b4d3ccfcf816d9901feea0ed9` recorded the same two failures in `source-cbed-targeted-failures.txt`.
- Those two files retain the complete failure traces and results. Only pytest-generated trailing whitespace was removed so the candidate can satisfy `git diff --check`; no result text was changed.
- Pre-normalization SHA-256 values:
  - `pytest-output.txt`: `6203d35199e98db8d05d16a43e67b5020ea3a7bed89bd6e26649e0870ecde885`
  - `source-cbed-targeted-failures.txt`: `d97fcbb95c503a3cce62f8072eeedb6ce800df17efd1bd1433ee79c8241b75f0`
- Candidate SHA-256 values after whitespace-only normalization:
  - `pytest-output.txt`: `1c99f78d7ed284631af4eaf34bbe9bf02d3238c58b18a5eb3a95a5c2eeee750f`
  - `source-cbed-targeted-failures.txt`: `0420bd6b6e0afe3194dae09baa3b167d8cdc89ed295c9d207c25490acec55415`

## Corrected Classification

- Resolved blocker: `HOST_CAPACITY_FLOOR`.
- The earlier `RUNTIME_BASE_TEST_CONTRACT_DRIFT` interpretation is superseded.
- Mainline reported host free space recovery from approximately 16 GiB to approximately 28 GiB and a clean-source rerun of the two affected tests at the exact source SHA: `2 passed in 12.12s`.
- This worktree observed 26 GiB available immediately before the resumed full gate.

## Resumed Full Gate

- Command scope: all 10 pytest groups required by Integration-002/003.
- Result: `412 passed, 1 warning in 161.22s`.
- Exit code: `0`.
- Full output: `pytest-output-resume.txt`.
- SHA-256: `9999f3b42629bede3ea4ce2964b07ae479bedd102beb97be4cff4b67756f841e`.

The full required gate now passes without Runtime or Publisher changes.
