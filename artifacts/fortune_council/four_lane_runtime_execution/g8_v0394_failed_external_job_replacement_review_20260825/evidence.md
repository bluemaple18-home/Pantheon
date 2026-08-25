# V0394 failed external job replacement review evidence

## Scope

- Review card commit / current HEAD: `13deef25d11630c223c3fb4a067d09be6f4b958a`.
- Base: `998a797f3618a47a3d0493503e937a06b84e3da3`.
- Candidate: `a0c3ffe33e9dbbb80524fe75d0486063e02d67d7`.
- Worktree status before review: clean.
- CodeGraph was attempted first and unavailable for this worktree: `CodeGraph not initialized`.
- Candidate-only evidence was read with `git show a0c3ffe33e9dbbb80524fe75d0486063e02d67d7:<repo-relative-path>`.
- No checkout change, source/test/runtime mutation, production runtime action, merge, push, deploy, promotion, launchctl action, or archive action was performed.

## Commands

- `pwd` -> `/Users/mattkuo/.codex/worktrees/1400/Pantheon`.
- `git rev-parse HEAD` -> `13deef25d11630c223c3fb4a067d09be6f4b958a`.
- `git status --short` -> clean.
- `git diff --name-status 998a797f3618a47a3d0493503e937a06b84e3da3..a0c3ffe33e9dbbb80524fe75d0486063e02d67d7` -> only V0393 card/evidence plus `scripts/agy_gemini_outbox.py`, `scripts/agy_gemini_coordinator.py`, `tests/test_agy_gemini_outbox.py`, `tests/test_agy_gemini_coordinator.py`.
- `git diff --check 998a797f3618a47a3d0493503e937a06b84e3da3..a0c3ffe33e9dbbb80524fe75d0486063e02d67d7` -> passed with no output.
- Candidate Repair evidence reports `450 passed in 451.32s (0:07:31)` for `tests/test_agy_gemini_outbox.py tests/test_agy_gemini_coordinator.py`.

## Finding P1

- Severity: P1.
- Category: production safety / correctness / crash consistency.
- Path: `scripts/agy_gemini_coordinator.py:1631`.
- Trigger: `replace-failed-external-job --execute` crashes or is killed after `atomic_write_json(outbox_path, replacement_request)` and before both the formal replacement decision and run-state transition are durably written; or the runner wakes in that window.
- Evidence: Candidate writes the replacement request directly to live `outbox/*.json` at line 1631, writes the decision at line 1635, and updates state at lines 1637-1645. The runner independently claims any `outbox/*.json` by globbing and `os.replace` at `scripts/agy_gemini_runner.py:524` and `scripts/agy_gemini_runner.py:551`; it does not share the coordinator flock or require the replacement decision before provider execution.
- Risk: A replacement can be processed without the formal decision that makes the original failed job route to the replacement response. That creates an orphan provider call, leaves the original failed result terminal, breaks exactly-once recovery, and violates the contract that formal decision precedes redirection and that mutation is all-or-none.
- Suggested fix: Stage the replacement request under a non-runner-visible name/directory, write and fsync the decision/state transition first or use a resumable two-phase receipt, then atomically publish the request to `outbox` only after the formal decision is durable. Also make replay repair or complete any recognized in-progress receipt instead of rejecting a half-written replacement as `request already exists without decision`.
- Validation gap: Existing tests cover happy-path execute, same-authority replay, drift rejection, and plan-only zero mutation, but no crash/partial-write or runner-race harness exercises the window between outbox publish and decision/state durability.
- Confidence: high.

## Non-Blocking Observations

- P2 / validation hardening: source archive and failed receipt validation still uses separate path checks and later path reads (`scripts/agy_gemini_coordinator.py:1514`, `scripts/agy_gemini_coordinator.py:1524`, `scripts/agy_gemini_outbox.py:474`). A concurrent local path replacement can make validation and read operate on different filesystem objects. Use `openat`/`O_NOFOLLOW` plus `fstat` and read from the same descriptor if this endpoint will operate against mutable production queues. Confidence: medium.

## Verdict

`REPAIR_REQUIRED`

Minimum repair scope:

- Keep changes limited to `scripts/agy_gemini_coordinator.py`, `scripts/agy_gemini_outbox.py` if routing validation needs a receipt-state tweak, and the two affected test files.
- Add targeted tests for crash/partial states around replacement request, decision receipt, and state transition.
- Add a runner-race or equivalent harness proving runner cannot process a replacement before the formal decision exists.
- Preserve current fail-closed identity checks and CLI receipt shape.

