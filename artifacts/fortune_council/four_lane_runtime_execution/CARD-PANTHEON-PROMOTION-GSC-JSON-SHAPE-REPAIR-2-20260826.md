---
id: CARD-PANTHEON-PROMOTION-GSC-JSON-SHAPE-REPAIR-2-20260826
chain_id: PANTHEON-PROMOTION-HISTORY-AUTHORITY-BOUNDARY-20260826
role: repair
cycle: 2
model: gpt-5.5
reasoning: high
status: ready
thickness: strict
risk: high
parent_candidate_sha: d91ff1c161
finding_ids:
  - PHAB-P1-002
---

# 修正 Promotion GSC JSON 形狀契約

## 唯一 finding

`PHAB-P1-002`：`_gsc_copy_identity_snapshot()` 以 `_read_json_file()` 驗證所有
`gsc-copy/**/*.json`；後者同時要求 JSON 頂層必須是 object。既有
`editorial-review/deterministic-findings.json` 的合法契約是 array，因此正式 plan
在 snapshot 階段錯誤拒絕既有合法資料。

## 唯一修復切片

- 允許修改：
  - `scripts/pantheon_content_runtime_promotion.py`
  - `tests/test_pantheon_content_runtime_promotion.py`
- 先在 `d91ff1c161` 上新增並實跑一個 RED-capable regression，證明合法 JSON array
  會因 `gsc-copy JSON must be an object` 被拒絕。
- 最小修復 snapshot seam：GSC `.json` 必須是可解析的 JSON value；object 與 array
  都合法。不得放寬 transaction receipt、publisher ledger、run state、brief、capacity
  receipt 或 terminalization receipt 的 object 契約。
- invalid JSON、symlink、unexpected residue、plan/apply drift 與 byte-preservation 必須
  維持 fail closed。

## Regression 與驗收

- `PHAB-REG-P1-002`：preserved run 的 `editorial-review/deterministic-findings.json`
  內容為 `[]`；`plan_promotion()` 必須回 `READY_TO_APPLY`，且不得改寫既有 bytes。
- 既有 invalid JSON regression 必須仍失敗在 snapshot gate。
- 執行 promotion 全檔與 runtime activation 測試。
- 執行 Python syntax check、確認無 `[DBG-`、執行 `git diff --check`。
- 交付 RED 指令與症狀、GREEN 結果、candidate SHA、changed files、production mutation
  count（必須為 `0`）。

## 禁止範圍

- 不刪除、不隔離、不改寫那兩個 array JSON 或任何 queue／歷史資料。
- 不執行 promotion apply/finalize、A/B/C、transaction、push、deploy、publish 或 restart。
- 七個服務維持停止；不得建立新 Repair、Reviewer 或 replacement task。
- 只能交付 `DELIVERED_REPAIR_CANDIDATE`，不得宣稱 Review GO 或 production 可用。
