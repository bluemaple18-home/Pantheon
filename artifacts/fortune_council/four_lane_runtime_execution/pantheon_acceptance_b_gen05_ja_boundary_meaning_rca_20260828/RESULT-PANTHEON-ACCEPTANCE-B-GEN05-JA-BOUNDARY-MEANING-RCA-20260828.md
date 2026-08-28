---
schema_version: 1
title: Pantheon Acceptance B gen05 JA boundary meaning reviewer RCA result
date: 2026-08-28
status: COMPLETE
mode: RCA_ONLY
target_run: auto-i18n-ja-1414b75a404721e95e74
target_article: V2-TAROT-DEATH-MONEY:ja
failure_code: BOUNDARY_MEANING_MISSING
missing_category: outcome_not_determined
missing_fields:
  - meta_description
  - body
source_commit: ac1faef520c9b79f9bb70265735d07a6ca826b7d
primary_verdict: CONTENT_OUTPUT_MISS_WITH_SECONDARY_REVIEWER_PATTERN_NARROWNESS
data_only: false
bounded_repair_allowed: true
---

# 結論

本 RCA 判定：`NO-GO` 不是 runtime lifecycle、promotion、replacement 或
provider transport 問題；是 gen05 candidate 在 JA protected boundary
contract 下未通過 deterministic reviewer。

Primary cause 是 content output miss：Writer 雖收到完整
`protected_constraints.required_fields` contract，但 gen05 candidate 沒把
`outcome_not_determined` 寫進 `meta_description` 的 machine-recognizable
日文。`body` 有一句語意接近「任何預測工具都無法完全確定未來的結果」的日文，
但目前 deterministic target pattern 沒認到；這是 secondary reviewer pattern
narrowness。整體 Reviewer `REJECT` 仍正確，因為 `meta_description` 確實缺
`outcome_not_determined`。

這不是 DATA_ONLY。target continuation state 已 terminal complete，
`approved_by_reviewer=0`，沒有 active continuation 可合法再 tick；若要恢復
LIVE，需要唯一 bounded Repair，不得手改 runtime state 或直接 publish。

# Evidence artifacts

- `boundary-rca-evidence.json`
- `red-capable-reproduction-receipt.json`
- `collect_boundary_evidence.py`
- `red_capable_boundary_acceptance_check.py`

# 四項證據

## 1. Last successful generation / candidate

同一 production run 沒有 approved successful candidate：

- `attempts/01`：`BOUNDARY_MEANING_MISSING`
- `attempts/02`：`BOUNDARY_BOILERPLATE_REPEATED`
- `attempts/03`：`BOUNDARY_MEANING_MISSING`
- `generations/04`：planning 階段 abandoned，沒有 committed candidate
- `generations/05`：`BOUNDARY_MEANING_MISSING`

最近可比 successful JA boundary contract 是 committed fixture：

- `tests/fixtures/agy_multilingual_pipeline/ja_boundary_contract/corrected_test_only_candidate.json`
- sha256：`667dea0e2db5da7d0ec27ce357825345d583e0ba6bade53425bf6d09f43230e8`
- deterministic `translation_findings(...) == []`
- `meta_description` 與 `body` 都同時命中：
  - `contextual_or_general_interpretation`
  - `outcome_not_determined`
  - `professional_advice_non_substitution`

## 2. First failing generation / mechanism

Boundary contract 的 first failing mechanism 在同 run 的 `attempts/01` 已出現：
candidate 全文雖有三類 boundary category，但 required fields 沒逐欄成立，
Reviewer 因 `meta_description/body` field-level coverage 不完整而拒絕。

本次 release 阻塞的精確 failure 是 `generations/05`：

- candidate sha256：
  `e8937d77fe21800d69ebacd6ed7d3fb6bbb0cb15c81ba0368fc63574900d7555`
- deterministic finding：
  `BOUNDARY_MEANING_MISSING`
- missing category：
  `outcome_not_determined`
- missing fields：
  `meta_description`, `body`
- present categories：
  `contextual_or_general_interpretation`,
  `professional_advice_non_substitution`

`generations/04` 不是本 failure 的 first failing content generation；它在
PLANNING 階段因 `source ref map missing for persisted external locale plan`
被 terminalized/abandoned，沒有進入 article/reviewer。

## 3. Durable invariant

Authoritative invariant 是：

`protected_constraints.required_fields → writer prompt/candidate → deterministic reviewer`

Live evidence：

- Protected constraint categories：
  - `contextual_or_general_interpretation`
  - `outcome_not_determined`
  - `professional_advice_non_substitution`
- Required fields：
  - `meta_description`
  - `body`
- Constraint counts：
  - contextual/general：9
  - outcome_not_determined：8
  - professional advice：3

Prompt evidence：

- gen05 plan prompt、article prompt、reviewer prompt 均含：
  - `protected_constraints`
  - `required_fields`
  - `outcome_not_determined`
- article prompt 明文要求：
  `JA protected_constraints 必須覆蓋其 required_fields`
- article prompt archived jobs：
  - source failed job `61a83c341d39c882d5eed8ea23b7f805a89085e3`
  - replacement writer job `59c0a5ec749022160627e8a1f56aa7d9c0e7afc9`

所以 `constraint normalization/dedup lost the category` 與
`writer prompt fully omitted protected contract` 均被 falsified。

## 4. RED-capable deterministic test

已建立並執行：

```text
.venv/bin/python artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen05_ja_boundary_meaning_rca_20260828/red_capable_boundary_acceptance_check.py
```

Receipt：

- `red-capable-reproduction-receipt.json`
- returncode：1
- red_capable：true
- target symptom：
  `BOUNDARY_MEANING_MISSING missing outcome_not_determined in gen05 candidate`

