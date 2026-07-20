---
card_id: CARD-CONTENT-LIFECYCLE-CONTROL-001
status: CARD_DRAFTED
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 三條內容線共享文章 identity、狀態與整合邊界，若鎖與分流錯誤會造成跨 worktree 覆寫或錯誤部署，需 strict 跑道維護核心 invariant
ownership: 新文、舊文修復與 GSC 優化三線的 deterministic routing、文章鎖、狀態機與 plan-only 控制介面
allowlist:
  - docs/pantheon_content_lifecycle_workflow.md
  - scripts/pantheon_content_lifecycle.py
  - tests/test_pantheon_content_lifecycle.py
  - artifacts/fortune_council/content_lifecycle_execution/evidence/content_lifecycle_control_001/**
forbidden_scope:
  - app/**
  - 任何文章正文、metadata、registry、prerender、sitemap、feed、redirects
  - Gemini runner、GSC client 與既有文章 pipeline 的行為修改
  - push、deploy、publish、production、OAuth、token 與外部控制面
verification:
  - public CLI 行為測試
  - schema 與 forward-only state transition 測試
  - single-owner article lock 與跨線 collision 測試
  - 現有三線 artifact fixture 相容性
  - plan-only、fail-closed、git diff --check 與 allowlist
evidence_path: artifacts/fortune_council/content_lifecycle_execution/evidence/content_lifecycle_control_001/
worktree_path: pending_platform_provisioning
cwd: pending_platform_provisioning
main_cwd: <repo-root>
worktree_exists: false
source_branch: main
source_sha: a39e7296710904949c1405d1d12226dcea5d922f
source_clean: true
index_lock: absent
thread_id: pending
thread_status: CARD_DRAFTED
---

# CARD-CONTENT-LIFECYCLE-CONTROL-001｜三線內容生命週期總控

## 五行派工卡

任務 ID｜`CARD-CONTENT-LIFECYCLE-CONTROL-001`，建立新文、舊文修復、GSC 優化三線共用的 deterministic 控制層。
派工對象｜`gpt-5.6-sol`、`high`；本卡只實作路由、鎖、狀態與 plan-only CLI，不執行 Gemini、不產文、不部署。
任務目的｜確保同一文章同時間只有一個 owner，讓新文上線後進入觀測期，GSC 小修留在 GSC 線，正文或搜尋意圖問題明確轉交舊文修復線。
可改範圍｜只可新增一份流程文件、一個獨立 lifecycle 模組、一份 public-behavior 測試與本卡 evidence；既有 pipeline 與所有文章檔唯讀。
驗收證據｜schema、狀態轉移、三線分流、single-owner lock、跨線碰撞、GSC 升級為舊文修復、plan-only 無內容副作用、測試與 allowlist 證據。

## Root Question

Pantheon 如何把以下三條內容線接成單一可控生命週期，同時避免同篇文章被平行修改？

```text
新文產出 → 主線驗收／上線 → 觀測期 → GSC 數據優化
                                      └→ 若需正文大改，轉入舊文修復
舊文品質稽核 ─────────────────────────→ 舊文修復
```

## 三線責任

### `NEW_CONTENT`

- 輸入：去重後內容 backlog、使用者情境 brief、Gemini Writer／Reviewer candidate manifest。
- 責任：只建立 registry 中不存在的新文章候選。
- 完成：主線驗收與部署後進入 `OBSERVATION`，不得直接進 GSC 優化。

### `LEGACY_REPAIR`

- 輸入：舊文品質 audit、Gemini triage／rewrite manifest，或 GSC 線明確升級的正文問題。
- 責任：修復正文的模板腔、口語度、情境密度、搜尋意圖與可行下一步。
- 禁止：不得把單純 CTR／title 問題擴大成全文改寫。

### `GSC_OPTIMIZE`

- 輸入：真實 GSC read-only evidence 與現行文章 copy。
- 責任：只處理既有 pipeline 允許的 `title / description / answer` 小幅優化。
- 升級：若 findings 指向正文意圖不符、內容過薄或需改 `bodySections`，不得在 GSC 線修改；必須輸出 `LEGACY_REPAIR` handoff。

## 核心 Invariants

1. 同一 `article_identity` 同時間最多一個 active owner；identity 至少包含 `article_id + product + slug`。
2. 所有狀態轉移 forward-only；不得由完成狀態自行回退或跳過 human approval／mainline acceptance。
3. LLM、Gemini verdict 與自然語言完成訊息均屬 advisory；鎖、狀態、changed fields、SHA 與 route 由 deterministic code 驗證。
4. `NEW_CONTENT` 不得接管已存在 identity；`LEGACY_REPAIR` 不得新增 identity；`GSC_OPTIMIZE` 不得改正文。
5. 同篇文章若已有 active work item，第二條線必須 fail closed，輸出 collision evidence，不得覆寫 lock。
6. 新文上線後必須先進 `OBSERVATION`；未達 configured observation evidence 時不得自動進 GSC。
7. deploy、publish、Gemini、GSC API 與任何外部 write 均不屬於本控制層；CLI 預設且本卡只允許 `plan-only`。

## 狀態機

最小狀態集合：

```text
PROPOSED → ELIGIBLE → LOCKED → CANDIDATE_READY
→ READY_FOR_MAINLINE_REVIEW → ACCEPTED → INTEGRATED
→ READY_TO_DEPLOY → DEPLOYED → OBSERVATION → OPTIMIZATION_ELIGIBLE
```

允許的分支：

- 任一非終態在有證據時可進 `BLOCKED`；解除後回 `PROPOSED` 重跑完整驗證。
- `GSC_OPTIMIZE` 判定需正文修改時，原 work item 產生 `HANDOFF_REQUIRED`，釋放前不得建立 `LEGACY_REPAIR` active owner。
- 本卡不實作 deploy 或 production transition，只驗證外部 receipt 能否支持狀態計畫。

## Public Interface

新增 `scripts/pantheon_content_lifecycle.py`，提供至少以下 plan-only 行為：

```text
validate-item <work-item.json>
plan-route <work-item.json> [--active-locks <locks.json>]
plan-transition <work-item.json> --to <state>
reconcile --new <manifest> --legacy <manifest> --gsc <brief-or-manifest>
```

輸出必須是 stable JSON，至少包含：

- `schema_version`
- `article_identity`
- `requested_line`
- `effective_route`
- `current_state`
- `planned_state`
- `allowed_fields`
- `lock_owner`
- `decision_codes`
- `required_evidence`
- `mutation_executed: false`

錯誤 schema、未知 route/state、identity collision、非法 changed fields、缺 SHA／evidence 必須非零退出且 fail closed。

## 垂直切片與 Blocking Edges

1. Slice A（frontier）：鎖定 schema、三線欄位邊界、decision codes 與 public CLI contract；以失敗測試開始。
2. Slice B：實作 `validate-item + plan-route`，包含 single-owner collision 與 GSC→Legacy handoff；blocked by A。
3. Checkpoint 1：public behavior tests、stable JSON snapshot、plan-only 無文章副作用。
4. Slice C：實作 forward-only `plan-transition` 與 evidence requirements；blocked by B。
5. Slice D：實作 `reconcile` adapters，讀取既有新文 candidate manifest、舊文 audit／manifest、GSC brief fixture；只做 schema normalization，不改來源；blocked by C。
6. Checkpoint 2：三線 fixture、collision matrix、非法欄位、缺 evidence、`git diff --check` 與 allowlist。
7. Slice E：撰寫 lifecycle 文件、主線接線與兩張執行卡交付後的 adapter follow-up 清單；blocked by D。

## 必交付

- `docs/pantheon_content_lifecycle_workflow.md`：三線責任、狀態圖、路由表、鎖、主線收卡／部署邊界與 failure handling。
- `scripts/pantheon_content_lifecycle.py`：無外部服務副作用的 plan-only deterministic CLI。
- `tests/test_pantheon_content_lifecycle.py`：只測 public behavior，覆蓋三線 happy path、collision、GSC 大改升級、非法欄位、非法狀態、缺 evidence。
- `evidence/content_lifecycle_control_001/verification.txt`：可重現指令、測試、changed-file allowlist、`mutation_executed=false`。
- `evidence/content_lifecycle_control_001/fixture-matrix.json`：至少包含 NEW、LEGACY、GSC、GSC→LEGACY、跨線 collision 五種結果。
- `evidence/content_lifecycle_control_001/handoff.md`：兩張目前內容卡交付後需核對的實際 manifest 欄位與 adapter follow-up，不得假造尚未交付的格式。

## 禁止範圍

- 不修改 `app/**`、任何文章、registry、metadata、sitemap、feed、redirects 或部署設定。
- 不修改 Gemini outbox runner、GSC client、`agy_seo_copy_pipeline.py` 或其既有測試。
- 不呼叫 Gemini、不查 GSC、不建立 OAuth、不讀寫 token、不 push、不 deploy、不 publish。
- 不把尚未完成的兩張內容卡之預期輸出偽裝成已驗證實際格式；只可用明示 fixture，並在 handoff 列 follow-up。
- 不建立 daemon、hook、無上限 loop、自動 retry 或第二套 workflow engine；保持薄 router 與 deterministic gate。

## 驗收與交付

- 所有 CLI 子命令具 deterministic exit code 與 stable JSON；正常結果必須含 `mutation_executed=false`。
- 三條線的允許欄位、identity 存在性與 route 約束均有 public-behavior 測試。
- 同篇文章兩個 active owner 必須 fail closed；GSC 要求改正文必須轉為 `HANDOFF_REQUIRED`，不得核准正文修改。
- 非法狀態跳轉、缺 evidence、缺 SHA、manifest identity 重複均必須退件。
- 執行 `.venv/bin/python -m pytest tests/test_pantheon_content_lifecycle.py`、必要既有 focused tests 與 `git diff --check`。
- changed files 必須完全落在 allowlist；建立 candidate commit 並回報完整 SHA。
- 只能宣稱 `DELIVERED_CANDIDATE`，不得宣稱已接上尚未交付的兩張卡、已整合、已部署或已上線。
- 同一 blocker 失敗三次立即停止，不做第四次嘗試。

## Gate 狀態

- Gate 1：實體卡已建立，等待正式 thread 與獨立 worktree receipt。
- Gate 2–5：尚未開始，禁止預填通過。
