---
card_id: CARD-PANTHEON-FOUR-LANE-FORMAL-RUNTIME-CHAIN-REPAIR-001
finding_id: PANTHEON-FORMAL-RUNTIME-001
status: REPAIR_READY_FOR_REREVIEW
formal_thread_id: 019feaaa-54a5-7741-83c9-187e0cce510b
required_base_sha: 6c57f3d9a47a76704acf4f0cfdf5522f48a7685d
production_mutation: false
---

# Repair receipt：正式 Publisher capability 呼叫鏈

## Root question

`formal_capability_preflight()` 是否真的進入正式 Publisher／transaction／release boundary，同時以 injected dry-run 保證不改正式 queue、worktree、tag 或 remote？

## 根因與修復

- RED 證明原實作只回傳手寫 `called_entrypoints`／command plan；monkeypatch call recorder 的事件序列為空。
- 根因是 `formal_capability_preflight()` 未呼叫 `publish_ready_runs()`、`_isolated_transaction_worktree()` 或 `_stage_commit_tag_push()`。
- 修復讓同一 public interface 直接呼叫上述既有正式函式；Git 與 host-check 副作用由明示 injected runner 截斷，正式介面的狀態、exception 與 SHA 驗證仍 fail closed。
- CodeGraph semantic query 先定位上述四個 symbol；再由原始碼確認 `GitRunner`、`dry_run`、`exact_run_ids` 與 `_stage_commit_tag_push()` 是既有可注入接縫，未修改 adapter 或第三個 production/test 檔。

## Public-interface invocation evidence

| Capability | 實際正式函式 | 參數摘要 | Return／trace 判定 | Mutation assertion |
|---|---|---|---|---|
| `publish` | `publish_ready_runs()` | `dry_run=True`、`push=False`、`run_tests=False`、`release_gate=False`、`exact_run_ids=<四線 run IDs>`、`seed_translations=False` | 實測 `status=idle`、`base_sha=6c57f3d9a47a76704acf4f0cfdf5522f48a7685d`；非 `idle/dry-run`、缺 SHA 或錯誤 run identity 皆 BLOCKED | queue/state 僅使用 probe sandbox；Git runner 不執行 fetch 或 mutation |
| `transaction` | `_isolated_transaction_worktree()` | actor root、sandbox state root、injected Git runner | context 正常 enter/exit 才 PASS；exception 原樣 fail closed | worktree add/remove 只在暫存 sandbox materialize runtime manifest bytes |
| `tag` | `_stage_commit_tag_push()` | `version=0.0.0`、`push=False`、`release_gate=False`、injected Git/checked runner | 正式 release boundary 回傳 exact base SHA；非 40 hex SHA 即 BLOCKED | add/commit/tag 僅進入 recorder，不呼叫正式 Git |
| `push` | `_stage_commit_tag_push()` | `version=0.0.0`、`push=True`、`release_gate=False`、injected Git/checked runner | trace 包含 atomic push command；正式 boundary exception 原樣 fail closed | push 僅進入 recorder，不接觸 remote |

直接 invocation trace 的 `called_entrypoints` 分別包含：

- `scripts.agy_content_publisher:publish_ready_runs`
- `scripts.agy_content_publisher:_isolated_transaction_worktree`
- `scripts.agy_content_publisher:_stage_commit_tag_push`

所有結果均為 `production_mutation=false`。完整 formal probe 測試另比較執行前後 production source digest 與 `git status --porcelain --untracked-files=all`，兩者均不變；因此 receipt 不是唯一證據。

## TDD evidence

1. RED：`test_publisher_preflight_invokes_formal_publish_transaction_and_release_boundaries` 最初失敗，`events == []`，證明原 finding 可重現。
2. GREEN：最小實作後，call order 為 `publish → transaction → tag → push`，並逐項驗證正式函式參數。
3. RED：`test_publisher_preflight_blocks_publish_return_without_runtime_identity` 最初未丟例外。
4. GREEN：缺 runtime SHA、錯誤 status、錯誤 run identity、boundary exception 或無效 release SHA 均 fail closed。

## Verification

- `pytest -q tests/test_pantheon_content_capability_probe.py tests/test_agy_content_publisher.py`
  - `126 passed`
  - 既有 `DeprecationWarning: invalid escape sequence '\/'` 1 筆；不影響本 finding，且不在本卡範圍。
- `git diff --check`：PASS。
- `[DBG-...]` 掃描：無殘留。
- Exact changed-file inventory：僅含卡片 allowlist 內的 source、test、task card、repair card 與本 receipt。

## 限制與交接

- 未修改 `scripts/pantheon_content_capability_adapter.py` 或其他 production/test 檔。
- 未執行 merge、push、deploy、production canary、launchctl 或正式 queue/state/git mutation。
- CodeGraph semantic query 使用 activation 的 exact-base index；commit 後 `indexed-head` 仍是 base SHA，candidate reindex 留給 re-review 前的 control-plane prepare，驗收結論以原始碼與測試為準。
- Candidate commit SHA 由包含本 receipt 的 repair-only commit 與 thread handoff 提供；本卡不自行給 `REVIEW_GO`。
