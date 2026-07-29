# Integration v2.1 provenance

## Decision

本卡不執行 code merge。Verified remote main
`baa29d87fd472da5ceeea7b10a1eaf7311baa8b5` 已是 reviewed candidate
`39a3a9f23720e158bd2cf9e630901f9debbceb15` 的直接三代祖先；candidate 可由
remote main fast-forward 接收。

執行線只在 candidate tip 依序新增：

1. Integration card commit：
   `f3f36ae40230df26c0bfb4356b67ccd063e9a6f5`
2. 唯一 evidence/finalization commit：`SELF`，完整 SHA 由正式 delivery
   response 回報。

未執行 merge、cherry-pick、rebase、squash、patch、amend或歷史改寫。

## Fixed lineage

```text
baa29d87fd472da5ceeea7b10a1eaf7311baa8b5
  -> 751b4db759baf3d1990795f3ea27c5e4084a6100
  -> 03acf19208383de1a992471e9d1cebc9ef1b80cb
  -> 39a3a9f23720e158bd2cf9e630901f9debbceb15
  -> f3f36ae40230df26c0bfb4356b67ccd063e9a6f5
  -> SELF (evidence/finalization commit)
```

Review evidence `f0254a0ff701e1a11ecb8235b9198b4c4e11398b` 固定
reviewed candidate 為 `39a3a9f...`，final verdict 為 `REVIEW_GO`、findings
為 0。

## Changed-files contract

`baa29d87...39a3a9f...` 精確為既有 27 paths；其 path-list SHA-256 為：

`2791af88a94893af9270a5316ffa273feed2a0b2d8f8dadc0c53e2cd0481e2cd`

`39a3a9f...` 之後只允許：

- `artifacts/fortune_council/content_pipeline_repair_execution/CARD-PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-INTEGRATION-20260729.md`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-integration-20260729/**`

Candidate 27 paths 相對 `39a3a9f...` 無 blob delta；`uv.lock` 相對
`39a3a9f...` 無變更。

## Excluded fork

Local `f432f078b2c76c7d474a2d09e0d9a68f33074573` 是 canonical-host pending
fork。它不是本 delivery candidate 的 ancestor、parent或patch source；本卡未
修改、搬運或清理該 fork。

## Production boundary

- 未 push、未建立 PR、未 merge 到實際 main。
- 未 deploy、未操作 launchd或啟動 publisher。
- 未修改 queue、ledger、outbox、run state、registry或文章。
- 未讀取、列印或修改 secret、token、credential pool。
- 本卡不宣稱 production fixed、`INTEGRATED`、`CLOSED` 或已上線。
