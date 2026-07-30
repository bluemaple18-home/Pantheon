---
card_id: CARD-PANTHEON-I18N-REWRITE-4OF4-RUNTIME-TRANSPORT-REPAIR-1-20260730
chain_id: pantheon-i18n-rewrite-4of4-runtime-stability-p0-20260730
parent_card_id: CARD-PANTHEON-I18N-REWRITE-4OF4-RUNTIME-TRANSPORT-REVIEW-20260730
role: repair
cycle: 1
repair_generation: 1
status: REPAIR_READY
thickness: strict
risk: high
model: gpt-5.4
reasoning: medium
model_reason: Review 已把問題收斂成單一 deterministic retry allowlist與測試修正；不需重新做架構判斷，使用 bounded repair 跑道，仍保留 strict re-review。
project_id: local-0020d4379451d545eb08362962f1def0
repo_identity: github.com/bluemaple18-home/Pantheon
required_source_kind: commit
required_source_sha: b7f4b0f1bf1c40f3c62e1d65038a0b9011c4c4ad
required_direct_parent: 7c0ce9f637ade2684751c6c1938999f20476d1fa
review_thread_id: 019fb18e-f645-7b80-b9e6-476d6fe58650
review_evidence_commit: 31156da5a2a7af11f1c39df53d2ffc24129ad2e7
blocking_findings:
  - RT-TR-REV-001
regression_ids:
  - RT-TR-REG-001
  - RT-TR-REG-002
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-RUNTIME-TRANSPORT-REPAIR-1-20260730/
created_at: 2026-07-30 Asia/Taipei
---

# Pantheon Runtime／Transport Repair-1

## Root question

如何修正 `RT-TR-REV-001`，讓需要設定或外部狀態改變的永久 provider failure
立即 terminal，不建立額外 queue attempt／provider call，同時保留真正 transient
transport／payload failure的 bounded retry與既有 logical request identity？

## Source and finding authority

- Source candidate：
  `b7f4b0f1bf1c40f3c62e1d65038a0b9011c4c4ad`
- Review evidence：
  `31156da5a2a7af11f1c39df53d2ffc24129ad2e7`
- 唯一 blocking finding：`RT-TR-REV-001`
- Finding authority：
  - `AUTH`、`QUOTA`、`MODEL_UNAVAILABLE` 不得 retry。
  - 使用 explicit retry allowlist，不得再以全部 closed categories減去少數項目推導。
  - terminal cases必須證明不建立 transport attempt 1、額外 outbox job或第二次
    provider call。
  - 若保留 rate-limit retry，必須先拆 hard quota／rate limit並加入 backoff；
    本 Repair 不做此擴張，因此 `QUOTA` 全部 terminal。

## Allowlist

- `scripts/agy_gemini_outbox.py`
- `tests/test_agy_gemini_outbox.py`
- 本 Repair 專屬 evidence／handoff

## Forbidden scope

- 不修改 runtime manifest、Publisher、LaunchAgent、runner、SEO或 multilingual
  implementation。
- 不改 failure taxonomy名稱或 receipt schema；只修 retry policy。
- 不擴張 retry attempt上限、不新增 backoff／scheduler、不建立新 provider流程。
- 不修改 production queue、candidate、review、approval、apply、publish或ledger。
- 不呼叫 provider、不 push、不 deploy、不 publish。
- 不建立 Review、Repair-2、replacement或其他 task；完成後回主線送原 Reviewer
  targeted re-review。
- 不使用 hidden sub-agent。

## Required tests

### RT-TR-REG-001 — Permanent failures are terminal

將原本把所有分類視為 retryable的 parametrized test拆成 retryable與terminal兩組。
至少覆蓋：

- `AUTH`
- `QUOTA`
- `MODEL_UNAVAILABLE`
- `CLI_UNAVAILABLE`

每個 terminal case驗證：

- 原 failure原樣拋回。
- 沒有 transport attempt `1` request。
- outbox job數量不增加。
- 沒有第二次 provider-side operation evidence。

### RT-TR-REG-002 — Transient bounded retry remains intact

保留並驗證 explicit retry allowlist中的 transient categories，至少包含：

- `NETWORK`
- `MALFORMED_PAYLOAD`
- `SCHEMA_INVALID_PAYLOAD`
- `CLI_NONZERO`
- `PROVIDER_UNAVAILABLE`

驗證 attempt最多三次、logical `request_sha256`不變、job ID可依 attempt區分，
且 semantic repair budget不前進。

## Required workflow

1. 驗證 exact source candidate、direct parent、clean worktree與無 `index.lock`。
2. 先把 terminal category行為改成 RED-capable tests，再做最小 allowlist修復。
3. 跑：

```text
.venv/bin/python -m pytest \
  tests/test_agy_gemini_outbox.py \
  tests/test_agy_seo_copy_pipeline.py \
  tests/test_agy_multilingual_pipeline.py \
  tests/test_agy_gemini_coordinator.py \
  tests/test_agy_gemini_v4_broker.py \
  tests/test_agy_gemini_reviewer_cutover.py -q
git diff --check
```

4. changed files必須精確落在 allowlist。
5. 交付單一 Repair candidate commit與 evidence；不得宣稱 REVIEW_GO、
   ACCEPTED、INTEGRATED或CLOSED。

## Delivery format

- Repair candidate commit SHA與direct parent
- `RT-TR-REV-001`修正摘要
- `RT-TR-REG-001`／`RT-TR-REG-002` RED→GREEN證據
- Fresh suite與 `git diff --check`結果
- Remaining risks與未執行的 production actions
