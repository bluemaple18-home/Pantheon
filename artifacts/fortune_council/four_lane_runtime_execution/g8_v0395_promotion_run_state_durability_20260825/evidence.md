# V0395 promotion run state durability evidence

## Scope

- Base SHA：`345d9c3184856718254615b58b92655743a8d64a`。
- CodeGraph 先以任務語意查詢，定位 `PromotionRequest`、`_queue_identity_snapshot` 與 promotion 入口；active-run cleanup seam 未完整覆蓋後，依 Rule 21 bounded fallback 只讀 allowlist source/tests。
- 未操作 production runtime、launchctl、Publisher、模型、真實 queue/state、publish、tag、push 或公開網站。
- `tests/test_install_agy_gemini_coordinator_launchd.py` 在本 revision 不存在；installer 完整測試位於 `tests/test_agy_gemini_coordinator.py`。

## RED

等價可重現命令：

```bash
uv run pytest -q \
  tests/test_pantheon_content_runtime_promotion.py::test_apply_preserves_exact_active_run_queue \
  tests/test_pantheon_content_runtime_promotion.py::test_plan_rejects_dangling_preserved_run_before_runtime_mutation \
  tests/test_agy_gemini_coordinator.py::test_cycle_blocks_dangling_active_registry_before_automatic_sweeps \
  tests/test_agy_gemini_coordinator.py::test_installer_injects_one_shared_allocator_contract_into_coordinator_and_all_lanes
```

有效 RED 證據：

```text
promotion plan 缺 run_dir / run_tree_digest snapshot
promotion plan 未拒絕不存在的 preserved run_dir
coordinator 先執行 new/legacy sweeps，並未回傳 blocked receipt
installer --new-matrix-run-root 仍解析為 <actor>/.work/gsc-copy
```

## Root Fix

- installer 將 new/rewrite run root 固定為 `<queue-root>/gsc-copy`；不一致的 `PANTHEON_GSC_COPY_ROOT` override 在任何 launchd side effect 前拒絕。
- promotion 要求 preserved registry 的 `run_dir` 為 queue-owned durable root 的 canonical descendant，且實體目錄、`brief.json`、run identity 均一致；plan 保存 `run_tree_digest`，既有 apply/postcheck queue snapshot 同時驗證 promotion 前後無 drift。
- coordinator 在 lock 內、任何 automatic sweep/replacement identity 建立前驗證 normal active registry；dangling/missing brief/identity drift 回傳 `status=blocked` receipt，且不推進其他 run。
- 既有 failed external job replacement 帶 durable recovery metadata 的特殊路徑維持原契約，不改其 replacement 邏輯。

## GREEN

焦點 regression：

```text
6 passed in 3.25s
```

promotion 完整測試檔：

```bash
uv run pytest -q tests/test_pantheon_content_runtime_promotion.py
```

```text
30 passed in 9.22s
```

coordinator／installer 完整測試檔：

```bash
uv run pytest -q tests/test_agy_gemini_coordinator.py
```

```text
292 passed in 424.97s (0:07:04)
```

其他 gate：

```bash
bash -n scripts/install_agy_gemini_coordinator_launchd.sh
git diff --check
```

```text
PASS
```

本機實際使用既有 project `uv` environment 的 `<main-worktree>/.venv/bin/python` 執行 pytest；上列 `uv run` 為跨機等價入口。

## Baseline Finding

coordinator 首輪完整測試另揭露 6 個 publisher-reset cases 的 fake `launchctl print` 缺少 parser 已要求的 `gui/<uid>/<label> = { ... }` 外框。以乾淨 base SHA 暫存副本重跑單一 case，同樣失敗於 `publisher reset identity mismatch`，證明不是本卡 production diff 造成；只修正 allowlist test fixture，未修改 capacity guard 或 publisher reset production 邏輯。

## Residual Risk

- 本卡只使用 synthetic fixture；未執行 production promotion 或新 canary，依卡片契約留給主線另行驗收。
- coordinator 的 failed external job replacement durable recovery 是明確豁免；其既有專屬測試已在完整 coordinator 檔通過。
