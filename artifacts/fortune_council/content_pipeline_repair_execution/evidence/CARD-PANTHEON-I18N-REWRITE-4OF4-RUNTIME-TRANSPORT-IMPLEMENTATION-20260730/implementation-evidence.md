# Runtime／Transport P0 Implementation Evidence

- card: `CARD-PANTHEON-I18N-REWRITE-4OF4-RUNTIME-TRANSPORT-IMPLEMENTATION-20260730`
- chain: `pantheon-i18n-rewrite-4of4-runtime-stability-p0-20260730`
- role: implementation
- cycle: 1
- status: `DELIVERED_CANDIDATE`
- base: `7c0ce9f637ade2684751c6c1938999f20476d1fa`
- context: `CONTEXT_DEGRADED`（CodeGraph 未在本 worktree 初始化；依卡片契約降級為 allowlist 限域原始碼查找）

## Acceptance mapping

### SC-001 — Runtime identity

- Publisher 以封閉、排序的 `TRANSACTION_RUNTIME_PATHS` 產生 manifest。
- manifest 同時綁定 path membership、檔案 byte length 與 SHA-256；canonical manifest 再產生 runtime digest。
- deployment contract 新增 `--expected-runtime-digest`；actor bytes、manifest membership 或 digest 漂移均 fail closed。
- content-only `origin/main` descendant 仍可由舊 actor runtime 執行；transaction worktree 以 manifest 與 digest 比對 actor runtime。

### SC-002 — Transport budget

- 外部 failure receipt 新增封閉 `failure_category`：auth、quota、network、model unavailable、CLI nonzero、malformed payload、schema-invalid payload 等。
- runner 在寫入 inbox 前執行 response schema 驗證；schema-invalid payload 寫入 failure receipt，不交給 semantic repair。
- transport retry 固定最多兩次重試／三次總 attempt；operation receipt 記錄 category、attempt count 與 logical request SHA。

### SC-003 — Idempotency and side effects

- retry queue job 由 `logical request SHA + transport_attempt` 派生；job ID 可區分 attempt，但 namespace、prompt/schema hash 與 `request_sha256` 全程不變。
- writer／reviewer schema failure 不建立 root candidate、review、approval 或 run evidence，也不前進至 semantic attempt 02。
- 未修改 publication、ledger、tag、push ordering。

## RED evidence

Command:

```text
.venv/bin/python -m pytest tests/test_agy_content_publisher.py::test_runtime_manifest_digest_is_path_ordered_and_byte_sensitive tests/test_agy_content_publisher.py::test_deployment_preflight_returns_read_only_plan_without_mutation tests/test_agy_gemini_outbox.py::test_runner_classifies_schema_invalid_payload_before_inbox_side_effect tests/test_agy_gemini_outbox.py::test_outbox_client_retry_keeps_logical_request_identity tests/test_agy_gemini_outbox.py::test_transport_failure_taxonomy_is_closed_and_retryable tests/test_agy_gemini_outbox.py::test_invalid_writer_schema_uses_transport_budget_without_semantic_repair tests/test_agy_multilingual_pipeline.py::test_transport_failure_does_not_advance_translation_semantic_attempt -q
```

Result: `13 failed`。失敗點分別證明當時尚無 runtime manifest/digest、retry 仍以 `-rN` 改變 logical identity、runner 尚未在 inbox 前拒絕 schema-invalid payload，且 operation receipt 尚未保存 transport category。

## GREEN and regression evidence

Focused GREEN:

```text
.venv/bin/python -m pytest tests/test_agy_content_publisher.py::test_runtime_manifest_digest_is_path_ordered_and_byte_sensitive tests/test_agy_content_publisher.py::test_deployment_preflight_returns_read_only_plan_without_mutation tests/test_agy_gemini_outbox.py::test_runner_classifies_schema_invalid_payload_before_inbox_side_effect tests/test_agy_gemini_outbox.py::test_outbox_client_retry_keeps_logical_request_identity tests/test_agy_gemini_outbox.py::test_outbox_client_stops_after_two_json_decode_retries tests/test_agy_gemini_outbox.py::test_transport_failure_taxonomy_is_closed_and_retryable tests/test_agy_gemini_outbox.py::test_invalid_writer_schema_uses_transport_budget_without_semantic_repair tests/test_agy_multilingual_pipeline.py::test_transport_failure_does_not_advance_translation_semantic_attempt -q
```

Result: `14 passed in 0.11s`。

Affected suites:

```text
.venv/bin/python -m pytest tests/test_agy_content_publisher.py tests/test_agy_seo_copy_pipeline.py tests/test_agy_multilingual_pipeline.py tests/test_agy_gemini_outbox.py tests/test_agy_gemini_transport_probe.py -q
```

Result: `371 passed, 1 warning in 60.56s`。

Additional runner consumers:

```text
.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py tests/test_agy_gemini_v4_broker.py tests/test_agy_gemini_reviewer_cutover.py -q
```

Result: `89 passed in 23.34s`。

## Changed-file boundary

- `ops/launchd/com.pantheon.agy-content-publisher.plist.example`
- `scripts/agy_content_publisher.py`
- `scripts/agy_gemini_outbox.py`
- `scripts/agy_gemini_runner.py`
- `scripts/agy_seo_copy_pipeline.py`
- `scripts/install_agy_content_publisher_launchd.sh`
- `tests/test_agy_content_publisher.py`
- `tests/test_agy_gemini_outbox.py`
- `tests/test_agy_multilingual_pipeline.py`
- 本 evidence

全部位於卡片 allowlist。

## Remaining risk and forbidden production actions

- 未呼叫真實 provider，未 push、deploy、publish，未安裝或重裝 LaunchAgent。
- production actor 採用新 runtime digest contract 前仍需由主線取得明確授權後執行一次正式部署；本卡沒有執行。
- affected suite 保留一個既有 selector-resolution `SyntaxWarning`；不影響測試結果。
