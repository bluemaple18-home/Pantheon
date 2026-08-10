# Verification receipt

## Identity

- Base：`f31ef017170c69543528708fd1314dc87ff7528a`
- Candidate／HEAD：`c61491e748acad43e44e73f7eabbc320dcbaa532`
- Parent：`f31ef017170c69543528708fd1314dc87ff7528a`
- Diff：87 files，4,646 insertions，201 deletions
- CodeGraph semantic query：已以 four-lane formal runtime、publisher transaction、七服務 identity/barrier/rollback 語意查詢；indexed source 對齊 candidate。

## H-001 invocation proof

以 call recorder 替換：

- `publish_ready_runs`
- `_isolated_transaction_worktree`
- `_stage_commit_tag_push`

逐一呼叫 `formal_capability_preflight(select|publish|transaction|tag|push)`：五個結果均為 `PASS`，`actual_calls=[]`。提交的正向 receipt 所列 publisher entrypoints亦僅為 preflight、normalizer、capacity preflight 或 release plan。

## Tests

- Targeted six affected test files：241 passed，0 failed，見 `targeted-suite.junit.xml`。
- Actor recovery fail-closed unit：1 passed，0 failed，見 `actor-recovery-fail-closed.junit.xml`。
- Targeted aggregate：242 passed。
- Current worktree actor scenarios：3 failed；全部在 local `git push` 的 pre-push hook，原因為 worktree 缺 `.venv/bin/python`。
- Isolated clean base：3 failed；全部在 fixture `git commit`，原因為 `nothing to commit`，未進 actor recovery。
- Isolated clean candidate：3 failed；同 base，未進 actor recovery。
- Playwright import：`ModuleNotFoundError`，因此 repository full collection blocker 可重現。

## Static verification

- `git diff --check <base> <candidate>`：PASS
- `bash -n`：publisher、coordinator、capacity 三個 installer PASS
- `plutil -lint`：四個 launchd plist template PASS
- Rollback fake identity normalization：`pid = 4242` 經 production sed normalization 後為 0 bytes。

## Safety boundary

- 未修改 candidate source、tests、installer 或 plist。
- 未執行 network、launchctl、production queue/state、正式 publisher mutation、tag、push、deploy 或 canary。
- 寫入僅限 Review 卡、task、review-orchestrator 輸出與 task-owned review evidence。
