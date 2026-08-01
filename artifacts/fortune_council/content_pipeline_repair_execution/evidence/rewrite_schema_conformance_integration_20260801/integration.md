---
card_id: CARD-PANTHEON-REWRITE-SCHEMA-CONFORMANCE-RECOVERY-20260801
chain_id: PANTHEON-REWRITE-SCHEMA-CONFORMANCE-RECOVERY-20260801
status: READY_TO_DEPLOY
evidence_type: integration
---

# Rewrite schema conformance integration receipt

## Lineage

- 最新整合基線：`97345bd2d9813f366080387eab0714ee918ebb32`（v0.3.234）。
- 原始 candidate：`cd3833212ad64af0a1b016c7cc7206464bb8575e`。
- 獨立 Review：`888bb4090d3f57af116853c2ae30b71afff678b6`，`REVIEW_GO`，無 P0/P1。
- 主線 candidate cherry-pick：`67c6aa00c`。
- 主線 Review cherry-pick：`c025227d7`。

## Mainline acceptance

- affected suite：`438 passed, 1 warning in 82.78s`。
- warning：既有 publisher selector fixture 的 `SyntaxWarning: invalid escape sequence '\/'`；無 test failure。
- `py_compile`：PASS。
- `git diff --check`：PASS。
- production code diff 只包含 `scripts/agy_seo_copy_pipeline.py` 的 rewrite provider schema seam。
- Review P2 `RSC-REV-001` 已補：candidate SHA、Review SHA、verdict 與 local-only path 標示已寫回 Implementation 卡／decision evidence。

## Safety boundary

- 測試與 Review 未呼叫 Gemini、未讀 raw production response／prompt／credential。
- `new`、`i18n-new`、`i18n-rewrite`、broker、runner、coordinator、publisher runtime 與 ops 無 production-code diff。
- 目前尚未 push、deploy、切 production actor 或執行 controlled canary。

## Pending acceptance

只有下列全部完成才可把狀態改為 `ACCEPTED`：

1. integration commit 推到 `origin/main`。
2. production actor 精確對齊 integration runtime SHA，六個既有 LaunchAgent 恢復。
3. 一次真實 rewrite 產出通過 provider → local gate → reviewer → publisher，形成新的 rewrite release。
4. 其他三 Lane 保持 exit 0，且沒有新容量異常。
