---
card_id: CARD-PANTHEON-FOUR-LANE-FORMAL-RUNTIME-CHAIN-REPAIR-002
status: REPAIR_READY_FOR_REREVIEW
execution_authorized: true
production_authorized: false
formal_thread_id: 019feaaa-54a5-7741-83c9-187e0cce510b
dispatch_key: v1:abc10d630ebee4c9e7ad00db4ce2e4b11c3ca22f80e89002c18caf3fad9b683f
activation_status: BOUND
activation_token: act-v1:a08ddcea2974f63c85ecb79fc882bcbc8e09986c99be72b55be21c30bb3b4044
chain_id: PANTHEON-FOUR-LANE-FORMAL-RUNTIME-CHAIN
role: repair
cycle: 2
final_repair_generation: true
finding_ids:
  - PANTHEON-FORMAL-RUNTIME-001
required_base_ref: codex/four-lane-formal-runtime-repair-2-source-20260810
required_base_sha: 83a57a8b796b7a7509a870028ba12c60e92aea46
repair_1_candidate_sha: 12a86f91bc56a3c3566038deb0dc062f1b6a0c4d
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 最終 Repair 需跨 Adapter 與 Publisher 關閉 caller-controlled path trust、symlink escape 與首次 I/O 前 fail-closed，同時保留正式 boundary invocation，屬高風險 trust-boundary 修復。
provider_boundary: Codex-only；禁止外部 provider
subagent_decision: NOT_ELIGIBLE
subagent_reason: 只改 3 個 source/test 檔、2 個緊密相依模組、單一 finding；不符合 8 檔／3 模組／多輪安全委派門檻。
traces_to:
  - FR-001
  - SC-001
allowlist:
  - scripts/agy_content_publisher.py
  - scripts/pantheon_content_capability_adapter.py
  - tests/test_pantheon_content_capability_probe.py
  - .ai/codex_task_four_lane_formal_runtime_chain_repair_002.md
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-FOUR-LANE-FORMAL-RUNTIME-CHAIN-REPAIR-002.md
  - artifacts/fortune_council/four_lane_runtime_execution/repair/formal_runtime_chain_repair_002/**
forbidden_scope:
  - 其他 source/test、installer、plist、manifest schema、queue/state schema 或 runtime topology
  - PANTHEON-FORMAL-RUNTIME-002／003
  - merge、push、deploy、production canary、launchctl、正式 queue/state/git mutation
  - hidden agent、子代理、外部 provider、full-auto、sandbox bypass
---

# Repair-2：封住 capability sandbox 路徑信任邊界

## 工作名稱 → 正在做什麼 → 現在狀態

- 工作名稱：封住 capability sandbox 路徑信任邊界
- 正在做什麼：讓正式 Publisher capability 只在 Adapter 已驗證的 sandbox descendants 執行；外部或 symlink escape 路徑在首次 I/O 前拒絕。
- 現在狀態：RUNNING；沿用正式 Repair thread，這是 strict chain 最後一代 Repair。

## Root question

能否保留 Repair-1 已建立的真實 production-boundary invocation，同時證明 caller／manifest 無法讓 preflight 在 sandbox 外建立 queue、state、publisher.lock、transaction worktree、tag 或 remote side effect？

## 固定 finding 證據

- Repair-1 已確實命中 `publish_ready_runs()`、`_isolated_transaction_worktree()`、`_stage_commit_tag_push()`。
- 但外部 queue/state 在呼叫前不存在，呼叫後被建立且包含 `publisher.lock`，回傳仍為 `PASS / production_mutation=false`。
- 根因：Publisher 直接信任 environment roots；Adapter 只驗 `sandbox_root` 本身，未把 manifest queue/state roots 綁定為其 strict descendants。
- 本卡仍只處理 `PANTHEON-FORMAL-RUNTIME-001`，不得建立新 finding 或修 P2。

## 唯一切片 REPAIR-SANDBOX-CONTAINMENT-002

### 行為契約

1. Adapter 從已完成 realpath 驗證的 source contract 取得唯一 trusted sandbox root，明確傳入 Publisher public interface；禁止 Publisher 以 caller environment variable 自證 sandbox authority。
2. 在任何 `mkdir`、lock open、transaction context、Git runner 或正式 publisher invocation 前，驗證 queue root、publisher state root與所有 transaction/materialization root 都是 sandbox 的 strict resolved descendants。
3. 拒絕：sandbox 本身、sandbox 父層、外部 sibling、尚不存在但父鏈逃逸、既存 symlink escape，以及 queue/state 彼此不符合契約的路徑。
4. 拒絕必須發生在首次 filesystem/git I/O 前；before/after snapshot 完全一致。
5. sandbox 內正向仍須實際命中 Repair-1 的三個正式 production boundaries；不可退回手寫 PASS、command plan 或 simulator。
6. `production_mutation` 不得無條件常數自報；必須由可信 sandbox containment 與實際 mutation trace/snapshot 推導。若只能證明 sandbox mutation，receipt 必須明確區分 `sandbox_mutation` 與 `production_mutation`。
7. 正常 production caller 未注入 dry-run runner 時，既有 `_run_checked`、Git、Publisher defaults 與 CLI 語意不變。

### TDD

先以同一 public interface 加 RED cases，再做最小 GREEN：

- 外部 queue root：BLOCKED，零 I/O。
- 外部 state root：BLOCKED，零 I/O。
- queue 或 state symlink escape：BLOCKED，零 I/O。
- sandbox 內 queue/state：publish → transaction → tag → push 真實 invocation 順序保持，僅 sandbox 內可觀察 mutation，正式 source/git/status 不變。
- 直接呼叫 Publisher 而未提供 Adapter 驗證的 sandbox authority：fail closed。

## 必跑驗證

1. `pytest -q tests/test_pantheon_content_capability_probe.py tests/test_agy_content_publisher.py`
2. 既有 4lan formal runtime targeted suite。
3. Reviewer 的外部-root harness 或等價獨立測試必須轉為 BLOCKED，且 before/after identical。
4. `git diff --check`、allowlist-only inventory、source digest／git status mutation comparison。
5. 產出 `repair-receipt.md`，明列 path authority、containment cases、actual calls 與 mutation scope。

## 交付與停損

- 只可 `REPAIR_READY_FOR_REREVIEW` 或 `BLOCKED`；提交 repair-only commit 並保持 clean。
- 不得自行 REVIEW_GO、merge、push、deploy 或 production mutation；交回原 Reviewer。
- 若需要第四個 production/test 檔、manifest schema 或 topology 變更，立即 `BLOCKED / CONTRACT_EXPANSION_REQUIRED`。本 chain 已達 Repair 上限，不得開 Repair-3。
