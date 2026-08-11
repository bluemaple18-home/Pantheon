---
card_id: CARD-PANTHEON-RUNTIME-AUTHORITY-ACTIVATION-REPAIR-002
status: CARD_DRAFTED
execution_authorized: true
production_authorized: false
chain_id: PANTHEON-RUNTIME-AUTHORITY-ACTIVATION
role: repair
cycle: 2
repair_generation: 2
repair_limit: 2
required_source_ref: codex/runtime-authority-activation-repair-2-source-20260810
required_source_sha: bcd35b090dd37b118632d3b4153308964218f0c8
candidate_under_repair: 63d9cd29b1de666bc17df8f031267d279466964e
review_commit: bcd35b090dd37b118632d3b4153308964218f0c8
review_verdict: REVIEW_NO_GO
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 最後 Repair 額度，只有一個已重現的 stale-cleanup P1；固定 source/call chain，需最小 fd-authority 修補與回歸證據。
ownership: 只關閉 RAA-REVIEW-002 的 post-lock stale transaction cleanup 子路徑
allowlist:
  - artifacts/fortune_council/runtime_authority_activation_execution/CARD-PANTHEON-RUNTIME-AUTHORITY-ACTIVATION-REPAIR-002.md
  - scripts/agy_content_publisher.py
  - scripts/pantheon_runtime_fs_authority.py
  - tests/test_pantheon_runtime_fs_authority.py
  - tests/test_agy_content_publisher.py
  - artifacts/fortune_council/runtime_authority_activation_execution/repair/runtime_authority_activation_repair_002/**
forbidden_scope:
  - 修改任何既有 review/repair/implementation card 或 evidence
  - token、adapter、coordinator、runner、capacity、trace identity 已通過部分的再設計
  - Repair-3、舊四 lane chain、架構重寫、Writer vNext、內容/SEO/前端/registry
  - production queue/state/article、publication、tag、push、deploy、network、launchctl 或服務啟動
  - ordinary absolute Path cleanup、僅前後 assert_current、caller boolean 或測試專用 bypass
evidence_path: artifacts/fortune_council/runtime_authority_activation_execution/repair/runtime_authority_activation_repair_002/
---

# Runtime Authority Activation Repair-2：Stale Cleanup Authority

## 五行派工卡

任務 ID｜`CARD-PANTHEON-RUNTIME-AUTHORITY-ACTIVATION-REPAIR-002`；這是本 chain 最後 Repair 額度，只修 stale transaction cleanup P1。

派工對象｜單一嚴格 Repair task；固定 re-review commit、clean worktree；不得自審、Repair-3、merge、push、deploy 或碰 production。

任務目的｜讓 lifecycle lock open 後的 stale transaction enumeration/removal 仍由 live sandbox dir-fd authority 執行，parent swap 時外部 tree before/after identical。

可改範圍｜只限 Publisher、filesystem authority、兩個直接測試檔、本卡與唯一 evidence；不得重碰已通過 token/trace/adapter 模組。

驗收證據｜先把 re-review `post_lock_cleanup_swap` 落成 public RED，再以 fd-relative enumerate/remove 轉 GREEN；targeted/regression、`git diff --check`、allowlist 與 clean candidate commit 通過。

## 工作名稱 → 正在做什麼 → 現在狀態

- 工作名稱：Runtime Authority Activation Repair-2
- 正在做什麼：關閉 post-lock stale cleanup 的 late parent-swap 外部刪除。
- 現在狀態：`CARD_DRAFTED`；production `NO-GO`；Repair generation `2/2`。

## 固定 Finding

`RAA-REVIEW-002 P1`：`formal_capability_preflight("transaction")` 已開啟 lifecycle lock 後、進入 `_cleanup_stale_transaction_worktrees()` 前交換 sandbox parent；現況最終雖 `PublishBlocked`，但 ordinary `state_root.iterdir()`／`transaction_root.exists()`／`shutil.rmtree()` 已刪除外部 `publisher-state/transaction-escape/repo/marker.txt`，`external_tree_identical=false`。

source 必須為 `bcd35b090dd37b118632d3b4153308964218f0c8`，parent 必須為 Repair-1 candidate `63d9cd29b1de666bc17df8f031267d279466964e`。不符回 `BLOCKED / SOURCE_MISMATCH`。

## Repair 契約

1. formal capability mode 的 stale cleanup 必須以 held `TrustedSandboxDirectoryAuthority` 與 `state_root` 相對 component 操作。
2. authority 需提供或重用 fd-relative、no-follow 的 directory listing/stat/remove primitives：拒絕 symlink、`.`、`..`、absolute、非 directory、identity drift。
3. `transaction-*` enumeration 與 repo/tree removal 都不得先 materialize ordinary absolute Path 再 `iterdir/exists/rmtree`；mutation 必須發生在 authority-opened parent fd 下。
4. 每個 cleanup operation 的 trace event 必須與實際 authority operation 同源；BLOCKED 時不得先刪除任何 external entry。
5. 正常 sandbox stale cleanup 仍須成功；non-transaction entry 不刪、symlink entry 拒絕、missing entry idempotent、exception path 不 double-close/leak fd。
6. Repair-1 已通過的 initial Git-root swap、transaction create/remove、missing token、6/7、stale token、unverified identity 不得 regression；但不得修改它們的 source 模組。

## 唯一 RED → GREEN

新增 public test，從 formal transaction public entrypoint在 `filesystem-lock-open` 後觸發 parent swap，外部預先放置 `transaction-escape/repo/marker.txt`：

- RED：現況 `status=BLOCKED` 但 external stale/marker 被刪。
- GREEN：仍 `BLOCKED`，external tree snapshot/identity 完全相同，stale/marker 保留；sandbox/production/network 無其他 mutation。

不得先加第二個 RED。第一個 GREEN 後再補 normal cleanup、symlink/non-transaction/exception regression。

## 必跑驗證

```bash
PYTHONDONTWRITEBYTECODE=1 <repo-root>/.venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_pantheon_runtime_fs_authority.py \
  tests/test_agy_content_publisher.py

PYTHONDONTWRITEBYTECODE=1 <repo-root>/.venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_pantheon_runtime_fs_authority.py \
  tests/test_pantheon_runtime_activation.py \
  tests/test_pantheon_content_runtime_manifest.py \
  tests/test_pantheon_content_capability_probe.py \
  tests/test_agy_content_publisher.py \
  tests/test_agy_gemini_coordinator.py \
  tests/test_agy_gemini_runner.py \
  tests/test_pantheon_content_capacity_guard.py

git diff --check bcd35b090dd37b118632d3b4153308964218f0c8..HEAD
```

保存 RED/GREEN 命令、exit code、external tree snapshot；normal/symlink/missing/exception cleanup matrix；changed-files allowlist、debug-marker scan、candidate parent/SHA、clean status。

## 停損與交付

- 同一 blocker 第三次失敗立即停止，不做第四次。
- 需要 allowlist 外 source/test、平台 unsafe fallback 或 contract expansion，回 `BLOCKED / CONTRACT_EXPANSION_REQUIRED`。
- 交付只能是 parent=`bcd35b0...` 的 clean candidate commit，狀態 `CANDIDATE_READY_FOR_REVIEW` 或 `BLOCKED`。
- 不得自行 Review、開始 Repair-3、merge、push、deploy、production、canary 或服務啟動。
