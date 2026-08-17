---
id: CARD-PANTHEON-GEMINI-QUOTA-ROUTING-PUSH-INTEGRATION-20260817
status: ready
chain_id: PANTHEON-GEMINI-QUOTA-ROUTING-20260817
role: implementation
cycle: 1
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 規格固定但涉及 GitHub push、分支整合與 runtime identity 後續邊界，需以 strict core-bounded 契約執行。
ownership: Gemini 配額感知路由功能分支推送、乾淨整合候選與驗證
allowed_files:
  - .ai/codex_task_gemini_quota_routing_push_integration_20260817.md
  - .ai/handoff_20260817_gemini_quota_routing_ready_for_integration.md
  - .ai/evidence/gemini_quota_routing_push_integration_20260817/**
  - scripts/agy_gemini_allocator.py
  - scripts/agy_gemini_outbox.py
  - scripts/agy_gemini_runner.py
  - scripts/agy_seo_copy_pipeline.py
  - scripts/install_agy_gemini_coordinator_launchd.sh
  - tests/test_agy_gemini_allocator.py
  - tests/test_agy_gemini_coordinator.py
  - tests/test_agy_gemini_outbox.py
  - tests/test_agy_seo_copy_pipeline.py
forbidden_scope:
  - production LaunchAgent 安裝、啟用、重載或停止
  - runtime promotion apply、production canary、外部模型呼叫或文章發布
  - 直接推送、合併或修改 origin/main
  - 修改文章、registry、sitemap、feed、redirect 或 publisher transaction
verification:
  - 核對 origin URL、origin/main 與來源 commit lineage
  - 推送 codex/gemini-model-quota-fallback-20260817 到可信 origin
  - 在獨立乾淨 integration branch/worktree 整合並處理必要衝突
  - 跑受影響 pytest、installer bash syntax、git diff --check
  - 輸出 candidate commit、remote branch identity、changed paths 與 production mutation=0
evidence_path: .ai/evidence/gemini_quota_routing_push_integration_20260817/
---

# Gemini 配額路由推送與乾淨整合

## 目標

把已完成並修正的 Gemini Writer／Reviewer 配額感知路由推到可信 `origin`，再以乾淨、可重現的方式準備最新 `origin/main` 上的整合候選，讓後續 runtime identity 重產與 no-mutation canary 有正式來源。

## 固定來源

- 功能分支：`codex/gemini-model-quota-fallback-20260817`
- 功能 commit：`802133cc99f8f329e8d46b1ca3756db103d95980`
- 429 分類修復 commit：`23de80fc7e`
- 建卡時 base：`origin/main = 2d8d8cb27e872f21c445d863bd7e15dbd1c0a7f7`
- 既有交接：`.ai/handoff_20260817_gemini_quota_routing_ready_for_integration.md`

執行時必須重新解析完整 SHA；若上述短 SHA、branch lineage、remote 或 `origin/main` 漂移，先保存證據並只做必要的乾淨 rebase／merge 決策，不得 force push 或改寫遠端歷史。

## 執行契約

1. 先讀 `AGENTS.md`、本卡與既有交接，執行 CodeGraph source decision；確認 worktree 獨立、乾淨且 HEAD 精確為建卡來源。
2. 唯讀核對 `origin` remote URL 與最新 `origin/main`；只接受可信 Pantheon repository。
3. 普通推送功能分支 `codex/gemini-model-quota-fallback-20260817`；禁止 force、force-with-lease、tag、delete ref 或直接寫 `main`。
4. 若 `origin/main` 未漂移且是來源 ancestor，現分支可作整合候選；若已漂移，建立新的 `codex/gemini-quota-routing-integration-20260817`，在獨立乾淨 worktree 以非破壞方式整合。
5. 只處理本卡 allowlist 內、由 upstream drift 直接造成的衝突；若需要修改 publisher、runtime authority、LaunchAgent template 以外檔案或共享生成檔，回 `BLOCKED_SCOPE_CHANGE`。
6. 重跑驗證並保存精簡 evidence；若發現 P0／P1，留在本正式 task 修正並追加 commit，不建立 replacement task。
7. 交付 `DELIVERED_CANDIDATE`：列出 remote feature ref SHA、integration candidate SHA、base SHA、changed paths、測試結果與剩餘風險。

## 驗收

- `origin/codex/gemini-model-quota-fallback-20260817` 精確指向已驗證候選，且無 force push。
- 整合候選建立於最新可信 `origin/main`，worktree 乾淨。
- Writer／Reviewer model 必須不同；只有三個安全 slot 的同模型 `PerDay` quota 都耗盡才降級；RPM 429／503 不降模型。
- 受影響 suites、installer 測試、`bash -n scripts/install_agy_gemini_coordinator_launchd.sh`、`git diff --check` 全通過。
- production activation、canary、provider call、publish、transaction、tag、push main 與 deploy 全為 `0`。

## 交付限制

本卡授權推送功能分支與建立本機整合候選，不授權直接更新 `origin/main`、production runtime 或發文。完成後等待主線驗收與後續獨立啟用授權。
