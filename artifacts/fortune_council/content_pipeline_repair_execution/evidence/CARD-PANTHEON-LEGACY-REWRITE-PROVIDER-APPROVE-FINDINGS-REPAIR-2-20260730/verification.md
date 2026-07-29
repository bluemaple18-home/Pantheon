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
