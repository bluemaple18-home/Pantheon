# Configurable Model Route Repair-1 Re-review Receipt

card_id: CARD-PANTHEON-CONFIGURABLE-MODEL-ROUTE-REVIEW-20260817
chain_id: PANTHEON-NEW-FLOW-PRODUCTION-PUBLISH-RECOVERY-20260817
reviewer_identity: B Reviewer（本 chain 原唯一 Reviewer）
cycle: repair-1-re-review
model: gpt-5.6-sol
reasoning: high
parent_candidate: 95485ab4921991e809a5414a579de8cc8bc97e2e
prior_review_receipt: 3c3c4aa2bdeeb3e15d7a74e14728db0fbd8fe227
fixed_candidate: 28e83d94f5f6320f02c3c1eaf039c3f09a7a9fbf
repair_evidence: artifacts/fortune_council/four_lane_runtime_execution/configurable_model_route_repair_20260817/repair-1-evidence.md

## Scope

- 回原唯一 Reviewer task，完整重讀 Repair-1 diff、evidence、三個原 findings、targeted tests 與 installer activation lifecycle。
- Repair diff 僅修改 B model route source、tests、installer 與 Repair-1 evidence。
- `scripts/pantheon_content_runtime_manifest.py`、`tests/test_pantheon_content_runtime_manifest.py`、A queue preservation source/tests/evidence 均無 diff。
- 未修改 fixed candidate、source、tests、config、runtime manifest、production runtime、production queue、launchd live state、network、remote、tag 或 merge state。

## Initial Gate

- Reviewer worktree 起始 HEAD：`3c3c4aa2bdeeb3e15d7a74e14728db0fbd8fe227`；clean。
- Fixed candidate 可解析，且 parent candidate `95485ab4921991e809a5414a579de8cc8bc97e2e` 是其 ancestor。
- Candidate 驗證期間使用 clean detached HEAD；完成後已回原 Reviewer receipt HEAD。

## CodeGraph

- `codegraph_context` 回傳「CodeGraph not initialized」。依專案規則改用 fixed SHA diff、candidate file bodies、限域 `rg` 與 targeted tests。

## Verification

Targeted quota persistence／all-blocked：

```text
<pantheon-primary-repo>/.venv/bin/python -m pytest -q tests/test_agy_gemini_outbox.py -k 'same_day_route_state or all_models_quota_blocked'
2 passed, 179 deselected in 0.06s
```

Targeted strict schema：

```text
<pantheon-primary-repo>/.venv/bin/python -m pytest -q tests/test_agy_seo_copy_pipeline.py::test_model_route_config_rejects_invalid_contract
10 passed in 0.04s
```

Targeted installer identity/drift：

```text
<pantheon-primary-repo>/.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py -k 'staged_model_route_drift or installer_injects_one_shared_allocator'
5 passed, 182 deselected in 11.03s
```

Claimed routing suite：

```text
<pantheon-primary-repo>/.venv/bin/python -m pytest -q tests/test_agy_gemini_allocator.py tests/test_agy_gemini_outbox.py tests/test_agy_seo_copy_pipeline.py
330 passed in 121.30s
```

Claimed installer suite：

```text
<pantheon-primary-repo>/.venv/bin/python -m pytest -q tests/test_agy_gemini_coordinator.py -k installer
26 passed, 161 deselected in 33.69s
```

Additional gates：

```text
bash -n scripts/install_agy_gemini_coordinator_launchd.sh
<pantheon-primary-repo>/.venv/bin/python -m py_compile scripts/agy_gemini_allocator.py scripts/agy_gemini_outbox.py scripts/agy_seo_copy_pipeline.py
git diff --check 95485ab4921991e809a5414a579de8cc8bc97e2e..28e83d94f5f6320f02c3c1eaf039c3f09a7a9fbf
```

Result：全部 passed。

Additional diagnostic：`test_four_lane_activation_success_commits_matching_private_stage` 在本 review worktree 使用 shared Pantheon interpreter 時，先於相關 postcondition 因 fixture `uv_executable mismatch` 失敗；未用此環境性失敗判 candidate。該 test source 本身明確要求 successful activation 後 `stage_dir` 不存在，與 fixed candidate 的 live plist path形成可直接判定的 lifecycle 衝突。

## Original Findings Re-review

### 1. Same-day exact-model quota block persistence

Status：CLOSED。

- Durable state identity 綁定 config digest、role、exact model 與 Pacific reset timestamp。
- 後續不同操作與新 client/process restart 會跳過同日 blocked primary。
- 所有 ordered models blocked 時，在新 request enqueue 前 fail closed。
- Reset timestamp 到期後回首順位；429／503／`API_RATE_LIMITED` 不寫 quota block、也不 downgrade。
- Targeted 與 330 suite 通過。

### 2. Installer staged/live config identity

Status：OPEN；仍有 P1。

- Repair 已補 staged bytes、digest-addressed filename、digest/path receipts、五份 plist identity，以及 activate-only bytes/delete/symlink drift pre-mutation rejection。
- 但 active config 的生命週期仍綁在 temporary stage，successful activation 後會被 cleanup 刪除；見 finding。

### 3. Strict schema version type

Status：CLOSED。

- Loader 先要求 `type(schema_version) is int`，再比較 exact supported version。
- `true`、`false`、float、string、`null` 負向 tests 通過。

### 4. B scope

Status：CLOSED。

- 未碰 A、runtime manifest source/tests 或 production state。

## Findings

- [P1] Successful activation 刪除五份 live plist 仍引用的 digest-addressed config - `scripts/install_agy_gemini_coordinator_launchd.sh:764`
  - Category: correctness / installer lifecycle / production liveness。
  - Trigger: `--activate` 或 `--activate-only` 成功完成 bootstrap、aggregate validation 與 barrier activation。
  - Evidence: coordinator 與四 lanes 在 lines 257、303 把 `AGY_GEMINI_MODEL_ROUTE_CONFIG` 設為 `${STAGE_DIR}/model-route-config-${digest}.json`；line 764 在 successful activation 無條件 `rm -rf "${STAGE_DIR}"`。既有 successful activation tests也明確 assert stage 不存在。使用者已獨立確認此 blocker。
  - Risk: live launchd plists 保留一個成功 activation 後不存在的 config path。`model_route_config_from_environment()` 每次 formal pipeline tick 都以 `resolve(strict=True)` 重讀該 path；stage cleanup 後下一次 Writer／Reviewer admission會以「model route config is unavailable」fail closed，四 lanes 無法持續工作。
  - Fix: 把 digest-addressed config 安裝到不受 stage cleanup 影響的 private immutable config store，讓 staged 與 live plists指向該 durable path；activation 前驗證 bytes/path/digest 與五份 plist identity。GC 僅能刪除未被任何 live／staged plist引用的舊 digest，且須在 activation 成功後另行安全處理。
  - Validation gap: 新增 successful `--activate` 與 `--activate-only` tests；完成 stage cleanup 後解析五份 live plist，確認同一 config path仍存在、不是 symlink、mode/bytes/canonical digest正確，並用其 environment 成功呼叫 public `model_route_config_from_environment()`。保留現有 bytes/delete/symlink pre-mutation negatives。
  - Confidence: certain；source lifecycle 是同一條 successful path 的直接必然結果，且使用者已確認。

## Final Verdict

FINAL_REVIEW_NO_GO

Reason: quota persistence 與 strict schema findings 已關閉，但 installer 的 active digest-addressed config 仍位於 successful activation 後被刪除的 stage，留下未解 P1 production liveness blocker。
