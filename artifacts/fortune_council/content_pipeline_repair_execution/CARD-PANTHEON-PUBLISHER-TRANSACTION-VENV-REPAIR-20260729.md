# Pantheon Publisher Transaction Venv Repair

## 目的

讓隔離發布 worktree 能執行 repository 的 pre-push hook，解除 release commit 與 tag atomic push 阻塞。

## 根因

- Repository 設定 `core.hooksPath=.githooks`。
- `.githooks/pre-push` 固定使用 transaction repo 根目錄下的 `.venv/bin/python`。
- `.venv` 是 ignored runtime，不會出現在新建的隔離 worktree。
- `_isolated_transaction_worktree` 只連結 `node_modules`，沒有連結 actor 已驗證的 `.venv`。
- 因此內容與 196 項 gate 全過後，`git push --atomic` 仍被 pre-push hook 以 exit code 1 中止；交易已完整復原。

## 可修改範圍

- `scripts/agy_content_publisher.py`
- `tests/test_agy_content_publisher.py`
- 本卡與同任務驗證證據

## 禁止範圍

- 不繞過或停用 pre-push hook。
- 不修改文章候選、review、queue、ledger 或 retry 狀態。
- 不改 Reviewer、品質門檻、重試次數與自動發布政策。

## 驗收

1. 隔離 transaction worktree 連結 actor 的 `.venv` 與 `node_modules` runtime。
2. publisher 完整單元測試與受影響 release suite 通過。
3. `git diff --check` 通過。
4. 合併部署後執行單篇實際發布 canary，atomic push 成功且 ledger/evidence/remote main/tag 一致。
5. canary 通過後才安裝並驗證常駐 publisher。

## 回退

- 修復分支：`codex/publisher-transaction-venv-repair-20260729`
- 若驗收失敗，不合併；若上線後異常，以修復 commit 的 revert 回退。
