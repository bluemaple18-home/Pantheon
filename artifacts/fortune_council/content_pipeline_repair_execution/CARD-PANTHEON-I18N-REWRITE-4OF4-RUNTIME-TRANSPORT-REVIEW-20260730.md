---
card_id: CARD-PANTHEON-I18N-REWRITE-4OF4-RUNTIME-TRANSPORT-REVIEW-20260730
chain_id: pantheon-i18n-rewrite-4of4-runtime-stability-p0-20260730
parent_card_id: CARD-PANTHEON-I18N-REWRITE-4OF4-RUNTIME-TRANSPORT-IMPLEMENTATION-20260730
role: reviewer
cycle: 1
status: CARD_DRAFTED
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: Candidate 改動 Publisher runtime identity、LaunchAgent contract、provider failure taxonomy 與 retry idempotency；錯判會阻斷 production publisher 或誤耗語意修復，需 strict maker/checker 分離。
project_id: local-0020d4379451d545eb08362962f1def0
repo_identity: github.com/bluemaple18-home/Pantheon
required_source_kind: commit
required_source_sha: b7f4b0f1bf1c40f3c62e1d65038a0b9011c4c4ad
required_direct_parent: 7c0ce9f637ade2684751c6c1938999f20476d1fa
implementation_thread_id: 019fb17f-adbb-7220-a670-07fd1c0d8196
ownership: independent review of P0-A runtime identity and P0-B transport retry candidate
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-I18N-REWRITE-4OF4-RUNTIME-TRANSPORT-REVIEW-20260730/
created_at: 2026-07-30 Asia/Taipei
---

# Pantheon Runtime／Transport P0 Independent Review

## Role and stop boundary

你是本 chain 唯一 Reviewer。只審查 candidate
`b7f4b0f1bf1c40f3c62e1d65038a0b9011c4c4ad`，不得修改 production code、tests、
Implementation evidence 或 LaunchAgent template。只可新增本 Review 專屬 evidence，
並交付單一 Review evidence commit。

不得呼叫 provider、push、deploy、publish、安裝 LaunchAgent、接觸 production queue／
ledger，亦不得自行建立 Repair、replacement 或其他 task。

## Root question

此 candidate 是否確實：

1. 以封閉 immutable runtime manifest／digest 讓 content-only main advance 繼續運作，
   同時在 runtime path、membership、bytes 或 digest漂移時 fail closed？
2. 以獨立 bounded transport budget處理 provider／payload failure，schema-valid
   payload前不消耗 semantic repair？
3. 在 retry時維持 logical request identity與 idempotency，且不產生 candidate、
   approval、apply、publish、ledger等副作用？

## Reviewed lineage

- Base：`7c0ce9f637ade2684751c6c1938999f20476d1fa`
- Reviewed candidate：`b7f4b0f1bf1c40f3c62e1d65038a0b9011c4c4ad`
- Candidate direct parent必須精確等於 base。
- Candidate changed files：
  - `ops/launchd/com.pantheon.agy-content-publisher.plist.example`
  - `scripts/agy_content_publisher.py`
  - `scripts/agy_gemini_outbox.py`
  - `scripts/agy_gemini_runner.py`
  - `scripts/agy_seo_copy_pipeline.py`
  - `scripts/install_agy_content_publisher_launchd.sh`
  - `tests/test_agy_content_publisher.py`
  - `tests/test_agy_gemini_outbox.py`
  - `tests/test_agy_multilingual_pipeline.py`
  - Implementation evidence

## Spec axis

逐條核對 Implementation 卡 `SC-001`、`SC-002`、`SC-003`：

- runtime identity以 bytes／membership為 authority，不以整個 repo HEAD相等冒充。
- content-only `origin/main` descendant可繼續下一輪。
- runtime change、manifest membership或digest mismatch拒絕舊 actor。
- `CLI_NONZERO`、auth、quota、network、model unavailable、malformed／schema
  failure有封閉且可觀測分類。
- schema-valid payload前 semantic attempt／repair budget不前進。
- retry bounded且 logical request identity不變；queue attempt可區分但不得導致重複
  provider／candidate／approval／apply／publish副作用。
- capability probe不得攜帶文章 payload，也不得自證正式內容成功。

## Standards and risk axis

- 檢查 LaunchAgent argument index、template與CLI parser是否精確一致。
- 檢查 runtime manifest path set是否完整、排序 deterministic、缺檔與不安全 path
  fail closed，且不允許 digest取代 runtime ancestry／transaction ordering。
- 檢查 failure receipt schema向後相容、closed fields、敏感資料不落盤。
- 檢查 runner在寫 inbox前完成 schema validation，且失敗不留下 ambiguous inbox／
  failed雙寫狀態。
- 檢查 transport retry是否會把非 retryable auth／quota／model錯誤誤重試，或讓
  JSON/schema-invalid payload改變 logical identity。
- 檢查既有 new／rewrite／translation lane、V4 broker、coordinator與 reviewer
  cutover沒有回歸。

## Required fresh verification

至少 fresh執行：

```text
.venv/bin/python -m pytest \
  tests/test_agy_content_publisher.py \
  tests/test_agy_seo_copy_pipeline.py \
  tests/test_agy_multilingual_pipeline.py \
  tests/test_agy_gemini_outbox.py \
  tests/test_agy_gemini_transport_probe.py \
  tests/test_agy_gemini_coordinator.py \
  tests/test_agy_gemini_v4_broker.py \
  tests/test_agy_gemini_reviewer_cutover.py -q
git diff --check 7c0ce9f637ade2684751c6c1938999f20476d1fa b7f4b0f1bf1c40f3c62e1d65038a0b9011c4c4ad
```

若 worktree缺 `.venv`，依專案 `uv + .venv` 規範做 bounded prepare；不得下載新工具。
CodeGraph在 source decision前先查；若此 worktree仍無法 prepare，記錄
`CONTEXT_DEGRADED` 後限域讀 reviewed diff與其 entry points。

## Verdict contract

- 只有具體、可重現且落在本 candidate scope的 P0／P1 finding可 `REVIEW_NO_GO`。
- P2／P3記為 residual risk／backlog，不得阻擋。
- Finding必須包含穩定 ID、severity、`path:line`、觸發條件、風險、重現／證據與
  bounded修法。
- Re-review只能驗原 P0／P1與 regression，不得移動球門。
- 無未解 P0／P1時輸出 `REVIEW_GO`；不得宣稱 ACCEPTED、INTEGRATED或CLOSED。

## Delivery format

- Reviewed candidate與direct parent
- Spec-axis verdict
- Standards-axis verdict
- Findings（若無，明確寫 none）
- Fresh verification commands/results
- Residual risks
- Review evidence commit SHA
