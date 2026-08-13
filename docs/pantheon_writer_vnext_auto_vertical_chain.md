# Writer vNext APF-002／APF-003 垂直鏈

`execute_campaign_editorial_work_item` 是 APF-001 campaign workset 到既有 Publisher 相容邊界的唯一新接點。它只接受 `matrix/new` 與 `legacy/rewrite` 的 zh-TW work item，並重新計算 `work_id`，因此來源 identity、campaign version、locale 與 lane 不可漂移。

`execute_campaign_editorial_workset` 是唯一的 bounded 自動入口：它從已驗證的 APF-001 workset 只各選一個 `new` 與 `rewrite`，以固定 lane 順序執行，且要求剛好兩項。它不建立 queue、scheduler 或 Publisher mutation；其結果仍交由既有 Publisher 的 dry-run acceptance seam 擁有後續 authority。

每個 run 的 `editorial-vnext/` 依序保存：

1. `article-brief-v2.json`：由注入的 brief factory 產生，並以 `ArticleBriefV2` 嚴格驗證。
2. `legacy-candidate.json`：由注入的 Writer 產生，必須先通過既有 `validate_candidate` 才保存。
3. `legacy-review.json`：由注入的 Reviewer 產生，必須先通過既有 `validate_review` 才保存；任何非 `APPROVE`、hard failure 或 finding 都會 fail closed。
4. `editorial-manifest-v1.json`：以既有 `EditorialManifestV1` contract 驗證，並再次呼叫 legacy candidate validator。

已存在的合格 artifact 會被重用，所以 resume 不會再次呼叫已完成 stage 的 factory、Writer 或 Reviewer。任何 artifact、run identity、article identity、candidate mode、SHA 或 review 發現漂移時，流程停止且不會產生相容結果。

`replay_campaign_editorial_workset_through_publisher` 分成兩階段：先在記憶體完整核對 new／rewrite 的 campaign work ID、run ID、article identity、candidate SHA、review SHA 與 rewrite brief，全部通過才批次映射為既有 queue/run contract，再實際呼叫 `collect_ready_runs` 與 `collect_ready_rewrite_runs`。任何漂移都在 queue 或 handoff 目錄寫入前 fail closed。此 dry-run seam 不呼叫 Publisher mutation、publication transaction、tag、push、scheduler 或外部發文，兩個 collector 都接受才回傳 `published: 0`。

## APF-003 單一 locale 翻譯鏈

`replay_campaign_editorial_workset_through_translation` 接受 APF-002 的完整雙 lane 結果，固定只處理一個受支援 locale。它先重用相同 campaign handoff preflight，再把 new candidate 與 rewrite candidate（搭配 rewrite brief 的 immutable metadata）正規化為 multilingual source snapshot。translation run ID 沿用既有 `translation_run_id(source_run_id, article_id, locale)`，因此 retry／resume 可重算且不會建立重複 run；譯文 identity 固定為 `<source_article_id>:<locale>`，不會與原文 publication identity 混淆。

兩個 lane 都在暫存目錄走完既有 `run_writer_reviewer`、`validate_translation_brief`、`validate_translation_candidate`、`pipeline.validate_review` 與 deterministic findings。只有 new／rewrite 全部通過，才呼叫既有 `enqueue_article_translations` 寫入 queue，保存 candidate／review SHA 並把 state 標成 complete。已完成且 SHA／identity 一致的 run 直接重用；source SHA、translation SHA、locale、article identity 或 review identity 任一漂移，都在 queue／handoff 新增寫入前 fail closed。

最後以同一份未發布 campaign source snapshot 呼叫未修改的 `collect_ready_translation_runs`。collector 仍執行完整 source-current、multilingual validation、Reviewer 與 deterministic acceptance，但不需把 APF candidate 寫進 production registry。此入口只回傳 `status: dry-run` 與 `published: 0`，不呼叫 publish、ledger transaction、tag、commit、push、deploy 或 production activation。

## CHECKPOINT-A 私有四 lane E2E

`execute_private_campaign_e2e` 是 APF-001～003 的唯一私有組合入口。它自行以 `repo_root`、queue/state root、`campaign_version` 與 `locale` 呼叫 `build_campaign_dry_run_workset`，再穩定選取第一個 `new`、第一個 `rewrite` 與各自唯一匹配的 `i18n-new`／`i18n-rewrite` work item；呼叫端不得手工傳入四 lane workset。缺少或重複匹配的 translation work item 都會在 Writer、Reviewer 與 Publisher collector 前拒絕。

入口在可丟棄的 staging 目錄依序執行 editorial、既有 Publisher dry-run collector 與既有 translation collector。只有四 lane 都成功才將私有 receipt 複製至呼叫端 root；翻譯失敗不會留下可被 Publisher 收集的半套結果。既有 receipt 會在 staging 與私有 root 間重綁路徑，因此 retry／resume 不重跑已完成 Writer／Reviewer／translation 工作，並回傳 contract-stable 的四 lane receipt。

## APF-004 Existing Publisher Canary Readiness

`build_apf_004_readiness_candidate` 只建立 synthetic readiness package，不建立 production canary。它重用既有 `coordinator_create_run_receipt_preflight` 產生 `create → run` receipt，再重用 `formal_capability_preflight` 覆蓋 `select → publish → transaction → tag → push`，全鏈固定 `exec-apf-004-readiness` 與 `corr-apf-004-readiness`。

APF-004 evidence 保存於 `artifacts/fortune_council/content_writer_vnext_execution/apf_004_readiness/`。`package/production-canary-capability-receipt.json` 是 ai-core official readiness gate 的輸入；`official-gate-ready.json` 必須為 `READY`，而 `official-gate-blocked.json` 以 missing-step fixture 證明 fail closed。容量證據在 `capacity/capacity-receipt.json`，包含兩個 synthetic cycle、cleanup reclaim、retention projection 與 stop-loss negative matrix。所有 APF-004 readiness receipt 都明示 `canary_created=false`、`production_mutation=false`，且未 publish、tag、push、deploy、schedule 或 production activation。
