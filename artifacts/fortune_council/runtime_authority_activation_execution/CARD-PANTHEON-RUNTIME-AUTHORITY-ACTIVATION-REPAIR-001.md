---
card_id: CARD-PANTHEON-RUNTIME-AUTHORITY-ACTIVATION-REPAIR-001
status: CARD_DRAFTED
execution_authorized: true
production_authorized: false
chain_id: PANTHEON-RUNTIME-AUTHORITY-ACTIVATION
role: repair
cycle: 1
repair_generation: 1
repair_limit: 2
required_source_ref: codex/runtime-authority-activation-repair-1-source-20260810
required_source_sha: 72743258f602e7cce07463bea87849e00a7d1ee1
candidate_under_repair: a0767f2071efd5593eca005e5bc7c390d416a266
review_commit: 72743258f602e7cce07463bea87849e00a7d1ee1
review_verdict: REVIEW_NO_GO
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 兩個 P1 已有固定 public reproducer 與精確修復邊界；屬核心 bounded Repair-1，不重開架構 fork，也不含 production mutation。
ownership: 只關閉 RAA-REVIEW-001、RAA-REVIEW-002；同步消除 RAA-REVIEW-003 自證 identity，不處理其他產品範圍
allowlist:
  - artifacts/fortune_council/runtime_authority_activation_execution/CARD-PANTHEON-RUNTIME-AUTHORITY-ACTIVATION-REPAIR-001.md
  - scripts/agy_content_publisher.py
  - scripts/agy_gemini_coordinator.py
  - scripts/agy_gemini_runner.py
  - scripts/pantheon_content_capability_adapter.py
  - scripts/pantheon_content_capacity_guard.py
  - scripts/pantheon_content_runtime_manifest.py
  - scripts/pantheon_runtime_activation.py
  - scripts/pantheon_runtime_fs_authority.py
  - tests/test_agy_content_publisher.py
  - tests/test_agy_gemini_coordinator.py
  - tests/test_agy_gemini_runner.py
  - tests/test_pantheon_content_capability_probe.py
  - tests/test_pantheon_content_capacity_guard.py
  - tests/test_pantheon_content_runtime_manifest.py
  - tests/test_pantheon_runtime_activation.py
  - tests/test_pantheon_runtime_fs_authority.py
  - artifacts/fortune_council/runtime_authority_activation_execution/repair/runtime_authority_activation_repair_001/**
forbidden_scope:
  - 修改 Review 卡、review evidence、implementation card 或既有 implementation evidence
  - 舊 PANTHEON-FOUR-LANE-FORMAL-RUNTIME-CHAIN 的 Repair-3、重命名重置或任何舊 chain 修補
  - Writer vNext、內容政策、prompt、SEO、Schema、文章、前端、registry、sitemap、feed、redirects
  - production queue/state/article、publication、tag、push、deploy、network、launchctl 或服務啟動
  - 新 daemon、第二套 queue/lock/control plane、只為測試存在的平行 runtime
  - 用 optional token、caller boolean、absolute Path 前後 assert、終態 snapshot 或 mock PASS 冒充 authority
evidence_path: artifacts/fortune_council/runtime_authority_activation_execution/repair/runtime_authority_activation_repair_001/
---

# Runtime Authority Activation Repair-1

## 五行派工卡

任務 ID｜`CARD-PANTHEON-RUNTIME-AUTHORITY-ACTIVATION-REPAIR-001`；只修獨立 Review 的兩個 P1，並移除同一 trace seam 的 P2 自證 identity。

派工對象｜單一嚴格 Repair task；從固定 review commit 建立 clean worktree；不得自審、merge、push、deploy 或碰 production。

任務目的｜讓 activation token 成為 formal runtime 的必備 I/O authority，並讓可信 directory authority 覆蓋完整 Publisher transaction lifecycle。

可改範圍｜只限 frontmatter allowlist；review artifacts 唯讀；若需要 allowlist 外 source/test，立即回 `BLOCKED / CONTRACT_EXPANSION_REQUIRED`。

驗收證據｜先把兩個 Reviewer reproducer 落成 public RED，再逐一 GREEN；缺 token／6-of-7 零 I/O，late parent-swap 外部 tree before/after identical；targeted suite、`git diff --check`、allowlist 與 clean candidate commit 通過。

## 工作名稱 → 正在做什麼 → 現在狀態

- 工作名稱：Runtime Authority Activation Repair-1
- 正在做什麼：關閉 `RAA-REVIEW-001`、`RAA-REVIEW-002`，同步移除 `RAA-REVIEW-003` 的自證 trace identity。
- 現在狀態：`CARD_DRAFTED`；production 維持 `NO-GO`。

## 固定來源與 Review 證據

1. `HEAD` 必須等於 `72743258f602e7cce07463bea87849e00a7d1ee1`；其 parent 必須等於 candidate `a0767f2071efd5593eca005e5bc7c390d416a266`。
2. Review verdict 固定為 `REVIEW_NO_GO`；findings 只認：
   - `RAA-REVIEW-001 P1`：formal runtime 缺 `PANTHEON_RUNTIME_ACTIVATION_TOKEN` 仍 PASS 且可 queue I/O。
   - `RAA-REVIEW-002 P1`：fd authority context 關閉後，Git common-dir／lock／transaction absolute Path 可 late parent-swap 外部 mutation。
   - `RAA-REVIEW-003 P2`：trace identity 未配置時以 publisher+correlation 自產 64-hex。
3. 兩個 P1 必須各自先轉成 public-behavior RED；不得用 import error、fixture error、private helper assertion或人工修改 expected 充當 RED。
4. 同一 blocker 第三次失敗立即停止，不做第四次；Repair-1 不得擴張成 Repair-3 或新架構重寫。

## Repair 契約

### RR-001｜Activation token 必填且先於 I/O

- `PANTHEON_FORMAL_RUNTIME=1` 時，`PANTHEON_RUNTIME_ACTIVATION_TOKEN` 必須存在、為 absolute path，並由 `validate_runtime_tick()` 驗證 manifest digest、runtime identity、generation、owner、七服務集合與 ack digests；缺 token／tamper／stale／mismatch 一律 fail-closed。
- `pantheon_content_capability_adapter` 的正式 input/environment contract 必須明確攜帶 activation token；不得由 adapter 自造 token、從任意 caller fallback，或因 env 缺席跳過 barrier。
- coordinator、四 lane、Publisher、capacity guard 的每個 queue/state public entrypoint 都必須在第一次 read/write 前走同一 runtime tick；Publisher 在 lock／transaction／publication boundary 前再驗。
- token validation 失敗時 call recorder 必須證明 queue/state/lock/Git operation 為零。

### RR-002｜Directory authority 覆蓋完整 transaction lifecycle

- `TrustedSandboxDirectoryAuthority` 必須存活到 `formal_capability_preflight()` 全部 filesystem/Git transaction 操作結束，且每個 mutation 都以可信 fd 下的相對 component 執行。
- 至少涵蓋 Git common-dir mkdir、lock open、transaction parent create/remove、repo materialization/copy、worktree add/remove、cleanup/prune 所觸及的 sandbox target。
- 不得只在 ordinary absolute `Path` mutation 前後呼叫 `assert_current()`；這仍保留 check/use window。需要可證明不可繞過的 dir-fd/no-follow traversal、opened-parent identity 或等價的 mutation-time authority。
- external parent/sandbox root 在 initial mkdir 後、Git-root check 後、lock open 前、transaction create前任一時點被交換時，必須在任何 external mkdir/open/copy/Git 前拒絕；external tree before/after identical。
- operation trace 必須由同一被允許 operation 產生；若 authority 拒絕，記錄 BLOCKED 但不得先 mutation。

### RR-003｜Verified trace identity

- formal capability trace 的 runtime identity digest 只能來自已驗證 manifest/barrier receipt；缺 verified identity 必須 `BLOCKED`，不得用 publisher ID、correlation ID 或隨機/雜湊 fallback 產生看似合法的 64-hex。
- trace event 必須保留 correlation、anchor identity、pre/post identity、result 與 deterministic digest，但 `status=PASS` 不得隱含未驗 identity。

## 垂直切片

### Slice A｜Missing-token RED → GREEN

將 Reviewer 的最小 public reproducer落成測試：formal env 完整、token 缺席，`validate_runtime_tick()` 必須拒絕且 fake queue I/O recorder 為零。接線 adapter input/environment 與所有既有 formal public entrypoint，轉綠後重跑 manifest/adapter/coordinator/runner/capacity tests。

### Slice B｜Late parent-swap RED → GREEN

將 Reviewer 的 transaction reproducer 落成 public test：在 initial authority 成立後交換 Git/transaction parent，確認 external `.git`、lock、transaction tree 完全不存在。把 authority 延伸到完整 lifecycle，轉綠後重跑 Publisher/capability/fs-authority tests。

### Slice C｜Trace identity 收斂

移除自產 digest fallback；用已驗 runtime receipt 傳入 trace。新增 missing/mismatch identity negative test，且不得新增第二套 identity cache。

### Final checkpoint

只跑受影響 suite、allowlist inventory、debug marker scan、`git diff --check`。不得執行 production、network、launchctl、tag、push、deploy 或 repository-wide destructive action。

## 必跑驗證

```bash
PYTHONDONTWRITEBYTECODE=1 <repo-root>/.venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_pantheon_runtime_fs_authority.py \
  tests/test_pantheon_runtime_activation.py \
  tests/test_pantheon_content_runtime_manifest.py \
  tests/test_pantheon_content_capability_probe.py \
  tests/test_agy_content_publisher.py \
  tests/test_agy_gemini_coordinator.py \
  tests/test_agy_gemini_runner.py \
  tests/test_pantheon_content_capacity_guard.py
git diff --check 72743258f602e7cce07463bea87849e00a7d1ee1..HEAD
```

保存：兩個 P1 的 RED/GREEN 原始命令、exit code、外部 tree identity；missing/6-of-7/tamper/stale/token-before-I/O matrix；changed-files allowlist、`[DBG-]`/TODO/FIXME/HACK scan；source/candidate SHA 與 clean status。

## 交付

- 只能交付 clean candidate commit，狀態 `CANDIDATE_READY_FOR_REVIEW` 或 `BLOCKED`。
- commit parent 必須是 `72743258f602e7cce07463bea87849e00a7d1ee1`；不得 amend Review commit。
- 不得自行 Review、宣稱 `REVIEW_GO`、開始 Repair-2、merge、push、deploy、production、canary 或服務啟動。
