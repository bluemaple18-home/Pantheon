---
id: SLICE-JKQ-OBS-001
status: OBSERVATION_COMPLETE
type: evidence
---

# 日韓翻譯品質基線

- snapshot_at: `2026-08-03T16:01:33+08:00`
- sample: `ja=20, ko=20, en=10`
- source_class: `i18n-new=23, i18n-rewrite=27`
- primary_stage: `{"plan": 34, "publisher": 7, "reviewer": 9}`
- unknown_or_generic: `0`
- runtime sources: local-only 唯讀 queue snapshot 與 Publisher ledger；提交檔不保存絕對路徑或完整文章內容。

## Harness contract

```text
harness: yes
pattern: Classify and Act
scope: 20 ja + 20 ko + 10 en terminal translation runs
output_schema: locale/source_class/primary_stage/outcome/error/reviewer_codes/repair_route/evidence_digest
stop_condition: 50 mutually-exclusive rows; unknown_or_generic=0; replay controls match expectations
safety_boundary: read-only runtime; no provider call; output only in card evidence allowlist
```

## 分類摘要

- outcome_code: `{"plan_contract_rejected": 32, "plan_transport_GeminiApiFailure": 1, "plan_transport_V4BrokerFailure": 1, "publisher_published": 6, "publisher_ready": 1, "reviewer_rejected": 9}`
- target reviewer codes: `{"NON_NATIVE_SEARCH_INTENT": 3, "SOURCE_SYNTAX_TRANSFER": 7}`
- saved plan replays: `32`
- proven false-negative: `1`
- negative controls preserved: `True`

## Observation checkpoint

保存 response 顯示一個可重現的 locale-plan false-negative：來源中的 `Rider–Waite–Smith`
在 plan response 以 ASCII hyphen 寫成 `Rider-Waite-Smith`，後接自然日文時仍被語言 gate 拒絕。
其餘 plan rejection 為 safety flag 不一致、來源語言殘留或 rebuild topology 重用；不得放寬。
Reviewer 主因另由固定 fixture 建立 RED 後才能修改 writer prompt。
