---
card_id: CARD-CONTENT-GEMINI-REVIEWER-TRANSPORT-V2-REPAIR-002
chain_id: CONTENT-GEMINI-REVIEWER-TRANSPORT-V2-001
status: CARD_DRAFTED
repair_generation: 2
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 最後一代 Repair，需封閉 retry 前驗證、pre-filter replay bypass、logical/external accounting 分離與不可證明語意 finding 的 machine-gate 邊界
ownership: 只修 Repair 1 re-review 的四個固定旁路；成功後回原 Reviewer，失敗即整鏈 BLOCKED
repair_1_candidate_sha: 1bac6ea896c14f9f6b7dc4c3097f8b17cfbfff65
re_review_evidence_sha: f44ab3dbd178c8847d0c5460dc6276cf06ce6726
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
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_transport_v2_repair_002/**
forbidden_scope:
  - prior implementation, Review, Repair 1 or re-review evidence modification
  - app/**, articles, registry, metadata and publishing files
  - unrelated refactor or new feature
  - semantic guessing, keyword heuristics or free-form message trust
  - Gemini installation, login, OAuth, token, MCP or global configuration change
  - Repair 3, merge, push, deploy, publish, production or content-line recovery
verification:
  - exact re-review adversarial probes RED then GREEN
  - public production regressions for all four bypasses
  - focused/full affected tests and stored corpus tamper replay
  - py_compile, allowlist, privacy scan and git diff --check
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_transport_v2_repair_002/
thread_id: PENDING
thread_status: CARD_DRAFTED
worktree_path: PENDING
cwd: PENDING
---

# CARD-CONTENT-GEMINI-REVIEWER-TRANSPORT-V2-REPAIR-002｜最後四個旁路修復

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-REVIEWER-TRANSPORT-V2-REPAIR-002`；Repair generation 2，最後一代。
派工對象｜`gpt-5.6-sol`、`high`；只修 re-review 固定 3×P1、1×P2。
任務目的｜在任何 retry/process 啟動前驗證完整pair、讓所有matching persisted files先過schema、分開logical與started-process計數，並移除不可本地證明的model machine-gate codes。
可改範圍｜固定 transport、tests/docs 與本 Repair evidence；禁止內容與發布面。
驗收證據｜原 re-review probes RED→GREEN、production regressions、完整 gate 與固定 candidate SHA。

## 啟動與硬停損

- 新獨立 clean worktree；HEAD 必須為只含本卡的 provisioning commit，能追溯 Repair 1 candidate `1bac6ea896c14f9f6b7dc4c3097f8b17cfbfff65` 與 re-review evidence `f44ab3dbd178c8847d0c5460dc6276cf06ce6726`。
- 完整讀取並先執行 `gemini_reviewer_transport_v2_repair_001_re_review_001/adversarial_probes.py`；四個 `REPRO` 必須逐一成為 public RED test。
- 這是最後一代 Repair。任一 finding 無法封閉、Reviewer 再次 `NO_GO` 或外部 corpus 失敗，整條 chain `BLOCKED`；禁止 Repair 3、改名重開或擴需求。

## 固定修復 1｜retry authorization 必須先驗證 pair

- 在配置新 invocation ID、寫新檔或啟動 subprocess 之前，先對既有 terminal+gate 執行與 replay 相同的 strict pair validator。
- validator 輸入 caller-owned expected item/request/candidate/attempt/invocation binding；完整驗 schema、event type、status、multiplicity、pair equality與合法 transition。
- gate filename 正確但 payload 的 item/invocation/request/candidate/attempt 任一不符，必須 fail closed，且 `external_cli_process_invocations` 不增加、不得建立 runtime-retry receipt。
- 只有完整 validated pair 顯示 `process_succeeded + gate failed` 或合法 retryable transport failure 時，才可配置全新 invocation/attempt。
- 加入 re-review 精確反例：A/X terminal＋B/Y failed gate不得授權retry；合法A/X failed pair仍可fresh retry。

## 固定修復 2｜matching persisted files 不得在 schema 前消失

- 先列舉所有符合 terminal/gate naming contract 的檔案，再逐一 strict JSON parse與schema validation；禁止用 `terminal_status`、event type或其他payload discriminator做pre-filter。
- matching file缺欄、unknown欄位、unknown status/event、錯誤型別或非法binding必須立即阻擋 replay；不得變成pending、0 invocation或被略過。
- 檔名與payload type必須一致；任何partial/corrupt file視為 evidence integrity failure。
- 加入精確反例：`terminal-receipt.json` 缺 `terminal_status` 且無gate必須 fail closed；另測gate缺status、unknown field與malformed JSON。

## 固定修復 3｜logical attempts 與 actual started processes 分帳

- `reviewer_attempts`／attempted identities 可包含 `process_not_started`；`external_cli_process_invocations` 與 `reviewer_processes` 只能計算可證明process已啟動的 terminal states。
- allowlisted started states至少明確列出 `process_succeeded`、`process_nonzero`、`process_timeout`；`process_not_started`／`CLI_NOT_FOUND` 為0 external process。
- 不得用 receipt數或logical call數替代process數。所有top-level、closure、partial failure、resume與accounting artifact使用同一 validated reducer。
- first/middle/last failure與closure N篇測試需同時assert logical attempts、started processes、success/failure/pending，不可只assert單一calls欄位。

## 固定修復 4｜不可證明的比較語意退出 machine gate

- `TEMPLATE_USAGE` 等比較型／cross-item／deterministic codes必須從 Gemini model output allowlist移除，只能由本地cross-item deterministic gate對實際items產生。
- 建立明確 `model_code -> local witness validator` registry。每個仍可由模型輸出的code都必須有code-specific machine-verifiable predicate；沒有validator的code不得進production accepted allowlist，Gemini對其文字判斷最多是advisory，不能造成machine REJECT/APPROVE。
- 單純「quote存在target」不夠。validator必須證明quote與該code的local predicate相符；拒絕structural key/slot/synthetic ID、過短generic token、與message無關的quote及只在其他item成立的比較claim。
- 不對free-form message做關鍵字或語意猜測；message不是machine evidence。若code本質無法由本地predicate證明，必須移出model machine-gate contract。
- 加入精確反例：A上的generic quote `article-01`＋B-only `TEMPLATE_USAGE` message必須拒絕；真正cross-item template finding只由local deterministic gate產生且綁定正確items。

## TDD 節奏

1. 原 Reviewer re-review probes原封不動跑出四個RED並保存輸出。
2. 每個旁路先補一個production public regression，再一次只改一個接縫。
3. 每項修完立即重跑該RED與既有Repair 1 tests；不得四項一起改完才驗證。
4. 精準假說：
   - P1-01 在retry decision前缺共同strict validator。
   - P1-02 在schema前按payload discriminator過濾。
   - P1-03 reducer把terminal receipt存在等同process started。
   - P2-01 quote existence被誤當code-specific grounding。
- debug僅可用唯一 `[DBG-...]` 前綴，交付前必須清零。

## Gemini CLI 邊界

- 先完成所有離線 RED→GREEN與stored tamper replay。
- 若本卡只縮小model allowlist且既有fresh corpus仍符合新contract，優先離線重算，不增加外部process。
- 若 prompt/schema或REJECT fixture必須改，才允許一組新的sanitized APPROVE/REJECT各3 fresh processes，共精確6次、無retry/第7次；任一3/3失敗即`BLOCKED`。
- 不安裝、不登入、不改設定；`provider_model_calls=unobservable/unknown`。

## 驗收與交付

- re-review四個原始REPRO全部無法再穿透，且相鄰合法case仍通過。
- focused affected tests、full suite、py_compile、strict stored replay/tamper matrix、allowlist、privacy/secret/raw/path/`[DBG-]` scan、`git diff --check`完成。
- Ziwei baseline failures如仍存在可如實列出，不得修改無關檔或宣稱全綠。
- evidence至少包含 `root-cause.md`、`red-green.txt`、`verification.txt`、`decision.md`；如重跑Gemini才加入fresh corpus/receipts。
- 建立單一Repair 2 candidate commit，回完整SHA；只能 `READY_FOR_REVIEW` 或 `BLOCKED`。
- READY後回原Reviewer thread `019f83d4-de93-79c0-ba8a-674565e107e8` re-review。若仍NO_GO，立即BLOCKED並停止；不得Repair 3、自審GO、merge、push、deploy、publish或恢復內容線。
