# Preflight

- Dispatch key：`v1:b44ecef777a5bd5b603335dcd845c24c01f95f0dd125bf4dd469d3cd3dd4241a`
- Formal thread：`019fb358-d09e-71e3-9ed0-f2bba14d6a16`
- Project binding：與 activation prompt 的 verified projectId 相符。
- Worktree：`<repo-root>`，獨立 detached worktree，可寫。
- Required base ref：`codex/pantheon-p0c-locale-authority-successor-base`
- Required base SHA／初始 HEAD：`ce34670911a7c4691cb6a3cea851b7a805ff965e`
- 初始狀態：clean。
- Git index lock：不存在。
- Existing venv Python：沿用 Pantheon 既有 `.venv`，未安裝或下載依賴。
- Provider／production `.work`／push／deploy／publish：均未執行。

基線不含實體卡是已確認的 ancestry 差異。依同一 dispatch 的 amendment，從
`16db4868a6a001738d9bc27091352306cf86ab60` 精確帶入單一卡片；帶入後
`git hash-object` 為預期 blob
`4e0f1e815d5c2ed2499d532edaba1d9a38305a92`，內容未改寫。
