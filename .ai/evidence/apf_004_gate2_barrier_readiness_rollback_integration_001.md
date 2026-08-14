# APF-004 Gate 2 barrier readiness rollback integration evidence

- base：`a153219f919f965821dd7ee15d23a01f0469133f`
- candidate：`17191c54f06c28dcebfb613a1d4ff518f1257fe2`
- review：`REVIEW_GO`；無P0/P1
- integrated repair commit：`6cf82f474b`
- source blobs與candidate一致
- affected coordinator：`62 passed, 113 deselected in 131.86s`
- runtime manifest＋activation：`50 passed in 3.38s`
- 三installer `bash -n`：PASS
- drift／binary／`diff/show --check`：PASS
- production mutation／push／發文：false
- 結果：`INTEGRATION_PASS`
