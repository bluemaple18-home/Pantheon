---
id: EVIDENCE-PANTHEON-CONFIGURABLE-MODEL-ROUTE-REPAIR-20260817
status: green
type: implementation-evidence
chain_id: PANTHEON-NEW-FLOW-PRODUCTION-PUBLISH-RECOVERY-20260817
scope: B-model-route
---

# B. Configurable Model Route Repair Evidence

## 契約

- Config：`config/agy_gemini_model_routes.v1.json`
- Schema version：`1`
- Canonical SHA-256：`781f243c541e4829ba1e5beebc41fec78bac196d258340faf4aae384dd5d9463`
- Writer ordered route：`gemini-3.5-flash-lite` → `gemini-3.5-flash` → `gemini-2.5-flash`
- Reviewer ordered route：`gemini-3.1-flash-lite` → `gemini-2.5-flash-lite`
- Consumers：SEO pipeline loader／direct client、outbox／四 lane runner、coordinator installer staged plist。

## RED

Command：

```text
.venv/bin/python -m pytest -q tests/test_agy_seo_copy_pipeline.py tests/test_pantheon_content_runtime_manifest.py -k 'model_route_config'
```

Result：`7 failed, 190 deselected`；缺少 route loader、schema／digest validation 與 config identity。收到 scope override 後，runtime manifest 方向已完整撤除，後續 RED／GREEN 僅保留 B 範圍。

## GREEN

```text
.venv/bin/python -m pytest -q tests/test_agy_gemini_allocator.py tests/test_agy_gemini_outbox.py tests/test_agy_seo_copy_pipeline.py
323 passed in 116.71s

.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py -k 'installer'
23 passed, 161 deselected in 25.75s

bash -n scripts/install_agy_gemini_coordinator_launchd.sh
PASS

.venv/bin/python -m py_compile scripts/agy_gemini_allocator.py scripts/agy_gemini_outbox.py scripts/agy_seo_copy_pipeline.py scripts/pantheon_content_runtime_manifest.py
PASS（runtime manifest 僅編譯驗證，無 diff）

git diff --check
PASS
```

涵蓋：config schema／安全 ID／非空 route／ordered duplicate／role primary collision／canonical digest；exact-model 三 slot `API_QUOTA` 才前進；中間 model 全阻擋後跳下一順位；Flash／Flash-Lite quota identity 隔離；429／503 不 downgrade；quota reset 後回首順位；四 lane 與 coordinator 保存同一 config path／digest；環境 model/config drift fail closed。

## Scope receipt

- `scripts/pantheon_content_runtime_manifest.py`：無 diff。
- `tests/test_pantheon_content_runtime_manifest.py`：無 diff。
- 未碰 Queue Repair A source／tests／evidence。
- 未碰 production runtime、production queue、launchd live state、network、push、merge、tag。
