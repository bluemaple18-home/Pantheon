# Production Gemini key sharding verification

## Snapshot

- Status: `DELIVERED_CANDIDATE`
- Base: `1e9e505f3a40627abbf797e0fe8d8572fa72f192`
- Root question: production 新文、舊文改寫、英／日／韓 lane 是否能對每個新 job deterministic 選擇三個 owner-only credential slot 之一，同時保持 V4 shadow 與 flag-off CLI 不變。
- Result: implementation 與本機測試通過；未 activation、未 live request、未 deploy。

## Repair 1

- Candidate repaired: `7a99579310d4ed6140117464db524e495efd471e`
- RED：
  - relative manifest path 在 absolute-path gate 前會進入 `_open_private_file`。
  - JSON boolean `true` 會因 Python `bool`/`int` 相容性通過 `schema_version == 1`。
  - 相同 pool 與相同三槽只改輸入排列時，`manifest_sha256` 不同。
  - 三個 regression tests 首跑結果：`3 failed, 90 deselected`。
- GREEN：
  - manifest path 在任何 production manifest open 前要求 absolute。
  - `schema_version` 要求 exact `int` 且值為 `1`。
  - 驗證完成後，以 `slot_id` 排序的 canonical manifest projection 計算 SHA-256；projection 只含 manifest identity/path 欄位，不讀取 credential value。
  - 三個 regression tests：`3 passed, 90 deselected`。
  - production pool focused：`20 passed, 73 deselected`。
  - outbox + SEO copy + coordinator：`179 passed in 48.64s`。
  - publisher + multilingual：`59 passed in 3.14s`。
  - full pytest（完整 dependencies）：`476 passed, 1 warning in 102.33s`。
- Fixed-base comparison：
  - 沒有 `node_modules/iztro` 時，Repair 1 full pytest 為 `474 passed, 2 failed`；兩個 failure 都是 Ziwei provider 回退。
  - 在相同無 `node_modules` 條件下，fixed base `1e9e505f3a40627abbf797e0fe8d8572fa72f192` 的相同兩個 test nodes 亦為 `2 failed`，failure message 相同。
  - 暫時提供既有 `node_modules` 後，Repair 1 full pytest 為 `476 passed`；暫時 symlink 已移除。
- Static gates：
  - Python compile、`git diff --check`、privacy pattern、absolute user path、debug marker：pass。
  - V4 broker/probe/plist/installer/docs/tests path-scoped diff：empty。

## RED / GREEN

- RED：新增 production pool 測試後首次有效執行為 `8 failed, 1 passed, 73 deselected`。主要預期失敗是 secure pool selector 尚不存在、production flag 尚未導向 provider、receipt 尚未支援匿名 pool identity；另有一個測試 placement defect，修正 test harness 後才進入 GREEN。
- GREEN（production pool focused）：`9 passed, 73 deselected`。
- 最終三套 focused：`176 passed in 48.19s`。

## Acceptance mapping

- `PROD-SHARD-001/006`：production 只讀 `AGY_GEMINI_CREDENTIAL_POOL_FILE`；未設定時維持既有 CLI。V4 檔案與 V4 environment contract 未修改。
- `PROD-SHARD-002/003`：strict 三欄 manifest、三個唯一 slot、absolute credential paths；manifest 與全部 credential file 都驗證 owner、mode、regular、non-symlink。Selected credential 採 lstat/open/fstat identity check。
- `PROD-SHARD-004`：canonical `slot_id` sort；`SHA-256(pool_id + NUL + job_id)` 前 8 bytes big-endian modulo 3；300-job 測試覆蓋三槽且同 job 穩定。
- `PROD-SHARD-005`：production pool 使用 no-redirect 單次 HTTP transport。3xx、429、503、timeout、transport failure 測試都只有一次 provider call，terminal 且不建立 inbox。
- `PROD-SHARD-007`：success/failure receipt 與 stdout 只含 strict validated `pool_id`、`slot_id`、`manifest_sha256`；invalid extra path field fail closed。
- `PROD-SHARD-008`：installer 只在明確 opt-in 時，對 `new`、`rewrite`、`i18n-new`、`i18n-rewrite` 四條 lane 動態加入 production pool manifest path；template flag-off 不含該 environment key。
- `PROD-SHARD-009`：既有 archive/failed 行為保留；terminal failed job 由既有 archive/failed identity 阻止重送。未修改 queue/ledger/deferred/quarantine 清理行為。
- `PROD-SHARD-010`：focused、publisher、多語、full suite、shell syntax、compile、diff 與 privacy gates 均已執行。

## Verification results

- Focused:
  - `.venv/bin/python -m pytest -q tests/test_agy_gemini_outbox.py tests/test_agy_seo_copy_pipeline.py tests/test_agy_gemini_coordinator.py`
  - Result: `176 passed in 48.19s`
- Publisher + multilingual:
  - `.venv/bin/python -m pytest -q tests/test_agy_content_publisher.py tests/test_agy_multilingual_pipeline.py`
  - Result: `59 passed in 2.92s`
- Full pytest:
  - `.venv/bin/python -m pytest -q`
  - Result: `473 passed, 1 warning in 102.12s`
  - Warning: upstream Starlette `httpx` deprecation warning；非本次變更。
- Python compile:
  - `.venv/bin/python -m py_compile scripts/agy_gemini_runner.py scripts/agy_gemini_outbox.py scripts/agy_seo_copy_pipeline.py`
  - Result: pass
- Installer syntax:
  - `bash -n scripts/install_agy_gemini_coordinator_launchd.sh`
  - Result: pass
- Diff whitespace:
  - `git diff --check`
  - Result: pass
- V4 boundary:
  - V4 broker、probe、plist、installer、docs 與 tests 的 path-scoped diff 為空。
  - `scripts/agy_gemini_runner.py` 的 added/removed lines 不含 `AGY_GEMINI_V4` 或 V4 contract 變更；既有 V4 branch body 保留。
- Privacy:
  - Changed-line secret pattern scan 與 absolute user-path scan：pass。
  - Test credentials 全為 synthetic non-secret values。

## Remaining risks

- 未用真實 owner-only manifest 或真實 Gemini credential 做 live request；這是刻意遵守 no-secret/no-deploy 邊界。
- Provider 接收 request 後若網路回應遺失，無法由 client 證明 provider-side exactly-once；實作會 terminal fail closed，且禁止自動重送。
- Installer/plist candidate 尚未寫入使用者 LaunchAgents；activation 需要後續獨立 deploy 授權與本機 manifest 準備。

## Boundary statement

本次未讀取或持久化任何真實 secret value；未建立 PR、未 merge、未 deploy、未修改 live plist，且未接觸 production queue、ledger、failed、deferred 或 quarantine。
