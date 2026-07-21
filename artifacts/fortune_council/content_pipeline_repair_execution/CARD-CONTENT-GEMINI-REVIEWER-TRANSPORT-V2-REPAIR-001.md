---
card_id: CARD-CONTENT-GEMINI-REVIEWER-TRANSPORT-V2-REPAIR-001
chain_id: CONTENT-GEMINI-REVIEWER-TRANSPORT-V2-001
status: CARD_DRAFTED
repair_generation: 1
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 三個 P1 與一個 P2 橫跨 retry eligibility、persisted replay trust boundary、production accounting 與 target-local semantic binding，屬核心 transport 修復
ownership: 只修 Transport V2 Review 001 的四個固定 findings，交付 Repair 1 candidate
base_candidate_sha: 96d3a3a17b3e97f2f5e099f1c739ad6c84e7bc0c
review_evidence_sha: d8b6a235bd19d8aae72d40565841f09d35b3f83d
reviewer_thread_id: 019f83d4-de93-79c0-ba8a-674565e107e8
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
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_transport_v2_repair_001/**
forbidden_scope:
  - implementation or Review evidence modification
  - app/**, articles, registry, metadata and publishing files
  - unrelated refactor or new feature
  - tolerant JSON or semantic guessing from free-form text
  - Gemini installation, login, OAuth, token, MCP or global configuration change
  - merge, push, deploy, publish, production or content-line recovery
verification:
  - reviewer adversarial probes RED then GREEN
  - focused regression and full affected tests
  - stored corpus offline replay and conditional bounded Gemini CLI corpus
  - py_compile, allowlist, privacy scan and git diff --check
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_transport_v2_repair_001/
thread_id: PENDING
thread_status: CARD_DRAFTED
worktree_path: PENDING
cwd: PENDING
---

# CARD-CONTENT-GEMINI-REVIEWER-TRANSPORT-V2-REPAIR-001｜固定四項 finding 修復

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-REVIEWER-TRANSPORT-V2-REPAIR-001`；Repair generation 1。
派工對象｜`gpt-5.6-sol`、`high`；只修固定 3×P1、1×P2。
任務目的｜讓 strict failure 可安全 resume、persisted replay fail closed、production accounting 全由 receipts 推導，並把 model finding 綁到 target-local evidence。
可改範圍｜固定 production transport、tests/docs 與 Repair evidence；禁止文章與發布面。
驗收證據｜Reviewer adversarial RED→GREEN、focused/full affected tests、stored corpus、privacy/allowlist 與 candidate SHA。

## 啟動 Gate

- 新的獨立 clean worktree；HEAD 必須是只含本 Repair 卡的 provisioning commit，並能追溯 fixed candidate `96d3a3a17b3e97f2f5e099f1c739ad6c84e7bc0c` 與 Review evidence `d8b6a235bd19d8aae72d40565841f09d35b3f83d`。
- 完整讀取 Review `review.md`、`verification.txt`、`adversarial_probes.py`；先實際跑出四個 finding 的 RED，不得只相信文字報告。
- 任一 finding 無法重現時先補最小 public red-capable test或回 `BLOCKED`，不得猜修。

## 固定 Findings 與修復契約

### P1-01｜strict gate failure 無法 resume

- retry eligibility 必須由同 invocation 的 terminal receipt 加 strict gate event 聯合決定，不能只看 `process_succeeded`。
- exit-zero 但 parse/schema/rubric/identity gate 失敗必須視為該 review attempt 未通過，可用全新 invocation ID／attempt ID resume。
- 舊 terminal/gate pair 保持 immutable；不得覆寫或重用檔名。成功 identity 不重送，Writer 不重跑。
- 補 outer failure、inner strict parse、schema、rubric、duplicate/unknown code、blank message與cross-field contradiction後resume測試。

### P1-02｜persisted replay 接受偽造／矛盾 records

- 為 terminal receipt 與 gate event 建立 strict local schemas與allowed states；unknown field/status/event type fail closed。
- caller 必須提供 expected item/request/candidate/attempt binding；replay逐欄比對，不接受record自我聲明作 truth source。
- 每個 invocation 必須恰好一個 terminal與一個 gate；duplicate/missing pair、gate-before-terminal、同invocation不同binding、未知status、非法transition全部拒絕。
- persisted files 使用 exclusive create或等價不可覆寫機制；不得靜默 normalize、去重或取最後一筆。
- stored corpus verifier必須驗證相同schema、binding、multiplicity與ordering；tampered request/candidate/item/attempt/status/event type 一律 `BLOCKED_CORPUS`。

### P1-03｜production process accounting 少算

- 所有對外 `reviewer_processes`／`external_cli_process_invocations` 只能從已通過 strict receipt replay 的 terminal records 推導，不得在整批return後用控制流加總。
- 即使第 k 篇拋錯，已啟動的 k 個process仍精確記入final run evidence；first/middle/last failure都需測。
- closure N篇必須記N個Reviewer processes，不得固定1；review rounds、attempts、transport retries、Writer/Reviewer invocations分欄。
- exception path也必須先保存可驗證 accounting evidence，再fail closed；不得為了記帳吞掉原錯誤。

### P2-01｜global code／free-form message 可跨 slot

- 不得用 literal item ID blacklist或對message做語意猜測。
- deterministic-only codes不得由模型輸出；只由本地deterministic gate對實際target產生。
- 每個model-eligible finding必須帶 target-local machine-verifiable witness。預設為非空 `evidence_quote`，其normalized exact span必須存在於當次target candidate；若某code不適合quote，必須有該code專屬 deterministic predicate，否則該code不得進accepted allowlist。
- accepted codes由當次target request契約生成；unknown/duplicate/global-unbound code、空白witness、只存在其他item的quote、swapped candidate SHA全部fail closed。
- prompt/schema/docs/mapper/tests需同步；witness只用於grounding，不得作identity routing，不得保存超出既有sanitized evidence邊界的全文。

## TDD 與假說順序

1. 若 resume blocker是只看terminal status，改成terminal+gate pair後 exit-zero/gate-failed identity應能fresh resume且成功identity不重送。
2. 若 replay blocker是信任record自述與寬鬆聚合，加入caller expected binding、strict schemas、pair/order/multiplicity驗證後所有tamper probes應fail closed。
3. 若少算來自control-flow counters，改由validated terminal receipts重算後partial failure與closure N篇應精確。
4. 若cross-slot來自global ungrounded finding，加入target-local witness／predicate後B-only prose與swapped SHA不得附到A，A的真實quote finding仍可通過。
- 一個RED對一個最小修復；不可同時大改後才回頭補測試。
- 若需要debug instrumentation，使用唯一 `[DBG-...]` 前綴並在交付前完全移除。

## Gemini CLI 與驗證上限

- 先完成全部離線 RED→GREEN與stored corpus tamper matrix。
- 若 prompt/schema/model-output contract 未改，禁止額外 Gemini CLI 呼叫，只離線重算既有6-process corpus。
- 若因 `evidence_quote` 必須修改模型輸出契約，才允許重新跑一個 sanitized APPROVE與一個REJECT corpus，各3個fresh process，共精確6次；無retry、無第7次。任一3/3失敗立即 `BLOCKED`。
- 不安裝、不登入、不改設定；`provider_model_calls` 維持 `unobservable/unknown`。

## 驗收與交付

- Reviewer `adversarial_probes.py` 原始四個REPRO全部轉為拒絕/正確計數，並補production tests防止只修probe。
- focused affected tests、py_compile、strict stored corpus replay、allowlist、privacy/secret/raw/path/`[DBG-]` scan、`git diff --check` 全部通過。
- full suite要跑；既有Ziwei baseline failures可如實列出，但不得宣稱全綠或修改無關路徑。
- evidence至少包含 `root-cause.md`、`red-green.txt`、`verification.txt`、`decision.md`；若重跑Gemini才新增fresh receipts/corpus。
- 建立單一Repair 1 candidate commit，回完整SHA；只能 `DELIVERED_CANDIDATE`、`READY_FOR_REVIEW` 或 `BLOCKED`。
- 完成後必須回原Reviewer thread `019f83d4-de93-79c0-ba8a-674565e107e8` re-review；不得換Reviewer、自審GO、merge、push、deploy、publish或恢復內容線。
