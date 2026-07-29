# Repair-2 最終獨立 Review

## Verdict

`REVIEW_GO`

- reviewed candidate：`5cd8617a2115e5df4ce285aa62ebb071678cb9d9`
- required direct parent：`9474db388f6c84e9e988dec3fe249aa0833cb0ef`
- parent verification：PASS
- P0：0
- P1：0
- P2：0
- P3：0

本次候選只強化 rewrite Reviewer 的一般與 repair prompt。它沒有修改
strict hydration、schema、deterministic authority、repair budget，亦沒有修改
create、optimize 或 translation 路徑。Production 所見
`APPROVE + non-empty positive semantic_findings` 仍會 hard reject，不會發布。

## Preflight 與 scope

- Reviewer worktree 切換前為 clean，且 worktree `index.lock` 不存在。
- fresh fetch 後 detached 切至 reviewed candidate；切換後 HEAD 與 parent 均精確符合契約。
- 未接觸主工作區 dirty changes。
- CodeGraph 在本 Reviewer worktree 未初始化；依專案規則改用限域
  `git diff`、`rg` 與逐段 source inspection。
- candidate diff allowlist：PASS。

```text
A artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-LEGACY-REWRITE-PROVIDER-APPROVE-FINDINGS-REPAIR-2-20260730/verification.md
M scripts/agy_seo_copy_pipeline.py
M tests/test_agy_seo_copy_pipeline.py

3 files changed, 344 insertions(+)
```

## Spec axis

| Requirement | Result | Evidence |
|---|---|---|
| 一般與 repair rewrite prompt 套用同一契約 | PASS | `_rewrite_reviewer_semantic_contract()` 由 `_reviewer_prompt()` rewrite branch 與 `_repair_reviewer_prompt()` 共用 |
| findings 僅列阻塞問題；APPROVE 精確對應 `[]`；非空對應 REJECT | PASS | `scripts/agy_seo_copy_pipeline.py:3334-3340` |
| positive non-empty findings 不得被自動清除 | PASS | candidate 沒有 message sentiment filtering；production-shaped test 保留 raw payload，hydration 轉成 hard REJECT |
| hostile semantic mislabel 不得洗成 APPROVE | PASS | strict semantic hydration 與既有 hostile-mislabel regression 保留；本候選未改 reconciliation |
| cached legacy payload fail closed | PASS | 舊 `slot/verdict/findings` payload 仍因 strict rewrite fields 被拒絕 |
| 六個 rewrite hydration 入口沒有漏用其他 prompt | PASS | 一般 prompt：`run_writer_reviewer`、`review_existing_candidate`；repair prompt：`run_rewrite_repair`、`run_rewrite_release_generation`、`review_rewrite_release_final`、`run_rewrite_repair_closure` |
| create／optimize／translation 不退化 | PASS | candidate source diff 僅新增 rewrite-only helper 及兩個 rewrite prompt 插入點；完整 regression suites 通過 |

## Standards axis

| Risk | Result | Review |
|---|---|---|
| false approve | PASS | prompt 明確禁止正面評語進 findings；即使 provider 違約，`hydrate_rewrite_review()` 仍拒絕 `APPROVE + non-empty` |
| semantic Reviewer authority | PASS | semantic REJECT 必須帶 findings；finding code 即使看似 objective 也明令留在 semantic findings |
| deterministic authority | PASS | deterministic findings 仍不可忽略；本候選沒有改 machine gate 或 reconciliation |
| strict schema / provider compatibility | PASS | provider schema 未變；prompt 與既有 strict schema 一致；舊或 malformed payload fail closed |
| mode isolation | PASS | `external_review_schema()`、`hydrate_review()` 與 translation Reviewer prompt 均未修改 |
| bounded execution | PASS | 沒有修改 Writer／Reviewer call site、loop 或 repair budget |

## Finding matrix

| Severity | Count | Finding |
|---|---:|---|
| P0 | 0 | 無 |
| P1 | 0 | 無 |
| P2 | 0 | 無 |
| P3 | 0 | 無 |

## Fresh verification

所有 Python 指令均在 `<repo-root>` 執行，使用與 candidate 相同 implementation
worktree 的既有 `.venv`；未建立或修改本 Reviewer worktree `.venv`。

```text
<implementation-worktree>/.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py -q \
  -k 'rewrite_reviewer_prompts_require_empty_findings_for_approval or rewrite_provider_approve_with_positive_findings_fails_closed or rewrite_cached_legacy_review_payload_fails_closed or rewrite_ignores_false_body_shape or rewrite_semantic_reject_survives or rewrite_malformed_machine_owned or rewrite_semantic_rejection_keeps or rewrite_deterministic_reject_never or rewrite_unknown_reviewer or batch_002_isolated_runner or review_existing_rewrite or create_machine_length_repair_is_field_bounded'
15 passed, 102 deselected in 0.71s

<implementation-worktree>/.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py -q
117 passed in 64.24s

<implementation-worktree>/.venv/bin/python -m pytest \
  tests/test_agy_gemini_coordinator.py tests/test_agy_content_publisher.py -q
99 passed, 1 warning in 17.35s

<implementation-worktree>/.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py -q
19 passed in 0.08s

git diff 9474db388f6c84e9e988dec3fe249aa0833cb0ef..5cd8617a2115e5df4ce285aa62ebb071678cb9d9 --check
PASS
```

唯一 warning 是既有 `DeprecationWarning: invalid escape sequence '\\/'`，不在
candidate diff。

## Residual risk 與 production acceptance

- 本 review 未接觸真實 provider，不能證明模型每次都遵守 prompt；但違約結果仍
  由 unchanged strict hydration fail closed，因此是可用性／重試風險，不是
  false-approve 風險。
- production acceptance 仍需由 production owner 執行一次 non-publishing
  machine-clean rewrite Reviewer attempt，確認新 prompt 下
  `semantic_verdict=APPROVE` 時 `semantic_findings=[]`，並保留 provider receipt。
- 若 provider 再回 positive findings、舊 schema 或 malformed payload，必須維持
  hard reject，由外部 retry／人工處置；不得以 message 正負向推斷自動刪除。

本 Reviewer 到 evidence-only commit 為止；未修改 production code/tests，未
push、deploy 或 publish。
