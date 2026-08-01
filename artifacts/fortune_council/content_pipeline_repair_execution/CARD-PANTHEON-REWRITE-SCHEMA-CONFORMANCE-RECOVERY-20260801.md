---
card_id: CARD-PANTHEON-REWRITE-SCHEMA-CONFORMANCE-RECOVERY-20260801
chain_id: PANTHEON-REWRITE-SCHEMA-CONFORMANCE-RECOVERY-20260801
role: implementation
cycle: 1
ownership: rewrite_schema_conformance_only
status: READY_TO_DISPATCH
user_hold: false
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: Production rewrite 的核心 response-schema／重試契約連續跨目標失敗，涉及跨模組 invariant、外呼成本與錯誤放行風險；需要 strict 主線能力，但禁止擴張成四線重寫。
source_ref: origin/main
source_sha_at_card_creation: e51ac1ec34d772ab357368985677c00373e05e64
dispatch_base_ref: codex/rewrite-schema-conformance-recovery-20260801-base
dispatch_base_sha: 800fba7278b59667269743de7837ea5d579658bc
worktree: platform_assigned_independent_worktree
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/rewrite_schema_conformance_recovery_20260801
---

# CARD-PANTHEON-REWRITE-SCHEMA-CONFORMANCE-RECOVERY-20260801

## 五行派工摘要

1. 只修 `rewrite` 真實回傳反覆撞 `SCHEMA_INVALID_PAYLOAD / SCHEMA_MISMATCH` 的根因。
2. 沿用既有 V4 closed diagnostic、local validator、bounded retry 與 i18n canonicalization 經驗，不另造第二套 pipeline。
3. 不碰 `new`、`i18n-new`、`i18n-rewrite`、publisher release、文章／registry 或 production 服務。
4. 先 RED 重現跨目標長度 mismatch，再做最小修正；canonical quality gate 不得放寬。
5. 只交 candidate commit 與離線證據；不得 Gemini 外呼、push、deploy、publish 或操作 LaunchAgent。

## Root question

為什麼 production `rewrite` 已有成功 transport 與可解析 JSON object，仍在不同文章上連續被 V4 broker 以長度 schema mismatch 拒絕；如何用現有 contract seam 修好，使回傳能進入原本 deterministic validator／reviewer，而不是反覆用同一無差別 request 消耗外呼？

## 已確認事實

- 2026-08-01 10:54–11:08（Asia/Taipei）至少四個不同 rewrite run 連續終態失敗：
  - `legacy-auto-sweep-v1-personality-0029-mbti-branch-infj-ah`
  - `legacy-auto-sweep-v1-personality-0030-mbti-branch-infj-ac`
  - `legacy-auto-sweep-v1-personality-0031-mbti-branch-infj-oh`
  - `legacy-auto-sweep-v1-personality-0032-mbti-branch-infj-oc`
- 共同 failure：`V4BrokerFailure / SCHEMA_INVALID_PAYLOAD`。
- closed diagnostic 證明 transport 並未失敗：`outcome=SUCCESS`、`process_count=1`、`replay_status=COMPLETE`、`result_validation=SCHEMA_MISMATCH`。
- 已觀察的 mismatch 包含 rewrite `bodySections[*].paragraphs[*]` 的 `maxLength`；同時 `new` 曾出現 `answer.maxLength`、`description.minLength`，但本卡禁止順手修 `new`。
- credential slot 不同仍重現，因此不能把問題歸因為單一帳號。
- 其他三線與 scheduler／publisher 正常持續運轉；`i18n-new` 已真實發布 v0.3.222。本卡不得停掉或重載它們。
- 既有可沿用經驗：
  - `CARD-CONTENT-GEMINI-V4-LIMITED-ACTIVATION-DIAGNOSTIC-REPAIR-001` 已提供 privacy-safe `broker_diagnostic`，不得重寫診斷層。
  - `CARD-CONTENT-GEMINI-V4-LIMITED-ACTIVATION-003` 已證明 process success 不等於 response-schema conformance。
  - 四線修復中的 i18n 做法是：provider 邊界只承擔可保證的結構；內容完整性／唯一性／安全性由本機 deterministic gate 驗證後才 canonicalize。rewrite 若採相似分層，必須證明 canonical quality contract 完整保留。