---

# Re-review amended candidate f4c7ddd1

## Scope

- Re-review 前 review card commit：`df84805b96c8b1ac5d21d3094da502c67d83d443`。
- Base: `998a797f3618a47a3d0493503e937a06b84e3da3`.
- Amended candidate: `f4c7ddd1c1cafd2f5520fd4b49bc21d048a7717d`.
- Re-review 前 worktree status：clean。
- 已先嘗試 CodeGraph；此 worktree 未初始化：`CodeGraph not initialized`。
- candidate-only Repair evidence 以 `git show f4c7ddd1c1cafd2f5520fd4b49bc21d048a7717d:<repo-relative-path>` 讀取。
- 未切換 checkout，未修改 source/test/runtime，未執行 production runtime action、merge、push、deploy、promotion、launchctl action 或 archive action。

## Commands

- `pwd` -> `/Users/mattkuo/.codex/worktrees/1400/Pantheon`.
- `git rev-parse HEAD` -> `df84805b96c8b1ac5d21d3094da502c67d83d443`.
- `git status --short` -> clean.
- `git diff --name-status 998a797f3618a47a3d0493503e937a06b84e3da3..f4c7ddd1c1cafd2f5520fd4b49bc21d048a7717d` -> V0393 card/evidence plus `scripts/agy_gemini_outbox.py`, `scripts/agy_gemini_coordinator.py`, `tests/test_agy_gemini_outbox.py`, `tests/test_agy_gemini_coordinator.py`.
- `git diff --check 998a797f3618a47a3d0493503e937a06b84e3da3..f4c7ddd1c1cafd2f5520fd4b49bc21d048a7717d` -> passed with no output.
- Candidate Repair evidence 記錄 targeted coordinator `17 passed`、targeted outbox `7 passed`、完整受影響兩檔 `457 passed in 432.06s (0:07:12)`，以及 `git diff --check` passed。

## Re-review Checks

- P1 live outbox premature publish / runner claim race：resolved。Amended candidate 將 replacement request stage 到 `failed-external-job-replacements/<source>.<replacement>.request-staged.json`，不在 runner `outbox/*.json` 掃描範圍內。它在 `scripts/agy_gemini_coordinator.py:1699` 寫 decision、`1708` 寫 state，之後才於 `1650` / `1709` 以 `os.replace(staging_path, outbox_path)` final-publish 到 live outbox。
- Runner scope：runner `_claim_next` 只在 `scripts/agy_gemini_runner.py:524` glob 掃描 `outbox/*.json`，並於 `551` claim 這些檔案；staging suffix/path 不可執行。
- Crash replay：same-authority replay 可處理 decision-only 與 decision+state partial，不建立第二個 replacement。decision 存在但 state 仍指 source 時會補 state 再 publish；decision+state 但無 outbox 時會 publish 同一 job 並 idempotent 回傳。
- Different authority / identity drift：existing decision stable identity 包含 `authority_digest`、source/replacement ids、request hash、namespace、role/model 與 lineage；mismatch 仍 fail-closed 且 zero mutation。
- P2 archive+failed receipt path-read TOCTOU：source archive read 現在於 coordinator 使用 descriptor-bound `read_closed_json_artifact`；failed receipt validation 也使用同一 helper。helper 會在可用時以 `O_NOFOLLOW` open，從 descriptor 讀取，檢查 regular file、size limit，並在 read 後驗證 inode/size。
- Cross-platform semantics：`getattr(os, "O_NOFOLLOW", 0)` 保留沒有該 flag 的平台相容性，同時保留 descriptor-bound `fstat` 與 size validation。對本 Python/runtime target 的剩餘風險可接受。
- `CLI_NONZERO`：仍分類為 `CLI_NONZERO`，且不在 `RETRYABLE_EXTERNAL_FAILURE_CATEGORIES`；retry path 只 retry API quota/rate-limit 或 bounded retryable category set。

## Re-review Verdict

`GO`

Findings:

- 未發現 P0/P1。
- 未發現 amended candidate 的 production safety blocker。

Residual risk:

- Decision receipt 在此 diff path 仍使用一般 `read_text`，但本輪指定 P2 範圍是 archive+failed receipt path-read TOCTOU；replacement request 與 failed receipt artifacts 已改為 descriptor-bound read。此項不阻擋 amended candidate。

Validation gaps:

- 我未本機重跑 457-test suite；測試執行採 candidate evidence，並已獨立執行 candidate `git diff --check`。
