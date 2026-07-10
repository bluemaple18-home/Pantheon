# Requirements Matrix

任務ID：CARD-FORTUNE-ENTRY-PORTFOLIO-PRD-001

## BRS / StRS / SRS Trace

| ID | 類型 | 需求 | 追溯 |
|---|---|---|---|
| BRS-001 | Business | Pantheon 需要入口 portfolio 來決定每個入口的第一入口情境與本輪優先驗證 | Root |
| BRS-002 | Business | 第一階段要降低三入口混做造成的範圍與信任風險 | Root |
| BRS-003 | Business | 入口必須接回 Pantheon 商業飛輪 | Root |
| StRS-001 | Stakeholder | 新使用者需要低摩擦、可分享的身份入口 | BRS-001 |
| StRS-002 | Stakeholder | 回訪使用者需要可日常互動的當下問題入口 | BRS-001, BRS-003 |
| StRS-003 | Stakeholder | 深度使用者需要理解命盤/命書何時出現 | BRS-003 |
| StRS-004 | Stakeholder | PM 需要明確知道下一張卡不是開發卡 | BRS-002 |
| SRS-001 | System/Product | 產品需求 SHALL 把 64 人格定位為 identity / share 入口 | StRS-001 |
| SRS-002 | System/Product | 產品需求 SHALL 把塔羅定位為 daily ritual / current question 入口 | StRS-002 |
| SRS-003 | System/Product | 產品需求 SHALL 把命盤/命書定位為 depth / paid report 層 | StRS-003 |
| SRS-004 | System/Product | 產品需求 SHALL 明列每個入口的成功指標 | StRS-004 |
| SRS-005 | System/Product | 產品需求 SHALL 明列第一階段不做前端/API/runner | StRS-004 |
| SRS-006 | System/Product | 產品需求 SHALL 明列非診斷、非保證、非恐嚇銷售邊界 | BRS-002 |

## Quality Check

| 需求 | 必要性 | 單一性 | 無歧義 | 可驗證 | WHAT not HOW | 結果 |
|---|---|---|---|---|---|---|
| SRS-001 | yes | yes | yes | yes | yes | pass |
| SRS-002 | yes | yes | yes | yes | yes | pass |
| SRS-003 | yes | yes | yes | yes | yes | pass |
| SRS-004 | yes | yes | yes | yes | yes | pass |
| SRS-005 | yes | yes | yes | yes | yes | pass |
| SRS-006 | yes | yes | yes | yes | yes | pass |

## Acceptance

- PRD 可讓 PM 判斷三個入口是否都能作第一入口，以及本輪優先驗證哪個入口。
- PRD 不要求任何前端/API/runner 實作。
- 每個入口都有使用者問題、飛輪節點、成功指標與風險邊界。
- 下一張卡仍是產品驗證卡，不是工程卡。
