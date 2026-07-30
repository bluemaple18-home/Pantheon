---
card_id: CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-REPAIR-2-20260730
chain_id: pantheon-i18n-rewrite-4of4-runtime-stability-p0-20260730
parent_card_id: CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-REPAIR-1-20260730
role: repair
cycle: 2
repair_cycle: 2
status: CARD_DRAFTED
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
project_id: local-0020d4379451d545eb08362962f1def0
repo_identity: github.com/bluemaple18-home/Pantheon
repair_1_candidate: bcb1ae53215996a9d4504bdb3247e1090afbb3ee
targeted_re_review_evidence_commit: 5d75d1802e379e022ae5682fd9d6ebe019d804f6
required_direct_parent: 5d75d1802e379e022ae5682fd9d6ebe019d804f6
repair_thread_id: 019fb1d1-f44f-7401-8f8f-78c6e4ddbc26
review_thread_id: 019fb1c4-9a1b-7831-a8f5-16d38db5992a
mainline_thread_id: 019fb165-8174-7192-b19f-4ed19ed19426
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-REPAIR-2-20260730/
created_at: 2026-07-30 Asia/Taipei
---

# Pantheon i18n-rewrite Native Outline Continuation Repair-2

## Role and hard stop

重用既有Repair thread `019fb1d1-f44f-7401-8f8f-78c6e4ddbc26`，只修targeted
re-review留下的兩筆P1：

- `P0C-REREV-001`
- `P0C-REREV-002`

這是strict chain第二代、最後一代Repair。禁止新增功能、順手重構、改動已關閉
findings、建立其他task或自行宣稱Review GO。完成後只交付單一Repair-2 candidate，
回主線交給同一原Reviewer targeted re-review。

## Root question

如何讓later-generation plan pending replay保持完全相同的prompt／request identity，
並讓locale plan在article phase前逐欄拒絕錯語言的query／outline authority，而不
誤拒proper nouns、ASCII acronyms、numbers或合法母語內容？

## Preserved evidence

Base `5d75d1802e379e022ae5682fd9d6ebe019d804f6`包含：

- Repair-1 candidate `bcb1ae53215996a9d4504bdb3247e1090afbb3ee`
- 原Review evidence與`adversarial_review_tests.py`
- targeted re-review evidence與`targeted_re_review_probes.py`

不得修改上述Review evidence或probe來讓結果變綠。

## Repair slices

### R2-SL-01 — Canonical structured prompt replay

`traces_to: P0C-REREV-001`

Confirmed failure：

- generation 04完成後，generation 05 plan第一次使用in-memory `prior_plan`。
- plan pending後重跑，`prior_plan`來自sorted-key JSON artifact。
- `_plan_prompt()`對structured fragment未canonical serialize，prompt SHA與
  Outbox request identity漂移。

Required behavior：

1. Plan prompt中的所有structured fragments使用同一canonical serialization
   規則；至少`prior_plan`、findings、source fact package、structure blacklist與
   rebuild authority不得受dict insertion order影響。
2. 同logical generation第一次與pending replay的完整prompt bytes、prompt SHA、
   operation/request identity完全相同。
3. replay不得重複enqueue、建立第二plan operation、前進generation或更新root
   candidate/review/state。
4. 不改Outbox identity算法；在prompt authority source修正root cause。

RED→GREEN：

- 先重跑targeted probe
  `test_later_generation_plan_pending_replay_keeps_prompt_identity`確認RED。
- 將同一observable behavior加入direct test；最小修復後兩者GREEN。

Blocking edge：此slice GREEN前不得做SL-02以外的任何scope。

### R2-SL-02 — Per-field native authority gate

`traces_to: P0C-REREV-002`

Confirmed failure：

- ko plan的intent／queries／angle／coverage notes為韓文，但所有H2為英文時，
  aggregate Hangul ratio仍通過。
- article phase被迫逐字使用錯語言H2。

Required behavior：

1. 分別驗證critical scalar/list groups；至少：
   - `native_search_intent`
   - 每一個native query phrase
   - `article_angle`
   - 每一個`ordered_h2_outline` item
   - 每一個`coverage_note`
2. 任何整個critical item為明顯錯語言時fail closed；其他欄位不得替它墊分。
3. locale正向契約：
   - en：英文為主，拒絕CJK主導item。
   - ja：允許日文漢字與kana的自然混合；不得要求每個短heading都一定含kana，
     但全英文／繁中主導item不得通過。
   - ko：Hangul為主；全英文／繁中主導item不得通過。
4. 局部proper noun、ASCII acronym、產品名與number可存在；但不能讓整個query／
   H2只剩英文一般句子。
5. `source_structure_not_copied`只作blacklist，不進母語判定。
6. 不新增外部語言套件、不呼叫provider。

RED→GREEN：

- 先重跑targeted probe
  `test_locale_gate_rejects_wrong_language_outline_when_other_fields_are_native`
  確認RED。
- direct tests至少覆蓋en／ja／ko：
  - 每個critical group的錯語言negative；
  - 合法native positive；
  - proper noun／acronym／number positive；
  - 其他母語欄位不能掩護錯語言H2/query。

## Checkpoint

SL-01與SL-02各自GREEN後，先跑direct multilingual tests與兩組Review probes。
只有全部GREEN才跑required suite。

## Allowlist

- `scripts/agy_multilingual_pipeline.py`
- `tests/test_agy_multilingual_pipeline.py`
- 本Repair-2專屬evidence／handoff

除非新的RED證據明確顯示Outbox實作有錯，否則不得修改Outbox production code或
tests。

## Forbidden scope

- 不修改既有Implementation、Review、targeted re-review或Repair-1 evidence／probes。
- 不修改deterministic、Reviewer、SEO、canonical、安全或publication gate。
- 不修改已關閉`P0C-REV-003..006`的契約，須維持其probes GREEN。
- 不手改production candidate、review、queue、approval、apply、publish或ledger。
- 不修改frontend、registry、sitemap、feed、redirect。
- 不呼叫provider、不讀寫production `.work`、不push、不deploy、不publish。
- 不建立Review、replacement或其他task；不使用hidden sub-agent。

## Verification

至少fresh執行：

```text
<existing-venv-python> -m pytest \
  tests/test_agy_multilingual_pipeline.py -q

<existing-venv-python> -m pytest \
  artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-REVIEW-20260730/adversarial_review_tests.py \
  artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-NATIVE-OUTLINE-CONTINUATION-REVIEW-20260730/targeted_re_review_probes.py -q

<existing-venv-python> -m pytest \
  tests/test_agy_multilingual_pipeline.py \
  tests/test_agy_gemini_outbox.py \
  tests/test_agy_seo_copy_pipeline.py \
  tests/test_agy_content_publisher.py \
  tests/test_agy_gemini_coordinator.py \
  tests/test_agy_gemini_v4_broker.py \
  tests/test_agy_gemini_reviewer_cutover.py -q

git diff --check
```

另執行`rg '\\[DBG-'`確認沒有debug instrumentation殘留。

## Delivery

- 狀態只能是`DELIVERED_REPAIR_2_CANDIDATE`
- candidate SHA與direct parent
- R2-SL-01／02 RED→GREEN證據
- P0C-REREV-001／002 disposition
- 已關閉P0C-REV-003..006 regression結果
- changed files與allowlist
- direct、Review probes、required suite、`git diff --check`
- residual risks與未執行production actions

完成後停止，回主線；不得自行修復Review結果或進入production。
