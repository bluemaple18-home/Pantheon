# Verification

## Required pytest

Command：

```bash
uv run pytest tests/test_agy_seo_copy_pipeline.py tests/test_agy_gemini_coordinator.py tests/test_agy_content_publisher.py
```

Final result：

```text
collected 183 items
tests/test_agy_seo_copy_pipeline.py: passed
tests/test_agy_gemini_coordinator.py: passed
tests/test_agy_content_publisher.py: passed
183 passed in 62.93s
```

第一次完整執行為 `182 passed / 1 failed`；唯一失敗是既有測試手造的
`argparse.Namespace` 沒有新增欄位。CLI 讀取改為向後相容後，針對性回歸
`2 passed`，再執行完整三檔得到上述 `183 passed`。

`uv run` 會把 root package 的目前版本同步到 allowlist 外的 `uv.lock`。
每次測試後均精準還原該單行工具副作用；交付 diff 不包含 `uv.lock`。

## Shell and plist

```text
bash -n scripts/install_agy_content_publisher_launchd.sh
exit: 0

plutil -lint ops/launchd/com.pantheon.agy-content-publisher.plist.example
ops/launchd/com.pantheon.agy-content-publisher.plist.example: OK
```

## Diff gates

```text
git diff --check
exit: 0

rg '\[DBG-' <changed Python and tests>
matches: 0
```

完成 staging 後另執行 `git diff --cached --check`，結果記錄於 candidate
commit handoff。

## Allowlist consistency

預期交付檔案：

```text
artifacts/fortune_council/content_pipeline_repair_execution/CARD-PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-IMPLEMENTATION-20260729.md
artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-implementation-20260729/preflight.md
artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-implementation-20260729/reproduction.md
artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-implementation-20260729/verification.md
artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-implementation-20260729/result.md
docs/pantheon_deployment_workflow.md
docs/pantheon_gemini_outbox_runner.md
ops/launchd/com.pantheon.agy-content-publisher.plist.example
scripts/agy_content_publisher.py
scripts/agy_gemini_coordinator.py
scripts/agy_seo_copy_pipeline.py
scripts/install_agy_content_publisher_launchd.sh
tests/test_agy_content_publisher.py
tests/test_agy_gemini_coordinator.py
tests/test_agy_seo_copy_pipeline.py
```

以上全部位於卡片 allowlist；沒有文章、registry、generated pages、sitemap、
feed、redirect、queue、ledger 或歷史 run state 變更。

## Publisher dry-run/read-only proof

`test_deployment_preflight_returns_read_only_plan_without_mutation`：

- pre/post fixture inventory 完全相同；
- `mutation_permitted=false`、`dry_run=true`；
- Git double 僅接到 `status --porcelain`、`rev-parse HEAD`、
  `rev-parse origin/main`；
- actor、queue、state、runtime、dirty、origin/main、push mode drift
  共 7 組 fixture 全部 fail closed。

`test_main_deployment_preflight_returns_before_state_or_publish_mutation`：

- CLI 在建立 state root 前返回；
- publisher function 未被呼叫；
- state root 不存在。

## Prohibited-action declaration

本卡未執行：

- production publisher 或正式 publish；
- queue、ledger、outbox、run state 的真實 mutation；
- `launchctl bootstrap`／`bootout`／`kickstart`；
- installer `--install`；
- deploy、PR、merge、`git push` 或 `--push` publish；
- API、OAuth、credential pool、secret 或 token 讀取。
