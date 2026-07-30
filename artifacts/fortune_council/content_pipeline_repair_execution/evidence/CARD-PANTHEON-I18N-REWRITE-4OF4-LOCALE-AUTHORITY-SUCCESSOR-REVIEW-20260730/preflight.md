# Review preflight

- Dispatch phase：`ACTIVATED`
- Activation token：已核對與 dispatch key
  `v1:8f90c26907991b53e95ed79f61c0b6deac1a80277951bef021f94b2d4012100e`
  對應；不保存 token 本體。
- Formal thread：`019fb36b-25b3-7990-a4d7-fdb858fab6c6`
- Project binding：與 activation prompt 的 verified projectId 相符。
- Worktree：`<repo-root>`，獨立 detached worktree。
- Reviewed HEAD：`1f9b9359754d4f3959ee86afcb9d5c257605f9dd`
- Direct parent：`ce34670911a7c4691cb6a3cea851b7a805ff965e`
- 初始狀態：clean。
- Review 卡來源：mainline commit
  `3f037bbd943d2f2836bb35b9c905bd7641953b9e`。
- Review 卡來源 blob／materialized blob：
  `56d6cbb57d2adf194f0a155a844bb5717224d9ea`，精確相符，內容未改寫。
- Implementation 卡來源／candidate blob：
  `4e0f1e815d5c2ed2499d532edaba1d9a38305a92`，與 Implementation preflight
  receipt 相符。
- Candidate changed files：production、direct tests、Implementation 卡與其六個
  evidence 檔，共九檔；全部落在 amendment allowlist。
- 既有 Review probes：candidate diff 未修改。
- Candidate 掃描：未發現本機絕對路徑、已知 private-key/API-key 形狀或
  `[DBG-` instrumentation。
- CodeGraph：目前 worktree 未初始化；為避免寫入索引，依專案規則降級為只讀、
  限域 source/diff 查閱。
- Provider、production `.work`、push、deploy、publish：均未執行。
