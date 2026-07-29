# Overnight content pipeline recovery — Integration v2.1 result

```text
card_id: CARD-PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-INTEGRATION-20260729
chain_id: PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-20260729
status: DELIVERED_INTEGRATION_CANDIDATE
verified_remote_main: baa29d87fd472da5ceeea7b10a1eaf7311baa8b5
reviewed_candidate: 39a3a9f23720e158bd2cf9e630901f9debbceb15
review_evidence: f0254a0ff701e1a11ecb8235b9198b4c4e11398b
card_commit: f3f36ae40230df26c0bfb4356b67ccd063e9a6f5
final_tip: SELF (完整 SHA 由正式 thread delivery response 回報)
branch: codex/overnight-content-pipeline-recovery-integration-20260729
candidate_delta_paths: 27
candidate_blob_equivalence: PASS
uv_lock_equivalence: PASS
context: CONTEXT_DEGRADED
push: not_performed
deploy: not_performed
production_fixed: not_claimed
integrated: not_claimed
```

## Result

Reviewed candidate 已在同一 lineage 上補入獨立 Integration card 與唯一
evidence/finalization commit；delivery branch tip 是可由 verified remote main
`baa29d87...` fast-forward 接收的乾淨 Integration candidate。

## Ancestry

- `baa29d87fd472da5ceeea7b10a1eaf7311baa8b5`：final tip ancestor。
- `39a3a9f23720e158bd2cf9e630901f9debbceb15`：final tip ancestor。
- `f3f36ae40230df26c0bfb4356b67ccd063e9a6f5`：finalization 的直接 parent。
- `f432f078b2c76c7d474a2d09e0d9a68f33074573`：不是 final tip ancestor；
  維持 canonical-host pending fork。

## Changed-files allowlist

Candidate 的既有 27 paths 相對 `39a3a9f...` 全部 blob-equivalent。新增寫入
精確限制為 current Integration card 與：

- `preflight.md`
- `integration.md`
- `verification.md`
- `result.md`

Evidence directory：
`artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-integration-20260729/`

## Verification summary

- Targeted pipeline regression：`10 passed, 88 deselected`
- Pipeline/coordinator/publisher regression：`192 passed`
- Web regression：`71 passed, 2 warnings`
- Installer shell syntax：PASS
- Publisher plist lint：PASS
- `git diff --check baa29d87... HEAD`：PASS
- 27-path blob equivalence：PASS
- `uv.lock` equivalence：PASS
- Final branch tip / clean worktree / no index lock：PASS

## Publisher residual

Review evidence 保留的 publisher P2 residual 為 `open_out_of_scope`：先前
deployment preflight 只比較當時可能 stale 的 local `origin/main` tracking ref。
本卡雖以 fresh `ls-remote` 鎖定 remote main，但未執行 publisher deployment
preflight、production cutover或任何新的 production-safety 驗證，因此不把該
P2 升級為本 Integration blocker，也不宣稱它已解決。

## Boundary

本結果僅代表 `DELIVERED_INTEGRATION_CANDIDATE`。未 push、未 deploy、未操作
launchd或 production、未 merge 到實際 main；不代表 `INTEGRATED`、`CLOSED`
或 production fixed。
