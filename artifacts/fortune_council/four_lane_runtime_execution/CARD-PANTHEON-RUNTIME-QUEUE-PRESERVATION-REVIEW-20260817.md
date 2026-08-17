---
id: CARD-PANTHEON-RUNTIME-QUEUE-PRESERVATION-REVIEW-20260817
chain_id: PANTHEON-NEW-FLOW-PRODUCTION-PUBLISH-RECOVERY-20260817
role: reviewer
cycle: 1
status: ready
thickness: strict
risk: high
model: gpt-5.5
reasoning: high
model_reason: 固定 candidate 的 production promotion queue identity、rollback 與 fail-closed 核心契約審查。
ownership:
  - scripts/pantheon_content_runtime_promotion.py
  - tests/test_pantheon_content_runtime_promotion.py
  - artifacts/fortune_council/four_lane_runtime_execution/runtime_queue_preservation_review_20260817/**
forbidden_scope:
  - 修改 source、tests、candidate commit
  - production runtime、queue、launchd、network、push、merge、tag
  - 建立 Repair 或第二個 Reviewer task
evidence_path: artifacts/fortune_council/four_lane_runtime_execution/runtime_queue_preservation_review_20260817/
---

# Review Runtime Queue Preservation

工作名稱 → 審查 Runtime Queue Preservation
正在做什麼 → 唯讀審查固定 candidate 的 queue snapshot、drift、rollback 與測試證據
現在狀態 → ready；未 activation 前只做 bootstrap

## 固定範圍

- base/card SHA：`8fad3fcbc3940bfde311eac02a5f6010e10f0b41`
- implementation SHA：`b30cf964818e823611dec26b102d4984e01e9214`
- delivery tip／reviewed candidate：`c5cce3db0ae313d5dbd20192f8ffea33451c4039`
- diff：`8fad3fcbc3940bfde311eac02a5f6010e10f0b41..c5cce3db0ae313d5dbd20192f8ffea33451c4039`

## Review axes

1. failed run 僅保存 identity，不復活、不執行、不發布。
2. gsc-copy snapshot 必須 deterministic、包含 path/type/content digest，invalid JSON、symlink、unexpected residue fail closed。
3. duplicate／unexpected／missing run identity 與不允許 status fail closed。
4. plan→apply 間任何 queue/gsc-copy drift 必須 rollback runtime，且不得改寫既有 queue bytes。
5. 空 preserve list 不得繞過非空 runs/gsc-copy 檢查。
6. tests 必須實際證明上述正向與負向；不得只驗狀態文案。
7. 檢查效能／TOCTOU／path traversal／非 JSON bytes／目錄 identity／snapshot sorting。

## 驗證

- 完整讀 candidate diff 與 evidence。
- `uv run --frozen --group dev pytest tests/test_pantheon_content_runtime_manifest.py tests/test_pantheon_content_runtime_promotion.py -q`
- `git diff --check 8fad3fcbc3940bfde311eac02a5f6010e10f0b41..c5cce3db0ae313d5dbd20192f8ffea33451c4039`
- finding 必須含 severity、path:line、trigger、risk、fix、validation gap、confidence。

## Verdict

- 只有未解 P0/P1 可 `REVIEW_NO_GO`。
- 無 P0/P1：`REVIEW_GO`；P2/P3 列 residual risk/backlog。
- Reviewer 不得修改 candidate；證據寫入唯一 evidence path並 commit review-only receipt。
