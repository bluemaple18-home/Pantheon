---
id: CARD-PANTHEON-PUBLISHER-DRY-RUN-TRANSACTION-REPAIR-20260826
status: verified
thickness: strict
risk: high
---

# Pantheon Publisher dry-run transaction 修復

## 目標與邊界

- 修正正式 Publisher CLI 的 dry-run routing：與實際 publish 一樣，從最新 `origin/main` 建立隔離 transaction worktree，再執行指定 lane 的 dry-run。
- 保留 immutable runtime actor；禁止把 actor `6477ab815e…` 回推覆蓋遠端 `0257bd5213…`。
- 只修改 `scripts/agy_content_publisher.py`、`tests/test_agy_content_publisher.py` 與本卡證據；不碰 production queue/state/registry、公開內容與七個 launchd 服務。
- 遠端 write 只能是包含既有遠端 main 的 fast-forward；任何 SHA drift 或 non-fast-forward 立即停止。

## 根因證據

- 最後成功版本：actor `6477ab815e8aecca7d1e8e1588e6e5eba0fab001` 成功發布遠端子 commit `0257bd5213eed0d0df10661a54f6215901a54997`。
- 失敗起點：成功 publish 後，CLI dry-run 直接在 immutable actor 呼叫 lane publisher，觸發 `_assert_clean_origin_head`。
- Durable invariant：actor 是 runtime code authority；內容 authority 是最新 `origin/main`。dry-run 與 write path 都必須使用同一個 latest-origin isolated transaction seam，且先驗 runtime digest 無 drift。
- 排除方案：禁止 force push／回推 actor；禁止用反覆 promotion 掩蓋每次 publish 後必然再次出現的 drift。

## RED → GREEN

1. 新增 regression：actor 留在父 commit、remote 只新增 content commit，CLI dry-run 必須把 transaction root 傳給 publisher function，而不是 actor root。
2. 先只跑該測試，確認現況 RED 且失敗原因是 publisher 收到 actor root。
3. 最小修改 `main()` dry-run 分支，沿用 `_isolated_transaction_worktree`。
4. 重跑 regression、相關 Publisher 測試、`git diff --check`。
5. 遠端與 actor runtime paths 無 drift、遠端即時 SHA 未變才允許 fast-forward push；再回原 A、B 正式 task 依序重驗。

## 回退

- code 回退：revert 本修復 commit。
- 遠端保護：push 前以 `--force-with-lease` 也禁止；只允許 ordinary fast-forward，GitHub main 必須仍為已驗證 SHA。
- 七個服務全程保持停止。

## 驗證結果

- RED：`test_main_runs_dry_run_in_latest_origin_transaction_worktree` 在修復前收到 actor root，`1 failed`。
- GREEN：同一 regression 加既有 real-publish／new-only routing 測試，`3 passed`。
- Publisher 全檔：`134 passed`。
- 受影響 release gate：`357 passed`；兩個既有 warning，無新增 failure。
- 遠端 `0257bd5213…` 已先無衝突合併進本機 main；備援分支 `codex/backup-pre-remote-convergence-20260826` 保留修復前 SHA。
