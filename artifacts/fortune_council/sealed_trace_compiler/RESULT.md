# C-A sealed trace compiler receipt

結果：`CA_R2_IMPLEMENTATION_READY_FOR_FREEZE`

- compiler 強制 actor root 等於 module repo root、HEAD exact actor SHA、accepted base ancestor 與 git worktree clean（含 untracked）。
- source tree digest 僅接受 caller owner 的 regular files；copy 前後一致。
- evidence artifact directory 為 caller 明示的 `evidence_artifact_dir`；owner-only sibling `O_EXCL` claim 封鎖 compiler-publisher 競態，bundle / receipt 先完整寫入 0600 temp files、fsync files / directories / parent，再發布 0700 final directory。R2 bundle schema 未擴張。
- trace 實際呼叫既有 `run_writer_reviewer`，Recording client 以既有 `build_external_request` 錄取 role/model/prompt/schema identity。
- R2 bundle 已由既有 loader 與 `entry.validate_result` 驗證。runtime queue 沒有任何寫入。

真實 clean actor integration：`NOT_RUN`（freeze 前 worktree 非 clean）。

R2：18 tests PASS。包含真 git actor dirty/untracked、HEAD mismatch、base non-ancestor；claim publish race；source pre/post digest drift、symlink/owner；staging/evidence/executable/generation/repair preflight；editorial 與 translation production trace 的 R2 loader/result validator；以及 deterministic rejection 的 writer-only required trace。

主線獨立重跑 C-A focused suite 加既有 Runner regression：85 tests PASS。clean actor integration 必須在本候選 commit 建立後另行執行，未執行前不得取得 `CA_REVIEW_READY`。
