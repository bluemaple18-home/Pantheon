---
schema_version: 1
title: Pantheon Acceptance B gen05 production entrypoint INVALID_RECEIPT RCA result
date: 2026-08-28
status: COMPLETE
mode: RCA_ONLY
target_run: auto-i18n-ja-1414b75a404721e95e74
job_id: 61a83c341d39c882d5eed8ea23b7f805a89085e3
target_commit: 23eab63ea31031094aa084faee0e5ff65d326533
production_actor: 23eab63ea31031094aa084faee0e5ff65d326533
---

# 結論

Primary verdict：`OPERATOR_ENTRYPOINT_MISMATCH`。

直接誘因不是 provider 失敗，也不是 request 壞掉。`61a83c...` request
本身在 current `validate_external_request` 下有效；失敗來自 retry1 helper
用 `barrier-exec` 直接呼叫 `scripts.agy_gemini_runner`，但沒有帶正式
LaunchAgent 的 credential pool / allocator env。`process_once` 因此沒有走
production credential path，而是落到 `_cli_generate_json` 的 CLI fallback；
fallback 產生 `ValueError`，failed receipt 沒有 `credential_pool`、沒有
`error_code`、沒有 HTTP diagnostic，最終被分類為 `INVALID_RECEIPT`。

Durable invariant：production runner 的外部生成 transport 必須由正式
LaunchAgent entrypoint 或等價 env contract 啟動；operator helper 不可只帶
formal runtime env，而漏掉 credential pool / allocator / model-route contract。

# 證據閉合

## 1. 正式 LaunchAgent 與 helper 差異

`launchagent-env-diff-receipt.json` 顯示 installed
`com.pantheon.agy-gemini-i18n-new.plist` 含：

- `AGY_GEMINI_CREDENTIAL_POOL_FILE`
- `AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE`
- `AGY_GEMINI_MODEL_ROUTE_CONFIG`
- `AGY_GEMINI_MODEL_ROUTE_CONFIG_DIGEST`
- `AGY_WRITER_MODEL`
- `AGY_REVIEWER_MODEL`
- `AGY_GEMINI_RATE_LIMIT_COOLDOWN_SECONDS`
- formal runtime `PANTHEON_RUNTIME_*`

同一 receipt 也顯示 retry1 operator helper command 缺：

- `AGY_GEMINI_CREDENTIAL_POOL_FILE`
- `AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE`

Credential pool file 只記錄 presence/digest/mode/size，未讀出 secret 值：
exists=true、mode `0o600`、sha256
`b8451b15e9aeb3c33462b2dcbf0bb89c57c51308b5e5149aa5a856744ab98906`。

附帶發現：current installed i18n-new plist 的 ProgramArguments 仍指向舊
`g47-6477ab81-activation-only-20260826` barrier/digest，而 current production
manifest 是 `g58-23eab63e-gen05-lane-selector-repair-retry1-20260828`。這代表
「直接啟動 installed LaunchAgent」也不是可直接使用的 current exact-run
entrypoint；promotion 裝的是 staged readiness/barrier，不等於 live plist 已被
realign。

## 2. Source trace：production_enabled 與 fallback

`scripts/agy_gemini_runner.py`：

- `process_once` 先讀 `AGY_GEMINI_CREDENTIAL_POOL_FILE`。
- `production_enabled = AGY_GEMINI_V4_BROKER != "1" and bool(pool_file)`。
- production path 會要求 `AGY_GEMINI_CREDENTIAL_POOL_STATE_FILE`，讀 pool，
  做 `production_slot_admission`，並呼叫 `_begin_production_attempt`。
- 若 production path 沒啟用，會直接 `_claim_next`，然後走
  `_cli_generate_json`。
- `_cli_generate_json` 使用 `GeminiClient._cli_transport`。
- exception path 若沒有 `credential_pool`、沒有 recognized `error_code`，
  `classify_external_failure` 會落到 `INVALID_RECEIPT`。

Formal runtime guard 有驗 `PANTHEON_RUNTIME_*` 與 lane queue root，但沒有
要求 production provider env 必須存在。因此它能擋 runtime identity drift，
但不能擋「operator helper 走 fallback transport」。

