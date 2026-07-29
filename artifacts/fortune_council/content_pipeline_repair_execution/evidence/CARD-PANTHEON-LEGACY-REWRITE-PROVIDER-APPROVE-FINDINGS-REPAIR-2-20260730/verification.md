# Legacy rewrite provider APPROVE findings Repair-2 驗證紀錄

## 契約與 provenance

- card：`CARD-PANTHEON-LEGACY-REWRITE-PROVIDER-APPROVE-FINDINGS-REPAIR-2-20260730`
- required base：`9474db388f6c84e9e988dec3fe249aa0833cb0ef`
- worktree：`<repo-root>`
- 禁止動作：provider、push、deploy、publish、sub-agent
- 修改範圍：SEO copy pipeline、對應測試、本卡 evidence

切換前後均確認 Repair worktree clean 且無 `index.lock`；fetch 後以 detached
HEAD 精確切到 required base，未接觸主工作區 dirty changes。

## Capability 與 source context

- `worktree_capability_preflight.sh --prepare --with-codegraph`：PASS。
- CodeGraph indexed SHA：`9474db388f6c84e9e988dec3fe249aa0833cb0ef`。
- graph：285 files、3,699 nodes、3,387 edges。
- `hydrate_rewrite_review()` 的六個 callers：
  - `run_writer_reviewer`
  - `run_rewrite_repair`
  - `run_rewrite_release_generation`
  - `review_rewrite_release_final`
  - `run_rewrite_repair_closure`
  - `review_existing_candidate`
- 六個入口共用 strict hydration；Reviewer prompt 由 `_reviewer_prompt()` 與
  `_repair_reviewer_prompt()` 兩條路徑產生。

## Production-shaped invariant

fixture 對應：

- run：`legacy-auto-sweep-v1-fortune-0026-chart-bazi-05`
- article：`CHART-BAZI-05`
- deterministic findings：`[]`
- 正文：5 節 × 3 段、精確 1762 字
- Reviewer payload：
  - `semantic_verdict=APPROVE`
  - 四筆語意正面評語誤放入非空 `semantic_findings`
  - 四筆 allowlisted `objective_observations`

結果維持 fail closed：

- Writer / Reviewer：1 / 1
- final：`REJECT`
- `hard_failure=true`
- code：`invalid_reviewer_json:ValueError`
- 原始正面 findings 完整保留於 `external-review.json`，未依 message
  看似正面而自動刪除。

舊 cached payload（`slot/verdict/findings` schema）仍由
`hydrate_rewrite_review()` 拒絕，不能繞過目前 strict schema。

## RED → GREEN

RED：

```text
.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py -q \
  -k 'rewrite_reviewer_prompts_require_empty_findings_for_approval or rewrite_provider_approve_with_positive_findings_fails_closed'

1 failed, 1 passed, 114 deselected
```

失敗點：一般與 repair Reviewer prompt 都未明列
`APPROVE -> []` 與 `non-empty -> REJECT`。

修復：

- 新增單一 `_rewrite_reviewer_semantic_contract()`。
- `semantic_findings` 只允許阻塞核准的問題。
- `semantic_verdict=APPROVE` 時 findings 必須精確為 `[]`。
- findings 非空時 verdict 必須為 `REJECT`。
- 禁止把正面評語、通過項目、摘要或建議放入 findings。
- 兩條 rewrite Reviewer prompt 共用同一契約。
- 未修改 hydration、objective allowlist、call budget 或非 rewrite 流程。

GREEN：

```text
2 passed, 114 deselected
```

Targeted acceptance：

```text
15 passed, 102 deselected
```

涵蓋 production false objective、provider APPROVE + positive findings、
舊 cached payload、hostile semantic mislabel、malformed payload、
deterministic short-circuit、unknown finding、`max_repairs=0/1/2`、
isolated runner、existing-candidate 與 create bounded repair。

## Fresh regression

```text
.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py -q
117 passed in 55.78s

.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py tests/test_agy_content_publisher.py -q
99 passed, 1 warning in 16.03s

.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py -q
19 passed in 0.03s

git diff --check
PASS
```

warning 是既有 `DeprecationWarning: invalid escape sequence '\\/'`，不在本卡
修改範圍。

## Residual risk

- 本卡沒有呼叫真實 provider；prompt compliance 由 production-shaped fixture
  與 test double 證明，實際模型仍可能輸出不合約 payload。
