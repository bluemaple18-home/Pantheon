---
id: CARD-PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-REPAIR-1-20260729
chain_id: PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-20260729
type: implementation
role: repair_1
status: DELIVERED_REPAIR
strict: true
parent_candidate: 751b4db759baf3d1990795f3ea27c5e4084a6100
review_evidence_commit: daf2642697f816f52bb68bd4143da523639c44fd
review_verdict: REVIEW_NO_GO
---

# Overnight content pipeline recovery — Repair 1

## 目的

只修獨立 Review 的阻斷性 P1：create bounded repair 對
`standalone_answer` 的欄位授權錯誤。`standalone_answer` 必須只授權
`answer`，未知 deterministic create finding 必須明確 fail closed，不得
fallback 到 `bodySections`。

## 已確認事實與假說

- 隔離 worktree、乾淨狀態、精確 parent HEAD、parent/reviewer commits 與無
  index lock 均已由 preflight 確認。
- CodeGraph 在此 worktree 未初始化；初始化會新增 allowlist 外索引，因此
  本卡使用鎖定 source/tests 的限域 fallback，不建立索引。
- 受影響 public execution seam 是 `run_writer_reviewer()` 的 create bounded
  repair；直接修改的內部介面是 `_create_repair_fields()`，下游為
  `_create_repair_contract()`、`external_create_repair_schema()` 與
  `hydrate_create_repair()`。
- 可證偽假說 A：若 P1 根因是缺少明確 mapping，加入
  `standalone_answer -> answer` 後，targeted regression 會由
  `bodySections` 轉為只允許 `answer`。
- 可證偽假說 B：若靜默 fallback 隱藏 deterministic code 缺口，移除 fallback
  並補完整 code-to-field 契約後，未知 code 會明確拋出 unmapped finding，
  既有已知 codes 仍可產生 bounded schema。

## 允許寫入

- 本卡。
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-repair-1-20260729/**`
- `scripts/agy_seo_copy_pipeline.py`
- `tests/test_agy_seo_copy_pipeline.py`

## 禁區

- 不修改 publisher、coordinator、installer、plist、docs、implementation
  evidence 或 Review evidence。
- 不放寬 schema、validator、quality gate、publication policy、repair budget
  或獨立 Reviewer 契約。
- 不改 deployment preflight 或 `NEW_ONLY` coordinator 行為。
- 不執行 launchd install/load/bootstrap/bootout/kickstart、production
  publisher、deploy、push、PR、merge、cherry-pick 或 main 改寫。
- 不 mutation queue、ledger、outbox、run state、registry 或文章；不讀取、
  列印或修改 secret、token、credential pool。

## 必修契約

1. `standalone_answer` 只映射至 `answer`。
2. 所有 deterministic create finding codes 都有明確欄位授權測試。
3. 未映射 deterministic finding 明確 fail closed。
4. repair response 只能包含 `slot` 與已授權欄位。
5. hydrate/merge 後未授權欄位內容及 compact JSON bytes 不變。
6. 短 answer bounded repair 在獨立 Reviewer 呼叫前通過 deterministic gate。
7. 不放寬既有 schema、validator、quality gate、publication policy 或 budget。
8. publisher deployment preflight 與 `NEW_ONLY` coordinator 行為不變。

## 驗證計畫

1. 先新增 targeted regression，執行
   `uv run pytest tests/test_agy_seo_copy_pipeline.py -k 'standalone_answer or repair_fields or bounded_create_repair'`，
   證明 parent candidate 因錯誤 mapping 失敗。
2. 最小修改 `_create_repair_fields()` 與必要常數，再重跑同一命令轉綠。
3. 執行完整指定 regression：
   `uv run pytest tests/test_agy_seo_copy_pipeline.py tests/test_agy_gemini_coordinator.py tests/test_agy_content_publisher.py`。
4. 執行 installer shell syntax、publisher plist lint 與
   `git diff --check 751b4db759baf3d1990795f3ea27c5e4084a6100 HEAD`。
5. 確認 `uv.lock` 無差異、parent 到 Repair HEAD 恰一個 commit、提交後
   worktree clean、無 index lock。

## 交付契約

- evidence 必含 `preflight.md`、`reproduction.md`、`implementation.md`、
  `verification.md`、`result.md`，逐項記錄命令、exit code 與摘要。
- `result.md` 列 parent candidate、Review evidence、Repair commit 完整 SHA、
  changed files、targeted red/green、full regression、P1 disposition、P2
  residual 與是否 ready for same-reviewer re-review。
- 最終狀態只可為 `DELIVERED_REPAIR`；本卡不宣稱 Review 通過、accepted、
  integrated、closed 或 production fixed。

## 已知 residual

P2：publisher deployment preflight 只比較本機 `origin/main` tracking ref，
可能受 stale ref 影響。本卡只記錄，不修改。
