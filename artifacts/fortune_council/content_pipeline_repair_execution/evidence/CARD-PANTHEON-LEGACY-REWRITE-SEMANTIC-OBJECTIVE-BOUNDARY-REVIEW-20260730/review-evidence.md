---
id: CARD-PANTHEON-LEGACY-REWRITE-SEMANTIC-OBJECTIVE-BOUNDARY-REVIEW-20260730-EVIDENCE
status: REVIEW_GO
type: independent-review-evidence
reviewed_candidate: 6235afea4a22153cc1f436a3143557086d64d377
required_direct_parent: 3ee7b2d3becb8c07f7c62726d14412964739f628
review_thread_id: 019faef5-129f-71f1-919c-4ab9017d58c2
implementation_thread_id: 019faee9-8e56-7c83-be16-ab19d95bcea6
dispatch_key: v1:9d18a829612ae5dc9ff8eb5961cfae3bce0478791e7e738e7a154c84977d0ec0
activation_token: act-v1:1d93a406f2de18dd2dfc7079f00f6c9cbd477133bba39836b4631f93ab6a878e
---

# Legacy rewrite semantic/objective boundary independent review evidence

## Verdict

`REVIEW_GO`

未發現 P0／P1 finding。Candidate 可進入主線整合；本 Review 不授權 push、
merge、deploy、production publish 或其他後續狀態變更。

## Reviewed scope

- Candidate：`6235afea4a22153cc1f436a3143557086d64d377`
- Direct parent：`3ee7b2d3becb8c07f7c62726d14412964739f628`
- Candidate 確認為上述 parent 的 direct child。
- Candidate diff 僅包含：
  - `scripts/agy_seo_copy_pipeline.py`
  - `tests/test_agy_seo_copy_pipeline.py`
  - 本卡 implementation evidence
- Review 本身只新增本檔，未修改 production code、測試、queue、receipt、
  approval、ledger、文章內容、registry 或共享生成檔。

## Findings

未發現阻塞問題。

### Spec axis

- `hydrate_rewrite_review()` 現在是 rewrite semantic/objective reconciliation 的
  中央點；normal rewrite、isolated repair、release generation、release
  reviewer-only、deterministic closure 與 review-existing caller 都經過此函式。
- Pure exact canonical machine-owned `semantic_findings` 會被移除；若原 verdict
  為 `REJECT` 且 findings 清空，會提升為 `APPROVE`。
- Mixed findings 只移除 exact canonical machine-owned code，未知／真正 semantic
  finding 保留，verdict 維持 `REJECT`。
- 大小寫變體不會被 semantic reconciliation 猜測接受；既有 hostile-label
  regression 證明 `BODY_SHAPE_VIOLATION` 仍保留為 semantic finding。
- `objective_observations.code` 改為 exact lowercase canonical enum membership；
  大小寫或 alias 會以 invalid reviewer payload fail closed。
- Create mode 仍使用既有 case-normalized reconciliation，未被 rewrite 的
  `exact_codes=True` 改變。

### Standards axis

- Schema 與 JSON field validation 維持 strict；malformed finding、欄位集合、
  verdict／findings 關係、slot 與 candidate hash 仍 fail closed。
- Deterministic findings 在 Reviewer 前阻擋，且 Reviewer 結果後仍會重新附加；
  本次變更沒有放寬 deterministic gate、禁詞、內容政策或 immutable identity。
- 新增參數以 keyword-only 暴露，預設值保留 create caller 的既有行為。

## Caller coverage

限域原始碼檢查確認以下 rewrite 路徑皆呼叫 `hydrate_rewrite_review()`：

1. `run_writer_reviewer()`
2. `run_rewrite_repair()`
3. `run_rewrite_release_generation()`
4. `review_rewrite_release_final()`
5. `run_rewrite_repair_closure()`
6. `review_existing_candidate()`

未發現 rewrite 外部 review 直接呼叫 `hydrate_review()` 而繞過中央契約的路徑。

## Verification

所有 pytest 驗證均以 production actor 既有唯讀 interpreter 執行：
`<production-actor>/.venv/bin/python`（Python 3.11.14、pytest 9.0.3）。

### Lineage、scope 與 diff

