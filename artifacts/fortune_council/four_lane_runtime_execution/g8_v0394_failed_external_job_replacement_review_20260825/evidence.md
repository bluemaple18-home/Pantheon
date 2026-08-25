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

---

# Follow-up re-review amended candidate b64582e7

## Scope

- Re-review 前 review receipt commit：`dd1f5f3c1cdc64602d901c273918824385fb7ed2`。
- Base / parent：`998a797f3618a47a3d0493503e937a06b84e3da3`。
- Follow-up amended candidate：`b64582e7f213948acc36e19c19c620fe5f6ba669`。
- Lineage：candidate parent 仍為 V0393 base `998a797f3618a47a3d0493503e937a06b84e3da3`；相對前一版 candidate `f4c7ddd1c1cafd2f5520fd4b49bc21d048a7717d` 只改 V0393 Repair card/evidence、`scripts/agy_gemini_coordinator.py` 與 `tests/test_agy_gemini_coordinator.py`。
- Follow-up re-review 前 worktree status：clean。
- 已先嘗試 CodeGraph；此 worktree 未初始化：`CodeGraph not initialized`。
- Candidate-only Repair evidence was read with `git show b64582e7f213948acc36e19c19c620fe5f6ba669:<repo-relative-path>`。
- 未切換 checkout，未修改 source/test/runtime，未執行 production、push、promotion、deploy、launchctl 或 archive action。

## Commands

- `git rev-parse b64582e7f213948acc36e19c19c620fe5f6ba669^` -> `998a797f3618a47a3d0493503e937a06b84e3da3`。
- `git diff --name-status f4c7ddd1c1cafd2f5520fd4b49bc21d048a7717d..b64582e7f213948acc36e19c19c620fe5f6ba669` -> V0393 card/evidence、coordinator、coordinator tests。
- `git diff --check f4c7ddd1c1cafd2f5520fd4b49bc21d048a7717d..b64582e7f213948acc36e19c19c620fe5f6ba669` -> passed with no output。
- Candidate Repair evidence reports targeted coordinator `19 passed`、targeted outbox `7 passed`、完整受影響兩檔 `459 passed in 444.22s (0:07:24)`，以及 `git diff --check` passed。

## Follow-up Checks

- Missing actor-local `brief.json`：resolved。`replace_failed_external_job` 現在使用 `run_dir.resolve(strict=False)`，只在 local `brief.json` 存在時驗證它；並透過 `_read_run_state_by_id(expected_run_id, state_root)` 讀 durable state，仍要求 `state.run_id`、`state.run_dir`、`state.correlation_id` 與 explicit CLI identity 相符。
- No identity relaxation：run id format、run_dir string、correlation id、namespace、source job id、request hash、failure category/error code、authority digest、active status、last-job identity、source archive 與 failed receipt checks 都保留在 replacement path。
- Durable recovery tick gating：`_advance` 只在 local brief 缺失且 `state.failed_external_job_replacement` 是 dict 時略過 local `brief.json`。`_recover_failed_external_job_replacement_result` 接著要求 formal receipt key set，並在 consume result 前驗證 source archive identity、state last replacement job 與 correlation。沒有 formal replacement receipt 的一般 run 仍走 normal `tick` path，local brief 缺失時 fail closed。
- Replacement result consumption：recovery 會載入 archived source request，再呼叫 `consume_external_response(job_queue_root, source_request)`；該路徑要求 source job 的 formal replacement decision 與 exact replacement request/inbox identity 後才回傳 replacement result。
- Exactly-once / crash replay：follow-up 未改前輪已審的 staging -> decision -> state -> publish sequence。Same-authority replay、different authority fail-closed 與 no executable orphan property 仍由 candidate evidence 覆蓋。
- TOCTOU hardening：source archive 與 failed receipt descriptor-bound reads 相對 prior GO candidate 未回退。
- `CLI_NONZERO`：仍不在 `RETRYABLE_EXTERNAL_FAILURE_CATEGORIES`；retry 仍限於 quota/rate-limit 與 bounded retryable categories。
- Source evidence immutability：follow-up 只新增 durable-state recovery 與 result continuation；source archive request 與 failed receipt 仍只讀，不 rewrite、不 delete。

## Follow-up Verdict

`GO`

Findings:

- 未發現 P0/P1/P2。
- 未發現 production safety blocker。

Residual risk:

- Recovery helper 將 durable state receipt 視為內部可信 state，並依賴 `consume_external_response` 驗證 formal on-disk decision 與 replacement result；我未發現這放寬已審過的 external identity boundary。

