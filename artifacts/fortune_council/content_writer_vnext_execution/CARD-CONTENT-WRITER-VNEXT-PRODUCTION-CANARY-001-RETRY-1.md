---
id: CARD-CONTENT-WRITER-VNEXT-PRODUCTION-CANARY-001-RETRY-1
status: ready
chain_id: CONTENT-WRITER-VNEXT-RUNTIME-ACTIVATION
role: canary-executor
cycle: 1
supersedes_card_id: CARD-CONTENT-WRITER-VNEXT-PRODUCTION-CANARY-001
supersedes_dispatch_key: v1:ffeb06e993839e4ddb420413bedfaefeb00fd2b3fd6ca76060d9dd97038101ce
replacement_reason: 舊 reservation 綁定已淘汰 project ID；舊正式 task 僅完成 bootstrap，worktree clean 且無 unique work。
execution_authorized: false
production_authorized: false
publication_authorized: false
push_authorized: false
service_activation_authorized: false
thickness: critical
risk: critical
model: gpt-5.6-sol
reasoning: high
model_reason: 單次 production canary 會觸及正式模型、內容 transaction、release tag 與 origin/main 原子 push；任何 selector、identity、容量或 rollback 判斷錯誤都可能直接影響公開內容，需 Sol high 嚴格執行並 fail closed。
traces_to:
  - RA-CHECKPOINT-B
  - SC-production-canary-readiness
  - SC-human-authorization
  - FR-014
depends_on:
  - CHECKPOINT-B-READY@7a8b927fa7f56199b31371e4ab5d6608b18dd7c9
---

# Writer vNext 單次 Production Canary RETRY-1

## 工作名稱 → 正在做什麼 → 現在狀態

- 工作名稱：Writer vNext 單次 Production Canary RETRY-1
- 正在做什麼：以唯一 run、唯一 correlation、最多一篇新文，走正式 create → run → select → publish → transaction → tag → atomic push；失敗即停並保留證據。
- 現在狀態：`READY_FOR_DISPATCH / BOOTSTRAP_ONLY`。本卡只授權安全重建正式 task；production 執行仍需主線再次明確啟動。

## 授權邊界

使用者已明確授權正式退役舊 task 並建立、派送本卡。現階段授權只涵蓋：

1. 建立唯一 RETRY-1 正式 task 與獨立 worktree。
2. 執行 Bootstrap-only 第一拍與唯讀 pre-canary preflight。

未取得與新 dispatch key 對應的 activation token 及主線明確 production 啟動前，下列動作全部禁止：

1. 一個 production canary execution line。
2. 一個新文 run；最多發布一篇文章。
3. 一次正式模型執行所需的既有 production credential/provider 呼叫。
4. 一個 isolated publisher transaction。
5. 一個符合 release gate 的 annotated tag。
6. 一次 `git push --atomic origin HEAD:main v<version>`；目標 remote 固定 `git@github.com:bluemaple18-home/Pantheon.git`。

不授權：launchctl mutation、plist 安裝、七服務 aggregate activation、常駐排程、四 lane 服務啟用、第二篇文章、第二個 run、第二次模型呼叫鏈、第二次 push、force push、非 atomic push、deploy 控制面操作、清理舊 queue／evidence、修改 ai-core。

## 固定來源與權威

- Source parent：`7a8b927fa7f56199b31371e4ab5d6608b18dd7c9`。
- Checkpoint B：`runtime_activation/ra_checkpoint_b_reassessment/**`。
- Capability authority：`scripts/pantheon_writer_vnext_runtime_activation_readiness.py`、`scripts/pantheon_content_capability_receipt.py`。
- Runtime entry：`scripts/agy_gemini_coordinator.py`、`scripts/agy_gemini_runner.py`。
- Publisher entry：`scripts/agy_content_publisher.py`，必須使用 exact run selector。
- Capacity authority：`scripts/pantheon_writer_vnext_runtime_activation_capacity.py`、`scripts/pantheon_content_capacity_guard.py`、目前 host fresh sample。
- Deployment contract：`docs/pantheon_deployment_workflow.md`。

## Bootstrap-only 第一拍

收到 activation token 前只做唯讀：

1. 核對 cwd 是獨立 worktree、HEAD 等於 card source、worktree clean、卡片可由 HEAD 讀取。
2. 核對 remote URL、`origin/main`、fast-forward lineage、Git hook、release gate、credential/provider 存在性；不得輸出 secret。
3. 重建 repo readiness package，再呼叫 official thin gate；驗證 positive READY、missing-step BLOCKED、adversarial thin receipt 被 repo authority 擋下。
4. 重新取兩次 current-host capacity sample；任一低於 `max(20 GiB, 10% total)` 即停。
5. 唯讀列出可用的新文 brief 候選；只可選一個尚未發布、無 existing active/completed run collision、內容來源與 locale 契約完整的候選。
6. 回報 exact payload：`run_id`、`article_id`、lane、locale、source digest、correlation ID、預計 release version/tag、origin/main SHA、rollback 動作。

