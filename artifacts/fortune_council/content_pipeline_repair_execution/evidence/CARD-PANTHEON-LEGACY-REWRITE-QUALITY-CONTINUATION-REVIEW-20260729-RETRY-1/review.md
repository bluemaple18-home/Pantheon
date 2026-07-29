# Pantheon Legacy Rewrite Quality Continuation Independent Review Retry-1

## Verdict

- status: `REVIEW_GO`
- card_id: `CARD-PANTHEON-LEGACY-REWRITE-QUALITY-CONTINUATION-REVIEW-20260729-RETRY-1`
- chain_id: `PANTHEON-LEGACY-REWRITE-QUALITY-CONTINUATION-REPAIR-20260729`
- reviewer_thread_id: `019fae60-82c5-74c3-8033-03202772980a`
- reviewed_candidate: `8faba380eecfd24ae661074e7296499a3761dd01`
- required_direct_parent: `87799903e18bdfb1f2432456beb2a6fcc21597e3`
- verdict_basis: 未發現 P0／P1 finding；candidate 符合 root question 與 locked repair budget。

## Scope and provenance

- Candidate direct parent 經 fresh `git rev-parse <candidate>^` 驗證為 required parent。
- Candidate branch ref 經 fresh `git rev-parse codex/legacy-rewrite-quality-continuation-repair-20260729` 驗證為 reviewed candidate。
- Candidate diff 僅包含：
  - `scripts/agy_seo_copy_pipeline.py`
  - `tests/test_agy_seo_copy_pipeline.py`
- Diff 統計：2 files changed，346 insertions，21 deletions。
- Review 前 worktree 為 clean detached HEAD，精確位於 reviewed candidate。
- CodeGraph preflight 已執行，但本 worktree 未初始化 CodeGraph；依專案規則降級為限域 `git diff`、`rg` 與 source seam 審查，未初始化或修改索引。

## Fresh verification

### Contract command capability

Reviewer worktree 不含 `.venv/bin/python`，因此以下兩條原始命令在 pytest 啟動前即以 exit 127 結束：

- `.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py -q`
- `.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py tests/test_agy_content_publisher.py -q`

主線其後明確提供 implementation worktree 的既有 `.venv/bin/python` 作為唯讀 runtime。Fresh `git rev-parse HEAD` 證實該 implementation worktree 同樣位於 `8faba380eecfd24ae661074e7296499a3761dd01`；所有測試 cwd 仍保持 reviewer worktree，且未在 reviewer worktree 建立或修改 `.venv`。

### Executed results

| Command | Result |
|---|---|
| `<implementation-worktree>/.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py -q` | PASS：104 passed in 54.13s |
| `<implementation-worktree>/.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py tests/test_agy_content_publisher.py -q` | PASS：99 passed，1 non-blocking `SyntaxWarning` in 15.75s |
| `git diff 87799903e18bdfb1f2432456beb2a6fcc21597e3..8faba380eecfd24ae661074e7296499a3761dd01 --check` | PASS：exit 0，無輸出 |

### Supplemental in-memory runtime seam

使用同一 candidate runtime、repo source 與測試 helper，在 temporary directory 執行 `run_writer_reviewer()`；未修改 repo tests。

| Scenario | Calls | Result |
|---|---|---|
| `max_repairs=0`、初稿 machine REJECT | `writer` | 1 attempt、0 content repair、0 Reviewer、final REJECT |
| `max_repairs=1`、machine REJECT 後 Writer 修綠 | `writer → writer → reviewer` | 2 attempts、1 content repair、final APPROVE |
| `max_repairs=2`、Reviewer 連續兩次 semantic REJECT | `writer → reviewer → writer → reviewer → writer → reviewer` | 3 attempts、2 content repairs、final APPROVE |
| invalid Reviewer payload、`max_repairs=2` | `writer → reviewer` | 1 attempt、0 content repair、hard REJECT |

Supplemental seam 的 corrected invocation exit 0；第一次組裝 `python -c` 命令時因 shell quoting 令換行成為 literal `\n`，在載入專案程式前即 `SyntaxError`，修正 invocation 後上述 assertions 全數通過。

## Finding matrix

| Severity | Count | Disposition |
|---|---:|---|
| P0 | 0 | 無 |
| P1 | 0 | 無 |
| P2 | 0 | 無 |
| P3 | 0 | 無 |

未發現阻塞問題。

## Required-risk review

