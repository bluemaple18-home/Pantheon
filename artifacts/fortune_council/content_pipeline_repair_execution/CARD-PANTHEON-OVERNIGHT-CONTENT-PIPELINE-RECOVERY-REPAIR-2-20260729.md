---
id: CARD-PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-REPAIR-2-20260729
chain_id: PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-20260729
type: implementation
role: repair_2
status: DELIVERED_REPAIR
strict: true
parent_repair_commit: 03acf19208383de1a992471e9d1cebc9ef1b80cb
re_review_evidence_commit: ce05de3dcc4cf625fbd45e12b5cc7d92658dd923
re_review_verdict: REVIEW_NO_GO
---

# Overnight content pipeline recovery — Repair 2

## 目的

只修 same-reviewer re-review 的兩項 create bounded-repair correctness
finding：

1. 初始 create payload 在 `hydrate_candidate()` 的完整 publication-policy
   validation 過早丟棄可修的 `standalone_answer`，正式
   `run_writer_reviewer()` 無法進入 answer-only bounded repair。
2. `false_social_origin` detector 掃描四個 content fields，但 Repair-1
   固定只授權 `bodySections`。

## 已確認事實與可證偽假說

- Preflight 已確認獨立 detached worktree、clean status、精確 parent HEAD、
  re-review evidence commit 存在且無 index lock。
- CodeGraph 在本 worktree 未初始化；依 allowlist 不建立索引，改以 re-review
  鎖定的五個 symbols 與相鄰 tests 限域檢查。
- 假說 A：若初始 create hydration 只做完整結構／shape validation，並將
  full policy validation 延後到 deterministic gate 清零之後，短 answer
  E2E 應由 `writer → writer → reviewer` 收斂，且不消耗 schema budget。
- 假說 B：若 `false_social_origin` 與 validator 共用同一 predicate 並逐欄
  掃描，contract 會只包含實際命中欄位；跨欄拼接但單欄無命中時會明確
  fail closed。

## 受影響介面

- `hydrate_candidate()`
- `hydrate_create_repair()`
- `validate_candidate()`
- `quality_findings()`
- `_create_repair_fields()`
- `run_writer_reviewer()`

## 唯一 allowlist

- 本卡。
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-repair-2-20260729/**`
- `scripts/agy_seo_copy_pipeline.py`
- `tests/test_agy_seo_copy_pipeline.py`

## 必修 A：初始 hydration 與 bounded repair

1. 初始 create hydration 保留 schema、identity、immutable fields 與
   `publicationPolicy` shape fail-closed validation。
2. 可修 deterministic content-policy finding 必須保存 candidate、建立
   machine-owned findings 與最小 contract。
3. 非 content、非 deterministic、無法分類或未映射 validation failure 仍
   fail closed。
4. bounded repair 成功後及最終輸出前均跑完整 `validate_candidate()`／policy
   gate。
5. E2E 證明 `writer → writer → reviewer`、`schema_repairs_used=0`、
   `content_repairs_used=1`、第二次 Writer schema 只含 `slot`+`answer`、
   Reviewer 只在 deterministic gate 歸零後呼叫，其他欄位 compact JSON
   bytes 不變。
6. content failure 不計 schema repair，不增加 budget。

## 必修 B：`false_social_origin`

1. 對 `title`、`description`、`answer`、`bodySections` 使用與 validator
   同語意 predicate 逐欄定位。
2. 單欄命中只授權該欄；多欄命中只授權實際聯集。
3. finding 存在但無單欄可定位時明確 fail closed，不 fallback。
4. detector 不移除、不放寬；優先重用 predicate 避免 drift。
5. external schema 只含 `slot` 與授權欄位；多帶欄位拒絕；hydrate 後未授權
   欄位 bytes 不變。
6. RED/GREEN 覆蓋四個單欄、多欄聯集、無法定位 fail-closed、修復後 finding
   歸零。

## 必須保持

- `standalone_answer -> answer`。
- deterministic mapping 與未映射 fail-closed。
- Reviewer 自訂 `copy`、`TEMPLATE_*` 等 bounded fallback。
- schema、identity/immutable validation、publication policy、quality gate、
  repair budget、Reviewer 契約。
- publisher preflight 與 `NEW_ONLY` coordinator 行為。

## 禁區與 residual

- 不修改 publisher、coordinator、installer、plist、docs、既有
  implementation/Review/Repair-1 evidence。
- 不操作 launchd、production publisher、queue、ledger、outbox、run state、
  registry、文章、secret、token 或 credential pool。
- 不 push、deploy、開 PR、merge、cherry-pick、改寫 main 或封存 thread。
- Publisher stale `origin/main` residual 只記錄，不在本卡修正。
- 不宣稱 `REVIEW_GO`、`ACCEPTED`、`INTEGRATED`、`CLOSED` 或 production
  fixed。

## 驗證計畫

1. 先新增正式 `run_writer_reviewer()` short-answer E2E 與
   `false_social_origin` 欄位定位 tests，執行 targeted command 取得有效
   RED。
2. 最小修改 production path 與 predicate，重跑 targeted 轉綠。
3. 執行三檔完整 regression、installer shell syntax、publisher plist lint、
   parent-to-HEAD diff check。
4. 確認 uv.lock 無 parent delta、allowlist 精確、parent 到 HEAD 恰一個
   commit、提交後 clean、無 index lock。

## 交付

Evidence 至少包含 `preflight.md`、`reproduction.md`、`implementation.md`、
`verification.md`、`result.md`。`result.md` 必列 parent、re-review
evidence、Repair-2 SHA/SELF、changed files、RED/GREEN、E2E order/counters、
full regression、P1/P2 disposition、publisher residual 與
`ready_for_same_reviewer_re_review`。
