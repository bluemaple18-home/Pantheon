---
id: CARD-PANTHEON-HISTORICAL-RUN-RETIREMENT-20260826
chain_id: PANTHEON-HISTORICAL-RUN-RETIREMENT-20260826
role: implementation
cycle: 1
model: gpt-5.5
reasoning: high
model_reason: 規格固定但涉及 production registry transaction
status: ready
thickness: strict
risk: high
traces_to:
  - FR-HRR-001
  - FR-HRR-002
  - FR-HRR-003
  - FR-HRR-004
  - FR-HRR-005
  - SC-HRR-001
  - SC-HRR-002
  - SC-HRR-003
  - SC-HRR-004
  - SC-HRR-005
---

# Pantheon Historical Run Retirement

## 目標與邊界

- 建立 deterministic historical-run retirement 的 plan/apply/rollback 工具與測試，安全退役下列固定 13 筆歷史 operational registry state；本卡只交付 repo candidate，正式 thread 不得碰 production。
- 允許修改：`scripts/pantheon_historical_run_retirement.py`、`tests/test_pantheon_historical_run_retirement.py`，以及本卡專屬 evidence 目錄。
- 不得修改既有 `pantheon_content_runtime_promotion`、Publisher、Coordinator 程式或測試，不得修改共享 registry、生成頁、sitemap、feed、redirects 或其他整合檔。
- production apply 只能由主線在獨立 Reviewer `GO`、fresh capacity `PASS`、fresh plan 精確列出 13 筆，且具使用者既有授權證據後執行；本卡不授權 apply。

## 固定 retirement target

只接受下列 13 個 exact IDs；集合、順序與數量均須 deterministic，任何第 14 筆或 ID drift 都 fail closed：

```text
auto-i18n-ja-fcbf5d1af50382a4d586-replacement-01
auto-i18n-en-cc1a68261a5cd9e99640-replacement-01
auto-i18n-en-cc1a68261a5cd9e99640
auto-i18n-en-a2089936cbb010f5b0c1
auto-i18n-ja-fcbf5d1af50382a4d586
auto-i18n-en-fcaa5bb4adcfef7aa55c
auto-i18n-ko-c656242ea6760f47e01a
auto-i18n-ko-9dfd75660d7a4dcc9c35-replacement-01
auto-i18n-ko-9dfd75660d7a4dcc9c35
auto-i18n-en-614aa4dc3542ab2c5637
auto-i18n-ja-1414b75a404721e95e74
auto-new-v1-20260818-001-01
auto-new-v1-20260818-002-01
```

## Preservation contract

- 保留 immutable quarantine/backup、精確 digest、原始 identity 與 ledger snapshot；quarantine 必須可由 receipt 反查且不得覆寫既有 evidence。
- 只從 operational queue 退役；不得刪公開頁、修改公開內容或刪除 translation artifacts。
- 已發布 `en V2-TAROT-LOVERS-LOVE` 必須保留 ledger 與 public identity，不得因 retirement 重新發布或移除。
- 七個服務全程停止；不得 push、deploy、publish 或 start service。
- 不得處理其餘 135 筆 state 或 26 個 create candidates；不得把本卡變成 A/B/C 驗收卡，也不得建立新卡。

## Functional requirements

- `FR-HRR-001`：plan 只讀 registry 與既有 artifact，驗證 exact 13-ID set、expected pre-state digest、identity、lane 與 artifact locator，產生 deterministic plan digest；plan 不產生 production mutation。
- `FR-HRR-002`：apply 僅接受與 fresh plan 完全相符的 expected pre-state digest、authorization digest、target set 與 transaction nonce，並以 atomic quarantine 寫入 transaction receipt。
- `FR-HRR-003`：rollback 以 receipt 保存的 immutable backup、digest 與 ledger snapshot 還原，任何 backup、digest、identity 或 pre-state drift 均 fail closed，不猜測修復。
- `FR-HRR-004`：重複 plan/apply/rollback 必須 idempotent；同 transaction identity 只能回傳既有 receipt，不得建立第二份 quarantine 或重複退役。
- `FR-HRR-005`：任何 tamper、drift、缺欄、錯 lane、14th ID、target set 不完整、公開 identity 不一致或非授權 apply 都在 mutation 前拒絕。

## Success criteria / negative matrix

- `SC-HRR-001`：plan fixture 精確包含 13 筆 target，順序、集合、pre-state digest 與 plan digest 可重現；135 筆其餘 state 與 26 create candidates 明確排除。
- `SC-HRR-002`：正向 transaction 測試證明 quarantine/backup、ledger snapshot、transaction receipt 與 rollback bundle 原子產生，且公開頁、公開內容與 translation artifacts 零變更。
- `SC-HRR-003`：idempotence 測試證明相同 plan/transaction 不重複寫入；rollback 後再次 rollback 回傳既有結果且無額外 mutation。
- `SC-HRR-004`：negative matrix 覆蓋 expected pre-state digest、authorization digest、quarantine/backup、ledger snapshot、target set、14th ID、tamper/drift、已發布 public identity 與 capacity/authorization 缺失；全部 fail closed 且 mutation count 為 0。
- `SC-HRR-005`：targeted tests、受影響 promotion tests、`git diff --check` 與 plan fixture/negative matrix 通過；candidate 不含 production apply、push、deploy、publish 或服務啟動證據。

## RED → GREEN 驗證

1. 先新增 deterministic plan/apply/rollback regression 與 exact-13 fixture，確認現況對 14th ID、digest drift、tamper、非授權 apply 或重複 transaction 未必 fail closed。
2. 以最小修改建立 retirement 工具；apply 必須由 expected pre-state、authorization、fresh plan 與 transaction receipt 共同守門。
3. 補齊 atomic quarantine、immutable backup/ledger snapshot、rollback 與 idempotence；所有負向案例在第一個 production mutation 前拒絕。
4. 執行 targeted tests、受影響 promotion tests、plan fixture 精確 13 驗證、negative matrix 與 `git diff --check`。
5. 只交付 repo candidate 與 evidence；不得執行 production plan/apply、資料搬遷、publish、push、deploy 或服務啟動。

## Production boundary / rollback

- 本卡禁止 production registry/run-dir mutation、資料搬遷、公開內容變更、translation artifact deletion、publish、push、deploy、service start 及任何外部 write。
- production apply 的唯一入口、授權、fresh capacity receipt、fresh exact plan 與 Reviewer GO 由主線另行核驗；本卡不建立或替代該 gate。
- 工具 rollback 必須只依 transaction receipt 的 exact immutable backup 與 ledger snapshot；缺任一證據即 `BLOCKED`，不得猜測、重建或刪除資料。

## 交付物

- `scripts/pantheon_historical_run_retirement.py`
- `tests/test_pantheon_historical_run_retirement.py`
- 本卡專屬 evidence：`artifacts/fortune_council/four_lane_runtime_execution/evidence/historical_run_retirement/`
- 交付需包含 candidate commit SHA、測試摘要、plan digest、exact 13-ID fixture、negative matrix、production mutation count（必須為 `0`）與剩餘風險；不得宣稱已整合、已 apply 或已發布。
