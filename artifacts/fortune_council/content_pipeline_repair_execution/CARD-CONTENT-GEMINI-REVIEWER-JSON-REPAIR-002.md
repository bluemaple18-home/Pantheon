---
card_id: CARD-CONTENT-GEMINI-REVIEWER-JSON-REPAIR-002
chain_id: CONTENT-GEMINI-CONTRACT-REPAIR-001
status: BLOCKED_PROVISIONING_CONTROL_PLANE
repair_generation: 2
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: Reviewer strict JSON 失敗位於外部 CLI、sanitized failure receipt、重試 identity 與 candidate 不變性之間；涉及核心契約、外部呼叫與 fail-closed 邊界，回退成本高
ownership: Gemini Reviewer JSONDecodeError 的安全診斷、一次性 fresh transport retry、Reviewer-only resume 與 canary 驗證
allowlist:
  - scripts/agy_seo_copy_pipeline.py
  - scripts/agy_gemini_outbox.py
  - scripts/agy_gemini_runner.py
  - tests/test_agy_seo_copy_pipeline.py
  - tests/test_agy_gemini_outbox.py
  - docs/pantheon_gemini_outbox_runner.md
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_json_repair_002/**
forbidden_scope:
  - app/**
  - 正式文章、registry、metadata、prerender、sitemap、feed、redirects
  - 前一卡 canary 的 /tmp job、receipt、response 或 retry identity
  - 寬鬆 JSON 修復、code fence 擷取、raw invalid response、CLI stderr 或 prompt 內容落盤
  - deploy、publish、push、production、OAuth、token、Gemini CLI 安裝或全域設定
verification:
  - red-capable invalid Reviewer JSON tests
  - sanitized error fingerprint schema tests
  - Reviewer-only bounded retry and unchanged-candidate tests
  - strict fail-closed and second-failure stop tests
  - four-article fresh Gemini canary
  - focused/full pytest、git diff --check、allowlist、敏感字串與 debug marker
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_json_repair_002/
source_kind: commit
source_sha: fa64029acae36f6559b576112b8932238ff16dad
source_branch: codex/gemini-contract-repair-candidate
provisioning_source_branch: codex/gemini-reviewer-json-repair-source
provisioning_source_sha: 6707f072af2810b79b643e9c5a333216e1b23922
source_clean: true
main_cwd: <repo-root>
worktree_path: PENDING
cwd: PENDING
worktree_exists: false
index_lock: absent
unrelated_dirty_paths: []
thread_id: PENDING
thread_status: BLOCKED_PROVISIONING_CONTROL_PLANE
previous_card_id: CARD-CONTENT-GEMINI-CONTRACT-REPAIR-001
previous_thread_id: 019f7fb1-60b5-7183-bd55-99eaeb503107
previous_worktree_path: <codex-worktree>/e2d42265-1097-4341-b030-8eba32c67993/Pantheon
previous_candidate_sha: fa64029acae36f6559b576112b8932238ff16dad
---

# CARD-CONTENT-GEMINI-REVIEWER-JSON-REPAIR-002｜Reviewer strict JSON 最終修復

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-REVIEWER-JSON-REPAIR-002`，同一 chain 的第 2 次且最後一次 Repair。
派工對象｜`gpt-5.6-sol`、`high`；只修 Reviewer JSON transport seam 與安全診斷，不改文章生成策略。
任務目的｜在不放寬 strict JSON、不保存 invalid raw output 的前提下，定位 Reviewer `JSONDecodeError`，加入最多一次 fresh Reviewer-only retry，讓 Writer candidate 不被重跑或污染。
可改範圍｜三個 Gemini pipeline／runner、兩份 focused tests、一份 runner 文件與本卡 evidence；所有正式文章與共享發布檔唯讀。
驗收證據｜red-green、sanitized fingerprint、Reviewer-only retry invariant、第二次失敗停損、4/4 fresh canary、完整測試與 candidate commit。

## 固定輸入證據

- 基底 candidate：`fa64029acae36f6559b576112b8932238ff16dad`，不得從 main 或未提交 worktree 開始。
- 前一卡 canary：Tarot `run-02` Writer strict JSON 成功並 hydrate；fresh Gemini 3.1 Pro Low Reviewer request SHA `6ef45c19d11a9ac0124a99c1444d43ee1a6befe82393aa3b6c7461e25d54124b` 回 `JSONDecodeError`。
- 同一 CLI／Writer model 的最小與完整 sanitized Writer request 均曾成功，已排除 CLI 不存在、登入失效與 Writer schema 全面不相容。
- 前一卡 evidence 只讀；禁止搬運 `/tmp` response、重送原 job 或沿用原 retry identity。

## 可證偽假說

1. `H1_UNOBSERVABLE_PARSE_FAILURE`：runner 只存 `error_type`，使 CLI exit 0 後的 invalid JSON 無法區分截斷、Markdown 包裝或其他語法錯誤。若加入安全 fingerprint，fixture 應能保存 output SHA、UTF-8 byte length 與 JSON error position，但不得包含 raw output、prompt 或 stderr。
2. `H2_TRANSIENT_REVIEWER_OUTPUT`：Reviewer invalid JSON 是 fresh process 的暫時性 transport failure。若只對 Reviewer `JSONDecodeError` 建立一次全新 request identity，第二次可成功且 candidate SHA 完全不變、Writer call count 不增加。
3. `H3_RETRY_AMPLIFICATION`：無界重試會重現舊問題。若 retry budget 鎖為 1，第二個 Reviewer `JSONDecodeError` 必須 fail-closed `BLOCKED`，不得建立 retry-02、attempt-04 或第三張 Repair。

## Slice 與 blocking edges

### Slice A｜安全可重現訊號（frontier）

- 先寫 public/observable red test：CLI exit 0 但輸出不是合法 JSON。
- 定義 typed failure 與 sanitized fingerprint；只允許 `error_type`、固定 `error_code`、output SHA-256、UTF-8 byte length、JSON error line／column／position。
- 明確斷言 raw output、prompt、stderr、絕對路徑與秘密不會出現在 exception、failed receipt 或 evidence。
- blocking edge：Slice A 未綠前，不得實作 retry。

### Slice B｜一次性 Reviewer-only fresh retry

- 只攔截 Reviewer 的 typed JSON parse failure；Writer、HTTP、CLI nonzero、timeout、schema validation 與其他 error 不得進此 retry。
- retry 必須使用全新 opaque retry identity 與 request SHA、fresh headless process；candidate SHA 與 public candidate 必須不變，Writer 不得重跑。
- 同一 Reviewer 最多 1 次 transport retry；第二次 parse failure 立即 `BLOCKED`，保留兩份 SHA-bound receipts。
- checkpoint：focused tests 全綠、strict JSON 行為未放寬、無 attempt 04。

### Slice C｜四篇 fresh Gemini canary

- Tarot、Personality、Fortune、Astrology 各一篇，全新 run identity；不得沿用前一卡任何 job。
- 每次 Writer 精確一篇；Reviewer 使用 fresh Gemini 3.1 Pro Low process。
- 若第一次 Reviewer `JSONDecodeError`，只可走 Slice B 的一次 fresh retry；第二次即停止全部 canary並 `BLOCKED`。
- 成功標準：4/4 strict JSON、hydrate、Reviewer APPROVE、deterministic findings=0、`description_boundary=0`、candidate SHA 在 Reviewer retry 前後不變、Writer 無額外 call、無 attempt 04。

### Slice D｜證據與候選

- 交付 `root-cause.md`、`red-green.txt`、`failure-fingerprint.json`、`reviewer-retry-manifest.json`、`canary-manifest.json`、`verification.txt`。
- 更新 runner 文件，說明 typed failure、sanitized fingerprint、一次 Reviewer-only retry 與第二次停損。
- 跑 focused/full pytest、`git diff --check`、changed-file allowlist、secret/path/raw-output 掃描與 debug marker 清除。
- 建立完整 candidate commit；終態只能 `DELIVERED_CANDIDATE` 或 `BLOCKED`。

## 不變契約

- strict `json.loads` 與 response schema 不放寬，不猜測補 JSON，不剝 code fence，不保存 invalid raw response。
- 不重跑 Writer 來掩蓋 Reviewer transport failure。
- partial aggregate 只收 `APPROVED + findings=0`。
- runner／coordinator 不 approve、不 apply、不修改文章、不 commit、不 push、不部署。
- 本卡是 chain 的 Repair 2；若獨立 review 或 canary 仍 `NO-GO/BLOCKED`，回主線，不建立 Repair 3。

## Gate 1–5

- Gate 1：實體卡已在 main commit `09e101f` 建立；candidate-based provisioning source branch 為 `codex/gemini-reviewer-json-repair-source`，commit `6707f072af2810b79b643e9c5a333216e1b23922`，來源乾淨且卡片可讀。
- Gate 2：`list_projects` 控制面逾時；未呼叫 `create_thread`，沒有 `clientThreadId` 或正式 `thread_id`，因此標記 `BLOCKED_PROVISIONING_CONTROL_PLANE`。禁止宣稱已建立、排隊或執行中。
- Gate 3：需 completed turn、final output 與完整 candidate SHA。
- Gate 4：candidate 後由獨立 Reviewer thread 固定 reviewed commit 判定 GO／NO-GO。
- Gate 5：主線重跑驗證並核對 allowlist 後才可接受；未授權 merge、push、deploy 或 publish。
