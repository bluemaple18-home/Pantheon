---
card_id: CARD-PANTHEON-REWRITE-SCHEMA-CONFORMANCE-REVIEW-20260801
chain_id: PANTHEON-REWRITE-SCHEMA-CONFORMANCE-RECOVERY-20260801
role: reviewer
cycle: 1
status: REVIEW_GO
thickness: strict
risk: high
base_sha: 800fba7278b59667269743de7837ea5d579658bc
candidate_sha: cd3833212ad64af0a1b016c7cc7206464bb8575e
formal_thread_id: 019fbbf3-d906-7501-b3df-77257f9080d7
project_id: c2xpbmdzaG90OmVudl9lXzZhMTdiMzc4MTg1ODgzMmRhZWU4Njk3YzMwZmM3ZTdjCi9Vc2Vycy9tYXR0a3VvL0RvY3VtZW50cy9QYW50aGVvbg==
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/rewrite_schema_conformance_review_20260801
---

# Rewrite schema conformance independent Review

## Dispatch binding

- Dispatch key 已與 activation token 核對；evidence 不保存 activation token。
- 正式 thread、project binding、`<repo-root>` 獨立 detached worktree 均已驗證。
- Reviewed HEAD 精確為 candidate；direct parent 精確為 base；初始狀態 clean。
- 禁止委派與另開 thread；本 Review 未使用兩者。

## Review objective

對 candidate 做獨立、可重現、唯讀程式碼審查，判定它是否安全修正 rewrite
provider schema conformance seam，同時完整保留 canonical 本機 quality gate 與其他
Lane 行為。

## Spec axis

### SC-REWRITE-ROOT

核對合法 JSON object 在 provider paragraph `minLength`／`maxLength` 邊界被提前拒絕
的根因，以及不同 section／paragraph path 的 RED-capable coverage。

### SC-REWRITE-SEAM

Provider boundary 只能移除 rewrite paragraph string 的 `minLength`／`maxLength`；
不得改 canonical schema、broker、runner、normalizer 或建立第二套 truth source。

### SC-REWRITE-QUALITY

Canonical schema、`rewrite_quality_findings`、bounded reason-bearing repair 與
publisher eligibility 必須 fail closed。禁止 silent truncate、任意切字、刪段、
補空話或接受 invalid candidate。

### SC-REWRITE-ISOLATION

不得改 `new`、`i18n-new`、`i18n-rewrite`、publisher runtime、ops、production
queue/state、文章、registry、metadata、sitemap、feed、redirect、prerender 或版本。

### SC-REWRITE-ACCEPTANCE

至少證明：

1. min/max 與不同 section／paragraph path 可重現。
2. Payload 原樣通過 provider structural schema 後進入 local gate。
3. Canonical-invalid candidate 仍被拒絕且 repair bounded。
4. Canonical-valid fixture 真走 generator、validator、reviewer 與 publisher
   eligibility 的 production seam。
5. Affected regressions、compile、diff 與 clean-state gates 通過。

## Standards axis

1. `_article_json_schema()` 每次回傳 fresh object；provider helper 的 `pop()` 不得
   污染 canonical 或後續 create/rewrite schema。
2. External schema 從 canonical schema 派生，責任清楚且沒有第二套 truth source。
3. RED/GREEN 覆蓋 min/max、不同 path、payload identity 與 local fail-closed gate。
4. Offline production seam 覆蓋 generator → validator → reviewer → publisher
   eligibility。
5. Changed files 必須完整符合 implementation allowlist；publisher 只能新增測試。
6. Evidence 不得含 raw production response、prompt、credential、完整 environment 或
   敏感 CLI log。
7. 檢查假陽性、脆弱 fixture、錯誤 monkeypatch 與 canonical mutation regression。
8. 只有 P0/P1 blocking；P2/P3 記為 residual risk。

## Required verification

```text
<repo-root>/.venv/bin/python -m pytest -q tests/test_agy_seo_copy_pipeline.py tests/test_agy_gemini_coordinator.py tests/test_agy_gemini_outbox.py tests/test_agy_content_publisher.py
<repo-root>/.venv/bin/python -m py_compile scripts/agy_seo_copy_pipeline.py scripts/agy_gemini_coordinator.py scripts/agy_gemini_runner.py
git diff --check 800fba7278b59667269743de7837ea5d579658bc..cd3833212ad64af0a1b016c7cc7206464bb8575e
git status --short
```

`.venv` 使用同一 candidate Implementation worktree 的既有 438-test environment
symlink；禁止下載 dependency。CodeGraph 記 `CONTEXT_DEGRADED`，後續只允許限域
`rg`／固定 diff 查閱。Node tests 不在本 Review required verification。

## Writable scope

- 本 Review 卡。
- `evidence_path/**`。

不得修改 candidate code、tests 或 implementation evidence。

## Forbidden

不得 Gemini 外呼、production replay、push、merge、deploy、publish、tag、
`launchctl`、修改或停止任何 Lane、清理 worktree、讀取 production raw response、
prompt、credential、完整 environment，或建立 replacement。

## Decision contract

- `REVIEW_GO`：無 P0/P1；列 evidence 與 P2/P3 residual。
- `REVIEW_NO_GO`：列可定位、可重現 P0/P1，含 path、line、失敗契約與最小修正方向。
- 不得宣稱 `INTEGRATED`、`DEPLOYED` 或 production fixed。

## Result

`REVIEW_GO`。Spec axis `PASS`；Standards axis `PASS_WITH_RESIDUAL_P2`。完整證據與
finding disposition 見 `evidence_path`。
