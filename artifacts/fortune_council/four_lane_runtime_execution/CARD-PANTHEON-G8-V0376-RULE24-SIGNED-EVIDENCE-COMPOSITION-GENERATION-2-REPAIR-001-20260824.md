---
id: CARD-PANTHEON-G8-V0376-RULE24-SIGNED-EVIDENCE-COMPOSITION-GENERATION-2-REPAIR-001-20260824
chain_id: PANTHEON-G8-RULE24-SIGNED-EVIDENCE
role: repair
cycle: 1
status: ready
type: strict_core_bounded_repair
thickness: strict
risk: critical
model: gpt-5.5
reasoning: high
model_reason: 修 exact-byte trust boundary 的單一 P1；finding 與修法已收斂。
candidate_sha: 097a2f164e7d77f913f30bd9c364c5a06102c48b
review_result_commit: 4ce136d247b57e32df19ab521e3331fe7abf8846
blocking_findings:
  - V0376-REVIEW-P1-001
ownership:
  - scripts/pantheon_rule24_signed_capacity_evidence.py
  - tests/test_pantheon_rule24_signed_capacity_evidence.py
  - artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0376-RULE24-SIGNED-EVIDENCE-COMPOSITION-GENERATION-2-REPAIR-001-20260824-RESULT.md
  - artifacts/fortune_council/four_lane_runtime_execution/g8_v0376_rule24_signed_evidence_composition_generation_2_repair_001_20260824/**
forbidden_scope:
  - 修改 capacity evaluator、DSSE primitive、其 tests、其他 source/config/metadata/handoff/未追蹤檔
  - 讀取、diff、cherry-pick、merge、套用 0af881df、6de8e487、5ca75022ba、d90137815d、d1e1be51aa
  - 擴 API、重寫 composition、dependency/network/push/deploy/canary/production mutation
verification:
  - /Users/mattkuo/Documents/Pantheon/.venv/bin/python -m pytest -q tests/test_pantheon_rule24_signed_capacity_evidence.py tests/test_pantheon_rule24_dsse_attestation.py tests/test_pantheon_writer_vnext_runtime_activation_capacity.py
  - py_compile、JSON parse、ownership-only、git diff --check
result_path: artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0376-RULE24-SIGNED-EVIDENCE-COMPOSITION-GENERATION-2-REPAIR-001-20260824-RESULT.md
---

# V0376 composition Gen2 Repair-001

## 工作名稱 → 正在做什麼 → 現在狀態

V0376 Repair-001 → 關閉 producer post-bundle artifact drift → READY

## Fixed finding

- `V0376-REVIEW-P1-001`：producer 取得 exact-byte bundle 後又從 paths 重讀 bytes，簽署 bytes 可與 bundle SHA/length metadata 分叉。
- Review probe 已證明 mutation 可得到 `PASS` 且 metadata 不等於 signed current bytes。

## Repair contract

1. 先新增 producer-side post-bundle drift RED test，至少覆蓋 capacity receipt 與一個 cycle artifact。
2. 最小修法：producer 每次讀取後，在簽署前以 bundle 中 verifier-owned SHA256＋byte_length 比對；任一 drift deterministic fail closed。
3. 不得只更新回傳 metadata 配合新 bytes；bundle 既有 identity 是 authority。
4. mismatch 不得輸出 envelope、PASS、authenticated/release fields 或 side effects。
5. 不改 verifier ordering、public APIs、capacity evaluator 或 DSSE primitive。

## Delivery

- 單一 repair candidate commit；parent 精確等於 dispatch source commit。
- RESULT 寫 finding closure、RED/GREEN、完整 commands/results、concrete candidate SHA linkage、remaining risk。
- 只交 `DELIVERED_REPAIR_CANDIDATE`；不得整合、push、派 Review 或開下一張卡。
- 同 blocker第三次停。
