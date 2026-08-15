# APF Gate A validator 與 authorization consumption 實作卡

## 目標

將 Gate A pre-mutation 判斷移入 deterministic code，避免 evidence metadata 缺口觸發新 root chain。

## 邊界

- 只改：
  - `scripts/pantheon_gate_a_governance.py`
  - `tests/test_pantheon_gate_a_governance.py`
  - 本卡
- 不改 runtime promotion、Publisher、queue、scheduler、LaunchAgent、文章或 SEO 內容。
- 不執行 Gate A apply、finalize、Gate B、publish、tag、push 或其他 production mutation。

## Slice 與追溯

### APF-GOV-SLICE-001

- traces_to：`FR-APF-GOV-001`、`FR-APF-GOV-002`、`SC-APF-GOV-001`
- blocking_edges：無；目前 frontier。
- 行為：驗證 required schema、repo-relative evidence root、path traversal、duplicate root、exact argv artifact 與 digest binding。
- gate：`schema_gate`＋`recompute_gate`。
- 驗收：missing field、traversal、duplicate、digest drift 全部在 mutation 前回 `BLOCKED_BEFORE_MUTATION`。

### APF-GOV-SLICE-002

- traces_to：`FR-APF-GOV-003`、`SC-APF-GOV-002`、`SC-APF-GOV-003`
- blocking_edges：`APF-GOV-SLICE-001`。
- 行為：以 immutable tuple digest＋`apply_calls` 判斷 authorization 是否仍可用。
- gate：`schema_gate`＋`trace_gate`。
- 驗收：tuple unchanged＋`apply_calls=0` 保持有效；tuple drift 或 `apply_calls>0` fail closed。

## Immutable tuple

- production target
- source SHA
- plan digest
- exact apply argv digest
- mutation scope
- rollback contract
- authorization expiry／revocation state

`evidence_root` 與 receipt metadata 不屬於 tuple；不得改變 production argv、write path 或 rollback 行為。

## 驗證

1. `uv run --python .venv/bin/python pytest -q tests/test_pantheon_gate_a_governance.py`
2. `uv run --python .venv/bin/python pytest -q tests/test_pantheon_content_runtime_promotion.py tests/test_pantheon_gate_a_governance.py`
3. 以 synthetic valid authorization 執行 public validator CLI，預期 `READY`、`apply_calls=0`、`production_mutation=0`。
4. `git diff --check`

## 交付

- 單一 candidate commit。
- 單一既有 Reviewer thread 複審。
- Reviewer APPROVED 後才整合／push。
- production mutation 固定為 `0`。
