---
id: CARD-CONTENT-WRITER-VNEXT-RA-SLICE-001-REPAIR-001
card_id: CARD-CONTENT-WRITER-VNEXT-RA-SLICE-001-REPAIR-001
status: ready
execution_authorized: true
production_authorized: false
type: repair
chain: PANTHEON-WRITER-VNEXT-RUNTIME-ACTIVATION
chain_id: PANTHEON-WRITER-VNEXT-RUNTIME-ACTIVATION
role: repair
role_slot: repair
cycle: 2
generation: 1
strictness: strict
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: P1 位於 production-readiness 核心 schema authority，但 finding 與最小修法已固定，屬 strict/core-bounded Repair，使用 GPT-5.5 high，不升 Sol。
required_base_sha: ed59db9cf8a95b068c00ec4bf6709c828c6adf16
required_review_commit: 6b9df0eb75d879599a0e0b1cb8481ba0b4dc6bb6
required_review_verdict: REPAIR_REQUIRED
finding_ids:
  - RA-SLICE-001-REVIEW-P1-BOOL-SCHEMA-VERSION
ownership: 最小修復 top-level schema_version 的 bool／numeric-equality 型別繞過並補 regression；不擴張 receipt contract。
allowlist:
  - artifacts/fortune_council/content_writer_vnext_execution/CARD-CONTENT-WRITER-VNEXT-RA-SLICE-001-REPAIR-001.md
  - scripts/pantheon_content_capability_receipt.py
  - tests/test_pantheon_content_capability_receipt.py
  - artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_001_repair/**
forbidden_scope:
  - 修改 RA-SLICE-001 implementation evidence、review evidence、原 implementation/review cards、plan 或 planning evidence
  - 修改既有 probe、adapter、coordinator、runner、Publisher、runtime manifest、capacity guard 或 deployment scripts
  - 實作 RA-SLICE-002／003、重構 validator、改 public fields、另建 schema authority 或擴充 finding 範圍
  - 自行 Review、另開 Reviewer／Repair／替代 task、merge、push、deploy、publication、canary、tag、network write、launchctl、服務啟停或正式產文
verification:
  - exact candidate and P1 finding lineage
  - public-behavior RED regression before repair
  - minimal GREEN
  - full RA-SLICE-001 validator tests
  - existing capability probe regression
  - adversarial JSON scalar matrix
  - allowlist audit
  - git diff --check
evidence_path: artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_001_repair/
tdd: required
---

# RA-SLICE-001 Repair-1：封閉 schema_version 型別繞過

## 工作名稱 → 正在做什麼 → 現在狀態

- 工作名稱：修復 Writer vNext Receipt Schema 型別閘門
- 正在做什麼：針對唯一 P1 finding 補 public regression，再做最小型別檢查修復。
- 現在狀態：`REPAIR_READY`；production `NO-GO`、正式服務 `0/4`。

## 固定 Finding

Candidate `ed59db9cf8a95b068c00ec4bf6709c828c6adf16` 的
`scripts/pantheon_content_capability_receipt.py` 使用：

```python
if receipt.get("schema_version") != SCHEMA_VERSION:
```

Python/JSON boolean `True` 因 `True == 1` 而被 canonicalized 成 `status=PASS`。Reviewer 已以 Python boolean 與 JSON round-trip 兩種 probe 獨立重現，finding：

`RA-SLICE-001-REVIEW-P1-BOOL-SCHEMA-VERSION`

## 唯一允許的 Repair

1. 先在既有 test file 新增 public regression，證明 top-level `schema_version=True` 目前未 fail closed。
2. Regression 應覆蓋 JSON scalar 的同類型邊界：`True`、`False`、`1.0`、`"1"`、`None` 均不是 exact integer schema version，必須拋 `CapabilityReceiptError(code="type")`。
3. Validator 必須先驗證 `type(schema_version) is int`，再比較支援的 version value；exact integer `1` 維持通過，其他 integer 維持 `schema_version` error。
4. 不改其他 public field、error code、canonical output、capability sequence 或 evidence contract，不做順手重構。

## TDD 與驗證

依序保存：

- `red.txt`：新增 regression 後、修 code 前的預期 failure。
- `green.txt`：修復後 validator suite 與 probe regression。
- `adversarial-matrix.json`：輸入類別、預期 error code、實際結果摘要。
- `verification-receipt.md`：fixed lineage、changed files、測試與禁制動作聲明。

至少執行：

```text
uv run pytest tests/test_pantheon_content_capability_receipt.py
uv run pytest tests/test_pantheon_content_capability_probe.py
uv run pytest tests/test_pantheon_content_capability_receipt.py tests/test_pantheon_content_capability_probe.py
git diff --check
```

## Acceptance

1. P1 regression 先 RED 後 GREEN，且 exact integer schema version 仍通過。
2. `True`、`False`、`1.0`、`"1"`、`None` 全部 deterministic `type` reject。
3. 既有 65-test baseline 無 regression；新增測試後 combined suite 全綠。
4. Candidate 相對 base 只新增最小修復、tests 與 repair evidence；changed files 完全落在 allowlist。
5. 建立單一 Repair candidate commit，worktree clean。
6. 回報只能是 `RA_SLICE_001_REPAIR_READY_FOR_REVIEW` 或 `BLOCKED`；不得宣稱 REVIEW_GO、ACCEPTED 或 INTEGRATED。

## Stop Conditions

- finding／candidate lineage 不符或 worktree 不乾淨。
- 修復必須改其他模組、contract 或 runtime 才能成立。
- 需要任何外部 write、production、canary、push、deploy、tag、publication、服務啟停或正式產文。
- 同一 blocker 第三次失敗即停止，不做第四次。
