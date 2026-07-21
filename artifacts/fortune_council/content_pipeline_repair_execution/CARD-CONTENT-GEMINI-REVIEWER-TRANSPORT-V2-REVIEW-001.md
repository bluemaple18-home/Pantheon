---
card_id: CARD-CONTENT-GEMINI-REVIEWER-TRANSPORT-V2-REVIEW-001
chain_id: CONTENT-GEMINI-REVIEWER-TRANSPORT-V2-001
status: CARD_DRAFTED
review_kind: full
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
model_reason: 固定候選跨 26 檔並修改 production Gemini transport、identity、receipt 與 accounting；錯配或漏記會污染三條內容線，需高風險獨立審查
ownership: 唯讀審查固定 Transport V2 candidate 的 spec、correctness、regression、privacy 與 test gaps
base_sha: 22b7d44a8bdee8d64aaea6addeaa882817141bbc
candidate_sha: 96d3a3a17b3e97f2f5e099f1c739ad6c84e7bc0c
reviewed_commit_required: 96d3a3a17b3e97f2f5e099f1c739ad6c84e7bc0c
implementation_thread_id: 019f83ad-1be1-7a91-94a4-fe0e4e33b57a
allowlist:
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_transport_v2_review_001/**
forbidden_scope:
  - candidate code, tests, docs or implementation evidence
  - app/** and all article, registry, metadata and publishing files
  - Gemini CLI, HTTP or external model invocation
  - merge, push, deploy, publish, production or content-line recovery
verification:
  - fixed-range diff and allowlist audit
  - adversarial offline probes for identity, immutable receipts and event replay
  - focused tests, stored corpus replay, py_compile and git diff --check
  - privacy and evidence integrity scan
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_reviewer_transport_v2_review_001/
thread_id: PENDING
thread_status: CARD_DRAFTED
worktree_path: PENDING
cwd: PENDING
---

# CARD-CONTENT-GEMINI-REVIEWER-TRANSPORT-V2-REVIEW-001｜Transport V2 獨立審查

## 五行派工卡

任務 ID｜`CARD-CONTENT-GEMINI-REVIEWER-TRANSPORT-V2-REVIEW-001`；固定審查 `22b7d44..96d3a3a`。
派工對象｜`gpt-5.6-sol`、`high`；full review，只審不修。
任務目的｜判定 V2 是否真正封閉 stale receipt、cross-slot attribution、terminal completeness 與 partial-failure accounting，且未引入新的 privacy／regression 風險。
可改範圍｜只可新增本 Review evidence；candidate 與 production code 全部唯讀。
驗收證據｜path:line findings、adversarial probes、Spec／Standards axes、GO／NO_GO 與固定 reviewed SHA。

## 啟動 Gate

- worktree 必須獨立、clean，HEAD 必須是只含本 Review 卡的 provisioning commit，HEAD^ 精確為 candidate `96d3a3a17b3e97f2f5e099f1c739ad6c84e7bc0c`。
- 實際 reviewed range 固定為 `22b7d44a8bdee8d64aaea6addeaa882817141bbc..96d3a3a17b3e97f2f5e099f1c739ad6c84e7bc0c`；不得把 provisioning card commit 算入 candidate。
- implementation evidence、stored corpus 與 12 個 receipt/gate files 必須可讀；任一 SHA、scope 或 evidence 不一致立即 `BLOCKED`。

## 必審風險

### Correctness

- 每個 Reviewer process 是否真的只有一個 caller-bound target；model payload、judgment、mapper 或 batch context 是否仍有任何可改變 identity／slot 的旁路。
- accepted-code contract 是否完整 target-bound；global code/message、deterministic-only code、unknown／duplicate code 是否可能附錯文章仍通過。
- success、nonzero exit、timeout、outer envelope failure、inner parse/schema/rubric failure 是否恰好各產生一個屬於當次 invocation 的 terminal receipt；不得讀取 stale shared state。
- stdout SHA／bytes 是否只來自同 invocation 的實際 bytes；unavailable 是否維持 null，不被後續 event 或 fallback 補寫。
- terminal receipt 是否不可變；append-only gate event 是否能被重複、缺漏、覆寫或用相同 invocation ID 混淆。
- receipt replay 對 multi-item 第 k 篇失敗、resume、reviewer-only rounds、closure、success/error/pending 是否精確，且不把 batch completion、attempt、retry、review round、writer/reviewer invocation 混帳。
- `provider_model_calls` 必須始終為 `unobservable/unknown`，外部 process 數不得被宣稱為 provider call 數。

### Strict parsing and schema

- 任一層 duplicate key、trailing prose、markdown fence、unknown field、錯誤型別與 contradictory verdict 都 fail closed。
- `APPROVE ⇔ hard_failure=false + findings=[]`；`REJECT ⇔ hard_failure=true + findings>=1`。
- finding code/message trim 後非空；unknown／duplicate code fail closed；mapper 不得修補或猜測。

### Regression and privacy

- Writer path、既有 outbox/runner CLI contract、舊 manifest／receipt consumers、resume 行為與 deterministic gates 不得被意外破壞。
- evidence 與 persisted receipts 不得含 prompt、raw stdout/stderr、response content、secret/token、PII、本機絕對路徑、executable path 或 argv text。
- UUID/timestamp 不得使 stored corpus 無法離線重算；replay 必須驗證 uniqueness、terminal completeness、request/candidate/item binding。

## 必做 adversarial probes

1. success 後接 outer-envelope failure、inner parse failure、timeout、nonzero exit，逐一驗證沒有 stale SHA／bytes。
2. A/B cross-slot：只在 B 的問題，以 global code、B-only message、deterministic code、交換 candidate SHA 等方式嘗試讓 A 被 REJECT。
3. duplicate terminal receipt、duplicate gate event、missing terminal、gate-before-terminal、相同 invocation ID 不同 item/attempt、未知 terminal status。
4. 第 1／中間／最後一篇失敗；resume 只重送失敗 identity；成功 identity 不重送；replay counts 精確。
5. nested duplicate JSON key、empty/blank message、unknown/duplicate codes、所有 verdict/hard_failure/findings 矛盾組合。

## 驗證與結論

- 不呼叫 Gemini CLI；只離線重算既有 6-process corpus，確認 APPROVE／REJECT 各 3/3、無 retry、第 7 次不存在、`provider_model_calls=unobservable/unknown`。
- 跑 focused affected tests、必要 adversarial probe、py_compile、fixed-range allowlist、privacy scan 與 `git diff --check`。可跑 full suite，但不得把已知 Ziwei baseline failures寫成全綠。
- Findings 依 P0→P3，每筆含 path:line、觸發條件、證據、風險、建議修法、validation gap、confidence。
- 分列 Spec axis、Standards axis、Testing gaps、Residual risks。
- 任一 P0/P1/P2、production safety risk、SHA/scope/evidence 不一致或關鍵 invariant 無法重現：`NO_GO`。全部關閉才可 `GO`。
- 建立單一 Review evidence commit，回完整 SHA；不得修改 candidate、修復 finding、merge、push、deploy、publish或恢復內容線。
