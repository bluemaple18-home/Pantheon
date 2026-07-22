---
card_id: CARD-CONTENT-GEMINI-REVIEWER-V4-ARCHITECTURE-REVIEW-001
chain_id: CONTENT-GEMINI-REVIEWER-V4-001
status: CARD_DRAFTED
role: independent_architecture_reviewer
thickness: strict
risk: high
reviewed_candidate_sha: 735d2850bd89bf3e4b29748f310981ba4d855709
reviewed_range: 8a4ade5bcadd16fa8e5a7bc0d14e730041b43088..735d2850bd89bf3e4b29748f310981ba4d855709
allowlist:
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_v4_architecture_review_001/**
forbidden_scope:
  - candidate, POC, tests, docs, spike evidence and all V1-V3 files modification
  - production implementation or repair
  - Gemini CLI, HTTP or external model invocation
  - merge, push, deploy, publish or content recovery
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_v4_architecture_review_001/
thread_id: PENDING
thread_status: CARD_DRAFTED
worktree_path: PENDING
cwd: PENDING
---

# V4 Architecture Review｜Inherited-FD broker ledger

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-REVIEWER-V4-ARCHITECTURE-REVIEW-001`。
派工對象｜獨立 full／strict architecture Reviewer。
任務目的｜判定方案 B 是否足以進入 production implementation，且沒有重演 V3 的信任邊界誇大。
可改範圍｜只可新增本 Review evidence。
驗收證據｜reviewer-owned probes、finding schema、GO／NO_GO與單一review commit。

## 啟動 Gate

- 獨立 clean worktree；HEAD 為只含本卡的provisioning commit，HEAD^精確為reviewed candidate。
- reviewed range固定為`8a4ade5...735d285...`；provisioning不算candidate。
- 完整讀取架構文件、POC/tests、四份spike evidence、V3 recovery review與使用者開源盤點。
- Python只用主工作區既有`.venv`；全程離線。

## Spec axis

- 三方案是否真的可比較，C沒有kernel實作時是否全數`UNSUPPORTED`。
- 方案 B 是否不再使用filesystem token，且Gemini child不繼承ledger FD、capability、records path或writer authority。
- event schema是否清楚分離logical operation、broker/fork attempt、Gemini CLI process start、exec failure與terminal outcome。
- missing/preflight=0；成功跨spawn邊界後success/nonzero/timeout=1；provider internal calls unknown。
- crash/partial failure後，replay是否能誠實輸出complete、blocked或ambiguous，不得猜process count。

## Standards／adversarial axis

- Reviewer-owned probe不得只重跑candidate tests；需攻擊：FD leak across exec、wrong `close_fds/pass_fds`、foreign inherited FD、same-UID raw ledger write、partial/truncated/duplicate/out-of-order frame、wrong binding、parent crash、broker crash before/after spawn event、exec missing/race、PID reuse與replay completeness。
- same-UID raw filesystem mutation若不能prevent，必須標`OUT_OF_SCOPE`或`DETECTED`，且external anchor不能由ledger自證。
- append-only／hash chain只證tamper evidence，不得宣稱kernel immutability。
- matrix不能硬編期待值而沒有實際observable；兩次byte-identical不得掩蓋未測行為。
- POC不得被production import；不得新增重型framework dependency或automatic retry。
- migration／rollback／implementation allowlist與caller API必須足以開下一張bounded implementation卡。

## Finding 與 verdict

- finding必須含severity、category、path:line、evidence、risk、suggested_fix、validation_gap、confidence。
- `GO`：無P0/P1、方案B可進production implementation；P2/P3需列清楚但不冒充零風險。
- `NO_GO`：任一process accounting、FD isolation、crash replay、threat boundary或證據誠實性P1。
- `BLOCKED`：只限客觀環境阻斷；同 blocker第三次即停。
- 只新增review evidence並提交單一commit；不得修candidate或開始implementation。
