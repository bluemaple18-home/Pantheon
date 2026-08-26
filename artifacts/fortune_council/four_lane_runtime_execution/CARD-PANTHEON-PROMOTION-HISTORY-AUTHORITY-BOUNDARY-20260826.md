---
id: CARD-PANTHEON-PROMOTION-HISTORY-AUTHORITY-BOUNDARY-20260826
chain_id: PANTHEON-PROMOTION-HISTORY-AUTHORITY-BOUNDARY-20260826
role: implementation
cycle: 1
model: gpt-5.5
reasoning: high
model_reason: fixed-authority-boundary change in production promotion safety logic
status: ready
thickness: strict
risk: high
---

# Promotion 歷史狀態權限邊界修復

## Root question

修正 runtime promotion 的責任邊界：promotion 必須證明 queue 在換版期間原封不動，但不得因已具有 durable terminal/publication evidence 的歷史 state 缺少新版 execution schema，就讓它們繼續擁有全域 promotion 否決權。

## 已確認根因

目前 `_queue_identity_snapshot` 會把 `preserved_run_ids` 對應的所有 registry state 以現行 identity-envelope／brief schema 重新做語意驗證。這把「byte-preservation / concurrent-mutation guard」與「歷史 job schema migration」綁成同一個 promotion gate，導致 terminal、published、released、superseded 或 abandoned 歷史紀錄因格式舊而阻塞新 runtime。

## 唯一實作切片

- `traces_to`: `FR-PHAB-001`、`FR-PHAB-002`、`FR-PHAB-003`、`SC-PHAB-001`。
- 允許修改：
  - `scripts/pantheon_content_runtime_promotion.py`
  - `tests/test_pantheon_content_runtime_promotion.py`
- 其他檔案只能唯讀。
- 不得 cherry-pick 或整批搬入 `ff8d61a328b39c91de49cdc9b3c4bd9f77c08443`；可唯讀參考，但實作必須由本卡 invariant 推導且保持最小 diff。

## 行為契約

- `FR-PHAB-001`：promotion 仍須對整個 queue 建立 deterministic byte/tree snapshot，並在 plan/apply/finalize 邊界拒絕任何 drift、symlink、path escape、重複 run identity、unexpected residue 或 exact allowlist mismatch。
- `FR-PHAB-002`：只有仍具 operational authority、可能在 promotion 後繼續執行或被選取的 run，才必須通過現行 identity-envelope／brief semantic contract；至少包含 active/in-flight 與尚未發布的 candidate。這些 run 缺 schema 或 identity 不一致仍須在 mutation 前 fail closed。
- `FR-PHAB-003`：已由 durable ledger／terminalization evidence 證明為 published、published_translation、released、superseded 或 terminal-abandoned 的 history，只需通過其 owner evidence、run-id/path 結構與 byte-preservation 契約；不得僅因缺少後來新增的 identity-envelope、brief lane 或其他新版 execution-only 欄位而阻塞 promotion。禁止使用 hard-coded run ID、13/6/19 allowlist、日期或 production 特例。

## RED → GREEN

先建立一個 public-behavior RED：含「舊格式 terminal/publication history + 一筆合法 current operational run」的 promotion plan，在 queue bytes 不變的前提下應 `READY_TO_APPLY`；現行程式須因歷史 schema mismatch 重現失敗。再做最小 GREEN。

另須證明：

1. active/in-flight 缺 identity 或 brief mismatch 仍失敗。
2. 未發布 create/rewrite candidate 缺現行 identity 仍失敗。
3. ledger／terminal receipt 不匹配、偽造或 conflict 仍失敗。
4. duplicate identity、unexpected state、symlink/path escape 與 allowlist drift 仍失敗。
5. plan 前後 queue 與 publisher ledger bytes/digest 完全不變。

## 禁止範圍

- 不修改、封存或刪除任何 production registry state、run directory、公開文章、publication ledger 或 create candidate。
- 不修改 Coordinator、Publisher、selector、A/B/C 驗收程式或任何服務設定。
- 不建立 retirement、cleanup、migration、rollback 或 archive subsystem。
- 不啟動七個服務；不執行 production apply、publish、push、deploy 或 restart。
- 不順手修 P2/P3，不新增第二個切片。

## 驗證與交付

- 執行新增 RED（保存失敗訊號）後完成 GREEN。
- 執行 `tests/test_pantheon_content_runtime_promotion.py` 全檔。
- 執行受影響的 promotion/runtime gate 測試；若無額外受影響集合，明確列出依據。
- 執行 Python syntax check 與 `git diff --check`。
- evidence 寫入 `artifacts/fortune_council/four_lane_runtime_execution/evidence/promotion_history_authority_boundary/`，只收精簡 machine-readable receipt，不放 production 資料副本。
- 交付完整 candidate SHA、changed files、RED/GREEN 指令與結果、測試摘要、production mutation count（必須 `0`）及剩餘風險；只能回報 `DELIVERED_CANDIDATE`，不得宣稱已整合或可啟服務。

## 停損

- 若無法用 durable owner evidence 區分 operational 與 historical authority，立即停止並回報唯一 blocker；不得退回用 status、日期、run ID 或刪資料猜測。
- 同一 blocker 第三次失敗即停止，不建立第四次嘗試。