Validation gaps:

- 我未本機重跑 459-test suite；測試執行採 candidate evidence，並已獨立執行 follow-up candidate `git diff --check`。

---

# Same-job replacement resume re-review candidate a6e2554840

## Scope

- Re-review 前 review receipt commit：`471e3853ae4f3960c1ce652deddd1ff2156dbf59`。
- Base / parent：`b64582e7f213948acc36e19c19c620fe5f6ba669`。
- Candidate：`a6e255484006aca9662cef4c96c4f828d59bff36`。
- Candidate parent 已核對為 `b64582e7f213948acc36e19c19c620fe5f6ba669`，同一 V0393 candidate lineage。
- Diff scope：V0393 Repair card/evidence、`scripts/agy_gemini_coordinator.py`、`tests/test_agy_gemini_coordinator.py`。
- 已先嘗試 CodeGraph；此 worktree 未初始化：`CodeGraph not initialized`。
- Repair evidence 以 `git show a6e255484006aca9662cef4c96c4f828d59bff36:<repo-relative-path>` 讀取。
- 未修改 source/test/runtime，未執行 production、push、promotion、deploy、launchctl 或 archive action。

## Commands

- `git rev-parse a6e2554840` -> `a6e255484006aca9662cef4c96c4f828d59bff36`。
- `git rev-parse a6e2554840^` -> `b64582e7f213948acc36e19c19c620fe5f6ba669`。
- `git diff --name-status b64582e7f213948acc36e19c19c620fe5f6ba669..a6e255484006aca9662cef4c96c4f828d59bff36` -> V0393 card/evidence、coordinator、coordinator tests。
- `git diff --stat b64582e7f213948acc36e19c19c620fe5f6ba669..a6e255484006aca9662cef4c96c4f828d59bff36` -> `4 files changed, 344 insertions(+), 2 deletions(-)`。
- `git diff --check b64582e7f213948acc36e19c19c620fe5f6ba669..a6e255484006aca9662cef4c96c4f828d59bff36` -> passed with no output。
- Targeted rerun in existing candidate worktree：`env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_agy_gemini_coordinator.py -k failed_external_job_replacement_resume` -> `5 passed, 285 deselected in 0.09s`。
- Candidate Repair evidence reports targeted coordinator `5 passed` for resume tests and full affected `464 passed in 448.40s (0:07:28)`。

## Re-review Checks

- Default replacement behavior：`replace_failed_external_job` only enters resume when `resume_replacement=True` and `local_preflight_reason` is supplied; the normal default remains non-resume and still requires active source state.
- Closed local reason：accepted resume reason is limited to `NO_ANTIGRAVITY_LOW_MODEL_LABEL`; helper rejects wrong reason and rejects models already present in `pipeline.ANTIGRAVITY_MODEL_LABELS`。
- Existing decision/state/identity gate：resume branch is only reachable after the formal decision already exists, stable decision identity matches, state `last_job_id` equals replacement job id, state receipt equals decision receipt, and decision location is exactly source archive for that replacement job。
- Exact archive payload：candidate reads the archived replacement request via descriptor-bound closed JSON read and requires exact equality with the rebuilt replacement request before any mutation。
- Failure evidence：resume requires replacement failure receipt `error_type == ValueError`, classified `INVALID_RECEIPT`, matching replacement job id and request hash. On execute it preserves the failed receipt in `failed-external-job-replacements/<source>.<replacement>.failed-preserved.json` before requeueing。
- No production attempt marker：presence of `production-attempts/<replacement>.attempt` rejects resume as evidence mismatch, preserving zero mutation。
- Same-job archive to outbox：execute moves the same replacement job from archive back to outbox with the same job id and does not allocate a second replacement job. Replay after outbox publish returns `already_replaced` with unchanged file snapshot。
- Plan-only：plan-only returns resume proof fields and decision metadata without mutating archive/outbox/failed/preserved artifacts。
- Crash consistency：crash after failure preservation but before archive publish can replay using the preserved failure; crash after state activation but before publish can replay the same formal decision; crash after publish falls into existing idempotent outbox path. I found no second replacement allocation path in these windows。
- Not a generic retry：the gate requires formal replacement decision, exact replacement archive payload, invalid-receipt failure, closed Lite label proof, and absence of provider attempt marker. This does not reopen `CLI_NONZERO` or general failed jobs for retry。
- Source evidence immutability：source archive and original source failure evidence are read-only in this diff; only replacement failed evidence is moved to the dedicated preserved artifact during execute resume。
- Bloat review：source + test additions are narrowly tied to same-job invalid-receipt resume and fail-closed tests. I did not find an actionable removable generalization that would reduce risk without losing evidence coverage。

