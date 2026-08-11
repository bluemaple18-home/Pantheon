# CARD-CONTENT-WRITER-VNEXT-RA-CHECKPOINT-B-REASSESSMENT-001

## 工作名稱

Writer vNext Checkpoint B post-repair reassessment

## 固定來源

- integrated parent：`95798b7ec62df617b22a4a7f4257d029506a25c9`
- previous BLOCKED assessment：`4b90fb7f61d52fc0ff50af20acae678b0b1ca149`
- Repair-1 candidate：`883db8cbf2033fe5bbb1acb8399a5d021047e63a`
- Repair-1 REVIEW_GO：`95798b7ec62df617b22a4a7f4257d029506a25c9`
- chain／role：沿用唯一 Reviewer
- 模型：`gpt-5.5`
- reasoning：`high`

## 目的

在原 P1 已修復並通過獨立 re-review 後，重新判定 Checkpoint B 是否可進入「等待使用者另行授權 canary」狀態。

這不是 canary 授權；任何 production/canary/正式產文仍為禁止。

## 必驗契約

1. 重新跑 repo readiness packager／validator，必須先於 official thin gate。
2. official positive gate、missing-step negative gate、adversarial thin-gate probe 都需重跑並保留邊界解釋。
3. 重算 RA004 capability continuity、RA005 full capacity proof、RA007 digest/current baseline。
4. 重新取得當下 host capacity 的兩次唯讀樣本；套用 `max(20 GiB, 10% total)` reserve。若任一必要樣本低於 reserve，必須 `BLOCKED`，不得用歷史 PASS 覆蓋。
5. 重跑 Repair-1 卡片指定的 capacity suite 與 13-test 組合 suite。
6. 驗 Repair-1 REVIEW_GO、findings 為空、production/canary flags 均為 false、正式服務仍 0/4。
7. 不得把 RA007 slice-local `NO-GO` 改寫為 `PASS`；只能在新 reassessment evidence 中做 composition 判定。

## 可改範圍

- `artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_checkpoint_b_reassessment/**`

其他檔案一律禁止修改。

## 必備輸出

- `findings.json`
- `authority-map.md`
- `gate-results.json`
- `capacity-composition.json`
- `current-host-samples.json`
- `checkpoint-verdict.md`
- `verification.md`

## 結論

- `CHECKPOINT_B_READY_FOR_CANARY_AUTHORIZATION`：所有必要 gate、測試與當下容量安全均通過；仍須使用者另行明確授權 canary。
- `BLOCKED`：任何 P0/P1、測試、identity、digest、capacity 或 current-host reserve gate 未通過。

## 禁止範圍

- 禁止新增 Reviewer／Repair／task／sub-agent。
- 禁止修改 code、tests、既有 RA004–RA007／assessment／repair／review evidence。
- 禁止 cleanup、remove、prune、archive、push、deploy、tag、production、canary、publication、network write、服務啟停。

## 交付

- 單一 assessment evidence commit，父節點必須是本卡 source commit。
- worktree clean。
- 回報結論、evidence SHA、findings 與必要驗證摘要。
