# Pantheon promotion 歷史終態 authority 邊界 Repair 2

## 工作名稱

修正既有 durable failed artifact 被 current identity schema 阻塞 promotion。

## Root question

Promotion 只能讓仍具 operational authority 的 state 接受 current identity schema gate。已是 `failed` 的歷史終態，只要 identity 可由 queue-owned canonical durable evidence 唯讀重建，就不得繼續阻塞 promotion；`active` 缺 current identity envelope 則必須維持 fail closed。

## 已閉合證據

- 最後一筆正式成功 promotion transaction：`v0402-legacy-identity-runtime-promotion-6477ab81-20260826`，target actor `6477ab815e8aecca7d1e8e1588e6e5eba0fab001`，`COMMITTED` at `2026-08-26T02:01:28+00:00`。
- 現行零寫入 plan 在 `_queue_identity_snapshot()` 失敗，錯誤為 `preserved run identity envelope is missing or invalid`；transaction root 未建立，production mutation count 為 0。
- 現場缺 envelope 的 registry 分類為：`failed=12`、`complete=2`、`active=3`。第一個實際 blocker 是 canonical translation run directory 仍存在的 legacy `failed` artifact。
- `ff8d61a328b39c91de49cdc9b3c4bd9f77c08443` 曾提供 canonical brief 的唯讀 identity reconstruction，但對所有狀態使用，authority 範圍過寬。
- `92131e35522ea18063f98cf3ecd76d9675a4c299` 收緊成所有既有 run directory 都要求 current envelope；後續 `d60a078fc204c87e3d4811a9b1ee1678123d402c` 只補 published ledger 與 missing-directory terminal receipt，留下 existing-directory `failed` artifact 的缺口。

## Durable invariant

1. `active` 是 operational state；缺合法 current identity envelope 必須阻擋 promotion。
2. `failed` 且 run directory 仍存在時，可只用 canonical queue-owned durable run directory、合法 `brief.json`、registry 的 exact run binding 與 terminal status 唯讀重建 identity。
3. 重建 identity 不得修改 registry、brief、ledger、queue 或 production。
4. 所有既有 path/symlink、brief identity、durable-root 與 terminalization receipt 防護必須保持 fail closed。

## 唯一允許修改

- `scripts/pantheon_content_runtime_promotion.py`
- `tests/test_pantheon_content_runtime_promotion.py`

## 必做 RED

- `failed` + canonical durable run directory + canonical brief + missing identity envelope：修復前 RED，修復後 plan/classification PASS，且 evidence source 明確標示為 terminal brief reconstruction。
- 相同 fixture 改成 `active` + missing identity envelope：持續 RED，證明沒有把 operational authority 一併放寬。

## 禁止範圍

- 不修改或刪除任何 production queue、registry、brief、ledger、run directory。
- 不啟動七個服務，不執行 promotion apply/finalize，不跑 A/B/C。
- 不新增通用 migration、cleanup、filesystem framework、plan/apply/rollback abstraction。
- 不改 published ledger、missing-directory terminal receipt、symlink boundary 的既有契約。
- 不建立第二個 Repair task；必須回原 Repair task 執行。

## 驗證

- 新增兩個 authority-boundary regression。
- `tests/test_pantheon_content_runtime_promotion.py` 全檔。
- `tests/test_pantheon_runtime_activation.py` 全檔。
- Python syntax check。
- `git diff --check`。
- 確認 production mutation count = 0。

## 交付

只交付 `DELIVERED_REPAIR_CANDIDATE`：candidate SHA、changed files、RED→GREEN 證據、完整測試結果、clean state、production mutation count。不得 push、不得 promotion。
