# Repair-1 最終 Re-review

## Verdict

- status: `REVIEW_GO`
- card_id: `CARD-PANTHEON-LEGACY-REWRITE-QUALITY-CONTINUATION-REVIEW-20260729-RETRY-1`
- chain_id: `PANTHEON-LEGACY-REWRITE-QUALITY-CONTINUATION-REPAIR-20260729`
- reviewer_thread_id: `019fae60-82c5-74c3-8033-03202772980a`
- reviewed_candidate: `3570395faab289dd9ab824a2107bc0bd2d3625bb`
- required_direct_parent: `a243edacd981b8f28c257b040a41a121efc34b64`
- verdict_basis: 未發現 P0／P1；前次 semantic false-approve 與 rewrite entrypoint 漂移均已封閉。

## Provenance and boundary

- Re-review 開始時 Reviewer worktree HEAD 精確為 `a243edacd981b8f28c257b040a41a121efc34b64`、worktree clean、git-dir 無 `index.lock`。
- Candidate object 存在，direct parent 精確為 required parent。
- 已安全 detached 切到 reviewed candidate；切換後 worktree clean，未讀寫主工作區 dirty changes。
- Candidate diff 僅包含既有 Repair allowlist 三檔：
  - `scripts/agy_seo_copy_pipeline.py`
  - `tests/test_agy_seo_copy_pipeline.py`
  - `artifacts/fortune_council/content_pipeline_repair_execution/evidence/CARD-PANTHEON-LEGACY-REWRITE-OBJECTIVE-AUTHORITY-REPAIR-1-20260729/verification.md`
- Diff 統計：3 files changed，519 insertions，47 deletions。
- CodeGraph 在 Reviewer worktree 未初始化；依專案規則降級為限域 `git diff`、`rg`、caller source inspection 與 fresh runtime seam，未初始化索引。

## Finding matrix

| Severity | Count | Disposition |
|---|---:|---|
| P0 | 0 | 無 |
| P1 | 0 | 無 |
| P2 | 0 | 無 |
| P3 | 0 | 無 |

未發現阻塞問題。

## Spec axis

### 1. Strict rewrite schema 明確拆分 semantic 與 objective authority

PASS。

`scripts/agy_seo_copy_pipeline.py:3107` 的 rewrite-only provider schema將每篇 Reviewer output 鎖為四個 exact fields：

- `slot`
- `semantic_verdict`
- `semantic_findings`
- `objective_observations`

`scripts/agy_seo_copy_pipeline.py:3153` 的 `hydrate_rewrite_review()` 執行下列不變量：

- semantic verdict 只能是 `APPROVE`／`REJECT`；
- semantic APPROVE 不得帶 semantic findings；
- semantic REJECT 必須至少有一筆 semantic finding；
- objective observation 必須為 exact `code`／`message`，且 code 必須位於 closed machine-owned allowlist；
- final review 只由 semantic verdict/findings hydrate；objective observations 不得推導或改寫 final verdict。

### 2. Semantic REJECT 即使誤標 objective code 也不可洗成 APPROVE

PASS。

Fresh hostile test以 `semantic_verdict=REJECT`、semantic finding code=`BODY_SHAPE_VIOLATION`、message 為搜尋意圖與文化定論問題；final review完整保留該 finding 並維持 REJECT。

舊 code-only reconciler 不再介入 rewrite path；它只保留給 create 的既有 machine-owned reconciliation。

### 3. 六個 rewrite hydration 入口共用同一 authority helper

PASS。

限域 caller inspection 確認六個 rewrite provider review入口皆使用 `rewrite_external_review_schema()` 與 `hydrate_rewrite_review()`：

| Entrypoint | Hydration seam |
|---|---:|
| `run_writer_reviewer()` | `scripts/agy_seo_copy_pipeline.py:3679` |
| `run_rewrite_repair()` | `scripts/agy_seo_copy_pipeline.py:3930` |
| `run_rewrite_release_generation()` | `scripts/agy_seo_copy_pipeline.py:4338` |
| `review_rewrite_release_final()` | `scripts/agy_seo_copy_pipeline.py:4424` |
| `run_rewrite_repair_closure()` | `scripts/agy_seo_copy_pipeline.py:4981` |
| `review_existing_candidate()` | `scripts/agy_seo_copy_pipeline.py:5052` |

同時確認 main runner、isolated runner、release generation 與 existing-candidate 在 deterministic 非空時不呼叫 Reviewer；review-only 與 closure entrypoint 原有 deterministic-clean 前置條件維持。

### 4. Create／optimize／translation schema 與行為

