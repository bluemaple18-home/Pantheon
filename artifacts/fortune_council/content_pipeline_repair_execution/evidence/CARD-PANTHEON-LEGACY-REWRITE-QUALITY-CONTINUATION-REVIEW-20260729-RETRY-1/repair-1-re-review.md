# Repair-1 定向 Re-review

## Verdict

- status: `REVIEW_NO_GO`
- card_id: `CARD-PANTHEON-LEGACY-REWRITE-QUALITY-CONTINUATION-REVIEW-20260729-RETRY-1`
- chain_id: `PANTHEON-LEGACY-REWRITE-QUALITY-CONTINUATION-REPAIR-20260729`
- reviewer_thread_id: `019fae60-82c5-74c3-8033-03202772980a`
- reviewed_candidate: `7cf63b5e40a1f5fd0c8ce3c05fe1f17e11274c47`
- required_direct_parent: `ca1e7bf89cb32e8d50aa933dfa125ed2280e51a2`
- verdict_basis: 2 個可重現 P1；candidate 尚未封閉 semantic false-approve，且隔離 rewrite runner 仍會浪費唯一 repair。

## Provenance and boundary

- Re-review 前 Reviewer worktree clean，git-dir 無 `index.lock`。
- 已安全 detached 切到 reviewed candidate；切換後 HEAD 與 direct parent 均精確符合契約，worktree clean。
- Candidate diff 僅包含 allowlist 三檔：
  - `scripts/agy_seo_copy_pipeline.py`
  - `tests/test_agy_seo_copy_pipeline.py`
  - `artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-LEGACY-REWRITE-OBJECTIVE-AUTHORITY-REPAIR-1-20260729/verification.md`
- Diff 統計：3 files changed，537 insertions，6 deletions。
- 未讀寫主工作區 dirty changes。
- CodeGraph 在 Reviewer worktree 未初始化；依專案規則降級為限域 `git diff`、`rg`、caller source inspection 與 fresh runtime seam，未初始化索引。

## Findings

### [P1] Allowlisted objective code 可把真正 semantic REJECT 翻成 APPROVE

- path: `scripts/agy_seo_copy_pipeline.py:3108`
- related promotion: `scripts/agy_seo_copy_pipeline.py:3115`
- caller: `scripts/agy_seo_copy_pipeline.py:3548`

觸發條件：

1. rewrite candidate 的 deterministic machine gate 為綠；
2. Reviewer 確實發現搜尋意圖、語意品質或安全問題；
3. Reviewer 將該問題錯標成 closed allowlist 內的 objective code，例如 `BODY_SHAPE_VIOLATION`；
4. 該筆是唯一 finding。

Fresh hostile seam 使用以下 Reviewer finding：

```json
{
  "code": "BODY_SHAPE_VIOLATION",
  "message": "文章完全誤解搜尋意圖，且把文化反思寫成個人定論"
}
```

實際結果：finding 被刪除，原始 `REJECT` 被改為 `APPROVE`。

風險：

- Reconciler 只信任 code label，不保留獨立 semantic verdict；prompt 只是模型指令，不能阻止模型誤分類。
- Closed allowlist 降低攻擊面，但 `BODY_SHAPE_VIOLATION` 等廣義 code 仍足以吞掉真正語意問題。
- 這會直接移除 Reviewer 的 semantic rejection authority，使 production 內容 false approve，違反本 chain root contract。

建議修法：

- 將 machine observation 與 semantic verdict 分成不同、嚴格 schema 欄位；例如 Reviewer 必須輸出獨立 `semantic_verdict`／`semantic_findings`。
- Reconcile 只能移除 objective observations，不能因 findings 變空就推導 semantic APPROVE；只有 Reviewer 明確 semantic-approve 時才可核准。
- 新增 hostile regression：semantic message 故意搭配每一個 allowlisted objective code，都不得把 semantic REJECT 翻成 APPROVE。

### [P1] 隔離 `run_rewrite_repair()` 未套 objective reconciliation

- path: `scripts/agy_seo_copy_pipeline.py:3783`
- missing seam after hydrate: `scripts/agy_seo_copy_pipeline.py:3798`
- repair targeting: `scripts/agy_seo_copy_pipeline.py:3813`

觸發條件：

1. `run_rewrite_repair()` 的 aggregate deterministic gate 為綠；
2. Reviewer 對其中一篇錯誤回報 `BODY_SHAPE_VIOLATION`；
3. runner 使用 locked `max_repairs=1`。

Fresh hostile seam 結果：

```text
writer_calls=6
reviewer_calls=2
internal_repairs_used=1
final_verdict=REJECT
final_findings=[BODY_SHAPE_VIOLATION]
```

初始五個 Writer 後，錯誤 objective finding 令第一篇多跑一次 Writer，唯一 internal repair 被消耗；第二次相同 false finding 仍終局 REJECT。

風險：

- Item 1 的修復只接到 `run_writer_reviewer()`，沒有覆蓋同為 `rewrite_existing_body` 的既有隔離 runner。
- 既有 runner 仍重現本 Repair-1 要消除的 repair-budget 浪費與 false reject，形成明確邏輯漂移。

建議修法：

- 在 `run_rewrite_repair()` deterministic-green 的 `hydrate_review()` 後套用同一個可信 objective reconciliation。
- Reconciliation 必須同時採納前一 finding 的 semantic-verdict 分離設計，不能直接複製目前會 false approve 的 promotion 邏輯。
- 新增 aggregate runner regression：五篇 machine-green、單篇 false objective finding 時，Writer 應為 5 次、Reviewer 1 次、final APPROVE、internal repair 0。

