# Source Inventory

固定 HEAD：`4a3dfeac1943061edfce5350cb6bb25e35ff64c0`

Generation：`provider-readiness-4a3dfeac1943-20260902`

Provider fix SHA：`2d03f97a7750e23cb1e67dd850e841fa35e3e194`（固定 HEAD 的直接父 commit，`Fix fresh allocator provider count`）。

CodeGraph：`CONTEXT_DEGRADED`。依任務指示，CodeGraph 已確認未初始化，因此只以 bounded `rg` 與必要 source ranges 盤點。

## 正式入口

| Step | Production formal boundary | Harness call | I/O evidence |
|---|---|---|---|
| create | `scripts.agy_gemini_coordinator:register_run` | `scripts.agy_gemini_coordinator:coordinator_create_run_receipt_preflight` | `harness/sandbox/evidence/positive/01-create.json` |
| run | `scripts.agy_gemini_coordinator:cycle_once` | `scripts.agy_gemini_coordinator:coordinator_create_run_receipt_preflight` | `harness/sandbox/evidence/positive/02-run.json` |
| select | `scripts.agy_content_publisher:formal_capability_preflight` | same | `harness/sandbox/evidence/positive/03-select.json` |
| publish | `scripts.agy_content_publisher:formal_capability_preflight` → `publish_ready_runs` | same | `harness/sandbox/evidence/positive/04-publish.json` |
| transaction | `scripts.agy_content_publisher:formal_capability_preflight` → `_isolated_transaction_worktree` | same | `harness/sandbox/evidence/positive/05-transaction.json` |
| tag | `scripts.agy_content_publisher:formal_capability_preflight` → `_stage_commit_tag_push` | same, injected dry-run git | `harness/sandbox/evidence/positive/06-tag.json` |
| push | `scripts.agy_content_publisher:formal_capability_preflight` → `_stage_commit_tag_push` | same, injected dry-run git | `harness/sandbox/evidence/positive/07-push.json` |

## 隔離契約

- create/run 的 `process` 採正式 coordinator 入口內建的 deterministic `local_process`，不呼叫外部 provider。
- publish 設定 `dry_run=True`、`push=False`；transaction/tag/push 的 git runner 為 `_formal_capability_dry_run_git`。
- fake tag/push sink 僅為 `capability/harness/sandbox/.git/**` 與 operation trace；不解析或呼叫 remote。
- `publisher-real-tag-mode` 與 `publisher-real-push-mode` 由相同正式 Publisher boundary 拒絕，證據分別為 blocked 74/75。
- 全鏈固定 `execution_line_id=exec-provider-readiness-4a3dfeac1943-20260902`、`correlation_id=corr-provider-readiness-4a3dfeac1943-20260902`、task-specific actor identity 與可由 `harness/runtime_binding.json` 重算的 runtime digest `a6f7ac78b0a6659ccc884a9c712a999b1d6fed0661d8b631809c073cdc41284a`。
- `provider_runtime_readiness_harness.py --verify-only` 對 generation、actor HEAD、Provider fix SHA、七步 identity 與每個正負 evidence artifact執行 fail-closed assertion。
- 未執行真 provider、network、publish、deploy、activation、launchctl、remote push 或 production mutation。
