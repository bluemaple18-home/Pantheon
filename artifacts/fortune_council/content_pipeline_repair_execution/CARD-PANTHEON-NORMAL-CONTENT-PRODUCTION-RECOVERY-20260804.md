---
card_id: CARD-PANTHEON-NORMAL-CONTENT-PRODUCTION-RECOVERY-20260804
chain_id: PANTHEON-NORMAL-CONTENT-PRODUCTION-RECOVERY-20260804
role: implementation
cycle: 1
ownership: normal_content_recovery_integration_and_staged_activation
status: GO_ACCEPTED_2_OF_2
user_hold: false
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 候選跨 Gemini transport、Publisher 契約、主線整合、容量閘門與 production launchd；錯誤整合可能再次全域停機或污染正式發布，需 strict 隔離 worktree、獨立 Review 與主線驗收。
source_ref: origin/main
source_sha: cd2a36fd214e624dffbf9855f4b4f0a6861a9570
dispatch_base_ref: codex/normal-content-production-recovery-20260804-base
worktree: platform_assigned_independent_worktree
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/normal_content_production_recovery_20260804
---

# Pantheon 正常產文分階段復工卡

## 五行派工摘要

1. 從 `origin/main@cd2a36fd21` 建立乾淨候選，只整合已交付的 Publisher 日期契約修復與 Gemini HTTP 安全診斷修復。
2. 排除兩個來源 worktree 的未提交 `uv.lock`；不得整合日韓品質候選、delivery receipt commit 或其他漂移。
3. 實作 thread 只交候選 commit、完整測試與可重現 runbook；不得啟動 production、呼叫 Gemini、push 或發布。
4. 主線獨立 Review GO、容量閘門 PASS 後，先恢復 `new`、`rewrite`、Coordinator、Publisher；`i18n-new`、`i18n-rewrite` 維持暫停。
5. 驗收必須由 `new`、`rewrite` 各一次真實 provider → gate → Reviewer → Publisher → commit/tag/push 證明；`idle`、服務 loaded、fixture 或舊 release 均不算。

## Root question

如何在不讓日韓品質 canary 綁住全站的前提下，恢復正常新文與重寫正式產出，並保留足以判斷後續 Gemini HTTP 失敗的安全診斷？

## 已知事實

- production actor 與 `origin/main` 目前均為 `cd2a36fd214e624dffbf9855f4b4f0a6861a9570`，是日韓候選回滾後 runtime。
- `new`、`rewrite`、`i18n-new`、`i18n-rewrite`、Coordinator、Publisher 目前均為人為 `PAUSED`；capacity guard 為 `PASS`，不是本次停機來源。
- Publisher 日期候選 `1b7924abb680a47be2c10d358302178f65f8d52e` 的 parent 為 `cd2a36fd21`；修正 stale test，維持 rewrite `updated` 可前進、`published` 不變。
- Gemini HTTP 診斷候選 `6b5e4b67a136c6432b5020ad85cda9ee552d5c7c` 的 parent 為 `cd2a36fd21`；只保存封閉 `http_status`／`http_status_class`，不改 request、模型、retry、rotation 或品質 gate。
- 兩個來源 worktree 現有未提交 `uv.lock` 漂移，不屬於候選 commit，必須排除。
- 日韓四格 canary 仍為 `0/4`；本卡不宣稱日韓修復完成，也不恢復 production i18n runners。

## 使用者故事

### 正常產文不再被日韓 canary 全域阻斷 <!-- US-001 -->

作為內容營運者，我要繁中新文與重寫先在原有品質、安全與容量閘門下恢復正式產出，同時把日韓品質驗證留在隔離 queue，避免單一 locale 或 provider 問題再次停止整套內容系統。

## 功能需求

