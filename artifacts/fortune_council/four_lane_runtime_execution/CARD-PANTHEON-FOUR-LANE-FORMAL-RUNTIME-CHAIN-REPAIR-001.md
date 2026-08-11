---
card_id: CARD-PANTHEON-FOUR-LANE-FORMAL-RUNTIME-CHAIN-REPAIR-001
status: REPAIR_READY_FOR_REREVIEW
execution_authorized: true
production_authorized: false
formal_thread_id: 019feaaa-54a5-7741-83c9-187e0cce510b
dispatch_key: v1:9586578d7e2501488905c3d1f9a83a3099cb71be351c6ab12f14340bcbb44a58
activation_status: BOUND
activation_token: act-v1:321dfd851592339062c6bcd57e38c458c9d9b17e5fa02e5a3c86c289735d7c75
chain_id: PANTHEON-FOUR-LANE-FORMAL-RUNTIME-CHAIN
role: repair
cycle: 1
finding_ids:
  - PANTHEON-FORMAL-RUNTIME-001
required_base_ref: codex/four-lane-formal-runtime-repair-1-source-20260810
required_base_sha: 6c57f3d9a47a76704acf4f0cfdf5522f48a7685d
reviewed_candidate_sha: c61491e748acad43e44e73f7eabbc320dcbaa532
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 修復雖限制兩個 source/test 檔，但同時涉及正式 Publisher transaction/release public boundary、無副作用 dry-run 與可信 invocation evidence，屬高風險契約修復。
provider_boundary: Codex-only；禁止 Claude Code、Gemini 或其他外部 provider
subagent_decision: NOT_ELIGIBLE
subagent_reason: 可修改程式／測試只有 2 個檔、單一 bounded finding、預期一輪完成，不符合安全委派的 8 檔／3 模組／多輪門檻。
traces_to:
  - FR-001
  - SC-001
allowlist:
  - scripts/agy_content_publisher.py
  - tests/test_pantheon_content_capability_probe.py
  - .ai/codex_task_four_lane_formal_runtime_chain_repair_001.md
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-FOUR-LANE-FORMAL-RUNTIME-CHAIN-REPAIR-001.md
  - artifacts/fortune_council/four_lane_runtime_execution/repair/formal_runtime_chain_repair_001/**
forbidden_scope:
  - scripts/pantheon_content_capability_adapter.py
  - 其他 production source、installer、plist、queue/state schema 或 runtime topology
  - 修補 P2 PANTHEON-FORMAL-RUNTIME-002／003
  - merge、push、deploy、production canary、launchctl、正式 queue/state/git mutation
  - hidden agent、子代理、外部 provider、full-auto、sandbox bypass
---

# 修復正式 Publisher capability 呼叫鏈

## 工作名稱 → 正在做什麼 → 現在狀態

- 工作名稱：修復正式 Publisher capability 呼叫鏈
- 正在做什麼：只關閉 `PANTHEON-FORMAL-RUNTIME-001`，讓 capability probe 的 publish／transaction／tag／push 命中正式 production public boundary，且保持零正式副作用。
- 現在狀態：REPAIR_READY_FOR_REREVIEW；Repair candidate 已驗證，尚未接受、merge 或 production。

## Root question

能否讓同一個 `formal_capability_preflight()` 真正呼叫正式 Publisher／transaction／release 實作，又以可注入、可觀察、fail-closed 的方式保證不寫正式 queue、worktree、tag 或 remote？

## 固定事實

- Reviewed candidate：`c61491e748acad43e44e73f7eabbc320dcbaa532`。
- Review-only base：`6c57f3d9a47a76704acf4f0cfdf5522f48a7685d`。
- Blocking finding：五個 publisher capabilities 可全回 PASS，但對 `publish_ready_runs()`、`_isolated_transaction_worktree()`、`_stage_commit_tag_push()` 的 call recorder 為空。
- Repair 不得以新增 receipt 字串、command plan、wrapper 模擬器或另一個 capability simulator 關閉 finding。

## 唯一實作切片 REPAIR-PUBLISHER-INVOCATION-001

### 允許改動

只可修改：

1. `scripts/agy_content_publisher.py`
2. `tests/test_pantheon_content_capability_probe.py`

不得修改 adapter；既有 adapter 仍呼叫同一個 `formal_capability_preflight()`。

### 行為契約

1. `publish` 必須實際呼叫正式 `publish_ready_runs(..., dry_run=True, exact_run_ids=...)` 或等價既有 production public interface。
2. `transaction`、`tag`、`push` 必須進入既有正式 isolated-worktree／release boundary；只能透過明示 dependency injection／dry-run runner 阻止 mutation，不能只產 command plan。
3. PASS 必須源自正式 invocation 的 return／trace；禁止由函式手寫 `called_entrypoints` 冒充呼叫證據。
4. 同一 public interface 的任何 exception、非預期 status、identity／run-id 缺失必須 fail closed，且不得留下 filesystem／git／queue 副作用。
5. 不改 4lan topology、runtime manifest、Publisher 正常發布語意與 CLI 預設行為。

### TDD 與 deterministic checks

先新增會失敗的 public-interface 測試，再做最小實作：

- 用 monkeypatch／call recorder 包住正式函式，逐步斷言實際 call count、參數與順序。
- 正向：publish／transaction／tag／push 命中正式 boundary，回 PASS，且 sandbox 之外無 filesystem/git mutation。
- 負向：任一正式 boundary 拋錯或回拒絕狀態，probe 必須 BLOCKED，不得繼續下一步。
- 測試不得只檢查 `production_entrypoints`、`called_entrypoints` 或非空 receipt。

## 必跑驗證

1. `pytest -q tests/test_pantheon_content_capability_probe.py`
2. 受影響 Publisher／4lan targeted tests；至少覆蓋 `test_agy_content_publisher.py` 與既有正式 runtime chain suite。
3. `git diff --check`
4. exact changed-file inventory 必須只含 allowlist。
5. 產出 invocation receipt，列出實際被呼叫函式、參數摘要、return status、mutation assertion；receipt 不能作為唯一證據，必須能由測試重現。

## 交付

- source/test commit SHA。
- `artifacts/fortune_council/four_lane_runtime_execution/repair/formal_runtime_chain_repair_001/repair-receipt.md`。
- clean worktree、完整測試摘要、exact changed files。
- 狀態只可 `REPAIR_READY_FOR_REREVIEW` 或 `BLOCKED`。
- 不得自行給 `REVIEW_GO`、不得自行 merge／push／deploy；完成後交回原 Reviewer thread re-review。

## 停損

- 若必須修改第三個 production/test 檔才能真實命中 boundary，停止並回 `BLOCKED / CONTRACT_EXPANSION_REQUIRED`，附 call graph 與最小擴張理由；不得自行擴張。
- 同一 blocker 失敗三次即停。
