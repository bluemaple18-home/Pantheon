# Writer vNext APF-002 垂直鏈

`execute_campaign_editorial_work_item` 是 APF-001 campaign workset 到既有 Publisher 相容邊界的唯一新接點。它只接受 `matrix/new` 與 `legacy/rewrite` 的 zh-TW work item，並重新計算 `work_id`，因此來源 identity、campaign version、locale 與 lane 不可漂移。

每個 run 的 `editorial-vnext/` 依序保存：

1. `article-brief-v2.json`：由注入的 brief factory 產生，並以 `ArticleBriefV2` 嚴格驗證。
2. `legacy-candidate.json`：由注入的 Writer 產生，必須通過既有 `validate_candidate`。
3. `legacy-review.json`：由注入的 Reviewer 產生，必須通過既有 `validate_review`；任何非 `APPROVE`、hard failure 或 finding 都會 fail closed。
4. `editorial-manifest-v1.json`：以既有 `EditorialManifestV1` contract 驗證，並再次呼叫 legacy candidate validator。

已存在的合格 artifact 會被重用，所以 resume 不會再次呼叫已完成 stage 的 factory、Writer 或 Reviewer。任何 artifact、run identity、article identity、candidate mode、SHA 或 review 發現漂移時，流程停止且不會產生相容結果。

此接點不呼叫 Publisher mutation、publication transaction、queue、scheduler 或外部發文；它的輸出僅是已驗證的 legacy candidate 與 review，交由既有 Publisher 擁有後續 authority。
