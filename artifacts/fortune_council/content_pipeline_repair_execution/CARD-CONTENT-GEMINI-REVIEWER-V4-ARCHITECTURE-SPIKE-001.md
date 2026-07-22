---
card_id: CARD-CONTENT-GEMINI-REVIEWER-V4-ARCHITECTURE-SPIKE-001
chain_id: CONTENT-GEMINI-REVIEWER-V4-001
status: CARD_DRAFTED
role: architecture_spike
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 需重建process accounting與writer ownership信任邊界，並從三種架構中做可驗證取捨
base_main_sha: c489422
blocked_v3_candidate_sha: f6a86a5884a55514133c9ce2ea9553c32444bca2
allowlist:
  - docs/pantheon_gemini_reviewer_v4_architecture.md
  - scripts/agy_gemini_v4_architecture_probe.py
  - tests/test_agy_gemini_v4_architecture_probe.py
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_v4_architecture_spike_001/**
forbidden_scope:
  - existing production pipeline, outbox, runner, transport and operation modules
  - V1/V2/V3 cards, code candidates and evidence modification
  - app/**, articles, registry, metadata and publishing files
  - Gemini installation/login/configuration or fresh model invocation
  - merge, push, deploy, publish, production or content-line recovery
verification:
  - reproduce V3 same-UID token-file bypass
  - executable comparison of three trust-boundary options
  - explicit threat model and process-accounting state machine
  - focused tests, py_compile, privacy, allowlist and diff checks
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_v4_architecture_spike_001/
thread_id: PENDING
thread_status: CARD_DRAFTED
worktree_path: PENDING
cwd: PENDING
---

# V4 Architecture Spike｜移除 filesystem token ownership

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-REVIEWER-V4-ARCHITECTURE-SPIKE-001`；全新 V4 chain，不是 Repair 3。
派工對象｜`gpt-5.6-sol`、`high`；架構與 executable POC。
任務目的｜選定不依賴同 UID 可讀 token 檔的最小 single-shot supervisor／ledger 架構。
可改範圍｜一份架構文件、一個隔離 probe／POC、對應 tests與 spike evidence。
驗收證據｜V3 exploit RED、三方案實測矩陣、選型決策、可交付 implementation contract。

## 啟動 Gate

- 獨立 clean worktree；HEAD 為只含本卡的 provisioning commit，父鏈基於 blocked V3 後的 clean main。
- 完整讀取 V3 recovery `review.md`、`reviewer_probes.py`、Repair 2 evidence與使用者提供的 2026-07-21 官方文件／開源盤點。
- 只以 `git show f6a86a5...` 研究 V3 candidate；不得 cherry-pick或修改 V3 code。
- 先重現同 UID token discovery＋foreign terminal＋target spawn=1；不能重現即 BLOCKED。

## 根因與不可變限制

- 同一 OS UID 對同一 filesystem tree沒有真正的 discretionary isolation；0600 token檔不是同UID capability boundary。
- V4 不得宣稱能阻止可任意掃描／改寫同UID filesystem的惡意程序，除非實際採不同UID、sandbox或kernel-enforced boundary並以probe證明。
- V4 必須防正常 application-level non-owner writer、重複completion、partial ledger、錯binding與 accidental concurrency；raw filesystem attacker屬明列的out-of-scope tamper，必須可被外部anchor／replay偵測，不得假稱預防。
- 每 operation仍為0/1 external Gemini CLI process；CLI missing/preflight=0，fork/spawn成功後success/nonzero/timeout=1。provider internal calls保持unknown。

## 必比三方案

### A｜Parent-held in-memory capability＋single trusted writer

- capability只存在parent memory，不落盤、不放env／argv／stdin、不傳入Gemini child。
- 只有supervisor擁有record writer；child只回stdout/stderr/exit，不持records path或writer API authority。
- 實測正常跨process writer、token discovery、raw path write與parent crash邊界。

### B｜Inherited FD broker＋append-only event ledger

- parent預先open append-only／exclusive ledger FD；只傳給最小trusted broker，設定close-on-exec，Gemini process不繼承。
- 分離 logical operation、broker/fork attempt、Gemini CLI process start與terminal event；不可把task attempt當provider invocation。
- 實測preflight missing、exec failure、spawn後parent crash、partial frame、duplicate event、foreign writer與replay completeness。

### C｜Kernel-enforced isolation

- 評估不同UID、macOS sandbox／container或等價邊界是否能真正阻止same-user raw filesystem mutation。
- 列出部署、可攜性、權限、維運與回退成本；除非A/B無法滿足誠實contract，否則不預設採重方案。

## 開源方法映射

- Temporal：只借 logical invocation／attempt／failure metadata分層，不導入runtime。
- Dagster：借 event replay＋terminal completeness，不把event log當防惡意filesystem的安全邊界。
- OpenAI Agents SDK：借 generation／tool span分帳，不依賴其provider abstraction保存CLI raw bytes。
- LangGraph：借 per-item local identity與fan-out/fan-in，不採其at-least-once node語意作Gemini process計數。
- PydanticAI／Gemini structured output：只借typed local validation，不使用automatic retry解決transport attribution。

## POC 與決策要求

- `agy_gemini_v4_architecture_probe.py`必須是隔離POC，不被production import。
- 產出固定JSON matrix，至少包含：preflight missing、success、nonzero、timeout、same-UID token discovery、normal non-owner、raw filesystem tamper、duplicate/partial event、parent/broker crash模擬、replay completeness。
- 每方案標示 `PREVENTED / DETECTED / OUT_OF_SCOPE / UNSUPPORTED`；不得把detected寫成prevented。
- 選型需給decision drivers、淘汰理由、threat boundary、state/event schema、caller API、migration steps、rollback、implementation allowlist與review probes。
- 優先最小架構；禁止直接新增Temporal、Dagster、LangGraph、PydanticAI等依賴。

## 驗證與交付

- 測試只能用fake executable／local subprocess，不呼叫Gemini／HTTP／外部model。
- 跑focused tests、py_compile、同一POC至少兩次確認deterministic matrix、allowlist、privacy/secret/raw path/`[DBG-]`、`git diff --check`。
- evidence至少`root-cause.md`、`options-matrix.json`、`verification.txt`、`decision.md`。
- 建立單一 architecture-spike candidate commit，狀態只能 `READY_FOR_REVIEW` 或 `BLOCKED`。
- 不得自行進production implementation、整合、恢復內容線或宣稱V4 GO。
