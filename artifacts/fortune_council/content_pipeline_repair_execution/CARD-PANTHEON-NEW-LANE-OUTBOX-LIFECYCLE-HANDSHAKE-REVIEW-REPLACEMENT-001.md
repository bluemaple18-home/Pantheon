---
card_id: CARD-PANTHEON-NEW-LANE-OUTBOX-LIFECYCLE-HANDSHAKE-REVIEW-REPLACEMENT-001
status: STOPPED_DUPLICATE_REVIEW
type: independent-review-replacement
project: Pantheon
chain_id: PANTHEON-NEW-LANE-OUTBOX-LIFECYCLE-HANDSHAKE-20260728
owner: independent-review
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: allocator lifecycle、trusted provenance、outbox transaction 與 replay 邊界具有高回退成本，必須用 exact-lineage 的獨立 Review。
created_at: 2026-07-28 Asia/Taipei
candidate_sha: cea69cc97b59b1635f0e48a444c6d222efc24670
required_direct_parent: e42b3e5231cfe0cd41ee3dd5b113e5f07b1b2041
review_budget: 1
repair_budget: 0
previous_invalid_reviewer_thread: 019fa7ac-19cf-7900-b666-040a04f4096a
previous_invalid_reason: CROSS_THREAD_BINDING
---

# Pantheon New-Lane Outbox Lifecycle Handshake Review Replacement

## Stop record

- disposition：`STOPPED_DUPLICATE_REVIEW`
- reason：主線 lineage audit 確認既有 commit `c44953a7c3a68008a84eb8e7fb8fc88147a18fd2` 已是 candidate `cea69cc97b59b1635f0e48a444c6d222efc24670` 的有效唯一 Review。
- authoritative verdict：`NO_GO / STOP_NO_REPAIR_BUDGET`
- duplicate thread：`019fa85b-971c-7db3-b253-1586ef514d2f`
- duplicate thread result：`STOPPED_DUPLICATE_REVIEW / NO_COMMIT`
- duplicate worktree：只留下未提交的 replacement card／evidence；不得視為有效 Review，不得整合。
- replacement implementation：`CARD-PANTHEON-NEW-LANE-PRODUCTION-OWNED-PENDING-CAPABILITY-IMPLEMENTATION-001`

本卡是主線誤判造成的重複派工，未產生 commit，也未消耗新的合法 Review 額度。後續不得恢復本卡。

## Root question

候選提交是否真的讓一條 SEO copy New lane 經 production Python construction path，完整走通：

`PENDING registration → outbox → runner → TERMINAL → response acceptance → writer/reviewer`

同時維持 exact trusted allocator provenance、exact role model、無 legacy/direct-client bypass，且所有錯誤路徑 fail closed？

## Why this is a replacement

- Implementation thread：`019fa7c5-0983-7f31-b178-761a91d8f994`
- Implementation candidate：`cea69cc97b59b1635f0e48a444c6d222efc24670`
- required direct parent：`e42b3e5231cfe0cd41ee3dd5b113e5f07b1b2041`
- 原指定 Reviewer thread：`019fa7ac-19cf-7900-b666-040a04f4096a`
- 原 thread 在收到本 chain 的 Review prompt 後，仍回報舊候選 `b3accad…` 的舊結果，命中 `CROSS_THREAD_BINDING`。
- 原 thread 的 verdict 與 evidence 對本候選無效，不得繼承、引用為結論或計入有效 Review。
- 本卡是本 chain 唯一一次有效 Review；`review_budget=1`，`repair_budget=0`。

## Fixed lineage

Reviewer 開始前必須逐一證明：

1. `git rev-parse HEAD` 精確等於 `cea69cc97b59b1635f0e48a444c6d222efc24670`。
2. `git rev-parse HEAD^` 精確等於 `e42b3e5231cfe0cd41ee3dd5b113e5f07b1b2041`。
3. candidate 是 commit object，且 worktree clean。
4. candidate diff 恰為 15 個既定檔案；沒有 allowlist 外 production、test、shared integration 或 binary 變更。
5. 若任一 lineage 驗證失敗，立即 `NO_GO / STOP_NO_REPAIR_BUDGET`，不得換 SHA、不得自行修正候選。