這條 command 使用同一 live `brief.json` 與 `generations/05/candidate.json`，
只呼叫本機 deterministic `translation_findings(...)`，不呼叫 provider。

# Gen03 / Gen04 / Gen05 comparison

## Attempts / gen03

`attempts/03`：

- description category presence：none
- body category presence：none
- visible category presence：`outcome_not_determined`
- finding：
  `BOUNDARY_MEANING_MISSING`
- missing categories：
  `contextual_or_general_interpretation`,
  `professional_advice_non_substitution`

This was not the same missing category as gen05, but it proves the same
field-level invariant: visible/global presence is insufficient when required
fields do not carry all required categories.

## Gen04

`generations/04`：

- allocated：true
- committed：false
- lifecycle_state：`abandoned`
- terminal_stage：`PLANNING`
- terminal_reason：
  `source ref map missing for persisted external locale plan`

Gen04 did not produce a committed article candidate; it is a lifecycle boundary,
not the Reviewer boundary failure.

## Gen05

`generations/05`：

- locale plan exists and planning status `PASS`
- coverage count：22
- contains `safety_boundary` field：true
- article operation success via formal outbox transport
- reviewer operation success via formal outbox transport
- deterministic reviewer rejected candidate for missing
  `outcome_not_determined` in `meta_description` and `body`

Candidate field evidence：

- `meta_description` says the article is for general understanding and does not
  make financial promises, but it does not explicitly say results/future outcomes
  are not determined.
- `body` contains a semantically close sentence:
  `どのような予測ツールも未来の結果を完全に確定することはできないため...`
- Current deterministic matcher does not count that body sentence as
  `outcome_not_determined`.

# Hypotheses

## A. Writer prompt omission

Rejected as primary cause.

The archived gen05 article prompt contains `protected_constraints`,
`required_fields`, `outcome_not_determined`, and the explicit sentence that
JA protected constraints must cover required fields. The issue is not total
contract absence.

Residual contributor: the prompt does not expose a compact field-by-field
machine-check checklist or canonical accepted Japanese phrasings, so the Writer
can produce semantically close but matcher-invisible phrasing.

## B. Constraint normalization / dedup failure

Rejected.

The boundary contract preserves all three categories. `outcome_not_determined`
has 8 constraints and required fields remain `meta_description/body`.

## C. Reviewer false positive

Partially true but not sufficient.

For `body`, the candidate contains a reasonable outcome-not-determined sentence,
but the current regex does not match it. For `meta_description`, however, the
candidate lacks a direct outcome/result-not-determined expression. Therefore the
overall `REJECT` is not a pure false positive.

## D. Content output miss

Accepted as primary cause.

Writer generated a candidate that satisfied general interpretation and
professional advice categories, but did not satisfy outcome-not-determined in
`meta_description`, and did not use a body phrasing accepted by the deterministic
contract.

# Authoritative owner

- Boundary source extraction / normalization owner：
  `scripts/agy_multilingual_pipeline.py`
- Writer prompt / candidate hydration owner：
  `scripts/agy_multilingual_pipeline.py`
- Deterministic reviewer owner：
  `scripts/agy_multilingual_pipeline.py`
- Runtime promotion / replacement owner：
  not implicated by this RCA
- Production data / registry：
  not authoritative for changing the boundary decision

# Generation lifecycle / replacement boundary

The ac1 replacement seam successfully recovered the previous
provider-attempt=0 `INVALID_RECEIPT` residue and preserved the run identity.
After recovery:

- replacement writer job processed
- reviewer job processed
- state became terminal complete
- `approved_by_reviewer=0`
- no publish URL
- no gen06

The failure crossed from runtime recovery back into the existing content
quality gate. Replacement did not alter the brief, locale plan, protected
constraints, or candidate bytes outside the formal Writer output.

# why_not_less

Less than a bounded Repair would mean either:

- publish a Reviewer-rejected candidate,
- hand-edit runtime candidate/state,
- ignore the missing `meta_description` required-field invariant, or
- rerun provider against a terminal complete state without a formal seam.

All four violate the production acceptance contract.

# why_not_more

More than a bounded Repair is unnecessary because:

- source extraction preserved `outcome_not_determined`;
- prompts carried the contract;
- deterministic reviewer correctly blocked the candidate at the public seam;
- promotion, replacement, queue identity, and provider transport all worked.

No new registry, FSM, database, promotion subsystem, or generation lifecycle
rewrite is justified.

# do_not_absorb

Do not absorb:

- a second content registry or boundary ledger;
- manual runtime state editing;
- generic prompt framework;
- broad semantic judge replacement;
- gen06 creation as a workaround;
- publication override for Reviewer `REJECT`;
- general relaxation of `BOUNDARY_MEANING_MISSING`.

# Repair frontier

`DATA_ONLY=false`。

唯一 bounded Repair frontier：

1. 在 `scripts/agy_multilingual_pipeline.py` 的 JA boundary article/reviewer
   seam 內，加入 field-by-field deterministic accepted-category checklist 或
   equivalent narrow guidance，讓 Writer 在 `meta_description` 與 `body` 各自
   產出 machine-recognizable `outcome_not_determined`。
2. 極窄補強 JA `outcome_not_determined` target pattern，接受目前 body 這類
   「未来の結果を完全に確定することはできない」語意，但不得放寬到普通
   uncertainty wording。
3. 加 RED-capable fixture：用 live-shaped gen05 candidate 證明目前會 RED；
   修後同 fixture 或最小 corrected candidate GREEN。
4. 若需恢復 live terminal rejected run，必須另有正式、bounded、
   no-manual-state-edit 的 Reviewer-rejected recovery seam；不得直接改
   continuation state。

# Final status

RCA complete。可進唯一 bounded Repair；不可直接 publish / gen06 / manual data
mutation。