PASS。

- `external_review_schema()` 的既有 `slot/verdict/findings` contract 未改。
- create 繼續使用原 schema、`hydrate_review()` 與既有 reconciliation。
- optimize 繼續使用原 schema與 `hydrate_review()`。
- multilingual writer/reviewer 兩入口仍明確使用 `external_review_schema()` 與 `hydrate_review()`。
- Fresh core、coordinator/publisher 與 multilingual suites 全數通過。

### 5. 舊／cached payload fail-closed 與 provider schema 相容

PASS，並保留 operational residual risk。

Fresh compatibility seam：

- 舊 rewrite payload `{slot, verdict, findings}` 傳入 `hydrate_rewrite_review()`，立即得到 `ValueError: external rewrite review fields are strict`。
- isolated runner 預置舊格式 cached `external-review.json` 時，attempt 1 轉為 `invalid_reviewer_json:ValueError` hard REJECT；舊 payload 不會被解讀成 APPROVE。
- 後續只有 fresh Reviewer 以新 schema 回傳 semantic APPROVE，run 才能 final APPROVE。

Provider schema只使用既有 provider path 已採用的 object、array、string、enum、required 與 `additionalProperties: false` primitive；targeted test亦核對四個 exact fields。未引入 `$ref`、union 或自訂 keyword。

### 6. Fresh suites 與 diff check

PASS。完整結果見下節。

## Standards axis

- Correctness：PASS；semantic verdict 不再由 objective code推導，deterministic authority仍優先。
- Regression：PASS；六個 rewrite entrypoint收斂至同一 helper，create／optimize／translation維持原 contract。
- Security／privacy：PASS；diff 未擴張 provider credential、apply、deploy 或 publish authority。
- Testing：PASS；包含 hostile mislabel、objective false observation、deterministic short-circuit、isolated runner與 existing-candidate seams。
- Maintainability：PASS；rewrite schema與 hydration集中為單一 reusable boundary。

## Fresh verification

Candidate runtime 來自同 SHA implementation worktree 的既有 `.venv`；所有 command cwd 保持 Reviewer worktree，未建立或修改本 worktree `.venv`。

| Command | Result |
|---|---|
| `<implementation-worktree>/.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py -q -k 'rewrite_ignores_false_body_shape or rewrite_semantic_reject_survives or rewrite_malformed_machine_owned or rewrite_semantic_rejection_keeps or rewrite_deterministic_reject_never or rewrite_unknown_reviewer or batch_002_isolated_runner or review_existing_rewrite or create_machine_length_repair_is_field_bounded'` | PASS：12 passed，102 deselected in 0.27s |
| `<implementation-worktree>/.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py -q` | PASS：114 passed in 54.39s |
| `<implementation-worktree>/.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py tests/test_agy_content_publisher.py -q` | PASS：99 passed，1 existing non-blocking warning in 15.78s |
| `<implementation-worktree>/.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py -q` | PASS：19 passed in 0.07s |
| `git diff a243edacd981b8f28c257b040a41a121efc34b64..3570395faab289dd9ab824a2107bc0bd2d3625bb --check` | PASS：exit 0，無輸出 |
| Temporary legacy／cached compatibility seam | PASS：舊 payload hard REJECT；只有 fresh new-schema Reviewer 可核准 |

唯一 warning 為既有 `DeprecationWarning: invalid escape sequence '\\/'`，不在 candidate diff。

## Residual risk

- 真實 provider 未在本 Reviewer 卡執行；schema compatibility 結論來自 provider schema subset、transport contract 與 test double，不是 production provider receipt。
- Isolated runner 遇到舊 cached review 時會安全地 hard-reject該 attempt，但仍消耗一次 bounded content repair，之後才接受 fresh new-schema review。這是 migration operational cost，不會使用舊 payload false approve。
- 新 objective observation同義 code 若未列入 closed allowlist，會 fail closed 成 invalid review；可能 false reject，但不會 false approve。

## Acceptance required before production

1. 用 production-owned transport執行一個 non-publishing rewrite acceptance，保存新四欄 schema 的原始 Reviewer payload 與 operation receipt。
2. 核對 semantic REJECT、objective observation、unknown observation與 cached legacy payload在真實 transport下仍符合本次 fail-closed結果。
3. 未完成上述 acceptance 前，不得把本 code-review verdict外推為 production publish approval。

## Stop boundary

本 final re-review 只交付 `REVIEW_GO` evidence。Reviewer 未修改 candidate、production code、tests 或 config；未 push、deploy、publish、整合或接觸真實 provider。
