---
card_id: CARD-CONTENT-GEMINI-REVIEWER-SINGLE-SHOT-V3-REVIEW-001
chain_id: CONTENT-GEMINI-REVIEWER-SINGLE-SHOT-V3-001
status: CARD_DRAFTED
review_kind: full
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 候選跨31檔並重建production Gemini operation state、outbox跨tick、immutable evidence與machine witness；需高風險獨立審查
ownership: 唯讀審查固定Single-Shot V3 candidate的spec、correctness、regression、privacy與test gaps
base_sha: 37e1cf2b81eb10006ad2ec41bfdc81df12e94144
candidate_sha: a5309552a9e7caf3ba85fb627a82dbfee0b3c21c
reviewed_commit_required: a5309552a9e7caf3ba85fb627a82dbfee0b3c21c
implementation_thread_id: 019f8438-8e87-7e71-8416-061be5958584
allowlist:
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_single_shot_v3_review_001/**
forbidden_scope:
  - candidate code, tests, docs or implementation evidence
  - app/**, articles, registry, metadata and publishing files
  - Gemini CLI, HTTP or any external model invocation
  - fix, merge, push, deploy, publish, production or content-line recovery
verification:
  - fixed-range diff and allowlist audit
  - adversarial offline probes for single-shot, outbox cross-tick and immutable replay
  - focused tests, stored corpus replay, py_compile and git diff check
  - privacy and evidence integrity scan
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_single_shot_v3_review_001/
thread_id: PENDING
thread_status: CARD_DRAFTED
worktree_path: PENDING
cwd: PENDING
---

# CARD-CONTENT-GEMINI-REVIEWER-SINGLE-SHOT-V3-REVIEW-001｜V3 獨立審查

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-REVIEWER-SINGLE-SHOT-V3-REVIEW-001`；固定審查 `37e1cf2..a530955`。
派工對象｜`gpt-5.6-sol`、`high`；full review，只審不修。
任務目的｜判定 V3 是否真正移除同 operation transport retry，且 new-operation resume、outbox跨tick、records與model witness不形成等價旁路。
可改範圍｜只新增本Review evidence；candidate全部唯讀。
驗收證據｜path:line findings、adversarial probes、Spec/Standards axes、GO/NO_GO與固定reviewed SHA。

## 啟動 Gate

- 獨立clean worktree；HEAD為只含本Review卡的provisioning commit，HEAD^精確為candidate `a5309552a9e7caf3ba85fb627a82dbfee0b3c21c`。
- 實際reviewed range固定`37e1cf2b81eb10006ad2ec41bfdc81df12e94144..a5309552a9e7caf3ba85fb627a82dbfee0b3c21c`；provisioning不算candidate。
- implementation evidence、corpus與18份records可讀；SHA/scope/evidence不一致立即BLOCKED。

## 必審 correctness

- 沿所有production caller追蹤同一operation ID，證明最多一個external process start；不得只靠字串搜尋。
- `_outbox_transport` pending跨tick只能consume既有response，不得再次generate、建立新job、改request binding或把不同operation response接回舊operation。
- duplicate operation、已存在manifest/terminal/gate、partial triple、malformed record、concurrent writer都須在process前fail closed且舊bytes不變。
- PROCESS_NOT_STARTED、PROCESS_TERMINAL、GATE_TERMINAL狀態、sequence、parent hash與binding是否完整；hash chain是否涵蓋所有安全關鍵欄位，是否有可替換record但維持驗證的旁路。
- `parent_operation_id`只供audit；不得影響本次authorization、result selection或讓新operation沿用舊request/candidate/response。
- 上層resume只重送BLOCKED/PENDING item；APPROVED不重送；同blocker第三個獨立operation後無第四個。測count與實際launcher calls一致。
- CLI_NOT_FOUND=0 external；success/nonzero/timeout=1 external。outbox queue未啟動process時不得誤計external process。
- HTTP、CLI、outbox、runner所有transport均無自動retry、backoff、attempt loop或同operation第二次call；外部CLI內部provider calls仍標unknown。

## Judgment與machine witness

- model output不參與identity routing；comparative/deterministic codes不在model machine allowlist。
- 每個model code的local validator是否真的code-specific、綁定target content且不只做脆弱關鍵字判斷；無法本地證明者必須advisory。
- `evidence_quote`需與target、code predicate一致；generic/structural/synthetic token、無關quote、other-item claim、swapped candidate SHA須拒絕。
- strict JSON拒絕nested duplicate keys、unknown/missing fields、wrong types、trailing prose/fence與所有cross-field contradiction。

## 必做 adversarial probes

1. 同operation連續呼叫兩次；pending outbox跨tick；response存在/缺失/錯job/錯binding；驗新增external calls為0或1且不重送。
2. manifest-only、terminal-only、gate-only、duplicate triple、partial write、unknown status/type、hash/binding swap、record替換與concurrent exclusive create。
3. new operation偽造parent link、沿用request ID、candidate SHA或response；APPROVED item混入resume；三次同blocker後嘗試第四次。
4. HTTP 429/503、CLI nonzero/timeout/missing、outbox pending等路徑，逐一驗0/1 process與無backoff/retry。
5. model code搭配unrelated but existing quote、generic token、other-item prose、comparative claim；檢查是否仍可machine REJECT。
6. V2 final multi-retry反例以V3 public API等價重建；不得依賴V2-only private helper才能驗證。

## 驗證與結論

- 禁止呼叫Gemini CLI；只離線strict replay既有6-operation corpus，確認6 manifests+6 terminals+6 gates、APPROVE/REJECT各3、無第7process、provider calls unknown。
- 跑focused affected tests、adversarial probes、py_compile、fixed-range allowlist、privacy scan與git diff check。可跑full suite，但Ziwei baseline不得寫成全綠。
- findings依P0→P3，每筆path:line、trigger、evidence、risk、suggested fix、validation gap、confidence。
- 分列Spec axis、Standards axis、Testing gaps、Residual risks。
- 任一P0/P1/P2、production safety risk、SHA/scope/evidence不一致或single-shot invariant無法重現 => NO_GO；全部關閉才GO。
- 建立單一Review evidence commit，回完整SHA；不得修改candidate、自行修復、merge、push、deploy、publish或恢復內容線。