- **FR-001**：候選必須精確整合 `1b7924abb680a47be2c10d358302178f65f8d52e` 與 `6b5e4b67a136c6432b5020ad85cda9ee552d5c7c` 的 patch identity，base 固定為 `cd2a36fd21`。 <!-- FR-001 traces_to: US-001 -->
- **FR-002**：候選 diff 只允許兩個 commit 的 7 個 code／test 檔與本卡唯一 evidence；不得包含 `uv.lock`、日韓品質 patch、生成內容、registry、sitemap、feed、redirect、plist 或 queue state。 <!-- FR-002 traces_to: US-001 -->
- **FR-003**：Publisher 必須維持 substantive rewrite 的 `updated == publicationPolicy.modified`、`published` 不變，以及 full-test failure atomic rollback。 <!-- FR-003 traces_to: US-001 -->
- **FR-004**：Gemini failure receipt 只新增封閉且相互一致的 `http_status`／`http_status_class`；不得保存 body、prompt、credential 或 account secret，也不得改 retry、rotation、模型與 failure category。 <!-- FR-004 traces_to: US-001 -->
- **FR-005**：主線 activation 只載入 `com.pantheon.agy-gemini-new`、`com.pantheon.agy-gemini-rewrite`、`com.pantheon.agy-gemini-coordinator`、`com.pantheon.agy-content-publisher`；兩個 i18n runner 必須保持未載入。 <!-- FR-005 traces_to: US-001 -->
- **FR-006**：復工停損按 lane／共享依賴精準處理；一般 canary failure 不得借用 capacity guard 的六服務全停演練。只有 capacity guard 真正命中容量契約時才允許其既有全內容停損。 <!-- FR-006 traces_to: US-001 -->
- **FR-007**：真實驗收需保存 `new`、`rewrite` 各一個新的 release commit、annotated tag、origin push、run lineage 與容量前後樣本；舊 release 與 idle 不得計數。 <!-- FR-007 traces_to: US-001 -->

## 驗收情境

1. 從固定 base 套用兩個候選時，patch identity 與來源 commit 相同，且 `git diff` 不含 `uv.lock` 或日韓品質程式。 <!-- AS-US001-01 traces_to: FR-001 -->
2. Allowlist 檢查只得到 7 個 code／test 檔與唯一 evidence；任何共享生成檔或 production state 進 diff 都 fail closed。 <!-- AS-US001-02 traces_to: FR-002 -->
3. 合法 rewrite 把 `updated` 推進到本次 `modified`、保留 `published`，而 full test 失敗仍回到乾淨 base。 <!-- AS-US001-03 traces_to: FR-003 -->
4. 離線 400、401、403、404、429、500、503 fixture 產生正確 sanitized status；forged／不一致 receipt 仍 fail closed。 <!-- AS-US001-04 traces_to: FR-004 -->
5. Activation 後四個正常服務可查，兩個 i18n runner 仍不可查；任何自動恢復 i18n 都判定 NO-GO。 <!-- AS-US001-05 traces_to: FR-005 -->
6. `new` 或 `rewrite` 單 lane 失敗時只停該 runner；Publisher 契約失敗只停 Publisher；不因日韓或單一 lane failure 全停六服務。 <!-- AS-US001-06 traces_to: FR-006 -->
7. Activation 後新產生的 `new`、`rewrite` 各完成一次正式發布，且容量 samples 均在預算內。 <!-- AS-US001-07 traces_to: FR-007 -->

## 成功條件

- **SC-001**：候選 branch 以兩個已知 code commit 組成，無來源 worktree 未提交漂移。 <!-- SC-001 traces_to: FR-001 -->
- **SC-002**：Provider affected suite、Publisher official release gate、compile 與 `git diff --check` 全通過。 <!-- SC-002 traces_to: FR-003 -->
- **SC-003**：獨立 Review 對固定 base/current SHA 判定 `REVIEW_GO`，無未解 P0/P1。 <!-- SC-003 traces_to: FR-001 -->
- **SC-004**：容量上線前閘門與 activation 後至少兩個完整取樣週期均為 `PASS`，主機保留空間高於強制門檻。 <!-- SC-004 traces_to: FR-006 -->
- **SC-005**：`new`、`rewrite` 真實 release grid 為 `2/2`；i18n production grid 保持 `NOT_STARTED / PAUSED`。 <!-- SC-005 traces_to: FR-007 -->

## 可執行切片

### `SLICE-NCR-ASSEMBLE-001`｜候選精確組裝

- traces_to: `FR-001`、`FR-002`、`SC-001`
- frontier: `CURRENT`
- blocking_edges: 無。
- actions:
  - 驗證兩候選 parent 都是 `cd2a36fd21`、commit 可讀且 patch allowlist 正確。
  - 從本卡 base 依序 cherry-pick code commit；衝突即停止，不手工猜合併。
  - 驗證 patch identity；排除 `uv.lock`、delivery docs 與日韓候選。
