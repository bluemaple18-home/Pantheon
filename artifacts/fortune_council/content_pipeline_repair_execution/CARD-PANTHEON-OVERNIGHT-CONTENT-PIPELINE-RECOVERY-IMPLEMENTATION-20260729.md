# CARD-PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-IMPLEMENTATION-20260729

## Thread contract

- sidebar title: `CARD-PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-IMPLEMENTATION-20260729`
- source host: `slingshot:env_e_6a17b3781858832daee8697c30fc7e7c`
- source thread: `019fab40-ef11-74c3-b113-a1d2a295d495`
- execution boundary: 正式可見 thread；只能在平台建立的獨立乾淨 worktree 施工，不得使用或搬入主工作區 dirty working tree。

## Verified thread receipt

- status: `RUNNING`
- thread_id: `019fab58-0c2f-7223-ac89-bb0adb865f54`
- thread_host_id: `slingshot:env_e_6a17b3781858832daee8697c30fc7e7c`
- thread_status: `active_in_progress`
- worktree_path: `<codex-worktrees>/93954b6b-3be2-487a-a673-e1fa05d2adef/Pantheon`
- worktree_exists: `true`
- branch: `detached@baa29d87fd472da5ceeea7b10a1eaf7311baa8b5`
- clean: `true_at_thread_creation`
- gate_1_card_contract: `passed`
- gate_2_visible_thread: `passed`
- mainline verification: thread 可由 list 查詢、title/preview 正確、cwd 為獨立 worktree，且 HEAD 正好為 reference SHA。

## Card identity

- card_id: `CARD-PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-IMPLEMENTATION-20260729`
- chain_id: `PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-20260729`
- role: `implementation`
- target delivery status: `DELIVERED_CANDIDATE`
- thickness: `strict`
- risk: `high`
- routing decision: `gpt-5.6-sol / high`
- routing reason: 跨產文、排程與 publisher 部署契約，涉及正式發布前的 fail-closed 邊界與多模組 invariant。
- card_path: `artifacts/fortune_council/content_pipeline_repair_execution/CARD-PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-IMPLEMENTATION-20260729.md`
- evidence_path: `artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-implementation-20260729/`

## Startup contract

先確認 `pwd` 是平台 worktree 且不等於主工作區，記錄 `git status --short --branch`、HEAD、branch、worktree path、`index.lock`。執行：

```bash
bash ${AI_CORE_DIR:-$HOME/ai-core}/scripts/worktree_capability_preflight.sh --check --root <worktree-root>
bash ${AI_CORE_DIR:-$HOME/ai-core}/scripts/worktree_capability_preflight.sh --prepare --root <worktree-root> --require-python-tests
```

確認 baseline 含有 reference SHA `baa29d87fd472da5ceeea7b10a1eaf7311baa8b5` 的內容契約；若預設 baseline 缺少必要 runtime，立即回報 `BLOCKED / BASELINE_MISMATCH`，不得自行搬運 dirty working tree。

## 五行摘要

1. 目標：把新文 repair、publisher 部署接線與 `NEW_ONLY` 狀態顯示修到可安全 dry-run，交付可審查 candidate commit。
2. 範圍：只改 allowlist；所有施工在獨立乾淨 worktree。
3. 禁區：不得放寬 validator、改文章內容／registry／feed、操作正式 queue、載入 launchd、push、deploy 或發布。
4. 驗證：先建立 red-capable 回歸測試，再跑指定 pytest、shell/plist 檢查與 `git diff --check`。
5. 交付：保存 evidence、提交單一 candidate commit，狀態只能是 `DELIVERED_CANDIDATE`，交回主線另開獨立 Review。

## Root question

如何在不放寬內容政策、不直接操作 production、不搬入主工作區 dirty state 的前提下，讓 Pantheon 自動文章流程恢復為：

1. machine-owned 長度問題能在 bounded repair 內收斂；
2. publisher 部署設定能 fail-closed 地偵測 actor／queue 漂移並提供安全 dry-run；
3. `AGY_GEMINI_NEW_ONLY=1` 時，停用的 rewrite backlog 不再偽裝成可執行 active 工作。

## 已知證據

- 2026-07-28 18:00 至 2026-07-29 08:26（Asia/Taipei）共有 319 篇不重複文章登記：61 complete、11 validator PASS、50 validator FAIL、251 technical failed、7 active。
- 2026-07-29 00:27 後 cohort：60 registered、58 complete、8 PASS、50 FAIL、0 technical failed、2 active。
- `auto-new-v1-20260729-071-01` 經三次 writer attempt 後仍為 description 61 字（低於 70）、body 2104 字（高於 2000）；repair prompt 已包含 measured targets，但沒有收斂。
- 本機 deterministic gate 正確擋下 `description_length`、`body_length`、`paragraph_length`、`banned_phrase`；不得靠放寬 gate 解決。
- 已安裝 publisher plist 指向舊 actor／舊 queue，publisher launchd 服務未載入；舊 stderr 顯示 actor runtime 與 `origin/main` 不一致。
- coordinator 與 new lane 每 60 秒正常退出，最後 exit code 0。
- `AGY_GEMINI_NEW_ONLY=1` 下 rewrite runner 回報 `disabled/new_only`，但仍有 5 個歷史 rewrite states 顯示 active、1 個 rewrite outbox job 殘留。
- API rate-limit／HTTP failure 在 00:27 後 cohort 未再出現；禁止改 rate-limit、credential pool、writer/reviewer model。

## 可證偽假說

