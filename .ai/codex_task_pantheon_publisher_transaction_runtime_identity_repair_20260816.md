---
id: CARD-PANTHEON-PUBLISHER-TRANSACTION-RUNTIME-IDENTITY-REPAIR-20260816
status: validated
role: implementation
chain_id: pantheon-runtime-retry-deploy-resume-20260816
cycle: 2
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
ownership: Publisher transaction runtime identity boundary
---

# Publisher transaction runtime identity 修正

## 目標

修正正式 Publisher 在隔離 transaction worktree 內，把 transaction root 誤當 manifest actor root 驗證而 fail-closed 的問題；保留正式 actor authority 與 transaction runtime byte-equivalence。

## 事實與邊界

- 使用者已授權唯一 run `apf-create-run-new-7d0e46d9ec617526f77f8213` 執行 transaction、commit、tag、push；不得處理其他 run。
- 失敗發生於 mutation 前：`formal runtime actor_root mismatch`；尚未寫文章、commit、tag、push。
- 呼叫鏈：`main` → `_isolated_transaction_worktree` → decorated `publish_ready_runs` → `_validate_formal_runtime(transaction_root, ...)`。
- 可改：Publisher、runtime manifest/promotion、三個 launchd installer、直接相關測試、本卡。
- 不改：queue schema、文章內容、Reviewer 結果、其他 run、容量政策。
- transaction root 必須是 state root 下 `transaction-*/repo` 的 canonical directory，且其 runtime bytes 必須與正式 actor 相同。

## 實作與驗證

1. 新增 formal-runtime + real transaction worktree 重現測試，證明 mutation function 收到 transaction root，但 manifest 驗證仍綁正式 actor。
2. 由 `_isolated_transaction_worktree` 建立 scoped internal authority，分離 runtime actor 與 mutation root；不得由 ENV 或路徑形狀推定 authority。
3. 非正式模式與直接 public function 行為維持不變；偽造／越界 transaction root fail-closed。
4. 跑 targeted test、受影響 Publisher suite、`git diff --check`。
5. Reviewer 通過後 commit、push、整合、正式 runtime promotion，再重新執行容量閘與唯一 run publish。
6. Promotion 只可保留明列 identity 的 `active` 或 `complete` run；`failed` 與額外 run 仍 fail-closed。
7. Prerender、feed、canonical、release-record 與 pytest 子程序統一使用 `uv run --frozen python`，不得依賴無專案套件的 system Python。
8. `uv` 必須以 manifest 綁定的 canonical absolute executable 注入所有 launchd identities；正式 Publisher 不得依賴 PATH 查找。

## 回退

若任何 pre-mutation gate 失敗，保留 run complete 狀態並停止；若 mutation 後失敗，使用既有 recovery journal 回復 base SHA。

## 驗證結果

- 重現／正負 authority 邊界：PASS。
- Publisher + runtime manifest + promotion：`195 passed`。
- `git diff --check`：PASS。
- 獨立 Reviewer：APPROVED；先前 forged bounded transaction P1 已修正並 re-review 通過。
- Promotion plan 實測發現 `complete` run 被舊 active-only 契約拒絕；納入同卡修正並重新驗證。
- Promotion 增量 re-review：APPROVED。
- 正式 transaction 實測在 prerender 因 system Python 缺 `fastapi` 失敗並完整 recovery；納入 uv execution 修正。
- uv absolute identity、presence/absence/value drift 與 restricted-PATH 正／負驗證：PASS；受影響套件 `201 passed`。
- uv authority 獨立 Reviewer re-review：APPROVED。
