---
card_id: CARD-PANTHEON-RUNTIME-AUTHORITY-ACTIVATION-REVIEW-002
status: CARD_DRAFTED
execution_authorized: true
production_authorized: false
chain_id: PANTHEON-RUNTIME-AUTHORITY-ACTIVATION
role: code_review
cycle: 2
review_kind: re-review
required_source_ref: codex/runtime-authority-activation-re-review-source-20260810
required_candidate_sha: 63d9cd29b1de666bc17df8f031267d279466964e
required_candidate_parent: 72743258f602e7cce07463bea87849e00a7d1ee1
original_candidate_sha: a0767f2071efd5593eca005e5bc7c390d416a266
original_review_commit: 72743258f602e7cce07463bea87849e00a7d1ee1
repair_generation: 1
repair_limit: 2
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 固定 Repair-1 SHA，重驗兩個既有 P1 與 repair regression；不重開完整架構探索。
ownership: 獨立 re-review；只驗 unresolved findings、Repair-1 diff 與直接 regression
allowlist:
  - artifacts/fortune_council/runtime_authority_activation_execution/CARD-PANTHEON-RUNTIME-AUTHORITY-ACTIVATION-REVIEW-002.md
  - artifacts/fortune_council/runtime_authority_activation_execution/review/runtime_authority_activation_review_002/**
forbidden_scope:
  - 修改任何既有 source、test、implementation/review/repair card 或 evidence
  - Repair、Repair-2、舊四 lane Repair-3、重做架構、擴大產品範圍
  - merge、push、deploy、production、publication、tag、network、launchctl 或服務啟動
  - 只採信 Repair receipt／targeted PASS，不獨立重現原 P1
review_output: artifacts/fortune_council/runtime_authority_activation_execution/review/runtime_authority_activation_review_002/
---

# Runtime Authority Activation Repair-1 獨立 Re-review

## 五行派工卡

任務 ID｜`CARD-PANTHEON-RUNTIME-AUTHORITY-ACTIVATION-REVIEW-002`；固定審查 Repair-1 candidate `63d9cd29b1de666bc17df8f031267d279466964e`。

派工對象｜全新獨立 Reviewer；clean worktree；不得由 Repair 實作者自審。

任務目的｜重新執行原 Reviewer 的兩個 P1 reproducer，確認 token-before-I/O 與 late parent-swap 已真實 fail-closed，並掃 Repair regression。

可改範圍｜只可新增本卡與唯一 re-review output；候選 source/test 全部唯讀。

驗收證據｜固定 SHA/parent、CodeGraph semantic query、兩個原 P1 的獨立 reproducer、targeted suite、allowlist、`git diff --check`、唯一 verdict。

## 工作名稱 → 正在做什麼 → 現在狀態

- 工作名稱：Runtime Authority Activation Repair-1 獨立 Re-review
- 正在做什麼：重驗 `RAA-REVIEW-001..003` 與 Repair-1 直接 regression。
- 現在狀態：`CARD_DRAFTED`；production 維持 `NO-GO`。

## 固定邊界

1. `HEAD` 必須等於 `63d9cd29b1de666bc17df8f031267d279466964e`，`HEAD^` 必須等於 `72743258f602e7cce07463bea87849e00a7d1ee1`；不符回 `BLOCKED / SOURCE_MISMATCH`。
2. Review scope 是 `7274325..63d9cd2` 的 11 個 changed files，加上原 findings 指向的直接 call chain；不得全 repo 發散。
3. 原 unresolved state：
   - `RAA-REVIEW-001 P1` activation token 非必備 authority。
   - `RAA-REVIEW-002 P1` late parent-swap 可先外部 mutation。
   - `RAA-REVIEW-003 P2` trace identity fallback 自證。
4. 已修復 finding 不重報；未修復必須保留原 ID。新 finding 只限 Repair-1 引入的 P0/P1 或明確 P2 regression。
5. 只有 P0/P1 或 production safety risk 可 `REVIEW_NO_GO`；P2/P3 列 residual。

## 必重驗

### RAA-REVIEW-001

- `PANTHEON_FORMAL_RUNTIME=1`、manifest env 完整、token 缺席時，`validate_runtime_tick()` 與 adapter/coordinator public path 必須在任何 queue/state read/write 前拒絕。
- token 必須來自 handoff contract，不可 optional、fallback、自造；6/7、tamper、stale、mismatch 同樣零 I/O。
- 檢查四 lane、Publisher、capacity guard 的直接 entrypoint 是否都有 token-before-I/O；若 Repair 只修測試示例而正式 caller 未接線，維持 P1。

### RAA-REVIEW-002

- 重跑原 late parent-swap：initial queue/state mkdir 後、Git-root check 後或 lock open 前交換 parent，external tree before/after 必須 identical，且不得出現 `.git`、lock、transaction/copy artifact。
- 確認 live `TrustedSandboxDirectoryAuthority` 覆蓋 common-dir mkdir、lock open、transaction create/remove、repo copy/remove；每個 mutation 由 dir-fd/no-follow authority執行，不是 ordinary absolute Path 前後 assert。
- 檢查 exception cleanup path 同樣不可掉出 authority。

### RAA-REVIEW-003

- missing `PANTHEON_RUNTIME_IDENTITY_DIGEST`／verified runtime receipt 時 formal preflight 必須拒絕；trace event 不得出現 publisher+correlation 自造 digest。
- verified receipt 的 digest 必須和 manifest/barrier identity 相同且被實際 trace 使用。

## Regression 快檢

- adapter/probe handoff schema 與既有 caller 相容；缺欄 fail-closed，不得把 production default 變成測試-only bypass。
- Publisher transaction create/remove、lock context、file descriptor close、cleanup 與 operation trace ordering 不得漏資源、double-close 或在錯誤路徑留下 tree。
- Repair changed files須落在 Repair allowlist；不得含 debug marker、hardcoded machine path、新 control plane 或 production side effect。
- `repair_receipt.md` 的 candidate SHA placeholder 可列 evidence P3，但不得單獨阻擋；真實 SHA 以 Git object 為 authority。

## 驗證

至少執行並保存：

```bash
git rev-parse HEAD
git rev-parse HEAD^
git diff --check 72743258f602e7cce07463bea87849e00a7d1ee1..63d9cd29b1de666bc17df8f031267d279466964e
PYTHONDONTWRITEBYTECODE=1 <repo-root>/.venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_pantheon_runtime_fs_authority.py \
  tests/test_pantheon_runtime_activation.py \
  tests/test_pantheon_content_runtime_manifest.py \
  tests/test_pantheon_content_capability_probe.py \
  tests/test_agy_content_publisher.py \
  tests/test_agy_gemini_coordinator.py \
  tests/test_agy_gemini_runner.py \
  tests/test_pantheon_content_capacity_guard.py
```

另以獨立 public reproducer 輸出：missing-token I/O count、6/7 I/O count、late-swap external tree、unverified identity結果。不得操作 production/network。

## Finding 與 Verdict

每個 finding 必須含 severity、category、`path:line`、觸發條件、reproducer、風險、建議修法、validation gap、confidence。

- `REVIEW_GO`：原兩個 P1 已獨立關閉、無新 P0/P1，Spec/Standards 兩軸通過；列 residual 與 production 仍 NO-GO。
- `REVIEW_NO_GO`：任一原 P1 未關閉或 Repair 引入新 P0/P1；需最短 reproducer 與 Repair-2 精確邊界。
- `BLOCKED`：source mismatch 或關鍵環境不可重現；不得把單純未跑測試當 finding。
- 寫入 `review_report.md`、`verification_receipt.md`、`findings.json`，建立只含 allowlist 新檔的 review-only commit，交付 SHA 與 clean status。
- 不得 Repair、merge、push、deploy、production、canary 或啟動服務。
