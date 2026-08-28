---
schema_version: 1
title: Pantheon Acceptance B gen06 terminal reject next-generation seam repair review
date: 2026-08-28
reviewer: codex-independent-reviewer
status: COMPLETE
mode: REVIEW_ONLY
source_commit_reviewed: 99507c67e27d
target_run: auto-i18n-ja-1414b75a404721e95e74
target_generation: 6
production_mutation: false
provider_called: false
source_modified_by_reviewer: false
verdict_commit_push: NO-GO
verdict_production_one_gen06: NO-GO
---

# 結論

NO-GO。Repair 的正向 authority binding、plan-only read-only、receipt-first/state-second crash recovery、canonical hash guard、semantic budget arithmetic 與 operation_id transition 大致正確；targeted/full tests 也通過。

但 review 發現兩個 P1：

1. progressed-state `ALREADY_AUTHORIZED` replay 分支過寬，會在 `generations/06` 內容已 drift/corrupt 時仍回 `ALREADY_AUTHORIZED`。
2. execute transition 沒有 shared lock 或正式 services-stopped guard/evidence；在 production exact recovery 前不能排除與 coordinator/continuation 的 TOCTOU race。

因此目前不建議 commit/push，也不可做 controlled production one gen06。需先補最小 guard 與 RED-capable tests 後再 re-review。

# Findings

## P0

無。

## P1

### P1-1 `ALREADY_AUTHORIZED` progressed-state 分支會吞掉 target generation artifact drift

- Source: `scripts/agy_multilingual_pipeline.py:2959`
- Source: `scripts/agy_multilingual_pipeline.py:2963`
- Source: `scripts/agy_multilingual_pipeline.py:2965`

既有 transition receipt 存在時，程式在 state 已前進且 `generations/{to_next_generation}` 目錄存在時，呼叫 `_load_or_create_continuation_state(...)` 後直接回 `ALREADY_AUTHORIZED`。這能防止 replay 建 gen07，但沒有直接驗證 `generations/06/candidate.json`、`review.json`、`locale-plan.json`、`source-ref-map.json` 是否仍與 root/state/receipt 的 canonical hash 一致。

我用唯讀臨時 probe 重現：

```text
execute → continue_writer_reviewer 建立 gen06 → 人為改壞 copy 內 generations/06/candidate.json → replay authorize
```

結果：

```json
{"status":"ACCEPTED","replay_status":"ALREADY_AUTHORIZED","generated":[6],"gen06_candidate":{"drifted":true}}
```

這違反本卡要求的 drift/corrupt fail-closed 精神，尤其會讓 exact recovery 在 target generation artifact 已漂移時看起來像安全重播成功。

最小修復建議：

- 在 progressed-state `ALREADY_AUTHORIZED` 分支中，對 `to_next_generation` 的 generation dir 做完整 artifact validation。
- 至少要求：
  - `candidate.json` 與 root `candidate.json` canonical hash 一致，且等於 complete state 的 `terminal_candidate_sha256`。
  - `review.json` 與 root `review.json` canonical hash 一致，且等於 complete state 的 `terminal_review_sha256`。
  - `locale-plan.json` / `source-ref-map.json` 仍通過 schema validation；若 receipt 只綁 terminal gen05 plan/map，則不要把 gen06 plan/map 當成已授權，只做存在與 schema/identity validation。
  - 若 state 仍 active 或 target generation partial，必須明確 fail closed，不要用「目錄存在」判定 already authorized。
- 補 RED test：成功 gen06 後修改 `generations/06/candidate.json` 或 `review.json`，replay `authorize_next_generation_after_reviewer_reject(..., execute=True)` 必須 raise。

### P1-2 execute transition 缺 shared lock / formal stopped-services guard

- Source: `scripts/agy_multilingual_pipeline.py:2775`
- Source: `scripts/agy_multilingual_pipeline.py:3031`
- Source: `scripts/agy_multilingual_pipeline.py:3032`

Repair 的 execute path 在 `_load_rejected_terminal_authority(...)` 先確認 next dir 不存在，之後才寫 `authority-transition-05.json` 與 `continuation/state.json`。這段沒有 shared lock；repo 內也沒有看到此 seam 與 coordinator/continuation 共用的 lock、pid guard、launchd/services-stopped guard 或對應 evidence。

