# Promotion plan command receipt

- 正式入口：`scripts.pantheon_content_runtime_promotion.plan_promotion`
- 包裝入口：`build_readonly_evidence.py --source-root <local-temp-source-worktree>`；source locator 必須由 caller 顯式提供 canonical directory，不再寫死 machine-specific temporary path
- 模式：`plan` 等價 public API，只讀
- source checkout：`<local-temp-source-worktree>`，HEAD `5a9103785ebfc8d5a28fa8188def6069beb12d88`
- current inputs：`promotion-plan-inputs.json`
- output：`promotion-plan.json`
- output file sha256：`81237460b9088fd33799b22e999af46e9dcb99d52ba4f5cc3d596a73806b526c`
- plan digest：`e4d385214ccc09318be454e8c21a8c213d1cb1d126ed41a7e08a1c3a08422f1c`
- repeated deterministic run：兩次成功輸出的 file sha256 相同
- 結果：`READY_TO_APPLY`
- authorization state：`NOT_GRANTED`
- production mutation：`false`
- 禁止且未呼叫：`apply`、`rollback`、`finalize`、`status`

第一次 public plan 呼叫因 source path 使用 macOS `/tmp` alias 而 fail closed：`source_repo must be a canonical directory`。修正為同一 worktree 的 canonical `/private/tmp/...` 後成功；這是固定輸入路徑，不是忽略失敗。

Repair 僅修正 wrapper 的可重放參數契約；沒有重跑 plan，既有 raw plan 內的 current-machine locators 保持不變。