任一欄缺失：`BLOCKED / PRE_CANARY_PREFLIGHT`，不得寫入 production。

## 執行契約

取得 activation token 後仍須先確認 bootstrap 證據未漂移，才可執行：

1. 建立或註冊唯一新文 run；禁止 auto sweep、legacy sweep、rewrite、i18n 與多 run selector。
2. Coordinator 與 runner 只能使用 `--exact-run-id <run_id>` 或等價正式 exact selector；每步保存 actor、runtime identity、input/output digest 與同一 correlation。
3. Publisher 必須 `--exact-run-id <run_id> --max-runs 1`；先 dry-run，再執行一次正式 transaction。
4. 不得使用 `--skip-tests` 或 `--skip-release-gate`。
5. 正式 transaction 必須只含：該篇文章、必需 registry/meta/SEO/sitemap/feed/redirect/cache/version/changelog 衍生變更與本卡 evidence。若 diff 出現其他路徑，停止且不得 tag/push。
6. 推送前再次重驗 current-host capacity、remote `main` 未漂移、release record、annotated tag 指向 transaction commit、公開 canonical redirect gate。
7. 只允許一次 atomic push。命令失敗、remote 漂移或非 fast-forward：停止；不得 retry、force、改用兩次 push。
8. push 成功後只做唯讀公開驗收；不得以等待部署為由操作 deploy 控制面。

## Stop-loss 與回復

- 建立 run 前、模型 I/O 前、publisher transaction 前、push 前各跑一次必要 identity/capacity gate。
- 任一 identity/correlation/digest 不連續、selector 不唯一、容量 deficit、未知 write path、transaction temp root 未清、測試失敗、release gate 失敗：立即停止下一步。
- push 前失敗：不推送；保留 queue、run、transaction、log、evidence，不刪除。
- push 後公開驗收失敗：停止後續 run；不得自行 force-revert 或刪 remote tag。產出 exact rollback candidate/commands，回主線取得新的明確 rollback 授權。
- 本卡不啟用常駐服務；canary 結束後正式服務狀態仍須誠實回報，不得宣稱 `4/4`。

## 可改範圍

Production runtime/state write：只允許唯一 canary run 對應的既有正式 queue/state/log 路徑。

Repo candidate/transaction 可改：

- 唯一 canary 文章來源與產物。
- `app/web/static/article-registry.js`
- `app/web/static/article-meta.js`
- `app/web/static/article-seo.js`
- `app/web/sitemap.xml`
- `app/web/_redirects`
- `app/web/static/**` 中該文章必需的生成檔與 cache query。
- `pyproject.toml`
- `package.json`
- `CHANGELOG.md`
- `artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/production_canary_001_retry_1/**`

任何實際路徑必須由 publisher 正式 transaction 產生並在 evidence 中列出。未列路徑或非該篇衍生變更一律阻擋。

禁止修改：scripts、tests、ops/launchd、AGENTS.md、`.ai/**`、ai-core、既有 RA004–RA007／Checkpoint B／Review／Repair evidence。

## 必驗與證據

Evidence root：

`artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/production_canary_001_retry_1/`

至少保存：

- `preflight-receipt.json`
- `capacity-samples.json`
- `payload.json`
- `execution-line.json`
- `publisher-dry-run.json`
- `transaction-manifest.json`
- `release-gate.txt`
- `push-receipt.json`（未推送也要記錄 `NOT_ATTEMPTED` 與 blocker）
- `public-acceptance.json`（若 push 成功）
- `rollback-receipt.json`
- `verification.md`

必跑：受影響 tests、release gate、`git diff --check`、JSON parse、changed-path allowlist、secret scan。公開驗收至少核對 canonical、文章 URL、mobile、registry/meta/SEO/sitemap 與 release SHA。

## 唯一交付結論

- `CANARY_PASS`：唯一 run 全鏈成功、一次 atomic push 成功、公開驗收通過、無下一篇或服務常駐。
- `BLOCKED`：push 前 fail-closed，附最後成功 step 與未嘗試操作。
- `CANARY_FAIL_ROLLBACK_AUTH_REQUIRED`：push 後公開驗收失敗，附 rollback candidate；不得自行回復。

不得宣稱 permanent runtime activation、正式四 lane `4/4` 或 production rollout 完成。
