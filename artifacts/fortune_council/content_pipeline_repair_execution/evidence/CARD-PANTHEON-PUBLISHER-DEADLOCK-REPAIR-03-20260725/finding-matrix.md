# Repair-3 Finding Matrix

Card：`CARD-PANTHEON-PUBLISHER-DEADLOCK-REPAIR-03-20260725`

| Finding | Repair | Regression evidence | Status |
| --- | --- | --- | --- |
| PPD-R-001 | 正式 CLI mutation 改在從最新 `origin/main` 建立的隔離 transaction worktree 執行；正式 actor 全程唯讀，失敗 cleanup 只移除 transaction worktree。 | `test_isolated_transaction_never_mutates_actor_concurrent_bytes`、`test_main_runs_real_publish_in_isolated_worktree` | GREEN |
| PPD-R-002 | Repair-2 durable unresolved push control record 未修改。 | publisher focused suite | PRESERVED |
| PPD-R-003 | Repair-2 collector-selected retry attribution 未修改。 | publisher focused suite | PRESERVED |
| PPD-R-004 | Repair-1 pre-cleanup／step evidence 未修改。 | publisher focused suite | PRESERVED |

## Safety interpretation

`MutationJournal.capture()` 不再對正式 actor worktree 執行。transaction 期間在正式
actor 注入同路徑 concurrent bytes，CLI 結束後該 bytes 仍原樣存在；publisher
cleanup 不會對正式 actor 執行 restore、unlink 或 HEAD update。

## V4 boundary

Repair-3 未修改 `scripts/agy_gemini_runner.py` 或任何 V4 routing／launchd 設定。
`AGY_GEMINI_V4_BROKER` 仍需顯式設為 `1` 才會進入 V4 lane。
