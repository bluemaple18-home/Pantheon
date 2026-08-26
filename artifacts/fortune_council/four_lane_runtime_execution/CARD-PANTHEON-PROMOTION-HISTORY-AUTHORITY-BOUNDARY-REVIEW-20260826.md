---
id: CARD-PANTHEON-PROMOTION-HISTORY-AUTHORITY-BOUNDARY-REVIEW-20260826
chain_id: PANTHEON-PROMOTION-HISTORY-AUTHORITY-BOUNDARY-20260826
role: reviewer
cycle: 1
model: gpt-5.5
reasoning: high
model_reason: fixed-SHA review of production promotion authority and fail-closed boundaries
status: ready
thickness: strict
risk: high
candidate_sha: d60a078fc204c87e3d4811a9b1ee1678123d402c
base_sha: 1a05ee2a9fb2e8a760e2e5672f87778fc5b22178
---

# Review：Promotion 歷史狀態權限邊界

## 目的

獨立審查 candidate `d60a078fc204c87e3d4811a9b1ee1678123d402c` 是否真正把 promotion 的 byte-preservation responsibility 與歷史 execution-schema validation 分離，同時維持 operational state fail closed。

## 唯讀範圍

- 比較 base `1a05ee2a9fb2e8a760e2e5672f87778fc5b22178` 與 candidate `d60a078fc204c87e3d4811a9b1ee1678123d402c`。
- 主要檔案：
  - `scripts/pantheon_content_runtime_promotion.py`
  - `tests/test_pantheon_content_runtime_promotion.py`
  - `artifacts/fortune_council/four_lane_runtime_execution/evidence/promotion_history_authority_boundary/`
- 不得修改檔案、production runtime、registry、run directory、ledger 或服務。
- 不得 push、deploy、publish、啟動服務、清資料或建立其他 task。

## 必查契約

1. 只有 durable owner evidence 已完整證明的 published、published_translation、released、superseded 或 terminal-abandoned history，才可免除後來新增的 execution-only schema；不得只靠 status、日期、run ID 或目錄缺失放行。
2. active/in-flight 與未發布 create/rewrite candidate 缺 identity、brief mismatch、lane/article drift 時仍在任何 mutation 前 fail closed。
3. publication ledger 必須拒絕 duplicate、conflict、wrong mode、wrong article IDs 與 status/lifecycle 不一致；不得讓偽造 ledger 把 operational run 降格成 history。
4. dangling-active terminalization receipt 必須完整綁定 state before/after、run ID、run directory、reason、digest 與 canonical path；檔案本身或任一祖先 symlink/path escape 均不得使 promotion 讀取受控 queue root 外的 evidence。
5. exact preserved-run allowlist、duplicate identity、unexpected residue、queue tree digest、plan/apply drift 與 transaction rollback 防線不得弱化。
6. plan 對 queue 與 publisher ledger 為零寫入；candidate 不得包含 13/6/19 或任何 production identity 特例。
7. 變更必須符合原 implementation card 的 FR-PHAB-001/002/003 與 RED→GREEN 契約；不得把本 Review 擴成 registry redesign。

## 驗證

- 重跑 `tests/test_pantheon_content_runtime_promotion.py` 全檔。
- 重跑 `tests/test_pantheon_runtime_activation.py`。
- 另做 bounded adversarial check：terminal receipt parent-directory symlink escape、ledger/status conflict、active missing schema、unpublished candidate missing schema。
- 執行 syntax check 與 `git diff --check`。
- production mutation、service start、push、deploy、publish 均須為 `0`。

## 判定

- 只接受 `REVIEW_GO` 或 `REVIEW_NO_GO`。
- 只有 P0/P1（資料完整性、authority bypass、production safety、需求不符或 regression）可阻擋；P2/P3 只列 residual risk。
- finding 必須有 ID、severity、檔案/行號、可重現證據與 bounded acceptance；不得提出 scope 外的一般重構。
