# Configurable Model Route Review Receipt

card_id: CARD-PANTHEON-CONFIGURABLE-MODEL-ROUTE-REVIEW-20260817
chain_id: PANTHEON-NEW-FLOW-PRODUCTION-PUBLISH-RECOVERY-20260817
reviewer_identity: B Reviewer（本 chain 唯一 Reviewer）
model: gpt-5.6-sol
reasoning: high
review_head: d4e5b5f2aa5c625353acc9c3dd5a6f79f53f32a0
base_sha: b81ed94a80d8d9808356ac959aaaba387d57c19e
reviewed_candidate_sha: 95485ab4921991e809a5414a579de8cc8bc97e2e
diff: b81ed94a80d8d9808356ac959aaaba387d57c19e..95485ab4921991e809a5414a579de8cc8bc97e2e
claimed_config_digest: 781f243c541e4829ba1e5beebc41fec78bac196d258340faf4aae384dd5d9463
verified_config_digest: 781f243c541e4829ba1e5beebc41fec78bac196d258340faf4aae384dd5d9463

## Scope

- 完整審查 fixed candidate diff、implementation evidence、route config、outbox client、SEO pipeline loader/direct client、coordinator installer 與三組受影響 tests。
- current HEAD 相對 candidate 只有正式 review card；candidate source、tests、config 與 evidence bytes 未改。
- 未修改 candidate、source、tests、route config、Queue Repair A、runtime queue、production、launchd live state、network、remote、tag 或 merge state。
- synthetic repro 僅寫入 `/private/tmp`。

## Initial Gate

- HEAD：`d4e5b5f2aa5c625353acc9c3dd5a6f79f53f32a0`，符合派工契約。
- Worktree：clean。
- Card commit 與內容：存在且符合 chain、model、reasoning、fixed candidate、ownership 與 forbidden scope。
- Candidate ancestry：`95485ab4921991e809a5414a579de8cc8bc97e2e` 是 review HEAD 的直接父提交。

## CodeGraph

- `codegraph_context` 回傳「CodeGraph not initialized」。依專案規則改用 fixed SHA diff、限域 `rg`、candidate file bodies 與 targeted tests；未做全 repo 掃描。

## Verification

Command：

```text
<pantheon-primary-repo>/.venv/bin/python -m pytest -q tests/test_agy_gemini_allocator.py tests/test_agy_gemini_outbox.py tests/test_agy_seo_copy_pipeline.py
```

Result：

```text
323 passed in 120.05s
```

Command：

```text
<pantheon-primary-repo>/.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py -k installer
```

Result：

```text
23 passed, 161 deselected in 26.64s
```

Additional gates：

```text
bash -n scripts/install_agy_gemini_coordinator_launchd.sh
<pantheon-primary-repo>/.venv/bin/python -m py_compile scripts/agy_gemini_allocator.py scripts/agy_gemini_outbox.py scripts/agy_seo_copy_pipeline.py scripts/pantheon_content_runtime_manifest.py
git diff --check b81ed94a80d8d9808356ac959aaaba387d57c19e..95485ab4921991e809a5414a579de8cc8bc97e2e
```

Result：全部 passed。

## Independent Reproduction

### Same-day fallback regression

在 synthetic queue 讓 Writer primary 的三個 exact-slot request 都收到 `API_QUOTA`，並讓第二順位成功；同一 client 隨即提交另一個不同 prompt。

Result：

```json
{
  "active_after_fallback": "gemini-3.5-flash",
  "expected_same_day_model": "gemini-3.5-flash",
  "first_result": {"ok": true},
  "regression": true,
  "second_pending_model": "gemini-3.5-flash-lite"
}
```

第二個操作重新排 primary；當正式 allocator 已把該 exact model 的三個 slots block 時，runner 只回 `quota_blocked` 並保留 outbox request，不產生 client 可消費的 failure receipt，因此 route 無法前進。

### Schema version type regression

以 `{"schema_version": true, ...}` 呼叫 public `load_model_route_config()`。

Result：config 被接受，回傳 `schema_version == 1`；未 fail closed。

## Findings

- [P1] 同日 fallback 後下一操作重新從已全封鎖 primary 排隊，route 會停住 - `scripts/agy_gemini_outbox.py:665`
  - Category: correctness / quota routing / production liveness。
  - Trigger: 某 role 的 primary exact model 已由三個 production slots 回報 `API_QUOTA`，client 成功選到下一順位；在 quota reset 前，同一 role 執行另一個不同 prompt。process restart 後亦相同，因 client 每次重建且沒有 durable route admission state。
  - Risk: `generate_json()` 每次都從 `_model_routes[role][0]` 建立 candidates，沒有以 `_active_models[role]` 或 allocator 的 durable exact-model block 狀態決定起點。runner 在三 slots 已 block 時於 `scripts/agy_gemini_runner.py:1179` 回 `quota_blocked`，不 claim request、也不寫 failure receipt。pipeline 之後永遠只看到 `ExternalJobPending`，無法跳至第二／第三順位；同日後續 Writer／Reviewer、repair 或 lane run 會停到 daily reset。
  - Fix: 讓 route admission 與 allocator 的 durable `(slot, exact model, blocked_until)` 狀態整合；已全封鎖 model 應產生可驗證、封閉且不消耗 provider attempt 的 route-admission 結果，或由 client 讀取可信的 durable routing state後跳過。fallback 選擇須跨 tick／process restart 保存，只有 allocator clock 證明 daily block 已到期才回首順位。
  - Validation gap: 新增 public integration test：第一個不同操作耗盡 primary 三 slots 並成功 fallback；第二個操作同日、以及重啟新 client 後，都直接跳過 blocked primary；Pacific daily reset 後才回 primary。另測中間 model 預先全 block 與全 route blocked。
  - Confidence: high；fixed candidate synthetic repro 可重現，且 runner denial path 明確不產生 failure receipt。

