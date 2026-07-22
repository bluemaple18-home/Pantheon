---
card_id: CARD-CONTENT-GEMINI-REVIEWER-V4-ARCHITECTURE-REPAIR-001
chain_id: CONTENT-GEMINI-REVIEWER-V4-001
status: CARD_DRAFTED
repair_generation: 1
role: architecture_repair
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
base_candidate_sha: 735d2850bd89bf3e4b29748f310981ba4d855709
review_evidence_sha: 0e53198511b34ca1001b819fa61438ebe0aae2aa
reviewer_thread_id: 019f881f-825d-79a1-b8d3-4fcdd07f0a86
allowlist:
  - docs/pantheon_gemini_reviewer_v4_architecture.md
  - scripts/agy_gemini_v4_architecture_probe.py
  - tests/test_agy_gemini_v4_architecture_probe.py
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_v4_architecture_repair_001/**
forbidden_scope:
  - Review/spike/V1-V3 evidence modification
  - existing production pipeline, outbox, runner, transport and operation modules
  - app/**, articles, registry, metadata and publishing files
  - framework dependency, automatic retry or Gemini invocation
  - merge, push, deploy, publish, production or content-line recovery
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_v4_architecture_repair_001/
thread_id: PENDING
thread_status: CARD_DRAFTED
worktree_path: PENDING
cwd: PENDING
---

# V4 Architecture Repair 1｜Broker handshake、strict replay與誠實邊界

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-REVIEWER-V4-ARCHITECTURE-REPAIR-001`；Repair 1/2。
派工對象｜`gpt-5.6-sol`、`high`；只修 Architecture Review固定5個P1與2個P2。
任務目的｜讓方案B POC真正走broker→target，補exec/crash分帳、strict replay、資料一致性邊界與bounded caller API。
可改範圍｜V4架構文件、隔離POC/tests與Repair 1 evidence。
驗收證據｜原Reviewer probes RED→GREEN、fresh negative controls、derived matrix與單一candidate commit。

## 啟動 Gate

- 獨立 clean worktree；HEAD為只含本卡的provisioning commit，父鏈包含review evidence與candidate。
- 完整讀Review `review.md`、`findings.json`、`reviewer_probes.py`與results；原5P1/2P2全部先RED。
- Python只用主工作區既有`.venv`；fake executable/local subprocess only。

## P1-01｜Crash window不得猜0／1

- 建立真實broker process；broker才是唯一ledger writer與target launcher。
- 使用POSIX close-on-exec error-pipe或等價可驗handshake：preflight reject、fork attempted、exec failed、exec confirmed、process terminal為不同observable／event。
- broker crash before fork且有durable evidence才可0；exec confirmed且durable start event才可1；spawn／exec與durable event間無法判定時必須`AMBIGUOUS`，禁止自動重送。
- crash-before-spawn與crash-after-spawn-before-event不得再得到相同`complete=true/process=0`結論。

## P1-02｜Strict typed FSM replay

- 每event使用strict schema：拒絕unknown/missing/type錯誤、非法outcome、非法ordinal、wrong binding/version。
- 恰一OPERATION_CREATED、恰一broker attempt；合法序列與terminal completeness明列。
- 拒絕terminal-before-start、re-chained duplicate、out-of-order、partial/truncated frame、duplicate ordinal與未知event。
- replay status至少`COMPLETE / BLOCKED / AMBIGUOUS / INVALID`，process count只能`0 / 1 / UNKNOWN`並有合法組合表。

## P1-03｜真實broker→target FD isolation

- POC必須由broker接收唯一allowlisted ledger FD，再由broker啟動fake Gemini target；不得由parent另起target冒充。
- broker保有ledger FD；target以`close_fds=True`且不在`pass_fds`帶入ledger，exec後實測FD table不可寫ledger。
- 非預期close_fds、pass_fds與額外繼承FD必須作為negative control，並使matrix降級／失敗，不能仍綠。
- ledger FD/capability/path不得放target argv/env/stdin；target只持必要stdio pipes。

## P1-04｜External anchor與本機同帳號一致性邊界

- 明列external anchor owner、建立／原子更新順序、crash lifecycle與recovery讀取接口。
- 若anchor仍與ledger位於相同本機帳號與trust domain，整份ledger替換固定`OUT_OF_SCOPE`，不得標`DETECTED`。
- hash chain只偵測相對既有trusted anchor的資料變更；ledger不得自證anchor。
- application-level wrong binding／partial mutation仍需`DETECTED`或`PREVENTED`。

## P1-05｜Preflight與post-fork exec failure分帳

- schema新增明確preflight rejection與exec failure；真實missing executable、permission/loader failure或preflight-to-exec race需獨立probe。
- preflight rejection為0；fork後exec failure不得與preflight byte-identical，需記broker/fork attempt與exec failure；Gemini process count依定義為0或UNKNOWN，但不得偽裝未attempt。
- exec confirmed後success/nonzero/timeout皆process=1。

## P2｜Evidence與bounded implementation contract

- matrix supported cells必須引用`observable_id`與predicate，由runtime結果推導；加入資料變更／negative control，observable反轉時cell必須降級。
- 架構文件鎖定：單一broker entrypoint、wire/frame schema、FD allowlist/CLOEXEC、anchor owner、handshake、replay enums、PID非identity、exact production callers/callsites、feature flag、legacy retry移除、migration/rollback與implementation allowlist/test filenames。
- spike仍不得修改production；只把下一張implementation卡寫到可bounded執行。

## 驗證與交付

- 原Reviewer probes先RED後GREEN；新增真實broker crash、orphan target、exec race、FD-table、anchor-loss/full-replacement、illegal FSM與matrix negative-control tests。
- focused tests、py_compile、POC兩次byte-identical、matrix schema/status/observable linkage、allowlist、privacy/secret/raw path/`[DBG-]`、`git diff --check`。
- 不呼叫Gemini／HTTP／外部model。
- evidence至少`root-cause.md`、`red-green.txt`、`verification.txt`、`decision.md`。
- 建立單一Repair 1 architecture candidate，狀態`READY_FOR_REVIEW`或`BLOCKED`；回原Reviewer re-review，不自審GO、不進production。
