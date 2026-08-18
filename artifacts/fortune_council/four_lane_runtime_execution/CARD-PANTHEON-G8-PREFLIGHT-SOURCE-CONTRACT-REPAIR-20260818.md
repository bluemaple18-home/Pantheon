---
id: CARD-PANTHEON-G8-PREFLIGHT-SOURCE-CONTRACT-REPAIR-20260818
chain_id: PANTHEON-G8-PREFLIGHT-SOURCE-CONTRACT-REPAIR-20260818
parent_card_id: CARD-PANTHEON-G8-FOUR-LANE-PRODUCTION-CANARY-20260818
role: implementation
cycle: 1
status: ready
type: source_contract_repair
thickness: standard
risk: medium
model: gpt-5.6-terra
reasoning: medium
model_reason: 四個可重現 source contract 已由 G8 preflight 鎖定，禁止 production mutation，屬 bounded standard repair；以 Terra medium 節省成本，不使用 Sol。
ownership:
  - scripts/agy_gemini_coordinator.py
  - scripts/pantheon_content_capability_probe.py
  - scripts/pantheon_content_runtime_manifest.py
  - scripts/pantheon_runtime_activation.py
  - scripts/pantheon_content_actor_recovery.py
  - tests/test_agy_gemini_coordinator.py
  - tests/test_pantheon_content_capability_probe.py
  - tests/test_pantheon_runtime_activation.py
  - tests/test_pantheon_content_actor_recovery.py
  - .work/CARD-PANTHEON-G8-PREFLIGHT-SOURCE-CONTRACT-REPAIR-20260818/**
forbidden_scope:
  - production、push、tag、publish、LaunchAgent staging/activation
  - 手改 queue、transaction、plist、barrier、runtime live state 或既有 G8 evidence
  - 放寬 fail-closed gate、刪除 assertion、skip/xfail、改 fixture 掩蓋 source regression
  - Writer、lane routing、內容生成、SEO 或與四類紅燈無關的重構
verification:
  - canonical four-test command 先可重現 RED，修後 4 passed
  - G8 broader 16-file source suite 604 tests全部通過
  - 無 DBG 殘留，git diff --check通過
  - candidate commit只含allowlist且worktree clean
evidence_path: .work/CARD-PANTHEON-G8-PREFLIGHT-SOURCE-CONTRACT-REPAIR-20260818/
---

# G8 preflight source contract repair

## 工作名稱 → 正在做什麼 → 現在狀態

修復 G8 preflight 四類 source contract → 以最小根因修復讓 canonical 與 broader suite 轉綠 → `READY`

## Root Question

能否不放寬任何 production fail-closed 契約，只修正 APF-004 backlog、capability probe、Publisher runtime manifest 與 actor recovery 四個接縫，使 G8 source gate 全綠？

## 已鎖定證據

- G8 source：`6a7b445861589575a5783616b174f7e834859ace`。
- readiness/capability：`READY`；storage/capacity：`PASS`。
- broader suite：`11 failed, 593 passed, 1 warning`。
- canonical `uv run --frozen` 四測試重跑：`4 failed`。
- G8 evidence commit：`9f9832ba8bd8d0ed776197cdb684d7d9f5861c5d`；不得依賴其 worktree 路徑，失敗名稱已完整寫入本卡。
- production mutation、push、tag、publish 均為零。

## 需求與成功準則

- `FR-SCR-01`：APF-004 create-run adapter 必須以 repository authority 正確解析 new article matrix backlog，plan-only 仍 deterministic、zero-write。
- `FR-SCR-02`：正式 capability probe 的正向鏈必須 `PASS`，corrupted handoff 仍 fail-closed `BLOCKED`。
- `FR-SCR-03`：Publisher formal activation manifest 必須完整攜帶並驗證 `uv_executable`，不得削弱 hardened environment identity。
- `FR-SCR-04`：actor recovery 必須在空 target 與 exact restore 上完成正式 installer preflight；preflight 失敗仍不得留下 half-ready actor。
- `SC-SCR-01`：canonical 四測試 `4 passed`。
- `SC-SCR-02`：G8 16-file broader suite `604 passed`，不得 skip/xfail。
- `SC-SCR-03`：無 production mutation、無 scope 外 diff、candidate worktree clean。

## 執行切片與 blocking edges

### `SLICE-SCR-RED-LOCALIZE`

- `traces_to`: `FR-SCR-01`, `FR-SCR-02`, `FR-SCR-03`, `FR-SCR-04`
- 先執行下方 canonical 四測試，證明同症狀 RED；逐群建立可證偽假說，一次只改一個變數。
- 若任一失敗只剩環境／fixture 問題而非目標症狀，停止並交 exact evidence，不猜修。

### `SLICE-SCR-MINIMAL-FIX`

- `traces_to`: `FR-SCR-01`, `FR-SCR-02`, `FR-SCR-03`, `FR-SCR-04`, `SC-SCR-01`
- 被 `SLICE-SCR-RED-LOCALIZE` 阻擋。
- 依序修 APF-004、probe、manifest/activation、actor recovery；每群原測試轉綠才進下一群。
- 不新增平行 workflow、fallback path、retry 或第二套 authority。

### `SLICE-SCR-REGRESSION`

- `traces_to`: `SC-SCR-01`, `SC-SCR-02`, `SC-SCR-03`
- 被 `SLICE-SCR-MINIMAL-FIX` 阻擋。
- 重跑 canonical 四測試、G8 broader 16-file suite、`rg -n '\\[DBG-' scripts tests` 與 `git diff --check`。
- 保存 root-cause mapping、RED/GREEN commands、changed files與candidate SHA。

## Canonical RED/GREEN command

```bash
cd <repo-root>
uv run --frozen python -m pytest -q -p no:cacheprovider \
  tests/test_agy_gemini_coordinator.py::test_apf_004_single_create_only_adapter_plan_only_is_deterministic_and_zero_write \
  tests/test_pantheon_content_capability_probe.py::test_one_formal_probe_emits_machine_correlated_positive_chain \
  tests/test_pantheon_runtime_activation.py::test_activation_token_allows_seven_matching_services_before_io \
  tests/test_pantheon_content_actor_recovery.py::test_same_recovery_entrypoint_preflights_and_restores_exact_actor
```

## Broader regression command

```bash
cd <repo-root>
uv run --frozen python -m pytest -q -p no:cacheprovider \
  tests/test_pantheon_content_capacity_guard.py \
  tests/test_pantheon_content_runtime_manifest.py \
  tests/test_pantheon_content_runtime_promotion.py \
  tests/test_agy_gemini_coordinator.py \
  tests/test_agy_content_publisher.py \
  tests/test_pantheon_writer_vnext_runtime_activation_readiness.py \
  tests/test_pantheon_writer_vnext_runtime_activation_capacity.py \
  tests/test_pantheon_writer_vnext_runtime_activation_e2e.py \
  tests/test_pantheon_content_capability_receipt.py \
  tests/test_pantheon_content_capability_probe.py \
  tests/test_agy_gemini_coordinator_capability_receipt.py \
  tests/test_agy_content_publisher_capability_receipt.py \
  tests/test_pantheon_runtime_activation.py \
  tests/test_pantheon_runtime_fs_authority.py \
  tests/test_prepare_pantheon_canary_actor.py \
  tests/test_pantheon_content_actor_recovery.py
```

## Exact failure inventory

- APF-004：5 tests；代表錯誤 `create-run adapter new article is not in matrix backlog`。
- Capability probe：2 tests；正向 expected `PASS` actual `BLOCKED`，且 corrupted-handoff 邊界需保留。
- Runtime activation：1 test；`formal publisher uv_executable is required`。
- Actor recovery：3 tests；正式 installer preflight 失敗與 half-ready cleanup 契約。

## 停損與交付

- 同一假說連續三次仍 RED：停止，不做第四次補丁。
- 需要改 allowlist、production state 或放寬 fail-closed 契約：`BLOCKED / SCOPE_EXPANSION`。
- 交付只能是 `DELIVERED_CANDIDATE` 或帶 exact evidence 的 `BLOCKED`；不得自行 push、整合或宣稱 production 可用。
- Final 必須列 root cause mapping、完整 changed files、canonical與broader結果、candidate commit SHA、worktree clean。
