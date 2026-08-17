---
id: EVIDENCE-PANTHEON-CONFIGURABLE-MODEL-ROUTE-REPAIR-1-20260817
status: green
type: repair-evidence
chain_id: PANTHEON-NEW-FLOW-PRODUCTION-PUBLISH-RECOVERY-20260817
scope: B-model-route
parent_candidate: 95485ab4921991e809a5414a579de8cc8bc97e2e
review_receipt: 3c3c4aa2bdeeb3e15d7a74e14728db0fbd8fe227
review_verdict: FINAL_REVIEW_NO_GO
---

# B. Model Route Repair-1 Evidence

## 修復契約

- Config：`config/agy_gemini_model_routes.v1.json`
- Schema version：`1`，且 JSON `true`／`false`、浮點數、字串與 `null` 均 fail closed。
- Canonical SHA-256：`781f243c541e4829ba1e5beebc41fec78bac196d258340faf4aae384dd5d9463`
- 同日 quota state 以 config digest、role、exact model 與 Pacific 次日零時為 identity；process restart 後仍跳過已全 slot quota-block 的 model，daily reset 才回首順位。
- Installer 以 digest-addressed staged config 保存 bytes、canonical path 與 digest；activate-only 在任何 live mutation 前驗證 staged config、receipt 與五份 Gemini plist identity。

## RED

```text
.venv/bin/python -m pytest -q tests/test_agy_seo_copy_pipeline.py::test_model_route_config_rejects_invalid_contract
2 failed, 8 passed
```

`schema_version=true` 與 `1.0` 被既有 `== 1` 判斷接受。

```text
.venv/bin/python -m pytest -q tests/test_agy_gemini_outbox.py -k 'same_day_route_state or all_models_quota_blocked'
2 failed
```

既有 client 沒有 durable route-state clock／storage contract，無法跨操作與 restart 保存 exact-model quota block。

```text
.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py -k 'staged_model_route_drift'
3 failed
```

既有 stage 未保存 model route config bytes／digest-addressed identity，bytes change、delete、symlink drift 均未在 activation 前被擋下。

## GREEN

```text
.venv/bin/python -m pytest -q tests/test_agy_seo_copy_pipeline.py::test_model_route_config_rejects_invalid_contract
10 passed in 0.05s

.venv/bin/python -m pytest -q tests/test_agy_gemini_outbox.py -k 'same_day_route_state or all_models_quota_blocked'
2 passed, 169 deselected in 0.05s

.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py -k 'staged_model_route_drift or installer_injects_one_shared_allocator'
5 passed, 182 deselected in 11.62s

.venv/bin/python -m pytest -q tests/test_agy_gemini_allocator.py tests/test_agy_gemini_outbox.py tests/test_agy_seo_copy_pipeline.py
330 passed in 117.46s

.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py -k 'installer'
26 passed, 161 deselected in 34.73s

bash -n scripts/install_agy_gemini_coordinator_launchd.sh
PASS

.venv/bin/python -m py_compile scripts/agy_gemini_allocator.py scripts/agy_gemini_outbox.py scripts/agy_seo_copy_pipeline.py
PASS

git diff --check
PASS
```

涵蓋：primary 三 slots 全 `API_QUOTA` 後持久化 block；後續不同操作與 restart 直接使用同日可用後順位；所有 ordered models blocked 時 enqueue 前 fail closed；daily reset 回 role primary；既有 429／503 不 downgrade；staged bytes／delete／symlink drift 均在 mutation log 產生前 NO-GO；schema bool／float fail closed。

## Scope receipt

- `scripts/pantheon_content_runtime_manifest.py` 與 `tests/test_pantheon_content_runtime_manifest.py`：無 diff。
- 未碰 A. Queue Repair source／tests／evidence。
- 未碰 production runtime、production queue、launchd live state、network、push、merge、tag。
