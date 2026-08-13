# Writer vNext APF-002 垂直鏈

`execute_campaign_editorial_work_item` 是 APF-001 campaign workset 到既有 Publisher 相容邊界的唯一新接點。它只接受 `matrix/new` 與 `legacy/rewrite` 的 zh-TW work item，並重新計算 `work_id`，因此來源 identity、campaign version、locale 與 lane 不可漂移。

`execute_campaign_editorial_workset` 是唯一的 bounded 自動入口：它從已驗證的 APF-001 workset 只各選一個 `new` 與 `rewrite`，以固定 lane 順序執行，且要求剛好兩項。它不建立 queue、scheduler 或 Publisher mutation；其結果仍交由既有 Publisher 的 dry-run acceptance seam 擁有後續 authority。

每個 run 的 `editorial-vnext/` 依序保存：

1. `article-brief-v2.json`：由注入的 brief factory 產生，並以 `ArticleBriefV2` 嚴格驗證。
2. `legacy-candidate.json`：由注入的 Writer 產生，必須先通過既有 `validate_candidate` 才保存。
3. `legacy-review.json`：由注入的 Reviewer 產生，必須先通過既有 `validate_review` 才保存；任何非 `APPROVE`、hard failure 或 finding 都會 fail closed。
4. `editorial-manifest-v1.json`：以既有 `EditorialManifestV1` contract 驗證，並再次呼叫 legacy candidate validator。

已存在的合格 artifact 會被重用，所以 resume 不會再次呼叫已完成 stage 的 factory、Writer 或 Reviewer。任何 artifact、run identity、article identity、candidate mode、SHA 或 review 發現漂移時，流程停止且不會產生相容結果。

`replay_campaign_editorial_workset_through_publisher` 分成兩階段：先在記憶體完整核對 new／rewrite 的 campaign work ID、run ID、article identity、candidate SHA、review SHA 與 rewrite brief，全部通過才批次映射為既有 queue/run contract，再實際呼叫 `collect_ready_runs` 與 `collect_ready_rewrite_runs`。任何漂移都在 queue 或 handoff 目錄寫入前 fail closed。此 dry-run seam 不呼叫 Publisher mutation、publication transaction、tag、push、scheduler 或外部發文，兩個 collector 都接受才回傳 `published: 0`。