### [P2] `review_existing_candidate()` 的 rewrite path 仍保留 false objective finding

- path: `scripts/agy_seo_copy_pipeline.py:4892`
- missing seam after hydrate: `scripts/agy_seo_copy_pipeline.py:4901`

觸發條件：既有 rewrite candidate machine-green，但 Reviewer 回報 allowlisted false objective finding。

風險：此路徑不會浪費 Writer repair，但會產生與主 runner 不同的 false REJECT，讓相同 candidate 依入口得到不同 verdict。

建議修法：把修正後、保留 semantic authority 的 reconcile helper 套到所有 rewrite review entrypoint，並新增 existing-candidate regression。

## Non-findings

### Deterministic authority

- Candidate 的 deterministic 非空路徑仍 short-circuit Reviewer。
- Fresh targeted test證實真正 `paragraph_length` failure 時 Writer 1 次、Reviewer 0 次、final REJECT。
- Reviewer 無法覆蓋 deterministic finding。

### Correctly labeled semantic and unknown codes

- `search_intent_mismatch` 保留並在 `max_repairs=0/1/2` 下維持 bounded REJECT。
- Unknown code 維持 fail closed。
- Malformed finding 透過 strict `validate_review()` 轉成 `invalid_reviewer_json:ValueError` hard REJECT。

### Global `validate_review()` compatibility

- `external_review_schema()` 本來就將 finding 鎖為 exact `code`／`message`，新增 runtime validation 與既有 model transport schema 一致。
- create／optimize／translation 的內部 review payload 皆使用 `code`／`message`；本次 fresh core、publisher 與 multilingual suites 全數通過。
- 限域 repo artifact 搜尋找到 189 個含 `candidate_sha256` 的 review-like JSON；未找到同時含 `severity`、`field`、`category` 或 `authority` 類 finding extra field 的檔案。
- `agy_gemini_transport_probe` 的 `severity` finding 使用不同 probe schema，未呼叫本 pipeline 的 `validate_review()`。

## Fresh verification

Candidate runtime 來自同 SHA implementation worktree 的既有 `.venv`；所有 command cwd 保持 Reviewer worktree，未建立或修改本 worktree `.venv`。

| Command | Result |
|---|---|
| `<implementation-worktree>/.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py -q -k 'rewrite_ignores_false_body_shape or rewrite_malformed_machine_owned or rewrite_semantic_rejection_keeps or rewrite_deterministic_reject_never or rewrite_unknown_reviewer'` | PASS：7 passed，104 deselected in 0.16s |
| `<implementation-worktree>/.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py -q` | PASS：111 passed in 55.92s |
| `<implementation-worktree>/.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py tests/test_agy_content_publisher.py -q` | PASS：99 passed，1 existing non-blocking warning in 15.97s |
| `<implementation-worktree>/.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py -q` | PASS：19 passed in 0.07s |
| `git diff ca1e7bf89cb32e8d50aa933dfa125ed2280e51a2..7cf63b5e40a1f5fd0c8ce3c05fe1f17e11274c47 --check` | PASS：exit 0，無輸出 |
| Temporary hostile semantic-mislabel seam | FAIL acceptance：REJECT 被翻成 APPROVE |
| Temporary isolated-runner false-objective seam | FAIL acceptance：消耗 1 repair，終局 REJECT |

完整 suite 綠燈不能抵銷 hostile seam 已重現的 P1。

## Spec axis

1. Machine-green rewrite 忽略客觀 false finding且不浪費 repair：FAIL；只修主 runner，隔離 runner 仍失敗。
2. Deterministic 真實失敗必拒絕且 Reviewer 不得覆蓋：PASS。
3. 語意／搜尋意圖／安全／錯別字／模板感與 unknown code 保留：PARTIAL；正確 code 可保留，但錯標 allowlisted code 會被刪除。
4. False-approve 防線：FAIL；prompt 與 closed allowlist 不足以防止錯標後 promotion。
5. 全域 strict finding schema 跨 mode：PASS；未測得 create／optimize／translation regression。
6. Diff allowlist與 fresh suites：PASS。

## Standards axis

- Correctness：FAIL；2 個 P1 可重現。
- Regression：FAIL；`run_rewrite_repair()` 與 `review_existing_candidate()` 未跟主 runner 同步 authority policy。
- Security／privacy：PASS；diff 未擴張 provider、secret、apply 或 deploy authority。
- Testing：FAIL；現有 tests 只覆蓋正確分類，缺 hostile mislabel 與隔離 runner false-objective seam。
- Maintainability：PARTIAL；closed allowlist 集中，但 reconciliation 未收斂成所有 rewrite entrypoint 共用的不變量。

## Minimal Repair allowlist

- `scripts/agy_seo_copy_pipeline.py`
- `tests/test_agy_seo_copy_pipeline.py`
- 本 chain 下一輪 Repair／Review evidence

禁止擴張至 config、文章、queue、ledger、provider、deploy、publish 或 live runtime。

## Stop boundary

本 re-review 只交付 `REVIEW_NO_GO` evidence。Reviewer 未修改 candidate、production code、tests 或 config；未 push、deploy、publish、整合或接觸真實 provider。