```text
git rev-parse HEAD
git rev-parse 6235afea4a22153cc1f436a3143557086d64d377^
git show -s --format='%H%n%P%n%an%n%ad%n%s' --date=iso-strict \
  6235afea4a22153cc1f436a3143557086d64d377
git diff --stat \
  3ee7b2d3becb8c07f7c62726d14412964739f628..6235afea4a22153cc1f436a3143557086d64d377
git diff --name-status \
  3ee7b2d3becb8c07f7c62726d14412964739f628..6235afea4a22153cc1f436a3143557086d64d377
```

結果：PASS。Direct parent 與 allowlist 均符合契約。

### Targeted regressions

```text
<production-actor>/.venv/bin/python -m pytest -q \
  tests/test_agy_seo_copy_pipeline.py::test_rewrite_ignores_false_body_shape_review_without_spending_writer_repair \
  tests/test_agy_seo_copy_pipeline.py::test_rewrite_review_schema_uses_canonical_objective_code_enum \
  tests/test_agy_seo_copy_pipeline.py::test_hydrate_rewrite_review_removes_only_machine_owned_semantic_findings \
  tests/test_agy_seo_copy_pipeline.py::test_hydrate_rewrite_review_requires_exact_objective_code \
  tests/test_agy_seo_copy_pipeline.py::test_rewrite_reviewer_prompts_require_exact_review_contract \
  tests/test_agy_seo_copy_pipeline.py::test_rewrite_semantic_reject_survives_machine_owned_code_label \
  tests/test_agy_seo_copy_pipeline.py::test_review_existing_rewrite_reconciles_misplaced_machine_finding \
  tests/test_agy_seo_copy_pipeline.py::test_machine_gate_reconciliation_preserves_semantic_reviewer_rejection
```

結果：`8 passed in 0.04s`。

### Complete SEO copy pipeline

```text
<production-actor>/.venv/bin/python -m pytest -q \
  tests/test_agy_seo_copy_pipeline.py
```

結果：`121 passed in 58.51s`。

### Coordinator、publisher、multilingual 與相鄰 SEO suites

```text
<production-actor>/.venv/bin/python -m pytest -q \
  tests/test_seo_publish_gate.py \
  tests/test_competitor_seo_tool.py \
  tests/test_agy_gemini_coordinator.py \
  tests/test_agy_content_publisher.py \
  tests/test_agy_multilingual_pipeline.py
```

結果：`152 passed in 16.29s`；一則既有 `DeprecationWarning`：
`tests/test_agy_content_publisher.py::test_preflight_test_command_selectors_resolve_to_top_level_tests`
觸發 `<unknown>:1545: invalid escape sequence '\\/'`。非本 candidate 引入且不阻擋。

### Diff check

```text
git diff --check \
  3ee7b2d3becb8c07f7c62726d14412964739f628..6235afea4a22153cc1f436a3143557086d64d377
```

結果：PASS，無輸出。

## Test accounting

- Targeted regressions：8 passed；為 SEO suite 子集合，不重複計入總數。
- 完整 SEO copy pipeline：121 passed。
- Coordinator／publisher／multilingual／相鄰 SEO suites：152 passed。
- 不重複總數：273 passed。

## Tooling note

依 Review 規則先查 CodeGraph，但本 worktree 尚未初始化：

```text
CodeGraph not initialized in <repo-root>. Run 'codegraph init' in that project first.
```

因此依專案規則降級為限域 `rg`、`sed` 與完整 candidate diff；未初始化或寫入
CodeGraph index。

## Blocking issues

無。

## Residual risk

- 本 Review 使用 test doubles 與本機測試，未重放真實 Gemini provider response、
  production receipt 或 coordinator runtime；這些屬後續 runtime 驗收，不阻擋本
  candidate 整合。
- Reconciliation 以 exact canonical code 作 deterministic authority 邊界；若外部
  Reviewer 錯把真正 semantic 問題標成 exact lowercase machine-owned code，該 finding
  會依已鎖定契約被移除。Prompt、schema 與大小寫／未知 code fail-closed regression
  已降低此操作風險，但無法以 message heuristic 猜測修正 Reviewer 的錯誤分類。
