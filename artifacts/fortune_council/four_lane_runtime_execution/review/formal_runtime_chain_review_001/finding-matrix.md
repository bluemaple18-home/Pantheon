# Finding matrix

| Axis | Status | Evidence / Finding |
|---|---|---|
| H-001 Publisher capability 為模擬成功 | CONFIRMED / P1 | `PANTHEON-FORMAL-RUNTIME-001`；五步全 PASS，但 production call recorder 為空。 |
| H-002 Full-suite unrelated 分類 | PARTIAL / P2 | `PANTHEON-FORMAL-RUNTIME-002`；base/candidate 都未進 actor production path，且候選確實修改 actor-recovery。 |
| FR-001 正式實作鏈 | FAIL | Publisher 後五步只走 preflight receipt。 |
| FR-002 七服務每輪身份一致 | PASS | 七 label source inspection + mismatch matrix。 |
| FR-003 7/7 barrier／rollback | PARTIAL | 7/7 barrier PASS；rollback mismatch dynamic evidence 缺口。 |
| SC-001 同一 correlation 正式鏈 | FAIL | `PANTHEON-FORMAL-RUNTIME-001`。 |
| SC-002 任一 identity mismatch 先於 I/O 拒絕 | PASS | targeted suite 七個 parameterized cases。 |
| SC-003 6/7、early、stale barrier 不放行 | PASS | targeted suite barrier/early-start cases。 |
| SC-004 rollback 實際 identity mismatch | PARTIAL / P2 | `PANTHEON-FORMAL-RUNTIME-003`。 |

唯一阻擋 finding：`PANTHEON-FORMAL-RUNTIME-001`。

唯一 verdict：`REVIEW_NO_GO`。