Secondary verdict：`RUNTIME_FORMAL_TRANSPORT_GUARD_GAP` 是放大因素，不是主因。
主因仍是 helper entrypoint mismatch。

## 3. Provider / network attempt = 0

`provider-attempt-zero-receipt.json` 顯示：

- 該 job 的 `production-attempts/*.attempt` marker count = `0`。
- failed receipt 不含 `credential_pool`。
- failed receipt 不含 `error_code`。
- credential pool state file 存在且 0600，但沒有此 job attempt 訊號。

所以本次不是 provider API rejection、quota、rate limit 或 network failure；
是 provider attempt 之前的 entrypoint/env 問題。

## 4. Replacement seam read-only preflight

`replacement-seam-readonly-preflight.json`：

- archived request 以 current `validate_external_request` 驗證為 valid。
- replacement preflight 未 execute，provider calls = 0。

`replacement-seam-readonly-preflight-correlation-corrected.json`：

- state `last_job_id` 是 `61a83c...`。
- state `status` 仍是 active。
- state `correlation_id` 是 null。
- existing `replace-failed-external-job --plan-only` 回
  `failed external replacement state identity mismatch`。

此外，該 seam 的 CLI 要求 `--error-code`，但本案 failed receipt 沒有
`error_code`。因此這不是可直接用既有 replacement seam 恢復的
`DATA_RESIDUE_ONLY`；要恢復需先有 bounded Repair 或新的正式 operator
entrypoint，不能手改 queue/state。

# Last success / first failing mechanism

- Last success：production promotion 本身在 retry1 完成到 `COMMITTED`，
  actor=23e，`rollback_required=false`；capacity gates 也 PASS。
- First failing mechanism：operator helper 嘗試補跑 target lane writer job 時，
  沒有使用正式 LaunchAgent env contract，導致 runner transport path 從
  production credential path 退到 CLI fallback。
- 23e 的 selector repair 成功：coordinator exact-run 從 8a 的 `selected=0`
  前進到 `i18n-new active=1 queued=1`。本 RCA 不否定 23e repair。

# Authoritative owner 與 boundary

- Queue/state authoritative owner：coordinator / runner durable queue state。
- Provider credential authoritative owner：正式 LaunchAgent installer 與
  credential pool env contract。
- Runtime identity authoritative owner：runtime manifest/barrier。
- Promotion boundary：promotion 只切 actor/manifest/stage，不保證 operator helper
  自動取得 LaunchAgent env，也不 realign installed live plist。
- Replacement boundary：failed external replacement seam 可處理 identity 完整、
  failure receipt 完整的 failed job；本案缺 correlation_id/error_code，因此不能
  直接當作 data residue 重排。

# why_not_less / why_not_more / do_not_absorb

- why_not_less：只說「重跑 runner」不夠，因為會再次用錯 entrypoint，且可能造成
  duplicate/ambiguous failed artifacts。
- why_not_more：不需要改 selector、promotion、publisher、provider 或手修
  queue/state；本次證據已定位到 operator entrypoint/env seam。
- do_not_absorb：不要吸收新 provider runner、第二套 queue repair、手動 state
  editor、泛用 retry loop、或把 LaunchAgent realign 與 content publication 混成一張
  Repair。

# 判定

不是 `DATA_RESIDUE_ONLY`。

需要唯一 bounded Repair，範圍應限於：

1. 提供正式、可驗證的 operator exact lane runner entrypoint，必須複用/驗證
   LaunchAgent credential pool / allocator / model-route env contract，並在缺 env
   時 fail closed，不落到 CLI fallback。
2. 或讓 formal runtime runner guard 在 production service label 下要求
   production transport env completeness。
3. 補 read-only/RED-capable test 或 harness：同一 target-shaped lane job 在缺
   credential env 時必須 BLOCKED before claim，不得產生 INVALID_RECEIPT failed
   artifact。
4. 另行處理既有 `61a83c...` failed artifact 的恢復 path；不得手改，需 bounded
   operator seam 支援 legacy null correlation / no-error-code INVALID_RECEIPT，或
   明確產生一次性 recovery card。

本 RCA 沒有 production mutation、沒有 retry、沒有 provider call、沒有 push、
promotion、deploy、publish、tag、gen06 或 manual state edit。
