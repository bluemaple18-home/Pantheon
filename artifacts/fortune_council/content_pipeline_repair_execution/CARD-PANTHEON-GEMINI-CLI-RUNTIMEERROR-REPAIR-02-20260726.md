# CARD-PANTHEON-GEMINI-CLI-RUNTIMEERROR-REPAIR-02-20260726

## 任務

- Chain：`pantheon-gemini-cli-runtimeerror-repair-20260725`
- Parent candidate：`d4fa6d1a29721714b72b46f69050f5a0905a5580`
- Reviewer verdict：`NO_GO`
- Role：implementation only

## 唯一修復

Failed receipt parser 對 64 KB 內的深巢狀合法 JSON 可能由 `json.loads` 拋出 `RecursionError`。在 public consumer parse boundary 將其收斂為固定 `InvalidFailureReceipt`，使用 `from None`，不得回顯 payload、traceback、本機路徑或任意 exception text。

## 範圍

只允許修改：

- `scripts/agy_gemini_outbox.py`
- `tests/test_agy_gemini_outbox.py`
- `tests/test_agy_gemini_coordinator.py`（state 端到端必要時）
- 原 repair evidence 目錄新增 `repair-2.md`
- 本卡

禁止其他 production code、真實 Gemini probe、生成請求、真實 queue/receipt/ledger/run state、文章、credential、CLI/global config/LaunchAgents、reload、fallback、V4 default、push、merge與 deploy。

## 驗證與交付

- Public consumer RED → GREEN。
- Privacy targeted、affected suites、publisher、full pytest。
- Compile、`git diff --check`、allowlist、DBG、secret/path/leakage scan。
- 單一 Repair-2 commit、worktree clean、不 push。
- 交付僅為 `REPAIR_READY_FOR_REVIEW + full SHA` 或 `BLOCKED`。
