# CARD-PANTHEON-MODEL-ROUTE-LITE-REPAIR-20260825 RESULT

status: DELIVERED_CANDIDATE
card_id: CARD-PANTHEON-MODEL-ROUTE-LITE-REPAIR-20260825
dispatch_key: v1:ecfe5970adfedcb1d0edd6154de5eb8037758bc63d37c22e7806784c722b1d11
activation_token_received: act-v1:d0125fb015f42041f17d446ea71f81d2cf12207f8fe89e647c44426616812a02
thread_id: 01a0374e-7b37-7f21-b911-984089be8509
source_thread_id: 01a034b0-a14a-7562-bc18-a014d47bb3ad

## 結論

已交付候選修正。正式 Writer / Reviewer route 現在鎖定官方 stable Gemini API Lite model ID：

- Writer: `gemini-3.5-flash-lite`
- Reviewer: `gemini-3.1-flash-lite`

本修正不再把 `agy-1.1.3 models` inventory 當作兩個 Lite role 的能力權威；Antigravity CLI 未曝光 Lite 時會被分類為 CLI inventory / transport 不支援，而不是 Gemini API model 不存在。

## Source Decision

CodeGraph 在 source decision 前已查詢既有 seam：

- `codegraph_status`: ready；582 indexed files, 6925 nodes, 15331 edges。
- `codegraph_search(GeminiClient)`: 定位 `scripts/agy_seo_copy_pipeline.py:2603`。
- `codegraph_search(GEMINI_ENDPOINT)` / `generativelanguage`: 定位既有 direct Gemini API `generateContent` endpoint。
- `codegraph_search(credential)`: 定位 `scripts/agy_gemini_runner.py` 的 production credential pool seam。
- `codegraph_search(OutboxGeminiClient)`: 定位 `scripts/agy_gemini_outbox.py` 的 queue/outbox route seam。

依主線已驗證的 Google 官方文件裁決：

- `gemini-3.5-flash-lite` 是 stable Gemini API model code。
- `gemini-3.1-flash-lite` 是 stable Gemini API model code。
- `gemini-3.1-flash-lite-preview` 已 shutdown，不可使用。
- Antigravity Managed Agent supported list 有 `gemini-3.5-flash-lite`，但未列 `gemini-3.1-flash-lite`，所以本修正不把 Managed Agent/CLI 當 Reviewer transport。

## RED

修正前 tracked route 違反固定 Lite 契約：

- Writer: `gemini-3.5-flash`
- Reviewer: `gemini-3.1-pro`

修正前 `validate_antigravity_cli_capabilities()` 將 route ID 綁到 `ANTIGRAVITY_MODEL_LABELS`；Lite label 不存在時會被混同為 model unavailable。

既有 CLI 探測上限已於前一輪用完，本輪未再次呼叫 `agy models` 或 Lite smoke。

## GREEN

本候選修正：

- 將 `config/agy_gemini_model_routes.v1.json` 改為唯一 Lite role：
  - Writer `gemini-3.5-flash-lite`
  - Reviewer `gemini-3.1-flash-lite`
- 將 `GeminiClient.from_environment()` 預設 transport 改為 direct Gemini API。
- 保留 explicit legacy CLI transport，但當正式 Lite route 進入 CLI transport 時 fail closed，且不啟動 CLI process。
- 新增 `validate_gemini_api_model_capabilities()`，將正式能力 gate 鎖定在官方 stable Lite API IDs。
- 更新 CLI capability diagnostic：Antigravity inventory 未曝光 route 時回報 `Antigravity CLI inventory does not expose ... route`，不再誤報為 API model absence。
- 測試覆蓋 exact Lite role、direct API default、CLI/Lite fail closed、legacy CLI closed diagnostics。

## Changed Files

- `config/agy_gemini_model_routes.v1.json`
- `scripts/agy_seo_copy_pipeline.py`
- `tests/test_agy_seo_copy_pipeline.py`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-MODEL-ROUTE-LITE-REPAIR-20260825-RESULT.md`

未修改 installer、runtime manifest、LaunchAgents、production actor、queue/state、Publisher、promotion、activation、正式 job、tag 或 push path。

## Verification

- `.venv/bin/python -m pytest -q tests/test_agy_seo_copy_pipeline.py -k 'model_route_config or gemini_api_model_capabilities or antigravity_cli_capability or antigravity_cli_transport or environment_defaults_to_direct or cli_transport_exposes'`: PASS, 23 passed / 141 deselected。
- `.venv/bin/python -m pytest -q tests/test_agy_gemini_outbox.py -k 'route or quota or model or transient or failure_category'`: PASS, 14 passed / 157 deselected。
- `.venv/bin/python -m pytest -q tests/test_agy_gemini_v4_broker.py -k 'agy_profile or model_label'`: PASS, 6 passed / 36 deselected。
- `git diff --check`: PASS。
- `rg -n "\\[DBG-" scripts tests`: PASS, no matches。
- `python3 -m json.tool config/agy_gemini_model_routes.v1.json`: PASS。

## 剩餘風險

- 本候選沒有送出任何 production Gemini request；direct API model availability 依官方 stable model ID 與既有 API transport/credential seam 判定，未消耗 production quota。
- `gemini-3.1-flash-lite` 未列於 Antigravity Managed Agent supported list，因此 Reviewer 不應改走 Managed Agent/CLI。
- 若未來 production runtime 顯式設定 `AGY_GEMINI_TRANSPORT=cli`，Lite route 會 fail closed，需要 runtime 環境改用 direct API transport。
