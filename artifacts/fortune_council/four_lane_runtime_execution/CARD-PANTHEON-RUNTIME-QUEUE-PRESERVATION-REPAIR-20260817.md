---
id: CARD-PANTHEON-RUNTIME-QUEUE-PRESERVATION-REPAIR-20260817
chain_id: PANTHEON-NEW-FLOW-PRODUCTION-PUBLISH-RECOVERY-20260817
role: implementation
cycle: 1
status: ready
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 規格已固定，但涉及 production promotion queue identity、fail-closed postcheck 與 rollback 核心契約。
ownership:
  - scripts/pantheon_content_runtime_promotion.py
  - tests/test_pantheon_content_runtime_promotion.py
  - artifacts/fortune_council/four_lane_runtime_execution/runtime_queue_preservation_repair_20260817/**
forbidden_scope:
  - production runtime、queue、run state、launchd、GitHub remote
  - Publisher、coordinator、lane runner、registry、sitemap、文章內容
  - 刪除、搬移、改寫 failed run 或 gsc-copy
evidence_path: artifacts/fortune_council/four_lane_runtime_execution/runtime_queue_preservation_repair_20260817/
---

# Runtime Queue Preservation Repair

工作名稱 → 修復 Runtime Promotion Queue Preservation
正在做什麼 → 讓正式 plan/apply 保留 active、complete、failed run 與既有 gsc-copy identity，同時維持 drift／symlink／duplicate fail-closed
現在狀態 → ready；未收到 activation token 前只能 bootstrap

## Root question

如何讓 aggregate promotion transaction 對 production 現況（88 runs：2 active、17 complete、69 failed；82 個 gsc-copy entries）產生 deterministic `READY_TO_APPLY` plan，同時禁止清 queue、忽略 identity 或降低 postcheck 安全性？

## 已知根因

- `scripts/pantheon_content_runtime_promotion.py::_validate_preserved_runs` 只接受 `active|complete`，拒絕 failed。
- 同函式拒絕任何非空 `gsc-copy`。
- `tests/test_pantheon_content_runtime_promotion.py::test_preserved_run_contract_rejects_failed_run` 固化了與 FR-002 衝突的舊契約。
- 不得用空 `preserved_run_ids` 繞過 plan-time identity 驗證。

## 實作契約

1. 先建立 RED：合法 failed run 與既有 gsc-copy 必須可被 promotion plan 精確保存；plan 重播 digest 相同。
2. 最小 GREEN：明確定義可保存狀態；failed 只能被完整 identity snapshot 保存，不得變成可執行／可發布。
3. gsc-copy 必須納入 deterministic snapshot／postcheck drift 驗證；不得刪除、搬移、忽略或僅檢查「非空」。
4. 保留現有 duplicate run ID、unexpected identity、invalid JSON、symlink、queue mutation、postcheck rollback tests。
5. 新增負向測試：failed identity 缺漏、gsc-copy plan/apply 間漂移、symlink/invalid residue 必須 fail closed；rollback 保留原 bytes。
6. 禁止 production mutation、launchctl、network、push、merge、tag。

## 驗證

- `<repo-root>/.venv/bin/python -m pytest tests/test_pantheon_content_runtime_promotion.py -q`
- 受影響 runtime manifest／promotion targeted tests。
- `git diff --check`
- candidate commit；工作區 clean。
- evidence：RED、GREEN、changed files、test counts、candidate SHA、remaining risk。

## 交付

只能回報 `DELIVERED_CANDIDATE` 或 `BLOCKED`。不得宣稱已整合、已部署或 production recovered。