## Verdict

`GO`

Findings:

- 未發現 P0/P1/P2。
- 未發現 production safety blocker。

Residual risk:

- Full affected 464-test suite 採 candidate Repair evidence，未在本 review worktree 重跑；本輪已本機重跑 focused resume targeted tests，並獨立執行 candidate diff check。

---

# Publisher reset launchctl identity parser re-review candidate 6b93ea6484

## Scope

- Re-review 前 review receipt commit：`14f8995173bb7cf735786f8d39737dd92d5800da`。
- Candidate：`6b93ea6484d6a3b0baf13a0efbb0fced0bc81719`。
- Base / parent：`a6e255484006aca9662cef4c96c4f828d59bff36`。
- Diff scope：V0393 Repair card/evidence、`scripts/pantheon_content_capacity_guard.py`、`tests/test_pantheon_content_capacity_guard.py`。
- Product behavior review scope：`scripts/pantheon_content_capacity_guard.py::_snapshot_launchctl_identity` and the new nested state fixture. V0393 card/evidence were checked only for fidelity to source/test behavior。
- 已先嘗試 CodeGraph；此 worktree 未初始化：`CodeGraph not initialized`。
- 未修改 source/test/runtime，未執行 production、queue/state、launchctl、publish、push 或 promotion。

## Commands

- `git rev-parse HEAD` -> `14f8995173bb7cf735786f8d39737dd92d5800da`。
- `git status --short` -> clean before review。
- `git rev-parse 6b93ea6484d6a3b0baf13a0efbb0fced0bc81719^` -> `a6e255484006aca9662cef4c96c4f828d59bff36`。
- `git diff --name-status 6b93ea6484d6a3b0baf13a0efbb0fced0bc81719^..6b93ea6484d6a3b0baf13a0efbb0fced0bc81719` -> V0393 card/evidence、capacity guard source、capacity guard tests。
- `git diff --check 6b93ea6484d6a3b0baf13a0efbb0fced0bc81719^..6b93ea6484d6a3b0baf13a0efbb0fced0bc81719` -> passed with no output。
- Candidate worktree `/Users/mattkuo/.codex/worktrees/32ca/Pantheon` HEAD -> `6b93ea6484d6a3b0baf13a0efbb0fced0bc81719` and clean before targeted tests。
- Targeted rerun：`env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_pantheon_content_capacity_guard.py::test_publisher_reset_snapshot_uses_top_level_launchctl_identity` -> `1 passed in 0.02s`。
- Full affected file：`env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_pantheon_content_capacity_guard.py` -> `60 passed in 26.47s`。

## Re-review Checks

- Top-level parser reuse：`_snapshot_launchctl_identity()` now builds expected target `gui/{os.getuid()}/{expected_path.stem}` and delegates to `_launchctl_top_level_identity()`。The parser only records `state/path/last exit code` at depth 1, so nested `resource coalition.state = active` does not affect the root service identity。
- Required PASS case：candidate test covers canonical top-level path, top-level `state = not running`, and nested `state = active`; `_snapshot_launchctl_identity()` returns `states=["not running"]`, exact path, and empty exit codes。
- Global pid fail-closed：the pre-parser regex still rejects any positive `pid` line anywhere in the launchctl output before top-level parsing。
- Root identity fail-closed：existing tests still cover duplicate top-level state, top-level running, missing state, unbalanced root, wrong root, prefix/suffix spoof, leading/trailing root whitespace, other label, multiple roots, garbage prefix, and garbage suffix。
- Path/state fail-closed：`_snapshot_launchctl_identity()` still requires `paths == [str(expected_path)]` and `states` exactly `["not running"]` or `["waiting"]`; duplicate or wrong top-level path/state cannot pass。
- Expected target：target uses `gui/<uid>/<plist stem>` and then separately verifies exact top-level plist path. I found no label/path bypass introduced by deriving the label from the already expected plist path。
- Docs fidelity：V0393 card/evidence accurately describe a false negative from whole-output regex and the repair as depth-aware root service parsing. I did not use those docs as product behavior evidence。

## Verdict

`GO`

P0/P1 Findings:

- None。

Residual risk:

- None blocking in the requested scope。
