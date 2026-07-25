# CARD-PANTHEON-REWRITE-LANE-ACTIVE-LIMIT-REPAIR-20260725

Chain: `pantheon-rewrite-lane-active-limit-20260725`

State: `CARD_DRAFTED → QUEUED`

Role: implementation only

## 目標

修正舊文 rewrite seeder 使用四條內容流程的全域 active 數量判斷容量，導致翻譯 backlog 阻擋新舊文改寫任務。修復後，`seed_legacy_rewrite_runs()` 的 active limit 與 capacity 只能計算 `rewrite_existing_body` 模式；create、translate、i18n-new、i18n-rewrite 不得占用 rewrite seeder 容量。

## 已知證據

正式佇列共 51 個 active run、rewrite lane 為 0，但 coordinator 回報 `legacy_sweep.status=active_limit`。`scripts/agy_gemini_coordinator.py` 目前使用 `len(_active_states(queue_root))`；同檔已有 `_active_count_by_mode(queue_root, mode)`。

## 可證偽假說

1. 若根因是全域 active 計數，加入「多個非 rewrite active + rewrite active 未達上限」測試時，現況會錯誤回 `active_limit`；改為只算 `rewrite_existing_body` 後應 seed。
2. 若另有 backlog 或 registered article 去重阻塞，即使修正計數仍不 seed；此時停止擴大修改並回報主線。

## Provisioning preflight

第一步先做 provisioning preflight 並回報：cwd 必須是獨立 worktree且不得等於 `/Users/mattkuo/Documents/Pantheon`；git status 必須 clean；source SHA；branch；卡片是否存在。若卡片不存在，先依本 prompt 的完整契約原文建立該 card path，再開始 RED。

## Allowlist

- `artifacts/fortune_council/content_pipeline_repair_execution/CARD-PANTHEON-REWRITE-LANE-ACTIVE-LIMIT-REPAIR-20260725.md`（僅來源缺卡時建立，不得改寫契約）
- `scripts/agy_gemini_coordinator.py`
- `tests/test_agy_gemini_coordinator.py`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-REWRITE-LANE-ACTIVE-LIMIT-REPAIR-20260725/**`

## Forbidden

不得修改 publisher、四個 worker、launchd plist、安裝腳本、V4 transport；不得新增/發布文章；不得 push、merge、deploy、reload launchd；不得改 V4 shadow；不得碰主工作區 `reports/`；不得無關重構。

## 實作契約

1. 先新增會重現本症狀的回歸測試並實際證明 RED。
2. 最小修正：rewrite seeder 的 active limit 與 capacity 只用 rewrite mode active count。
3. 保留 `max_active_runs` public interface 與回傳狀態契約。
4. 清除所有 `[DBG-`。

## 驗證

- `.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py -q`
- `.venv/bin/python -m pytest tests/test_agy_content_publisher.py tests/test_agy_gemini_coordinator.py -q`
- `.venv/bin/python -m pytest -q`
- `git diff --check`
- `rg -n "\\[DBG-" scripts tests`

## Evidence

必須放：`artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-REWRITE-LANE-ACTIVE-LIMIT-REPAIR-20260725/`，至少：

- `red-green.md`
- `verification.md`
- `changed-files.txt`

## 交付

交付只能是 `DELIVERED_CANDIDATE`，包含完整 candidate SHA、parent/source SHA、changed files、RED→GREEN 與驗證結果。不得宣稱 `ACCEPTED`、`INTEGRATED`、`DEPLOYED` 或正式舊文已恢復。不得自行 push、merge、deploy。主線會另開獨立 Reviewer thread。