| Risk | Evidence and decision |
|---|---|
| 1. `max_repairs=0/1/2` 精確 bounded | `run_writer_reviewer()` 在下一次 Writer 前檢查 `content_repairs_used >= max_repairs`；fresh supplemental seam 分別證實 0／1／2 次 repair，沒有多跑 Writer 或 Reviewer。`run_rewrite_repair()` 仍強制 `max_repairs == 1`。 |
| 2. machine REJECT authority 與 binding | machine review 只由 `rewrite_quality_findings()`／`rewrite_aggregate_findings()` 結果建立；每筆 review 使用當次 `_candidate_id(article)` 與 `article_sha256(article)`，finding 依 deterministic `article_id` 分組，未接受 Reviewer 偽造 machine code。 |
| 3. Reviewer ordering 與 semantic authority | `scripts/agy_seo_copy_pipeline.py:3471` 與 `scripts/agy_seo_copy_pipeline.py:3713` 僅在 deterministic findings 為空時呼叫 Reviewer。Fresh tests 證實 machine fail 先進 Writer、machine clean 後 Reviewer 必跑；既有隔離 runner test與 supplemental `max_repairs=2` seam 證實 semantic REJECT 在剩餘 budget 內仍回 Writer。 |
| 4. invalid Reviewer、schema repair、cached receipt | invalid Reviewer 由 `hydrate_review()` strict validation 轉成 `invalid_review_payload()` hard REJECT；supplemental seam 證實不消耗額外 content repair。Writer schema repair 維持獨立 `MAX_WRITER_SCHEMA_REPAIRS` 計數，完整 suite 的既有 schema-budget test 通過。`_generate_with_receipt()` 對既有 non-error receipt 拒絕重放、只允許 error receipt 使用新 retry receipt；隔離 runner 的 cached external payload 仍重新 hydrate／validate，無法繞過 fail-closed review。 |
| 5. `run_writer_reviewer()`／`run_rewrite_repair()` 漂移 | 兩條 runner 現在都採 machine-first、Reviewer-after-green ordering；一般 runner 保留 caller 指定 0／1／2 budget，隔離 runner保留 locked one-repair contract。兩者的不同 writer isolation／receipt policy 為既有契約差異，不是本次新漂移。 |
| 6. `duplicate_paragraph` 誤判 | Gate 只比對同篇 raw paragraph 的逐字完整相等，不做相似度或正規化擴張。空字串與短 boilerplate 同時必然命中既有 `paragraph_length` hard gate，不會把原本可接受內容變成錯誤拒絕；合法引用只有在整段逐字重複時才會被拒絕，符合 locked「不得逐字重複完整段落」契約。 |
| 7. prompt scope | `_rewrite_generation_instruction()` 只由 rewrite initial／rewrite repair branches 與隔離 rewrite Writer prompt 呼叫；create 原有 presentation instruction 未被替換，optimize repair instruction 未新增 rewrite contract。 |
| 8. diff contamination | `git diff --name-status` 僅有 source contract 指定的兩檔，無 config、文章、queue、ledger、runtime 或其他卡片變更。 |

## Spec axis

1. rewrite machine failure 先進 bounded Writer repair，machine clean 後才呼叫 Reviewer：PASS。
2. rewrite 初稿與 repair prompt 均明列可信 presentation contract：PASS。
3. 同篇逐字重複完整段落由 deterministic gate 穩定拒絕並回報首個位置：PASS。
4. create、rewrite 與既有隔離 rewrite runner 無測得回歸：PASS。

## Standards axis

- Correctness：PASS；ordering、hash binding、budget 與 fail-closed path 有 source 與 fresh runtime evidence。
- Regression：PASS；指定 pipeline suite 與 coordinator／publisher suites 全數通過。
- Security／privacy：PASS；diff 未擴張外部 provider、secret、path 或 apply authority。
- Testing：PASS；新增測試命中 prompt、machine ordering、duplicate location 與隔離 runner；補充 seam驗證 0／1／2 budget 與 invalid Reviewer。
- Maintainability：PASS；共用 `_rewrite_generation_instruction()` 避免三處 rewrite prompt contract 漂移。

## Remaining risk

- CodeGraph 在 reviewer worktree 未初始化，因此本次 symbol relationship 以限域 source inspection 取代；fresh tests 與 diff boundary 已補足行為證據。
- Exact duplicate gate 會刻意拒絕同篇重複的完整引文段落；這符合目前 locked contract，但 production acceptance 應觀察是否有真實合法引用需要未來另立、不可偽造的 quote-block 契約。
- 本 Review 未執行真實 provider 或 production publish；依卡片契約，此缺口不構成 code-review NO-GO。

## Acceptance required before production

1. 以 production-owned runtime 執行至少一個 rewrite acceptance batch，保存每次 attempt 的 Writer／Reviewer operation receipt。
2. 證實 machine REJECT attempt 沒有 Reviewer process，後續 machine-green attempt 才有 Reviewer process。
3. 核對 `run-evidence.json` 的 attempts、repair count、Reviewer process count、candidate hash 與逐篇 article hash。
4. 對真實候選內容人工抽查 presentation contract、Reviewer semantic quality 與 duplicate false-positive；未通過不得 apply 或 publish。

## Stop boundary

本 evidence 僅裁定 reviewed candidate 為 `REVIEW_GO`。Reviewer 未整合、未 push、未 deploy、未 publish、未接觸真實 provider，亦未修改 production code、tests、config、文章、queue、ledger 或 live runtime。
