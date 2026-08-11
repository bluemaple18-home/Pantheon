---
id: CARD-CONTENT-WRITER-VNEXT-RA-SLICE-003-REPAIR-001
status: ready
execution_authorized: true
production_authorized: false
type: repair_followup
chain_id: PANTHEON-WRITER-VNEXT-RUNTIME-ACTIVATION
formal_repair_thread_id: 019fefd1-2adb-7052-9e69-cd72a6671378
reservation_card_id: CARD-CONTENT-WRITER-VNEXT-RA-SLICE-001-REPAIR-001-RETRY-1
role: repair
cycle: 3
strictness: strict
model: gpt-5.5
reasoning: high
candidate_base_sha: 0ae5accbc61b942edb547931b779ef3daf47daa7
review_evidence_sha: 4b0516c95ae2f56c482170d6bc4dd2b186e6af0a
allowlist:
  - scripts/agy_content_publisher.py
  - tests/test_agy_content_publisher_capability_receipt.py
  - artifacts/fortune_council/content_writer_vnext_execution/CARD-CONTENT-WRITER-VNEXT-RA-SLICE-003-REPAIR-001.md
  - artifacts/fortune_council/content_writer_vnext_execution/runtime_activation/ra_slice_003_repair/**
forbidden_scope:
  - Coordinator、RA-SLICE-002、implementation/review evidence、retention manifest或共享整合檔
  - 自行 Review、另開 task/replacement、merge、push、deploy、production、canary、publication、tag、服務啟停或cleanup
---

# RA-SLICE-003 Publisher Receipt Repair

## 目標

同一唯一 Repair replacement 修復固定 RA-SLICE-003 candidate 的兩個 P1；不得建立新 Repair task。

## Findings

1. `scripts/agy_content_publisher.py:366`：receipt digest material 包含 absolute-root-dependent `boundary_result`／`operation_trace`。相同語意輸入跨兩個 canonical sandbox roots 必須得到穩定 output digest。
2. `scripts/agy_content_publisher.py:786`：blocked evidence write failure 被 `except Exception: pass` 吞掉。Evidence 無法寫入時必須 fail closed 且可觀察，不得只回原始 `PublishBlocked` 假裝 evidence 完整。

## TDD

1. 先新增 cross-root digest 與 evidence-write failure public regressions。
2. 修 code 前兩測試必須真 RED；否則 `BLOCKED`。
3. 最小修復；維持五段 ordinal、official publisher boundary、legacy API。
4. GREEN：

```text
uv run --frozen pytest tests/test_agy_content_publisher_capability_receipt.py tests/test_agy_content_publisher.py tests/test_pantheon_content_capability_receipt.py tests/test_pantheon_content_capability_probe.py
git diff --check
```

5. 另跑兩個 canonical roots、unwritable evidence root、actual blocked artifact、legacy compatibility、JSON與allowlist audit。
6. 單一 Repair candidate commit；最後 clean。

## 交付

只回 `RA_SLICE_003_REPAIR_READY_FOR_REVIEW` 或 `BLOCKED`。附 candidate／parent SHA、RED／GREEN、changed files、finding→regression mapping。
