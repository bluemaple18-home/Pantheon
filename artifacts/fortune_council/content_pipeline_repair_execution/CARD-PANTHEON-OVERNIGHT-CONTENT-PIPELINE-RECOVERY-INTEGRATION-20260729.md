---
id: CARD-PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-INTEGRATION-20260729
chain_id: PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-20260729
version: 2.1
status: DELIVERED_INTEGRATION_CANDIDATE
type: integration
role: mainline_integration_candidate
ownership: integration
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
source_kind: reviewed_candidate_commit
source_sha: 39a3a9f23720e158bd2cf9e630901f9debbceb15
verified_remote_main_sha: baa29d87fd472da5ceeea7b10a1eaf7311baa8b5
review_evidence_sha: f0254a0ff701e1a11ecb8235b9198b4c4e11398b
branch: codex/overnight-content-pipeline-recovery-integration-20260729
---

# Pantheon overnight content pipeline recovery — Integration v2.1

## 身分與狀態

- Card ID：`CARD-PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-INTEGRATION-20260729`
- Chain ID：`PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-20260729`
- 狀態：`DELIVERED_INTEGRATION_CANDIDATE`
- 角色：`mainline_integration_candidate`
- Ownership：`integration`
- 交付狀態上限：`DELIVERED_INTEGRATION_CANDIDATE`
- 正式 main 尚未接收前，不得宣稱 `INTEGRATED`、`CLOSED`、production fixed 或已上線。

## Root question

在不帶入 dirty local main／`f432f078b2c76c7d474a2d09e0d9a68f33074573`
canonical-host fork、不改 reviewed candidate 既有 27-path delta、也不執行 push、
deploy 或 production 操作的前提下，將
`39a3a9f23720e158bd2cf9e630901f9debbceb15` 提升為可由 verified remote main
`baa29d87fd472da5ceeea7b10a1eaf7311baa8b5` 快轉接收的乾淨 delivery
candidate。

## v2.1 mainline re-arbitration

原 v2 決策把 local `main` 的 `f432f078...` 當成 Integration target。唯讀
`git merge-tree` 證明該 target 會把 canonical-host fork 的 505 個
mainline-only web artifacts 帶入衝突，因此已由主線重新分類為 target 選錯，
不是 candidate defect。

v2.1 以 fresh remote receipt 為準：

- `git ls-remote origin refs/heads/main`：
  `baa29d87fd472da5ceeea7b10a1eaf7311baa8b5`
- local `origin/main`：
  `baa29d87fd472da5ceeea7b10a1eaf7311baa8b5`
- Reviewed candidate：
  `39a3a9f23720e158bd2cf9e630901f9debbceb15`
- Candidate lineage：
  `baa29d87... -> 751b4db7... -> 03acf192... -> 39a3a9f2...`
- Review evidence：
  `f0254a0ff701e1a11ecb8235b9198b4c4e11398b`
- Review verdict：`REVIEW_GO`、0 findings、P1/P2 resolved、Spec PASS、
  Standards PASS。
- Local `f432f078...`：獨立 `pending fork`，明確排除於本 Integration。

本卡不做 code merge、cherry-pick、rebase、squash、patch、amend 或歷史改寫。
Delivery branch 已安全指向 reviewed candidate；本卡只新增 card 與 evidence
commits。

## Model receipt

- Thickness：`strict`
- Risk：`high`
- Model：`gpt-5.6-sol`
- Reasoning：`high`
- Model reason：跨模組 production pipeline recovery 的 provenance、驗證與
  delivery boundary 具高回退成本；使用主線 strict 跑道保留 fail-closed
  判定與可重現 evidence。

## Context receipt

- Canonical capability tool：
  `<ai-core>/scripts/worktree_capability_preflight.sh`
- Capability check：`provisioning=ready`、`python_tests=ready`、
  `node_tests=needs_prepare`、`codegraph=needs_prepare`、
  `code_context=not_ready`
- CodeGraph tool query：此 worktree 未初始化。
- Context state：`CONTEXT_DEGRADED`
- Degraded scope：本卡不做 source decision；限域使用固定 SHA、Git ancestry、
  27-path blob equivalence、`git diff --check` 與實際 tests 驗證。
- 禁止為本卡安裝 Node、初始化下載型工具或修改 lockfile。

## Previous binding

- Previous card：
  `CARD-PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-REVIEW-20260729`
- Previous thread：`019fab71-3d51-7733-a1a5-66884de74bfd`
- Previous reviewed worktree：僅作歷史 receipt，不作可照抄路徑。
- Dispatcher：current root/mainline thread。
- 本 Integration thread/worktree 與 previous identity 不同。

## Candidate 27-path delta

相對 `baa29d87fd472da5ceeea7b10a1eaf7311baa8b5`，reviewed candidate 必須只含：

