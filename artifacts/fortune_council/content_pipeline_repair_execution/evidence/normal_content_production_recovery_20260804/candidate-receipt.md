# Candidate receipt

- base：`cd2a36fd214e624dffbf9855f4b4f0a6861a9570`
- source patches：`6b5e4b67a136c6432b5020ad85cda9ee552d5c7c`、`1b7924abb680a47be2c10d358302178f65f8d52e`
- integration candidate：`efe69373e6326e7da07be85d1ca1ca5ceb5cbd20`
- branch：`codex/normal-content-production-recovery-20260804`（整合後確認為 `origin/main` ancestor，已安全移除 branch 與臨時 worktree）
- scope：7 個 allowlist code／test 檔；`uv.lock`、日韓 patch、delivery docs、生成內容皆未帶入。
- verification：Provider affected suite `292 passed`；Publisher combined official gate `477 passed`；changed Python `py_compile` PASS；`git diff --check` PASS。
- provider calls during candidate verification：`0`。

判定：`READY_FOR_REVIEW`。