## 需求與成功準則

### SC-REWRITE-ROOT

以 red-capable test 重現「合法 JSON object、transport success，但 rewrite 字串長度 mismatch 在 broker 邊界直接終止，原本 local validation／有原因的 bounded repair 無法接手」。

### SC-REWRITE-SEAM

找出並使用現有 seam。允許的方向只有：

- provider-facing structural schema 與 canonical local quality schema 的明確分層；或
- 使用既有 closed diagnostics 做一次有差異、可驗證的 bounded retry／repair instruction。

若兩者都需要，必須逐項 RED→GREEN，不能一次改完整流程。

### SC-REWRITE-QUALITY

- canonical rewrite paragraph／description／answer／section／body 品質門檻不得降低。
- 不得用 silent truncate、任意切字、刪段、補空話或接受 invalid candidate 過關。
- broker 放寬只可移除 provider 無法可靠保證、且會在本機重新完整驗證的 keyword；需有 equivalence test 證明 invalid candidate 仍 fail closed。
- retry 必須 bounded、帶 closed reason、生成不同 request digest；不得對同一 payload 無上限重送。

### SC-REWRITE-ISOLATION

- `new`、兩條 i18n、publisher、四線 LaunchAgent 與 production queue 行為保持不變。
- 不改文章內容、registry、metadata、sitemap、feed、prerender 或 release version。
- 不讀取／保存 raw production response、prompt、credential、完整 environment 或 CLI log；只使用 closed diagnostics 與 synthetic fixture。

### SC-REWRITE-ACCEPTANCE

Candidate 交付前至少證明：

1. RED fixture 能抓到當前跨目標 `maxLength/minLength` 失敗路徑。
2. GREEN 後，結構正確但邊界長度不符的 response 會進入既有 deterministic local gate 或有差異的 bounded repair，不再只得到無差別 broker failure。
3. 超出 canonical quality 契約的內容仍被拒絕；沒有 silent normalization。
4. 一份真正符合 canonical contract 的 rewrite fixture 可完整通過 generator → local validator → reviewer/publish eligibility 的離線接縫。
5. rewrite retry exhaustion、privacy、exactly-once、failure categorization 與其他三線 regression 測試通過。
6. `git diff --check` 通過，且 changed files 完全落在 allowlist。

## Frontier 與 blocking edges

- `SLICE-RED`：frontier；先重現與定位，`traces_to: [SC-REWRITE-ROOT]`。
- `SLICE-SEAM`：blocked by `SLICE-RED`；最小實作，`traces_to: [SC-REWRITE-SEAM, SC-REWRITE-QUALITY]`。
- `SLICE-REGRESSION`：blocked by `SLICE-SEAM`；跨 lane／privacy／retry gate，`traces_to: [SC-REWRITE-ISOLATION, SC-REWRITE-ACCEPTANCE]`。
- `SLICE-EVIDENCE`：blocked by `SLICE-REGRESSION`；candidate commit 與證據，`traces_to: [SC-REWRITE-ACCEPTANCE]`。

## Allowlist

- `scripts/agy_seo_copy_pipeline.py`
- `scripts/agy_gemini_coordinator.py`
- `scripts/agy_gemini_runner.py`
- `tests/test_agy_seo_copy_pipeline.py`
- `tests/test_agy_gemini_coordinator.py`
- `tests/test_agy_gemini_outbox.py`
- `tests/test_agy_content_publisher.py`（只允許增加離線 eligibility regression；不得改 publisher 行為）
- `tests/fixtures/agy_rewrite_schema_conformance/**`
- 本卡
- `artifacts/fortune_council/content_pipeline_repair_execution/evidence/rewrite_schema_conformance_recovery_20260801/**`

若根因要求 allowlist 外檔案，立即 `BLOCKED / SCOPE_CHANGE_REQUIRED`，不得自行擴張。

## Forbidden scope

