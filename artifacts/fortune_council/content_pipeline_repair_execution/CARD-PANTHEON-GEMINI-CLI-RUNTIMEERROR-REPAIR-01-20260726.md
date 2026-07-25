# CARD-PANTHEON-GEMINI-CLI-RUNTIMEERROR-REPAIR-01-20260726

## 任務

- Chain：`pantheon-gemini-cli-runtimeerror-repair-20260725`
- Parent candidate：`ed8147bafb11a6948ba19eec95d5e5c745da6a49`
- Reviewer verdict：`NO_GO`
- Role：implementation only

## 必修

1. 在 failed receipt consumer boundary 封閉 `error_type`，核對 receipt schema、job id 與 request hash；malformed、超長、敏感文字、非字串值必須 fail closed，且不得進入 exception、CLI stdout、coordinator state 或 downstream operation receipt。
2. Operation receipt 只有在 `type(error_code) is str` 且命中 closed enum 時才保存；non-string、unhashable 與 unknown string 不得造成 exception handler 二次失敗。

## 範圍

只允許修改：

- `scripts/agy_gemini_outbox.py`
- `scripts/agy_gemini_coordinator.py`
- `scripts/agy_seo_copy_pipeline.py`
- `scripts/agy_gemini_runner.py`（僅端到端必要時）
- 對應三個 test files
- 原 repair evidence 目錄
- 本卡

禁止真實 Gemini probe、生成請求、真實 queue/receipt/ledger/run state 操作、credential/login/CLI/global config/LaunchAgents 修改、fallback、V4 default 變更、發布、reload、push、merge 或 deploy。

## 驗證與交付

- Synthetic RED → GREEN。
- 受影響 suites、full pytest、`git diff --check`、allowlist、DBG 與 leakage scan。
- 追加 Repair-1 evidence。
- 單一 Repair-1 commit、worktree clean、不 push。
- 交付僅為 `REPAIR_READY_FOR_REVIEW + full SHA` 或 `BLOCKED`。
