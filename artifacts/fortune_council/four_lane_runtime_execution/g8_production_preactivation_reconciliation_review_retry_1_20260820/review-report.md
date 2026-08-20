# G8 preactivation reconciliation review retry 1

## Re-review Verdict

`GO`

唯一一次 re-review 只重看前次 P1：`--evidence-path` 在 reconcile/snapshot/write 前 canonicalize，且不得指向 protected roots 或其 symlink/realpath alias。Repair candidate `9d7fb950fd84dac3572871ff706e745599be837b` 已由主線整合為 `7a4cd321921f4f56c74d1961de197cdff041d810`。

未發現前次 P1 仍可重現。

### Re-review Evidence

- Source review: `scripts/pantheon_g8_production_preactivation.py:61` 到 `scripts/pantheon_g8_production_preactivation.py:146` 先把 protected args 與 `evidence_path` canonicalize；`scripts/pantheon_g8_production_preactivation.py:493` 到 `scripts/pantheon_g8_production_preactivation.py:506` 在任何 reconcile/snapshot/write 前 fail closed，stdout 輸出 `BLOCKED` 並 return `1`。
- Tests added for the P1: `tests/test_pantheon_g8_production_preactivation.py:428` 到 `tests/test_pantheon_g8_production_preactivation.py:491` 覆蓋 protected path reject、symlink alias reject、合法外部 evidence path write。
- Manual boundary harness covered `queue_root`、`state_root`、`transaction_root`、`live_root`、`staged_root`、`git_common_dir`、manifest exact、publisher lock exact、symlink alias、realpath alias。每個 protected case 都是 exit `1`、stdout `BLOCKED`、未建立 parent、未寫目標檔、protected snapshot unchanged；合法外部 evidence path 是 exit `0`、`READY_FOR_PRODUCTION_AUTHORIZATION`、可寫 receipt、protected snapshot unchanged。

### Re-review Verification

- PASS: CodeGraph task-semantic query found the repaired preactivation surface and mutation tripwire tests.
- PASS: `/Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest -q tests/test_pantheon_g8_production_preactivation.py`
  - Result: `21 passed`
- PASS: `/Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest -q tests/test_agy_content_publisher.py::test_collect_ready_runs_skips_reviewer_reject tests/test_agy_content_publisher.py::test_collect_ready_runs_exact_selector_excludes_unlisted_ready_run tests/test_agy_content_publisher.py::test_collect_ready_runs_without_exact_selector_keeps_existing_selection tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_stages_during_manifest_bound_preactivation_transition tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_rejects_unsafe_preactivation_transition_cases`
  - Result: `10 passed`
- PASS: `git diff --check 9d7fb950fd^..9d7fb950fd`

### Re-review Scope

只更新本 reviewer evidence file。未改 source/tests、未動 production、remote、git refs、queue/state/transaction、LaunchAgent，未另開 task。

## Initial Verdict

`NO-GO`

Candidate: `0894ace3b82f13eade9bb209e85caed5386c8080`

Reviewed from formal thread: `01a01e71-0934-7f42-8c7b-7b714671b412`

## CodeGraph

Task-semantic CodeGraph query succeeded and located the relevant review surface:

- `scripts/pantheon_g8_production_preactivation.py`
- `scripts/agy_content_publisher.py::collect_ready_runs`
- `scripts/pantheon_content_capacity_guard.py::validate_preactivation_transition`

## Findings

- [P1] Receipt write can mutate a protected production root after the mutation tripwire has already passed - `scripts/pantheon_g8_production_preactivation.py:417`
  - Trigger: caller passes `--evidence-path` inside one of the protected roots, for example inside `--state-root`.
  - Risk: `reconcile()` snapshots before and after authority/runtime/selector evaluation at lines 340-382, but `main()` writes the receipt only after that at lines 417-421. A misrouted or hostile evidence path can therefore create or overwrite a file in production `queue_root`, `state_root`, `transaction_root`, `live_root`, `staged_root`, or beside the manifest while the emitted receipt still says `status=READY_FOR_PRODUCTION_AUTHORIZATION`, `production_mutation=false`, and `mutation_tripwire.status=PASS`. This violates the card requirement that protected roots remain unchanged and that any protected mutation fail closed.
  - Reproduction: on a detached candidate copy, I reused the candidate test fixture and set `evidence_path = fixture["state"] / "receipt-inside-state.json"`. The CLI returned exit code `0`; the receipt reported `READY_FOR_PRODUCTION_AUTHORIZATION` and `mutation_tripwire.changed=[]`; a post-call snapshot showed `actual_changed_after_cli=["state_root"]` and the evidence file existed inside the protected state root.
  - Suggested fix: validate `--evidence-path` before reconciliation and fail closed if it resolves inside or aliases any protected input root, git metadata root, live/staged roots, or manifest path. Keep the receipt write outside production roots, or include the receipt write in the before/after protected snapshot so any overlap returns `BLOCKED / MUTATION_DETECTED`.

## Verification

- PASS: `git diff --check 0894ace3b82f13eade9bb209e85caed5386c8080^..0894ace3b82f13eade9bb209e85caed5386c8080`
- PASS: `/Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest -q tests/test_pantheon_g8_production_preactivation.py`
  - Result: `16 passed`
- PASS after rerun in a detached Git-backed candidate copy: `/Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest -q tests/test_agy_content_publisher.py::test_collect_ready_runs_skips_reviewer_reject tests/test_agy_content_publisher.py::test_collect_ready_runs_exact_selector_excludes_unlisted_ready_run tests/test_agy_content_publisher.py::test_collect_ready_runs_without_exact_selector_keeps_existing_selection tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_stages_during_manifest_bound_preactivation_transition tests/test_pantheon_content_capacity_guard.py::test_capacity_installer_rejects_unsafe_preactivation_transition_cases`
  - Result: `10 passed`
- Note: the first affected-suite run against a plain `git archive` candidate copy failed because the capacity tests require Git metadata. I reran the same tests in `/tmp/pantheon-g8-review-0894ace3-git`, a local detached shared clone at `0894ace3b82f13eade9bb209e85caed5386c8080`, and they passed.

## Scope

No source or test files were modified. No production activation, remote mutation, git ref mutation, queue/state/transaction mutation, LaunchAgent mutation, push, tag, archive, or replacement task was performed.
