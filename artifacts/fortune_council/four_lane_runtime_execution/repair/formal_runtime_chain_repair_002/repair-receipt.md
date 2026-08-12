# Repair-2 invocation receipt

- 狀態：`REPAIR_READY_FOR_REREVIEW`
- finding：`PANTHEON-FORMAL-RUNTIME-001`
- base：`83a57a8b796b7a7509a870028ba12c60e92aea46`
- production authorized：`false`

## Path authority 與 containment

- Adapter 先驗證 source contract 的 canonical `sandbox_root`，再以 Publisher 的單一純 containment check 驗證 manifest `queue_root` 與 `publisher_state_root`，最後明確把三個 resolved roots 傳入 `formal_capability_preflight()`。
- Publisher 不接受 environment roots 自證 authority；缺少明示 `trusted_sandbox_root`、queue 或 state 時直接 `BLOCKED`。
- containment 在 mkdir、lock open、transaction、Git runner 與正式 Publisher boundary 前完成；只接受 sandbox 的 strict resolved descendants，並拒絕 equal、parent、external、queue/state overlap 與既存 symlink escape。
- injected Git runner 對 transaction materialization／remove root 再套用同一 containment check。

## Public boundary invocation

| capability | 實際正式 boundary | 參數摘要 | 接受狀態 |
| --- | --- | --- | --- |
| publish | `publish_ready_runs()` | `dry_run=True`、`push=False`、`exact_run_ids=<correlated IDs>`、injected Git runner | `dry-run` 或 `idle` |
| transaction | `_isolated_transaction_worktree()` | verified state root、injected Git runner | context 正常進出 |
| tag | `_stage_commit_tag_push()` | `push=False`、`release_gate=False`、injected runners | 40-char candidate SHA |
| push | `_stage_commit_tag_push()` | `push=True`、`release_gate=False`、injected runners | 40-char candidate SHA |

正向 probe 仍由同一 public interface 命中上述三組 production boundaries；測試以 call recorder 核對 publish → transaction → tag → push 的呼叫次數、參數與順序。

## Mutation assertions

- external queue、external state、queue symlink escape、state symlink escape、sandbox equal／parent 與 queue/state overlap：全部在正式 boundary 與 Git runner 前 `BLOCKED`，fixture tree before/after identical。
- external Adapter manifest queue/state：`_load_contract()` fail closed，before/after identical。
- transaction materialization 指向 sandbox 外：dry-run Git runner 在建立目錄前 `BLOCKED`，before/after identical。
- sandbox 正向：`sandbox_mutation` 由 queue/state/lock/sandbox Git existence snapshot before/after 推導；`production_mutation` 由 verified containment 與實際 trace roots 推導，未以常數冒充 Publisher 結果。
- 正式 source digest 與 git status 在完整正向 probe 前後一致。

## 收斂後 diff 對應

- Publisher `+89/-16`：明示 authority、單一 containment check、transaction root reuse、最小 mutation 欄位。
- Adapter `+33/-3`：contract root 驗證、明示傳入 trusted roots、傳遞 Publisher mutation 結果。
- capability test `+206/-1`：before/after snapshot、參數化 containment 負例、Adapter external-root harness、transaction escape 與既有正向 boundary 測試調整。
- 未新增 helper hierarchy、receipt state machine、通用 mutation framework或政策層；source/test diff 共 `+328/-20`。

## Verification

- `uv run --frozen pytest -q tests/test_pantheon_content_capability_probe.py tests/test_agy_content_publisher.py`：`137 passed`，1 個既有 `SyntaxWarning`。
- 4lan formal runtime targeted suite（capability probe、Publisher、coordinator、runner、capacity guard、runtime manifest）：`258 passed`，1 個相同既有 `SyntaxWarning`。
- `git diff --check`：PASS。
- source SHA-256：
  - `scripts/agy_content_publisher.py`：`f432f44b4c27651178057dc34e18efccea0fe9b4d3105efdc947d2874388af3a`
  - `scripts/pantheon_content_capability_adapter.py`：`8d80b50c1a86e6a146dc80788ac7e2e4be4cab390dbe68c6b8ea04ba94c8d1b2`
  - `tests/test_pantheon_content_capability_probe.py`：`07943779472c9d41714484f8bd502a74d9c6bc0b72bfc194ad9ec8043c51e5a4`

## Exact changed files

1. `scripts/agy_content_publisher.py`
2. `scripts/pantheon_content_capability_adapter.py`
3. `tests/test_pantheon_content_capability_probe.py`
4. `.ai/codex_task_four_lane_formal_runtime_chain_repair_002.md`
5. `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-FOUR-LANE-FORMAL-RUNTIME-CHAIN-REPAIR-002.md`
6. `artifacts/fortune_council/four_lane_runtime_execution/repair/formal_runtime_chain_repair_002/repair-receipt.md`
