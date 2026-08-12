# CARD-CONTENT-WRITER-VNEXT-RA-CHECKPOINT-B-REPAIR-1-001

## 工作名稱

Writer vNext Checkpoint B capacity deterministic-test Repair-1

## 固定來源

- BLOCKED evidence：`4b90fb7f61d52fc0ff50af20acae678b0b1ca149`
- finding：`P1`，`tests/test_pantheon_writer_vnext_runtime_activation_capacity.py:169`
- chain／role：沿用 Writer vNext Runtime Activation chain 的唯一 `Repair`
- 模型：`gpt-5.5`
- reasoning：`high`
- 啟動條件：須另有使用者對本 action/card/model/reasoning 的明確授權

## 根因契約

失敗測試使用 `_default_sampler` 讀取即時 host free space。當 host free 低於
`max(20 GiB, 10% total)` 時，production guard 會在 workload 前正確 fail-closed，
使 `len(calls) == 0`。測試原本想驗證的則是 workload 寫入後的
`project-bytes-over-budget`，因此 fixture 不具 deterministic isolation。

## 任務

只修測試 fixture：為該 over-budget test 注入 deterministic sampler，明確提供
高於 reserve 的 host free、零初始 project bytes，並保留 workload 寫入後由
`project-bytes-over-budget` 阻擋的原始驗收語意。

不得削弱、繞過或修改 production capacity guard；不得把真實 host-free
fail-closed 改成 PASS。

## 可改範圍

- `tests/test_pantheon_writer_vnext_runtime_activation_capacity.py`
- `artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_checkpoint_b_repair_1/**`

其他檔案一律禁止修改。

## 必跑驗證

1. `uv run --frozen pytest tests/test_pantheon_writer_vnext_runtime_activation_capacity.py -q -p no:cacheprovider`
2. `uv run --frozen pytest tests/test_pantheon_writer_vnext_runtime_activation_readiness.py tests/test_pantheon_writer_vnext_runtime_activation_e2e.py tests/test_pantheon_writer_vnext_runtime_activation_capacity.py -q -p no:cacheprovider`
3. `git diff --check`
4. 證明修後案例的 blocker case 仍是 `project-bytes-over-budget`、`len(calls) == 1`、`next_cycle_started is False`

## 禁止範圍

- 禁止 push、deploy、tag、production、canary、正式產文、publication、network write。
- 禁止啟停服務、清理其他 worktree／thread、修改既有 RA004–RA007 或 Checkpoint B evidence。
- 禁止新增 Reviewer／Repair／sub-agent。
- 禁止擴大成 production capacity policy 變更。

## 交付

- 單一 candidate commit，父節點必須是本卡 source commit。
- worktree clean。
- 回報 candidate SHA、修改檔案、兩組 pytest 結果、`git diff --check`。
- 完成後停止；主線必須回到既有唯一 Reviewer re-review。
