# Runtime Authority Activation Review 002

## Verdict

`REVIEW_NO_GO`

理由：`RAA-REVIEW-001` 的 missing-token / 6-of-7 / stale-token 路徑已獨立重現為零 I/O fail-closed，`RAA-REVIEW-003` 的 unverified identity 也已 fail-closed；但 `RAA-REVIEW-002 P1` 尚未完全關閉。Repair-1 只覆蓋了 Git-root swap 與 transaction create/remove，沒有覆蓋 lifecycle lock open 之後的 stale transaction cleanup。獨立 reproducer 證明 external tree before/after 不一致。

Production 維持 `NO-GO`。未執行 Repair、merge、push、deploy、production、canary 或服務啟動。

## Findings

### RAA-REVIEW-002｜P1｜Stale transaction cleanup 在 lock-open 後仍可 late parent-swap 外部刪除

- 位置：`scripts/agy_content_publisher.py:1444`、`scripts/agy_content_publisher.py:1461`、`scripts/agy_content_publisher.py:1462`、`scripts/agy_content_publisher.py:1494`
- 觸發條件：`formal_capability_preflight("transaction")` 開啟 lifecycle lock 後、執行 `_cleanup_stale_transaction_worktrees()` 前，sandbox parent 被替換成 external symlink，且 external `publisher-state` 內已有 `transaction-*` stale tree。
- 可重現證據：`public_reproducer.py` 的 `post_lock_cleanup_swap` 回傳 `status=BLOCKED`、`error="PublishBlocked: publisher sandbox authority identity drift"`，但同時 `external_tree_identical=false`、`external_stale_exists=false`、`external_marker_exists=false`。也就是 fail-closed 前已刪除 external `publisher-state/transaction-escape/repo/marker.txt`。
- 風險：FRA-001/SCA-001 要求任何外部 mkdir/open/tempfile/Git/cleanup 前 fail-closed 且 external tree before/after identical。Repair-1 仍讓 cleanup path 使用 ordinary absolute `state_root.iterdir()`、`transaction_root.exists()`、`shutil.rmtree()`，filesystem authority 沒有覆蓋完整 transaction lifecycle。
- 建議修法：formal capability mode 下讓 `TrustedSandboxDirectoryAuthority` 覆蓋 stale cleanup：以 held sandbox fd 列舉 `state_root` 相對路徑，拒絕 symlink，對 `transaction-*` 用 `sandbox_authority.remove_tree()` 清理，並在每個 cleanup mutation 前後 `assert_current()`。避免 absolute Path cleanup fallback。
- Validation gap：Repair-1 新增測試覆蓋 Git-root late swap，但沒有覆蓋 lock-open 後 cleanup drift。targeted suite 通過仍無法證明此路徑安全。
- Confidence：high

## 原 Finding 重驗

- `RAA-REVIEW-001 P1`：已關閉。missing token、6/7 ack、stale token 均在 queue/state I/O 前拒絕；public reproducer 的 I/O count 皆為 0。adapter contract 現在要求 activation token。
- `RAA-REVIEW-002 P1`：未關閉。Git-root late swap 子路徑已關閉，但 lock-open 後 stale cleanup 子路徑仍可外部 mutation。
- `RAA-REVIEW-003 P2`：已關閉。missing `runtime_receipt` 時 publisher preflight 拒絕；verified trace 使用 receipt digest。

## Spec Axis

- FRA-004 / SCA-004：通過本次 re-review。activation token 已是 formal runtime I/O 前必備 authority。
- FRA-001 / SCA-001：未通過。`_cleanup_stale_transaction_worktrees()` 仍可在 fail-closed 前刪除 external tree。
- Trace identity：通過本次 re-review。unverified digest 不再自證 PASS。

## Standards Axis

- Fail-closed：未通過，因 cleanup mutation 可發生在 authority drift 報錯之前。
- Scope：Repair changed files 為 11 個，落在 Repair-1 allowlist；本 re-review 僅新增 allowlist card/evidence。
- Production boundary：未操作 production/network/launchctl/deploy。

## Verification

- `git rev-parse HEAD`：`63d9cd29b1de666bc17df8f031267d279466964e`
- `git rev-parse HEAD^`：`72743258f602e7cce07463bea87849e00a7d1ee1`
- CodeGraph semantic query：`CAPABILITY_READY / CONTEXT_READY`
- Candidate diff check：PASS
- Public reproducer：PASS as evidence; includes one P1 failure under `post_lock_cleanup_swap`
- Targeted suite：`269 passed, 1 warning in 46.85s` using `/Users/mattkuo/Documents/Pantheon/.venv/bin/python` against this worktree source with `PYTHONPATH=.`

## Residual

- This worktree does not contain `<repo-root>/.venv/bin/python`; the card-specified interpreter command could not run locally. System Python also lacks pytest. I used the existing Pantheon venv interpreter as an environment fallback and recorded that gap.
- `repair_receipt.md` still has placeholder candidate SHA text; treated as non-blocking P3 evidence issue per card.
