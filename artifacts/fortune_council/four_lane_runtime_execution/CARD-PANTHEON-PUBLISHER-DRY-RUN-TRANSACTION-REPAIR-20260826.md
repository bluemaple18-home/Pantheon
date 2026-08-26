---
id: CARD-PANTHEON-PUBLISHER-DRY-RUN-TRANSACTION-REPAIR-20260826
status: blocked
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

## Promotion blocker

- 正式 promotion plan：`NO-GO / preserved run directory is outside durable root`；未執行 apply、push 或 runtime mutation。
- 既有 promotion contract 把所有 preserved run_dir 限制在 `queue/gsc-copy`，但 production registry 同時包含正式 translation root、舊 runtime durable root 與已失聯的 actor-local 歷史路徑；這是保存契約分類不足，不得直接解讀為「146 個 run 全部搬家」。
- 148 個 registry state 的唯讀分類：
  - `queue/gsc-copy`：2 個，維持原位。
  - `queue/translation-runs`：18 個（6 active、2 complete、10 failed），本來就在 durable queue；禁止為滿足錯誤 allowlist 而搬到 `gsc-copy`。
  - runtime sibling `gsc-copy`：120 個（31 complete、89 failed），先保留原位並依 lifecycle 分類；禁止整批 rehome。
  - actor-local `.work/gsc-copy`：8 個且全為 failed，實體目錄已不存在；不得建立假目錄或偽造 artifact lineage。

## 歷史 complete 決策

- 120 個舊 runtime state 中的 31 個 complete 必須拆開處理，不得統稱為待搬資料：
  - 2 個 create run 已記錄於 publisher ledger，且文章 ID 已存在於目前網站；只保留歷史證據。
  - 26 個 create run 未發布：候選稿全數 clean APPROVE、沒有跨稿完全重複段落，但 ID 與 slug 均不存在於目前網站，也未登記於 content backlog／prior-art registry；其正式 mode 是 `create`，禁止改標為 `rewrite_existing_body`。
  - 3 個真正的 `rewrite_existing_body` run：`ASTRO-BASE-01`、`ASTRO-BASE-03` 已 released；`ASTRO-BASE-02` clean APPROVE 但尚未 released，是唯一可繼續舊文驗收的歷史 complete。
- 26 個未發布 create run 的處置是「退出 operational publish queue，保留冷封存與 immutable identity」：
  - 不發布、不重驗新文、不轉成舊文重寫。
  - 保留 run identity、題目、primary keyword、candidate/review digest 與原始 artifact，避免失去稽核證據或被 seeder 當成從未生成而重做。
  - 後續若要把某個題目併入既有文章，必須另有明確 canonical article ID，重新以 rewrite brief 建立 lineage；不得沿用原 create run 冒充 rewrite。

## 最小 preservation contract

1. active／complete：必須保留可解析的 immutable identity 與實際 artifact；合法 durable root 依 lane 明確判定，不以單一 `queue/gsc-copy` allowlist 代替 lifecycle 驗證。
2. terminal failed：registry identity 是 authoritative tombstone；若 run_dir 已不存在，不得為通過 promotion 製造或搬移假 artifact。缺 identity envelope 的歷史項目必須 fail closed，另以可驗證的既有 brief／evidence 補證，不能猜測。
3. released／published：以 publisher ledger 加公開內容證據判定，只保留歷史，不重新排入 publish。
4. superseded create：保留冷封存與 identity，但排除 operational selection；不得刪除後讓相同 topic 被重新 seed。
5. translation：保留 `queue/translation-runs` 的 lane 邊界；本卡不重驗翻譯內容，也不改 translation run 狀態。

## 下一個 RED gate

- 先新增 promotion regression，證明下列情境在任何 runtime mutation 前可被區分：
  1. durable translation run 不因位於 `queue/translation-runs` 被誤判為 actor-local。
  2. terminal failed tombstone 不要求建立不存在的 run_dir，但缺少可驗 identity 時仍 fail closed。
  3. create candidate 不得靠改 mode 或改路徑冒充 rewrite。
  4. published／released 與 superseded create 不會重新進入 operational publish selection。
- RED 證據閉合前，不修改 production registry、不移動 run_dir、不執行 promotion apply、push 或 A/B 重驗。
- 本修復沿用同一張卡，不建立第四張卡；完成 preservation contract 的最小 code repair 與受影響 gate 後，才允許重新產生 read-only promotion plan。