- `scripts/agy_multilingual_pipeline.py`
- `scripts/agy_content_publisher.py`
- `scripts/agy_gemini_v4_broker.py`（closed diagnostic 已存在，不得重寫 broker）
- `ops/launchd/**`
- `app/web/**`
- 任何 production queue／state／ledger、文章、registry、metadata、sitemap、feed、redirect、prerender、版本與 changelog
- Gemini／agy 外呼、production replay、credential／登入修改
- `launchctl`、push、deploy、publish、merge、PR、tag、archive 或 worktree cleanup

## 執行契約

1. 先跑 worktree capability preflight 與 CodeGraph context；CodeGraph unavailable 才限域 `rg`。
2. 使用 root-cause-triage：先建立一個 red-capable test，再列可證偽假說；禁止先改 production code。
3. 只做能讓 RED 轉 GREEN 的最小修正，不做 schema framework 重構。
4. 若要分離 external／canonical schema，命名與測試必須清楚證明兩者責任，不得複製出第二套真相來源。
5. 若要使用 broker diagnostic 產生 repair instruction，必須 deterministic、privacy-safe、bounded，且測試 request digest 改變與 exhaustion。
6. 不得以單一 happy fixture 宣稱修好；至少覆蓋四次現場 failure 中出現的 keyword/path 類型。

## 驗證

至少執行並保存完整指令與結果：

```bash
&lt;repo-root&gt;/.venv/bin/python -m pytest -q \
  tests/test_agy_seo_copy_pipeline.py \
  tests/test_agy_gemini_coordinator.py \
  tests/test_agy_gemini_outbox.py \
  tests/test_agy_content_publisher.py
&lt;repo-root&gt;/.venv/bin/python -m py_compile \
  scripts/agy_seo_copy_pipeline.py \
  scripts/agy_gemini_coordinator.py \
  scripts/agy_gemini_runner.py
git diff --check
git status --short
```

如完整 affected suite 超過合理時間，可先 focused RED/GREEN，但 candidate commit 前仍須完成上述 affected suite；若既有無關 failure，需提供 baseline 對照，不能掩蓋。

## Evidence 交付

在 `evidence_path` 下建立：

- `root-cause.md`
- `red-green.txt`
- `verification.txt`
- `changed-files.txt`
- `privacy-scan.txt`
- `decision.md`

交付必須包含完整 candidate commit SHA、實際 changed files、測試結果與剩餘風險。只允許：

- `DELIVERED_CANDIDATE / READY_FOR_REVIEW`
- `BLOCKED`

不得宣稱 `ACCEPTED`、`INTEGRATED`、`DEPLOYED` 或 production 已修好；主線保留獨立 Review、整合、controlled canary 與最終驗收責任。

## Dispatch receipt

- dispatch_status: RUNNING
- dispatch_key: v1:cbecc6060ca39e2d6fe2dcf777313242ab74e048e6bd51682b3e22cb2542ed34
- formal_thread_id: 019fbb55-1846-7b60-a03b-bb30506733cc
- project_id: c2xpbmdzaG90OmVudl9lXzZhMTdiMzc4MTg1ODgzMmRhZWU4Njk3YzMwZmM3ZTdjCi9Vc2Vycy9tYXR0a3VvL0RvY3VtZW50cy9QYW50aGVvbg==
- worktree_path: /Users/mattkuo/.codex/worktrees/f4269d89-6ebb-4da0-9ffd-a90614e371a6/Pantheon
- main_cwd: /Users/mattkuo/Documents/Pantheon
- provisioning_source_ref: codex/rewrite-schema-conformance-recovery-20260801-base
- provisioning_source_sha: 800fba7278b59667269743de7837ea5d579658bc
- worktree_head: 800fba7278b59667269743de7837ea5d579658bc
- worktree_clean: true
- activation_state: BOUND
- activation_status: VERIFIED
- capability_preflight: PROVISIONING_GO
- code_context: NEEDS_PREPARE_IN_IMPLEMENTATION_THREAD
- gate_1: PASS
- gate_2: PASS
- gate_3-5: PENDING