1. `artifacts/fortune_council/content_pipeline_repair_execution/CARD-PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-IMPLEMENTATION-20260729.md`
2. `artifacts/fortune_council/content_pipeline_repair_execution/CARD-PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-REPAIR-1-20260729.md`
3. `artifacts/fortune_council/content_pipeline_repair_execution/CARD-PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-REPAIR-2-20260729.md`
4. `artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-implementation-20260729/preflight.md`
5. `artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-implementation-20260729/reproduction.md`
6. `artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-implementation-20260729/result.md`
7. `artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-implementation-20260729/verification.md`
8. `artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-repair-1-20260729/implementation.md`
9. `artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-repair-1-20260729/preflight.md`
10. `artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-repair-1-20260729/reproduction.md`
11. `artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-repair-1-20260729/result.md`
12. `artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-repair-1-20260729/verification.md`
13. `artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-repair-2-20260729/implementation.md`
14. `artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-repair-2-20260729/preflight.md`
15. `artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-repair-2-20260729/reproduction.md`
16. `artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-repair-2-20260729/result.md`
17. `artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-repair-2-20260729/verification.md`
18. `docs/pantheon_deployment_workflow.md`
19. `docs/pantheon_gemini_outbox_runner.md`
20. `ops/launchd/com.pantheon.agy-content-publisher.plist.example`
21. `scripts/agy_content_publisher.py`
22. `scripts/agy_gemini_coordinator.py`
23. `scripts/agy_seo_copy_pipeline.py`
24. `scripts/install_agy_content_publisher_launchd.sh`
25. `tests/test_agy_content_publisher.py`
26. `tests/test_agy_gemini_coordinator.py`
27. `tests/test_agy_seo_copy_pipeline.py`

## Allowed writes

只允許：

1. 本卡：
   `artifacts/fortune_council/content_pipeline_repair_execution/CARD-PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-INTEGRATION-20260729.md`
2. 本卡 evidence：
   `artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-integration-20260729/**`

Reviewed candidate 27-path delta 不得產生任何新 blob；`uv.lock` 不得變更。

## Forbidden scope

- 不得搬運 local main、`f432f078...` 或任何 dirty/untracked path。
- 不得修改 candidate 的 code、tests、docs、plist、installer、舊 card 或舊 evidence。
- 不得修改 queue、ledger、outbox、run state、registry 或文章。
- 不得讀取、列印或修改 secret、token、credential pool。
- 不得操作 launchd、publisher、deploy、push、PR 或實際 main branch。
- 不得建立替代 branch、封存／刪除 thread、清理 worktree/branch。
- 不得宣稱 production fixed、`INTEGRATED`、`CLOSED` 或已上線。

## Required verification

以下命令必須執行並在 evidence 記錄 exit code 與摘要：

1. `.venv/bin/pytest tests/test_agy_seo_copy_pipeline.py -k 'standalone_answer or false_social_origin or repair_fields or bounded_create_repair or run_writer_reviewer'`
2. `.venv/bin/pytest tests/test_agy_seo_copy_pipeline.py tests/test_agy_gemini_coordinator.py tests/test_agy_content_publisher.py`
3. `.venv/bin/pytest tests/test_web.py`
4. `bash -n scripts/install_agy_content_publisher_launchd.sh`
5. `plutil -lint ops/launchd/com.pantheon.agy-content-publisher.plist.example`
6. `git diff --check baa29d87fd472da5ceeea7b10a1eaf7311baa8b5 HEAD`

另須驗證：

- `baa29d87...` 與 `39a3a9f...` 都是 final tip ancestors。
- `f432f078...` 不是 final tip ancestor。
- Candidate 原有 27 paths 相對 `39a3a9f...` blob-equivalent。
- `uv.lock` 相對 `39a3a9f...` 無變更。
- `baa29d87...39a3a9f...` 的 delta 精確為既有 27 paths。
- `39a3a9f...HEAD` 的新增寫入只限本卡與本 evidence path。
- Final branch tip 等於 final SHA。
- 最終 worktree clean、無 index lock。

## Evidence contract

至少建立：

- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-integration-20260729/preflight.md`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-integration-20260729/integration.md`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-integration-20260729/verification.md`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-integration-20260729/result.md`

Result 必列 verified remote main、candidate、review evidence、card commit、final tip、
ancestry、27-path blob equivalence、changed-files allowlist、測試摘要、local
`f432f078...` pending fork、publisher stale-origin/main P2 residual與
production/integration boundary。

## Success criteria

- Delivery branch 以 `39a3a9f...` 為 reviewed base。
- 本卡獨立 card commit 可追溯。
- 全部 required verification 通過。
- 四份 evidence 與本卡 final 狀態以唯一 finalization commit 提交。
- Final branch tip 為可由 verified remote main 快轉接收的乾淨
  `DELIVERED_INTEGRATION_CANDIDATE`。

## Delivery receipt

- Card commit：`f3f36ae40230df26c0bfb4356b67ccd063e9a6f5`
- Card commit parent：`39a3a9f23720e158bd2cf9e630901f9debbceb15`
- Finalization commit：`SELF`；完整 SHA 由正式 thread delivery response 回報。
- Branch：`codex/overnight-content-pipeline-recovery-integration-20260729`
- Result：`DELIVERED_INTEGRATION_CANDIDATE`
- Boundary：未 push、未 deploy、未操作 production、未宣稱 `INTEGRATED`。
