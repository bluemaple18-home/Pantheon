---
card_id: CARD-PANTHEON-RUNTIME-AUTHORITY-ACTIVATION-REVIEW-001
status: CARD_DRAFTED
execution_authorized: true
production_authorized: false
chain_id: PANTHEON-RUNTIME-AUTHORITY-ACTIVATION
role: code_review
cycle: 1
required_base_sha: 80fa0641102fa08d03acb1ee2b91559e0700763a
required_candidate_sha: a0767f2071efd5593eca005e5bc7c390d416a266
required_source_ref: codex/runtime-authority-activation-review-source-20260810
source_kind: commit
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 固定 SHA 的核心 trust-boundary 審查；需獨立驗證 filesystem authority、operation trace、runtime identity 與 activation barrier，但不重開架構 fork。
ownership: 唯讀獨立審查 Runtime Authority candidate；只可新增 Review 卡與 review evidence
allowlist:
  - artifacts/fortune_council/runtime_authority_activation_execution/CARD-PANTHEON-RUNTIME-AUTHORITY-ACTIVATION-REVIEW-001.md
  - artifacts/fortune_council/runtime_authority_activation_execution/review/runtime_authority_activation_review_001/**
forbidden_scope:
  - 修改任何既有 source、test、installer、plist、handoff、implementation card 或 implementation evidence
  - Repair、Repair-3、重做舊四 lane chain、重新定義需求或放寬 success criteria
  - merge、push、deploy、production queue/state/article、publication、tag、network、launchctl 或服務啟動
  - 以實作者 receipt、單次 PASS、mock、狀態文字或自填 artifact 取代獨立重現
review_output: artifacts/fortune_council/runtime_authority_activation_execution/review/runtime_authority_activation_review_001/
---

# Runtime Authority Activation 獨立 Review

## 五行派工卡

任務 ID｜`CARD-PANTHEON-RUNTIME-AUTHORITY-ACTIVATION-REVIEW-001`；固定審查 candidate `a0767f2071efd5593eca005e5bc7c390d416a266` 相對 base `80fa0641102fa08d03acb1ee2b91559e0700763a`。

派工對象｜獨立 Reviewer；使用 clean worktree；不得修改候選 source/test，不得要求實作者自審。

任務目的｜判斷候選是否以真實 runtime authority 關閉 parent-swap TOCTOU、transient mutation 漏報、七服務 identity 與 7/7 atomic activation 缺口。

可改範圍｜只可新增本 Review 卡與唯一 review output 目錄；所有產品碼與測試唯讀。

驗收證據｜固定 SHA／clean worktree／allowlist、逐 finding 可重現證據、獨立 targeted suite、`git diff --check`，最後只能交付 `REVIEW_GO` 或 `REVIEW_NO_GO`。

## 工作名稱 → 正在做什麼 → 現在狀態

- 工作名稱：Runtime Authority Activation 獨立 Review
- 正在做什麼：從固定 candidate 做 correctness、regression、security/runtime identity 與 test-gap 審查。
- 現在狀態：`CARD_DRAFTED`；production 維持 `NO-GO`。

## 固定邊界

1. 先證明 `HEAD == a0767f2071efd5593eca005e5bc7c390d416a266` 且 parent 正是 `80fa0641102fa08d03acb1ee2b91559e0700763a`；不符立即 `BLOCKED / SOURCE_MISMATCH`。
2. Review 對象只限 `80fa064..a0767f2` 的 11 個 changed files與它們直接呼叫的既有 runtime seam。
3. Spec axis 以 implementation card 的 `FRA-001..004`、`SCA-001..004` 為準；Standards axis 以 repo 契約、fail-closed、單一 control plane、跨機可重現性為準，兩軸不得互相抵銷。
4. 只有 P0/P1 或明確 production safety risk 可阻擋；P2/P3 必須列為 residual，不可單獨導出 `REVIEW_NO_GO`。
5. Review scaffold 不得寫進候選 worktree；實體 Review 卡與 evidence 是唯一允許新增的檔案。

## 必審風險問題

### RQ-1｜Filesystem authority 是否真的不可繞過

- `TrustedSandboxDirectoryAuthority` 是否從可信 root descriptor 執行所有相對 traversal，而非只在檢查時持有 fd、後續仍回到一般 absolute `Path` I/O。
- 每個 parent component、leaf、create/open/remove 是否使用 no-follow／dir-fd 語意並拒絕 symlink、`..`、absolute、identity drift。
- adversarial parent-swap 必須在任何外部 `mkdir/open/tempfile/Git` 前 fail-closed；外部 tree before/after identical。
- 檢查 Publisher 正式 public path 是否仍有 allowlisted mutation seam 未經 authority 包覆。

### RQ-2｜Operation trace 是否來自實際 operation

- trace event 必須與實際被允許的 filesystem／Git operation 同源，不能由 caller boolean、預期 path 或終態 snapshot 自證。
- transaction worktree create+remove 的終態即使相同，也必須留下可重算事件，且 production/sandbox mutation verdict 只能由可信 target 與事件推導。
- correlation ID、runtime identity digest、anchor identity、pre/post identity、result 與 ordering 必須 deterministic、不可由缺值 fallback 生成看似合法的自證 identity。

### RQ-3｜七服務 identity 是否由權威來源驗證

- coordinator、四 lane、Publisher、capacity guard 共七服務的 manifest／readiness／runtime tick 必須使用同一 versioned contract。
- 特別審查 `_runtime_identity_digest_for_trace()` 在未配置 identity 時的 fallback：若能用 `publisher_id + correlation_id` 自產 64-hex 並被當成已驗 runtime identity，視實際可達影響決定嚴重度。
- 缺欄、manifest mismatch、service mismatch、generation mismatch、config/runtime digest mismatch 必須在第一次 queue/state I/O 前 fail-closed；Publisher 在 transaction/publication boundary 前再驗。

### RQ-4｜Activation token/barrier 是否是唯一 I/O authority

- 7/7 readiness 必須原子產生單一 generation token；6/7、duplicate service、identity mismatch、stale generation、unreadable manifest 不得放行。
- `PANTHEON_RUNTIME_ACTIVATION_TOKEN` 與 `validate_runtime_tick()` 必須驗證 token 所代表的 barrier 內容、generation、identity、七服務集合及必要 correlation binding，不得只驗 path 存在或回傳 caller correlation ID。
- 找出任何在 token 驗證前可達的 queue/state read/write；如有，提供最短 public call-chain reproducer。
- rollback 若在本 candidate 未實作，必須判斷這是既定 scope 缺口、未接線還是可由現有 authority 安全維持 NO-GO，不得靠狀態文字宣稱完成。

### RQ-5｜Regression 與 scope

- `_isolated_transaction_worktree`、formal preflight、lock path／open、runtime manifest API 的既有 production default 行為是否被意外改變。
- 所有 changed files 必須落在 implementation allowlist；不得有 debug marker、hardcoded machine-specific contract 或新的第二套 queue/lock/control plane。
- 新測試需擊中 public behavior 與負向路徑，不能只測 private helper 或 mock 自證。

## 獨立驗證矩陣

至少保存下列命令、exit code 與關鍵 assertions：

```bash
git rev-parse HEAD
git rev-parse HEAD^
git diff --check 80fa0641102fa08d03acb1ee2b91559e0700763a..a0767f2071efd5593eca005e5bc7c390d416a266
<repo-root>/.venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_pantheon_runtime_fs_authority.py \
  tests/test_pantheon_runtime_activation.py \
  tests/test_pantheon_content_runtime_manifest.py \
  tests/test_pantheon_content_capability_probe.py \
  tests/test_agy_content_publisher.py \
  tests/test_agy_gemini_coordinator.py \
  tests/test_agy_gemini_runner.py \
  tests/test_pantheon_content_capacity_guard.py
```

另需獨立執行或從 public test 精確重現：parent-swap、symlink component、transient create+remove、missing identity、6/7、duplicate service、identity mismatch、stale token、token tamper、token-before-I/O ordering。不得操作 production 或 network。

## Finding 契約

每個 finding 必須包含：`finding_id`、`severity`、`category`、`path:line`、觸發條件、可重現證據、風險、建議修法、validation gap、confidence。先列 findings；找不到阻擋問題時明確寫「未發現阻塞問題」。

- `P0`：資料破壞、資安事故、錯誤 production mutation／部署。
- `P1`：主要 runtime authority 可繞過、正式 call chain 未接線、錯誤放行或重要 regression。
- `P2`：可控邊界缺口或非主要相容性／測試缺口。
- `P3`：維護性與非阻塞改善。

## Verdict 與交付

- `REVIEW_GO`：無 P0/P1，Spec axis 與 Standards axis 均通過；列 residual P2/P3 與 production 仍 NO-GO 的外部前置條件。
- `REVIEW_NO_GO`：至少一個可重現 P0/P1 或 production safety risk；每個 blocker 都要有最短 reproducer 與精確修復邊界。
- `BLOCKED`：來源不符、關鍵環境無法重現或需要 contract expansion；不得把未執行測試本身當 finding。
- 寫入 `review_report.md`、`verification_receipt.md`、`findings.json`（無 finding 時為空陣列），再建立只含 allowlist 新檔的 review-only commit，交付 commit SHA 與 clean `git status --short`。
- 不得 Repair、merge、push、deploy、production、launchctl、啟動服務或宣稱 production ready。