風險是：若 coordinator 或另一個 continuation/exact recovery 同時操作同一 run，`next_dir.exists()` 到 state write 之間可能發生 TOCTOU race，導致 transition/state 覆寫或與新 generation dir 不一致。RCA 文字提過 services stayed stopped，但本 Repair result/evidence 沒有可驗證的正式 guard 或 receipt；對 production exact recovery 邊界不足。

最小修復建議：

- 首選：讓 `authorize_next_generation_after_reviewer_reject(..., execute=True)` 與 coordinator/continuation 使用同一個 per-run exclusive lock；lock scope 覆蓋 authority load、next dir absence check、transition receipt write、state write。
- 若本次 production recovery 只允許在 services stopped 狀態下執行，則需要一個正式、可重放的 stopped-services preflight receipt，並在 operator command 執行前驗證；但 code-level per-run lock 仍較穩。
- 補 RED test：模擬 next generation 在 authority load 後、state write 前被建立，execute 必須 fail closed，不得覆寫成 active state 或回 authorized。

## P2

無獨立 P2。測試缺口已併入 P1 最小修復建議。

# Positive checks

- Plan-only 預設 read-only：`authorize_next_generation_after_reviewer_reject(..., execute=False)` 沒有呼叫 `_recover_root_result`，且遇到 pending `continuation/root-update.json` 會拒絕，未做 durable mutation。
- Identity/canonical hash binding：run id、source sha256、terminal candidate/review、root candidate/review、locale plan、source-ref map 都用 canonical `_json_sha256` 驗證；file-byte hash 會被拒絕。
- Terminal rejected authority：要求 state `complete`、`next_generation == terminal_generation + 1`、last completed generation 等於 terminal generation、root/generation review 全 `REJECT` 且 `hard_failure`，並要求 deterministic findings artifact 與 review findings code 對得上。
- Receipt-first/state-second：execute 先寫 transition receipt，再寫 state；transition-only crash recovery 可補 state；corrupt receipt/state drift 會 fail closed。
- Semantic budget / operation_id：`required_budget = next_generation - started_after_generation - abandoned_count`，目標 fixture 會從 1 補到 2，讓 existing continuation 只跑 gen06；operation_id 轉為 terminal review authority。
- No provider / no production mutation：review 與 tests 使用 fake client/monkeypatch；未觸碰 live runtime。
- No new FSM/registry/db/runtime：diff 僅新增 narrow function/CLI/tests，未新增第二套 registry 或 lifecycle engine。

# Test evidence

Targeted:

```text
.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py::test_terminal_reviewer_reject_authority_plan_is_read_only tests/test_agy_multilingual_pipeline.py::test_terminal_reviewer_reject_authority_execute_creates_exactly_one_next_generation tests/test_agy_multilingual_pipeline.py::test_terminal_reviewer_reject_authority_crash_resume_from_transition_only tests/test_agy_multilingual_pipeline.py::test_terminal_reviewer_reject_authority_existing_transition_rejects_state_drift tests/test_agy_multilingual_pipeline.py::test_terminal_reviewer_reject_authority_rejects_corrupt_transition_receipt tests/test_agy_multilingual_pipeline.py::test_terminal_reviewer_reject_authority_requires_canonical_json_hashes tests/test_agy_multilingual_pipeline.py::test_terminal_reviewer_reject_authority_cli_defaults_to_plan_only tests/test_agy_multilingual_pipeline.py::test_terminal_reviewer_reject_authority_fail_closed -q
13 passed in 0.12s
```

Affected full file:

```text
.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py -q
241 passed in 0.37s
```

Compile / whitespace:

```text
.venv/bin/python -m py_compile scripts/agy_multilingual_pipeline.py tests/test_agy_multilingual_pipeline.py
git diff --check
PASS
```

Additional reviewer probe:

```text
gen06 artifact drift replay probe
Result: replay returned ALREADY_AUTHORIZED after generations/06/candidate.json drift
```

# Final gate

- Commit/push: NO-GO until P1-1 and P1-2 are closed and re-reviewed.
- Controlled production one gen06: NO-GO until P1 closure plus normal Rule24/Rule25/production operator evidence.