## Candidate diff allowlist

- `artifacts/fortune_council/content_pipeline_repair_execution/CARD-PANTHEON-NEW-LANE-OUTBOX-LIFECYCLE-HANDSHAKE-IMPLEMENTATION-001.md`
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/pantheon_new_lane_outbox_lifecycle_handshake_implementation_001/**`
- `scripts/agy_gemini_allocator.py`
- `scripts/agy_gemini_coordinator.py`
- `scripts/agy_gemini_outbox.py`
- `scripts/agy_gemini_runner.py`
- `scripts/agy_seo_copy_pipeline.py`
- `tests/test_agy_gemini_allocator.py`
- `tests/test_agy_gemini_coordinator.py`
- `tests/test_agy_gemini_outbox.py`
- `tests/test_agy_seo_copy_pipeline.py`

## Review requirements

### 1. Findings-first code review

先輸出 findings，按嚴重度排序並附檔案／行號；至少檢查：

- authority 或 allocator identity 是否可被 caller 偽造。
- registration、outbox enqueue、runner start、terminal receipt 與 response acceptance 間的 TOCTOU。
- SQLite transaction、rollback、concurrency、idempotency 與 replay。
- receipt digest／request identity／operation identity 是否穩定且不可跨 request 重用。
- writer／reviewer 是否各自綁 exact role model。
- legacy、direct client、injected provider 或舊 construction path 是否能繞過 handshake。
- timeout、provider error、malformed response、receipt mismatch 等路徑是否留下錯誤 side effect。

### 2. Independent Stage A production-path probe

在 `<temp-root>` 建立獨立 disposable runtime，不讀、不改 live queue 或 credentials。必須使用 production Python construction path：

- `prepare_matrix_runs(limit=1)`
- production `run_pipeline_tick`／`cycle_once`／`process_once`
- 同一組 `TransportContext`／`SharedAllocator`
- synthetic structured executable；禁止真實 Gemini、HTTP 或 model call

必須證明：

1. 第一個 tick 只產生 `pending=1 / outbox=1 / provider=0 / candidate=0`。
2. writer runner 執行後恰有 `provider=1`，並留下 valid terminal receipt。
3. coordinator 只有在 exact terminal／receipt 驗證成功後才能 resume。
4. reviewer 使用 exact reviewer model，且 writer → reviewer 能得到一個合法 candidate／review outcome。
5. replay 同一 operation 不增加 provider call、registration、binding 或 terminal receipt。

### 3. Adversarial matrix

至少覆蓋：

- 缺 authority、缺 role 或錯 role。
- 同 operation identity 搭配不同 request。
- 另一個 allocator、verifier 或 transport context。
- forged／missing registration。
- forged response、missing terminal、corrupt terminal。
- cross-second terminal、cross-request receipt 或 replay。
- direct／injected provider 嘗試繞過 trusted construction path。

任何一項 fail open 都是 `NO_GO`。

### 4. Affected verification

- allocator、outbox、SEO pipeline、coordinator 的受影響 suites。
- 下列 production files 必須通過 `py_compile`：
  - `scripts/agy_gemini_allocator.py`
  - `scripts/agy_gemini_coordinator.py`
  - `scripts/agy_gemini_outbox.py`
  - `scripts/agy_gemini_runner.py`
  - `scripts/agy_seo_copy_pipeline.py`
- evidence JSON parse、privacy scan、debug print scan、candidate allowlist、`git diff --check`。
- 核對 implementation 報告的 targeted `13/13` 與 affected `263/263`；Reviewer 必須獨立重跑，不得只引用原報告。

### 5. Contract axes

逐項判定：

- lifecycle authority
- provenance integrity
- transaction atomicity
- idempotency／replay safety
- exact role-model binding
- fail-closed error handling
- legacy/direct-client bypass resistance
- bounded scope

任一 P1、P2、lifecycle fail-open 或 exact-lineage mismatch，結論只能是 `NO_GO / STOP_NO_REPAIR_BUDGET`。

## Reviewer write allowlist

只允許新增／修改：

- 本卡：
  `artifacts/fortune_council/content_pipeline_repair_execution/CARD-PANTHEON-NEW-LANE-OUTBOX-LIFECYCLE-HANDSHAKE-REVIEW-REPLACEMENT-001.md`
- Review evidence：
  `artifacts/fortune_council/content_pipeline_repair_execution/evidence/pantheon_new_lane_outbox_lifecycle_handshake_review_replacement_001/**`
- `<temp-root>` 下的 disposable harness 與 runtime。

禁止修改 candidate 的 production code、tests、implementation card 或 implementation evidence。

## Forbidden scope

- 不修 code、不做 Repair、不開第二次 Review。
- 不重構 allocator、outbox、coordinator、runner 或四條 lane。
- 不接觸 live `.work`、credentials、Gemini key、真實 HTTP 或真實 model。
- 不 push、merge、deploy、publish 或修改 shared integration files。
- 不使用 sub-agent 或其他隱藏工作單元代替本 Reviewer。
- 不把舊 Reviewer thread 的 verdict 當本卡證據。
- 不修改 candidate SHA 或 direct parent。

## Evidence and delivery

Evidence root：

`artifacts/fortune_council/content_pipeline_repair_execution/evidence/pantheon_new_lane_outbox_lifecycle_handshake_review_replacement_001/`

至少交付：

- `review.md`：findings-first review、行號、contract axes、最終 verdict。
- `stage_a.md`：production-path probe 與 adversarial matrix。
- `results.json`：machine-readable lineage、counts、tests、verdict。
- `verification.txt`：完整可重現命令與摘要。

只允許一個 Review evidence commit：

- direct parent 必須是 candidate `cea69cc97b59b1635f0e48a444c6d222efc24670`
- commit 只能包含本卡與 Review evidence
- 交付時 worktree 必須 clean
- 回報完整 40 字元 evidence commit SHA

## Verdict contract

只能回傳其中之一：

- `GO / READY_FOR_BOUNDED_REAL_CANARY`
- `NO_GO / STOP_NO_REPAIR_BUDGET`

不得回傳 conditional GO、READY_FOR_REPAIR、部分通過或要求主線自行補證據。若為 `NO_GO`，列出精確 blocker 後停止；本 chain 沒有 Repair 額度。

## Stop conditions

- 同一 blocker 累計失敗 3 次，第 3 次立即停止，不做第 4 次。
- lineage、allowlist 或 independent worktree 任一不成立，立即停止。
- 需要修改 production／tests、接觸 live state、真實 provider 或擴大 scope 時停止。
- 任一 adversarial case fail open，保存證據後 `NO_GO`。

## Dispatch receipt

- provisioning source SHA：`2f804d185f384a1a168407a1eb0c56320814eff7`
- source branch/ref：`codex/review-new-lane-outbox-handshake-20260728`
- source clean：PASS
- Git metadata／index lock：PASS（無 index lock）
- unrelated dirty paths：NONE（派工來源 worktree clean）
- formal thread ID：`019fa85b-971c-7db3-b253-1586ef514d2f`
- title：`CARD-PANTHEON-NEW-LANE-OUTBOX-LIFECYCLE-HANDSHAKE-REVIEW-REPLACEMENT-001`
- worktree cwd／exists／clean：PASS（registered independent worktree `1608a4ae-e45d-46ba-adb4-c27ecab98967`，與 `<main-cwd>` 不同）
- model：`gpt-5.6-sol`
- reasoning：`high`
- previous invalid Reviewer：`019fa7ac-19cf-7900-b666-040a04f4096a / CROSS_THREAD_BINDING`
- Gate 1 card contract：PASS
- Gate 2 visible thread：PASS
- Gate 3 candidate delivery：`cea69cc97b59b1635f0e48a444c6d222efc24670 / READY_FOR_REVIEW`
- Gate 4 independent review：N/A（本卡為重複派工；有效 Review 為 `c44953a7…`）
- Gate 5 mainline acceptance：PENDING
- workflow：`STOPPED_DUPLICATE_REVIEW / NO_COMMIT`
