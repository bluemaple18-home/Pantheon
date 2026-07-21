---
card_id: CARD-CONTENT-GEMINI-REVIEWER-TRANSPORT-V2-IMPLEMENTATION-001
chain_id: CONTENT-GEMINI-REVIEWER-TRANSPORT-V2-001
status: CARD_DRAFTED
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 這是舊 Repair 額度用盡後的新架構鏈，涉及 Gemini CLI subprocess 邊界、per-item identity、不可變 receipt、partial failure 記帳與三條內容線恢復前的 machine gate
ownership: 實作 Gemini Reviewer Transport V2 的 per-item isolation、immutable invocation receipt 與 event-derived accounting，並以 bounded Gemini CLI corpus 驗證
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
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_transport_v2_implementation_001/**
forbidden_scope:
  - app/**
  - 正式文章、候選文章、registry、metadata、prerender、sitemap、feed、redirects
  - 舊 BLOCKED run、舊 receipt、舊 retry identity 或未核准 candidate 的重送與套用
  - tolerant JSON、regex 修補、括號補齊、任意 prose 移除或由 mapper 猜測模型遺漏欄位
  - Gemini CLI 安裝、登入、OAuth、token、MCP、全域設定或 model alias 修改
  - merge、push、deploy、publish、production
verification:
  - public red-green tests for per-item binding, stale receipt and partial-failure accounting
  - strict duplicate-key/schema/rubric tests
  - bounded sanitized Gemini CLI corpus with exact external-process receipts
  - focused and full affected pytest, py_compile, git diff --check and allowlist audit
  - privacy, secret, raw-output, absolute-path and debug-marker scan
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_transport_v2_implementation_001/
source_kind: commit
source_sha: be2309815bfcc658f8f82da9b038d95f8f6e99bf
source_branch: main
source_clean: true
main_cwd: <repo-root>
previous_blocked_chain: CONTENT-GEMINI-REVIEWER-MINIMAL-GATE-001
previous_blocked_candidate_sha: 5e9b1c898d943ae59f24f9f87206c3f60b0a0ceb
previous_final_review_sha: d7a14e66028d032354d7686f3dcd26f359ecf4bd
previous_open_findings:
  - stale transport fingerprint can cross invocation boundaries
  - globally allowed finding codes can be attached to the wrong article slot
thread_id: PENDING
thread_status: CARD_DRAFTED
worktree_path: PENDING
cwd: PENDING
---

# CARD-CONTENT-GEMINI-REVIEWER-TRANSPORT-V2-IMPLEMENTATION-001｜Reviewer Transport V2

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-REVIEWER-TRANSPORT-V2-IMPLEMENTATION-001`；這是從 main 開始的新 architecture／implementation chain，不是舊鏈 Repair 3。
派工對象｜`gpt-5.6-sol`、`high`；先建立 public RED，再做最小、可回退的 production transport 修改。
任務目的｜把 Reviewer 改為 per-item local identity binding，每次 Gemini CLI subprocess 直接回傳自己的 immutable receipt，並從 receipts 重建精確 external invocation／attempt／partial-failure 帳務。
可改範圍｜只限 pipeline、outbox、runner、transport probe、對應 tests/docs 與本卡 evidence；禁止文章與發布面。
驗收證據｜RED→GREEN、單篇 identity adversarial tests、success/error terminal receipts、partial failure replay、bounded Gemini CLI corpus、完整驗證與 candidate SHA。

## 固定背景與架構判定

- 舊 `CONTENT-GEMINI-REVIEWER-MINIMAL-GATE-001` 已在 Repair 2 後 `BLOCKED`；不得增加 Repair 3、不得修改或重送舊 candidate。
- 前一版已證明 Gemini CLI minimal Reviewer judgment 可在 sanitized APPROVE／REJECT corpus 達成 strict parse、schema 與 rubric；但 production candidate 仍有兩個未關閉 P2：跨 invocation stale fingerprint、跨 article slot finding 錯配。
- 本卡採用的 production 參考模式：
  - Temporal：logical invocation、attempt 與 execution identity 分層，但不引入 Temporal runtime。
  - Dagster：由 terminal events／receipts replay execution state，而非依賴 mutable last state，但不引入 Dagster。
  - LangGraph／DSPy：caller 以 canonical local item key fan-out／fan-in，模型輸出不得成為 identity truth source，但不引入其框架。
  - OpenAI Agents SDK／PydanticAI：request、response、usage／result 分離成每次 run 的物件，但本卡另補 CLI raw-byte fingerprint 與 exit metadata。
  - Gemini CLI JSON output 只視為 transport envelope；inner judgment 仍須本地 strict parse、schema 與 rubric。不得假設所有錯誤路徑都有完整 vendor JSON。
- 不新增大型 orchestration dependency；只吸收上述 object／event boundary。

## 必須先建立的 RED cases

1. `RED_STALE_RECEIPT`：第一次 invocation 成功，第二次在 outer envelope 或 inner judgment parse 前失敗；第二次不得取得第一次的 SHA／bytes。
2. `RED_CROSS_SLOT_GLOBAL_CODE`：A、B 同批，問題只存在 B；任何針對 A 的 judgment 都不能以 global code/message 描述 B 並被 A 接受。
3. `RED_TERMINAL_RECEIPT_COMPLETENESS`：success、nonzero exit、timeout、outer-envelope parse failure、inner strict parse failure 都各留下精確一個 terminal receipt。
4. `RED_PARTIAL_FAILURE_REPLAY`：第 k 篇失敗時，由 persisted receipts 重算的 invoked/succeeded/failed/pending 必須等於真正已啟動的外部 processes；不得等整批成功才累加。
5. `RED_DUPLICATE_KEY`：任一層重複 JSON key 必須 fail closed。

## V2 production contract

### 1. Per-item identity isolation

- orchestrator 為每篇建立 canonical `item_id`／`article_identity`，並在本地把 request、candidate SHA、attempt 與 invocation ID 綁定。
- 每個 Reviewer Gemini CLI invocation 只允許一個 target item。模型 judgment schema 不接受 article ID、slot 或任意 identity 欄位作為路由依據；fan-in 只用 caller 保存的 local binding。
- 若 Reviewer 需要 batch-level uniqueness context，只能傳 deterministic、sanitized、不可路由到其他 item 的摘要；跨篇 deterministic finding 由本地 gate 對實際 target 產生，不得要求模型替其他 slot 下 judgment。
- finding code allowlist 必須是該 target request 的完整 accepted-code contract。code/message 無法由本 target input 驗證時 fail closed。

### 2. Immutable invocation receipt

- 每次 subprocess 啟動前建立新的 invocation-local builder／context；禁止以 `last_transport_receipt` 或其他跨 invocation mutable singleton 作證據來源。
- invocation 完成時直接回傳 immutable terminal receipt；success 與 error 使用同一固定欄位集合，至少包含：schema version、invocation ID、item ID、attempt ID、request SHA、started/finished timestamp、exit status、stdout SHA、stdout byte length、sanitized error category、terminal status。
- 若尚未取得 stdout bytes，SHA／bytes 必須明確為 unavailable/null，不得沿用、猜測或由前一次補值。
- repo evidence 禁止保存 prompt、raw stdout、raw stderr、response content、秘密、PII 或本機絕對路徑。argv 只保存 allowlisted capability flags 或其 canonical hash，不保存 executable absolute path。
- terminal receipt 一旦產生不可原地改寫；後續 parse/schema/rubric 結果以同一 invocation ID 的 append-only operation event／derived record 表示。

### 3. Event-derived accounting

- `external_cli_process_invocations` 只由唯一 invocation-start／terminal receipts 計算；每個實際啟動 process 恰好一次。
- `attempt`、`transport retry`、`review round`、`writer invocation`、`reviewer invocation` 分欄，禁止混成一個 calls 數。
- partial failure、resume 與 reviewer-only round 必須由 receipts replay；成功 item 不重送，失敗 item 使用新的 invocation ID 與 attempt ID。
- `provider_model_calls` 固定為 `unobservable/unknown`，除非 Gemini CLI 提供可驗證 provider-level receipts；不得從 process 次數推論。
- 同一 blocker 第三次失敗立即停止，無 attempt 04；本卡不以 retry 作主要修復。

### 4. Strict judgment gate

- inner judgment 使用既有 minimal schema；strict parser 必須拒絕 trailing prose、markdown fence、duplicate keys、unknown fields 與不合法型別。
- deterministic rubric 強制 `APPROVE ⇔ hard_failure=false + findings=[]`；`REJECT ⇔ hard_failure=true + findings>=1`。
- finding code 與 trim 後 message 均須非空；unknown/duplicate code 與 contradictory verdict 一律 fail closed。
- mapper 只轉換已通過 strict parse/schema/rubric 的 judgment；不得修補、猜測或重寫模型輸出。

## Gemini CLI bounded verification

- 必須實際使用既有 Gemini CLI；不安裝、不登入、不修改設定。
- 先完成所有離線 RED→GREEN，再跑 sanitized public corpus。
- corpus 至少含一個合法 APPROVE 與一個合法 REJECT case；每 case 以 fresh process 跑 3 次，共精確 6 個 external CLI processes，無 transport retry、無第 7 次。
- 每次只保存 sanitized immutable receipt 與 typed gate 結果；`provider_model_calls=unobservable/unknown`。
- 任一 case 未達 3/3 exit、strict parse、schema、rubric 或 local identity invariant，立即 `BLOCKED`，不得擴大為正式文章 canary。

## 驗證與交付

- focused tests 必須涵蓋五組 RED cases、每種 terminal error path、multi-item partial failure、resume、reviewer-only rounds 與 closure accounting。
- 跑受影響完整 pytest、`py_compile`、stored corpus 離線重算、changed-file allowlist、privacy／secret／raw／path／`[DBG-]` scan、`git diff --check`。
- full suite 若有 baseline failure，必須固定 baseline SHA、證明與 diff 無關，不能宣稱全綠。
- evidence 至少包含 `root-cause.md`、`red-green.txt`、`receipts/`、`corpus.json`、`verification.txt`、`decision.md`。
- 建立單一 candidate commit，回完整 SHA；狀態只能 `DELIVERED_CANDIDATE`、`READY_FOR_REVIEW` 或 `BLOCKED`。
- 不得自行 merge、push、deploy、publish、恢復舊文修復／大量產文／GSC 三條線，亦不得自稱 production 已修復。

## Gate 1–5

- Gate 1：本實體卡已提交；thread 必須從本卡 commit 建立，且 parent 精確為 `be2309815bfcc658f8f82da9b038d95f8f6e99bf`。
- Gate 2：正式側邊欄 thread、獨立 clean worktree、cwd/path、rollout、registry 與卡片可讀皆驗證後才執行。
- Gate 3：執行線只交付固定 candidate commit 與 evidence，不宣稱接受或整合。
- Gate 4：candidate 交由新的獨立 Reviewer 固定 SHA 審查；implementation 不自審。
- Gate 5：主線重跑驗證並明確接受後才可整合；內容線恢復另開卡判定。
