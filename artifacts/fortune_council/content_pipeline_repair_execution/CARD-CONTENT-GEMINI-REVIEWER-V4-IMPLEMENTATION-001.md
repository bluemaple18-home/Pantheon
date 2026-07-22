---
card_id: CARD-CONTENT-GEMINI-REVIEWER-V4-IMPLEMENTATION-001
chain_id: CONTENT-GEMINI-REVIEWER-V4-IMPLEMENTATION-001
status: CARD_DRAFTED
role: production_implementation
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
architecture_sha: 3da0ba4
architecture_review_sha: afced35
allowlist:
  - scripts/agy_gemini_v4_broker.py
  - scripts/agy_gemini_runner.py
  - tests/test_agy_gemini_v4_broker.py
  - tests/test_agy_gemini_outbox.py
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_v4_implementation_001/**
forbidden_scope:
  - scripts/agy_seo_copy_pipeline.py
  - other outbox/coordinator production modules
  - app/**, articles, registry, metadata and publishing files
  - existing V1-V4 evidence and architecture candidate files
  - dependency, automatic retry, real Gemini invocation or HTTP
  - merge, push, deploy, publish or content-line recovery
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_v4_implementation_001/
thread_id: PENDING
thread_status: CARD_DRAFTED
worktree_path: PENDING
cwd: PENDING
---

# Gemini Reviewer V4｜Bounded Broker Implementation 1

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-REVIEWER-V4-IMPLEMENTATION-001`；新 implementation chain，不是 architecture Repair 3。
派工對象｜`gpt-5.6-sol`、`high`；production boundary，strict。
任務目的｜把已獲 GO 的方案 B 實作成單一 broker module，僅用 feature flag 接一條 runner canary caller。
可改範圍｜一個新 broker module、一個 runner callsite、兩個 test files、獨立 evidence root。
驗收證據｜isolated fake tests、flag-off regression、flag-on single-process trace、fail-closed replay、完整測試與單一 candidate commit。

## 固定前提

- 完整讀 `docs/pantheon_gemini_reviewer_v4_architecture.md` 與最終 GO evidence；架構契約是 immutable input，不得在本卡改寫。
- 唯一 production entrypoint 是 `scripts.agy_gemini_v4_broker:run_single_shot`；不得新增第二個 spawn helper。
- process accounting 定義為成功跨過 exec 的 target process 數，只能 `0 / 1 / UNKNOWN`。
- 本卡全程使用 synthetic executable/fake target；不得呼叫真實 Gemini CLI、HTTP 或外部 model。

## RED 先行

1. Flag 關閉時 `process_once` byte/behavior compatible，既有 injected `generate_json` 路徑只呼叫一次。
2. Flag 開啟時只走 `run_single_shot`，同一 operation 不得呼叫 legacy generator、不得 dual-spawn、不得 automatic retry。
3. 合法 success/nonzero/timeout trace 均只有一個 exec-confirmed target；結果與 receipt 綁定 job/request/model/item/attempt。
4. preflight missing=0；exec failure、crash-before-fork、fork/exec window、terminal loss分別依合法表回 `BLOCKED/AMBIGUOUS`，不得猜 count。
5. `BLOCKED / AMBIGUOUS / INVALID` 一律 fail closed，runner 寫 failed record並 archive；不得 fallback legacy、補 terminal、replay target。
6. schema/version/binding/order/frame/chain、legacy alias、PID domain、anchor missing/mismatch/ledger-ahead皆拒絕或 fail closed。
7. target exec 後只見 stdio，ledger FD/path/anchor/identity不得出現在 target argv/env/stdin。

## Production contract

- Parent→broker 使用 versioned length-prefixed JSON command frame；raw request 只走獨立 stdin pipe。
- Broker 是唯一 ledger writer及 target launcher；ledger append→fsync→next anchor；anchor store 介面固定 `load` 與 `compare_and_swap`。
- broker→target 固定 `close_fds=True`、`pass_fds=()`；使用 exec-confirmation handshake；wait/timeout 必須 reap。
- Event schema/FSM、合法 status/count/completeness/resend 表、external anchor consistency與 privacy boundary逐字遵守已審核架構。
- `run_single_shot` 回傳 typed immutable result；只有 `COMPLETE` 且符合 caller contract才可產生 inbox result。
- `AGY_GEMINI_V4_BROKER=1` 是唯一 canary switch。Flag 關閉走 legacy；flag 開啟後禁止任何 legacy fallback。
- 只改 `scripts/agy_gemini_runner.py:process_once` 內原 `generate_json(...)` 單一 callsite及必要的窄型別/flag wiring；其他 caller 不動。

## Migration 與 rollback

- evidence 明列 flag-off、flag-on fake canary、failure rollback 三種操作流程。
- rollback 只關 flag；V4 ledger/anchor保留唯讀，不翻譯成 legacy receipt、不補事件、不重啟 target。
- flag-on operation 若已 `BLOCKED/AMBIGUOUS/INVALID`，即使之後關 flag也不得讓同一 job fallback legacy。
- 真實 Gemini canary、舊 retry 移除、其他 caller cutover、三條內容線恢復都必須另卡。

## 驗證與交付

- 新增 `tests/test_agy_gemini_v4_broker.py`；只在 `tests/test_agy_gemini_outbox.py` 補 runner canary/fail-closed contract。
- focused tests、受影響 outbox tests、全套 tests、`py_compile`、fake trace兩次 byte-identical、allowlist、敏感資訊/原始本機路徑/`[DBG-]`、`git diff --check`。
- evidence 至少 `root-cause.md`、`red-green.txt`、`verification.txt`、`migration-rollback.md`、`decision.md`。
- 建立單一 implementation candidate commit，狀態只能 `READY_FOR_REVIEW` 或 `BLOCKED`；不得自審 GO。
- candidate 必須交獨立 Reviewer；Reviewer GO 前不得開真實 CLI canary或恢復任何內容線。
