# Gate C impact matrix

verdict: `IMPACT_MATRIX_ACCEPTED`

CodeGraph 結果僅為 frontend material identity，未提供相關 test seam；因此依卡片採 `CODEGRAPH_IRRELEVANT_FALLBACK_BOUNDED_RG`，且搜尋僅限 coordinator、publisher、multilingual tests 與其直接 scripts。current actor 僅採 Gate A1 的 `0f61545f8c6b561742b27792b8fef11ae8b1ccc5`。

| requirement_id | lane | evidence_layer | existing_receipt | dependency_intersection | evidence_disposition | execution_requirement | required_gate | reason_code |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TR-IMPACT-001 | v0.3.371/.372/.374/.375 | business outcome | baseline-result | 歷史 outcome；不重發 | CARRY_FORWARD | NOT_REQUIRED | Gate C | HISTORICAL_BUSINESS_OUTCOME_CARRY_FORWARD |
| TR-IMPACT-001 | seven-service | actor/manifest/generation/digest/token | Gate A1 final | current actor rebind；Phase C 僅測 consumer fail-closed | REBIND | REQUIRED | A1 → C | CURRENT_ACTOR_REBIND_REQUIRED |
| TR-IMPACT-003 | new/rewrite | routing/isolation/resume/rollback/capacity | baseline + frozen nodes | temporary roots only | REVALIDATE | REQUIRED | Gate C | ROUTING_IDENTITY_NEGATIVE_REQUIRED |
| TR-IMPACT-003 | i18n-new/i18n-rewrite | routing/locale/ledger | baseline + frozen nodes | temporary roots only | REVALIDATE | REQUIRED | Gate C | ROUTING_IDENTITY_NEGATIVE_REQUIRED |
| TR-NEG-001 | all four | worker/mode/lane/identity/manifest/generation | frozen manifest | pre-I/O fail-closed | REVALIDATE | REQUIRED | Gate C | PRE_IO_FAIL_CLOSED |
| TR-NEG-002 | publisher+i18n | selector/duplicate locale/ledger conflict | frozen manifest | temporary roots only | REVALIDATE | REQUIRED | Gate C | PRE_IO_FAIL_CLOSED |
| TR-NEG-003 | all four | capacity/rollback/resume/idempotency | frozen manifest | private campaign tmp_path only | REVALIDATE | REQUIRED | Gate C | OFFLINE_TEMP_ROOT_ONLY |
| TR-CARRY-001 | publisher/public | publication boundary | Gate A1 + authority snapshot | republish 禁止 | CARRY_FORWARD | NOT_REQUIRED | Gate C | REPUBLISH_NOT_REQUIRED |

先前 waived 狀態以 Gate A1 final 的 `GATE_A1_PASS` 與 `RE_REVIEW_GO` 分類為已解決；未將 waived 文案本身當 PASS 證據。