- verification: `git diff --name-only <base>...HEAD`、`git patch-id --stable`、`git status --short`、`git diff --check`。
- mutation: 只限隔離 worktree branch；禁止 provider／production。

### `SLICE-NCR-VERIFY-002`｜整合 regression

- traces_to: `FR-003`、`FR-004`、`SC-002`
- blocking_edges: `SLICE-NCR-ASSEMBLE-001`。
- actions:
  - 重跑 Provider affected suite 與 Publisher official release gate。
  - 跑 Python compile、secret/debug marker 掃描、allowlist 與 diff check。
- verification:
  - `uv run pytest tests/test_agy_seo_copy_pipeline.py tests/test_agy_gemini_outbox.py -q`
  - 依 `scripts.agy_content_publisher.TEST_COMMAND` 執行官方 Publisher gate。
  - `uv run python -m py_compile` 覆蓋實際 changed Python files。
- mutation: 只限測試 cache／唯一 evidence；禁止 production queue。

### `SLICE-NCR-REVIEW-003`｜主線獨立 Review

- traces_to: `FR-001`、`FR-002`、`FR-003`、`FR-004`、`SC-003`
- blocking_edges: `SLICE-NCR-VERIFY-002` 與完整 candidate SHA。
- reviewer: 不得使用 implementation thread 自評；固定 base/current、實際 diff、測試 receipt 與兩個來源 commit。
- acceptance: 無 P0/P1、patch identity 一致、品質／安全／atomic gate 未降級才 `REVIEW_GO`。
- mutation: Review 唯讀。

### `SLICE-NCR-ACTIVATE-004`｜正常服務分階段啟動

- traces_to: `FR-005`、`FR-006`、`SC-004`
- blocking_edges: `SLICE-NCR-REVIEW-003`、主線整合完成、production actor clean、容量 preflight PASS。
- owner: 主線；implementation thread 不得執行。
- actions:
  1. 部署 reviewed candidate runtime，核對 actor/origin SHA 與 plist digest。
  2. 載入 Publisher、Coordinator、`new`、`rewrite`；明確核對兩個 i18n label 仍未載入。
  3. 觀察至少兩個完整五分鐘容量樣本與每個 60 秒排程週期。
- stop_loss:
  - lane failure：只停該 lane runner；保留其他正常 lane。
  - Publisher contract failure：只停 Publisher並保留 producer queue。
  - capacity guard 真命中：依既有容量契約停六服務；不得把一般 canary failure偽裝成容量事件。

### `SLICE-NCR-E2E-005`｜真實 2×1 release 驗收

- traces_to: `FR-007`、`SC-004`、`SC-005`
- blocking_edges: `SLICE-NCR-ACTIVATE-004` 服務與容量狀態均 PASS。
- acceptance:
  - `new`：一個本次 activation 後 run 完成 provider、deterministic、Reviewer、Publisher、commit、annotated tag、push。
  - `rewrite`：同上，且 `updated`／`published` 契約正確。
  - i18n：兩個 runner 保持 paused；任何 i18n release 不作本卡驗收。
- forbidden_substitutes: `idle`、loaded、HTTP 200、fixture、舊 tag、candidate、Reviewer 自評。
- rollback: 任一 lane 失敗只停止對應服務並保留 evidence，不回滾或停止已驗證正常 lane；共享 Publisher 失敗時只停 Publisher。

## 檔案所有權

### 允許修改

