# Review preflight

- Dispatch phase：`ACTIVATED_REVIEW`。
- Activation：已核對與 dispatch key 對應；不保存 token 本體。
- Formal thread：`019fbbf3-d906-7501-b3df-77257f9080d7`。
- Project binding：與 activation prompt 的 expected projectId 相符。
- Worktree：`<repo-root>`，平台配置的獨立 detached worktree。
- Reviewed HEAD：`cd3833212ad64af0a1b016c7cc7206464bb8575e`。
- Direct parent：`800fba7278b59667269743de7837ea5d579658bc`。
- 初始 worktree：clean。
- Implementation worktree：同一 candidate，且初始 tracked state clean。
- Python capability：本 Review 最終使用 Implementation worktree 的既有 `.venv`
  symlink；`pytest 9.0.3`，未下載 dependency。
- Capability receipt：先前 sandbox prepare 因全域 cache 權限與 registry 解析失敗而
  中止，輸出明列 `downloaded 0`；收到追加限制後不再執行 prepare 或任何
  registry/network retry。其後一次已核准的 `UV_OFFLINE=1` 本地 prepare 雖成功，
  但產生的 review-local `.venv` 已移至 repo 外的 local-only 暫存備份保留，未作為
  驗證環境。
- CodeGraph：初始 query 回報 worktree 未初始化；雖曾產生 worktree-local index，
  依追加指示最終記為 `CONTEXT_DEGRADED`，source decision 只採固定 candidate diff
  與限域 `rg` 確認。
- Node：不在 required verification；未執行 Node tests，未做 registry retry。
- Provider、production replay、push、merge、deploy、publish、tag、Lane/launchctl：
  均未執行。