### H1 — create repair 契約過寬

若把 machine-owned finding 改為欄位／正文局部 repair，並以 trusted measurements 建立更窄契約後，回歸 fixture 應在 bounded repair 內通過既有 deterministic gate；若仍不通過，停止回報，不得放寬 validator。

### H2 — publisher 是部署設定漂移

新增或強化 read-only preflight 後，錯 actor／queue fixture 必須 fail closed，正確 fixture 必須輸出安全 dry-run 計畫；若核心 publisher 測試仍失敗，停止 production 操作。

### H3 — rewrite 假 active 是 reporting／lifecycle 缺口

在不搬動 queue 檔案前提下，coordinator 應把停用 lane backlog 分列 disabled／paused inventory，且不計入 runnable active；若需 destructive mutation，停止交回主線。

## Allowlist

- `artifacts/fortune_council/content_pipeline_repair_execution/CARD-PANTHEON-OVERNIGHT-CONTENT-PIPELINE-RECOVERY-IMPLEMENTATION-20260729.md`
- `scripts/agy_seo_copy_pipeline.py`
- `scripts/agy_gemini_coordinator.py`
- `scripts/agy_content_publisher.py`
- `scripts/install_agy_content_publisher_launchd.sh`
- `ops/launchd/com.pantheon.agy-content-publisher.plist.example`
- `tests/test_agy_seo_copy_pipeline.py`
- `tests/test_agy_gemini_coordinator.py`
- `tests/test_agy_content_publisher.py`
- `docs/pantheon_gemini_outbox_runner.md`
- `docs/pantheon_deployment_workflow.md`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/overnight-content-pipeline-recovery-implementation-20260729/**`

若最小修復需要 allowlist 外檔案，停止並列出原因，不得自行擴張。

## Forbidden scope

- 不得修改 `app/web/static/article-meta.js`、文章 body、文章 registry、generated pages、sitemap、feed、redirects 或共享整合檔。
- 不得讀取、輸出、修改 API key、OAuth、credential pool secret 或 token。
- 不得修改 writer/reviewer model、rate-limit、cooldown、credential allocator、strict round-robin。
- 不得降低或移除 70–95 description、1300–2000 body、paragraph、policy、originality 或 safety gate。
- 不得修改真實 `.work/gemini-runner`、`.work/gsc-copy`、publisher ledger、queue 或歷史 run state。
- 不得執行 `launchctl bootstrap/bootout/kickstart`、installer 寫入、production publisher、`--push`、正式 publish、deploy、PR、merge、`git push`。
- 不得帶入主工作區未提交變更、binary、PNG、截圖、prototype artifacts 或 `.pnpm-store`。
- 不得刪除、archive 或清理既有 thread、branch、worktree。

## 實作契約 A — Create repair closure

- 先用最小 fixture 重現「prompt 有 measurements，但 repair 後仍超出 deterministic 長度」。
- machine-owned finding 只能由本機 validator 判定；Reviewer 不得覆寫。
- repair 必須 bounded，只重做必要欄位／body，不得無條件重生已通過的 identity、URL、tags、FAQ、publication policy。
- deterministic gate 未通過時避免浪費獨立 Reviewer 呼叫；若架構不允許，保留並在 evidence 說明。
- 最終 candidate 仍須經既有 `validate_candidate`、deterministic findings 與 publication policy gate。

## 實作契約 B — Publisher deployment preflight

- 鎖定 desired repo/actor、queue root、state root、runtime SHA、push mode 契約。
- 錯 actor、錯 queue、runtime mismatch、dirty actor、local HEAD 不等於 `origin/main` 必須 fail closed。
- 提供 read-only/dry-run 驗證路徑；本卡不得載入服務或發布文章。
- 文件與指令只能用 `<repo-root>` 或 repo-relative path，不得新增本機絕對路徑。

## 實作契約 C — NEW_ONLY disabled backlog

- 保留 runner fail-closed disabled 行為。
- coordinator summary 區分 runnable active 與 disabled backlog。
- 只做 reporting/lifecycle contract，不搬動或刪除真實 outbox/runs。

## Verification

```bash
uv run pytest tests/test_agy_seo_copy_pipeline.py tests/test_agy_gemini_coordinator.py tests/test_agy_content_publisher.py
bash -n scripts/install_agy_content_publisher_launchd.sh
plutil -lint ops/launchd/com.pantheon.agy-content-publisher.plist.example
git diff --check
```

並保存 red→green reproduction、測試摘要、publisher 僅 dry-run/read-only 證明、changed files allowlist 一致性、未執行 production/push/deploy 聲明、residual risks。

## Evidence

至少包含：

- `preflight.md`
- `reproduction.md`
- `verification.md`
- `result.md`

## Stop conditions

- 同一 blocker 第 3 次失敗即停，不做第 4 次。
- baseline 缺必要 runtime、worktree 不乾淨、Git metadata/index lock 異常、需要 allowlist 外修改、production mutation 或 secret 時立即 `BLOCKED`。
- 無法建立 red-capable reproduction 時不得猜測改碼。

## Delivery

- 只提交 allowlist 與 evidence。
- 建立單一 candidate commit，回報完整 SHA、changed files、驗證結果、已知風險。
- 不得宣稱 `ACCEPTED`、`INTEGRATED`、`CLOSED` 或 production fixed。
- 正確狀態：`DELIVERED_CANDIDATE`；strict chain 的獨立 Review/Repair/主線整合由主對話另行建立正式可見 thread。
