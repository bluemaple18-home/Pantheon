---
id: CARD-PANTHEON-REPLACEMENT-IDENTITY-MINIMAL-REBIND-20260830
status: reviewed_local_candidate
type: bounded_implementation_card
priority: P1_HIGH
role: implementation
authority: Owner clean replan裁決；Mainline card review批准 bounded local code repair與local test execution；independent REVIEW_GO/no P0-P2；not committed
implementation_authorized: false
execution_authorized: false
production_authorized: false
remote_authorized: false
provider_authorized: false
publish_authorized: false
promotion_authorized: false
service_authorized: false
push_authorized: false
accepted_base: origin/main@54ad8654675dbf729367a25a5093a52b379b2538
readonly_evidence_ref: forensics/e0bff38
---

# Pantheon Replacement Identity Minimal Rebind — Clean Replan

## Root question

如何在不重跑 business outcome、不改 promotion/publisher、不吃事故腳本的前提下：

1. 修正 future translation replacement producer 漏寫 canonical `identity_envelope`；
2. 對唯一 current replacement 做 receipt-first Layer-A `REBIND`；
3. 只補缺失的 `identity_envelope`，並證明既有 production-shaped result 與 run tree 完全不變？

## Owner authority

本卡只承接 Owner 新裁決。

- `forensics/e0bff38` 是唯讀證據來源。
- 禁止 merge/cherry-pick 任何事故 branch、事故 scripts 或 giant diff。
- 禁止從 `/private/tmp/pantheon-replacement-identity-envelope-54ad` 讀取、複製或移植內容。
- 禁止把本卡擴張成 full rerun、promotion repair、publisher repair、receipt lifecycle 或新 registry。
- 實作開始前，Mainline 必須先審卡；本次 clean replan 不實作。

## Accepted base

`origin/main@54ad8654675dbf729367a25a5093a52b379b2538`

## Current target

Current target 由 `forensics/e0bff38` 唯讀證據固定為：

- source run：`auto-i18n-en-aa637e1bf05d3ad21429`
- target run：`auto-i18n-en-aa637e1bf05d3ad21429-replacement-01`
- registry relative path：`queue/runs/1bf0bbc61ff8d10e808f6923.json`
- article：`ASTRO-BASE-03`
- lane：`i18n-rewrite`
- reason：`LOCALE_PLAN_VALIDATION`

`forensics/e0bff38` 只作卡片與 fixture authority。Runtime command 不得讀 forensics branch；operator identities 必須由 required args 與 current canonical roots 解析。

實作啟動條件：

- target registry keys 必須精確等於：
  - `lane`
  - `last_job_id`
  - `mode`
  - `registered_at`
  - `replacement_of`
  - `replacement_reason`
  - `result`
  - `routing_schema_version`
  - `run_dir`
  - `run_id`
  - `schema_version`
  - `status`
  - `updated_at`
- `status` 必須是 `complete`；
- `mode`、`lane`、`routing_schema_version` 必須已存在且正確；
- 唯一允許補的欄位是 `identity_envelope`。

若 exact target 不唯一或 current shape 與上述不符，狀態為 `BLOCKED_SCOPE_EXPANSION`。

## Closed production shape to model

測試 fixture 必須模擬真實 current shape，不得再用 active/pristine replacement。

Closed shape：

- registry 是 `complete/unpublished`；
- registry 含 `result`：
  - `approved_by_reviewer: 0`
  - `candidate: <tmp path>`
  - `review: <tmp path>`
  - `run_id: <target>`
  - `status: complete`
  - 不含 `target`
- registry 含正確 `last_job_id`；
- run root 含：
  - `brief.json`
  - `candidate.json`
  - `review.json`
  - `attempts/01`
  - `attempts/02`
  - `attempts/03`
  - 每層 attempts 含實際 artifact file set
  - empty `continuation/` directory
- run root 不得含：
  - `attempts/04`
  - second replacement / `replacement-02`
  - publish transaction
  - production ledger mutation

測試只保存 bytes 與 tree snapshot；不得重新驗 attempt、candidate、review 內容語義。

## Allowed paths for implementation

Code：

- `scripts/agy_multilingual_pipeline.py`
- `scripts/agy_gemini_coordinator.py`

Tests：

- `tests/test_agy_multilingual_pipeline.py`
- `tests/test_agy_gemini_coordinator.py`
- `tests/test_pantheon_content_runtime_promotion.py`

Artifacts：

- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-REPLACEMENT-IDENTITY-MINIMAL-REBIND-20260830.md`
- `artifacts/fortune_council/four_lane_runtime_execution/RESULT-PANTHEON-REPLACEMENT-IDENTITY-MINIMAL-REBIND-20260830.md`

任何其他檔案變更都必須停止回 Mainline。

## Required implementation shape

### Future producer

在共同 enqueue path 原子寫入 replacement identity：

- `routing_schema_version`
- `mode`
- `lane`
- `identity_envelope`

不得建立平行 producer 或改 publisher/promotion。

### Current replacement repair

新增語意專屬 command：

`reconcile-translation-replacement-identity`

Command requirements：

- required args 必須含 exact target/source identity 與 current canonical roots；
- 必須要求 `--publisher-state-root`，或等價 explicit canonical publisher owner；
- 必須驗證 target 無 publisher ledger 且無 unresolved publish transaction；
- receipt-first；
- plan-only deterministic；
- existing `_run_identity_lock` fcntl lock + optimistic before digest；
- atomic exact registry update；
- after digest；
- no provider / no runner / no publisher / no promotion / no service write；
- 只允許補 `identity_envelope`；
- 不得重寫已正確存在的 `routing_schema_version`、`mode` 或 `lane`。

## One-shot receipt recovery matrix

此 receipt 是一次性 recovery receipt，不是 persistent lifecycle 或 FSM。

| state | required behavior |
|---|---|
| receipt absent + before digest matches | fcntl lock, exclusive receipt claim, then atomic registry update |
| receipt present + before digest matches | complete the pending exact update |
| receipt present + after digest matches | return already reconciled |
| any third state | fail closed, mutation count 0 |

Receipt 必須包含 expected before digest 與 expected after digest。

## Positive matrix

實作後必須用 TDD 證明：

1. Future `enqueue_translation_replacement` 對新 replacement 原子寫入四個 identity fields。
2. Existing closed current target plan-only：
   - 解析 exact target；
   - 回報 `missing_fields: ["identity_envelope"]`；
   - `planned_mutation_count: 0`；
   - before snapshot 完全不變。
   - expected write set 明示 execute 可能寫入：lock coordination artifact、one-shot receipt、exact registry。
3. Execute：
   - 只新增 `identity_envelope`；
   - registry 既有 keys/values 完全不變；
   - `result` 完全不變；
   - `last_job_id` 完全不變；
   - `registered_at` / `updated_at` 完全不變；
   - attempts/candidate/review/ledger/content bytes 完全不變；
   - run tree digest 除 registry identity field 外不變；
   - 寫入後產生 after digest receipt。
4. Existing pristine active replacement with all identity fields 仍 idempotent。
5. 現有 exact replacement create path 不回歸。
6. Production-shaped promotion fixture plan passes with `preserved_run_count=137` and promotion source diff `0`；不得執行 production。

## Negative matrix

以下全部 fail closed，且 semantic mutation count 必須為 0；execute 可留下 lock coordination artifact：

- exact target 不唯一；
- target status 非 `complete`；
- target already has conflicting `identity_envelope`；
- wrong lane；
- wrong digest；
- after-state replay lacks matching PREPARED/RECONCILED receipt；
- mode/routing schema drift；
- `replacement_of` drift；
- run_dir/result/candidate/review path drift，含 queue root 外部 run tree；
- last_job drift；
- before digest drift between plan and execute；
- run tree 含 `attempts/04`；
- root candidate/review mirror drift、result extra `target`、root 多出 `review.md`；
- run tree 含 second replacement / `replacement-02`；
- run tree 含 publish transaction；
- ledger/content bytes 會被改動；
- command 無 exact target ID；
- forensics/e0bff38 證據不可解析。

失敗時不得 fallback 到 full rerun。

## Delta decision

```yaml
acceptance_mode: DELTA
disposition:
  authority_binding: REBIND
  control_plane: CARRY_FORWARD
  capability_behavior: CARRY_FORWARD
  business_outcome: CARRY_FORWARD
required_new_evidence:
  - identity_envelope present on exact current replacement
  - before_digest / after_digest receipt
  - byte-preservation proof for result, last_job, timestamps, attempts, candidate, review, ledger, content
forbidden_evidence:
  - new attempt
  - new reviewer verdict
  - new publish
  - new promotion
  - full four-lane rerun
```

## Why this size

`why_not_less`：future-only 修正不能解除 current exact replacement 缺 `identity_envelope` 的 blocker。

`why_not_more`：current issue 是 Layer-A identity binding，不是 business outcome invalidation；attempt、candidate、review、publish、promotion evidence 均不得重驗。

## Verification requirements

實作 RESULT 必須列出：

- RED：production-shaped closed fixture 在舊路徑被拒絕；
- GREEN：future producer、plan-only、execute、idempotent、negative matrix；
- changed paths；
- source/test LOC added；
- before/after digest；
- mutation count；
- `git diff --check`；
- focused pytest selectors；
- 未跑完整 suite 的風險。

## Stop conditions

立即停止：

- 需要讀或複製事故 scripts / giant diff；
- 需要 merge/cherry-pick；
- 需要修改 promotion source 或 guard；
- 需要 provider、publish、promotion、service、remote 或 push；
- 需要新 DB、registry、FSM、receipt lifecycle；
- 需要 full rerun；
- 需要重驗 attempt/candidate/review 內容語義；
- 需要修改 allowed paths 以外檔案；
- exact current target 不能由 forensics/e0bff38 唯一解析。
