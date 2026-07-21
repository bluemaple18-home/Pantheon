---
card_id: CARD-CONTENT-GEMINI-REVIEWER-SINGLE-SHOT-V3-REPAIR-001
chain_id: CONTENT-GEMINI-REVIEWER-SINGLE-SHOT-V3-001
status: CARD_DRAFTED
repair_generation: 1
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 五個P1涉及production caller整合、outbox binding、record trust anchor、pre-launch concurrency與code-specific witness，屬核心transport修復
ownership: 只修V3 Review 001固定五個P1，交付Repair 1 candidate並回原Reviewer
base_candidate_sha: a5309552a9e7caf3ba85fb627a82dbfee0b3c21c
review_evidence_sha: be19f6223eaebcece71b326f71a497c7b161d3a8
reviewer_thread_id: 019f844f-5219-7221-a1ac-b4b72a976ba2
allowlist:
  - scripts/agy_gemini_operations.py
  - scripts/agy_seo_copy_pipeline.py
  - scripts/agy_gemini_outbox.py
  - scripts/agy_gemini_runner.py
  - scripts/agy_gemini_transport_probe.py
  - tests/test_agy_gemini_operations.py
  - tests/test_agy_seo_copy_pipeline.py
  - tests/test_agy_gemini_outbox.py
  - tests/test_agy_gemini_transport_probe.py
  - docs/pantheon_gemini_outbox_runner.md
  - docs/pantheon_gemini_reviewer_transport_strategy.md
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_single_shot_v3_repair_001/**
forbidden_scope:
  - implementation or Review evidence modification
  - app/**, articles, registry, metadata and publishing files
  - runtime retry, automatic retry or attempt-chain authorization
  - semantic guessing or unanchored replay
  - Gemini installation/login/configuration change
  - merge, push, deploy, publish, production or content-line recovery
verification:
  - exact Reviewer adversarial probes RED then GREEN
  - production caller graph and 0/1 launcher accounting tests
  - stored corpus strict replay with caller-owned anchors
  - focused/full tests, py_compile, allowlist, privacy and diff checks
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_single_shot_v3_repair_001/
thread_id: PENDING
thread_status: CARD_DRAFTED
worktree_path: PENDING
cwd: PENDING
---

# CARD-CONTENT-GEMINI-REVIEWER-SINGLE-SHOT-V3-REPAIR-001｜接入 production trust boundary

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-REVIEWER-SINGLE-SHOT-V3-REPAIR-001`；Repair generation 1。
派工對象｜`gpt-5.6-sol`、`high`；只修固定五個P1。
任務目的｜把single-shot operation正式接入所有production callers，封閉outbox binding、whole-triple replacement、pre-launch race與swapped witness。
可改範圍｜共用operation模組、既有transport callers、tests/docs與Repair evidence。
驗收證據｜Reviewer原probe RED→GREEN、production caller tests、strict anchored replay、完整gates與candidate SHA。

## 啟動 Gate

- 獨立clean worktree；HEAD為只含本卡的provisioning commit，能追溯candidate `a5309552a9e7caf3ba85fb627a82dbfee0b3c21c` 與Review evidence `be19f6223eaebcece71b326f71a497c7b161d3a8`。
- 完整讀取並先執行Review `adversarial_probes.py`，五個P1全部形成public RED；無法重現先BLOCKED，不得猜修。
- 只吸收V3 candidate，不沿用V2 run/receipt/retry chain。

## P1-01｜operation contract接入production

- 將operation binding、namespace claim、manifest/terminal/gate schema、single-shot launcher、anchored replay與resume policy抽到production共用模組`agy_gemini_operations.py`；probe只能作consumer，不得持有唯一實作。
- CLI、HTTP、outbox、runner與`_generate_with_receipt`所有external generation caller都必須先建立fresh operation binding，再透過同一single-shot API啟動零或一次process。
- production receipt/evidence必須保存operation ID、run/request/item/candidate binding與0/1 process accounting；schema/content repair loop每次generation都是新operation，不能在同operation重送。
- 同blocker第三個獨立operation失敗後停止，無第四個；APPROVED item不重送。
- 補caller graph tests，直接assert production launcher calls與records，不能只測probe。

## P1-02｜outbox落盤request strict binding

- `consume_existing_json`必須在outbox/processing/archive中精確找到一份request；0份、2份以上、malformed或unknown fields都fail closed。
- strict parse落盤request，canonical bytes/完整欄位與重新計算expected request逐欄相等後才可consume response。
- expected filename但request SHA/model/schema/prompt hash/job ID任一錯配都拒絕；不得建立新job、不得generate第二次。
- response同時維持既有strict binding；request與response必須共同指向同operation。

## P1-03｜whole-triple replacement需要caller-owned anchor

- `replay_operation_records`不得無expected bindings執行；API必須要求caller提供不可由records自我聲明的expected operation commitments（operation/item/request/run/candidate/manifest digest）。
- production expected commitments來自上層run manifest/operation plan，在process前exclusive create並由caller持有；replay逐筆比對，record自洽不等於truth。
- stored corpus verifier也必須從corpus summary中的固定commitments傳入expected bindings，並檢查record數、唯一性與manifest digest。
- Reviewer whole-triple替換＋重算hash時，因expected binding/digest不符而fail closed。
- 若本地filesystem owner可連同anchor一起任意替換，文件必須明列threat boundary；不得宣稱防惡意root。驗收只要求應用程式內records不能自證。

## P1-04｜pre-launch concurrent writer

- 在launcher前原子取得operation namespace ownership並預先claim manifest/terminal/gate完整路徑或等價單一journal；任何partial/競態existing path都在process前失敗。
- claim必須跨process可驗（O_EXCL/atomic directory/lock）；只做`exists()`不合格。
- launcher執行期間ownership持續有效；terminal/gate只由owner完成一次。另一合法writer不能插入或覆寫。
- 精確Reviewer probe：manifest建立後插入terminal時，launcher calls必須0；舊bytes不改。

## P1-05｜witness quote與code predicate直接綁定

- code validator只可檢查該finding的normalized `evidence_quote`及caller target，不得只在整體target另找關鍵字。
- `GUARANTEE_CLAIM`的quote本身必須含可驗證保證語；`UNSUPPORTED_AUTHORITY`的quote本身必須同時滿足其authority predicate。swapped quote必須拒絕。
- generic/structural/synthetic/過短quote、other-item/comparative claim與無validator code皆不得影響machine verdict；不可證明者advisory。
- message不作machine semantic evidence，不用keyword猜message。

## TDD與驗證

- 原Reviewer五個probe先RED；每個finding先補production public regression，再一次只改一個seam並立即GREEN。
- 需補HTTP429/503、CLI missing/nonzero/timeout、outbox pending跨tick、duplicate/partial/concurrent records、resume/third-blocker tests。
- prompt/schema若未變，不重跑Gemini，只離線strict replay既有6-operation corpus；若contract必須變，才允許全新APPROVE/REJECT各3，共6 processes、無第7次。
- 跑focused affected、full suite、py_compile、caller trace、runtime-retry search、anchored tamper matrix、allowlist、privacy/secret/raw/path/`[DBG-]`、git diff check。
- Ziwei baseline如實分列，不改無關檔。
- evidence至少`root-cause.md`、`red-green.txt`、`verification.txt`、`decision.md`；若fresh corpus才新增records/corpus。
- 建立單一Repair 1 candidate commit，回完整SHA；只能READY_FOR_REVIEW或BLOCKED。
- 完成回原Reviewer `019f844f-5219-7221-a1ac-b4b72a976ba2` re-review；不得自審GO、merge、push、deploy、publish或恢復內容線。
