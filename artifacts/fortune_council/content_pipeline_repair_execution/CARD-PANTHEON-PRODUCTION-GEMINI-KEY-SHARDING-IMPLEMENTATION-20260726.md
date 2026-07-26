---
status: DELIVERED_CANDIDATE
chain: PANTHEON-PRODUCTION-GEMINI-KEY-SHARDING-20260726
type: implementation
base: 1e9e505f3a40627abbf797e0fe8d8572fa72f192
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/production_gemini_key_sharding_20260726/
---

# Pantheon Production Gemini Key Sharding Implementation

- Chain: `PANTHEON-PRODUCTION-GEMINI-KEY-SHARDING-20260726`
- Type: `implementation`
- Thickness / risk: `strict / high`
- Model: `gpt-5.6-sol high`
- Base: `origin/main` at `1e9e505f3a40627abbf797e0fe8d8572fa72f192`
- Delivery ceiling: `DELIVERED_CANDIDATE`

## Root question

讓正式新文、舊文改寫、英文／日文／韓文 Gemini runner 對每個新 job deterministic 選擇三個 owner-only credential slot 之一，分攤不同帳號／project quota；V4 維持 shadow，不得升級為正式 transport。

## Verified root cause

- Production launchd 只設定 `AGY_GEMINI_CLI`，正式 job 共用單一 agy 登入帳號，該帳號 quota exhausted。
- 三槽 pool 目前只由 V4 shadow 使用；production mainline 沒有 pool manifest、選槽或匿名 slot evidence。
- 使用者意圖是三把 key 跨 operation 分流，不是只做 shadow。

## Requirements

1. `PROD-SHARD-001`：新增 production-only opt-in `AGY_GEMINI_CREDENTIAL_POOL_FILE`；不得沿用或啟用 `AGY_GEMINI_V4_CREDENTIAL_POOL_FILE`。
2. `PROD-SHARD-002`：沿用 owner-only manifest schema：`schema_version`、`pool_id`、`slots[].slot_id`、`slots[].credential_file`。
3. `PROD-SHARD-003`：manifest/credential 必須 owner-only regular non-symlink；key value 不得進 argv/env/log/queue/ledger/exception/test artifact。
4. `PROD-SHARD-004`：以 `SHA-256(pool_id + NUL + job_id)` 對 canonical sorted slots 選槽；同 job 穩定，無 mutable cursor。
5. `PROD-SHARD-005`：每 job 最多一個 provider request；429/timeout/nonzero/transport error terminal；不得換 key、retry、fallback。
6. `PROD-SHARD-006`：pool flag-off 保留既有 agy CLI；V4 broker/target/shadow/code/plist/installer 全部不得改。
7. `PROD-SHARD-007`：成功／失敗 stdout 或 closed receipt 可含非敏感 `pool_id`、`slot_id`、manifest digest；consumer strict validate；不得含 credential path/value。
8. `PROD-SHARD-008`：四個 production lane installer/plist 支援明確 pool opt-in；shared docs 不得硬編本機絕對路徑。
9. `PROD-SHARD-009`：queue/ledger/failed/deferred/quarantine 全保留；不重送既有 failed。
10. `PROD-SHARD-010`：測試覆蓋 deterministic distribution、同 job 穩定、unsafe manifest fail closed、只開 selected slot、單 request、無 fallback、privacy、flag-off regression。

## Slices

1. `PROD-SHARD-1`：secure manifest + deterministic selection，先 RED 再 GREEN。
2. `PROD-SHARD-2`：production one-request API transport，依賴 slice 1。
3. `PROD-SHARD-3`：launchd opt-in + regression，依賴 slice 2。

## Allowed files

- 本卡與其 evidence directory
- `CHANGELOG.md`
- `docs/pantheon_gemini_outbox_runner.md`
- `ops/launchd/com.pantheon.agy-gemini-lane.plist.example`
- `scripts/agy_gemini_runner.py`
- `scripts/agy_gemini_outbox.py`
- `scripts/agy_seo_copy_pipeline.py`
- `scripts/install_agy_gemini_coordinator_launchd.sh`
- `tests/test_agy_gemini_outbox.py`
- `tests/test_agy_seo_copy_pipeline.py`
- `tests/test_agy_gemini_coordinator.py`

## Forbidden

- Credential value/copy/login/OAuth/ADC/IAM/subscription change。
- 所有 V4 broker/target/shadow code、plist、installer、branch promotion/default transport。
- Queue deletion、ledger rewrite、retry reset、quarantine/deferred clearing、手動灌文章。
- Publisher/article/registry/sitemap/feed/SEO/frontend。
- Direct push main。
- Failure-driven key rotation、retry、fallback。

## Verification contract

- Focused：`test_agy_gemini_outbox.py`、`test_agy_seo_copy_pipeline.py`、`test_agy_gemini_coordinator.py`
- Publisher + multilingual regression
- Full pytest
- `bash -n scripts/install_agy_gemini_coordinator_launchd.sh`
- `git diff --check`
- Changed files/output privacy and secret scan
- Diff proves V4 unchanged
- Clean candidate commit

## Delivery contract

提交 implementation、tests、docs、changelog、card 與 evidence，回報完整 candidate SHA、changed files、精確驗證結果、remaining risks，並明確聲明未讀取或持久化任何 secret value。不得建立 PR、merge、deploy、修改 live plist，或接觸 production queue/ledger。

## Delivery result

- Status：`DELIVERED_CANDIDATE`
- Evidence：`artifacts/fortune_council/content_pipeline_repair_execution/evidence/production_gemini_key_sharding_20260726/verification.md`
- Boundary：未建立 PR、未 merge、未 deploy、未修改 live plist、未接觸 production queue/ledger。