- 若 provider 再輸出 `APPROVE` + 非空 findings、舊 schema、unknown 或 malformed
  observation，strict hydration 會安全退件，不會誤發布；代價是該 run 仍需外部
  重試或後續處置。

## Production acceptance follow-up

### Provenance

- follow-up required base：`cf0097aca06b2bd8b070ae132a8b8b39bb013f1c`
- worktree：`<repo-root>`
- 切換前後均 clean 且無 `index.lock`
- fetch 後 `origin/main` 已前進到
  `4e1d78d90ab7b672c41d9bc711c79fbeccda174f`；本卡依派工契約 detached
  到 required base，candidate direct parent 仍鎖定 `cf0097ac…`
- CodeGraph indexed SHA：`cf0097aca06b2bd8b070ae132a8b8b39bb013f1c`
- graph：287 files、3,714 nodes、3,400 edges

### Production evidence

- run：`legacy-auto-sweep-v1-fortune-0031-expansion-50d-fortune-0031`
- article：`EXPANSION-50D-FORTUNE-0031`
- attempt：02
- deterministic findings：`[]`
- Reviewer：
  - `semantic_verdict=APPROVE`
  - `semantic_findings=[]`
  - objective codes：
    - `SECTION_COUNT_VALID`
    - `PARAGRAPH_COUNT_VALID`
    - `PARAGRAPH_LENGTH_VALID`
    - `TOTAL_LENGTH_VALID`

上述 `_VALID` code 不在 canonical closed allowlist；production-shaped
regression 證明 strict hydration 維持 `invalid_reviewer_json:ValueError`
hard-failure，Writer / Reviewer 各 1 次，沒有誤發布，也沒有新增 alias 或模糊映射。

### RED → GREEN

RED：

```text
.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py -q \
  -k 'rewrite_review_schema_uses_canonical_objective_code_enum or rewrite_reviewer_prompts_require_exact_review_contract or rewrite_provider_valid_suffix_objective_codes_fail_closed'

2 failed, 1 passed, 116 deselected
```

失敗點：

- `rewrite_external_review_schema()` 的
  `objective_observations[].code` 只有任意 string，沒有 closed enum。
- 一般與 repair Reviewer prompt 都沒有列出精確允許 code。
- production `_VALID` fixture 在修復前已正確 fail closed，作為禁止放寬
  parser 的 invariant。

最小修復：

- semantic finding code 維持任意 string，保留 Reviewer 語意權限。
- objective observation code 的 schema enum 直接由
  `sorted(REWRITE_MACHINE_OWNED_REVIEW_CODES)` 產生。
- 新增單一 `_rewrite_reviewer_objective_contract()`，一般與 repair prompt
  共用同一 canonical code 清單，並要求無客觀觀察時輸出 `[]`。
- `hydrate_rewrite_review()`、closed allowlist、casefold 驗證與 Repair-2
  semantic contract 均未放寬。

GREEN：

```text
3 passed, 116 deselected
```

Targeted acceptance：

```text
17 passed, 102 deselected
```

涵蓋 schema/prompt canonical contract、production `_VALID` fail closed、
positive semantic findings、舊 cached payload、hostile semantic mislabel、
malformed/unknown payload、deterministic short-circuit、bounded repairs、
isolated runner、existing-candidate 與 create bounded repair。

### Fresh regression

```text
.venv/bin/python -m pytest tests/test_agy_seo_copy_pipeline.py -q
119 passed in 57.55s

.venv/bin/python -m pytest tests/test_agy_gemini_coordinator.py tests/test_agy_content_publisher.py -q
99 passed, 1 warning in 16.98s

.venv/bin/python -m pytest tests/test_agy_multilingual_pipeline.py -q
19 passed in 0.04s

git diff --check
PASS
```

warning 是既有 `DeprecationWarning: invalid escape sequence '\\/'`，不在本卡
修改範圍。

### Follow-up residual risk

- 本 follow-up 未呼叫真實 provider；JSON schema 與 prompt 現在共用 canonical
  allowlist，但模型仍可能輸出不合約 payload。
- 不合約 `_VALID`、unknown、malformed 或舊 cached payload 會維持安全退件，
  不會誤發布；代價仍是該 run 需要外部重試或後續處置。
- `origin/main` 在派工後已前進；本 candidate 依契約保持 required base 的
  direct child，主線整合時需自行處理較新的 main。
