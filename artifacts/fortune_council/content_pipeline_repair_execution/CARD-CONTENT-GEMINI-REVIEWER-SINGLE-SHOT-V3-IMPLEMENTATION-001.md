---
card_id: CARD-CONTENT-GEMINI-REVIEWER-SINGLE-SHOT-V3-IMPLEMENTATION-001
chain_id: CONTENT-GEMINI-REVIEWER-SINGLE-SHOT-V3-001
status: CARD_DRAFTED
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 前兩條 repair chain 均因 persisted multi-retry trust boundary 失敗；本卡移除 transport retry 能力並重建單次 invocation 與上層 resume 邊界，涉及 production transport 核心契約
ownership: 從 main 實作 Gemini Reviewer Single-Shot V3；每 operation 恰好零或一次 CLI process，失敗後只能由新 operation identity 恢復
allowlist:
  - scripts/agy_seo_copy_pipeline.py
  - scripts/agy_gemini_outbox.py
  - scripts/agy_gemini_runner.py
  - scripts/agy_gemini_transport_probe.py
  - tests/test_agy_seo_copy_pipeline.py
  - tests/test_agy_gemini_outbox.py
  - tests/test_agy_gemini_transport_probe.py
  - docs/pantheon_gemini_outbox_runner.md
  - docs/pantheon_gemini_reviewer_transport_strategy.md
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_single_shot_v3_implementation_001/**
forbidden_scope:
  - app/**, articles, candidate articles, registry, metadata and publishing files
  - cherry-picking or continuing blocked V2 candidates as the implementation base
  - runtime retry files, automatic transport retry or attempt-chain replay
  - tolerant JSON, semantic guessing or ungrounded model finding as machine truth
  - Gemini installation, login, OAuth, token, MCP or global configuration change
  - merge, push, deploy, publish, production or content-line recovery
verification:
  - single-shot public RED/GREEN and V2 final blocker regression
  - per-item new-operation resume and immutable evidence replay
  - bounded sanitized Gemini CLI corpus
  - focused/full tests, py_compile, allowlist, privacy and git diff checks
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_single_shot_v3_implementation_001/
source_kind: commit
source_sha: c675910b8378ef2136481dde000c1972d6a5f850
source_branch: main
source_clean: true
previous_blocked_chain: CONTENT-GEMINI-REVIEWER-TRANSPORT-V2-001
previous_final_candidate_sha: fe62f1679bf248b0c55a6cea566315dca15a2e07
previous_final_review_sha: 11f26dbae6539fbff73038fb94dd9c622b67aae7
thread_id: PENDING
thread_status: CARD_DRAFTED
worktree_path: PENDING
cwd: PENDING
---

# CARD-CONTENT-GEMINI-REVIEWER-SINGLE-SHOT-V3-IMPLEMENTATION-001｜移除 transport retry

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-REVIEWER-SINGLE-SHOT-V3-IMPLEMENTATION-001`；新的 V3 architecture chain，不是 V2 Repair 3。
派工對象｜`gpt-5.6-sol`、`high`；從 clean main 重建最小 production transport。
任務目的｜每個 Reviewer operation 最多啟動一次 Gemini CLI；任何失敗保留 immutable evidence 並結束，resume 只能建立全新 operation/run identity。
可改範圍｜pipeline/outbox/runner/probe、tests/docs 與 V3 evidence；禁止文章與發布面。
驗收證據｜single-shot invariant、V2 multi-retry 反例結構性不可達、new-operation resume、bounded Gemini corpus 與獨立 Review candidate。

## Mainline fork

- Root question：建立可安全支撐新文、舊文與 GSC 三條內容線的 Gemini Reviewer transport。
- V2 blocker：attempt-03 可跳過最新 runtime-retry pair，在 evidence integrity failure 被 replay 發現前先啟動新 process。
- V3 fork：刪除 transport 層的 persisted retry chain 與自動 retry capability；不是繼續驗更長 retry chain。
- 固定 base 是 clean main `c675910b8378ef2136481dde000c1972d6a5f850`。V2 candidates 只可 `git show` 研究；不得 cherry-pick整包、不得沿用V2 worktree/run/receipt。

## V3 invariants

### 1. One operation, zero-or-one process

- 每個 `review_operation_id` 在建立時綁定唯一 item/request/candidate/run identity。
- operation 狀態只能 `CREATED -> PROCESS_NOT_STARTED | PROCESS_TERMINAL -> GATE_TERMINAL`；不得回到前態。
- 每個 operation 最多一個 subprocess start。程式內不得存在 `runtime-retry-*`、retry index、next retry filename、automatic retry loop或對同operation第二次client call。
- CLI missing／preflight failure為零process；success/nonzero/timeout為一process。logical operations與external processes分帳。

### 2. Failure ends the operation

- nonzero、timeout、outer envelope、inner strict parse、schema、rubric、identity或local witness failure都寫入該operation的immutable terminal/gate evidence，狀態 `BLOCKED`，函式結束。
- 失敗不得在同一command／operation內重送Gemini、不得配置attempt-02、不得重跑Writer、不得改candidate SHA。
- 同一operation再次執行必須fail closed為duplicate operation；不得覆寫或補寫舊records。

### 3. Resume is a new operation

- 上層resume只挑選BLOCKED/PENDING item，建立新的run ID、operation ID與request identity；已APPROVED item不重送。
- 新operation可保存 `parent_operation_id` 與前次failure code作audit link，但不得把前次terminal/gate當作本次retry authorization，也不得共用檔名、mutable state或attempt chain。
- 每個新operation仍是single-shot。跨operation replay只做歷史與狀態選擇，不授權同operation重試。
- 同一 blocker 累計第三個獨立operation失敗後停止；沒有第四次。這是上層policy，不是transport retry loop。

### 4. Minimal immutable evidence

- operation manifest在process前以exclusive create保存caller-owned binding；terminal與gate各恰好一份，皆以operation ID命名並exclusive create。
- 每份record strict schema；unknown/missing field、wrong type/status/event、binding mismatch、duplicate/missing record一律fail closed。
- ordering由record內不可變sequence與parent hash鏈或等價content-bound欄位驗證；不得以mutable mtime作唯一authority。
- stdout SHA/bytes只屬該operation；未啟動/未取得為null。禁止保存prompt、raw stdout/stderr、response content、secret、PII、本機絕對路徑、executable path或argv text。

### 5. Reviewer judgment boundary

- per-item caller-local identity；模型輸出永遠不負責routing。
- deterministic/cross-item/comparative codes只由local gates產生，不得出現在model machine-gate allowlist。
- model code只有存在code-specific local validator時才可影響machine verdict；無可證明validator的Gemini finding只能advisory。
- strict JSON拒絕duplicate keys、unknown fields、trailing prose、markdown fence與矛盾cross-fields；mapper不得修補或猜測。

## 必須先有的 public RED

1. V2 final blocker fixture：合法operation A後放入錯綁的另一operation evidence；任何single-shot call都不得掃描它、不得啟動第二process、不得產生retry receipt。
2. duplicate invocation：同operation ID第二次呼叫，client calls維持0新增，existing evidence byte-for-byte不變。
3. failed gate：exit-zero但schema/rubric failure，該operation結束BLOCKED；同command無第二call。
4. new-operation resume：新ID只重送失敗item，成功item不重送；parent link可驗但不作authorization。
5. three-operation stop：同blocker連續三個獨立operation失敗後停止，無第四個operation/process。
6. accounting：CLI_NOT_FOUND=1 logical/0 external；success/nonzero/timeout=1 logical/1 external；partial batch與closure按records精確重算。

## Gemini CLI bounded verification

- 離線RED→GREEN後，使用既有Gemini CLI跑sanitized APPROVE與REJECT各3個fresh single-shot operations，共精確6 external processes。
- 無transport retry、無第7次；每operation三份immutable records（manifest/terminal/gate）可離線strict replay。
- APPROVE/REJECT各3/3 exit、strict parse、schema、rubric、binding；`provider_model_calls=unobservable/unknown`。
- 任一3/3失敗立即BLOCKED，不擴成正式文章canary；不安裝、不登入、不改設定。

## 驗證與交付

- 搜尋production code與tests，證明沒有runtime retry filename/index/loop或同operation第二次client call；不能只讓測試碰不到。
- 跑focused affected tests、V2 final adversarial fixture、stored replay/tamper matrix、py_compile、allowlist、privacy/secret/raw/path/`[DBG-]` scan、`git diff --check`。
- full suite必跑；Ziwei baseline failure如實分列，不改無關路徑。
- evidence至少：`root-cause.md`、`red-green.txt`、`architecture.md`、`corpus.json`、`records/`、`verification.txt`、`decision.md`。
- 建立單一candidate commit，回完整SHA；只能 `READY_FOR_REVIEW` 或 `BLOCKED`。
- candidate完成後由主線開新的獨立Reviewer；不得自行GO、merge、push、deploy、publish或恢復內容線。

## Gate 1–5

- Gate 1：實體卡已提交，thread從卡片commit建立且parent精確為`c675910b8378ef2136481dde000c1972d6a5f850`。
- Gate 2：正式thread、獨立clean worktree、rollout/registry/title/preview與卡片可讀都成立。
- Gate 3：只交付candidate/evidence，不宣稱production fixed。
- Gate 4：新的獨立Reviewer固定candidate SHA審查single-shot與resume邊界。
- Gate 5：主線重跑並接受後才可整合；恢復三條內容線另開canary/recovery卡。
