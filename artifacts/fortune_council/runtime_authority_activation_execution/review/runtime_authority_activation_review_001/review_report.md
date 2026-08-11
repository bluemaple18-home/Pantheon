# Runtime Authority Activation Review 001

## Verdict

`REVIEW_NO_GO`

理由：發現 2 個可重現 P1。Spec axis 中 FRA-001/SCA-001、FRA-004/SCA-004 未通過；Standards axis 中 fail-closed、實際 filesystem authority、activation barrier 作為唯一 I/O authority 未通過。Production 維持 `NO-GO`。

## Findings

### RAA-REVIEW-001｜P1｜Activation token 不是 formal runtime 的必備 I/O authority

- 位置：`scripts/pantheon_content_runtime_manifest.py:307`、`scripts/pantheon_content_capability_adapter.py:44`
- 觸發條件：`PANTHEON_FORMAL_RUNTIME=1` 且 manifest env 完整，但沒有 `PANTHEON_RUNTIME_ACTIVATION_TOKEN`。
- 可重現證據：最小 public API reproducer 回傳 `{'validate_status': 'PASS', 'token_present': False, 'io_mutated': True}`。
- 最短 public call chain：`pantheon_content_capability_adapter._formal_environment()` 未設定 token → `runtime_manifest.validate_runtime_tick()` 因 token env 缺席而跳過 barrier validation → caller 繼續 queue/state I/O。
- 風險：6/7、尚未 activation、或缺 token 的七服務 formal runtime 仍可通過 runtime tick，打破「7/7 generation token 是唯一 I/O authority」。
- 建議修法：`PANTHEON_FORMAL_RUNTIME=1` 時 token 必填；`validate_runtime_tick()` 缺 token 必須 fail-closed；adapter contract/input 必須攜帶 token 並由 `_formal_environment()` 注入；所有 queue/state public entrypoint 在第一次 I/O 前使用同一 token validation。
- Validation gap：現有測試只驗 `run_after_activation_token()` helper；沒有驗 formal runtime 缺 token 時 `validate_runtime_tick()` 必須拒絕。
- Confidence：high

### RAA-REVIEW-002｜P1｜Transaction/Git path 在 fd authority 關閉後仍可 late parent-swap 外部 mutation

- 位置：`scripts/agy_content_publisher.py:638`、`scripts/agy_content_publisher.py:1376`、`scripts/agy_content_publisher.py:166`
- 觸發條件：在 initial queue/state authority 通過後、Git common-dir descendant check 返回後，將 sandbox parent 交換為外部 symlink。
- 可重現證據：late parent-swap reproducer 回傳 `{'raised': 'FileNotFoundError', 'external_entries': ['.git', '.git/agy-content-publisher.lifecycle.lock']}`。雖然最後例外退出，但 fail-closed 前已建立外部 `.git` 與 lock。
- 最短 public call chain：`formal_capability_preflight('transaction')` → `_isolated_transaction_worktree()` → `_transaction_lifecycle_lock()` → `_repo_lock_path()` → `common_dir.mkdir()` / `lock_path.open()` 使用 absolute Path。
- 風險：FRA-001/SCA-001 要求任何外部 `mkdir/open/tempfile/Git` 前 fail-closed 且 external tree before/after identical；candidate 仍會先對外部樹產生 mutation。
- 建議修法：讓 `TrustedSandboxDirectoryAuthority` 的 fd/no-follow/identity check 覆蓋整個 transaction lifecycle；Git common-dir mkdir、lock open、transaction create/remove/copy2/rmtree 都要透過 authority relative operations，或在 mutation 前不可繞過地重驗 anchor identity。
- Validation gap：現有 parent-swap test 只覆蓋 initial queue/state mkdir，不覆蓋 authority context 關閉後的 Git/lock/transaction path。
- Confidence：high

### RAA-REVIEW-003｜P2｜Operation trace runtime identity 可由 fallback 自產

- 位置：`scripts/agy_content_publisher.py:116`
- 觸發條件：未配置 `PANTHEON_RUNTIME_IDENTITY_DIGEST` 時呼叫 `formal_capability_preflight('select')`。
- 可重現證據：fallback reproducer 回傳 `{'status': 'PASS', 'trace_digest': '549596c84b6f82b0a4f1998eec0f68058b0ae43d92d9d2963aaaf383715f605f', 'env_digest_present': False}`。
- 風險：trace digest 看起來像 verified runtime identity，但來源只是 `publisher_id + correlation_id`，若 receipt consumer 採信會形成自證 identity。
- 建議修法：formal capability path 應要求 manifest/barrier 驗證後的 identity digest；fallback 必須標記 unverified，且不得讓 `status=PASS` 暗示 runtime identity verified。
- Validation gap：trace tests 只檢查 64 hex 長度，沒有區分 verified digest 與 fallback digest。
- Confidence：medium

## Spec Axis

- FRA-001 / SCA-001：未通過。late parent-swap 可在 fail-closed 前造成外部 `.git`/lock mutation。
- FRA-002 / SCA-003：部分通過。transaction create/remove 有 trace，但 trace 的 target/identity authority 仍可被 late parent-swap 與 fallback digest 削弱。
- FRA-003：部分通過。七服務 labels、manifest digest、path identity 與 mismatch checks 存在。
- FRA-004 / SCA-004：未通過。token 不是 formal runtime tick 的必填 authority，adapter 也未注入 token。

## Standards Axis

- Fail-closed：未通過，因外部 mutation 可發生在 failure 前。
- 單一 control plane：未發現第二套 queue/lock/control plane。
- 跨機可重現：固定 SHA/parent 可驗證；review reproducer 不依賴 production、network 或 launchctl。
- Scope：candidate changed files 均落在 implementation allowlist；未發現 `[DBG-` marker。

## Residual

- 指定測試矩陣通過，但未覆蓋兩個 P1 reproducer。
- Production 仍 `NO-GO`，不得 merge/push/deploy/canary。