- `scripts/agy_gemini_outbox.py`
- `scripts/agy_gemini_runner.py`
- `scripts/agy_seo_copy_pipeline.py`
- `tests/test_agy_gemini_outbox.py`
- `tests/test_agy_seo_copy_pipeline.py`
- `tests/test_agy_content_publisher.py`
- `tests/test_web.py`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/normal_content_production_recovery_20260804/**`

### 禁止修改／帶入

- `uv.lock`、`pyproject.toml`、`package.json`（Publisher 正式 release 原子交易依既有流程更新者除外）。
- 日韓品質修復程式、prompt、validator、Reviewer gate 或任何 i18n scheduling policy。
- `app/web/**`、article registry、rewrite override、生成頁、sitemap、feed、redirects（正式 Publisher transaction 產出除外；不得成為 implementation candidate diff）。
- `~/Library/LaunchAgents/*.plist`、production queue、ledger、credentials、provider account 設定。
- 任何未列出的來源 worktree dirty／untracked 檔案。

## Implementation thread 交付契約

- 最終狀態只允許 `DELIVERED_CANDIDATE / READY_FOR_REVIEW` 或 `BLOCKED_WITH_EVIDENCE`。
- 必須交付完整 candidate commit SHA、實際 changed files、兩來源 patch identity、測試指令／exit／數量、工作樹 clean 與唯一 evidence receipt。
- 禁止自稱 `ACCEPTED`、`INTEGRATED`、`DEPLOYED`、`RUNNING` 或 production 復工完成。
- 禁止真實 Gemini／外部 provider 呼叫、launchctl mutation、push、tag、Publisher queue consumption 或 production actor mutation。

## 主線 activation／驗收契約

- 使用者已在本回合明確授權開卡執行正常產文復工；production mutation 仍必須等獨立 Review GO、主線整合與容量閘門 PASS。
- 啟動前核對目前 provider／publisher候選的實際 commit、actor/origin clean、LaunchAgent labels、capacity state 與 available disk。
- 每一步保存 before／after receipt；任一未知或失敗即停止後續步驟。
- 最終狀態只有 `GO`（真實 `new`＋`rewrite` 2/2 發布）或 `PARTIAL/NO-GO`；不得因其中一條成功就把另一條算完成。

## Evidence 交付

- `candidate-receipt.md`
- `review-receipt.md`
- `capacity-preflight.json`
- `activation-receipt.md`
- `new-release-receipt.md`
- `rewrite-release-receipt.md`
- `final-acceptance.md`

## Dispatch receipt

- dispatch_key: `v1:01bf8886a5dcd52ab5c06c926111bd5d5df65678b64144f4864aa1ab3310aad8`
- base_ref: `codex/normal-content-production-recovery-20260804-base`
- base_sha: `cd2a36fd214e624dffbf9855f4b4f0a6861a9570`
- capacity_precreate: `PASS / ALLOW_ONE_CREATE_REQUEST`
- create_attempt: `ONE_REQUEST / API_TIMEOUT`
- client_thread_id: `NONE`
- formal_thread_id: `NONE`
- worktree: `NOT_CREATED`
- reservation: `BLOCKED`
- blocker: `THREAD_CREATE_API_TIMEOUT_NO_ID`
- production_mutation: `NONE`

## Mainline recovery receipt（2026-08-04）

- Visible thread 建立逾時後，使用者明確要求「先復工」，主線依同一卡片契約採隔離 worktree fallback；未重試或冒充正式 thread。
- reviewed candidate：`efe69373e6326e7da07be85d1ca1ca5ceb5cbd20`，精確包含 Gemini HTTP 安全診斷與 Publisher 日期契約兩個修補；7 個 allowlist 檔，無 `uv.lock`、日韓 patch 或生成內容。
- verification：Provider affected suite `292 passed`；Publisher／web／SEO／multilingual／release gate `477 passed`；`py_compile`、`git diff --check` PASS；主線 Review `REVIEW_GO`，無 P0/P1。
- deployment：修補已快轉 `origin/main`；Publisher runtime pin 已更新。正常四服務載入，兩個 i18n runner 維持 unloaded。
- rewrite acceptance：`v0.3.288`／`c9b9dfcd9fae5ba2648dd9133afc28e2a8565609`，run `legacy-auto-sweep-v1-tarot-0079-tarot-pentacles-knight`；後續亦自動發布 `v0.3.289`、`v0.3.290`，復工後共 4 篇 rewrite。
- new acceptance：`v0.3.291`／`6f1d98b3dcce655709be6ac2f58477db113df3af`，run `auto-new-v1-20260804-002-01`，article `V2-MBTI-PAIR-INFJ-ESTJ-CONFLICT`，path `/articles/personality/personality-2177`。
- capacity：preflight 與多個 5 分鐘樣本皆 PASS；transaction 尖峰後可回收，最終樣本 `309,689,301 bytes / 32,146 files`，主機可用 `41,190,252,544 bytes`，無 reasons、無 stop-loss。
- final：`GO`；真實 release grid `new 1/1`、`rewrite 1/1`，i18n production `PAUSED / NOT_ACCEPTED_BY_THIS_CARD`。
