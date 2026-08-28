---
schema_version: 1
title: Pantheon Acceptance B gen06 terminal reject next-generation seam repair result
date: 2026-08-28
status: RE_REVIEW_REQUESTED
mode: REPAIR_ONLY
source_commit: 99507c67e27d9e6f3af4e33c3ab0727682ed82bd
target_run: auto-i18n-ja-1414b75a404721e95e74
target_generation: 6
production_mutation: false
provider_called: false
push: false
publish: false
commit: false
---

# 結論

本次 bounded Repair 已完成 Reviewer NO-GO 後的 P1 修正，狀態為
`RE_REVIEW_REQUESTED`。未做 production mutation、provider call、live gen06、
push、deploy、publish 或 commit。

修復仍維持同一 seam：

- function：`authorize_next_generation_after_reviewer_reject(...)`
- CLI：`authorize-next-generation-after-reviewer-reject`
- 預設 plan-only；只有 explicit `--execute` 才寫入 transition/state。

# Minimization pass

Owner anti-bloat 要求後已做第二輪縮 scope：不再支援 progressed-state
`ALREADY_AUTHORIZED` 泛化。Idempotency 只保留 transition crash window：
state hash 等於 `state_before_sha256` 時 execute 可補 `state_after`；state hash
等於 `state_after_sha256` 時回 `ALREADY_AUTHORIZED`。target generation dir 已存在、
state 已往前或任何其他 state hash，一律 fail-closed：
`authorization already consumed/state progressed`。

## LOC before / after

原 P1 修正後 diff：

```text
486 -4 scripts/agy_multilingual_pipeline.py
713 -0 tests/test_agy_multilingual_pipeline.py
```

縮碼後 diff：

```text
273 -4 scripts/agy_multilingual_pipeline.py
394 -0 tests/test_agy_multilingual_pipeline.py
```

縮碼內容：

- source：刪除 `_validate_progressed_target_generation_authority` 與 progressed
  replay 分支；共用 terminal generation artifact loader、transition receipt subset
  validator，並壓縮 wrapper / CLI 重複參數。
- tests：刪除 progressed drift 泛化 matrix；保留最小 replay-after-gen06
  consumed regression，證明不回 `ALREADY_AUTHORIZED`、不建 gen07。

已達 Owner 第二輪目標：

- source `+273/-4`，<= `+280`
- tests `+394/-0`，<= `+400`

保留 probe：plan zero-write、complete hard REJECT only、canonical hashes、
receipt-first/state-second crash recovery、shared lock concurrency、CLI plan-only、
replay after gen06 consumed fail-closed / no gen07。

# Reviewer NO-GO response

Review artifact：

- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_terminal_reject_next_generation_seam_repair_20260828/REVIEW-PANTHEON-ACCEPTANCE-B-GEN06-TERMINAL-REJECT-NEXT-GENERATION-SEAM-REPAIR-20260828.md`

## P1-1：progressed-state `ALREADY_AUTHORIZED` 過寬

第二輪縮 scope 後不再支援 progressed-state `ALREADY_AUTHORIZED`。只有 transition
crash window 可 replay：

- state hash == `state_before_sha256` 且 execute：補寫 `state_after`
- state hash == `state_after_sha256`：回 `ALREADY_AUTHORIZED`
- target gen dir 已存在、state 已往前或其他 hash：fail-closed
  `authorization already consumed/state progressed`

保留 regression：gen06 已跑完後 replay 會 reject，且不建 gen07。

## P1-2：execute transition 缺 shared lock

已補薄 per-run lock：

- lock file：`continuation/continuation.lock`
- lock primitive：`fcntl.flock(..., LOCK_EX)`
- `authorize_next_generation_after_reviewer_reject(..., execute=True)` 與
  `continue_writer_reviewer(...)` 共用同一把 lock。
- execute lock scope 覆蓋 re-read、validate、next-dir absence check、
  transition receipt-first write、state write。
- continuation lock scope 覆蓋 root recovery、state load/validate、partial
  transition、generation mutation 與 root/state update。
- plan-only 不開 lock、不寫 lock file，tree bytes 保持不變。

新增 concurrency regression：authorize 在 transition-first/state-second 中間暫停時，
continuation 不得完成；release 後 continuation 建立 gen06 一次且不建立 gen07。

# Changed files

- `scripts/agy_multilingual_pipeline.py`
- `tests/test_agy_multilingual_pipeline.py`
- `artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-ACCEPTANCE-B-GEN06-TERMINAL-REJECT-NEXT-GENERATION-SEAM-REPAIR-20260828.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_terminal_reject_next_generation_seam_repair_20260828/RESULT-PANTHEON-ACCEPTANCE-B-GEN06-TERMINAL-REJECT-NEXT-GENERATION-SEAM-REPAIR-20260828.md`
- `artifacts/fortune_council/four_lane_runtime_execution/pantheon_acceptance_b_gen06_terminal_reject_next_generation_seam_repair_20260828/RESPONSE-PANTHEON-ACCEPTANCE-B-GEN06-TERMINAL-REJECT-NEXT-GENERATION-SEAM-REPAIR-20260828.md`

# RED → GREEN

原 Reviewer P1 RED capability 保留，但第二輪縮 scope 後刪除 progressed 泛化
probe，改為 consumed replay fail-closed / no gen07 probe。

```text
.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py -q -k terminal_reviewer_reject_authority
```

RED-capable coverage：

```text
- removing shared lock makes concurrency probe fail
- accepting non-hard / approved terminal review makes fail-closed matrix fail
- allowing replay after gen06 completion would fail consumed replay / no gen07 assertion
- using file-byte hash instead of _json_sha256 canonical hash fails matrix
```

GREEN targeted command：

```text
.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py -q -k terminal_reviewer_reject_authority
```

GREEN targeted result：

```text
14 passed, 228 deselected in 0.35s
```

Affected suite：

```text
.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py -q
```

Result：

```text
242 passed in 0.55s
```

Compile / diff：

```text
.venv/bin/python -m py_compile scripts/agy_multilingual_pipeline.py tests/test_agy_multilingual_pipeline.py
git diff --check
```

Result：PASS，no output。

# Capacity boundary

本 Repair 未修改 Rule24 capacity policy/source。Production retry 仍必須使用正式
host telemetry；若 swap telemetry unavailable，仍依 Rule24 fail-closed。

# Risks

- 這是 lifecycle seam repair，不保證下一次 provider Writer/Reviewer 內容必定
  ACCEPT。
- Production 仍需重新跑 Rule24/Rule25、promotion status 與 exact operator flow。
- CLI 呼叫者必須提供 `_json_sha256` canonical hash；file-byte hash 會被拒絕。

# Suggested commit message

```text
fix: authorize terminal rejected continuation retry
```
