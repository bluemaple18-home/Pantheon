---
card_id: CARD-PANTHEON-REWRITE-SCHEMA-CONFORMANCE-RECOVERY-20260801
chain_id: PANTHEON-REWRITE-SCHEMA-CONFORMANCE-RECOVERY-20260801
status: DEPLOYMENT_NO_GO_STORAGE
evidence_type: integration
---

# Rewrite schema conformance integration receipt

## Lineage

- 最新整合基線：`7b24d76e3294cc61a8a730044c01d1fcf8b1db1f`（v0.3.246）。
- 原始 candidate：`cd3833212ad64af0a1b016c7cc7206464bb8575e`。
- 獨立 Review：`888bb4090d3f57af116853c2ae30b71afff678b6`，`REVIEW_GO`，無 P0/P1。
- 主線 candidate cherry-pick：`a54b4b7894`。
- 主線 Review cherry-pick：`d5b2185828`。
- 主線 acceptance receipt：`0e9a262194`。

## Mainline acceptance

- affected suite：`438 passed, 1 warning in 82.78s`。
- warning：既有 publisher selector fixture 的 `SyntaxWarning: invalid escape sequence '\/'`；無 test failure。
- `py_compile`：PASS。
- `git diff --check`：PASS。
- Rebase 至 v0.3.246 後 focused rewrite seam + 最新 `tests/test_web.py`：`80 passed, 2 warnings in 33.68s`。
- production code diff 只包含 `scripts/agy_seo_copy_pipeline.py` 的 rewrite provider schema seam。
- Review P2 `RSC-REV-001` 已補：candidate SHA、Review SHA、verdict 與 local-only path 標示已寫回 Implementation 卡／decision evidence。

## Safety boundary

- 測試與 Review 未呼叫 Gemini、未讀 raw production response／prompt／credential。
- `new`、`i18n-new`、`i18n-rewrite`、broker、runner、coordinator、publisher runtime 與 ops 無 production-code diff。
- 目前尚未 push、deploy、切 production actor 或執行 controlled canary。

## Storage-capacity safety gate

- 上線前基線：Data volume 228 GiB total、164 GiB used、11 GiB available、94%。
- 上線最低門檻：`max(30 GiB, 15%)` = 34.2 GiB available；實測少 23.2 GiB，`NO-GO`。
- 執行中停損門檻：`max(20 GiB, 10%)` = 22.8 GiB available；實測亦低於此值。
- Pantheon 已登記寫入面：
  - `.work/gemini-runner/**`：queue、run state、outbox/inbox、receipts、candidates，現約 570 MiB／22,721 files（此數亦包含同一 `.work` 下少量 repair state）。
  - production actor `.work/content-publisher/**`：transaction、ledger、state、receipts，現約 171 MiB／4,448 files。
  - `~/Library/Logs/Pantheon/**`：六個 LaunchAgent stdout/stderr，現約 29 MiB／16 files。
- 缺少可核准的 `max_bytes`、`max_file_count`、保留期限、輪替／清除 allowlist、兩週期 RSS/swap 增長實測與實際回收演練，因此即使釋放少量空間也不能直接重啟。
- 容量停損已實際執行：publisher、coordinator、new、rewrite、i18n-new、i18n-rewrite 六個 LaunchAgent 全數 `bootout`；`launchctl print` 六者皆回傳 113，證明未載入且不會自動重啟。
- 未切 production actor、未執行 provider canary、未刪 queue／ledger／receipt／文章或任何跨專案資料。
- 唯讀主機盤點另見：`~/.codex` 約 8.7 GiB，當中 archived sessions 約 2.6 GiB、worktrees 約 2.8 GiB、`logs_2.sqlite` 約 1.0 GiB；這些不是本卡的 Pantheon 自動清理 allowlist，未做刪除，也不能單獨補足 23.2 GiB 缺口。

## Pending acceptance

只有下列全部完成才可把狀態改為 `ACCEPTED`：

1. integration commit 推到 `origin/main`。
2. 主機可用空間回到至少 34.2 GiB。
3. 建立並驗證 Pantheon 寫入容量／檔案數預算、保留輪替、兩週期增長、回收與自動停損。
4. production actor 精確對齊 integration runtime SHA，六個既有 LaunchAgent 恢復。
5. 一次真實 rewrite 產出通過 provider → local gate → reviewer → publisher，形成新的 rewrite release。
6. 其他三 Lane 保持 exit 0，且沒有新容量異常。
