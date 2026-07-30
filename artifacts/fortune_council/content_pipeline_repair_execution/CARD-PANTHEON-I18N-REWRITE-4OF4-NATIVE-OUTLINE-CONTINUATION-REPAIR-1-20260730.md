---
card_id: CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-REPAIR-1-20260730
chain_id: pantheon-i18n-rewrite-4of4-runtime-stability-p0-20260730
parent_card_id: CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-REVIEW-20260730
role: repair
cycle: 2
repair_cycle: 1
status: CARD_DRAFTED
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
project_id: local-0020d4379451d545eb08362962f1def0
repo_identity: github.com/bluemaple18-home/Pantheon
reviewed_candidate: f0b70b4bba41a952f9b8bc2c12d3a2bc5c13502e
review_evidence_commit: cc76cce1eb713ab6e1cf202392b7f4ae35c62071
required_direct_parent: cc76cce1eb713ab6e1cf202392b7f4ae35c62071
review_thread_id: 019fb1c4-9a1b-7831-a8f5-16d38db5992a
implementation_thread_id: 019fb1a9-ea89-7231-beea-75d2fea93430
mainline_thread_id: 019fb165-8174-7192-b19f-4ed19ed19426
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-REPAIR-1-20260730/
created_at: 2026-07-30 Asia/Taipei
---

# Pantheon i18n-rewrite Native Outline Continuation Repair-1

## Role and stop boundary

你是本 chain 唯一 Repair-1 owner。只修復 Review evidence commit
`cc76cce1eb713ab6e1cf202392b7f4ae35c62071` 記錄的 findings；不得擴張功能、
改 gate 強度、呼叫 provider、讀寫 production `.work`、push、deploy、publish或
建立其他 task。

完成後形成單一 repair candidate commit，回主線等待原 Reviewer targeted
re-review。不得自行宣稱 Review GO。

## Blocking findings

### P0C-REV-001 — P1 — pending rebuild article replay

目前同 generation 的 locale plan 已成功而 article pending時，重跑會把這份 plan
當 prior plan並與自己比較，觸發 `reused prior outline topology`。

修復要求：

- prior plan必須鎖定為當前 generation之前最後一個已完成 generation，或在
  continuation state中保存其 identity/hash。
- replay當前 generation時重用同 plan與同 article request identity，不得再次
  enqueue plan、前進 generation或更新 root artifacts。
- plan pending與article pending都要有 direct regression test。

### P0C-REV-002 — P1 — non-native locale plan

目前 ko plan可接受全英文 semantic fields。

修復要求：

- 對 `native_search_intent`、native query phrases、article angle、H2與coverage
  note做locale-aware wrong-script validation。
- ko／ja至少拒絕全英文或繁中主導 plan；en拒絕CJK主導 plan。
- 不可誤判proper noun、ASCII acronym、number或
  `source_structure_not_copied` blacklist。
- en／ja／ko都要有正反向 direct tests；不以外部語言套件或 provider判定。

### P0C-REV-003 — P1 — root review finding authority

目前 attempts有 external review時，第一 continuation generation會忽略root
`review.json`的 final findings。

修復要求：

- 已驗證root review必須是第一 continuation generation的最後 authority。
- deterministic/machine findings與Reviewer findings都不得遺失。
- attempts-derived review若保留，只能作歷史／repeat detection，不得蓋過root
  final review。
- regression test必須證明root-only marker進入plan repair prompt／finding input。

### P0C-REV-004 — P1 — complete replay identity drift

目前 complete state不再驗證starting review，root candidate/review可被另一份合法
payload替換後直接回傳。

修復要求：

- state鎖定starting review hash，以及terminal candidate/review hash。
- active與complete各自驗證適用identity；root drift一律fail closed。
- complete replay不得呼叫client、enqueue或改寫generation。
- transaction recovery後的terminal identity仍須一致。

### P0C-REV-005 — P1 — repeated MIRRORED_STRUCTURE

`MIRRORED_STRUCTURE` 是Reviewer hard reject卻未納入rebuild policy。

修復要求：

- 加入closed rebuild-code policy。
- 同article consecutive時觸發；cross-article與non-consecutive不得誤觸發。
- topology validator仍須拒絕只換同義heading的相同fact grouping。

## Preserved P2

### P0C-REV-006 — P2 — attempts gap

若能在不擴大變更下完成，建立state前要求attempt目錄為從`01`開始的contiguous
sequence，並驗證generation/state一致。至少不得讓本次P1修復使gap行為更寬鬆。
若不修，repair evidence必須明確保留為residual P2。

## Required source and evidence

必讀：

- Review evidence：
  `artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-REVIEW-20260730/review-evidence.md`
- Adversarial probes：
  同目錄`adversarial_review_tests.py`
- Implementation evidence：
  `artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-IMPLEMENTATION-20260730/implementation-evidence.md`

不得修改Review evidence或adversarial probe來讓測試變綠；應把阻擋案例轉成直接
regression tests並修production code。

## Allowlist

- `scripts/agy_multilingual_pipeline.py`
- `tests/test_agy_multilingual_pipeline.py`
- 只有outbox replay確實需要時才可改
  `scripts/agy_gemini_outbox.py`／`tests/test_agy_gemini_outbox.py`
- 本Repair卡專屬evidence／handoff

## Forbidden scope

- 不修改deterministic、Reviewer、SEO、canonical、安全或publication gate。
- 不修改既有Implementation／Review evidence與Review adversarial tests。
- 不手改production candidate、review、queue、approval、apply、publish或ledger。
- 不修改frontend、registry、sitemap、feed、redirect。
- 不呼叫provider、不push、不deploy、不publish。
- 不建立Review、replacement或其他task；完成後只回主線。
- 不使用hidden sub-agent。

## Verification

至少fresh執行：

```text
.venv/bin/python -m pytest \
  tests/test_agy_multilingual_pipeline.py \
  tests/test_agy_gemini_outbox.py \
  tests/test_agy_seo_copy_pipeline.py \
  tests/test_agy_content_publisher.py \
  tests/test_agy_gemini_coordinator.py \
  tests/test_agy_gemini_v4_broker.py \
  tests/test_agy_gemini_reviewer_cutover.py -q

.venv/bin/python -m pytest \
  artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-REVIEW-20260730/adversarial_review_tests.py -q

git diff --check
```

若worktree沒有`.venv`，可使用canonical checkout既有`.venv`執行相同selectors，
但不得安裝或變更外部runtime。

## Delivery

- 狀態只能是`DELIVERED_REPAIR_CANDIDATE`
- repair candidate SHA與direct parent
- P0C-REV-001..006逐項mapping
- changed files與allowlist證明
- fresh direct suite、adversarial probes、`git diff --check`
- residual risks與未執行production actions

完成後停止，回主線安排原Reviewer targeted re-review。