- [P1] Staged plist 未綁定 immutable route config identity，activate-only 可使用 stale digest 啟動 - `scripts/install_agy_gemini_coordinator_launchd.sh:128`
  - Category: installer / TOCTOU / production activation safety。
  - Trigger: 執行 `--install` 後、`--activate-only` 前，source checkout 的 `config/agy_gemini_model_routes.v1.json` 內容被更新、替換或移除，但 runtime manifest digest／generation 不變。
  - Risk: 五個 staged plists 在 lines 245-292 保存 mutable source-checkout absolute path 與當時 digest；stage receipt 在 lines 327-345 只保存／比較 runtime manifest digest 和 generation，沒有 route config digest 或 frozen config bytes。activate-only 雖重新讀目前 config，卻不把新 identity 與 staged plists 比對，仍會進入 live launchctl mutation。staged plist 隨後以舊 expected digest 指向新內容，formal runtime 才失敗，造成 activation/readiness failure 與服務 bootout/rollback，而不是 mutation 前 fail closed。
  - Fix: 將 canonical route config 複製到 generation-scoped immutable private stage/live path，stage receipt 綁定 path、canonical digest 與五個 plist identities；任何 current/staged path 或 digest mismatch 必須在 aggregate activation 與任何 launchctl mutation前拒絕。可替代地把 route config digest 納入 runtime manifest generation，但仍須避免 plist 指向 mutable checkout。
  - Validation gap: 新增 installer 測試：stage 後改 config bytes、換 symlink、刪檔，再執行 activate-only；三種情況都應在 launchctl mutation log 為空時拒絕。另驗證 coordinator 與四 lanes 的 staged/live path/digest 完全一致。
  - Confidence: high；fixed diff 明確把 mutable checkout path寫入 plists，且 activation stage guard 沒有 route identity。

- [P2] JSON boolean `true` 被當成 schema version 1 接受 - `scripts/agy_seo_copy_pipeline.py:54`
  - Category: schema validation / fail-closed。
  - Trigger: route config 的 `schema_version` 是 JSON boolean `true`。
  - Risk: Python 的 `True == 1`，目前只用不等比較，因而把錯誤 JSON type 規範化為 `ModelRouteConfig(schema_version=1)`。這違反 unknown/type/version fail-closed，並讓 canonical digest 表示 boolean payload、runtime object 卻聲稱 integer v1，增加 migration 與 identity 判定歧義。
  - Fix: 在版本比較前要求 `type(payload.get("schema_version")) is int`，並保持 exact supported version check。
  - Validation gap: 補 `true`、`false`、`1.0`、`"1"`、`null` 負向測試。
  - Confidence: high；public loader synthetic repro 已接受 `true`。

## Axes Result

- 單一 versioned config、ordered route、claimed canonical digest：部分 pass；exact IDs 已移出 Python，但 schema type fail-closed 失敗。
- `(slot, exact model)` quota identity、Flash/Flash-Lite 隔離：allocator 實作與既有 tests pass。
- 三 slots quota 後前進／中間 model 跳過：預建 failure receipts 的 unit tests pass；已由 allocator 預先全 block 的 public flow fail，形成 P1。
- 429／503／`API_RATE_LIMITED` bounded retry 且不 downgrade：pass。
- daily reset 回首順位：未被新增 test 實證；該 test 的日期只存在未被讀取的 inbox timestamp，且實際行為在 reset 前就回 primary，形成 P1。
- Writer／Reviewer active exact model collision：順序執行的 runtime filter可 fail closed；新增 collision test 沒有建立真正 fallback overlap，仍需回歸測試。
- 四 lanes config path/digest 一致：staged plist unit assertion pass；immutable staged/live identity 與 TOCTOU fail-closed 失敗。
- Queue Repair A、runtime queue 與 production scope：fixed diff 未修改。

## Final Verdict

FINAL_REVIEW_NO_GO

Reason: fixed candidate 有兩項未解 P1：同日 quota fallback 後續操作會卡在已全封鎖 primary；installer 的 staged/live route config identity 未在任何 live mutation 前鎖定。P2 schema version type bug列入 repair backlog。
