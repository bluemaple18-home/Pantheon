# Command Receipt

執行時間範圍：`2026-08-22T14:31:00Z` 至 `2026-08-22T14:36:25Z`。

- Authority：`git rev-parse`、`git merge-base --is-ancestor`、`git cat-file`、`git status`、`git worktree list`；全為唯讀。
- CodeGraph：`worktree_capability_preflight.sh --check --root <repo-root>`；未執行 prepare，未建立 index。
- Production snapshot：`<evidence-root>/collect_protected_snapshot.sh before|after <evidence-root>`；只執行 digest、Git read、plist read與 `launchctl print`。
- Observation：`python3 <evidence-root>/collect_release_observation.py <evidence-root>/release-observation.json <evidence-root>/normalized-live-receipts`。
- Formal reconciler：執行一次 `scripts/pantheon_g8_production_preactivation.py`，未傳 `--allow-source-drift`；result=`BLOCKED / ALLOWLIST_REQUIRED`。
- Synthetic readiness：執行一次 `scripts/pantheon_content_capability_receipt.py apf-004-readiness --output-root <evidence-root>/synthetic-readiness --ai-core-root <ai-core-root>`；result=`READY`，只寫本卡 evidence。
- Mutation compare：`python3 <evidence-root>/compare_protected_snapshots.py <evidence-root>`；result=`PASS`。

Mutation invocation accounting：promotion/reset/Capacity install/activation/restage/canary/Publisher child/deploy/tag/push/schedule/launchctl mutation/git refs mutation 全為 `0`。
